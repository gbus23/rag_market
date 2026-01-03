
# ☁️ Real-Time Financial RAG (Full Azure Edition)

A robust, cloud-native Real-Time Retrieval-Augmented Generation system. This project ingests financial news streams via **Apache Kafka**, indexes them instantly using **Azure AI Search**, and uses **Azure OpenAI (GPT-4)** to answer user queries with up-to-the-second context.

---

## 📂 Project Structure & Data Flow

Here is how the files interact with each other and the infrastructure:

```text
[DATA SOURCES]                  [MESSAGING]                  [ETL PROCESS]
      |                              |                             |
      | (1) JSON Data                | (2) Consumes Data           | (3) Vectors & Text
      v                              v                             v
+------------------+       +------------------+       +----------------------+
| ingestion/       | ----> |   APACHE KAFKA   | ----> |  indexer_service.py  |
| ingest_*.py      |       | (Topic: news_raw)|       |  (Background Worker) |
+------------------+       +------------------+       +----------------------+
                                                                 |
                                                                 | (4) Indexing
                                                                 v
+------------------+                                  +----------------------+
|  rag_app_ui.py   | <---- (Imports Logic) ---------- |     AZURE CLOUD      |
|  (Streamlit UI)  |                                  | - Azure AI Search    |
+------------------+                                  | - Azure OpenAI       |
        |                                             +----------------------+
        | (6) User Question                                      ^
        v                                                        |
+------------------+                                             |
| rag_app_azure.py | --------------------------------------------+
| (RAG Logic)      |            (5) Semantic Search & LLM Generation
+------------------+

```

### 🔍 Key Components

1. **`ingestion/ingest_*.py`**: Modular scripts acting as **Producers**. They fetch data from APIs (Finnhub) or generate mock data, normalize it to JSON, and push it to the Kafka topic `news_raw`.
2. **`indexer_service.py`**: The **Consumer/Writer**. This background service listens to Kafka, converts article text into Embeddings using Azure OpenAI, secures IDs (Base64 encoding), and pushes the enriched documents to Azure AI Search.
3. **`rag_app_ui.py`**: The **Frontend**. A Streamlit interface that allows users to view the system status and ask questions.
4. **`rag_app_azure.py`**: The **Reader Logic**. It handles the connection to Azure, performs Hybrid Search (Vector + Keyword), constructs the context, and calls the LLM (GPT-4) to generate the final answer.

---

## ⚙️ Prerequisites

1. **Python 3.10+**
2. **Apache Kafka** (Running locally via Homebrew or Docker).
3. **Azure Account** with:
* **Azure AI Search** resource.
* **Azure OpenAI** resource (with deployments for `text-embedding-3` and `gpt-4` / `model-router`).



### Installation

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install specific dependencies
pip install streamlit confluent-kafka openai azure-search-documents azure-core python-dotenv requests finnhub-python

```

---

## 🔑 Configuration (.env)

Create a `.env` file at the root of the project. **Do not commit this file.**

```ini
# --- KAFKA INFRASTRUCTURE ---
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
NEWS_TOPIC=news_raw

# --- DATA SOURCES ---
FINNHUB_API_KEY=your_finnhub_api_key

# --- AZURE AI SEARCH (Vector DB) ---
# The URL of your search service (e.g., [https://my-service.search.windows.net](https://my-service.search.windows.net))
AZURE_SEARCH_ENDPOINT=[https://your-service-name.search.windows.net](https://your-service-name.search.windows.net)
# The Admin Key (found in Azure Portal > Keys)
AZURE_SEARCH_KEY=your_azure_search_admin_key
INDEX_NAME=rag-index

# --- AZURE OPENAI (Embeddings & LLM) ---
# The URL of your cognitive service
AZURE_OPENAI_ENDPOINT=[https://your-resource-name.openai.azure.com/](https://your-resource-name.openai.azure.com/)
OPENAI_KEY=your_azure_openai_key

```

---

## 🚀 How to Run (4 Terminal Setup)

To see the full pipeline in action, you need to open 4 separate terminals:

### Terminal 1: Infrastructure (Kafka)

Start Zookeeper and Kafka services.

```bash
# MacOS (Homebrew)
brew services start zookeeper
brew services start kafka

```

### Terminal 2: Ingestion (Producers)

Start fetching news. Use the "fake" ingestor for immediate demo data.

```bash
source .venv/bin/activate
# Real data (slow flow)
python3 -m ingestion.ingest_news_finhub &
# Mock data (fast flow for demo)
python3 -m ingestion.ingest_fake

```

### Terminal 3: Indexing Service (The Worker)

This script bridges Kafka and Azure. It must run in the background to fill the database.

```bash
source .venv/bin/activate
python3 indexer_service.py

```

*You should see logs like: `✅ Indexé: TSLA jumps 5%...*`

### Terminal 4: User Interface (The App)

Launch the web interface.

```bash
source .venv/bin/activate
streamlit run rag_app_ui.py

```

---

## 🎮 Features & Usage

* **Full Cloud Integration:** Data persists in Azure AI Search, no local RAM storage.
* **Hybrid Search:** Combines keyword search (BM25) with Vector Search (Cosine Similarity) for maximum relevance.
* **Real-Time:** News is searchable milliseconds after ingestion.
* **Scalable:** The decoupled Kafka architecture handles high throughput.

**Example Query:**

> *"Why is NVDA stock moving today?"*
> **Result:** The system retrieves the latest articles from Azure, cites the source (e.g., "FakeNewsGenerator" or "Finnhub"), and generates a summarized answer using GPT-4.

---

## 🛠️ Troubleshooting

* **`DummyBuffer object has no attribute...`**: You are likely using the wrong import in `rag_app_ui.py`. Ensure it imports `rag_app_azure`, which handles the cloud connection correctly.
* **`Invalid document key`**: Azure IDs cannot contain special characters. Ensure `indexer_service.py` uses Base64 encoding for IDs.
* **Kafka Connection Refused**: Check if `localhost:9092` is reachable. Restart Kafka services in Terminal 1.

```

```