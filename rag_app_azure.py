# rag_app_azure.py
import os
from dotenv import load_dotenv
load_dotenv()
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
import requests
from openai import AzureOpenAI

# --- CONFIG ---
# (Reprendre les mêmes configs Azure que ci-dessus)
AZURE_SEARCH_ENDPOINT = "https://vectordbfundidcardfree.search.windows.net"
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = "rag-index"

AZURE_OPENAI_ENDPOINT = "https://alexa-me2hz4ri-swedencentral.cognitiveservices.azure.com/"
AZURE_OPENAI_KEY = os.getenv("OPENAI_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"

# Pour le LLM (Génération) - On garde Ollama local ou on passe sur Azure GPT
# Ici je garde Ollama pour minimiser les changements, mais on peut switcher.
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "mistral" 

MODELS = {
    "model-router": {
        "api_version": "2024-12-01-preview",
        "endpoint": AZURE_OPENAI_ENDPOINT,
        "deployment": "model-router"  # Remplacez par le nom de votre déploiement
    }
}

class DummyBuffer:
    """Sert à tromper l'UI qui cherche app.buffer.articles"""
    def __init__(self):
        self.articles = [] 
        self.articles_by_ticker = {}

    def get_articles_by_ticker(self, ticker, limit=5):
        # L'UI a besoin de recevoir une liste non-vide pour continuer vers l'analyse.
        # On renvoie un article "placeholder" pour valider cette étape.
        return [{
            "headline": "Recherche Cloud Azure Active",
            "description": "Les articles sont stockés et indexés dans Azure AI Search. La recherche vectorielle précise se fera à l'étape suivante.",
            "source": "System",
            "published_at": "Temps Réel"
        }]

class RAGAppAzure:
    def __init__(self):
        # Clients Azure
        self.search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=INDEX_NAME,
            credential=AzureKeyCredential(AZURE_SEARCH_KEY)
        )
        self.openai_client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-12-01-preview",
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        
        # Hack pour l'UI: on simule un buffer vide
        self.buffer = DummyBuffer() 
        print("☁️ RAG App connectée à Azure AI Search")

    def _generate_embedding(self, text):
        response = self.openai_client.embeddings.create(input=[text], model=EMBEDDING_MODEL)
        return response.data[0].embedding

    def query(self, question: str) -> str:
        print(f"🔍 Question: {question}")
        
        # 1. Vectorisation de la question
        vector = self._generate_embedding(question)
        
        # 2. Recherche Vectorielle (Notebook logic)
        vector_query = VectorizedQuery(vector=vector, k_nearest_neighbors=3, fields="contentVector")
        
        results = self.search_client.search(
            search_text=question,
            vector_queries=[vector_query],
            select=["title", "content", "source", "published_at", "url"],
            top=3
        )
        
        # 3. Construction du contexte
        articles = list(results)
        print(f"📄 Documents trouvés: {len(articles)}")
        
        if not articles:
            return "Désolé, aucune information pertinente trouvée dans la base de connaissances."

        context_str = "\n\n".join([
            f"[{doc.get('published_at', 'N/A')}] Source {doc.get('source', '?')}: {doc['title']}\n"
            f"Contenu: {doc['content']}" 
            for doc in articles
        ])
        print(f"🧾 Contexte:\n{context_str}")
        # 4. Génération (Via Azure OpenAI GPT)
        prompt = f"""Tu es un analyste financier expert. Utilise UNIQUEMENT le contexte ci-dessous pour répondre.
        
        Contexte:
        {context_str}
        
        Question: {question}
        
        Réponse concise:"""
        
        return self._call_ollama(prompt)

    def _call_ollama(self, prompt):
        # Remplace l'appel à Ollama par un appel à Azure OpenAI
        try:
            return self.call_gpt_with_context(
                context="Contexte généré par la recherche vectorielle",
                query=prompt,
                attachment="",
                model_name="model-router"
            )
        except Exception as e:
            return f"Erreur GPT: {e}"

    def call_gpt_with_context(self, context: str, query: str, attachment: str, model_name="model-router") -> str:
        """
        Appelle Azure OpenAI en envoyant un prompt qui inclut :
        - un contexte
        - une requête
        - une pièce attachée (par ex. transcript YouTube)
        """
        config = MODELS.get(model_name)
        if not config:
            raise ValueError(f"Model '{model_name}' not configured")

        client = AzureOpenAI(
            api_version=config["api_version"],
            azure_endpoint=config["endpoint"],
            api_key=AZURE_OPENAI_KEY,
        )

        prompt = f"""
        You are an assistant.

        Context:
        {context}

        User request:
        {query}

        Attached document:
        \"\"\"{attachment}\"\"\"
        """

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=8192,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            model=config["deployment"]
        )

        return response.choices[0].message.content