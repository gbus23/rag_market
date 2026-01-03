# ☁️ Real-Time Financial RAG (Full Azure Edition)

A robust, cloud-native **Real-Time Retrieval-Augmented Generation (RAG)** system.  
This project ingests financial news streams via **Kafka**, indexes them instantly using **Azure AI Search**, and uses **Azure OpenAI (GPT-4)** to answer user queries with up-to-the-second context.

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
| (RAG Logic)      |     (5) Semantic Search & LLM Generation
+------------------+

🔍 Key Components

ingestion/ingest_*.py
Scripts that fetch data (API or Mock) and push it to Kafka.

indexer_service.py
The Writer. Reads Kafka, converts text to embeddings (Azure OpenAI), and pushes documents to Azure AI Search.

rag_app_ui.py
The frontend. Displays the Streamlit interface.

rag_app_azure.py
The Reader. Performs hybrid search and generates answers via GPT.

⚙️ Prerequisites

Python 3.10+

Apache Kafka (running locally via Homebrew or Docker)

Azure account with:

Azure AI Search

Azure OpenAI (deployments for text-embedding-3 and gpt-4 / model-router)

📦 Installation
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install \
  streamlit \
  confluent-kafka \
  openai \
  azure-search-documents \
  azure-core \
  python-dotenv \
  requests \
  finnhub-python

🔑 Configuration (.env)

Create a .env file at the root of the project.
Do not commit this file.

# --- KAFKA INFRASTRUCTURE ---
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
NEWS_TOPIC=news_raw

# --- DATA SOURCES ---
FINNHUB_API_KEY=your_finnhub_api_key

# --- AZURE AI SEARCH (Vector DB) ---
AZURE_SEARCH_ENDPOINT=https://your-service-name.search.windows.net
AZURE_SEARCH_KEY=your_azure_search_admin_key
INDEX_NAME=rag-index

# --- AZURE OPENAI (Embeddings & LLM) ---
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
OPENAI_KEY=your_azure_openai_key

🚀 How to Run (4-Terminal Setup)

To see the full pipeline in action, open 4 separate terminals.

Terminal 1 — Infrastructure (Kafka)

Start Zookeeper and Kafka services.

# macOS (Homebrew)
brew services start zookeeper
brew services start kafka

Terminal 2 — Ingestion (Producers)

Start fetching news.

source .venv/bin/activate

# Real data (slow flow)
python3 -m ingestion.ingest_news_finhub &

# Mock data (fast flow for demo)
python3 -m ingestion.ingest_fake

Terminal 3 — Indexing Service (Worker)

Bridges Kafka and Azure AI Search.

source .venv/bin/activate
python3 indexer_service.py


You should see logs like:

✅ Indexé: TSLA jumps 5%...

Terminal 4 — User Interface (App)

Launch the Streamlit web interface.

source .venv/bin/activate
streamlit run rag_app_ui.py

🎮 Features & Usage

Full Cloud Integration
Data persists in Azure AI Search (no local RAM storage).

Hybrid Search
Combines BM25 keyword search with vector similarity for maximum relevance.

Real-Time
News becomes searchable milliseconds after ingestion.

Scalable Architecture
Kafka-based decoupling handles high throughput.

Example Query

"Why is NVDA stock moving today?"

Result:
The system retrieves the latest indexed articles, cites the source (e.g. Finnhub or FakeNewsGenerator), and generates a concise explanation using GPT-4.

🛠️ Troubleshooting

DummyBuffer object has no attribute...
Ensure rag_app_ui.py imports rag_app_azure.py, which handles the Azure connection.

Invalid document key
Azure Search IDs cannot contain special characters.
Use Base64 encoding in indexer_service.py.

Kafka connection refused
Check that localhost:9092 is reachable and restart Kafka services.

✅ Status

✔ Fully functional
✔ Cloud-native
✔ Production-ready RAG architecture


---

Si tu veux, je peux aussi te fournir :
- une **version plus concise** (README “portfolio-ready”)
- un **diagramme Mermaid**
- une **section “Architecture Decisions”**
- ou une **checklist de déploiement Azure**