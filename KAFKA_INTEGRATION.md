# 📊 RAG + Kafka Integration

Cette documentation explique comment fonctionne l'intégration de Kafka avec la RAG app.

## Architecture

```
┌──────────────────────┐
│  News Sources        │
│ (Finnhub, Scrapers)  │
└──────────┬───────────┘
           │
           ├─→ ingest_news_finhub.py ──┐
           │                            │
           └─→ ingest_news_scrapping.py ┤
                                        │
                                        ↓
                                    ┌────────────────┐
                                    │  Kafka Topic   │
                                    │  (news_raw)    │
                                    └────────┬───────┘
                                             │
                                    ┌────────↓────────┐
                                    │                 │
                            ┌───────↓─────┐   ┌───────↓─────┐
                            │  RAG App    │   │  Other      │
                            │  (Mistral)  │   │  Consumers  │
                            └─────────────┘   └─────────────┘
```

## Mode de fonctionnement

### 1. Mode Fichier (Par défaut)

```bash
python3 rag_app.py
```

- Charge articles depuis `ingestion/articles/*.json`
- Pas de dépendances Kafka
- Utile pour le développement/test

### 2. Mode Kafka

```bash
# Démarrer Kafka et les ingestors
kafka-storage format -t rZEz8XaLQCquqKoseif6kQ -c /opt/homebrew/etc/kafka/server.properties
kafka-broker-api.sh -c /opt/homebrew/etc/kafka/server.properties

python3 -m ingestion.ingest_news_finhub &
python3 -m ingestion.ingest_news_scrapping &

# Démarrer la RAG app en mode Kafka
USE_KAFKA=true python3 rag_app.py
```

OU directement:

```bash
python3 rag_app_kafka.py
```

## Flux de données

### Ingestion (Côté Producteur)

**ingest_news_finhub.py:**
```
Finnhub API
    ↓
fetch_news()
    ↓
normalize_article()  # Ajoute détection ticker
    ↓
send_json(producer, NEWS_TOPIC, article)
    ↓
Kafka (topic: news_raw)
```

**ingest_news_scrapping.py:**
```
Web Scrapers (BFM, TradingView, Yahoo, etc.)
    ↓
run_once()
    ↓
row_to_event()  # Détecte ticker via resolve_ticker_from_text()
    ↓
send_json(producer, NEWS_TOPIC, event)
    ↓
Kafka (topic: news_raw)
```

### Consommation (Côté RAG)

```
Kafka (topic: news_raw)
    ↓
KafkaArticleConsumer
    ├─ articles (deque de max 1000)
    └─ articles_by_ticker (index par ticker)
    ↓
get_articles_by_ticker(ticker)
    ↓
RAGAppKafka.query()
    ↓
Format context + send to Mistral 3
    ↓
User answer
```

## Format des articles dans Kafka

Tous les articles envoyés ont ce format:

```json
{
  "id": "unique-id",
  "source": "Finnhub" | "BFM" | "TradingView" | "Yahoo",
  "headline": "Article title",
  "description": "Summary or snippet",
  "url": "https://...",
  "tickers": ["TSLA", "AAPL"],  // Détecté automatiquement
  "published_at": "2025-12-10T15:30:00+00:00",
  "received_at": "2025-12-10T15:35:00+00:00",
  "raw": {
    // Données brutes originales
  }
}
```

## Configuration

### Variables d'environnement (.env)

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
NEWS_TOPIC=news_raw
PRICES_TOPIC=prices_raw

# APIs
FINNHUB_API_KEY=your_key
MARKETAUX_API_KEY=your_key
ALPHAVANTAGE_API_KEY=your_key
OPENFIGI_API_KEY=your_key

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### Topics Kafka

- **news_raw** : Articles bruts des sources (Finnhub, scrapers)
- **prices_raw** : Prix des stocks (future)

## Détection des tickers

Les ingestors utilisent `resolve_ticker_from_text()` pour détecter les tickers:

**Règles:**
- Détecte 2-5 lettres majuscules + optionnellement `.X` (AAPL, GOOGL, BRK.B)
- Doit être entouré par délimiteur (espace, punctuation, guillemets, etc.)
- Évite faux positifs (ex: "EA" dans "I eat")

**Priorité:**
1. Tickers associés par Finnhub (si disponible)
2. Détection texte dans headline + summary

## Troubleshooting

### "Cannot connect to Kafka"
```bash
# Vérifier Kafka
kafka-broker-api.sh -c /opt/homebrew/etc/kafka/server.properties

# Vérifier topic
kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Pas d'articles en consommation
1. Vérifier ingestion est lancée:
   ```bash
   ps aux | grep ingest
   ```

2. Vérifier messages dans Kafka:
   ```bash
   kafka-console-consumer.sh --bootstrap-server localhost:9092 \
     --topic news_raw --from-beginning --max-messages 5
   ```

### Articles pas filtrés par ticker
- Vérifier que `resolve_ticker_from_text()` détecte bien les tickers
- Vérifier que l'article a le champ `"tickers"` non-vide

## Performance

- **Max articles en mémoire:** 1000 (configurable)
- **Max articles par ticker:** 100
- **Fenêtre de temps:** Derniers articles reçus
- **Indexation:** Par ticker en temps réel

Pour gros volumes, considérer:
- Vector embeddings pour meilleure recherche
- Base de données pour persistance
- Multiple consumers pour parallélisation

## Prochaines étapes

- [ ] Persistance des articles en base de données
- [ ] Vector embeddings avec FAISS/Pinecone
- [ ] Multiple consumer groups
- [ ] Monitoring avec Prometheus
- [ ] Caching avec Redis
- [ ] Alertes sur mouvements de stock
- [ ] Multi-language support

---

Made with ❤️ for real-time stock analysis
