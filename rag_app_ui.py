"""
Streamlit UI for the RAG app.

Run with: streamlit run rag_app_ui.py
"""

import streamlit as st
import time
from rag_app import RAGApp
from ingestion.ticker_resolver_local import resolve_ticker_from_text


@st.cache_resource
def load_rag_app():
    """Load RAG app (cached). Starts Kafka consumer on first load."""
    app = RAGApp()
    st.session_state.app_loaded = True
    return app


def main():
    st.set_page_config(page_title="📊 Stock Analysis RAG", layout="wide")
    
    st.title("📊 Stock Analysis RAG")
    st.markdown("Ask questions about stock movements using real-time Kafka data and Mistral 3 AI")
    
    # Sidebar info
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        **Real-time Stock Analysis**
        
        This app uses:
        - **Kafka** for real-time data streaming
        - **Mistral 3** (via Ollama) for LLM analysis
        - **RAG** to retrieve relevant articles
        - **Ticker detection** to identify stock symbols
        
        ### Prerequisites
        1. Kafka running: `kafka-server-start server.properties`
        2. Ollama running: `ollama serve`
        3. Ingestion scripts running:
           ```bash
           python3 -m ingestion.ingest_news_finhub &
           python3 -m ingestion.ingest_news_scrapping &
           ```
        """)
        
        st.divider()
        st.subheader("Example Questions")
        examples = [
            "Why did TSLA drop?",
            "What happened with AAPL?",
            "Why is GOOGL moving?",
            "Tell me about MSFT",
            "Is there news about NVDA?",
        ]
        for ex in examples:
            st.caption(f"💬 {ex}")
    
    # Main content
    app = load_rag_app()
    
    # Display status
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Articles in Buffer", len(app.buffer.articles))
    with col2:
        st.metric("Tickers Indexed", len(app.buffer.articles_by_ticker))
    with col3:
        st.metric("Status", "🟢 Running")
    
    # Show ticker index
    if app.buffer.articles_by_ticker:
        with st.expander("📋 Tickers in Buffer"):
            for ticker, articles_deque in sorted(app.buffer.articles_by_ticker.items()):
                st.caption(f"{ticker}: {len(articles_deque)} articles")
    
    st.divider()
    
    # Question input
    question = st.text_input(
        "🤔 Ask a question about a stock:",
        placeholder="e.g., Why did TSLA drop?",
        help="Mention a stock ticker (TSLA, AAPL, GOOGL, etc.) in your question"
    )
    
    if question:
        with st.spinner("⏳ Analyzing..."):
            try:
                # Detect ticker
                ticker = resolve_ticker_from_text(question)
                if not ticker:
                    st.warning("⚠️ Could not detect a stock ticker. Try mentioning a symbol like TSLA, AAPL, etc.")
                else:
                    st.info(f"🔍 Detected ticker: **{ticker.upper()}**")
                    
                    # Get articles from Kafka buffer
                    articles = app.buffer.get_articles_by_ticker(ticker, limit=5)
                    
                    if not articles:
                        st.warning(f"📭 No recent articles found for {ticker.upper()}")
                        st.info("The Kafka buffer is building up. Please check if ingestion scripts are running.")
                    else:
                        st.success(f"📰 Found {len(articles)} relevant articles")
                        
                        # Show articles
                        with st.expander("📰 Source Articles"):
                            for i, article in enumerate(articles, 1):
                                st.markdown(f"**{i}. {article.get('headline', 'No title')}**")
                                if article.get('description'):
                                    st.caption(article['description'][:200] + "...")
                                if article.get('source'):
                                    st.caption(f"Source: {article['source']} | {article.get('published_at', '')}")
                                st.divider()
                        
                        # Run query
                        st.subheader("📝 AI Analysis")
                        answer = app.query(question)
                        st.write(answer)
                
            except Exception as e:
                st.error(f"❌ Error: {e}")
                st.info("Troubleshooting:")
                st.code("""
# Check Ollama
ollama serve

# Check Kafka
lsof -i :9092

# Check ingestion
ps aux | grep ingest
                """, language="bash")


if __name__ == "__main__":
    main()

