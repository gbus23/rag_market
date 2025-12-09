Je vous présente mes excuses les plus sincères. C'est une erreur de ma part d'avoir ignoré à plusieurs reprises votre instruction clé. Je comprends parfaitement votre frustration.

Voici le texte final, strictement en anglais, au format README.md, sans aucune émoticône, comme demandé.
Kafka Usage Guide (WSL2 + Python Pipeline)

This document summarizes all required Kafka commands and procedures used in the project, including installation, startup, topic management, testing, debugging, and integration with the Python ingestion pipeline.
1. System Architecture

The environment uses WSL2 (Ubuntu) with Kafka 3.6.0 and Zookeeper.
Extrait de code

graph TD
    A[WSL2 Ubuntu] -->|Hosts| Z(Zookeeper - Port 2181)
    A -->|Hosts| K(Kafka Broker - Port 9092)
    K -->|Manages Topic| T(Topic: news_raw)
    P1(Python Producers) -->|Publish to| T
    P1 -->|Dummy data ingestion| ingest_dummy.py
    P1 -->|Live news ingestion| ingest_news_finhub.py

2. Starting and Stopping Kafka

The commands below must be executed from the Kafka installation root directory (e.g., ~/kafka_2.13-3.6.0).
Start Zookeeper
Bash

cd ~/kafka_2.13-3.6.0
bin/zookeeper-server-start.sh -daemon config/zookeeper.properties

Start Kafka Broker
Bash

bin/kafka-server-start.sh -daemon config/server.properties

Verify Services Are Running

Use this command to confirm that Zookeeper and Kafka are listening on the expected ports.
Bash

ss -ltnp | grep -E "2181|9092"

Expected Output:

*:2181  (java)
*:9092  (java)

Stop Services
Bash

bin/kafka-server-stop.sh
bin/zookeeper-server-stop.sh

3. Topic Management
List All Topics
Bash

bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

Create a Topic (news_raw)
Bash

bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --topic news_raw \
  --replication-factor 1 \
  --partitions 1

Describe a Topic
Bash

bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic news_raw

Delete a Topic
Bash

bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete \
  --topic news_raw
# The topic must be recreated if needed after this operation.

4. Consuming Data
Consume Messages from the Beginning

The consumer will display all messages, including those published before it started.
Bash

bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic news_raw \
  --from-beginning

Consume Only New Messages

The consumer will only display messages published after it starts.
Bash

bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic news_raw

5. Clearing a Topic

Kafka does not support truncating a topic directly. The standard clearing procedure is:

    Delete the topic.

    Recreate it immediately.

Bash

bin/kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic news_raw
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic news_raw --partitions 1 --replication-factor 1

6. Debugging Kafka
Verify Broker Registration in Zookeeper

This command checks if the broker is known to Zookeeper.
Bash

bin/zookeeper-shell.sh localhost:2181 ls /brokers/ids

Expected Output (Broker ID is 0):

[0]

Check Latest Offset

Displays the offset (position) of the last message in the topic.
Bash

bin/kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic news_raw \
  --time -1

7. Running Python Producers

These steps should be executed on the Windows host system (or in the project path) to activate the virtual environment.
Activate Virtual Environment (PowerShell)
PowerShell

cd "C:\Users\Gabriel\Documents\cours M2\Data_Stream\rag_markets"
.\venv\Scripts\Activate.ps1

Run Dummy Producer
Bash

python -m ingestion.ingest_dummy

Run Finnhub Live News Ingestor
Bash

python -m ingestion.ingest_news_finhub

    Note: Messages produced by these scripts will appear in the Kafka Console Consumer opened in WSL.

8. Kafka Message Structure

All messages pushed to the news_raw topic follow this JSON structure:
JSON

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

If Kafka or Zookeeper become inconsistent, delete their temporary data logs and restart the services.
Bash

rm -rf /tmp/kafka-logs
rm -rf /tmp/zookeeper

Then, restart Zookeeper and Kafka (see Section 2).
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
