Kafka Usage Guide (WSL2 + Python Pipeline)

This document summarizes all required Kafka commands and procedures used in the project, including installation, startup, topic management, testing, debugging, and integration with the Python ingestion pipeline.

1. System Architecture

The environment uses WSL2 (Ubuntu) with Kafka 3.6.0 and Zookeeper.

WSL2 Ubuntu
 ├── Zookeeper (port 2181)
 ├── Kafka Broker (port 9092)
 ├── Topic: news_raw
 └── Python Producers
        ├── ingest_dummy.py
        └── ingest_news_finhub.py

2. Starting and Stopping Kafka
Start Zookeeper
cd ~/kafka_2.13-3.6.0
bin/zookeeper-server-start.sh -daemon config/zookeeper.properties

Start Kafka Broker
bin/kafka-server-start.sh -daemon config/server.properties

Verify Services Are Running
ss -ltnp | grep -E "2181|9092"


Expected output:

*:2181  (java)
*:9092  (java)

Stop Services
bin/kafka-server-stop.sh
bin/zookeeper-server-stop.sh

3. Topic Management
List All Topics
bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

Create a Topic
bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --topic news_raw \
  --replication-factor 1 \
  --partitions 1

Describe a Topic
bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic news_raw

Delete a Topic
bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete \
  --topic news_raw


Recreate it if needed.

4. Consuming Data

Consume messages from the beginning of the topic:

bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic news_raw \
  --from-beginning


Consume only new messages:

bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic news_raw

5. Clearing a Topic

Kafka does not support truncating a topic directly.
The standard procedure is:

Delete the topic

Recreate it

bin/kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic news_raw
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic news_raw --partitions 1 --replication-factor 1

6. Debugging Kafka

Verify that the broker is registered in Zookeeper:

bin/zookeeper-shell.sh localhost:2181 ls /brokers/ids


Expected:

[0]


Check latest offset:

bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic news_raw \
  --time -1

7. Running Python Producers
Activate Virtual Environment
cd "C:\Users\Gabriel\Documents\cours M2\Data_Stream\rag_markets"
.\venv\Scripts\Activate.ps1

Run Dummy Producer
python -m ingestion.ingest_dummy

Run Finnhub Live News Ingestor
python -m ingestion.ingest_news_finhub


Kafka consumer in WSL will show the resulting messages.

8. Kafka Message Structure

All messages pushed to news_raw follow this structure:

{
  "id": "unique-id",
  "source": "Finnhub",
  "headline": "News headline",
  "description": "Summary of the article",
  "url": "https://...",
  "tickers": ["AAPL"],
  "published_at": "2025-12-09T12:10:25Z",
  "received_at": "2025-12-09T12:10:25Z"
}

9. Full Reset (If Kafka Becomes Corrupted)

If Kafka or Zookeeper becomes inconsistent:

rm -rf /tmp/kafka-logs
rm -rf /tmp/zookeeper


Then restart Zookeeper and Kafka.

10. Quick Reference Summary
Action	Command
Start Zookeeper	bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
Start Kafka	bin/kafka-server-start.sh -daemon config/server.properties
List Topics	bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
Create Topic	bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic news_raw --partitions 1 --replication-factor 1
Consume Messages	bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic news_raw --from-beginning
Delete Topic	bin/kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic news_raw
Run Dummy Ingestor	python -m ingestion.ingest_dummy
Run Finnhub Ingestor	python -m ingestion.ingest_news_finhub
