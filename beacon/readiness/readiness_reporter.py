from rich.console import Console
from rich.table import Table

console = Console()


def print_readiness_summary(summary):
    console.print("\n[bold cyan]Beacon Production Readiness[/bold cyan]\n")

    console.print(f"[bold]Production Readiness Score:[/bold] {summary['score']}/100")
    console.print(
        f"[bold]Operational Survivability:[/bold] {summary['survivability']}\n"
    )

    console.print(f"[bold]Business Summary:[/bold] {summary['business_summary']}")
    console.print(f"[bold]Recommended Action:[/bold] {summary['recommended_action']}\n")

    console.print(f"[bold]Critical Findings:[/bold] {summary['critical']}")
    console.print(f"[bold]High Findings:[/bold] {summary['high']}")
    console.print(f"[bold]Medium Findings:[/bold] {summary['medium']}")
    console.print(f"[bold]Low Findings:[/bold] {summary['low']}\n")
    console.print(f"[bold]Production Decision:[/bold] {summary['production_decision']}")
    console.print(f"[bold]Primary Risk Area:[/bold] {summary['primary_risk_area']}\n")

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

    console.print()

    console.print(table)
