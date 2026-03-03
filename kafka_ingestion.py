import json
import logging
from typing import Generator, Dict, Any
from kafka import KafkaConsumer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataStreamConsumer:
    """
    Kafka Consumer to ingest real-time streams of system logs, 
    transaction data, and IoT sensor feeds.
    """
    def __init__(self, topic: str = "system_metrics", bootstrap_servers: str = "localhost:9092"):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                auto_offset_reset='latest'
            )
            logger.info(f"Connected to Kafka topic: {self.topic}")
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka: {e}. Running in Mock mode.")

    def consume_events(self) -> Generator[Dict[str, Any], None, None]:
        """Yields events from the Kafka stream or mock data if Kafka is unavailable."""
        if not self.consumer:
            logger.info("Starting mock data stream generator...")
            import time
            import random
            
            # Simulate normal behavior and occasional anomalies
            while True:
                time.sleep(1) # Simulate 1 event per second
                is_anomaly = random.random() < 0.05 # 5% chance of anomaly
                
                event = {
                    "timestamp": time.time(),
                    "cpu_usage": random.uniform(80.0, 100.0) if is_anomaly else random.uniform(10.0, 60.0),
                    "memory_usage": random.uniform(85.0, 99.0) if is_anomaly else random.uniform(20.0, 70.0),
                    "latency": random.uniform(200.0, 1000.0) if is_anomaly else random.uniform(10.0, 100.0),
                    "error_rate": random.uniform(0.1, 0.5) if is_anomaly else random.uniform(0.001, 0.01)
                }
                yield event
                
        else:
            for message in self.consumer:
                if message and message.value:
                    yield message.value

if __name__ == "__main__":
    consumer = DataStreamConsumer()
    for i, event in enumerate(consumer.consume_events()):
        print(event)
        if i >= 5: # Just print first 5 for test
            break
