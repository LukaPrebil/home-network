#!/usr/bin/env python3
"""Wake page backend.

Sends a Wake-on-LAN magic packet for a configured host and reports whether that
host answers on a TCP port. Tailscale Serve publishes it to the tailnet and
injects Tailscale-User-Login, which is the only authorisation this process
checks. It binds loopback so nothing on the LAN reaches it directly.
"""

from __future__ import annotations

import argparse
import json
import logging
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

LOG = logging.getLogger("wake_page")

PACKET_PREFIX = b"\xff" * 6
PACKET_REPEATS = 16

PAGE = b"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wake</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; padding: 24px;
         background: #111; color: #eee; }
  h1 { font-size: 18px; font-weight: 600; margin: 0 0 20px; }
  .host { border: 1px solid #333; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
  .name { font-size: 20px; font-weight: 600; }
  .state { margin: 8px 0 16px; color: #9aa; }
  .state.up { color: #6c6; }
  button { font-size: 18px; padding: 16px; width: 100%; border-radius: 10px;
           border: 0; background: #2d6cdf; color: #fff; }
  button:active { background: #2456b0; }
  .foot { color: #667; font-size: 13px; margin-top: 16px; }
</style>
<h1>Wake</h1>
<div id="hosts"></div>
<div class="foot" id="foot"></div>
<script>
const hosts = document.getElementById('hosts');
const foot = document.getElementById('foot');
let seen = new Map();

function render(rows) {
  hosts.textContent = '';
  for (const row of rows) {
    const card = document.createElement('div');
    card.className = 'host';
    const name = document.createElement('div');
    name.className = 'name';
    name.textContent = row.host;
    const state = document.createElement('div');
    state.className = 'state' + (row.reachable ? ' up' : '');
    const before = seen.get(row.host);
    state.textContent = describe(row, before);
    const button = document.createElement('button');
    button.textContent = 'Wake ' + row.host;
    button.onclick = () => wake(row.host);
    card.append(name, state, button);
    hosts.append(card);
  }
}

function describe(row, before) {
  if (row.reachable) {
    const when = row.reachable_after !== null ? ' after ' + row.reachable_after + 's' : '';
    return 'reachable' + when;
  }
  if (row.monitoring) {
    return 'unreachable, probing (' + row.attempts + ' checks so far)';
  }
  if (before === 'monitoring') {
    return 'gave up after ' + row.attempts + ' checks';
  }
  return 'unreachable';
}

async function refresh() {
  try {
    const res = await fetch('/status');
    const data = await res.json();
    seen = new Map(data.hosts.map((row) => [row.host, row.monitoring ? 'monitoring' : 'idle']));
    render(data.hosts);
    foot.textContent = 'checked ' + new Date().toLocaleTimeString();
  } catch (err) {
    foot.textContent = 'status unavailable: ' + err;
  }
}

async function wake(host) {
  foot.textContent = 'waking ' + host;
  await fetch('/wake?host=' + encodeURIComponent(host), { method: 'POST' });
  await refresh();
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) refresh();
});
refresh();
</script>
</html>
"""


def parse_mac(mac: str) -> bytes:
    """Return the six raw bytes of a MAC given in colon or dash form."""
    raw = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(raw) != 6:
        raise ValueError(f"MAC {mac!r} is not six bytes")
    return raw


def build_magic_packet(mac: str) -> bytes:
    """Build the 102-byte packet a Wake-on-LAN NIC listens for."""
    return PACKET_PREFIX + parse_mac(mac) * PACKET_REPEATS


def send_magic_packet(settings: dict, host: dict) -> None:
    """Broadcast the magic packet for one host on every configured port."""
    packet = build_magic_packet(host["mac"])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        for port in settings["wol_ports"]:
            sock.sendto(packet, (settings["broadcast"], port))
            LOG.info(
                "magic packet sent host=%s bytes=%d dst=%s:%d",
                host["name"],
                len(packet),
                settings["broadcast"],
                port,
            )
    finally:
        sock.close()


def probe(host: dict, timeout: float) -> bool:
    """True when a TCP connection to the host's probe port opens."""
    try:
        with socket.create_connection((host["probe_host"], host["probe_port"]), timeout):
            return True
    except OSError:
        return False


class Monitor:
    """The probe cycle that follows one wake request for one host.

    A magic packet buys nothing for 60 to 90 seconds, so the first probe waits
    two seconds and later ones back off to the poll interval. The cycle ends on
    the first successful probe or when the window runs out.
    """

    def __init__(self, settings: dict, host: dict) -> None:
        self.settings = settings
        self.host = host
        self.lock = threading.Lock()
        self.attempts = 0
        self.reachable = False
        self.reachable_after: float | None = None
        self.started_at = time.monotonic()
        self.last_probe_at: float | None = None
        self.finished = False

    def start(self) -> None:
        threading.Thread(target=self.run, daemon=True).start()

    def run(self) -> None:
        backoff = list(self.settings["backoff_seconds"])
        poll = self.settings["poll_seconds"]
        window = self.settings["window_seconds"]
        delays = backoff + [poll] * (window // poll + 2)
        for delay in delays:
            if time.monotonic() - self.started_at + delay > window:
                break
            time.sleep(delay)
            ok = probe(self.host, self.settings["probe_timeout"])
            with self.lock:
                self.attempts += 1
                self.last_probe_at = time.monotonic()
                if ok:
                    self.reachable = True
                    self.reachable_after = round(self.last_probe_at - self.started_at, 1)
                    self.finished = True
                    LOG.info(
                        "host reachable host=%s after=%.1fs attempts=%d",
                        self.host["name"],
                        self.reachable_after,
                        self.attempts,
                    )
                    return
        with self.lock:
            self.finished = True
        LOG.info("gave up host=%s attempts=%d", self.host["name"], self.attempts)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "host": self.host["name"],
                "probe_host": self.host["probe_host"],
                "probe_port": self.host["probe_port"],
                "reachable": self.reachable,
                "attempts": self.attempts,
                "reachable_after": self.reachable_after,
                "last_probe_seconds_ago": (
                    None
                    if self.last_probe_at is None
                    else round(time.monotonic() - self.last_probe_at, 1)
                ),
                "monitoring": not self.finished,
            }


class Registry:
    """The current monitor per host, plus an on-demand probe when idle."""

    def __init__(self, settings: dict) -> None:
        self.settings = settings
        self.lock = threading.Lock()
        self.monitors: dict[str, Monitor] = {}

    def wake(self, only: str | None = None) -> list[dict]:
        rows = []
        for host in self.settings["hosts"]:
            if only is not None and host["name"] != only:
                continue
            send_magic_packet(self.settings, host)
            monitor = Monitor(self.settings, host)
            with self.lock:
                self.monitors[host["name"]] = monitor
            monitor.start()
            rows.append({"host": host["name"], "monitoring": True})
        return rows

    def status(self) -> list[dict]:
        rows = []
        for host in self.settings["hosts"]:
            with self.lock:
                monitor = self.monitors.get(host["name"])
            if monitor is not None:
                rows.append(monitor.snapshot())
                continue
            reachable = probe(host, self.settings["probe_timeout"])
            rows.append(
                {
                    "host": host["name"],
                    "probe_host": host["probe_host"],
                    "probe_port": host["probe_port"],
                    "reachable": reachable,
                    "attempts": 0,
                    "reachable_after": None,
                    "last_probe_seconds_ago": 0.0,
                    "monitoring": False,
                }
            )
        return rows


class Handler(BaseHTTPRequestHandler):
    """Loopback request handler. Authentication is the injected identity header."""

    server_version = "wake_page"

    def log_message(self, fmt: str, *args) -> None:
        LOG.info("http %s", fmt % args)

    def authorized(self) -> bool:
        return self.headers.get("Tailscale-User-Login") == self.server.settings["allow_login"]

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        if not self.authorized():
            LOG.info("refused path=%s reason=no-identity", self.path)
            self.send_json({"error": "forbidden"}, 403)
            return
        if self.path == "/status":
            self.send_json({"hosts": self.server.registry.status()})
            return
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
            return
        self.send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        if not self.authorized():
            LOG.info("refused path=%s reason=no-identity", self.path)
            self.send_json({"error": "forbidden"}, 403)
            return
        target = urlsplit(self.path)
        if target.path == "/wake":
            only = parse_qs(target.query).get("host", [None])[0]
            self.send_json({"woke": self.server.registry.wake(only)})
            return
        self.send_json({"error": "not found"}, 404)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/etc/wake-page/config.json")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    with open(args.config, encoding="utf-8") as handle:
        settings = json.load(handle)

    server = ThreadingHTTPServer((settings["listen"], settings["port"]), Handler)
    server.settings = settings
    server.registry = Registry(settings)
    LOG.info(
        "listening on %s:%d hosts=%s",
        settings["listen"],
        settings["port"],
        ",".join(host["name"] for host in settings["hosts"]),
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
