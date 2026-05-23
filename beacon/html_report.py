from jinja2 import Template
import os
import webbrowser

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
        </p>
    </div>

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

    html_content = template.render(
        findings=findings,
        score=score,
        readiness_summary=readiness_summary
    )

    output_path = "reports/report.html"

    with open(output_path, "w") as f:
        f.write(html_content)

    if open_report:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")