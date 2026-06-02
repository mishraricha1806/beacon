import argparse
import cgi
import json
import logging
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from beacon.flow_runtime import analyze_flow_file
from beacon.kafka_acl_scanner import analyze_kafka_acl_file
from beacon.kafka_history import analyze_kafka_history_file
from beacon.kafka_runtime_connector import analyze_kafka_cluster
from beacon.kubernetes_runtime_connector import analyze_kubernetes_cluster
from beacon.opentelemetry_connector import analyze_opentelemetry_file
from beacon.policy import apply_policy_to_findings, load_policy
from beacon.prometheus_connector import analyze_prometheus_config
from beacon.readiness.kafka.readiness_engine import calculate_readiness
from beacon.intelligence.context import load_intelligence_context
from beacon.readiness.interpretation import sort_findings
from beacon.runtime_snapshot import analyze_runtime_snapshot_file
from beacon.scanner import scan_path
from beacon.schema_registry_connector import analyze_schema_registry_config


LOGGER = logging.getLogger(__name__)


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
    .domain-panel {
      border-top: 1px solid var(--line);
      margin-top: 16px;
      padding-top: 16px;
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
    .result-actions {
      display: flex;
      gap: 10px;
      margin: 0 0 14px;
      flex-wrap: wrap;
    }
    .result-actions button {
      width: auto;
      margin-top: 0;
      background: #eef3f6;
      color: var(--ink);
      border: 1px solid var(--line);
      padding: 8px 10px;
      font-weight: 700;
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
    .insight-list {
      border: 1px solid var(--line);
      border-radius: 7px;
      background: white;
      padding: 12px 14px;
      margin-bottom: 14px;
    }
    .insight-list h3 {
      margin: 0 0 8px;
      font-size: 14px;
    }
    .insight-list ul {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.45;
      font-size: 13px;
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
      .result-actions button { width: 100%; }
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
      <form id="beacon-form">
        <label for="domain-select">Domain</label>
        <select id="domain-select" name="domain_select">
          <option value="all">All domains</option>
          <option value="static">Static readiness</option>
          <option value="runtime">Runtime snapshot</option>
          <option value="flow">Flow intelligence</option>
          <option value="kafka">Kafka</option>
          <option value="kubernetes">Kubernetes</option>
          <option value="schema">Schema Registry</option>
          <option value="telemetry">Prometheus and OpenTelemetry</option>
        </select>
        <div class="hint">Choose a focused domain, or keep all domains visible to combine multiple inputs into one report.</div>

        <label for="environment">Environment profile</label>
        <select id="environment" name="environment">
          <option value="">Auto-detect</option>
          <option value="dev">Dev</option>
          <option value="test">Test</option>
          <option value="staging">Staging</option>
          <option value="prod">Prod</option>
        </select>
        <div class="hint">Prod keeps strict HA rules. Dev/test allows common non-production patterns such as single-broker Kafka.</div>

        <label for="intelligence_context">Intelligence context</label>
        <input id="intelligence_context" name="intelligence_context" type="file">
        <div class="hint">Optional YAML/JSON profile with organization standards, environment policy, topic patterns, and approved exceptions.</div>

        <div class="domain-panel" data-domain-panel="static">
        <h2>Static Readiness</h2>
        <label for="static_config">Static config file</label>
        <input id="static_config" name="static_config" type="file">
        <div class="hint">Optional. Upload Terraform, Kubernetes YAML, Kafka config, CI/CD, cloud inventory, or topology YAML.</div>
        </div>

        <div class="domain-panel" data-domain-panel="runtime">
        <h2>Runtime Snapshot</h2>
        <label for="runtime_snapshot">Runtime snapshot</label>
        <input id="runtime_snapshot" name="runtime_snapshot" type="file">
        <div class="hint">Optional. Upload API, database, storage, Kubernetes, Kafka, or combined runtime snapshots.</div>
        </div>

        <div class="domain-panel" data-domain-panel="flow">
        <h2>Flow Intelligence</h2>
        <label for="flow_snapshot">Flow snapshot</label>
        <input id="flow_snapshot" name="flow_snapshot" type="file">
        <div class="hint">Optional. Upload cross-system flow telemetry that links API, Kafka, consumers, databases, and deployments.</div>
        </div>

        <div class="domain-panel" data-domain-panel="telemetry">
        <h2>Telemetry Collectors</h2>
        <label for="prometheus_config">Prometheus collector config</label>
        <input id="prometheus_config" name="prometheus_config" type="file">
        <label for="prometheus_timeout">Prometheus timeout seconds</label>
        <input id="prometheus_timeout" name="prometheus_timeout" type="number" value="5" min="1" max="30">

        <label for="opentelemetry_file">OpenTelemetry export</label>
        <input id="opentelemetry_file" name="opentelemetry_file" type="file">
        </div>

        <div class="domain-panel" data-domain-panel="kafka">
        <h2>Kafka Connection</h2>
        <label for="kafka_acl_export">Kafka ACL export</label>
        <input id="kafka_acl_export" name="kafka_acl_export" type="file">
        <div class="hint">Optional. Use when live DescribeAcls is blocked; supports YAML or JSON ACL exports.</div>

        <label for="kafka_history">Kafka runtime history</label>
        <input id="kafka_history" name="kafka_history" type="file">
        <div class="hint">Optional. Upload historical Kafka runtime snapshots for trend diagnostics.</div>

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

        <div class="grid2">
          <div>
            <label for="churn_samples">Group churn samples</label>
            <input id="churn_samples" name="churn_samples" type="number" value="1" min="1" max="5">
          </div>
          <div>
            <label for="churn_interval_seconds">Churn interval seconds</label>
            <input id="churn_interval_seconds" name="churn_interval_seconds" type="number" value="0" min="0" max="30">
          </div>
        </div>
        <div class="hint">Use 3 samples with a short interval to catch rebalance/member churn during a live incident.</div>
        </div>

        <div class="domain-panel" data-domain-panel="kubernetes">
        <h2>Kubernetes Live</h2>
        <label><input type="checkbox" name="kubernetes_live" value="true"> Collect live Kubernetes runtime signals</label>
        <label for="kubernetes_namespace">Namespace</label>
        <input id="kubernetes_namespace" name="kubernetes_namespace" placeholder="optional">
        <label for="kubernetes_context">Context</label>
        <input id="kubernetes_context" name="kubernetes_context" placeholder="optional">
        <label for="kubernetes_kubeconfig">Kubeconfig</label>
        <input id="kubernetes_kubeconfig" name="kubernetes_kubeconfig" type="file">
        <div class="hint">Uses read-only kubectl get commands. Leave unchecked if you only want uploaded Kubernetes snapshots.</div>
        </div>

        <div class="domain-panel" data-domain-panel="schema">
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
        <label for="schema_registry_timeout">Schema Registry timeout seconds</label>
        <input id="schema_registry_timeout" name="schema_registry_timeout" type="number" value="5" min="1" max="30">

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
        </div>

        <button id="run-button" type="submit">Run Beacon Readiness</button>
      </form>
    </section>

    <section>
      <h2>Report</h2>
      <div id="report" class="empty">Run a Beacon readiness check to see findings here.</div>
    </section>
  </main>
  <script>
    const form = document.getElementById('beacon-form');
    const report = document.getElementById('report');
    const button = document.getElementById('run-button');
    const direct = document.getElementById('direct-fields');
    const access = document.getElementById('access-fields');
    const schemaAuth = document.getElementById('schema_registry_auth_type');
    const schemaTokenFields = document.getElementById('schema-token-fields');
    const schemaBasicFields = document.getElementById('schema-basic-fields');
    const domainSelect = document.getElementById('domain-select');
    let latestReport = null;

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

    domainSelect.addEventListener('change', () => {
      document.querySelectorAll('[data-domain-panel]').forEach((panel) => {
        const selected = domainSelect.value;
        const domains = panel.dataset.domainPanel.split(' ');
        panel.classList.toggle('hidden', selected !== 'all' && !domains.includes(selected));
      });
    });
    domainSelect.dispatchEvent(new Event('change'));

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
        latestReport = data;
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
      const topReasons = summary.top_reasons || [];
      const nextActions = summary.next_best_actions || [];
      const rootCauses = summary.root_cause_hypotheses || [];
      const groupedRisks = summary.grouped_risks || [];
      const intelligenceContext = summary.intelligence_context || {};
      const architectAssessment = summary.architect_assessment || null;
      const summaryHtml = `
        <div class="result-actions">
          <button type="button" onclick="downloadReport()">Download JSON</button>
        </div>
        <div class="summary">
          <div class="metric"><span>Score</span><strong>${data.score ?? summary.score ?? '-'}</strong></div>
          <div class="metric"><span>Decision</span><strong>${summary.production_decision || '-'}</strong></div>
          <div class="metric"><span>Risk Points</span><strong>${summary.risk_points ?? '-'}</strong></div>
          <div class="metric"><span>Environment</span><strong>${summary.environment || '-'}</strong></div>
        </div>
        ${renderArchitectAssessment(architectAssessment)}
        ${renderIntelligenceContext(intelligenceContext)}
        ${renderBusinessCategories(summary.business_categories || {})}
        ${renderGroupedRisks(groupedRisks)}
        ${renderInsightList('Top Reasons', topReasons)}
        ${renderInsightList('Next Actions', nextActions)}
        ${renderRootCauses(rootCauses)}`;

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

    function renderInsightList(title, items) {
      if (!items.length) {
        return '';
      }
      return '<div class="insight-list"><h3>' + escapeHtml(title) + '</h3><ul>' +
        items.slice(0, 5).map((item) => '<li>' + escapeHtml(item) + '</li>').join('') +
        '</ul></div>';
    }

    function renderRootCauses(items) {
      if (!items.length) {
        return '';
      }
      return '<div class="insight-list"><h3>Root Cause Hypotheses</h3><ul>' +
        items.slice(0, 5).map((item) => {
          const label = typeof item === 'string' ? item : `${item.confidence || ''}: ${item.title || item.hypothesis || ''}`;
          return '<li>' + escapeHtml(label) + '</li>';
        }).join('') +
        '</ul></div>';
    }

    function renderArchitectAssessment(assessment) {
      if (!assessment) {
        return '';
      }
      const material = assessment.material_risks || [];
      const risks = material.slice(0, 4).map((risk) => {
        const affected = risk.affected_count ? ` (${risk.affected_count} affected)` : '';
        return '<li><strong>' + escapeHtml(risk.severity || '') + '</strong>: ' +
          escapeHtml(risk.title || '') + escapeHtml(affected) + '</li>';
      }).join('');
      return '<div class="insight-list"><h3>Architect Assessment</h3><ul>' +
        '<li><strong>Verdict:</strong> ' + escapeHtml(assessment.verdict || '') + '</li>' +
        '<li><strong>Confidence:</strong> ' + escapeHtml(assessment.confidence || '') + '</li>' +
        '<li><strong>Context:</strong> ' + escapeHtml(assessment.environment_context || '') + '</li>' +
        '<li><strong>Score:</strong> ' + escapeHtml(assessment.score_explanation || '') + '</li>' +
        (risks ? '<li><strong>Material risks:</strong><ul>' + risks + '</ul></li>' : '') +
        '</ul></div>';
    }

    function renderGroupedRisks(items) {
      if (!items.length) {
        return '';
      }
      return '<div class="insight-list"><h3>Grouped Root-Cause Risks</h3><ul>' +
        items.slice(0, 8).map((item) => {
          const affected = item.affected_count ? ` (${item.affected_count} affected)` : '';
          const category = item.business_category ? ` [${item.business_category}]` : '';
          const remediation = item.remediation_command ? '<br><span class="hint">' + escapeHtml(item.remediation_command) + '</span>' : '';
          return '<li><strong>' + escapeHtml(item.severity || '') + '</strong>: ' +
            escapeHtml(item.title || '') + escapeHtml(affected + category) + remediation + '</li>';
        }).join('') +
        '</ul></div>';
    }

    function renderBusinessCategories(categories) {
      const entries = Object.entries(categories);
      if (!entries.length) {
        return '';
      }
      return '<div class="insight-list"><h3>Business Risk Categories</h3><ul>' +
        entries.map(([name, data]) => '<li><strong>' + escapeHtml(name) + '</strong>: ' +
          escapeHtml(data.risk || '') + ' · ' + escapeHtml(data.risk_points ?? 0) +
          ' points · ' + escapeHtml(data.findings ?? 0) + ' grouped finding(s)</li>'
        ).join('') +
        '</ul></div>';
    }

    function renderIntelligenceContext(context) {
      if (!context.loaded) {
        return '';
      }
      const org = context.organization ? ` · ${context.organization}` : '';
      return '<div class="insight-list"><h3>Intelligence Context</h3><ul><li>' +
        'Loaded' + escapeHtml(org) +
        ' · environment ' + escapeHtml(context.environment || '-') +
        ' · ' + escapeHtml(context.topic_patterns || 0) + ' topic pattern(s)' +
        ' · ' + escapeHtml(context.rule_overrides || 0) + ' rule override(s)' +
        '</li></ul></div>';
    }

    function downloadReport() {
      if (!latestReport) {
        return;
      }
      const blob = new Blob([JSON.stringify(latestReport, null, 2)], {type: 'application/json'});
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'beacon-readiness-report.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
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

        request_id = f"{int(time.time() * 1000)}"
        started = time.monotonic()
        LOGGER.info("ui.request.start id=%s path=%s", request_id, self.path)
        try:
            LOGGER.info("ui.request.parse_multipart.start id=%s", request_id)
            fields, files = parse_multipart(self)
            LOGGER.info(
                "ui.request.parse_multipart.complete id=%s fields=%s files=%s",
                request_id,
                sorted(fields.keys()),
                sorted(files.keys()),
            )
            result = run_beacon_check(
                fields,
                files,
                force_kafka=self.path == "/api/kafka",
                request_id=request_id,
            )
            LOGGER.info(
                "ui.request.complete id=%s findings=%s elapsed=%.2fs",
                request_id,
                len(result.get("findings", [])),
                time.monotonic() - started,
            )
            self.respond_json(result)
        except Exception as error:
            LOGGER.exception(
                "ui.request.failed id=%s elapsed=%.2fs error=%s",
                request_id,
                time.monotonic() - started,
                error,
            )
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


def run_beacon_check(fields, files, force_kafka=False, request_id="local"):
    findings = []
    LOGGER.info(
        "ui.run.start id=%s force_kafka=%s fields=%s files=%s",
        request_id,
        force_kafka,
        sorted(fields.keys()),
        sorted(files.keys()),
    )

    if files.get("static_config"):
        LOGGER.info("ui.static.start id=%s path=%s", request_id, files["static_config"])
        findings.extend(scan_path(files["static_config"]))
        LOGGER.info("ui.static.complete id=%s findings=%s", request_id, len(findings))

    if files.get("runtime_snapshot"):
        before = len(findings)
        LOGGER.info(
            "ui.runtime_snapshot.start id=%s path=%s",
            request_id,
            files["runtime_snapshot"],
        )
        findings.extend(analyze_runtime_snapshot_file(files["runtime_snapshot"]))
        LOGGER.info(
            "ui.runtime_snapshot.complete id=%s added=%s",
            request_id,
            len(findings) - before,
        )

    if files.get("flow_snapshot"):
        before = len(findings)
        LOGGER.info("ui.flow.start id=%s path=%s", request_id, files["flow_snapshot"])
        findings.extend(analyze_flow_file(files["flow_snapshot"]))
        LOGGER.info(
            "ui.flow.complete id=%s added=%s", request_id, len(findings) - before
        )

    if files.get("prometheus_config"):
        before = len(findings)
        timeout = int(fields.get("prometheus_timeout") or 5)
        LOGGER.info(
            "ui.prometheus.start id=%s path=%s timeout=%s",
            request_id,
            files["prometheus_config"],
            timeout,
        )
        findings.extend(
            analyze_prometheus_config(
                files["prometheus_config"],
                timeout=timeout,
            )
        )
        LOGGER.info(
            "ui.prometheus.complete id=%s added=%s",
            request_id,
            len(findings) - before,
        )

    if files.get("opentelemetry_file"):
        before = len(findings)
        LOGGER.info(
            "ui.opentelemetry.start id=%s path=%s",
            request_id,
            files["opentelemetry_file"],
        )
        findings.extend(analyze_opentelemetry_file(files["opentelemetry_file"]))
        LOGGER.info(
            "ui.opentelemetry.complete id=%s added=%s",
            request_id,
            len(findings) - before,
        )

    if force_kafka or has_kafka_input(fields, files):
        before = len(findings)
        LOGGER.info("ui.kafka.start id=%s", request_id)
        findings.extend(run_kafka_collector(fields, files))
        LOGGER.info(
            "ui.kafka.complete id=%s added=%s", request_id, len(findings) - before
        )

    if files.get("kafka_acl_export"):
        before = len(findings)
        LOGGER.info(
            "ui.kafka_acls.start id=%s path=%s",
            request_id,
            files["kafka_acl_export"],
        )
        findings.extend(analyze_kafka_acl_file(files["kafka_acl_export"]))
        LOGGER.info(
            "ui.kafka_acls.complete id=%s added=%s",
            request_id,
            len(findings) - before,
        )

    if files.get("kafka_history"):
        before = len(findings)
        LOGGER.info(
            "ui.kafka_history.start id=%s path=%s",
            request_id,
            files["kafka_history"],
        )
        findings.extend(analyze_kafka_history_file(files["kafka_history"]))
        LOGGER.info(
            "ui.kafka_history.complete id=%s added=%s",
            request_id,
            len(findings) - before,
        )

    if fields.get("kubernetes_live") == "true":
        before = len(findings)
        LOGGER.info("ui.kubernetes.start id=%s", request_id)
        findings.extend(
            analyze_kubernetes_cluster(
                namespace=value_or_none(fields.get("kubernetes_namespace")),
                context=value_or_none(fields.get("kubernetes_context")),
                kubeconfig=files.get("kubernetes_kubeconfig"),
            )
        )
        LOGGER.info(
            "ui.kubernetes.complete id=%s added=%s",
            request_id,
            len(findings) - before,
        )

    LOGGER.info("ui.schema_registry.resolve.start id=%s", request_id)
    schema_registry_config = resolve_schema_registry_config(fields, files)
    if schema_registry_config:
        before = len(findings)
        timeout = int(fields.get("schema_registry_timeout") or 5)
        LOGGER.info(
            "ui.schema_registry.start id=%s path=%s timeout=%s",
            request_id,
            schema_registry_config,
            timeout,
        )
        findings.extend(
            analyze_schema_registry_config(
                schema_registry_config,
                timeout=timeout,
            )
        )
        LOGGER.info(
            "ui.schema_registry.complete id=%s added=%s",
            request_id,
            len(findings) - before,
        )
    else:
        LOGGER.info("ui.schema_registry.skipped id=%s", request_id)

    LOGGER.info("ui.policy.start id=%s findings=%s", request_id, len(findings))
    findings = apply_policy_to_findings(findings, load_policy())
    intelligence_context = load_intelligence_context(files.get("intelligence_context"))
    readiness_summary = calculate_readiness(
        findings,
        environment=value_or_none(fields.get("environment")),
        intelligence_context=intelligence_context,
    )
    displayed_findings = sort_findings(
        readiness_summary.get("interpreted_findings", [])
    )
    LOGGER.info(
        "ui.readiness.complete id=%s decision=%s score=%s",
        request_id,
        readiness_summary.get("production_decision"),
        readiness_summary.get("score"),
    )

    return {
        "score": readiness_summary["score"],
        "score_status": readiness_summary["score_status"],
        "readiness_summary": readiness_summary,
        "findings": displayed_findings,
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
        churn_samples=int(fields.get("churn_samples") or 1),
        churn_interval_seconds=float(fields.get("churn_interval_seconds") or 0),
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run Beacon local Kafka UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), BeaconUIHandler)
    print(f"Beacon Kafka UI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
