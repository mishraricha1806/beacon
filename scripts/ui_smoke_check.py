#!/usr/bin/env python3
import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beacon.ui import BeaconUIHandler  # noqa: E402


def multipart_body(fields, files):
    boundary = "----beacon-ui-smoke-boundary"
    chunks = []

    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode())
        chunks.append(b"\r\n")

    for name, path in files.items():
        path = Path(path)
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{path.name}"\r\n'
            ).encode()
        )
        chunks.append(b"Content-Type: application/x-yaml\r\n\r\n")
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode())
    return boundary, b"".join(chunks)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), BeaconUIHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        base_url = f"http://{host}:{port}"
        with urllib.request.urlopen(f"{base_url}/", timeout=10) as response:
            html = response.read().decode("utf-8")

        require("Beacon Readiness Console" in html, "homepage did not render")
        require("release-gate-card" in html, "release gate UI renderer missing")
        require("Is this production ready?" in html, "release gate question missing")

        boundary, body = multipart_body(
            fields={"mode": "direct", "environment": "prod"},
            files={
                "static_config": ROOT / "examples" / "bad-infra" / "kafka-topics.yaml"
            },
        )
        request = urllib.request.Request(
            f"{base_url}/api/beacon",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        summary = payload["readiness_summary"]
        gate = summary["release_gate"]
        rule_ids = {finding["rule_id"] for finding in payload["findings"]}

        require(
            gate["question"] == "Is this production ready?", "bad release gate question"
        )
        require(gate["answer"] == "No", "bad-infra should not be production ready")
        require(gate["decision"] == "NOT READY", "bad-infra should be NOT READY")
        require(gate["why_not"], "release gate should explain why not")
        require(gate["fix_first"], "release gate should include fix-first actions")
        require(
            "kafka.topic.replication_factor.low" in rule_ids,
            "expected Kafka RF finding missing",
        )

        print("ui smoke ok: homepage and static readiness upload")
        return 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
