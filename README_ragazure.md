# ☁️ Real-Time Financial RAG (Full Azure Edition)

**Architecture Full Cloud :**
* **Transport :** Apache Kafka
* **Vector Database :** Azure AI Search (Indexation & Recherche Hybride)
* **Embeddings :** Azure OpenAI (`text-embedding-3-small`)
* **LLM Generation :** Azure OpenAI (GPT-4 / `model-router`)

## ⚙️ Prérequis

1.  **Python 3.10+**
2.  **Apache Kafka** (Local ou Docker)
3.  **Compte Azure** avec les ressources déployées :
    * **Azure AI Search**
    * **Azure OpenAI** (avec déploiements pour `text-embedding-3` et `gpt-4` ou équivalent).

### Installation

```bash
# Création de l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installation des dépendances
pip install streamlit confluent-kafka openai azure-search-documents azure-core python-dotenv requests finnhub-python
```

---

## 🔑 Configuration (.env)

Créez un fichier `.env` à la racine contenant vos clés Azure (ne pas commiter ce fichier !) :

```ini
# --- KAFKA ---
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
NEWS_TOPIC=news_raw

# --- SOURCES ---
FINNHUB_API_KEY=votre_cle_finnhub

# --- AZURE AI SEARCH (Vector DB) ---
AZURE_SEARCH_ENDPOINT=[https://vectordbfundidcardfree.search.windows.net](https://vectordbfundidcardfree.search.windows.net)
AZURE_SEARCH_KEY=votre_admin_key_search
INDEX_NAME=rag-index

# --- AZURE OPENAI (LLM & Embeddings) ---
AZURE_OPENAI_ENDPOINT=[https://alexa-me2hz4ri-swedencentral.cognitiveservices.azure.com/](https://alexa-me2hz4ri-swedencentral.cognitiveservices.azure.com/)
OPENAI_KEY=votre_cle_openai
```

---

## 🚀 Lancement (4 Terminaux)

### 1. Infrastructure (Kafka)
```bash
brew services start zookeeper
brew services start kafka
# Ou via docker-compose si applicable
```

### 2. Ingestion des Données
Récupère les news et les envoie dans Kafka.
```bash
source .venv/bin/activate
# Lancer les producteurs
python3 -m ingestion.ingest_news_finhub &
python3 -m ingestion.ingest_fake  # (Optionnel: pour simuler du flux immédiat)
```

### 3. Service d'Indexation (ETL)
Consomme Kafka et remplit Azure AI Search en temps réel.
```bash
source .venv/bin/activate
python3 indexer_service.py
```

### 4. Application RAG (Frontend)
L'interface utilisateur Streamlit connectée à Azure.
```bash
source .venv/bin/activate
streamlit run rag_app_ui.py
```

---

## 🎮 Fonctionnalités

* ✅ **Full Azure Integration :** Utilise la puissance du cloud pour le stockage et la génération.
* ✅ **Hybrid Search :** Combine recherche par mots-clés et recherche vectorielle pour plus de pertinence.
* ✅ **Real-Time :** Les news ingérées sont disponibles dans la recherche quelques secondes après leur publication.
* ✅ **Scalable :** Architecture découplée via Kafka.

---

## 🛠️ Troubleshooting

**Erreur : `DummyBuffer object has no attribute...`**
* L'interface UI utilise un buffer fictif car les données sont dans le Cloud. Assurez-vous d'utiliser `rag_app_azure.py` qui gère correctement ce comportement simulé.