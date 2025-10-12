import os
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

Base = declarative_base()

class ArticleCache(Base):
    __tablename__ = 'article_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    newsletter_type = Column(String(50), nullable=False)
    date = Column(String(20), nullable=False)
    articles_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __init__(self, cache_key: str, newsletter_type: str, date: str, articles_json: str):
        self.cache_key = cache_key
        self.newsletter_type = newsletter_type
        self.date = date
        self.articles_json = articles_json

class DatabaseManager:
    def __init__(self):
        self.db_url = self._get_database_url()
        self.engine = None
        self.Session = None
        self._initialize_db()
    
    def _serialize_articles(self, articles_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Article namedtuples to dictionaries for JSON serialization."""
        import copy
        serialized = copy.deepcopy(articles_data)
        if "data" in serialized and "categories" in serialized["data"]:
            for category_data in serialized["data"]["categories"].values():
                if isinstance(category_data, dict) and "articles" in category_data:
                    serialized_articles = []
                    for article in category_data["articles"]:
                        if hasattr(article, 'as_dict'):
                            # Use the as_dict method from Article namedtuple
                            serialized_articles.append(article.as_dict())
                        else:
                            # If it's already a dict, keep as is
                            serialized_articles.append(article)
                    category_data["articles"] = serialized_articles
        return serialized
    
    def _reconstruct_articles(self, articles_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mark articles for reconstruction - actual reconstruction happens in newsletter.py"""
        # Just return the data as-is with dict articles
        # The Article.from_dict() conversion will happen in newsletter.py
        return articles_data
    
    def _get_database_url(self) -> str:
        host = os.getenv('DB_HOST', 'postgres')
        port = os.getenv('DB_PORT', '5432')
        user = os.getenv('DB_USER', 'tldr_user')
        password = os.getenv('DB_PASSWORD', 'tldr_password')
        database = os.getenv('DB_NAME', 'tldr_cache')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def _initialize_db(self):
        try:
            self.engine = create_engine(self.db_url, echo=False)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logging.info("Database connection established successfully")
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            self.engine = None
            self.Session = None
    
    def is_available(self) -> bool:
        return self.engine is not None and self.Session is not None
    
    def get_cached_articles(self, newsletter_type: str, date: str) -> Optional[Dict[str, Any]]:
        if not self.is_available():
            logging.warning("Database not available, skipping cache lookup")
            return None
        
        cache_key = f"{newsletter_type}_{date}"
        
        try:
            session = self.Session()
            cached_entry = session.query(ArticleCache).filter_by(cache_key=cache_key).first()
            session.close()
            
            if cached_entry:
                logging.info(f"Cache hit for {cache_key}")
                articles_data = json.loads(cached_entry.articles_json)
                return self._reconstruct_articles(articles_data)
            else:
                logging.info(f"Cache miss for {cache_key}")
                return None
                
        except Exception as e:
            logging.error(f"Error retrieving cached articles: {e}")
            return None
    
    def cache_articles(self, newsletter_type: str, date: str, articles: Dict[str, Any]) -> bool:
        if not self.is_available():
            logging.warning("Database not available, skipping cache storage")
            return False
        
        cache_key = f"{newsletter_type}_{date}"
        
        # Convert Article namedtuples to dictionaries for JSON serialization
        serializable_articles = self._serialize_articles(articles)
        articles_json = json.dumps(serializable_articles)
        
        try:
            session = self.Session()
            
            existing_entry = session.query(ArticleCache).filter_by(cache_key=cache_key).first()
            if existing_entry:
                existing_entry.articles_json = articles_json
                existing_entry.created_at = datetime.utcnow()
                logging.info(f"Updated cache for {cache_key}")
            else:
                new_entry = ArticleCache(
                    cache_key=cache_key,
                    newsletter_type=newsletter_type,
                    date=date,
                    articles_json=articles_json
                )
                session.add(new_entry)
                logging.info(f"Cached articles for {cache_key}")
            
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            logging.error(f"Error caching articles: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()