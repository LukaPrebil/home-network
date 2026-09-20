#!/usr/bin/env python3
"""Export whether the TIGO optimiser bus is actually reporting.

Nothing else in this path can say. The taptap bridge publishes its MQTT state
topic on a timer whether or not the bus produced anything, and the timestamp at
the top of that payload (`state["time"]`) is written from the bridge's own clock
on every pass. So the state topic, the heartbeat file, the container's health,
its MQTT session and its TCP socket to the tap bridge all keep looking correct
while the optimisers stop reporting. That is the blind-source shape: the
evidence that would show a problem is absent rather than negative.

The one number that stops moving is the optimisers' own last-report timestamp,
`nodes[*].tmstp`, carried inside the state payload. This sidecar subscribes to
that topic, reads the newest `tmstp` out of it, and exports it, so an alert can
read what is actually missing instead of the transport that keeps working.

Observed 2026-09-17 to 2026-09-20: the bridge's socket to the tap bridge stayed
ESTABLISHED, kept ACKing keepalives, and delivered zero bytes for three days
while 29 of 30 optimisers were reporting on the bus. The bridge logged nothing
and its heartbeat file stayed fresh throughout.

Read-only: it subscribes to one topic and never publishes.
"""

import configparser
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import paho.mqtt.client as mqtt

CONFIG_PATH = os.environ.get("TAPTAP_CONFIG", "/etc/taptap/config.ini")
PORT = int(os.environ.get("WATCHDOG_PORT", "9102"))

# Reference for the age of a report that has never arrived. Large enough to read
# as stale against any threshold, rather than 0, which would read as fresh.
NEVER_REPORTED = 1000000000.0

CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_PATH)

# Same topic the bridge publishes its whole state payload on, built the same way
# it builds it, so a prefix change moves both.
STATE_TOPIC = "{}/{}/state".format(
    CONFIG["TAPTAP"]["TOPIC_PREFIX"], CONFIG["TAPTAP"]["TOPIC_NAME"]
)

LOCK = threading.Lock()
STATE = {
    "connected": 0,
    "messages": 0,
    "last_report": 0.0,  # newest optimiser report epoch in the last state message
    "modules_total": 0,
    "modules_online": 0,
}


def on_connect(client, userdata, flags, rc):
    with LOCK:
        STATE["connected"] = 1 if rc == 0 else 0
    client.subscribe(STATE_TOPIC, qos=int(CONFIG["MQTT"]["QOS"]))


def on_disconnect(client, userdata, *args):
    with LOCK:
        STATE["connected"] = 0


def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return
    nodes = payload.get("nodes") or {}
    reports = [node["tmstp"] for node in nodes.values() if node.get("tmstp")]
    with LOCK:
        STATE["messages"] += 1
        STATE["last_report"] = max(reports) if reports else 0.0
        STATE["modules_total"] = len(nodes)
        STATE["modules_online"] = sum(
            1 for node in nodes.values() if node.get("state_online") == "online"
        )


def render():
    with LOCK:
        snapshot = dict(STATE)
    # Computed at scrape time, not at message time, so it keeps growing while
    # the bus is silent - which is the whole point - and so a caller never has
    # to hold a reference clock of its own. Clamped at 0 in case the CCA's clock
    # runs slightly ahead of this host's.
    if snapshot["last_report"] > 0:
        age = max(0.0, time.time() - snapshot["last_report"])
    else:
        age = NEVER_REPORTED
    return (
        "\n".join(
            [
                "# HELP taptap_mqtt_broker_connected 1 while the watchdog holds its MQTT session",
                "# TYPE taptap_mqtt_broker_connected gauge",
                "taptap_mqtt_broker_connected %d" % snapshot["connected"],
                "# HELP taptap_mqtt_state_messages_total State messages consumed since the watchdog started",
                "# TYPE taptap_mqtt_state_messages_total counter",
                "taptap_mqtt_state_messages_total %d" % snapshot["messages"],
                "# HELP taptap_mqtt_modules_total Optimisers listed in the last state message",
                "# TYPE taptap_mqtt_modules_total gauge",
                "taptap_mqtt_modules_total %d" % snapshot["modules_total"],
                "# HELP taptap_mqtt_modules_online Optimisers the last state message marked online",
                "# TYPE taptap_mqtt_modules_online gauge",
                "taptap_mqtt_modules_online %d" % snapshot["modules_online"],
                "# HELP taptap_mqtt_last_report_timestamp_seconds Unix time of the newest optimiser power report in the last state message, 0 if none has arrived",
                "# TYPE taptap_mqtt_last_report_timestamp_seconds gauge",
                "taptap_mqtt_last_report_timestamp_seconds %f" % snapshot["last_report"],
                "# HELP taptap_mqtt_report_age_seconds Age of that report, recomputed at every scrape",
                "# TYPE taptap_mqtt_report_age_seconds gauge",
                "taptap_mqtt_report_age_seconds %f" % age,
            ]
        )
        + "\n"
    ).encode("utf-8")


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/metrics", "/"):
            self.send_error(404)
            return
        body = render()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Prometheus scrapes every 15 s; the default access log would bury the
        # container's own output under it.
        pass


def main():
    client = mqtt.Client(client_id="taptap-watchdog")
    client.username_pw_set(CONFIG["MQTT"]["USER"], CONFIG["MQTT"]["PASS"])
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    # connect_async, unlike connect, does not raise when the broker is not up
    # yet; loop_start keeps retrying. The watchdog has to be reachable to report
    # that it cannot reach the broker.
    client.connect_async(
        CONFIG["MQTT"]["SERVER"],
        int(CONFIG["MQTT"]["PORT"]),
        int(CONFIG["MQTT"]["TIMEOUT"]),
    )
    client.loop_start()
    ThreadingHTTPServer(("", PORT), MetricsHandler).serve_forever()


if __name__ == "__main__":
    main()
