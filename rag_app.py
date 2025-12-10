"""
RAG app pour analyser les raisons des mouvements de stock en temps réel.
Consomme les articles directement depuis Kafka via les APIs (Finnhub, Scrapers).

Utilise Mistral 3 en local via Ollama.

Exemple d'utilisation:
    python3 rag_app.py
    > Why did TSLA drop?
    > What happened with AAPL?
"""

import json
import threading
import time
from collections import deque
from typing import Optional

import requests
from confluent_kafka import Consumer, KafkaError

from ingestion.ticker_resolver_local import resolve_ticker_from_text
from ingestion.config import KAFKA_BOOTSTRAP_SERVERS, NEWS_TOPIC


# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "mistral:latest"
MAX_ARTICLES_MEMORY = 1000  # Keep last N articles in memory


class KafkaArticleBuffer:
    """Buffer pour consommer les articles depuis Kafka en temps réel."""
    
    def __init__(
        self,
        bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS,
        topic: str = NEWS_TOPIC,
    ):
        """Initialize Kafka consumer buffer."""
        self.topic = topic
        self.articles = deque(maxlen=MAX_ARTICLES_MEMORY)
        self.articles_by_ticker = {}  # ticker -> deque of articles
        
        # Kafka consumer config
        conf = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": "rag-app-consumer",
            "auto.offset.reset": "latest",
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


class RAGApp:
    """RAG application consuming real-time data from Kafka APIs."""
    
    def __init__(self):
        """Initialize RAG app with Kafka consumer."""
        self.buffer = KafkaArticleBuffer()
        self.buffer.start()
        time.sleep(1)  # Wait for consumer to start
    
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
        print(f"🔍 Detected ticker: {ticker}")
        
        # 2. Get articles from Kafka buffer
        articles = self.buffer.get_articles_by_ticker(ticker, limit=5)
        print(f"📰 Found {len(articles)} relevant articles from Kafka")
        
        if not articles:
            return f"No recent articles found about {ticker}. The ingestion pipeline might still be loading data. Try again in a moment!"
        
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
            return f"Error calling Mistral: {e}\n\nMake sure Ollama is running with: ollama serve"
    
    def close(self):
        """Close the Kafka consumer."""
        self.buffer.stop()
    
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


def main():
    """Main interactive loop."""
    print("=" * 60)
    print("📊 Stock Analysis RAG App (Real-time Kafka + Mistral 3)")
    print("=" * 60)
    print("\n📋 Configuration:")
    print(f"   Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"   Topic: {NEWS_TOPIC}")
    print(f"   Model: {MODEL_NAME}")
    print("\n⚠️  Make sure you have running:")
    print("   1. Kafka broker")
    print("   2. News ingestion (ingest_news_finhub.py + ingest_news_scrapping.py)")
    print("   3. Ollama server (ollama serve)")
    print("\n💡 Ask questions like:")
    print("   - Why did TSLA drop?")
    print("   - What happened with AAPL?")
    print("   - Why is GOOGL moving?")
    print("\nType 'quit' to exit.\n")
    
    app = RAGApp()
    
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
