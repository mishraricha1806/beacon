from rich.console import Console
from rich.table import Table

console = Console()


def print_readiness_summary(summary):
    console.print("\n[bold cyan]Beacon Production Readiness[/bold cyan]\n")

    if summary.get("score_status") == "BLOCKED_BY_ANALYSIS_ERROR":
        console.print(
            f"[bold]Production Readiness Score:[/bold] BLOCKED ({summary['score']}/100 raw signal score)"
        )
    else:
        console.print(
            f"[bold]Production Readiness Score:[/bold] {summary['score']}/100"
        )
    console.print(
        f"[bold]Operational Survivability:[/bold] {summary['survivability']}\n"
    )

    console.print(f"[bold]Business Summary:[/bold] {summary['business_summary']}")
    console.print(f"[bold]Recommended Action:[/bold] {summary['recommended_action']}\n")

    if summary.get("environment"):
        console.print(f"[bold]Environment:[/bold] {summary['environment']}")
    if summary.get("suppressed_duplicate_count"):
        console.print(
            "[bold]Grouped/Deduplicated Signals:[/bold] "
            f"{summary['suppressed_duplicate_count']} repeated derivative finding(s)"
        )
    if summary.get("raw_critical") is not None:
        console.print(
            "[bold]Raw Critical/High Before Interpretation:[/bold] "
            f"{summary['raw_critical']}/{summary['raw_high']}"
        )
    console.print()

    console.print(f"[bold]Critical Findings:[/bold] {summary['critical']}")
    console.print(f"[bold]High Findings:[/bold] {summary['high']}")
    console.print(f"[bold]Medium Findings:[/bold] {summary['medium']}")
    console.print(f"[bold]Low Findings:[/bold] {summary['low']}\n")
    if summary.get("error"):
        console.print(f"[bold]Error Findings:[/bold] {summary['error']}")
    console.print(f"[bold]Production Decision:[/bold] {summary['production_decision']}")
    console.print(f"[bold]Primary Risk Area:[/bold] {summary['primary_risk_area']}\n")

    if summary.get("grouped_risks"):
        grouped_table = Table(title="Grouped Root-Cause Risks")
        grouped_table.add_column("Severity")
        grouped_table.add_column("Risk")
        grouped_table.add_column("Affected")
        grouped_table.add_column("Examples")

        for risk in summary["grouped_risks"][:10]:
            grouped_table.add_row(
                risk["severity"],
                risk["title"],
                str(risk.get("affected_count", 0)),
                ", ".join(risk.get("examples", [])[:3]),
            )

        console.print(grouped_table)

    table = Table(title="Production Readiness Categories")
    table.add_column("Category")
    table.add_column("Risk")
    table.add_column("Finding Count")

    for category, data in summary["categories"].items():
        table.add_row(
            category.replace("_", " ").title(), data["risk"], str(data["findings"])
        )

    console.print("[bold]Top Reasons:[/bold]")
    for reason in summary["top_reasons"]:
        console.print(f"- {reason}")

    console.print("\n[bold]Next Best Actions:[/bold]")
    for action in summary["next_best_actions"]:
        console.print(f"- {action}")

    if summary.get("root_cause_hypotheses"):
        console.print("\n[bold]Root Cause Hypotheses:[/bold]")
        for hypothesis in summary["root_cause_hypotheses"][:3]:
            console.print(
                f"- {hypothesis['confidence']}: {hypothesis['title']} "
                f"(score {hypothesis['score']})"
            )

    if summary.get("kafka_report"):
        console.print("\n[bold]Kafka Readiness Sections:[/bold]")
        for section in summary["kafka_report"]["sections"]:
            counts = section["severity_counts"]
            console.print(
                f"- {section['title']}: {section['finding_count']} finding(s) "
                f"(Critical {counts.get('CRITICAL', 0)}, High {counts.get('HIGH', 0)}, "
                f"Medium {counts.get('MEDIUM', 0)})"
            )

    console.print()

    console.print(table)
