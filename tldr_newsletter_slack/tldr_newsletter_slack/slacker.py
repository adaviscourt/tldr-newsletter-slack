import slack_sdk
import time


class Slacker:
    def __init__(self, channel: str, token: str):
        self.slacker = slack_sdk.WebClient(token=token)
        self.channel = channel

    def post_message(self, text: str, username: str, icon_emoji: str):
        self.slacker.chat_postMessage(
            channel=self.channel,
            text=text,
            username=username,
            icon_emoji=icon_emoji,
            unfurl_links=False,
        )

    def route_articles(self, articles: dict) -> None:
        summary_message = f"*{articles['metadata']['title']}*\n_{articles['metadata']['description']}._"
        if articles.get("cache_date"):
            summary_message += f"\nNo new articles since {articles.get('cache_date')}."
        else:
            summary_message += f"\nFound {articles['metadata']['total_categories']} categories and {articles['metadata']['total_articles']} articles for date {articles['metadata']['date']}."
        self.post_message(
            text=summary_message,
            username=f"TLDR Newsletter Bot",
            icon_emoji=articles["metadata"]["emoji"],
        )
        if not articles.get("cache_date"):
            for _, data in articles["data"]["categories"].items():
                time.sleep(10)
                for article in data["articles"]:
                    if data["title"]:  # Check if category title exists (usually sponsor article if not)
                        msg = f"""<{article.link}|{article.title}>\n{article.text}"""
                        self.post_message(
                            text=msg,
                            username=data["title"],
                            icon_emoji=data["emoji"],
                    )
