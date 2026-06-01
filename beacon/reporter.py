import json

from rich.console import Console
from rich.table import Table

from beacon.html_report import generate_html_report
from beacon.readiness.interpretation import interpret_findings, sort_findings
from beacon.scoring import calculate_score

console = Console()


def print_report(
    findings, html=True, open_report=True, output="terminal", readiness_summary=None
):
    """Print or emit the report in a chosen format.

    readiness_summary: optional dict produced by readiness engines. When provided,
    the JSON and HTML outputs will include it for richer reports.
    """
    if readiness_summary:
        score = readiness_summary.get("score", calculate_score(findings))
        display_findings = interpret_findings(
            findings, environment=readiness_summary.get("environment")
        )["findings"]
    else:
        score = calculate_score(findings)
        display_findings = sort_findings(findings)

    score_status = (
        readiness_summary.get("score_status") if readiness_summary else "CALCULATED"
    )

    if output == "json":
        payload = {
            "score": score,
            "score_status": score_status,
            "readiness_summary": readiness_summary,
            "findings": display_findings,
        }

        console.print(json.dumps(payload, indent=2))
        return

    if score_status == "BLOCKED_BY_ANALYSIS_ERROR":
        console.print(
            f"\n[bold cyan]Beacon Production Readiness Score:[/bold cyan] BLOCKED ({score}/100 raw signal score)\n"
        )
    else:
        console.print(
            f"\n[bold cyan]Beacon Production Readiness Score:[/bold cyan] {score}/100\n"
        )

    if not display_findings:
        console.print("[green]No major production risks found.[/green]")

        if html:
            generate_html_report(
                display_findings,
                score,
                open_report=open_report,
                readiness_summary=readiness_summary,
            )

        return

    table = Table(title="Beacon Findings")

    table.add_column("Severity", style="bold")
    table.add_column("Issue")
    table.add_column("Impact")
    table.add_column("Recommendation")
    table.add_column("File")

    for f in display_findings:
        table.add_row(
            f["severity"], f["title"], f["impact"], f["recommendation"], f["file"]
        )

    console.print(table)

    if html:
        generate_html_report(
            display_findings,
            score,
            open_report=open_report,
            readiness_summary=readiness_summary,
        )
