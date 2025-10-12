from typing import NamedTuple, Dict, List, Tuple
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
from collections import defaultdict

from tldr_newsletter_slack.common.constants import ACCEPTED_NEWSLETTERS
from tldr_newsletter_slack.database import db_manager

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Article(NamedTuple):
    link: str
    title: str
    text: str
    parent_section_title: str
    parent_section_emoji: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "link": self.link,
            "title": self.title,
            "text": self.text,
            "parent_section_title": self.parent_section_title,
            "parent_section_emoji": self.parent_section_emoji,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Article':
        """Create Article instance from dictionary."""
        return cls(
            link=data["link"],
            title=data["title"],
            text=data["text"],
            parent_section_title=data["parent_section_title"],
            parent_section_emoji=data["parent_section_emoji"]
        )


class NewsletterArticles:
    base_url = "https://tldr.tech"

    def __init__(self, newsletter: str = "tech"):
        self.newsletter = newsletter
        self.newsletter_link = (
            f"{self.base_url}/{ACCEPTED_NEWSLETTERS[self.newsletter]['endpoint']}"
        )

    def get_articles(self) -> Dict[str, List[Article]]:
        date, page = self._get_recent_articles()
        
        # Try to get from cache first
        cached_articles = db_manager.get_cached_articles(self.newsletter, date)
        if cached_articles:
            logging.info(f"Returning cached articles for {self.newsletter} on {date}")
            # Convert cached dictionaries back to Article namedtuples
            return self._reconstruct_articles_from_cache(cached_articles)
        
        # If not in cache, scrape and cache
        logging.info(f"Scraping articles for {self.newsletter} on {date}")
        soup = self._get_soup(page)
        articles = {"data": {}}
        articles["data"]["categories"] = defaultdict(list)
        newsletter_info = ACCEPTED_NEWSLETTERS[self.newsletter]
        articles["metadata"] = {
            "date": date,
            "title": newsletter_info["title"],
            "emoji": newsletter_info["emoji"],
            "description": newsletter_info["description"],
        }
        for section in soup.find_all("section"):
            header = section.find("header")
            if header:
                parent_section_title = (
                    header.find("h3").text.strip() if header.find("h3") else None
                )
                parent_section_emoji = (
                    header.find("div").text.strip() if header.find("div") else None
                )
                articles["data"]["categories"][parent_section_title] = defaultdict(dict)
                articles["data"]["categories"][parent_section_title][
                    "title"
                ] = parent_section_title
                articles["data"]["categories"][parent_section_title][
                    "emoji"
                ] = parent_section_emoji
                articles["data"]["categories"][parent_section_title]["articles"] = []

                for article in section.find_all("article"):
                    link_tag = article.find("a", href=True)
                    title_tag = link_tag.find("h3") if link_tag else None
                    summary_tag = article.find("div", class_="newsletter-html")

                    if link_tag and title_tag and summary_tag:
                        articles["data"]["categories"][parent_section_title][
                            "articles"
                        ].append(
                            Article(
                                link=link_tag["href"],
                                title=title_tag.text.strip(),
                                text=summary_tag.text.strip(),
                                parent_section_title=parent_section_title,
                                parent_section_emoji=parent_section_emoji,
                            )
                        )
        total_categories = len(articles["data"]["categories"])
        total_articles = sum(
            [
                len(category_data["articles"]) if isinstance(category_data, dict) and "articles" in category_data else 0
                for category_data in articles["data"]["categories"].values()
            ]
        )
        articles["metadata"]["total_categories"] = total_categories
        articles["metadata"]["total_articles"] = total_articles
        
        # Cache the scraped articles
        db_manager.cache_articles(self.newsletter, date, articles)
        
        return articles
    
    def _reconstruct_articles_from_cache(self, cached_data: Dict[str, any]) -> Dict[str, any]:
        """Convert cached dictionaries back to Article namedtuples."""
        if "data" in cached_data and "categories" in cached_data["data"]:
            for category_data in cached_data["data"]["categories"].values():
                if isinstance(category_data, dict) and "articles" in category_data:
                    reconstructed_articles = []
                    for article_data in category_data["articles"]:
                        article = Article.from_dict(article_data)
                        reconstructed_articles.append(article)
                    category_data["articles"] = reconstructed_articles
        cached_data["cache_date"] = cached_data["metadata"]["date"]
        return cached_data

    def _get_soup(self, page: requests.Response) -> BeautifulSoup:
        soup = BeautifulSoup(page.content, "html.parser")
        return soup

    def _get_articles_by_date(self, date) -> requests.Response:
        url = f"{self.newsletter_link}/{date}"
        page = requests.get(url)
        if page.url != url:
            logging.debug(f"Redirected to {page.url} for date {date}")
            page = requests.Response()
            page.status_code = 404
            page._content = b"No articles found for this date."
        return page

    def _get_recent_articles(self) -> Tuple[str, requests.Response]:
        for offset in [0, 1, 2, 3]:
            date = (datetime.today() - timedelta(days=offset)).strftime("%Y-%m-%d")
            page = self._get_articles_by_date(date)
            if page.status_code == 200:
                break
        return date, page


if __name__ == "__main__":
    newsletter = NewsletterArticles(newsletter="data")
    articles = newsletter.get_articles()
