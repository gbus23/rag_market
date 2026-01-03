# indexer_service.py
from dotenv import load_dotenv
load_dotenv()
import json
import os
from confluent_kafka import Consumer
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import base64

# --- CONFIGURATION (Reprise de votre Notebook & .env) ---
# Assurez-vous que ces variables sont dans votre .env ou définies ici
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = "news_raw"

# Azure Config (A remplir avec vos infos du notebook)
AZURE_SEARCH_ENDPOINT = "https://vectordbfundidcardfree.search.windows.net"
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY") # Ou votre clé en dur pour tester
INDEX_NAME = "rag-index" # Le nom de l'index créé dans le notebook

AZURE_OPENAI_ENDPOINT = "https://alexa-me2hz4ri-swedencentral.cognitiveservices.azure.com/"
AZURE_OPENAI_KEY = os.getenv("OPENAI_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"

# --- CLIENTS ---
search_client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(AZURE_SEARCH_KEY)
)

openai_client = AzureOpenAI(
    api_key=AZURE_OPENAI_KEY,
    api_version="2024-12-01-preview",
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)

consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'azure-indexer-group',
    'auto.offset.reset': 'earliest' # Pour tout indexer depuis le début
})
consumer.subscribe([TOPIC])

print(f"🚀 Indexeur Démarré : Kafka ({TOPIC}) -> Azure Index ({INDEX_NAME})")

def generate_embedding(text):
    # Même logique que le notebook cell 62
    response = openai_client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
    return response.data[0].embedding

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None: continue
        if msg.error():
            print(f"Erreur Kafka: {msg.error()}")
            continue

        # 1. Lecture Kafka
        article = json.loads(msg.value().decode('utf-8'))
        
        # 2. Préparation du texte (Titre + Description)
        text_to_embed = f"{article.get('headline', '')} {article.get('description', '')}"
        
        # 3. Embedding (Via Azure OpenAI)
        try:
            vector = generate_embedding(text_to_embed)
            
            raw_id = str(article.get('id', hash(text_to_embed)))
                        # On encode l'ID en Base64 pour qu'il soit "propre" pour Azure
            safe_id = base64.urlsafe_b64encode(raw_id.encode("utf-8")).decode("utf-8")

            doc = {
                "id": safe_id, 
                "title": article.get('headline'),
                "content": article.get('description'), 
                "contentVector": vector,
                "published_at": article.get('published_at', ''),
                "source": article.get('source', '')
            }
            # 5. Upload vers Azure
            search_client.upload_documents(documents=[doc])
            print(f"✅ Indexé: {doc['title'][:30]}...")
            
        except Exception as e:
            print(f"❌ Erreur Indexation: {e}")

except KeyboardInterrupt:
    consumer.close()
    print("Arrêt.")