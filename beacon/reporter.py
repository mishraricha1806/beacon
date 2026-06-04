import json

from rich.console import Console
from rich.table import Table

from beacon.html_report import generate_html_report
from beacon.diagnose.diagnostic_engine import build_diagnostic_summary
from beacon.readiness.interpretation import interpret_findings, sort_findings
from beacon.scoring import calculate_score

console = Console()


def print_report(
    findings,
    html=True,
    open_report=True,
    output="terminal",
    readiness_summary=None,
    diagnostic_summary=None,
):
    """Print or emit the report in a chosen format.

    readiness_summary: optional dict produced by readiness engines. When provided,
    the JSON and HTML outputs will include it for richer reports.
    """
    if readiness_summary:
        score = readiness_summary.get("score", calculate_score(findings))
        display_findings = readiness_summary.get(
            "interpreted_findings"
        ) or sort_findings(
            interpret_findings(
                findings, environment=readiness_summary.get("environment")
            )["findings"]
        )
    else:
        score = calculate_score(findings)
        display_findings = sort_findings(findings)

    score_status = (
        readiness_summary.get("score_status") if readiness_summary else "CALCULATED"
    )
    if diagnostic_summary is None and readiness_summary is None:
        diagnostic_summary = None

    if output == "json":
        payload = {
            "score": score,
            "score_status": score_status,
            "readiness_summary": readiness_summary,
            "diagnostic_summary": diagnostic_summary,
            "findings": display_findings,
        }

        print(json.dumps(payload, indent=2))
        return

    if not diagnostic_summary or readiness_summary:
        if score_status == "BLOCKED_BY_ANALYSIS_ERROR":
            console.print(
                f"\n[bold cyan]Beacon Production Readiness Score:[/bold cyan] BLOCKED ({score}/100 raw signal score)\n"
            )
        else:
            console.print(
                f"\n[bold cyan]Beacon Production Readiness Score:[/bold cyan] {score}/100\n"
            )

    if diagnostic_summary:
        print_diagnostic_summary(diagnostic_summary)

    if not display_findings:
        console.print("[green]No major production risks found.[/green]")

        if html:
            generate_html_report(
                display_findings,
                score,
                open_report=open_report,
                readiness_summary=readiness_summary,
                diagnostic_summary=diagnostic_summary,
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
            diagnostic_summary=diagnostic_summary,
        )


def print_diagnostic_summary(summary):
    console.print("[bold cyan]Beacon Runtime Diagnosis[/bold cyan]\n")
    console.print(f"[bold]Status:[/bold] {summary['diagnostic_status']}")
    console.print(f"[bold]Summary:[/bold] {summary['executive_summary']}")

    primary = summary.get("primary_hypothesis")
    if primary:
        console.print(
            f"[bold]Primary Hypothesis:[/bold] {primary['confidence']} - {primary['title']}"
        )
        console.print(f"[bold]Recommendation:[/bold] {primary['recommendation']}")

    incident = summary.get("incident_diagnosis")
    if incident:
        console.print("\n[bold]Incident Diagnosis:[/bold]")
        console.print(
            f"- Primary likely cause: {incident.get('confidence')} - {incident.get('title')}"
        )
        if incident.get("summary"):
            console.print(f"- Summary: {incident['summary']}")
        if incident.get("recommendation"):
            console.print(f"- Recommendation: {incident['recommendation']}")
        if incident.get("evidence"):
            console.print("- Why Beacon thinks this:")
            for evidence in incident["evidence"][:4]:
                console.print(f"  - {evidence}")
        runbook = incident.get("runbook") or {}
        if runbook:
            console.print(f"- Runbook: {runbook.get('title')}")
            for step in (runbook.get("check_first") or [])[:3]:
                console.print(f"  - Check: {step}")

    if summary.get("affected_domains"):
        table = Table(title="Affected Runtime Domains")
        table.add_column("Domain")
        table.add_column("Max Severity")
        table.add_column("Findings")
        for domain in summary["affected_domains"]:
            table.add_row(
                domain["domain"],
                domain["max_severity"],
                str(domain["findings"]),
            )
        console.print(table)

    console.print("[bold]First Actions:[/bold]")
    for action in summary.get("first_actions", [])[:5]:
        console.print(f"- {action}")

    if summary.get("diagnostic_playbooks"):
        table = Table(title="Matched Diagnostic Playbooks")
        table.add_column("Module")
        table.add_column("Use Case")
        table.add_column("Confidence")
        table.add_column("Evidence Still Needed")
        for playbook in summary["diagnostic_playbooks"]:
            table.add_row(
                playbook["module"],
                playbook["title"],
                playbook["confidence"],
                ", ".join(playbook.get("evidence_needed") or ["None"]),
            )
        console.print(table)

    if summary.get("consumer_group_diagnoses"):
        table = Table(title="Kafka Consumer Group Diagnosis")
        table.add_column("Consumer Group")
        table.add_column("Status")
        table.add_column("Likely Cause")
        table.add_column("Confidence")
        table.add_column("Lag")
        table.add_column("Evidence Missing")
        for diagnosis in summary["consumer_group_diagnoses"]:
            table.add_row(
                diagnosis["consumer_group"],
                diagnosis["status"],
                diagnosis["primary_likely_cause"],
                diagnosis["confidence"],
                str(diagnosis.get("total_lag") or "unknown"),
                ", ".join(diagnosis.get("evidence_missing") or ["None"]),
            )
        console.print(table)

    console.print("\n[bold]Telemetry Gaps:[/bold]")
    for gap in summary.get("telemetry_gaps", [])[:5]:
        console.print(f"- {gap}")
    console.print()


def diagnostic_payload(findings):
    return build_diagnostic_summary(findings)
