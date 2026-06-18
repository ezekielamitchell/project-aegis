"""Optional MQTT telemetry publisher.

A no-op unless enabled. paho-mqtt is imported lazily so the dependency is only
required when mqtt_enabled is true.
"""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)


class MqttClient:
    def __init__(
        self,
        enabled: bool = False,
        host: str = "localhost",
        port: int = 1883,
        topic: str = "aegis/telemetry",
    ):
        self.enabled = enabled
        self.host = host
        self.port = port
        self.topic = topic
        self._client = None

    def connect(self) -> None:
        if not self.enabled:
            return
        import paho.mqtt.client as mqtt  # lazy

        self._client = mqtt.Client()
        self._client.connect(self.host, self.port)
        self._client.loop_start()
        log.info("MQTT connected to %s:%d", self.host, self.port)

    def publish(self, payload: dict[str, Any]) -> None:
        if not self.enabled or self._client is None:
            return
        self._client.publish(self.topic, json.dumps(payload))

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
