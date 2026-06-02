from jinja2 import Template
import os
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
    {% else %}
    <div class="grid">
        <div class="card">
            <div class="metric">{{ score }}/100</div>
            <div class="label">Beacon Score</div>
        </div>
    </div>
    {% endif %}

    <div class="section">
        <h2>Detailed Findings</h2>

        {% if findings %}
            {% for finding in findings %}
            <div class="finding {{ finding.severity }}">
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


def generate_html_report(findings, score, open_report=True, readiness_summary=None):
    os.makedirs("reports", exist_ok=True)

    template = Template(HTML_TEMPLATE)

    # enrich findings with rule metadata when available for richer HTML
    enriched = []
    for f in findings:
        nf = dict(f)
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
        findings=enriched, score=score, readiness_summary=readiness_summary
    )

    output_path = "reports/report.html"

    with open(output_path, "w") as f:
        f.write(html_content)

    if open_report:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")
