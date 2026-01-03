import os
from dotenv import load_dotenv
load_dotenv()
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters
)

# 1. Configuration
ENDPOINT = "https://vectordbfundidcardfree.search.windows.net"
KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = "rag-index" # Le nom que vous utilisez dans votre app

# Configuration OpenAI pour le vectorizer (optionnel mais recommandé pour l'auto-vectorisation)
OPENAI_ENDPOINT = "https://alexa-me2hz4ri-swedencentral.cognitiveservices.azure.com/"
OPENAI_KEY = os.getenv("OPENAI_KEY")
MODEL_NAME = "text-embedding-3-small"

# 2. Client Admin
credential = AzureKeyCredential(KEY)
client = SearchIndexClient(endpoint=ENDPOINT, credential=credential)

# 3. Définition du NOUVEAU schéma (complet)
fields = [
    # ID unique
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    
    # Champs textuels (Recherchables)
    SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.lucene"),
    SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.lucene"),
    
    # --- LES CHAMPS MANQUANTS QUI CAUSAIENT L'ERREUR ---
    SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="published_at", type=SearchFieldDataType.String, sortable=True),
    SimpleField(name="url", type=SearchFieldDataType.String),
    
    # Liste de strings pour les tickers (Collection)
    SimpleField(name="tickers", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
    
    # Champ Vectoriel
    SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile")
]

# 4. Configuration Vectorielle (Identique à votre notebook)
vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
    profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw", vectorizer_name="myVectorizer")],
    vectorizers=[
        AzureOpenAIVectorizer(
            vectorizer_name="myVectorizer",
            parameters=AzureOpenAIVectorizerParameters(
                resource_url=OPENAI_ENDPOINT,
                deployment_name=MODEL_NAME,
                model_name=MODEL_NAME,
                api_key=OPENAI_KEY
            )
        )
    ]
)

# 5. Suppression et Recréation
try:
    print(f"🗑️ Suppression de l'index '{INDEX_NAME}' existant...")
    client.delete_index(INDEX_NAME)
except:
    pass # L'index n'existait peut-être pas

print(f"✨ Création du nouvel index '{INDEX_NAME}' avec le champ 'source'...")
index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)
client.create_index(index)
print("✅ Index recréé avec succès ! Relancez votre indexeur Kafka maintenant.")