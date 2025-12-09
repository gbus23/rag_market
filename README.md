# Kafka Quickstart for Local Development (WSL + Python)

## 1. Start Zookeeper and Kafka

```bash
cd ~/kafka_2.13-3.6.0

bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
bin/kafka-server-start.sh -daemon config/server.properties
```

Check that ports are open:

```bash
ss -ltnp | grep -E "2181|9092"
```

## 2. Kafka Topics Management

### List topics
```bash
bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Create a topic
```bash
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create   --topic news_raw --partitions 1 --replication-factor 1
```

### Describe a topic
```bash
bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic news_raw
```

### Delete a topic
```bash
bin/kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic news_raw
```

## 3. Producing and Consuming Messages

### Console consumer
```bash
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092   --topic news_raw --from-beginning
```

## 4. Full Kafka Reset (useful when cluster is stuck)

```bash
bin/kafka-server-stop.sh
bin/zookeeper-server-stop.sh
rm -rf /tmp/kafka-logs /tmp/zookeeper
bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
bin/kafka-server-start.sh -daemon config/server.properties
```

## 5. Python Ingestion Script Usage

From your project directory:

```bash
cd rag_markets
source venv/bin/activate
python -m ingestion.ingest_dummy
python -m ingestion.ingest_news_finhub
```

## 6. Useful Commands Summary

```bash
# list topics
bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

# create topic
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic <name> --partitions 1 --replication-factor 1

# consume messages
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic <name> --from-beginning

# stop services
bin/kafka-server-stop.sh
bin/zookeeper-server-stop.sh
```
