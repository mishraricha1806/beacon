import argparse
import cgi
import json
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from beacon.kafka_runtime_connector import analyze_kafka_cluster
from beacon.policy import apply_policy_to_findings, load_policy
from beacon.readiness.kafka.readiness_engine import calculate_readiness


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Beacon Kafka Readiness</title>
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
    input, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      background: white;
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
    <h1>Beacon Kafka Readiness</h1>
    <p class="sub">Connect to Kafka, run read-only diagnostics, and get a production-readiness report without writing YAML by hand.</p>
  </header>
  <main>
    <section>
      <h2>Kafka Connection</h2>
      <div class="readonly">
        Beacon only lists metadata, describes configs, and reads offsets. It never produces, consumes, alters topics, resets offsets, or changes ACLs.
      </div>
      <form id="kafka-form">
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

        <button id="run-button" type="submit">Run Readiness</button>
      </form>
    </section>

    <section>
      <h2>Report</h2>
      <div id="report" class="empty">Run a Kafka readiness check to see findings here.</div>
    </section>
  </main>
  <script>
    const form = document.getElementById('kafka-form');
    const report = document.getElementById('report');
    const button = document.getElementById('run-button');
    const direct = document.getElementById('direct-fields');
    const access = document.getElementById('access-fields');

    document.querySelectorAll('input[name="mode"]').forEach((input) => {
      input.addEventListener('change', () => {
        const useAccess = input.checked && input.value === 'access';
        direct.classList.toggle('hidden', useAccess);
        access.classList.toggle('hidden', !useAccess);
      });
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      button.disabled = true;
      button.textContent = 'Running...';
      report.className = 'empty';
      report.textContent = 'Connecting in read-only mode and building report...';

      try {
        const response = await fetch('/api/kafka', {
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
        button.textContent = 'Run Readiness';
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
        if self.path != "/api/kafka":
            self.send_error(404)
            return

        try:
            fields, files = parse_multipart(self)
            result = run_kafka_check(fields, files)
            self.respond_json(result)
        except Exception as error:
            self.respond_json(
                {
                    "score": 0,
                    "score_status": "BLOCKED_BY_ANALYSIS_ERROR",
                    "readiness_summary": None,
                    "findings": [
                        {
                            "rule_id": "beacon.ui.kafka.request_failed",
                            "domain": "kafka",
                            "category": "operational_safety",
                            "severity": "ERROR",
                            "title": "Kafka readiness request failed",
                            "impact": str(error),
                            "recommendation": "Review the connection inputs and retry.",
                            "file": "beacon-ui",
                            "evidence": {},
                            "tags": ["ui", "kafka"],
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


def run_kafka_check(fields, files):
    mode = fields.get("mode", "direct")
    access_config = files.get("access_config") if mode == "access" else None
    findings = analyze_kafka_cluster(
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
    findings = apply_policy_to_findings(findings, load_policy())
    readiness_summary = calculate_readiness(findings)

    return {
        "score": readiness_summary["score"],
        "score_status": readiness_summary["score_status"],
        "readiness_summary": readiness_summary,
        "findings": findings,
    }


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
