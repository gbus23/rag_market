"""
Test script for RAG app with sample data.
"""

import json
from pathlib import Path
from rag_app import RAGApp


def create_sample_articles():
    """Create sample articles for testing."""
    sample_articles = [
        {
            "title": "Tesla stock drops 5% after earnings miss",
            "description": "TSLA missed earnings expectations in Q4 2025",
            "content": "Tesla reported lower than expected earnings. The TSLA stock dropped after the announcement. Investors are concerned about margins.",
            "source": "FinHub",
            "date": "2025-12-10"
        },
        {
            "title": "TSLA shares tumble as production cuts announced",
            "description": "TSLA announces production cuts for next quarter",
            "content": "TSLA announced production cuts due to supply chain issues. The TSLA stock fell 3% on the news.",
            "source": "FinHub",
            "date": "2025-12-09"
        },
        {
            "title": "Apple reports strong Q4 results",
            "description": "AAPL beats earnings expectations",
            "content": "Apple delivered strong results. AAPL stock rose on the news.",
            "source": "FinHub",
            "date": "2025-12-08"
        },
    ]
    
    articles_dir = Path(__file__).parent / "ingestion" / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = articles_dir / "sample_articles.json"
    with open(output_file, "w") as f:
        json.dump(sample_articles, f, indent=2)
    
    print(f"✅ Sample articles created at {output_file}")


def test_rag():
    """Test RAG app with sample data."""
    create_sample_articles()
    
    app = RAGApp()
    
    print("\n" + "=" * 60)
    print("Testing RAG App")
    print("=" * 60)
    
    test_questions = [
        "Why did TSLA drop?",
        "What happened with AAPL?",
    ]
    
    for question in test_questions:
        print(f"\n🤔 Q: {question}")
        try:
            answer = app.query(question)
            print(f"📝 A: {answer[:500]}...")  # Show first 500 chars
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_rag()
