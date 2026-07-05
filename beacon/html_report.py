from jinja2 import Template
import os
import re
import webbrowser
from beacon.engine import metadata_registry as rules_registry

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Beacon Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            background: #0f172a;
            color: #e5e7eb;
            margin: 0;
            padding: 0;
        }

        .container {
            max-width: 1180px;
            margin: 0 auto;
            padding: 40px;
        }

        .header {
            margin-bottom: 32px;
        }

        .brand {
            color: #38bdf8;
            font-size: 34px;
            font-weight: 800;
            margin-bottom: 8px;
        }

        .subtitle {
            color: #94a3b8;
            font-size: 16px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.25);
        }

        .card h2, .card h3 {
            margin-top: 0;
            color: #f8fafc;
        }

        .release-gate {
            border-left: 6px solid #38bdf8;
            background: #0b1220;
        }

        .gate-answer {
            font-size: 38px;
            font-weight: 800;
            margin: 8px 0 10px;
        }

        .gate-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
            margin-top: 18px;
        }

        .gate-grid h3 {
            font-size: 16px;
        }

        .metric {
            font-size: 30px;
            font-weight: 800;
            color: #38bdf8;
        }

        .label {
            color: #94a3b8;
            font-size: 13px;
            margin-top: 6px;
        }

        .decision {
            font-size: 28px;
            font-weight: 800;
        }

        .NOT_READY, .CRITICAL_RISK, .CRITICAL {
            color: #ef4444;
        }

        .READY_WITH_MAJOR_RISKS, .HIGH_RISK, .HIGH {
            color: #f97316;
        }

        .READY_WITH_CONDITIONS, .MEDIUM_RISK, .MEDIUM {
            color: #eab308;
        }

        .READY, .LOW_RISK, .LOW {
            color: #22c55e;
        }

        .section {
            margin-bottom: 24px;
        }

        .finding {
            border-left: 6px solid #334155;
            background: #111827;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 14px;
            border-top: 1px solid #1f2937;
            border-right: 1px solid #1f2937;
            border-bottom: 1px solid #1f2937;
        }

        .finding.CRITICAL { border-left-color: #ef4444; }
        .finding.HIGH { border-left-color: #f97316; }
        .finding.MEDIUM { border-left-color: #eab308; }
        .finding.LOW { border-left-color: #22c55e; }
        .finding.ERROR { border-left-color: #a855f7; }

        .severity {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .finding-title {
            font-size: 18px;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 10px;
        }

        .muted {
            color: #94a3b8;
        }

        .evidence {
            margin-top: 8px;
            background: #0b1220;
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            color: #cbd5e1;
            border: 1px solid #1f2937;
        }

        .text-block {
            line-height: 1.6;
            color: #cbd5e1;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            overflow: hidden;
            border-radius: 12px;
        }

        th, td {
            border-bottom: 1px solid #1f2937;
            padding: 13px;
            text-align: left;
        }

        th {
            background: #1e293b;
            color: #cbd5e1;
            font-size: 13px;
        }

        td {
            background: #111827;
        }

        ul {
            padding-left: 22px;
            line-height: 1.7;
        }

        .pill {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            background: #1e293b;
            font-size: 12px;
            color: #cbd5e1;
            margin-right: 8px;
        }

        .incident-card {
            border-left: 6px solid #38bdf8;
            background: #0b1220;
        }

        .flow-path {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
            margin: 16px 0;
        }

        .flow-node {
            border: 1px solid #334155;
            background: #0b1220;
            border-radius: 10px;
            padding: 10px 12px;
            min-width: 120px;
        }

        .flow-node.bottleneck {
            border-color: #ef4444;
            box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.18);
        }

        .flow-node-title {
            color: #f8fafc;
            font-weight: 800;
            font-size: 13px;
        }

        .flow-node-meta {
            color: #94a3b8;
            font-size: 12px;
            margin-top: 4px;
        }

        .flow-arrow {
            color: #64748b;
            font-weight: 800;
        }

        .flow-evidence-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin: 12px 0 18px;
        }

        .flow-evidence-card {
            background: #0b1220;
            border: 1px solid #1f2937;
            border-radius: 10px;
            padding: 12px;
        }

        .flow-evidence-card h4 {
            margin: 0 0 8px;
            color: #f8fafc;
            font-size: 13px;
        }

        .source-findings {
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid #1f2937;
        }

        .source-findings a {
            color: #93c5fd;
            text-decoration: none;
        }

        .source-findings a:hover {
            text-decoration: underline;
        }

        .decision-grid-report {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 14px;
        }

        .decision-card-report {
            border: 1px solid #1f2937;
            border-left: 5px solid #38bdf8;
            background: #0b1220;
            border-radius: 10px;
            padding: 14px;
        }

        .decision-card-report h3 {
            margin: 0 0 8px;
            color: #f8fafc;
            font-size: 16px;
        }

        .decision-card-report .decision-action {
            color: #cbd5e1;
            margin: 8px 0;
        }

        .decision-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 8px 0;
        }

        .decision-chip-row span {
            border: 1px solid #334155;
            border-radius: 999px;
            color: #94a3b8;
            padding: 4px 8px;
            font-size: 12px;
        }

        .incident-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
        }

        @media (max-width: 860px) {
            .incident-grid, .gate-grid, .flow-evidence-grid, .decision-grid-report {
                grid-template-columns: 1fr;
            }
        }

        .footer {
            margin-top: 40px;
            color: #64748b;
            font-size: 13px;
        }
    </style>
</head>

<body>
<div class="container">

    <div class="header">
        <div class="brand">Beacon</div>
        <div class="subtitle">Production-readiness and operational intelligence report</div>
    </div>

    {% if readiness_summary %}
    {% if readiness_summary.release_gate %}
    <div class="card section release-gate">
        <h2>{{ readiness_summary.release_gate.question }}</h2>
        <div class="gate-answer {{ readiness_summary.production_decision.replace(' ', '_') }}">
            {{ readiness_summary.release_gate.answer }}
        </div>
        <p class="text-block">
            <strong>Production Decision:</strong> {{ readiness_summary.release_gate.decision }}
            · <strong>Score:</strong> {{ readiness_summary.release_gate.score }}/100
        </p>
        <p class="text-block">
            <strong>Business Risk:</strong> {{ readiness_summary.release_gate.business_risk }}
        </p>
        <div class="gate-grid">
            <div>
                <h3>Why Not?</h3>
                <ul>
                    {% for reason in readiness_summary.release_gate.why_not %}
                    <li>{{ reason }}</li>
                    {% endfor %}
                </ul>
            </div>
            <div>
                <h3>Fix First</h3>
                <ul>
                    {% for action in readiness_summary.release_gate.fix_first %}
                    <li>{{ action }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
    </div>
    {% endif %}

    {% if readiness_summary.release_evidence and readiness_summary.release_evidence.production_blockers %}
    <div class="card section">
        <h2>{{ readiness_summary.release_evidence.production_blockers.question }}</h2>
        <p class="text-block">
            <strong>Status:</strong> {{ readiness_summary.release_evidence.production_blockers.status }}
            · <strong>Decision:</strong> {{ readiness_summary.release_evidence.production_blockers.decision }}
            · <strong>Score:</strong> {{ readiness_summary.release_evidence.production_blockers.score }}/100
        </p>
        {% if readiness_summary.release_evidence.production_blockers.blockers %}
        <h3>Blockers</h3>
        <ul>
            {% for blocker in readiness_summary.release_evidence.production_blockers.blockers %}
            <li>
                <strong class="{{ blocker.severity }}">{{ blocker.severity }}</strong>:
                {{ blocker.title }}
                {% if blocker.affected_count %}({{ blocker.affected_count }} affected){% endif %}
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <p class="text-block"><strong>Blockers:</strong> none</p>
        {% endif %}

        {% if readiness_summary.release_evidence.production_blockers.fix_first %}
        <h3>Fix First</h3>
        <ul>
            {% for action in readiness_summary.release_evidence.production_blockers.fix_first %}
            <li>{{ action }}</li>
            {% endfor %}
        </ul>
        {% endif %}

        {% if readiness_summary.release_evidence.production_blockers.business_impact %}
        <p class="text-block">
            <strong>Business Impact:</strong>
            {{ readiness_summary.release_evidence.production_blockers.business_impact }}
        </p>
        {% endif %}
    </div>
    {% endif %}

    <div class="grid">
        <div class="card">
            <div class="metric">{{ readiness_summary.score }}/100</div>
            <div class="label">Production Readiness Score</div>
        </div>

        <div class="card">
            <div class="decision {{ readiness_summary.production_decision.replace(' ', '_') }}">
                {{ readiness_summary.production_decision }}
            </div>
            <div class="label">Production Decision</div>
        </div>

        <div class="card">
            <div class="decision {{ readiness_summary.survivability.replace(' ', '_') }}">
                {{ readiness_summary.survivability }}
            </div>
            <div class="label">Operational Survivability</div>
        </div>

        <div class="card">
            <div class="metric">{{ readiness_summary.primary_risk_area }}</div>
            <div class="label">Primary Risk Area</div>
        </div>

        <div class="card">
            <div class="metric">{{ readiness_summary.risk_points }}</div>
            <div class="label">Weighted Risk Points</div>
        </div>
    </div>

    <div class="card section">
        <h2>Executive Summary</h2>
        <p class="text-block"><strong>Business Summary:</strong> {{ readiness_summary.business_summary }}</p>
        <p class="text-block"><strong>Recommended Action:</strong> {{ readiness_summary.recommended_action }}</p>

        <p>
            <span class="pill">Critical: {{ readiness_summary.critical }}</span>
            <span class="pill">High: {{ readiness_summary.high }}</span>
            <span class="pill">Medium: {{ readiness_summary.medium }}</span>
            <span class="pill">Low: {{ readiness_summary.low }}</span>
            <span class="pill">Environment: {{ readiness_summary.environment }}</span>
        </p>
        {% if readiness_summary.intelligence_context.loaded %}
        <p class="text-block">
            <strong>Intelligence Context:</strong>
            {{ readiness_summary.intelligence_context.organization or 'Loaded' }}
            · topic patterns: {{ readiness_summary.intelligence_context.topic_patterns }}
            · rule overrides: {{ readiness_summary.intelligence_context.rule_overrides }}
        </p>
        {% endif %}
        <p class="muted">Scoring model: {{ readiness_summary.score_formula }}</p>
    </div>

    {% if readiness_summary.operational_decisions %}
    <div class="card section">
        <h2>Operational Decisions</h2>
        <div class="decision-grid-report">
            {% for decision in readiness_summary.operational_decisions[:5] %}
            <div class="decision-card-report">
                <h3>#{{ decision.rank }} · {{ decision.decision_label or decision.target }}</h3>
                <div class="decision-chip-row">
                    <span>{{ decision.disposition }}</span>
                    <span>{{ decision.safety }}</span>
                    <span>{{ decision.confidence }}</span>
                    <span>{{ decision.decision_type }}</span>
                </div>
                <p class="decision-action"><strong>Action:</strong> {{ decision.action }}</p>
                {% if decision.why %}
                <p class="text-block"><strong>Why:</strong> {{ decision.why }}</p>
                {% endif %}
                {% if decision.evidence_required %}
                <strong>Evidence Required</strong>
                <ul>
                    {% for item in decision.evidence_required[:4] %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
                {% if decision.do_not_do %}
                <strong>Do Not Do</strong>
                <ul>
                    {% for item in decision.do_not_do[:3] %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
                {% if decision.source_rule_ids %}
                <p class="muted"><strong>Source Rules:</strong> {{ decision.source_rule_ids | join(', ') }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    {% if readiness_summary.distributed_system_readiness %}
    <div class="card section">
        <h2>{{ readiness_summary.distributed_system_readiness.title }}</h2>
        <p class="text-block">
            <strong>Verdict:</strong> {{ readiness_summary.distributed_system_readiness.verdict }}
        </p>
        <p class="text-block">
            <strong>Confidence:</strong> {{ readiness_summary.distributed_system_readiness.confidence }}
        </p>
        {% if readiness_summary.distributed_system_readiness.domains_observed %}
        <p class="text-block">
            <strong>Domains Observed:</strong>
            {{ readiness_summary.distributed_system_readiness.domains_observed | join(', ') }}
        </p>
        {% endif %}
        {% if readiness_summary.distributed_system_readiness.critical_paths %}
        <h3>Critical Paths</h3>
        <ul>
            {% for path in readiness_summary.distributed_system_readiness.critical_paths %}
            <li>{{ path }}</li>
            {% endfor %}
        </ul>
        {% endif %}
        <table>
            <tr>
                <th>Dimension</th>
                <th>Status</th>
                <th>Max Severity</th>
                <th>Findings</th>
            </tr>
            {% for dimension in readiness_summary.distributed_system_readiness.dimensions %}
            <tr>
                <td>{{ dimension.title }}</td>
                <td>{{ dimension.status }}</td>
                <td>{{ dimension.max_severity }}</td>
                <td>{{ dimension.finding_count }}</td>
            </tr>
            {% endfor %}
        </table>
        {% if readiness_summary.distributed_system_readiness.coverage_gaps %}
        <h3>Coverage Gaps</h3>
        <ul>
            {% for gap in readiness_summary.distributed_system_readiness.coverage_gaps %}
            <li>{{ gap }}</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
    {% endif %}

    {% if readiness_summary.business_categories %}
    <div class="card section">
        <h2>Business Risk Categories</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Risk</th>
                <th>Risk Points</th>
                <th>Grouped Findings</th>
            </tr>

            {% for category, data in readiness_summary.business_categories.items() %}
            <tr>
                <td>{{ category }}</td>
                <td class="{{ data.risk.replace(' ', '_') }}">{{ data.risk }}</td>
                <td>{{ data.risk_points }}</td>
                <td>{{ data.findings }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}

    {% if readiness_summary.architect_assessment %}
    <div class="card section">
        <h2>Architect Assessment</h2>
        <p class="text-block"><strong>Verdict:</strong> {{ readiness_summary.architect_assessment.verdict }}</p>
        <p class="text-block"><strong>Confidence:</strong> {{ readiness_summary.architect_assessment.confidence }}</p>
        <p class="text-block"><strong>Context:</strong> {{ readiness_summary.architect_assessment.environment_context }}</p>
        <p class="text-block"><strong>Score:</strong> {{ readiness_summary.architect_assessment.score_explanation }}</p>

        {% if readiness_summary.architect_assessment.material_risks %}
        <h3>Material Risks</h3>
        <ul>
            {% for risk in readiness_summary.architect_assessment.material_risks %}
            <li><strong>{{ risk.severity }}</strong>: {{ risk.title }} ({{ risk.affected_count }} affected)</li>
            {% endfor %}
        </ul>
        {% endif %}

        {% if readiness_summary.architect_assessment.investigate_now %}
        <h3>Investigate Now</h3>
        <ul>
            {% for risk in readiness_summary.architect_assessment.investigate_now %}
            <li><strong>{{ risk.severity }}</strong>: {{ risk.title }} ({{ risk.affected_count }} affected)</li>
            {% endfor %}
        </ul>
        {% endif %}

        {% if readiness_summary.architect_assessment.context_gaps %}
        <h3>Context Gaps</h3>
        <ul>
            {% for gap in readiness_summary.architect_assessment.context_gaps %}
            <li>{{ gap }}</li>
            {% endfor %}
        </ul>
        {% endif %}

        {% if readiness_summary.architect_assessment.accepted_assumptions %}
        <h3>Accepted Assumptions</h3>
        <ul>
            {% for assumption in readiness_summary.architect_assessment.accepted_assumptions %}
            <li>{{ assumption }}</li>
            {% endfor %}
        </ul>
        {% endif %}

        {% if readiness_summary.architect_assessment.deemphasized_signals %}
        <h3>De-emphasized Signals</h3>
        <ul>
            {% for risk in readiness_summary.architect_assessment.deemphasized_signals %}
            <li><strong>{{ risk.severity }}</strong>: {{ risk.title }} ({{ risk.affected_count }} affected)</li>
            {% endfor %}
        </ul>
        {% endif %}
    </div>
    {% endif %}

    <div class="card section">
        <h2>Top Reasons</h2>
        <ul>
            {% for reason in readiness_summary.top_reasons %}
            <li>{{ reason }}</li>
            {% endfor %}
        </ul>
    </div>

    <div class="card section">
        <h2>Next Best Actions</h2>
        <ul>
            {% for action in readiness_summary.next_best_actions %}
            <li>{{ action }}</li>
            {% endfor %}
        </ul>
    </div>

    <div class="card section">
        <h2>Readiness Categories</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Risk</th>
                <th>Findings</th>
            </tr>

            {% for category, data in readiness_summary.categories.items() %}
            <tr>
                <td>{{ category.replace("_", " ").title() }}</td>
                <td class="{{ data.risk.replace(' ', '_') }}">{{ data.risk }}</td>
                <td>{{ data.findings }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    {% if readiness_summary.kafka_report %}
    <div class="card section">
        <h2>{{ readiness_summary.kafka_report.title }}</h2>
        <p class="text-block">Kafka findings are grouped by operational ownership so teams can route remediation faster.</p>

        {% for section in readiness_summary.kafka_report.sections %}
        <div class="finding">
            <div class="finding-title">{{ section.title }}</div>
            <p class="muted">
                Findings: {{ section.finding_count }}
                · Critical: {{ section.severity_counts.CRITICAL }}
                · High: {{ section.severity_counts.HIGH }}
                · Medium: {{ section.severity_counts.MEDIUM }}
            </p>
            <p class="text-block"><strong>Recommended Action:</strong> {{ section.recommended_action }}</p>
            <ul>
                {% for finding in section.top_findings %}
                <li><strong>{{ finding.severity }}</strong>: {{ finding.title }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if readiness_summary.grouped_risks %}
    <div class="card section">
        <h2>Grouped Root-Cause Risks</h2>
        <p class="text-block">
            Beacon groups repeated derivative findings so the report shows the highest-signal operational risks first.
            Environment: <strong>{{ readiness_summary.environment }}</strong>.
        </p>

        {% for risk in readiness_summary.grouped_risks %}
        <div class="finding {{ risk.severity }}">
            <div class="severity {{ risk.severity }}">{{ risk.severity }}</div>
            <div class="finding-title">{{ risk.title }}</div>
            <p class="text-block"><strong>Category:</strong> {{ risk.business_category }}</p>
            <p class="text-block"><strong>Affected:</strong> {{ risk.affected_count }}</p>
            <p class="text-block"><strong>Recommendation:</strong> {{ risk.recommendation }}</p>
            {% if risk.remediation_command %}
            <p class="text-block"><strong>Remediation Command:</strong> <code>{{ risk.remediation_command }}</code></p>
            {% endif %}
            {% if risk.examples %}
            <p class="muted"><strong>Examples:</strong> {{ risk.examples[:5] | join(', ') }}</p>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}
    {% elif not diagnostic_summary %}
    <div class="grid">
        <div class="card">
            <div class="metric">{{ score }}/100</div>
            <div class="label">Beacon Score</div>
        </div>
    </div>
    {% endif %}

    {% if diagnostic_summary %}
    {% if diagnostic_summary.incident_diagnosis %}
    <div class="card section incident-card">
        <h2>Incident Diagnosis</h2>
        <p class="text-block">
            <strong>Primary Likely Cause:</strong>
            {{ diagnostic_summary.incident_diagnosis.title }}
        </p>
        <p class="text-block">
            <strong>Confidence:</strong>
            {{ diagnostic_summary.incident_diagnosis.confidence }}
        </p>
        {% if diagnostic_summary.incident_diagnosis.evidence_quality %}
        <p class="text-block">
            <strong>Evidence Quality:</strong>
            {{ diagnostic_summary.incident_diagnosis.evidence_quality.status }}
            ({{ diagnostic_summary.incident_diagnosis.evidence_quality.score }}/100)
            · {{ diagnostic_summary.incident_diagnosis.evidence_quality.reason }}
        </p>
        {% endif %}
        <p class="text-block">
            <strong>Summary:</strong>
            {{ diagnostic_summary.incident_diagnosis.summary }}
        </p>
        {% if diagnostic_summary.incident_diagnosis.recommendation %}
        <p class="text-block">
            <strong>Recommendation:</strong>
            {{ diagnostic_summary.incident_diagnosis.recommendation }}
        </p>
        {% endif %}
        <div class="incident-grid">
            <div>
                <h3>Why Beacon Thinks This</h3>
                <ul>
                    {% for evidence in diagnostic_summary.incident_diagnosis.evidence %}
                    <li>{{ evidence }}</li>
                    {% endfor %}
                </ul>
            </div>
            <div>
                <h3>What To Do First</h3>
                <ul>
                    {% for action in diagnostic_summary.incident_diagnosis.first_actions %}
                    <li>{{ action }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        {% if diagnostic_summary.incident_diagnosis.missing_evidence %}
        <h3>Evidence Still Needed</h3>
        <ul>
            {% for gap in diagnostic_summary.incident_diagnosis.missing_evidence %}
            <li>{{ gap }}</li>
            {% endfor %}
        </ul>
        {% endif %}
        {% if diagnostic_summary.incident_diagnosis.runbook %}
        <h3>{{ diagnostic_summary.incident_diagnosis.runbook.title }}</h3>
        <div class="incident-grid">
            <div>
                <h3>Check First</h3>
                <ul>
                    {% for step in diagnostic_summary.incident_diagnosis.runbook.check_first %}
                    <li>{{ step }}</li>
                    {% endfor %}
                </ul>
            </div>
            <div>
                <h3>Safe Actions</h3>
                <ul>
                    {% for step in diagnostic_summary.incident_diagnosis.runbook.safe_actions %}
                    <li>{{ step }}</li>
                    {% endfor %}
                </ul>
            </div>
            <div>
                <h3>Avoid</h3>
                <ul>
                    {% for step in diagnostic_summary.incident_diagnosis.runbook.avoid %}
                    <li>{{ step }}</li>
                    {% endfor %}
                </ul>
            </div>
            <div>
                <h3>Evidence To Collect</h3>
                <ul>
                    {% for step in diagnostic_summary.incident_diagnosis.runbook.evidence_to_collect %}
                    <li>{{ step }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        {% endif %}
    </div>
    {% endif %}

    <div class="card section">
        <h2>Runtime Diagnosis</h2>
        <p class="text-block"><strong>Status:</strong> {{ diagnostic_summary.diagnostic_status }}</p>
        <p class="text-block"><strong>Summary:</strong> {{ diagnostic_summary.executive_summary }}</p>

        {% if diagnostic_summary.scope and diagnostic_summary.scope.kafka_consumer_group_scope %}
        <div class="evidence">
            <strong>Scoped Kafka Consumer Group Diagnosis</strong>
            <p><strong>Consumer Group:</strong> {{ diagnostic_summary.scope.kafka_consumer_group_scope.consumer_group }}</p>
            <p><strong>Status:</strong> {{ diagnostic_summary.scope.kafka_consumer_group_scope.status }}</p>
            <p><strong>Topic Scope:</strong> {{ diagnostic_summary.scope.kafka_consumer_group_scope.topic_scope }}</p>
            <p>{{ diagnostic_summary.scope.kafka_consumer_group_scope.summary }}</p>
        </div>
        {% endif %}

        {% if diagnostic_summary.primary_hypothesis %}
        <p class="text-block">
            <strong>Primary Hypothesis:</strong>
            {{ diagnostic_summary.primary_hypothesis.confidence }} -
            {{ diagnostic_summary.primary_hypothesis.title }}
        </p>
        <p class="text-block"><strong>Recommendation:</strong> {{ diagnostic_summary.primary_hypothesis.recommendation }}</p>
        {% endif %}

        {% if diagnostic_summary.first_actions %}
        <h3>First Actions</h3>
        <ul>
            {% for action in diagnostic_summary.first_actions %}
            <li>{{ action }}</li>
            {% endfor %}
        </ul>
        {% endif %}

        {% if diagnostic_summary.operational_decisions %}
        <h3>Runtime Operational Decisions</h3>
        <div class="decision-grid-report">
            {% for decision in diagnostic_summary.operational_decisions[:5] %}
            <div class="decision-card-report">
                <h3>#{{ decision.rank }} · {{ decision.decision_label or decision.target }}</h3>
                <div class="decision-chip-row">
                    <span>{{ decision.disposition }}</span>
                    <span>{{ decision.safety }}</span>
                    <span>{{ decision.confidence }}</span>
                    <span>{{ decision.decision_type }}</span>
                </div>
                <p class="decision-action"><strong>Action:</strong> {{ decision.action }}</p>
                {% if decision.why %}
                <p class="text-block"><strong>Why:</strong> {{ decision.why }}</p>
                {% endif %}
                {% if decision.evidence_required %}
                <strong>Evidence Required</strong>
                <ul>
                    {% for item in decision.evidence_required[:4] %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
                {% if decision.do_not_do %}
                <strong>Do Not Do</strong>
                <ul>
                    {% for item in decision.do_not_do[:3] %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
                {% if decision.source_rule_ids %}
                <p class="muted"><strong>Source Rules:</strong> {{ decision.source_rule_ids | join(', ') }}</p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% if diagnostic_summary.diagnostic_playbooks %}
        <h3>Matched Diagnostic Playbooks</h3>
        <table>
            <tr>
                <th>Module</th>
                <th>Use Case</th>
                <th>Confidence</th>
                <th>Evidence Still Needed</th>
            </tr>
            {% for playbook in diagnostic_summary.diagnostic_playbooks %}
            <tr>
                <td>{{ playbook.module }}</td>
                <td>{{ playbook.title }}</td>
                <td>{{ playbook.confidence }}</td>
                <td>{{ playbook.evidence_needed | join(', ') if playbook.evidence_needed else 'None' }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}

        {% if diagnostic_summary.consumer_group_diagnoses %}
        <h3>Kafka Consumer Group Diagnosis</h3>
        <table>
            <tr>
                <th>Consumer Group</th>
                <th>Status</th>
                <th>Likely Cause</th>
                <th>Confidence</th>
                <th>Evidence Quality</th>
                <th>Total Lag</th>
                <th>Evidence Missing</th>
            </tr>
            {% for diagnosis in diagnostic_summary.consumer_group_diagnoses %}
            <tr>
                <td>{{ diagnosis.consumer_group }}</td>
                <td>{{ diagnosis.status }}</td>
                <td>{{ diagnosis.primary_likely_cause }}</td>
                <td>{{ diagnosis.confidence }}</td>
                <td>
                    {% if diagnosis.evidence_quality %}
                    {{ diagnosis.evidence_quality.status }} ({{ diagnosis.evidence_quality.score }}/100)
                    {% else %}
                    unknown
                    {% endif %}
                </td>
                <td>{{ diagnosis.total_lag or 'unknown' }}</td>
                <td>{{ diagnosis.evidence_missing | join(', ') if diagnosis.evidence_missing else 'None' }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}

        {% if diagnostic_summary.flow_bottleneck_rankings %}
        <h3>Flow Bottleneck Ranking</h3>
        {% for ranking in diagnostic_summary.flow_bottleneck_rankings %}
        <p class="text-block">
            <strong>Flow:</strong> {{ ranking.flow }}
            · <strong>Top Bottleneck:</strong> {{ ranking.top_bottleneck }}
            · <strong>Confidence:</strong> {{ ranking.top_confidence }}
            · <strong>Priority:</strong> {{ ranking.incident_priority or '-' }}
            · <strong>Owner:</strong> {{ ranking.owner or 'unknown' }}
            · <strong>Criticality:</strong> {{ ranking.criticality or 'unknown' }}
        </p>
        {% if ranking.business_impact or ranking.affected_services %}
        <p class="text-block">
            {% if ranking.business_impact %}
            <strong>Business Impact:</strong> {{ ranking.business_impact }}
            {% endif %}
            {% if ranking.affected_services %}
            · <strong>Blast Radius:</strong> {{ ranking.affected_services | join(', ') }}
            {% endif %}
        </p>
        {% endif %}
        {% if ranking.flow_path %}
        <div class="flow-path" aria-label="Flow path">
            {% for node in ranking.flow_path %}
            <div class="flow-node {% if node.is_bottleneck %}bottleneck{% endif %}">
                <div class="flow-node-title">{{ node.label }}</div>
                <div class="flow-node-meta">
                    {{ node.status }} · {{ node.confidence }}
                    {% if node.is_bottleneck %} · bottleneck{% endif %}
                </div>
            </div>
            {% if not loop.last %}
            <div class="flow-arrow">→</div>
            {% endif %}
            {% endfor %}
        </div>
        <h4>Flow Path Evidence</h4>
        {% for node in ranking.flow_path %}
        <div class="flow-evidence-grid">
            <div class="flow-evidence-card">
                <h4>{{ node.label }}{% if node.is_bottleneck %} · Bottleneck{% endif %}</h4>
                <p class="muted">{{ node.status }} · {{ node.confidence }}</p>
                {% if node.source_findings %}
                <div class="source-findings">
                    <h4>Source Findings</h4>
                    <ul>
                        {% for source in node.source_findings %}
                        <li>
                            {% if source.anchor %}
                            <a href="#{{ source.anchor }}">{{ source.severity }} · {{ source.rule_id }}</a>
                            {% else %}
                            {{ source.severity }} · {{ source.rule_id }}
                            {% endif %}
                            {% if source.file %}
                            <br><span class="muted">{{ source.file }}</span>
                            {% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>
            <div class="flow-evidence-card">
                <h4>Evidence Used</h4>
                <ul>
                    {% for item in node.evidence_used %}
                    <li>{{ item }}</li>
                    {% else %}
                    <li>No direct evidence attached to this node.</li>
                    {% endfor %}
                </ul>
            </div>
            <div class="flow-evidence-card">
                <h4>Evidence Missing</h4>
                <ul>
                    {% for item in node.evidence_missing %}
                    <li>{{ item }}</li>
                    {% else %}
                    <li>No missing evidence listed.</li>
                    {% endfor %}
                </ul>
            </div>
            <div class="flow-evidence-card">
                <h4>Inspect Next</h4>
                <ul>
                    {% for item in node.inspect_next %}
                    <li>{{ item }}</li>
                    {% else %}
                    <li>No next inspection guidance listed.</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        {% endfor %}
        {% endif %}
        <table>
            <tr>
                <th>Rank</th>
                <th>Component</th>
                <th>Type</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Reason</th>
            </tr>
            {% for component in ranking.components %}
            <tr>
                <td>{{ component.rank }}</td>
                <td>{{ component.component }}</td>
                <td>{{ component.component_type }}</td>
                <td>{{ component.confidence }}</td>
                <td>{{ component.status }}</td>
                <td>{{ component.reason }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endfor %}
        {% endif %}

        {% if diagnostic_summary.deployment_window_analyses %}
        <h3>Before / After Deployment</h3>
        {% for analysis in diagnostic_summary.deployment_window_analyses %}
        <p class="text-block">
            <strong>Service:</strong> {{ analysis.service }}
            · <strong>Version:</strong> {{ analysis.version or '-' }}
            · <strong>Deployed:</strong> {{ analysis.deployed_at or '-' }}
        </p>
        <table>
            <tr>
                <th>Metric</th>
                <th>Before</th>
                <th>After</th>
                <th>Delta</th>
                <th>Ratio</th>
                <th>Severity</th>
                <th>Tuned Severity</th>
                <th>Tuning Reason</th>
            </tr>
            {% for metric in analysis.metrics %}
            <tr>
                <td>{{ metric.metric }}</td>
                <td>{{ metric.before }}</td>
                <td>{{ metric.after }}</td>
                <td>{{ metric.delta }}</td>
                <td>{{ metric.ratio }}</td>
                <td>{{ metric.severity }}</td>
                <td>{{ metric.tuned_severity }}</td>
                <td>{{ metric.tuning_reason }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endfor %}
        {% endif %}

        {% if diagnostic_summary.telemetry_gaps %}
        <h3>Telemetry Gaps</h3>
        <ul>
            {% for gap in diagnostic_summary.telemetry_gaps %}
            <li>{{ gap }}</li>
            {% endfor %}
        </ul>
        {% endif %}

        {% if diagnostic_summary.affected_domains %}
        <h3>Affected Domains</h3>
        <table>
            <tr>
                <th>Domain</th>
                <th>Max Severity</th>
                <th>Findings</th>
            </tr>
            {% for domain in diagnostic_summary.affected_domains %}
            <tr>
                <td>{{ domain.domain }}</td>
                <td>{{ domain.max_severity }}</td>
                <td>{{ domain.findings }}</td>
            </tr>
            {% endfor %}
        </table>
        {% endif %}
    </div>
    {% endif %}

    <div class="section">
        <h2>Detailed Findings</h2>

        {% if findings %}
            {% for finding in findings %}
            <div class="finding {{ finding.severity }}" id="{{ finding.anchor }}">
                <div class="severity {{ finding.severity }}">{{ finding.severity }}</div>
                <div class="finding-title">{{ finding.title }}</div>
                {% if finding.rule_id %}
                <div class="muted">Rule: <strong>{{ finding.rule_id }}</strong></div>
                {% endif %}
                                <p class="text-block"><strong>Impact:</strong> {{ finding.impact }}</p>
                <p class="text-block"><strong>Recommendation:</strong> {{ finding.recommendation }}</p>
                <p class="muted"><strong>File:</strong> {{ finding.file }}</p>

                                {% if finding.evidence %}
                <div class="evidence">
                    <strong>Evidence</strong>
                    <ul>
                        {% for k, v in finding.evidence.items() %}
                        <li><span class="muted">{{ k }}:</span> {{ v }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}

                                {% if finding.rule_description %}
                                <div class="evidence">
                                    <strong>Rule description</strong>
                                    <p>{{ finding.rule_description }}</p>
                                    {% if finding.remediation_link %}
                                    <p><a href="{{ finding.remediation_link }}" target="_blank">Remediation</a></p>
                                    {% endif %}
                                    {% if finding.runbook_url %}
                                    <p><a href="{{ finding.runbook_url }}" target="_blank">Runbook</a></p>
                                    {% endif %}
                                </div>
                                {% endif %}
            </div>
            {% endfor %}
        {% else %}
            <div class="card">
                <p>No findings detected.</p>
            </div>
        {% endif %}
    </div>

    <div class="footer">
        Generated by Beacon. Read-only, deterministic-first operational intelligence.
    </div>

</div>
</body>
</html>
"""


def generate_html_report(
    findings,
    score,
    open_report=True,
    readiness_summary=None,
    diagnostic_summary=None,
):
    os.makedirs("reports", exist_ok=True)

    template = Template(HTML_TEMPLATE)

    # enrich findings with rule metadata when available for richer HTML
    enriched = []
    for f in findings:
        nf = dict(f)
        nf["anchor"] = finding_anchor_id(nf)
        rid = nf.get("rule_id")
        if rid:
            meta = rules_registry.get(rid) or {}
            # include optional metadata fields
            nf["rule_title"] = meta.get("title")
            nf["rule_description"] = meta.get("description")
            nf["remediation_link"] = meta.get("remediation_link")
            nf["runbook_url"] = meta.get("runbook_url")
        enriched.append(nf)

    html_content = template.render(
        findings=enriched,
        score=score,
        readiness_summary=readiness_summary,
        diagnostic_summary=diagnostic_summary,
    )

    output_path = "reports/report.html"

    with open(output_path, "w") as f:
        f.write(html_content)

    if open_report:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")


def finding_anchor_id(finding):
    base = "|".join(
        str(value or "")
        for value in (
            finding.get("rule_id"),
            finding.get("title"),
            finding.get("file"),
        )
    )
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-").lower()
    return f"finding-{slug or 'unknown'}"
