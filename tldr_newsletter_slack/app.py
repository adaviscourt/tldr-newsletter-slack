import os
import logging
from flask import Flask, request, jsonify
from tldr_newsletter_slack.newsletter import NewsletterArticles
from tldr_newsletter_slack.slacker import Slacker
from tldr_newsletter_slack.database import db_manager
from tldr_newsletter_slack.common.constants import ACCEPTED_NEWSLETTERS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Suppress verbose Slack SDK debug messages
logging.getLogger("slack_sdk").setLevel(logging.WARNING)

app = Flask(__name__)


@app.route("/articles", methods=["GET"])
def get_articles():
    newsletter_type = request.args.get("newsletter", "tech")  # Default to 'tech'
    logging.debug(
        f"Fetching articles for newsletter: {newsletter_type}"
    )
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
        newsletter = NewsletterArticles(
            newsletter=newsletter_type
        )
        articles = newsletter.get_articles()
        logging.debug(f"Fetched articles: {articles}")
        return jsonify(articles), 200
    except Exception as e:
        logging.error(f"Error fetching articles: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/post-articles", methods=["POST"])
def post_articles():
    data = request.get_json()
    newsletter_type = data.get("newsletter", "tech")  # Default to 'tech'
    channel = data.get("channel", f"tldr-newsletter-{newsletter_type}")  # Default Slack channel
    token = os.getenv("SLACK_API_TOKEN")

    if newsletter_type not in ACCEPTED_NEWSLETTERS:
        return (
            jsonify(
                {
                    "error": f"Invalid newsletter type: {newsletter_type}, must be one of {list(ACCEPTED_NEWSLETTERS.keys())}"
                }
            ),
            400,
        )
    if not token:
        return jsonify({"error": "SLACK_API_TOKEN not set"}), 500
    try:
        newsletter = NewsletterArticles(
            newsletter=newsletter_type
        )
        articles = newsletter.get_articles()
        logging.debug(
            f"Fetched {articles['metadata']['total_articles']} articles for date {articles['metadata']['date']}"
        )

        slacker = Slacker(channel=channel, token=token)
        slacker.route_articles(articles)

        return jsonify({"message": "Articles posted successfully"}), 200
    except Exception as e:
        logging.error(f"Error posting articles: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    if os.getenv("ENABLE_DATABASE", "false") == "true":
        db_status = db_manager.is_available()
        if db_status:
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
    else:
        return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
