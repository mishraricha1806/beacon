# Add test to ensure HTML report renders rule_id and evidence

import os

from beacon.html_report import generate_html_report


def test_generate_html_includes_rule_id_and_evidence(tmp_path):
    findings = [
        {
            "severity": "HIGH",
            "title": "Kafka topic 'payments' has replication factor 1",
            "impact": "impact",
            "recommendation": "Use replication_factor=3",
            "file": "examples/kafka-topics.yaml",
            "rule_id": "kafka.topic.replication_factor.min",
            "evidence": {"path": "topics[0].replication_factor", "value": 1},
        }
    ]

    # Ensure reports output path does not conflict; generate will write reports/report.html
    generate_html_report(findings, score=42, open_report=False, readiness_summary=None)

    out_path = os.path.join("reports", "report.html")
    assert os.path.exists(out_path)

    with open(out_path, "r") as f:
        html = f.read()

    assert "kafka.topic.replication_factor.min" in html
    assert "topics[0].replication_factor" in html
