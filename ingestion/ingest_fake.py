import time
import json
import random
from datetime import datetime
from confluent_kafka import Producer
import socket

# Config Kafka (Adapter si besoin)
conf = {'bootstrap.servers': 'localhost:9092', 'client.id': socket.gethostname()}
producer = Producer(conf)
topic = 'news_raw'

tickers = ["TSLA", "AAPL", "NVDA", "MSFT", "GOOGL"]
actions = ["jumps", "crashes", "soars", "plunges", "rallies"]

print("🚀 Démarrage du générateur de fausses news...")

try:
    while True:
        ticker = random.choice(tickers)
        action = random.choice(actions)
        price_move = random.randint(2, 15)
        
        # Création d'une fausse news
        article = {
            "id": str(time.time()),
            "source": "FakeNewsGenerator",
            "headline": f"{ticker} {action} {price_move}% on breaking news",
            "description": f"Analysts are surprised by the sudden movement of {ticker} stock this morning.",
            "url": "http://localhost",
            "tickers": [ticker],
            "published_at": datetime.now().isoformat(),
            "received_at": datetime.now().isoformat()
        }
        
        # Envoi Kafka
        producer.produce(topic, json.dumps(article).encode('utf-8'))
        producer.flush()
        
        print(f"⚡ Envoyé: {article['headline']}")
        
        # On attend 10 secondes avant la prochaine
        time.sleep(10)

except KeyboardInterrupt:
    print("Arrêt.")