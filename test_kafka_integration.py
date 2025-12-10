#!/usr/bin/env python3
"""
Script de test pour vérifier l'intégration Kafka + RAG.

Cet script:
1. Vérifie que Kafka est disponible
2. Crée des articles de test dans Kafka
3. Teste la RAG app en mode Kafka
4. Affiche le résumé des résultats
"""

import json
import sys
import time
from pathlib import Path

def check_kafka_connection():
    """Vérifie la connexion à Kafka."""
    print("🔍 Checking Kafka connection...")
    
    try:
        from confluent_kafka import Producer
        from ingestion.config import KAFKA_BOOTSTRAP_SERVERS
        
        conf = {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "test-client",
        }
        
        producer = Producer(conf)
        
        # Test publish
        def delivery_report(err, msg):
            if err:
                raise Exception(f"Kafka error: {err}")
        
        producer.produce(
            topic="test-topic",
            value=b"test",
            on_delivery=delivery_report,
        )
        producer.flush()
        producer.close()
        
        print(f"✅ Kafka is ready at {KAFKA_BOOTSTRAP_SERVERS}")
        return True
    except Exception as e:
        print(f"❌ Kafka is not available: {e}")
        print("   Start Kafka with: kafka-broker-api.sh")
        return False


def check_ollama():
    """Vérifie la connexion à Ollama."""
    print("\n🔍 Checking Ollama connection...")
    
    try:
        import requests
        
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        
        models = response.json().get("models", [])
        print(f"✅ Ollama is ready with {len(models)} model(s)")
        
        if not any("mistral" in m.get("name", "").lower() for m in models):
            print("   ⚠️  Mistral not found. Pull it with: ollama pull mistral:latest")
        
        return True
    except Exception as e:
        print(f"❌ Ollama is not available: {e}")
        print("   Start Ollama with: ollama serve")
        return False


def publish_test_articles():
    """Publie des articles de test dans Kafka."""
    print("\n📰 Publishing test articles to Kafka...")
    
    try:
        from ingestion.kafka_producer import create_producer, send_json
        from ingestion.config import NEWS_TOPIC
        
        producer = create_producer(client_id="test-publisher")
        
        test_articles = [
            {
                "id": "test-1",
                "source": "Test",
                "headline": "Tesla drops after earnings miss",
                "description": "TSLA stock fell 5% following earnings announcement",
                "url": "https://example.com/1",
                "tickers": ["TSLA"],
                "published_at": "2025-12-10T15:30:00Z",
                "received_at": "2025-12-10T15:35:00Z",
            },
            {
                "id": "test-2",
                "source": "Test",
                "headline": "Apple reports strong Q4 results",
                "description": "AAPL beats earnings expectations with strong guidance",
                "url": "https://example.com/2",
                "tickers": ["AAPL"],
                "published_at": "2025-12-09T10:00:00Z",
                "received_at": "2025-12-09T10:05:00Z",
            },
            {
                "id": "test-3",
                "source": "Test",
                "headline": "Nvidia announces new AI chip",
                "description": "NVDA launches next generation GPU for AI applications",
                "url": "https://example.com/3",
                "tickers": ["NVDA"],
                "published_at": "2025-12-08T14:20:00Z",
                "received_at": "2025-12-08T14:25:00Z",
            },
        ]
        
        for article in test_articles:
            send_json(producer, NEWS_TOPIC, article, key=article["id"])
            print(f"   ✓ Published: {article['headline']}")
        
        producer.flush()
        print(f"✅ Published {len(test_articles)} test articles")
        return True
    except Exception as e:
        print(f"❌ Failed to publish articles: {e}")
        return False


def test_rag_app():
    """Teste la RAG app en mode Kafka."""
    print("\n🤖 Testing RAG app...")
    
    try:
        from rag_app_kafka import RAGAppKafka
        
        print("   Initializing RAG app...")
        app = RAGAppKafka()
        
        # Wait for consumer to receive messages
        print("   Waiting for articles to be consumed...")
        time.sleep(3)
        
        test_questions = [
            "Why did TSLA drop?",
            "What happened with AAPL?",
        ]
        
        for question in test_questions:
            print(f"\n   Q: {question}")
            try:
                answer = app.query(question)
                print(f"   A: {answer[:200]}...")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        app.close()
        print("\n✅ RAG app test completed")
        return True
    except Exception as e:
        print(f"❌ RAG app test failed: {e}")
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 Kafka + RAG Integration Test")
    print("=" * 60)
    
    results = {
        "Kafka": check_kafka_connection(),
        "Ollama": check_ollama(),
    }
    
    if results["Kafka"]:
        results["Articles"] = publish_test_articles()
    else:
        results["Articles"] = False
    
    if results["Kafka"] and results["Ollama"]:
        results["RAG App"] = test_rag_app()
    else:
        results["RAG App"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:.<40} {status}")
    
    all_passed = all(results.values())
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! RAG + Kafka is ready to use.")
        print("\nNext steps:")
        print("1. Start news ingestion:")
        print("   python3 -m ingestion.ingest_news_finhub &")
        print("   python3 -m ingestion.ingest_news_scrapping &")
        print("\n2. Start RAG app:")
        print("   USE_KAFKA=true python3 rag_app.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
