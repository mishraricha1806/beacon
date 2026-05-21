import typer

from beacon.scanner import scan_path
from beacon.reporter import print_report
from beacon.runtime_advisor import analyze_runtime_file

app = typer.Typer(help="Beacon - Production-readiness intelligence for modern infrastructure.")


@app.command()
def scan(path: str):
    """Scan infrastructure configuration for production risks."""
    findings = scan_path(path)
    print_report(findings)


@app.command()
def runtime(path: str):
    """Analyze runtime Kafka signals and recommend scale vs optimize vs code investigation."""
    findings = analyze_runtime_file(path)
    print_report(findings)


if __name__ == "__main__":
    app()