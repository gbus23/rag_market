o run the ingestion pipeline, start Zookeeper and Kafka in the background (daemon mode), then create the news_raw topic.

Start services
# Start Zookeeper in daemon mode
bin/zookeeper-server-start.sh -daemon config/zookeeper.properties

# Start Kafka in daemon mode
bin/kafka-server-start.sh -daemon config/server.properties


You can verify they’re running with:

jps -l

Create the required topic
bin/kafka-topics.sh --create \
  --topic news_raw \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1

Useful Kafka commands
# List existing topics
bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Describe a topic
bin/kafka-topics.sh --describe --topic news_raw --bootstrap-server localhost:9092

# Test producer
bin/kafka-console-producer.sh --topic news_raw --bootstrap-server localhost:9092

# Test consumer
bin/kafka-console-consumer.sh \
  --topic news_raw \
  --from-beginning \
  --bootstrap-server localhost:9092

Stop Kafka services
bin/kafka-server-stop.sh
bin/zookeeper-server-stop.sh
