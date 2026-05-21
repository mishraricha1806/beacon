import typer

from beacon.scanner import scan_path
from beacon.reporter import print_report
from beacon.runtime_advisor import analyze_runtime_file

app = typer.Typer(help="Beacon - Production-readiness intelligence for modern infrastructure.")


@app.command()
def scan(
    path: str,
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser.")
):
    """Scan infrastructure configuration for production risks."""
    findings = scan_path(path)
    print_report(findings, html=html, open_report=open_report)


@app.command()
def runtime(
    path: str,
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser.")
):
    """Analyze runtime Kafka signals and recommend scale vs optimize vs code investigation."""
    findings = analyze_runtime_file(path)
    print_report(findings, html=html, open_report=open_report)


if __name__ == "__main__":
    app()