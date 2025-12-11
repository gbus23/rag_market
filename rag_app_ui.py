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


@st.cache_data(ttl=60, show_spinner=False)
def get_sentiment_cached(_app: RAGApp, ticker: str):
    # Safety: sentiment is only computed for tickers explicitly in the portfolio
    if ticker not in st.session_state.get("portfolio", set()):
        return None
    return _app.get_sentiment(ticker)


def main():
    st.set_page_config(page_title="📊 Stock Analysis RAG", layout="wide")
    
    st.title("📊 Stock Analysis RAG")
    st.markdown("Ask questions about stock movements using real-time Kafka data and Mistral 3 AI")

    # Session state for portfolio management
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = set()
    if "last_seen_counts" not in st.session_state:
        st.session_state.last_seen_counts = {}

    # Auto-refresh the page every 30 seconds to pull latest Kafka news
    autorefresh_fn = getattr(st, "autorefresh", None)
    if autorefresh_fn:
        autorefresh_fn(interval=5_000, key="news_auto_refresh")
    else:
        # Fallback for older Streamlit versions: simple JS reload
        st.markdown(
            "<script>setTimeout(() => window.location.reload(), 5000);</script>",
            unsafe_allow_html=True,
        )
    st.caption("Auto-refreshing every 5s for newest ticker articles.")
    
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

    st.divider()

    # --- Portfolio & Alerts ---
    st.subheader("📂 Portfolio watchlist & alerts")
    col_add, col_refresh = st.columns([3, 1])
    with col_add:
        new_ticker_input = st.text_input(
            "Add ticker to portfolio",
            placeholder="e.g., NVDA or TSLA",
            help="Type a ticker symbol; basic validation will uppercase it",
        )
        if st.button("Add", type="primary"):
            if new_ticker_input:
                detected = resolve_ticker_from_text(new_ticker_input) or new_ticker_input.strip()
                ticker = detected.upper()
                st.session_state.portfolio.add(ticker)
                st.toast(f"Added {ticker} to portfolio")
    with col_refresh:
        if st.button("Refresh news"):
            st.session_state._portfolio_refresh = time.time()
            # st.experimental_rerun was deprecated; st.rerun is available in recent Streamlit
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()

    if not st.session_state.portfolio:
        st.info("Add tickers to monitor their latest news and alerts here.")
        return

    # Display current portfolio with remove buttons
    st.markdown("**Current portfolio:**")
    for ticker in sorted(st.session_state.portfolio):
        col_t, col_btn = st.columns([5, 1])
        with col_t:
            st.caption(f"• {ticker}")
        with col_btn:
            if st.button(f"Remove {ticker}", key=f"rm_{ticker}"):
                st.session_state.portfolio.discard(ticker)
                st.session_state.last_seen_counts.pop(ticker, None)
                try:
                    st.rerun()
                except AttributeError:
                    st.experimental_rerun()

    st.divider()

    # Latest news per ticker with simple alerting
    for ticker in sorted(st.session_state.portfolio):
        articles = app.buffer.get_articles_by_ticker(ticker, limit=5)
        prev_count = st.session_state.last_seen_counts.get(ticker, 0)
        new_count = len(articles)
        if new_count > prev_count and prev_count != 0:
            st.toast(f"🔔 New articles for {ticker}: {new_count - prev_count}")
        st.session_state.last_seen_counts[ticker] = new_count

        # Sentiment badge/metric
        sentiment = get_sentiment_cached(app, ticker)
        if sentiment:
            label = sentiment.get("sentiment", "Unknown")
            score = sentiment.get("score", 0)
            st.metric(f"{ticker} sentiment", label, delta=round(score, 2))
            if sentiment.get("reasoning"):
                st.caption(sentiment["reasoning"])
        else:
            st.metric(f"{ticker} sentiment", "No data")

        with st.expander(f"📰 {ticker}: {new_count} recent article(s)", expanded=False):
            if not articles:
                st.caption("No articles yet for this ticker.")
            for i, article in enumerate(articles, 1):
                st.markdown(f"**{i}. {article.get('headline', 'No title')}**")
                if article.get('description'):
                    st.caption(article['description'][:200] + "...")
                meta_bits = []
                if article.get('source'):
                    meta_bits.append(article['source'])
                if article.get('published_at'):
                    meta_bits.append(str(article['published_at']))
                if meta_bits:
                    st.caption(" | ".join(meta_bits))
                st.divider()


if __name__ == "__main__":
    main()

