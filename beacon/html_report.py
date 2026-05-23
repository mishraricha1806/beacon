from jinja2 import Template
import os
import webbrowser

HTML_TEMPLATE = """
<html>
<head>
    <title>Beacon Report</title>
    <style>
        body {
            font-family: Arial;
            margin: 40px;
            background: #0f172a;
            color: white;
        }

        h1 {
            color: #38bdf8;
        }

        .score {
            font-size: 28px;
            margin-bottom: 20px;
        }

        .finding {
            border: 1px solid #334155;
            padding: 16px;
            margin-bottom: 16px;
            border-radius: 8px;
            background: #111827;
        }

        .CRITICAL { border-left: 6px solid #ef4444; }
        .HIGH { border-left: 6px solid #f97316; }
        .MEDIUM { border-left: 6px solid #eab308; }

    </style>
</head>
<body>

<h1>Beacon Infrastructure Report</h1>

<div class="score">
Production Readiness Score: <strong>{{ score }}/100</strong>
</div>

{% for finding in findings %}
<div class="finding {{ finding.severity }}">
    <h3>{{ finding.severity }} - {{ finding.title }}</h3>

    <p><strong>Impact:</strong> {{ finding.impact }}</p>

    <p><strong>Recommendation:</strong> {{ finding.recommendation }}</p>

    <p><strong>File:</strong> {{ finding.file }}</p>
</div>
{% endfor %}

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