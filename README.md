## Requirements

- **Kafka** installed in WSL2 (for example: `~/kafka_2.13-3.6.0`)
- **Java** installed in WSL2
  ```bash
  sudo apt update && sudo apt install -y default-jdk
  ```
- **Python 3.12+** on Windows with virtual environment

## Kafka Configuration (inside WSL2)

1. Get WSL IP:
   ```bash
   hostname -I | awk '{print $1}'
   ```

2. Edit `config/server.properties` in your Kafka folder:
   ```properties
   listeners=PLAINTEXT://0.0.0.0:9092
   advertised.listeners=PLAINTEXT://<YOUR_WSL_IP>:9092
   listener.security.protocol.map=PLAINTEXT:PLAINTEXT
   inter.broker.listener.name=PLAINTEXT
   zookeeper.connect=localhost:2181
   ```

3. Start ZooKeeper and Kafka:
   ```bash
   cd ~/kafka_2.13-3.6.0
   bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
   bin/kafka-server-start.sh -daemon config/server.properties
   ```

4. Check:
   ```bash
   ss -ltnp | grep -E '2181|9092'
   bin/zookeeper-shell.sh localhost:2181 get /brokers/ids/0
   bin/kafka-topics.sh --bootstrap-server <YOUR_WSL_IP>:9092 --list
   ```

   5. receive: bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic news_raw --from-beginning


