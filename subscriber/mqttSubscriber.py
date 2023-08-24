import json
import os
import queue
import threading

import paho.mqtt.client as mqtt
from pymongo import MongoClient
import redis

NUM_WORKERS = int(os.environ.get("NUM_WORKERS"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE"))
TOPIC = os.environ.get("TOPIC")

# Replace with the IP address of the MQTT broker
BROKER_HOST = os.environ.get("BROKER_HOST")
BROKER_PORT = int(os.environ.get("BROKER_PORT"))


# Mongo setup
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")
MONGO_HOST = os.environ.get("MONGO_HOST")
MONGO_PORT = int(os.environ.get("MONGO_PORT"))
MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/"
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COL = os.environ.get("MONGO_COL")

# Connect to Redis
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = int(os.environ.get("REDIS_PORT"))
REDIS_DB = int(os.environ.get("REDIS_DB"))
REDIS_KEY_PREFIX = "Sensor"
REDIS_LAST_READINGS_COUNT = 10


class Subscriber:

    def __init__(self, broker: str, port: int, keepalive: int, queue: queue.Queue, topics: tuple) -> None:
        self.broker = broker
        self.port = port
        self.keepalive = keepalive
        self.queue = queue
        self.topics = topics
        self._mqtt_client = mqtt.Client()

    def connect(self) -> None:
        self._mqtt_client.connect(self.broker, self.port, self.keepalive)
        self._mqtt_client.on_connect = self._subscribe
        self._mqtt_client.on_message = self._on_message

    def start(self):
        self._mqtt_client.loop_forever()

    def _subscribe(self, client, userdata, flags, rc) -> None:
        topic = [(t, 0) for t in self.topics]
        self._mqtt_client.subscribe(topic)

    def _on_message(self, client, userdata, message) -> None:
        self.queue.put(message)

    def unsubscribe(self, topics):
        self._mqtt_client.unsubscribe()

    def __enter__(self):
        print("Subscriber started")
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Subscriber out")
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()


class Worker(threading.Thread):

    def __init__(self, queue: queue.Queue, redis_client: redis.Redis, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.queue = queue
        self.client_mongo = MongoClient(MONGO_URI)
        self.db = self.client_mongo[MONGO_DB]
        self.collection = self.db[MONGO_COL]
        self.redis_client = redis_client

    def store_reading(self, value):
        sensor_id = value["sensor_id"]
        key = "{}:{}".format(REDIS_KEY_PREFIX, sensor_id)
        self.redis_client.lpush(key, json.dumps(value))
        self.redis_client.ltrim(key, 0, REDIS_LAST_READINGS_COUNT - 1)

    def run(self):
        docs = []
        while True:
            message = self.queue.get()
            payload = message.payload.decode()
            json_payload = json.loads(payload)
            print(json_payload)
            self.store_reading(json_payload)
            docs.append(json_payload)
            if len(docs) >= BATCH_SIZE:
                self.collection.insert_many(docs)
                docs.clear()
            self.queue.task_done()


def main():
    message_queue = queue.Queue(maxsize=100)
    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB
    )
    redis_client = redis.Redis(connection_pool=redis_pool)
    workers = [Worker(message_queue, redis_client) for _ in range(NUM_WORKERS)]
    for worker in workers:
        worker.start()
    topics = (TOPIC,)
    with Subscriber(BROKER_HOST, BROKER_PORT, 60, message_queue, topics=topics) as subscriber:
        subscriber.start()
    message_queue.join()
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    main()
