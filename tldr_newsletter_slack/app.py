import os
import logging
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from tldr_newsletter_slack.newsletter import NewsletterArticles
from tldr_newsletter_slack.slacker import Slacker
from tldr_newsletter_slack.database import db_manager, is_cache_enabled
from tldr_newsletter_slack.common.constants import ACCEPTED_NEWSLETTERS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Suppress verbose Slack SDK debug messages
logging.getLogger("slack_sdk").setLevel(logging.WARNING)

app = Flask(__name__)


def _post_newsletter(newsletter_type: str, channel: str | None = None):
    token = os.getenv("SLACK_API_TOKEN")

    if newsletter_type not in ACCEPTED_NEWSLETTERS:
        raise ValueError(
            f"Invalid newsletter type: {newsletter_type}, must be one of {list(ACCEPTED_NEWSLETTERS.keys())}"
        )
    if not token:
        raise ValueError("SLACK_API_TOKEN not set")

    channel_prefix = os.getenv("SLACK_CHANNEL_PREFIX", "tldr-newsletter-")
    target_channel = channel or f"{channel_prefix}{newsletter_type}"

    newsletter = NewsletterArticles(newsletter=newsletter_type)
    articles = newsletter.get_articles()
    logging.debug(
        f"Fetched {articles['metadata']['total_articles']} articles for date {articles['metadata']['date']}"
    )

    slacker = Slacker(channel=target_channel, token=token)
    slacker.route_articles(articles)


def _configured_newsletters() -> list[str]:
    newsletters = os.getenv("NEWSLETTERS", "data,tech,devops,product,ai")
    return [newsletter.strip() for newsletter in newsletters.split(",") if newsletter.strip()]


def _next_run_at(schedule_time: str) -> datetime:
    hour, minute = [int(part) for part in schedule_time.split(":", 1)]
    now = datetime.now()
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return next_run


def _run_scheduler():
    schedule_time = os.getenv("SCHEDULE_TIME", "06:00")
    logging.info(f"Scheduler enabled for {schedule_time} with newsletters: {_configured_newsletters()}")

    if os.getenv("SCHEDULER_RUN_ON_START", "false").lower() == "true":
        _run_scheduled_newsletters()

    while True:
        next_run = _next_run_at(schedule_time)
        logging.info(f"Next scheduled run at {next_run.isoformat()}")
        while True:
            seconds_until_run = (next_run - datetime.now()).total_seconds()
            if seconds_until_run <= 0:
                break
            time.sleep(min(seconds_until_run, 3600))
        _run_scheduled_newsletters()


def _run_scheduled_newsletters():
    for newsletter_type in _configured_newsletters():
        try:
            logging.info(f"Posting scheduled newsletter: {newsletter_type}")
            _post_newsletter(newsletter_type)
        except Exception as e:
            logging.error(f"Error posting scheduled newsletter {newsletter_type}: {e}")


def _start_scheduler():
    if os.getenv("SCHEDULER_ENABLED", "false").lower() != "true":
        return
    scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
    scheduler_thread.start()


@app.route("/articles", methods=["GET"])
def get_articles():
    newsletter_type = request.args.get("newsletter", "tech")  # Default to 'tech'
    logging.debug(f"Fetching articles for newsletter: {newsletter_type}")
    if newsletter_type not in ACCEPTED_NEWSLETTERS:
        return (
            jsonify(
                {
                    "error": f"Invalid newsletter type: {newsletter_type}, must be one of {list(ACCEPTED_NEWSLETTERS.keys())}"
                }
            ),
            400,
        )
    try:
        newsletter = NewsletterArticles(newsletter=newsletter_type)
        articles = newsletter.get_articles()
        logging.debug(f"Fetched articles: {articles}")
        return jsonify(articles), 200
    except Exception as e:
        logging.error(f"Error fetching articles: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/post-articles", methods=["POST"])
def post_articles():
    data = request.get_json(silent=True) or {}
    newsletter_type = data.get("newsletter", "tech")  # Default to 'tech'
    channel = data.get("channel")

    if newsletter_type not in ACCEPTED_NEWSLETTERS:
        return (
            jsonify(
                {
                    "error": f"Invalid newsletter type: {newsletter_type}, must be one of {list(ACCEPTED_NEWSLETTERS.keys())}"
                }
            ),
            400,
        )
    try:
        _post_newsletter(newsletter_type, channel)
        return jsonify({"message": "Articles posted successfully"}), 200
    except Exception as e:
        logging.error(f"Error posting articles: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    if is_cache_enabled():
        db_status = db_manager.is_available()
        if db_status:
            return jsonify({"status": "ok"}), 200
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Cache database initialization failed",
                        "reason": db_manager.unavailable_reason,
                    }
                ),
                500,
            )
    else:
        return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    _start_scheduler()
    app.run(host="0.0.0.0", port=5000)
