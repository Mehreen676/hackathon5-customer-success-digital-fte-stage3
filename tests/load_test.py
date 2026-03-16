"""
Load Test Script — Customer Success Digital FTE (Stage 3)

Simulates realistic traffic across all three inbound channels:
  - Web Form  (POST /support/submit)
  - Gmail     (POST /webhooks/gmail)
  - WhatsApp  (POST /webhooks/whatsapp)

Usage modes:

  1. Standalone script (no extra dependencies):
        python tests/load_test.py
        python tests/load_test.py --workers 4 --requests 100 --rps 20

  2. Locust UI (requires: pip install locust):
        locust -f tests/load_test.py --host http://localhost:8000

  3. Locust headless:
        locust -f tests/load_test.py --host http://localhost:8000 \\
               --headless --users 10 --spawn-rate 2 --run-time 60s

Environment:
  LOAD_TEST_HOST   — base URL (default: http://localhost:8000)
  LOAD_TEST_RPS    — target requests/second for standalone mode (default: 10)
  LOAD_TEST_REQS   — total requests for standalone mode (default: 50)
  LOAD_TEST_WORKERS— thread workers for standalone mode (default: 2)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import random
import statistics
import sys
import threading
import time
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_HOST = os.getenv("LOAD_TEST_HOST", "http://localhost:8000")
DEFAULT_RPS = int(os.getenv("LOAD_TEST_RPS", "10"))
DEFAULT_REQS = int(os.getenv("LOAD_TEST_REQS", "50"))
DEFAULT_WORKERS = int(os.getenv("LOAD_TEST_WORKERS", "2"))

# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------

WEBFORM_SAMPLES = [
    {
        "name": "Alice Load",
        "email": "alice.load@example.com",
        "subject": "Invoice question",
        "message": "Could you please help me understand the line items on my latest invoice?",
    },
    {
        "name": "Bob Load",
        "email": "bob.load@example.com",
        "subject": "Password reset not working",
        "message": "I tried to reset my password three times but the email never arrives.",
    },
    {
        "name": "Carol Load",
        "email": "carol.load@example.com",
        "subject": "API integration help",
        "message": "Our integration is returning 401 errors after the recent credential rotation.",
    },
    {
        "name": "Dave Load",
        "email": "dave.load@example.com",
        "subject": "Pricing question",
        "message": "Can I get a discount for paying annually instead of monthly?",
    },
    {
        "name": "Eve Load",
        "email": "eve.load@example.com",
        "subject": "Feature request",
        "message": "We would love an SSO integration with Okta. Is this on the roadmap?",
    },
    {
        "name": "Frank Load",
        "email": "frank.load@example.com",
        "subject": "Data export",
        "message": "How can I export all our conversation history and ticket data?",
    },
    {
        "name": "Grace Load",
        "email": "grace.load@example.com",
        "subject": "Account upgrade",
        "message": "I'd like to upgrade from the Pro plan to the Enterprise plan.",
    },
    {
        "name": "Henry Load",
        "email": "henry.load@example.com",
        "subject": "Technical error",
        "message": "The dashboard shows a 500 error when I try to access the analytics section.",
    },
]

GMAIL_EMAILS = [
    ("gmail1.load@example.com", "Invoice help", "Please help with invoice #INV-2025-001."),
    ("gmail2.load@example.com", "Integration docs", "Where can I find API integration documentation?"),
    ("gmail3.load@example.com", "Billing cycle", "When does my billing cycle reset each month?"),
    ("gmail4.load@example.com", "User management", "How do I add team members to my account?"),
    ("gmail5.load@example.com", "Storage limits", "What is the storage limit for the Pro plan?"),
]

WHATSAPP_NUMBERS = [
    ("+15001110001", "Hi need help with billing"),
    ("+15001110002", "Password reset please"),
    ("+15001110003", "What are your enterprise pricing plans?"),
    ("+15001110004", "API key rotation help needed"),
    ("+15001110005", "How to cancel subscription?"),
]


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------

def _post_json(url: str, payload: dict, timeout: int = 10) -> tuple[int, float]:
    """POST JSON payload, return (status_code, latency_ms)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return resp.status, (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, (time.perf_counter() - t0) * 1000
    except Exception:
        return 0, (time.perf_counter() - t0) * 1000


def _post_form(url: str, fields: dict, timeout: int = 10) -> tuple[int, float]:
    """POST form-encoded payload, return (status_code, latency_ms)."""
    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return resp.status, (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, (time.perf_counter() - t0) * 1000
    except Exception:
        return 0, (time.perf_counter() - t0) * 1000


def _make_gmail_payload(email: str, subject: str, body: str, msg_id: str) -> dict:
    email_data = {"from_email": email, "subject": subject, "body": body, "message_id": msg_id}
    encoded = base64.b64encode(json.dumps(email_data).encode()).decode()
    return {
        "message": {
            "data": encoded,
            "messageId": msg_id,
            "publishTime": "2025-01-01T00:00:00Z",
            "attributes": {"email": email},
        },
        "subscription": "projects/nexora/subscriptions/gmail-push",
    }


def _make_whatsapp_form(phone: str, body: str, sid: str) -> dict:
    return {
        "From": f"whatsapp:{phone}",
        "Body": body,
        "MessageSid": sid,
        "AccountSid": "ACload",
        "To": "whatsapp:+14155238886",
        "NumMedia": "0",
    }


# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

@dataclass
class RequestResult:
    channel: str
    status: int
    latency_ms: float
    success: bool


@dataclass
class LoadTestReport:
    total: int = 0
    success: int = 0
    failed: int = 0
    latencies: List[float] = field(default_factory=list)
    by_channel: Dict[str, Dict] = field(default_factory=dict)

    def record(self, result: RequestResult) -> None:
        self.total += 1
        if result.success:
            self.success += 1
        else:
            self.failed += 1
        self.latencies.append(result.latency_ms)

        ch = self.by_channel.setdefault(
            result.channel, {"total": 0, "success": 0, "failed": 0, "latencies": []}
        )
        ch["total"] += 1
        if result.success:
            ch["success"] += 1
        else:
            ch["failed"] += 1
        ch["latencies"].append(result.latency_ms)

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("  LOAD TEST RESULTS")
        print("=" * 60)
        print(f"  Total requests : {self.total}")
        print(f"  Succeeded      : {self.success}")
        print(f"  Failed         : {self.failed}")
        if self.latencies:
            print(f"  Avg latency    : {statistics.mean(self.latencies):.1f} ms")
            print(f"  Median latency : {statistics.median(self.latencies):.1f} ms")
            print(f"  P95 latency    : {self._p95():.1f} ms")
            print(f"  Max latency    : {max(self.latencies):.1f} ms")
        print()
        for ch, stats in sorted(self.by_channel.items()):
            lat = stats["latencies"]
            avg = f"{statistics.mean(lat):.1f}" if lat else "N/A"
            p95 = f"{sorted(lat)[int(len(lat) * 0.95)]:.1f}" if lat else "N/A"
            print(
                f"  {ch:<12}  total={stats['total']}  ok={stats['success']}"
                f"  fail={stats['failed']}  avg={avg}ms  p95={p95}ms"
            )
        print("=" * 60)

    def _p95(self) -> float:
        sorted_lat = sorted(self.latencies)
        idx = max(0, int(len(sorted_lat) * 0.95) - 1)
        return sorted_lat[idx]


# ---------------------------------------------------------------------------
# Worker functions
# ---------------------------------------------------------------------------

_report = LoadTestReport()
_report_lock = threading.Lock()


def _record(result: RequestResult) -> None:
    with _report_lock:
        _report.record(result)


def send_webform_request(host: str) -> None:
    payload = random.choice(WEBFORM_SAMPLES).copy()
    # Add a unique suffix to avoid dedup issues
    payload = {**payload, "email": f"load_{int(time.time()*1000)}_{random.randint(0,9999)}@load.test"}
    status, latency = _post_json(f"{host}/support/submit", payload)
    _record(RequestResult("web_form", status, latency, status == 200))


def send_gmail_request(host: str) -> None:
    email, subject, body = random.choice(GMAIL_EMAILS)
    msg_id = f"load_gmail_{int(time.time()*1000)}_{random.randint(0, 99999)}"
    payload = _make_gmail_payload(email, subject, body, msg_id)
    status, latency = _post_json(f"{host}/webhooks/gmail", payload)
    _record(RequestResult("gmail", status, latency, status == 200))


def send_whatsapp_request(host: str) -> None:
    phone, body = random.choice(WHATSAPP_NUMBERS)
    sid = f"SM_load_{int(time.time()*1000)}_{random.randint(0, 99999)}"
    form = _make_whatsapp_form(phone, body, sid)
    status, latency = _post_form(f"{host}/webhooks/whatsapp", form)
    _record(RequestResult("whatsapp", status, latency, status == 200))


SENDERS = [send_webform_request, send_gmail_request, send_whatsapp_request]


# ---------------------------------------------------------------------------
# Rate-limited runner
# ---------------------------------------------------------------------------

def run_load_test(
    host: str = DEFAULT_HOST,
    total_requests: int = DEFAULT_REQS,
    target_rps: float = DEFAULT_RPS,
    workers: int = DEFAULT_WORKERS,
) -> LoadTestReport:
    """
    Execute `total_requests` requests at ~`target_rps` using `workers` threads.
    Returns the completed LoadTestReport.
    """
    global _report
    with _report_lock:
        _report = LoadTestReport()

    interval = 1.0 / target_rps  # seconds between request dispatches
    semaphore = threading.Semaphore(workers)
    threads: List[threading.Thread] = []
    start_time = time.perf_counter()

    print(f"\nLoad test starting: {total_requests} requests @ {target_rps} RPS "
          f"({workers} workers) → {host}")
    print("Channels: web_form / gmail / whatsapp (round-robin with jitter)\n")

    for i in range(total_requests):
        semaphore.acquire()
        sender = SENDERS[i % len(SENDERS)]

        def _run(fn=sender):
            try:
                fn(host)
            finally:
                semaphore.release()

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        threads.append(t)

        # Rate limiting
        elapsed = time.perf_counter() - start_time
        expected = (i + 1) * interval
        sleep_time = expected - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

        if (i + 1) % 10 == 0:
            print(f"  Dispatched {i + 1}/{total_requests} requests...")

    for t in threads:
        t.join(timeout=30)

    duration = time.perf_counter() - start_time
    actual_rps = _report.total / duration if duration > 0 else 0
    print(f"\nDone in {duration:.1f}s  (actual RPS: {actual_rps:.1f})")

    with _report_lock:
        return _report


# ---------------------------------------------------------------------------
# Scenario functions (reusable from pytest or CLI)
# ---------------------------------------------------------------------------

def scenario_webform_burst(host: str, count: int = 20, rps: float = 10.0) -> LoadTestReport:
    """Simulate a burst of web form submissions."""
    global _report
    with _report_lock:
        _report = LoadTestReport()

    interval = 1.0 / rps
    threads = []
    for i in range(count):
        t = threading.Thread(target=send_webform_request, args=(host,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(interval)
    for t in threads:
        t.join(timeout=20)

    with _report_lock:
        return _report


def scenario_gmail_burst(host: str, count: int = 20, rps: float = 10.0) -> LoadTestReport:
    """Simulate a burst of Gmail webhook notifications."""
    global _report
    with _report_lock:
        _report = LoadTestReport()

    interval = 1.0 / rps
    threads = []
    for i in range(count):
        t = threading.Thread(target=send_gmail_request, args=(host,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(interval)
    for t in threads:
        t.join(timeout=20)

    with _report_lock:
        return _report


def scenario_mixed_traffic(host: str, count: int = 30, rps: float = 10.0) -> LoadTestReport:
    """Mixed traffic: web_form (40%) + gmail (30%) + whatsapp (30%)."""
    global _report
    with _report_lock:
        _report = LoadTestReport()

    weights = [send_webform_request] * 4 + [send_gmail_request] * 3 + [send_whatsapp_request] * 3
    interval = 1.0 / rps
    threads = []
    for i in range(count):
        sender = random.choice(weights)
        t = threading.Thread(target=sender, args=(host,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(interval)
    for t in threads:
        t.join(timeout=20)

    with _report_lock:
        return _report


# ---------------------------------------------------------------------------
# Locust integration (optional — only used when locust is installed)
# ---------------------------------------------------------------------------

try:
    from locust import HttpUser, task, between, events

    class WebFormUser(HttpUser):
        """Simulates a customer submitting a web support form."""
        wait_time = between(1, 3)
        weight = 4

        @task
        def submit_form(self):
            payload = random.choice(WEBFORM_SAMPLES).copy()
            payload["email"] = f"locust_{int(time.time()*1000)}@load.test"
            self.client.post("/support/submit", json=payload, name="/support/submit")

        @task(weight=1)
        def check_health(self):
            self.client.get("/health", name="/health")

    class GmailWebhookUser(HttpUser):
        """Simulates Google Pub/Sub pushing Gmail notifications."""
        wait_time = between(2, 5)
        weight = 3

        @task
        def push_notification(self):
            email, subject, body = random.choice(GMAIL_EMAILS)
            msg_id = f"locust_gmail_{int(time.time()*1000)}_{random.randint(0, 9999)}"
            payload = _make_gmail_payload(email, subject, body, msg_id)
            self.client.post("/webhooks/gmail", json=payload, name="/webhooks/gmail")

    class WhatsAppWebhookUser(HttpUser):
        """Simulates Twilio sending WhatsApp message webhooks."""
        wait_time = between(2, 6)
        weight = 3

        @task
        def send_message(self):
            phone, body = random.choice(WHATSAPP_NUMBERS)
            sid = f"SM_locust_{int(time.time()*1000)}_{random.randint(0, 9999)}"
            form = _make_whatsapp_form(phone, body, sid)
            self.client.post(
                "/webhooks/whatsapp",
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                name="/webhooks/whatsapp",
            )

except ImportError:
    # Locust not installed — standalone mode only
    pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nexora Customer Success load test (standalone mode)"
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="API base URL")
    parser.add_argument("--requests", type=int, default=DEFAULT_REQS, help="Total request count")
    parser.add_argument("--rps", type=float, default=DEFAULT_RPS, help="Target requests per second")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Concurrent workers")
    parser.add_argument(
        "--scenario",
        choices=["all", "webform", "gmail", "mixed"],
        default="all",
        help="Which scenario to run",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.scenario == "webform":
        report = scenario_webform_burst(args.host, count=args.requests, rps=args.rps)
    elif args.scenario == "gmail":
        report = scenario_gmail_burst(args.host, count=args.requests, rps=args.rps)
    elif args.scenario == "mixed":
        report = scenario_mixed_traffic(args.host, count=args.requests, rps=args.rps)
    else:
        report = run_load_test(args.host, args.requests, args.rps, args.workers)

    report.print_summary()

    # Exit with non-zero if error rate > 10%
    if report.total > 0 and report.failed / report.total > 0.10:
        print(f"\nWARN: error rate {report.failed / report.total:.1%} exceeds 10% threshold")
        sys.exit(1)
