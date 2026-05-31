import argparse
import cgi
import json
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from beacon.flow_runtime import analyze_flow_file
from beacon.kafka_runtime_connector import analyze_kafka_cluster
from beacon.opentelemetry_connector import analyze_opentelemetry_file
from beacon.policy import apply_policy_to_findings, load_policy
from beacon.prometheus_connector import analyze_prometheus_config
from beacon.readiness.kafka.readiness_engine import calculate_readiness
from beacon.runtime_snapshot import analyze_runtime_snapshot_file
from beacon.scanner import scan_path
from beacon.schema_registry_connector import analyze_schema_registry_config


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Beacon Readiness Console</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #172026;
      --muted: #5c6873;
      --line: #d9e0e6;
      --panel: #ffffff;
      --bg: #f6f8fa;
      --accent: #0b6f6a;
      --warn: #a45c00;
      --danger: #b42318;
      --ok: #177245;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
      letter-spacing: 0;
    }
    header {
      padding: 24px 28px 14px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 {
      margin: 0 0 6px;
      font-size: 24px;
      font-weight: 720;
    }
    .sub {
      margin: 0;
      color: var(--muted);
      max-width: 900px;
      line-height: 1.5;
    }
    main {
      display: grid;
      grid-template-columns: minmax(320px, 430px) minmax(0, 1fr);
      gap: 18px;
      padding: 18px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    h2 {
      margin: 0 0 14px;
      font-size: 16px;
    }
    label {
      display: block;
      margin: 12px 0 5px;
      font-size: 13px;
      font-weight: 650;
    }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      background: white;
    }
    textarea {
      min-height: 80px;
      resize: vertical;
    }
    input[type="file"] { padding: 7px; }
    .grid2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .mode {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin: 8px 0 14px;
    }
    .mode label {
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px;
      cursor: pointer;
      font-weight: 650;
    }
    .mode input {
      width: auto;
      margin-right: 6px;
    }
    .hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      margin-top: 5px;
    }
    .readonly {
      border-left: 4px solid var(--accent);
      background: #eef8f6;
      padding: 10px 12px;
      border-radius: 6px;
      color: #16433f;
      font-size: 13px;
      line-height: 1.45;
      margin-bottom: 14px;
    }
    button {
      margin-top: 16px;
      width: 100%;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      padding: 11px 12px;
      font: inherit;
      font-weight: 750;
      cursor: pointer;
    }
    button:disabled {
      opacity: .65;
      cursor: wait;
    }
    .summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 12px;
      min-height: 82px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
    }
    .metric strong {
      font-size: 22px;
    }
    .findings {
      display: grid;
      gap: 10px;
    }
    .finding {
      border: 1px solid var(--line);
      border-left: 5px solid var(--muted);
      border-radius: 7px;
      padding: 12px;
      background: white;
    }
    .finding.CRITICAL, .finding.ERROR { border-left-color: var(--danger); }
    .finding.HIGH { border-left-color: #d04f2f; }
    .finding.MEDIUM { border-left-color: var(--warn); }
    .finding.LOW, .finding.INFO { border-left-color: var(--ok); }
    .finding-title {
      font-weight: 750;
      margin-bottom: 6px;
    }
    .meta {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }
    .empty {
      color: var(--muted);
      padding: 30px;
      text-align: center;
      border: 1px dashed var(--line);
      border-radius: 8px;
      background: #fbfcfd;
    }
    pre {
      white-space: pre-wrap;
      background: #f2f5f7;
      border-radius: 6px;
      padding: 10px;
      font-size: 12px;
      overflow: auto;
    }
    .hidden { display: none; }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      .summary { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Beacon Readiness Console</h1>
    <p class="sub">Run deterministic production-readiness checks across Kafka, Schema Registry, runtime snapshots, Flow, Prometheus, OpenTelemetry, and static infrastructure inputs.</p>
  </header>
  <main>
    <section>
      <h2>Beacon Inputs</h2>
      <div class="readonly">
        Beacon collectors are read-only. Runtime checks query metadata, metrics, spans, configs, and offsets without producing, consuming, altering topics, resetting offsets, or changing infrastructure.
      </div>
      <form id="kafka-form">
        <h2>Static & Runtime Files</h2>
        <label for="static_config">Static config file</label>
        <input id="static_config" name="static_config" type="file">
        <div class="hint">Optional. Upload Terraform, Kubernetes YAML, Kafka config, CI/CD, cloud inventory, or topology YAML.</div>

        <label for="runtime_snapshot">Runtime snapshot</label>
        <input id="runtime_snapshot" name="runtime_snapshot" type="file">

        <label for="flow_snapshot">Flow snapshot</label>
        <input id="flow_snapshot" name="flow_snapshot" type="file">

        <label for="prometheus_config">Prometheus collector config</label>
        <input id="prometheus_config" name="prometheus_config" type="file">

        <label for="opentelemetry_file">OpenTelemetry export</label>
        <input id="opentelemetry_file" name="opentelemetry_file" type="file">

        <h2>Kafka Connection</h2>
        <div class="mode">
          <label><input type="radio" name="mode" value="direct" checked> Direct</label>
          <label><input type="radio" name="mode" value="access"> Access YAML</label>
        </div>

        <div id="direct-fields">
          <label for="bootstrap_server">Bootstrap server</label>
          <input id="bootstrap_server" name="bootstrap_server" placeholder="localhost:9092">

          <label for="security_protocol">Security protocol</label>
          <select id="security_protocol" name="security_protocol">
            <option>PLAINTEXT</option>
            <option>SSL</option>
            <option>SASL_SSL</option>
          </select>

          <label for="ca_cert">CA certificate</label>
          <input id="ca_cert" name="ca_cert" type="file">
          <div class="hint">Optional. Upload is stored temporarily for this run only.</div>

          <label for="client_cert">Client certificate</label>
          <input id="client_cert" name="client_cert" type="file">

          <label for="client_key">Client key</label>
          <input id="client_key" name="client_key" type="file">
        </div>

        <div id="access-fields" class="hidden">
          <label for="access_config">Generic access profile YAML</label>
          <input id="access_config" name="access_config" type="file">
          <div class="hint">Use this for token + topic cert, SASL, mTLS, or mixed org-specific access models.</div>
        </div>

        <div class="grid2">
          <div>
            <label for="topic">Topic</label>
            <input id="topic" name="topic" placeholder="optional">
          </div>
          <div>
            <label for="consumer_group">Consumer group</label>
            <input id="consumer_group" name="consumer_group" placeholder="optional">
          </div>
        </div>

        <div class="grid2">
          <div>
            <label for="max_topics">Max topics</label>
            <input id="max_topics" name="max_topics" type="number" value="50" min="1">
          </div>
          <div>
            <label for="max_groups">Max groups</label>
            <input id="max_groups" name="max_groups" type="number" value="20" min="0">
          </div>
        </div>

        <h2>Schema Registry</h2>
        <label for="schema_registry_config">Schema Registry YAML</label>
        <input id="schema_registry_config" name="schema_registry_config" type="file">
        <div class="hint">Optional. Upload an existing Schema Registry collector config, or fill in the fields below.</div>

        <label for="schema_registry_url">Schema Registry URL</label>
        <input id="schema_registry_url" name="schema_registry_url" placeholder="http://schema-registry.local:8081">

        <div class="grid2">
          <div>
            <label for="schema_registry_auth_type">Auth type</label>
            <select id="schema_registry_auth_type" name="schema_registry_auth_type">
              <option value="">None</option>
              <option value="bearer_token">Bearer token</option>
              <option value="basic">Basic</option>
            </select>
          </div>
          <div>
            <label for="schema_registry_max_subjects">Max subjects</label>
            <input id="schema_registry_max_subjects" name="schema_registry_max_subjects" type="number" value="25" min="0">
          </div>
        </div>

        <div id="schema-token-fields" class="hidden">
          <label for="schema_registry_token">Bearer token</label>
          <input id="schema_registry_token" name="schema_registry_token" type="password" autocomplete="off">
        </div>

        <div id="schema-basic-fields" class="hidden">
          <div class="grid2">
            <div>
              <label for="schema_registry_username">Username</label>
              <input id="schema_registry_username" name="schema_registry_username" autocomplete="off">
            </div>
            <div>
              <label for="schema_registry_password">Password</label>
              <input id="schema_registry_password" name="schema_registry_password" type="password" autocomplete="off">
            </div>
          </div>
        </div>

        <label for="schema_registry_ca_cert">Schema Registry CA certificate</label>
        <input id="schema_registry_ca_cert" name="schema_registry_ca_cert" type="file">
        <div class="hint">Optional. Use this for private CAs or HTTPS trust chains.</div>

        <label for="schema_registry_client_cert">Schema Registry client certificate</label>
        <input id="schema_registry_client_cert" name="schema_registry_client_cert" type="file">

        <label for="schema_registry_client_key">Schema Registry client key</label>
        <input id="schema_registry_client_key" name="schema_registry_client_key" type="file">
        <div class="hint">Optional. Use these for mTLS, including organizations that reuse topic-level PEM/cert files.</div>

        <label for="schema_registry_expected_topics">Expected topic subjects</label>
        <textarea id="schema_registry_expected_topics" name="schema_registry_expected_topics" placeholder="payments: payments-key, payments-value&#10;audit-events: audit-events-value"></textarea>
        <div class="hint">Optional. One topic per line. Use "topic: subject-a, subject-b" or just "topic" for default key/value subjects.</div>

        <button id="run-button" type="submit">Run Beacon Readiness</button>
      </form>
    </section>

    <section>
      <h2>Report</h2>
      <div id="report" class="empty">Run a Beacon readiness check to see findings here.</div>
    </section>
  </main>
  <script>
    const form = document.getElementById('kafka-form');
    const report = document.getElementById('report');
    const button = document.getElementById('run-button');
    const direct = document.getElementById('direct-fields');
    const access = document.getElementById('access-fields');
    const schemaAuth = document.getElementById('schema_registry_auth_type');
    const schemaTokenFields = document.getElementById('schema-token-fields');
    const schemaBasicFields = document.getElementById('schema-basic-fields');

    document.querySelectorAll('input[name="mode"]').forEach((input) => {
      input.addEventListener('change', () => {
        const useAccess = input.checked && input.value === 'access';
        direct.classList.toggle('hidden', useAccess);
        access.classList.toggle('hidden', !useAccess);
      });
    });

    schemaAuth.addEventListener('change', () => {
      schemaTokenFields.classList.toggle('hidden', schemaAuth.value !== 'bearer_token');
      schemaBasicFields.classList.toggle('hidden', schemaAuth.value !== 'basic');
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      button.disabled = true;
      button.textContent = 'Running...';
      report.className = 'empty';
      report.textContent = 'Connecting in read-only mode and building report...';

      try {
        const response = await fetch('/api/beacon', {
          method: 'POST',
          body: new FormData(form)
        });
        const data = await response.json();
        renderReport(data);
      } catch (error) {
        report.className = 'finding ERROR';
        report.innerHTML = '<div class="finding-title">Request failed</div><pre>' + escapeHtml(String(error)) + '</pre>';
      } finally {
        button.disabled = false;
        button.textContent = 'Run Beacon Readiness';
      }
    });

    function renderReport(data) {
      const summary = data.readiness_summary || {};
      const findings = data.findings || [];
      const counts = countSeverities(findings);
      const summaryHtml = `
        <div class="summary">
          <div class="metric"><span>Score</span><strong>${data.score ?? summary.score ?? '-'}</strong></div>
          <div class="metric"><span>Decision</span><strong>${summary.production_decision || '-'}</strong></div>
          <div class="metric"><span>Critical/High</span><strong>${counts.CRITICAL + counts.HIGH}</strong></div>
          <div class="metric"><span>Status</span><strong>${data.score_status || summary.score_status || '-'}</strong></div>
        </div>`;

      if (!findings.length) {
        report.className = '';
        report.innerHTML = summaryHtml + '<div class="empty">No findings returned.</div>';
        return;
      }

      const findingsHtml = findings.map((finding) => `
        <div class="finding ${escapeHtml(finding.severity || '')}">
          <div class="finding-title">${escapeHtml(finding.title || finding.rule_id || 'Finding')}</div>
          <div class="meta">${escapeHtml(finding.severity || '')} · ${escapeHtml(finding.rule_id || '')}</div>
          <div>${escapeHtml(finding.impact || '')}</div>
          <div class="hint">${escapeHtml(finding.recommendation || '')}</div>
        </div>
      `).join('');

      report.className = '';
      report.innerHTML = summaryHtml + '<div class="findings">' + findingsHtml + '</div>';
    }

    function countSeverities(findings) {
      return findings.reduce((acc, finding) => {
        acc[finding.severity] = (acc[finding.severity] || 0) + 1;
        return acc;
      }, {CRITICAL: 0, HIGH: 0});
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[char]));
    }
  </script>
