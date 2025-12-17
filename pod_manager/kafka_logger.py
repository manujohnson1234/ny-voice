import json
import queue
import threading
from kafka import KafkaProducer


class KafkaLogProducer:
    def __init__(self, bootstrap_servers: str, client_id: str = "app-monitor", topic: str = "app-logs"):
        self.topic = topic
        self.queue = queue.Queue()
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id=client_id,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        # Start background thread for sending logs
        self._start_worker()

    def _start_worker(self):
        def worker():
            while True:
                try:
                    log_data = self.queue.get()
                    self.producer.send(self.topic, value=log_data)
                    self.producer.flush()  # Send instantly
                except Exception as e:
                    print(f"Kafka send error: {e}")
        
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def send_log(self, log_data: dict):
        self.queue.put(log_data)  # Non-blocking, queues for background thread

    def sink(self, message):
        # Loguru sink handler - extracts extra fields from logger.bind()
        record = message.record
        extra = record.get("extra", {})
        log_data = {
            "level": record["level"].name,
            "sessionId": extra.get("sessionId", ""),
            "userId": extra.get("userId", ""),
            "packageName": "ny-voice-pod-manager",
            "message": record["message"],
            "timestamp": str(record["time"])
        }
        self.send_log(log_data)
