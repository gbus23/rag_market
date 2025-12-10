# LLM/test_rag_news.py

import time
from LLM.rag_news import start_news_buffer_in_background, retrieve_news_for_query, get_buffer_stats

if __name__ == "__main__":
    start_news_buffer_in_background()

    print("Waiting a bit to fill the buffer...")
    time.sleep(15)  

    print("Buffer stats:", get_buffer_stats())

    query = "news about Nvidia"
    ticker = "NVDA"

    docs = retrieve_news_for_query(query=query, ticker=ticker, max_results=5)
    print(f"\nFound {len(docs)} matching news for ticker {ticker}:\n")
    for d in docs:
        print(f"- [{d['published_at']}] {d['source']} | {d['headline']} | {d['tickers']}")
