import json

from rich.console import Console
from rich.table import Table

from beacon.html_report import generate_html_report

console = Console()


def calculate_score(findings):
    penalty = 0

    for f in findings:
        severity = f["severity"]

        if severity == "CRITICAL":
            penalty += 20
        elif severity == "HIGH":
            penalty += 12
        elif severity == "MEDIUM":
            penalty += 7
        elif severity == "LOW":
            penalty += 3
        elif severity == "ERROR":
            penalty += 5

    return max(0, 100 - penalty)


def print_report(findings, html=True, open_report=True, output="terminal", readiness_summary=None):
    """Print or emit the report in a chosen format.

    readiness_summary: optional dict produced by readiness engines. When provided,
    the JSON and HTML outputs will include it for richer reports.
    """
    score = calculate_score(findings)

    if output == "json":
        payload = {
            "score": score,
            "readiness_summary": readiness_summary,
            "findings": findings
        }

        console.print(json.dumps(payload, indent=2))
        return

    console.print(f"\n[bold cyan]Beacon Production Readiness Score:[/bold cyan] {score}/100\n")

    if not findings:
        console.print("[green]No major production risks found.[/green]")

        if html:
            generate_html_report(findings, score, open_report=open_report, readiness_summary=readiness_summary)

        return

    table = Table(title="Beacon Findings")

    table.add_column("Severity", style="bold")
    table.add_column("Issue")
    table.add_column("Impact")
    table.add_column("Recommendation")
    table.add_column("File")

    for f in findings:
        table.add_row(
            f["severity"],
            f["title"],
            f["impact"],
            f["recommendation"],
            f["file"]
        )

    console.print(table)

    if html:
        generate_html_report(findings, score, open_report=open_report, readiness_summary=readiness_summary)