</body>
</html>
"""


class BeaconUIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in {"/", "/index.html"}:
            self.send_error(404)
            return
        self.respond_html(HTML)

    def do_POST(self):
        if self.path not in {"/api/beacon", "/api/kafka"}:
            self.send_error(404)
            return

        try:
            fields, files = parse_multipart(self)
            result = run_beacon_check(
                fields,
                files,
                force_kafka=self.path == "/api/kafka",
            )
            self.respond_json(result)
        except Exception as error:
            self.respond_json(
                {
                    "score": 0,
                    "score_status": "BLOCKED_BY_ANALYSIS_ERROR",
                    "readiness_summary": None,
                    "findings": [
                        {
                            "rule_id": "beacon.ui.request_failed",
                            "domain": "beacon",
                            "category": "operational_safety",
                            "severity": "ERROR",
                            "title": "Beacon readiness request failed",
                            "impact": str(error),
                            "recommendation": "Review the connection inputs and retry.",
                            "file": "beacon-ui",
                            "evidence": {},
                            "tags": ["ui", "beacon"],
                        }
                    ],
                },
                status=500,
            )

    def log_message(self, format, *args):
        return

    def respond_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_multipart(handler):
    form = cgi.FieldStorage(
        fp=handler.rfile,
        headers=handler.headers,
        environ={
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": handler.headers.get("Content-Type"),
        },
    )
    fields = {}
    files = {}

    for key in form.keys():
        item = form[key]
        if isinstance(item, list):
            item = item[0]

        if item.filename:
            content = item.file.read()
            if content:
                files[key] = save_temp_upload(item.filename, content)
        else:
            fields[key] = item.value

    return fields, files


def save_temp_upload(filename, content):
    suffix = "-" + filename.replace("/", "_")
    temp = tempfile.NamedTemporaryFile(
        prefix="beacon-kafka-ui-", suffix=suffix, delete=False
    )
    with temp:
        temp.write(content)
    return temp.name


def save_temp_json_config(prefix, config):
    temp = tempfile.NamedTemporaryFile(prefix=prefix, suffix=".json", delete=False)
    with temp:
        temp.write(json.dumps(config).encode("utf-8"))
    return temp.name


def run_kafka_check(fields, files):
    return run_beacon_check(fields, files, force_kafka=True)


def run_beacon_check(fields, files, force_kafka=False):
    findings = []

    if files.get("static_config"):
        findings.extend(scan_path(files["static_config"]))

    if files.get("runtime_snapshot"):
        findings.extend(analyze_runtime_snapshot_file(files["runtime_snapshot"]))

    if files.get("flow_snapshot"):
        findings.extend(analyze_flow_file(files["flow_snapshot"]))

    if files.get("prometheus_config"):
        findings.extend(
            analyze_prometheus_config(
                files["prometheus_config"],
                timeout=int(fields.get("prometheus_timeout") or 5),
            )
        )

    if files.get("opentelemetry_file"):
        findings.extend(analyze_opentelemetry_file(files["opentelemetry_file"]))

    if force_kafka or has_kafka_input(fields, files):
        findings.extend(run_kafka_collector(fields, files))

    schema_registry_config = resolve_schema_registry_config(fields, files)
    if schema_registry_config:
        findings.extend(
            analyze_schema_registry_config(
                schema_registry_config,
                timeout=int(fields.get("schema_registry_timeout") or 5),
            )
        )

    findings = apply_policy_to_findings(findings, load_policy())
    readiness_summary = calculate_readiness(findings)

    return {
        "score": readiness_summary["score"],
        "score_status": readiness_summary["score_status"],
        "readiness_summary": readiness_summary,
        "findings": findings,
    }


def has_kafka_input(fields, files):
    return any(
        [
            value_or_none(fields.get("bootstrap_server")),
            files.get("access_config"),
            files.get("ca_cert"),
            files.get("client_cert"),
            files.get("client_key"),
            value_or_none(fields.get("topic")),
            value_or_none(fields.get("consumer_group")),
        ]
    )


def run_kafka_collector(fields, files):
    mode = fields.get("mode", "direct")
    access_config = files.get("access_config") if mode == "access" else None
    return analyze_kafka_cluster(
        bootstrap_server=value_or_none(fields.get("bootstrap_server")),
        security_protocol=fields.get("security_protocol", "PLAINTEXT"),
        ca_cert=files.get("ca_cert"),
        client_cert=files.get("client_cert"),
        client_key=files.get("client_key"),
        access_config=access_config,
        topic=value_or_none(fields.get("topic")),
        consumer_group=value_or_none(fields.get("consumer_group")),
        max_topics=int(fields.get("max_topics") or 50),
        max_groups=int(fields.get("max_groups") or 20),
    )


def resolve_schema_registry_config(fields, files):
    if files.get("schema_registry_config"):
        return files["schema_registry_config"]

    url = value_or_none(fields.get("schema_registry_url"))
    if not url:
        return None

    registry = {
        "url": url,
        "max_subjects": int(fields.get("schema_registry_max_subjects") or 25),
    }
    auth = build_schema_registry_auth(fields)
    if auth:
        registry["auth"] = auth

    tls = build_schema_registry_tls(files)
    if tls:
        registry["tls"] = tls

    expected_topics = parse_expected_topic_subjects(
        fields.get("schema_registry_expected_topics")
    )
    if expected_topics:
        registry["expected_topics"] = expected_topics

    return save_temp_json_config(
        "beacon-schema-registry-ui-", {"schema_registry": registry}
    )


def build_schema_registry_auth(fields):
    auth_type = value_or_none(fields.get("schema_registry_auth_type"))

    if auth_type == "bearer_token":
        token = value_or_none(fields.get("schema_registry_token"))
        if token:
            return {"type": "bearer_token", "token": token}

    if auth_type == "basic":
        username = value_or_none(fields.get("schema_registry_username")) or ""
        password = value_or_none(fields.get("schema_registry_password")) or ""
        if username or password:
            return {"type": "basic", "username": username, "password": password}

    return None


def build_schema_registry_tls(files):
    tls = {}

    mapping = {
        "schema_registry_ca_cert": "ca_cert",
        "schema_registry_client_cert": "client_cert",
        "schema_registry_client_key": "client_key",
    }
    for upload_name, config_name in mapping.items():
        if files.get(upload_name):
            tls[config_name] = files[upload_name]

    return tls or None


def parse_expected_topic_subjects(raw):
    topics = []

    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue

        if ":" in line:
            name, subjects = line.split(":", 1)
            topic = {"name": name.strip()}
            subject_list = [
                subject.strip() for subject in subjects.split(",") if subject.strip()
            ]
            if subject_list:
                topic["subjects"] = subject_list
            topics.append(topic)
        else:
            topics.append({"name": line})

    return topics


def value_or_none(value):
    if value is None:
        return None
    value = value.strip()
    return value or None


def main():
    parser = argparse.ArgumentParser(description="Run Beacon local Kafka UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), BeaconUIHandler)
    print(f"Beacon Kafka UI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
