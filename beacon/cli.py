import typer

from beacon.scanner import scan_path
from beacon.reporter import print_report
from beacon.runtime_advisor import analyze_runtime_file
from beacon.kafka_runtime_connector import analyze_kafka_cluster

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

@app.command("runtime-kafka")
def runtime_kafka(
    bootstrap_server: str = typer.Option(..., help="Kafka bootstrap server, e.g. localhost:9092"),
    security_protocol: str = typer.Option("PLAINTEXT", help="PLAINTEXT, SSL, SASL_SSL"),
    ca_cert: str = typer.Option(None, help="Path to CA certificate"),
    client_cert: str = typer.Option(None, help="Path to client certificate"),
    client_key: str = typer.Option(None, help="Path to client private key"),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser.")
):
    """Connect to Kafka in read-only mode and collect basic runtime metadata."""
    findings = analyze_kafka_cluster(
        bootstrap_server=bootstrap_server,
        security_protocol=security_protocol,
        ca_cert=ca_cert,
        client_cert=client_cert,
        client_key=client_key,
    )

    print_report(findings, html=html, open_report=open_report)

if __name__ == "__main__":
    app()