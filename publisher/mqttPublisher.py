import json
import os
import random
import time

import paho.mqtt.client as mqtt

BROKER_HOST = os.environ.get("BROKER_HOST")
BROKER_PORT = int(os.environ.get("BROKER_PORT"))
NUM_DEVICES = int(os.environ.get("NUM_DEVICES"))
RATE_OF_PUBLISH = int(os.environ.get("RATE_OF_PUBLISH"))
TOPIC = os.environ.get("TOPIC")


class Publisher:

    def __init__(self, broker: str, port: int, keepalive: int) -> None:
        self.broker = broker
        self.port = port
        self.keepalive = keepalive
        self._mqtt_client = mqtt.Client()

    def connect(self) -> None:
        self._mqtt_client.connect(self.broker, self.port, self.keepalive)

    def publish(self, topic, message):
        self._mqtt_client.publish(topic, message, qos=0)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._mqtt_client.disconnect()


def generate_reading(sensor_id):
    reading = {
        "sensor_id": sensor_id,
        "temperature": random.randint(20, 40),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
    }
    print(reading)
    return json.dumps(reading)


def main():
    with Publisher(BROKER_HOST, BROKER_PORT, 60) as publisher:
        while True:
            for i in range(NUM_DEVICES):
                temperature_reading = generate_reading(i)
                publisher.publish(TOPIC, temperature_reading)
                time.sleep(RATE_OF_PUBLISH/NUM_DEVICES)


if __name__ == "__main__":
    main()
