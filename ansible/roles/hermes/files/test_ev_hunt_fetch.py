"""Tests for the EV hunt fetch script. Run directly with python3."""

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPT = pathlib.Path(__file__).with_name("ev-hunt-fetch.py")
SPEC = importlib.util.spec_from_file_location("ev_hunt_fetch", SCRIPT)
ev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ev)

CARD = """
<div class="car flexitem" data-href="/nl/schade/personenautos/bmw-i4/o/1001">
  <h2>BMW i4 eDrive40</h2>
  <p class="model-type">eDrive40</p>
  <div class="price">EUR 25.000</div>
  <div class="details">
    <div title="1ste toelating">2022</div>
    <div title="tellerstand">50.000 km</div>
    <div title="brandstof">Elektrisch</div>
  </div>
</div>
"""


def listing_page(padding=400):
    return "<html><body>%s<p>%s</p></body></html>" % (CARD, "x" * padding)


class FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    requests = {}

    def do_GET(self):
        route = self.path.split("?")[0]
        type(self).requests[route] = type(self).requests.get(route, 0) + 1
        cookie = self.headers.get("Cookie") or ""
        if route in ("/challenge", "/selftest"):
            if "__remote-test=ok" not in cookie:
                self._challenge()
                return
            self._send(200, listing_page())
        elif route == "/listing":
            self._send(200, listing_page())
        elif route == "/empty-full":
            self._send(200, "<html><body><p>%s</p></body></html>" % ("x" * 500))
        elif route == "/blocked":
            self._challenge()
        elif route == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self._send(404, "not found")

    def _challenge(self):
        self.send_response(200)
        self.send_header("Set-Cookie", "__remote-test=ok; Path=/")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send(self, status, body):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class ScriptTestCase(unittest.TestCase):
    def setUp(self):
        FixtureHandler.requests = {}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.base = "http://127.0.0.1:%d" % self.server.server_port
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def config(self, paths, **overrides):
        config = {
            "state_file": os.path.join(self.tmp.name, "state.json"),
            "user_agent": "ev-hunt-test",
            "timeout_seconds": 5,
            "retries": 1,
            "retry_backoff_seconds": 0,
            "request_delay_seconds": 0,
            "max_detail_fetches": 0,
            "max_pages_per_source": 1,
            "missing_runs_before_gone": 2,
            "km_max": 100000,
            "near_miss_factor": 1.2,
            "min_body_bytes": 200,
            "degraded_notice_hours": 24,
            "sources": [
                {
                    "name": "schadeautos-i4-salvage",
                    "platform": "schadeautos",
                    "category": "salvage",
                    "url": self.base + path,
                }
                for path in paths
            ],
            "models": [
                {
                    "key": "i4",
                    "label": "BMW i4",
                    "match": ["bmw i4"],
                    "min_year": 2021,
                    "bounds": {"default": {"salvage": 27300, "clean": 28400}},
                }
            ],
        }
        config.update(overrides)
        return config

    def write_config(self, config):
        path = os.path.join(self.tmp.name, "config.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle)
        return path

    def write_state(self, state):
        path = os.path.join(self.tmp.name, "state.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        return path

    def read_state(self):
        path = os.path.join(self.tmp.name, "state.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def run_main(self, config, argv=None):
        path = self.write_config(config)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ev.main(argv or ["--config", path])
        return code, out.getvalue()


class FetchTests(ScriptTestCase):
    def test_cold_challenge_is_retried(self):
        opener, jar = ev.new_session()
        config = self.config(["/challenge"])
        status, body = ev.fetch(
            self.base + "/challenge", config, config["user_agent"], opener=opener
        )
        self.assertEqual(200, status)
        self.assertGreater(len(body), config["min_body_bytes"])
        self.assertIn("__remote-test", {cookie.name for cookie in jar})
        cards = ev.parse_schadeautos_cards(ev.parse_html(body))
        self.assertEqual(1, len(cards))

    def test_all_short_bodies_raise_scrape_blocked(self):
        opener, _ = ev.new_session()
        config = self.config(["/blocked"])
        with self.assertRaises(ev.ScrapeBlocked):
            ev.fetch(
                self.base + "/blocked", config, config["user_agent"], opener=opener
            )
        self.assertEqual(config["retries"] + 1, FixtureHandler.requests["/blocked"])


class AccountingTests(ScriptTestCase):
    def test_blocked_source_is_not_empty(self):
        config = self.config(["/blocked"])
        self.write_state(
            {
                "version": 1,
                "listings": {},
                "sources": {
                    "schadeautos-i4-salvage": {
                        "last_count": 5,
                        "last_ok": True,
                        "last_run": "2026-11-18T21:00:00Z",
                    }
                },
            }
        )
        code, out = self.run_main(config)
        self.assertEqual(2, code, out)
        self.assertIn("EV-HUNT BLOCKED", out)
        self.assertIn("blocked: 1", out)
        state = self.read_state()
        self.assertEqual({}, state["listings"])
        self.assertEqual(5, state["sources"]["schadeautos-i4-salvage"]["last_count"])
        self.assertFalse(state["sources"]["schadeautos-i4-salvage"]["last_ok"])

    def test_partial_run_saves_healthy_source(self):
        config = self.config(["/blocked", "/listing"])
        config["sources"][1]["name"] = "schadeautos-i4-clean"
        self.write_state(
            {
                "version": 1,
                "listings": {},
                "sources": {
                    "schadeautos-i4-salvage": {
                        "last_count": 5,
                        "last_ok": True,
                        "last_run": "2026-11-18T21:00:00Z",
                    }
                },
            }
        )
        code, out = self.run_main(config)
        self.assertEqual(2, code, out)
        self.assertIn("EV-HUNT PARTIAL", out)
        self.assertIn("sources: 1/2 fetched", out)
        state = self.read_state()
        self.assertIn("schadeautos:1001", state["listings"])
        self.assertEqual(5, state["sources"]["schadeautos-i4-salvage"]["last_count"])
        self.assertEqual(1, state["sources"]["schadeautos-i4-clean"]["last_count"])

    def test_zero_after_stock_is_drift_not_a_fatal_run(self):
        config = self.config(["/empty-full"])
        self.write_state(
            {
                "version": 1,
                "listings": {},
                "sources": {
                    "schadeautos-i4-salvage": {
                        "last_count": 5,
                        "last_ok": True,
                        "last_run": "2026-11-18T21:00:00Z",
                    }
                },
            }
        )
        code, out = self.run_main(config)
        self.assertEqual(2, code, out)
        self.assertIn("drift: 1", out)
        self.assertIn("page yielded no listings but yielded 5 last run", out)
        state = self.read_state()
        self.assertEqual(0, state["sources"]["schadeautos-i4-salvage"]["last_count"])


class DegradedTests(ScriptTestCase):
    def existing_listing(self):
        return {
            "key": "schadeautos:9999",
            "first_seen": "2026-11-01T07:00:00Z",
            "last_seen": "2026-11-18T21:00:00Z",
            "missing_streak": 0,
            "source": "schadeautos-i4-salvage",
            "status": "match",
            "title": "BMW i4 eDrive40",
        }

    def test_total_block_exits_2_and_freezes_seen_set(self):
        config = self.config(["/blocked"])
        before = self.existing_listing()
        self.write_state(
            {
                "version": 1,
                "listings": {"schadeautos:9999": before},
                "sources": {
                    "schadeautos-i4-salvage": {
                        "last_count": 5,
                        "last_ok": True,
                        "last_run": "2026-11-18T21:00:00Z",
                    }
                },
                "last_healthy": {
                    "at": "2026-11-18T21:00:00Z",
                    "parsed": 80,
                    "scope": 26,
                    "matches": 9,
                    "near_misses": 5,
                },
            }
        )
        code, out = self.run_main(config)
        self.assertEqual(2, code, out)
        self.assertIn("EV-HUNT BLOCKED", out)
        self.assertIn("notify: first-degraded", out)
        state = self.read_state()
        self.assertEqual(before, state["listings"]["schadeautos:9999"])
        self.assertEqual(1, state["degraded"]["consecutive_runs"])
        self.assertEqual(26, state["degraded"]["last_healthy_count"])
        self.assertIn("next notice after", out)

    def test_healthy_run_advances_seen_set(self):
        config = self.config(["/challenge"])
        code, out = self.run_main(config)
        self.assertEqual(0, code, out)
        self.assertIn("EV-HUNT RUN", out)
        self.assertIn("notify: healthy", out)
        state = self.read_state()
        self.assertIn("schadeautos:1001", state["listings"])
        self.assertEqual(1, state["last_healthy"]["scope"])

    def test_degraded_notice_cadence(self):
        config = self.config(["/blocked"])
        code, out = self.run_main(config)
        self.assertEqual(2, code, out)
        self.assertIn("notify: first-degraded", out)
        state = self.read_state()
        first_notice = state["degraded"]["last_notice_at"]

        code, out = self.run_main(config)
        self.assertEqual(2, code, out)
        self.assertIn("notify: suppressed", out)
        state = self.read_state()
        self.assertEqual(2, state["degraded"]["consecutive_runs"])
        self.assertEqual(first_notice, state["degraded"]["last_notice_at"])
        self.assertNotIn("next notice after", out)

        state["degraded"]["next_notice_at"] = "2020-01-01T00:00:00Z"
        self.write_state(state)
        code, out = self.run_main(config)
        self.assertEqual(2, code, out)
        self.assertIn("notify: degraded-reminder", out)
        state = self.read_state()
        self.assertEqual(3, state["degraded"]["consecutive_runs"])
        self.assertGreaterEqual(state["degraded"]["last_notice_at"], first_notice)
        self.assertNotEqual("2020-01-01T00:00:00Z", state["degraded"]["next_notice_at"])

    def test_recovery_clears_degraded(self):
        config = self.config(["/challenge"])
        self.write_state(
            {
                "version": 1,
                "listings": {},
                "sources": {},
                "degraded": {
                    "since": "2026-11-19T07:00:00Z",
                    "consecutive_runs": 4,
                    "last_healthy_count": 26,
                    "sources": ["schadeautos-i4-salvage"],
                    "reason": "blocked",
                    "last_notice_at": "2026-11-19T07:02:00Z",
                    "next_notice_at": "2026-11-20T07:02:00Z",
                },
                "last_healthy": {"at": "2026-11-18T21:00:00Z", "scope": 26},
            }
        )
        code, out = self.run_main(config)
        self.assertEqual(0, code, out)
        self.assertIn("notify: recovered", out)
        self.assertIn("recovery:", out)
        state = self.read_state()
        self.assertNotIn("degraded", state)
        self.assertEqual(1, state["degraded_last"]["new_since_outage"])
        self.assertEqual(1, state["degraded_last"]["still_live"])


if __name__ == "__main__":
    unittest.main()
