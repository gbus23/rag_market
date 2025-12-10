"""
RAG app améliorée avec intégration Kafka.
Consomme les articles du topic Kafka et les analyse avec Mistral 3.

Exemple d'utilisation:
    python3 rag_app_kafka.py
    > Why did TSLA drop?
    > What happened with AAPL?
"""

import json
import threading
from pathlib import Path
from typing import Optional
from collections import deque
from datetime import datetime, timezone, timedelta

import requests
from confluent_kafka import Consumer, KafkaError, OFFSET_BEGINNING

from ingestion.ticker_resolver_local import resolve_ticker_from_text
from ingestion.config import KAFKA_BOOTSTRAP_SERVERS, NEWS_TOPIC


# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "mistral:latest"
MAX_ARTICLES_MEMORY = 1000  # Keep last N articles in memory


class KafkaArticleConsumer:
    """Consumes articles from Kafka and maintains a rolling buffer."""
    
    def __init__(
        self,
        bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS,
        topic: str = NEWS_TOPIC,
        max_articles: int = MAX_ARTICLES_MEMORY,
    ):
        """Initialize Kafka consumer."""
        self.topic = topic
        self.articles = deque(maxlen=max_articles)
        self.articles_by_ticker = {}  # ticker -> list of articles
        
        # Kafka consumer config
        conf = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": "rag-app-consumer",
            "auto.offset.reset": "latest",  # Start from end (new messages)
            "enable.auto.commit": True,
            "session.timeout.ms": 6000,
        }
        
        self.consumer = Consumer(conf)
        self.consumer.subscribe([topic])
        self.running = False
        self.consumer_thread = None
        
    def start(self):
        """Start consuming messages in background thread."""
        self.running = True
        self.consumer_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.consumer_thread.start()
        print(f"🔄 Kafka consumer started for topic '{self.topic}'")
    
    def stop(self):
        """Stop consuming messages."""
        self.running = False
        if self.consumer_thread:
            self.consumer_thread.join(timeout=5)
        self.consumer.close()
        print("🛑 Kafka consumer stopped")
    
    def _consume_loop(self):
        """Background loop that consumes messages."""
        while self.running:
            try:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(f"❌ Kafka error: {msg.error()}")
                        break
                
                # Parse article from Kafka message
                try:
                    article = json.loads(msg.value().decode('utf-8'))
                    self._add_article(article)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Failed to parse JSON: {e}")
                
            except Exception as e:
                print(f"❌ Consumer error: {e}")
    
    def _add_article(self, article: dict):
        """Add article to buffer and index by ticker."""
        self.articles.append(article)
        
        # Index by tickers
        tickers = article.get("tickers", [])
        for ticker in tickers:
            if ticker not in self.articles_by_ticker:
                self.articles_by_ticker[ticker] = deque(maxlen=100)
            self.articles_by_ticker[ticker].append(article)
        
        print(f"📰 New article: {article.get('headline', 'No title')} -> {tickers}")
    
    def get_articles_by_ticker(self, ticker: str, limit: int = 5) -> list[dict]:
        """Get recent articles for a specific ticker."""
        ticker = ticker.upper()
        if ticker in self.articles_by_ticker:
            return list(self.articles_by_ticker[ticker])[-limit:]
        return []
    
    def search_articles(self, query: str, limit: int = 10) -> list[dict]:
        """Search articles by keyword."""
        query_lower = query.lower()
        results = []
        
        for article in reversed(self.articles):
            headline = article.get("headline", "").lower()
            description = article.get("description", "").lower()
            
            if query_lower in headline or query_lower in description:
                results.append(article)
                if len(results) >= limit:
                    break
        
        return results


class RAGAppKafka:
    """RAG application with Kafka integration."""
    
    def __init__(
        self,
        bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS,
        topic: str = NEWS_TOPIC,
    ):
        """Initialize RAG app with Kafka consumer."""
        self.consumer = KafkaArticleConsumer(
            bootstrap_servers=bootstrap_servers,
            topic=topic,
        )
        self.consumer.start()
    
    def _format_context(self, articles: list[dict]) -> str:
        """Format articles into context for the LLM."""
        if not articles:
            return "No articles found for this ticker."
        
        context = "Recent articles about this stock:\n\n"
        for i, article in enumerate(articles, 1):
            headline = article.get("headline", "No title")
            description = article.get("description", "")
            source = article.get("source", "Unknown")
            published_at = article.get("published_at", "")
            
            context += f"{i}. [{source}] {headline}\n"
            if description:
                context += f"   Summary: {description}\n"
            if published_at:
                context += f"   Published: {published_at}\n"
            context += "\n"
        
        return context
    
    def query(self, question: str) -> str:
        """
        Process a user question and return an answer using RAG.
        
        Args:
            question: User question about stock movements
            
        Returns:
            Answer generated by Mistral 3
        """
        # 1. Extract ticker from question
        detected_ticker = resolve_ticker_from_text(question)
        
        if not detected_ticker:
            return "Could not identify a stock ticker in your question. Please mention a ticker like TSLA, AAPL, GOOGL, etc."
        
        ticker = detected_ticker.upper()
        print(f"\n🔍 Detected ticker: {ticker}")
        
        # 2. Filter relevant articles from Kafka
        articles = self.consumer.get_articles_by_ticker(ticker, limit=5)
        print(f"📰 Found {len(articles)} relevant articles")
        
        if not articles:
            return f"No recent articles found about {ticker}. Check if the ingestion is running and articles are being published to Kafka."
        
        # 3. Format context
        context = self._format_context(articles)
        
        # 4. Build prompt for LLM
        prompt = f"""You are a financial analyst. Answer the user's question about a stock movement based on the articles provided.

Articles context:
{context}

User question: {question}

Provide a concise analysis (2-3 sentences) based on the articles above. Be factual and reference the sources."""
        
        # 5. Query Mistral via Ollama
        try:
            response = self._call_ollama(prompt)
            return response
        except Exception as e:
            return f"Error calling Mistral: {e}\n\nMake sure Ollama is running with: ollama run mistral:latest"
    
    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API with prompt."""
        url = f"{OLLAMA_BASE_URL}/api/generate"
        
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7,
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "No response from model")
        except requests.exceptions.ConnectionError:
            raise Exception(
                f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
                "Make sure Ollama is running: ollama serve"
            )
        except Exception as e:
            raise Exception(f"Error calling Ollama: {e}")
    
    def close(self):
        """Close the Kafka consumer."""
        self.consumer.stop()


def main():
    """Main interactive loop."""
    print("=" * 60)
    print("📊 Stock Analysis RAG App with Kafka")
    print("=" * 60)
    print("\n📋 Make sure you have:")
    print("  1. Kafka running (kafka-broker-api.sh)")
    print("  2. News ingestion running (python3 -m ingestion.ingest_news_finhub)")
    print("  3. Ollama running (ollama serve)")
    print("\nAsk questions like:")
    print("  - Why did TSLA drop?")
    print("  - What happened with AAPL today?")
    print("  - Why is GOOGL moving?")
    print("\nType 'quit' to exit.\n")
    
    app = RAGAppKafka()
    
    # Wait a bit for consumer to connect
    import time
    time.sleep(2)
    
    try:
        while True:
            try:
                question = input("\n🤔 Your question: ").strip()
                
                if not question:
                    continue
                
                if question.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                
                print("\n⏳ Analyzing...")
                answer = app.query(question)
                print("\n📝 Answer:")
                print("-" * 60)
                print(answer)
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    finally:
        app.close()


if __name__ == "__main__":
    main()
