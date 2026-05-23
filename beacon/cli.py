# Beacon runtime Kafka connector is read-only by design.
# Do NOT add produce, consume, alter, delete, offset-reset, or mutation operations here.
# Allowed operations:
# - list topic metadata
# - describe topic configs
# - describe cluster metadata
import typer

from beacon.scanner import scan_path
from beacon.reporter import print_report
from beacon.runtime_advisor import analyze_runtime_file
from beacon.kafka_runtime_connector import analyze_kafka_cluster

app = typer.Typer(
    help="Beacon - Operational intelligence for modern infrastructure."
)

diagnose_app = typer.Typer(
    help="Runtime operational diagnostics."
)

app.add_typer(
    diagnose_app,
    name="diagnose"
)


@app.command()
def scan(
    path: str,
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json.")
):
    """Scan infrastructure configuration for production risks."""
    findings = scan_path(path)

    print_report(
        findings,
        html=html,
        open_report=open_report,
        output=output
    )


@app.command()
def runtime(
    path: str,
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json.")
):
    """Analyze runtime snapshot YAML."""
    findings = analyze_runtime_file(path)

    print_report(
        findings,
        html=html,
        open_report=open_report,
        output=output
    )


@diagnose_app.command("kafka")
def diagnose_kafka(
    bootstrap_server: str = typer.Option(..., help="Kafka bootstrap server."),
    security_protocol: str = typer.Option("PLAINTEXT", help="PLAINTEXT, SSL, SASL_SSL"),
    ca_cert: str = typer.Option(None, help="Path to CA certificate"),
    client_cert: str = typer.Option(None, help="Path to client certificate"),
    client_key: str = typer.Option(None, help="Path to client private key"),

    topic: str = typer.Option(None, help="Analyze only a specific topic."),
    consumer_group: str = typer.Option(None, help="Analyze only a specific consumer group."),

    max_topics: int = typer.Option(50, help="Maximum topics to analyze."),
    max_groups: int = typer.Option(20, help="Maximum consumer groups to analyze."),

    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json.")
):
    """Diagnose Kafka runtime operational behavior."""

    findings = analyze_kafka_cluster(
        bootstrap_server=bootstrap_server,
        security_protocol=security_protocol,
        ca_cert=ca_cert,
        client_cert=client_cert,
        client_key=client_key,
        max_topics=max_topics,
        topic=topic,
        consumer_group=consumer_group,
        max_groups=max_groups,
    )

    print_report(
        findings,
        html=html,
        open_report=open_report,
        output=output
    )


@diagnose_app.command("flow")
def diagnose_flow():
    """Future distributed flow diagnostics."""
    typer.echo("Flow diagnostics coming soon.")


@diagnose_app.command("kubernetes")
def diagnose_kubernetes():
    """Future Kubernetes operational diagnostics."""
    typer.echo("Kubernetes diagnostics coming soon.")


if __name__ == "__main__":
    app()