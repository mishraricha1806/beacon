from rich.console import Console

console = Console()


def print_readiness_summary(summary):
    console.print("\n[bold cyan]Beacon Production Readiness[/bold cyan]\n")

    console.print(
        f"[bold]Production Readiness Score:[/bold] {summary['score']}/100"
    )

    console.print(
        f"[bold]Operational Survivability:[/bold] {summary['survivability']}"
    )

    console.print(
        f"[bold]Critical Findings:[/bold] {summary['critical']}"
    )

    console.print(
        f"[bold]High Findings:[/bold] {summary['high']}"
    )

    console.print(
        f"[bold]Medium Findings:[/bold] {summary['medium']}"
    )

    console.print(
        f"[bold]Low Findings:[/bold] {summary['low']}"
    )