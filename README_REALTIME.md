# 📊 Real-Time Stock Analysis RAG App

RAG application that analyzes stock movements using **real-time data from Kafka** and **Mistral 3 LLM**.

## Architecture

```
┌─────────────────────┐
│  API Sources        │
│ (Finnhub, Scrapers) │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
 ┌──▼──┐   ┌────▼────┐
 │ API │   │ Scrapers │
 └──┬──┘   └────┬────┘
    │           │
    └──────┬────┘
           │
      ┌────▼────────────┐
      │  Kafka Broker   │
      │  (news_raw)     │
      └────┬────────────┘
           │
    ┌──────▼──────┐
    │  RAG App    │
    │  Mistral 3  │
    │  (Real-time)│
    └─────────────┘
```

## Quick Start

### Prerequisites

Make sure you have:
1. **Kafka** running
2. **Ollama** with Mistral 3 model
3. **Python dependencies** installed

```bash
pip install -r requirements_rag.txt
```

### Launch (4 terminals)

**Terminal 1: Start Kafka**
```bash
kafka-server-start /opt/homebrew/etc/kafka/server.properties
```

**Terminal 2: Start Ollama**
```bash
ollama serve
```

In another terminal, pull the model if not already done:
```bash
ollama pull mistral:latest
```

**Terminal 3: Start News Ingestion (pulls data from APIs)**
```bash
cd /Users/theocadene/Documents/M2\ DS/DataStream
source .venv/bin/activate
python3 -m ingestion.ingest_news_finhub &
python3 -m ingestion.ingest_news_scrapping &
```

**Terminal 4: Start RAG App**
```bash
cd /Users/theocadene/Documents/M2\ DS/DataStream/rag_market
python3 rag_app.py

ou 

streamlit run rag_app_ui.py
```

Then ask questions:
```
🤔 Your question: Why did TSLA drop?
🤔 Your question: What happened with AAPL?
```

## How It Works

1. **News Ingestion**: APIs pull articles and publish to Kafka
2. **Ticker Detection**: Each article is analyzed for stock tickers
3. **Real-time Buffer**: RAG app maintains a Kafka consumer buffer
4. **Query Processing**:
   - Extract ticker from user question
   - Fetch recent articles from Kafka buffer
   - Send to Mistral 3 LLM
   - Return analysis

## Configuration

Edit `.env`:
```bash
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
FINNHUB_API_KEY=your_key_here
```

## Example Usage

```
🤔 Your question: Why did TSLA drop?

🔍 Detected ticker: TSLA
📰 Found 3 relevant articles from Kafka

⏳ Analyzing...

📝 Answer:
Tesla stock fell following disappointing Q4 earnings guidance. 
The company cited supply chain challenges and lower than expected demand. 
Investors are concerned about margin compression in 2025.
```

## Features

✅ **Real-time data**: Pulls directly from APIs (Finnhub, web scrapers)
✅ **Kafka streaming**: Scalable event pipeline
✅ **Ticker detection**: Automatically identifies stock symbols
✅ **Multi-source**: Finnhub + web scraping
✅ **Smart filtering**: Index articles by ticker for fast retrieval
✅ **LLM analysis**: Mistral 3 provides contextual answers

## Ticker Detection

- **Length**: 2-5 letters + optional `.X` (AAPL, GOOGL, BRK.B)
- **Delimiters**: Must be surrounded by space, punctuation, or quotes
- **Examples**:
  - ✅ " TSLA " → detected
  - ✅ "(AAPL)" → detected
  - ❌ "I eat" → EA not detected

## Troubleshooting

### "Cannot connect to Kafka"
```bash
lsof -i :9092
```

### "Cannot connect to Ollama"
```bash
ollama serve
ollama pull mistral:latest
```

### No articles appearing
Check Kafka has messages:
```bash
kafka-console-consumer.sh --bootstrap-server 127.0.0.1:9092 \
  --topic news_raw --from-beginning --max-messages 5
```

---


HOW to lauch the app :

# Terminal 1: Kafka
kafka-server-start /opt/homebrew/etc/kafka/server.properties

# Terminal 2: Ingestion
python3 -m rag_market.ingestion.ingest_news_finhub &
python3 -m rag_market.ingestion.ingest_news_scrapping &

# Terminal 3: RAG App
USE_KAFKA=true python3 rag_app.py
    ou 
streamlit run rag_app_ui.py