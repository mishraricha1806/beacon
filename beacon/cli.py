# Beacon runtime Kafka connector is read-only by design.
# Do NOT add produce, consume, alter, delete, offset-reset, or mutation operations here.
# Allowed operations:
# - list topic metadata
# - describe topic configs
# - describe cluster metadata
import logging
import os
import time
from pathlib import Path
import shutil

import typer

from beacon.scanner import scan_path
from beacon.reporter import print_report
from beacon.runtime_advisor import analyze_runtime_file
from beacon.kafka_acl_scanner import analyze_kafka_acl_file
from beacon.kafka_history import analyze_kafka_history_file
from beacon.kafka_runtime_connector import analyze_kafka_cluster
from beacon.kubernetes_runtime_connector import analyze_kubernetes_cluster
from beacon.flow_runtime import analyze_flow_file
from beacon.runtime_snapshot import analyze_runtime_snapshot_file
from beacon.prometheus_connector import analyze_prometheus_config
from beacon.schema_registry_connector import analyze_schema_registry_config
from beacon.opentelemetry_connector import analyze_opentelemetry_file
from beacon.deployment_events import analyze_deployment_events_file
from beacon.readiness.kafka.readiness_engine import calculate_readiness
from beacon.engine import metadata_registry as rules_registry
from rich.table import Table
from beacon.diagnose.diagnostic_engine import build_diagnostic_summary
from beacon.intelligence.context import load_intelligence_context
from beacon.policy import load_policy, apply_policy_to_findings
from beacon.project_config import (
    as_list,
    config_context_path,
    config_environment,
    config_environment_model,
    config_live_inputs,
    config_readiness_includes,
    config_report_options,
    config_tasks,
    discover_config,
    load_project_config,
    resolve_config_path,
    starter_config,
)


from beacon.readiness.readiness_reporter import print_readiness_summary


LOGGER = logging.getLogger(__name__)

app = typer.Typer(help="Beacon - Operational intelligence for modern infrastructure.")

diagnose_app = typer.Typer(help="Runtime operational diagnostics.")

app.add_typer(diagnose_app, name="diagnose")

readiness_app = typer.Typer(help="Production readiness analysis.", invoke_without_command=True)

app.add_typer(readiness_app, name="readiness")

rules_app = typer.Typer(help="Rules metadata and management.")
app.add_typer(rules_app, name="rules")


def apply_runtime_policy(findings):
    policy = load_policy()
    return apply_policy_to_findings(findings, policy)


def emit_readiness(
    findings,
    html=True,
    open_report=True,
    output="terminal",
    environment=None,
    context_path=None,
    environment_model=None,
):
    findings = apply_runtime_policy(findings)
    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings,
        environment=environment,
        intelligence_context=intelligence_context,
        environment_model=environment_model,
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


def emit_readiness_report(findings, html, open_report, output, readiness_summary):
    if output != "json":
        print_readiness_summary(readiness_summary)

    print_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


def emit_diagnostics(findings, html=True, open_report=True, output="terminal"):
    findings = apply_runtime_policy(findings)
    diagnostic_summary = build_diagnostic_summary(findings)
    print_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        diagnostic_summary=diagnostic_summary,
    )


def collect_all_domain_findings(
    static_path=None,
    snapshot_path=None,
    flow_path=None,
    prometheus_path=None,
    opentelemetry_path=None,
    schema_registry_path=None,
    kafka_acl_path=None,
    kafka_history_path=None,
    deployment_events_path=None,
    prometheus_timeout=5,
    schema_registry_timeout=5,
    kafka_bootstrap_server=None,
    kafka_security_protocol="PLAINTEXT",
    kafka_ca_cert=None,
    kafka_client_cert=None,
    kafka_client_key=None,
    kafka_topic=None,
    kafka_consumer_group=None,
    kafka_max_topics=50,
    kafka_max_groups=20,
    kafka_churn_samples=1,
    kafka_churn_interval_seconds=0,
    kubernetes_live=False,
    kubernetes_namespace=None,
    kubernetes_context=None,
    kubernetes_kubeconfig=None,
):
    """Collect all explicitly provided Beacon domain inputs.

    Static inputs can include Terraform, Helm, Kubernetes YAML, Kafka config,
    CI/CD, cloud inventory, topology, and runtime snapshots discovered by the
    scanner. Live Kafka and Kubernetes collection stays opt-in and read-only.
    """

    findings = []

    if static_path:
        findings.extend(collect_domain_findings("static", lambda: scan_path(static_path)))

    if snapshot_path:
        findings.extend(
            collect_domain_findings(
                "runtime_snapshot", lambda: analyze_runtime_snapshot_file(snapshot_path)
            )
        )

    if flow_path:
        findings.extend(collect_domain_findings("flow", lambda: analyze_flow_file(flow_path)))

    if prometheus_path:
        findings.extend(
            collect_domain_findings(
                "prometheus",
                lambda: analyze_prometheus_config(prometheus_path, timeout=prometheus_timeout),
            )
        )

    if opentelemetry_path:
        findings.extend(
            collect_domain_findings(
                "opentelemetry", lambda: analyze_opentelemetry_file(opentelemetry_path)
            )
        )

    if schema_registry_path:
        findings.extend(
            collect_domain_findings(
                "schema_registry",
                lambda: analyze_schema_registry_config(
                    schema_registry_path, timeout=schema_registry_timeout
                ),
            )
        )

    if kafka_acl_path:
        findings.extend(
            collect_domain_findings("kafka_acls", lambda: analyze_kafka_acl_file(kafka_acl_path))
        )

    if kafka_history_path:
        findings.extend(
            collect_domain_findings(
                "kafka_history", lambda: analyze_kafka_history_file(kafka_history_path)
            )
        )

    if kafka_bootstrap_server:
        findings.extend(
            collect_domain_findings(
                "kafka_live",
                lambda: analyze_kafka_cluster(
                    bootstrap_server=kafka_bootstrap_server,
                    security_protocol=kafka_security_protocol,
                    ca_cert=kafka_ca_cert,
                    client_cert=kafka_client_cert,
                    client_key=kafka_client_key,
                    max_topics=kafka_max_topics,
                    topic=kafka_topic,
                    consumer_group=kafka_consumer_group,
                    max_groups=kafka_max_groups,
                    churn_samples=kafka_churn_samples,
                    churn_interval_seconds=kafka_churn_interval_seconds,
                ),
            )
        )

    if kubernetes_live:
        findings.extend(
            collect_domain_findings(
                "kubernetes_live",
                lambda: analyze_kubernetes_cluster(
                    namespace=kubernetes_namespace,
                    context=kubernetes_context,
                    kubeconfig=kubernetes_kubeconfig,
                ),
            )
        )

    if deployment_events_path:
        findings.extend(
            collect_domain_findings(
                "deployment_events",
                lambda: analyze_deployment_events_file(
                    deployment_events_path, existing_findings=findings
                ),
            )
        )

    return findings


def collect_domain_findings(domain, collect):
    started = time.monotonic()
    LOGGER.info("cli.domain.start domain=%s", domain)
    findings = collect()
    LOGGER.info(
        "cli.domain.complete domain=%s findings=%s elapsed=%.2fs",
        domain,
        len(findings),
        time.monotonic() - started,
    )
    return findings


def configure_logging():
    level_name = os.environ.get("BEACON_LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.WARNING),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def run_configured_readiness(config, config_path, environment=None, output=None):
    report_options = config_report_options(config)
    if output:
        report_options["output"] = output

    effective_environment = environment or config_environment(config)
    context_path = config_context_path(config, config_path)
    includes = config_readiness_includes(config, config_path)
    live_inputs = config_live_inputs(config, config_path)

    findings = []
    for include_path in includes:
        LOGGER.info("cli.config.readiness.include path=%s", include_path)
        findings.extend(scan_path(include_path))

    if any(value for value in live_inputs.values()):
        configured_findings = collect_all_domain_findings(**live_inputs)
        findings.extend(configured_findings)

    if report_options["output"] != "json":
        typer.echo(f"Found {config_path}")
        typer.echo(f"Scanning {len(includes)} configured path(s)...")

    emit_readiness(
        findings,
        html=report_options["html"],
        open_report=report_options["open_report"],
        output=report_options["output"],
        environment=effective_environment,
        context_path=context_path,
        environment_model=config_environment_model(config),
    )


def run_configured_task(config, config_path, task_name, output=None):
    tasks = config_tasks(config)
    task = tasks.get(task_name)
    if task is None:
        available = ", ".join(sorted(tasks)) or "none"
        raise typer.BadParameter(f"Unknown Beacon task '{task_name}'. Available tasks: {available}")
    if not isinstance(task, dict):
        raise typer.BadParameter(f"Task '{task_name}' must be a YAML mapping.")

    command = task.get("command")
    if command == "readiness":
        run_configured_readiness(
            config,
            config_path,
            environment=task.get("environment"),
            output=output,
        )
        return

    html = bool(task.get("html", False))
    open_report = bool(task.get("open", False))
    task_output = output or task.get("output") or "terminal"

    if command == "readiness static":
        path = task.get("path")
        if not path:
            raise typer.BadParameter(f"Task '{task_name}' requires path.")
        readiness_static(
            path=resolve_config_path(config_path, path),
            environment=task.get("environment") or config_environment(config),
            context_path=task.get("context")
            and resolve_config_path(config_path, task.get("context")),
            html=html,
            open_report=open_report,
            output=task_output,
        )
        return

    if command == "diagnose kafka-runtime":
        path = task.get("path")
        if not path:
            raise typer.BadParameter(f"Task '{task_name}' requires path.")
        diagnose_kafka_runtime(
            path=resolve_config_path(config_path, path),
            html=html,
            open_report=open_report,
            output=task_output,
        )
        return

    if command == "diagnose flow":
        path = task.get("path")
        if not path:
            raise typer.BadParameter(f"Task '{task_name}' requires path.")
        diagnose_flow(
            path=resolve_config_path(config_path, path),
            html=html,
            open_report=open_report,
            output=task_output,
        )
        return

    raise typer.BadParameter(
        f"Task '{task_name}' uses unsupported command '{command}'. "
        "Supported commands: readiness, readiness static, diagnose kafka-runtime, diagnose flow."
    )


@app.command("init")
def init_project(
    force: bool = typer.Option(False, "--force", help="Overwrite existing beacon.yaml."),
):
    """Create a starter beacon.yaml for project-local Beacon workflows."""
    path = Path("beacon.yaml")
    if path.exists() and not force:
        typer.echo("beacon.yaml already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    path.write_text(starter_config(), encoding="utf-8")
    Path("reports").mkdir(exist_ok=True)
    typer.echo("Created beacon.yaml")
    typer.echo("Created reports/")


@app.command("doctor")
def doctor(config: str = typer.Option(None, "--config", help="Path to beacon.yaml.")):
    """Check local Beacon project configuration and optional tool availability."""
    try:
        data, config_path = load_project_config(config)
    except Exception as error:
        typer.echo(f"[FAIL] Could not load Beacon config: {error}")
        raise typer.Exit(code=1)

    if config_path:
        typer.echo(f"[OK] Beacon config found: {config_path}")
    else:
        typer.echo("[WARN] No beacon.yaml found in this directory tree")
        data = {}

    reports_path = Path("reports")
    reports_path.mkdir(exist_ok=True)
    typer.echo(
        "[OK] reports directory writable"
        if os.access(reports_path, os.W_OK)
        else "[FAIL] reports directory not writable"
    )

    if shutil.which("helm"):
        typer.echo("[OK] helm found")
    else:
        typer.echo("[WARN] Helm not found; Helm chart rendering will be blocked or skipped")

    if shutil.which("kubectl"):
        typer.echo("[OK] kubectl found")
    else:
        typer.echo("[WARN] kubectl not found; live Kubernetes diagnostics need kubectl")

    if data and config_path:
        environment_model = config_environment_model(data)
        typer.echo(f"[OK] environment model: {environment_model['name']}")
        if environment_model.get("business_flows"):
            typer.echo("[OK] business flows: " + ", ".join(environment_model["business_flows"][:3]))
        if environment_model.get("dependency_domains"):
            typer.echo(
                "[OK] dependency domains: " + ", ".join(environment_model["dependency_domains"])
            )

        for include_path in config_readiness_includes(data, config_path):
            path = Path(include_path)
            status = "[OK]" if path.exists() else "[FAIL]"
            typer.echo(f"{status} readiness include path: {path}")

        for task_name in sorted(config_tasks(data)):
            typer.echo(f"[OK] task configured: {task_name}")


@app.command("run")
def run_task(
    task_name: str = typer.Argument(..., help="Task name from beacon.yaml."),
    config: str = typer.Option(None, "--config", help="Path to beacon.yaml."),
    output: str = typer.Option(None, help="Override output format."),
):
    """Run a named Beacon workflow from beacon.yaml."""
    data, config_path = load_project_config(config)
    if not config_path:
        typer.echo("No beacon.yaml found. Run `beacon init` first.")
        raise typer.Exit(code=1)

    run_configured_task(data, config_path, task_name, output=output)


@rules_app.command("list")
def list_rules(output: str = typer.Option("terminal", help="Output: terminal or json")):
    """List available rule metadata."""
    rules = rules_registry.list_rules()

    if output == "json":
        import json

        typer.echo(json.dumps(rules, indent=2))
        return

    table = Table(title="Beacon Rules")
    table.add_column("Rule ID", style="bold")
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Default Severity")

    for rule_id, meta in sorted(rules.items()):
        table.add_row(
            rule_id,
            meta.get("title", ""),
            meta.get("category", ""),
            meta.get("severity_default", ""),
        )

    from rich.console import Console

    Console().print(table)


@app.command()
def scan(
    path: str,
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Scan infrastructure configuration for production risks."""
    findings = scan_path(path)
    # apply runtime policy overrides (if present)
    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    print_report(findings, html=html, open_report=open_report, output=output)


@app.command()
def runtime(
    path: str,
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Analyze Kafka runtime snapshot YAML."""
    findings = analyze_runtime_file(path)
    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    print_report(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("snapshot")
def diagnose_snapshot(
    path: str = typer.Argument(..., help="Path to a runtime snapshot YAML."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose API, database, storage, flow, or Kubernetes runtime snapshots."""

    findings = analyze_runtime_snapshot_file(path)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("prometheus")
def diagnose_prometheus(
    path: str = typer.Argument(..., help="Path to Prometheus collector config YAML."),
    timeout: int = typer.Option(5, help="Prometheus query timeout in seconds."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose runtime signals from Prometheus."""

    findings = analyze_prometheus_config(path, timeout=timeout)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("opentelemetry")
def diagnose_opentelemetry(
    path: str = typer.Argument(..., help="Path to OpenTelemetry export YAML or JSON."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose runtime signals from OpenTelemetry exports."""

    findings = analyze_opentelemetry_file(path)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("schema-registry")
def diagnose_schema_registry(
    path: str = typer.Argument(..., help="Path to Schema Registry collector config YAML."),
    timeout: int = typer.Option(5, help="Schema Registry query timeout in seconds."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose Kafka Schema Registry readiness."""

    findings = analyze_schema_registry_config(path, timeout=timeout)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("kafka")
def diagnose_kafka(
    bootstrap_server: str = typer.Option(None, help="Kafka bootstrap server."),
    security_protocol: str = typer.Option("PLAINTEXT", help="PLAINTEXT, SSL, SASL_SSL"),
    ca_cert: str = typer.Option(None, help="Path to CA certificate"),
    client_cert: str = typer.Option(None, help="Path to client certificate"),
    client_key: str = typer.Option(None, help="Path to client private key"),
    access_config: str = typer.Option(
        None, help="Path to generic Kafka access profile config YAML."
    ),
    topic: str = typer.Option(None, help="Analyze only a specific topic."),
    consumer_group: str = typer.Option(None, help="Analyze only a specific consumer group."),
    max_topics: int = typer.Option(50, help="Maximum topics to analyze."),
    max_groups: int = typer.Option(20, help="Maximum consumer groups to analyze."),
    churn_samples: int = typer.Option(
        1, help="Number of consumer group member samples for churn diagnostics."
    ),
    churn_interval_seconds: float = typer.Option(
        0, help="Seconds between consumer group churn samples."
    ),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
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
        access_config=access_config,
        churn_samples=churn_samples,
        churn_interval_seconds=churn_interval_seconds,
    )
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("kafka-acls")
def diagnose_kafka_acls(
    path: str = typer.Argument(..., help="Path to Kafka ACL export YAML or JSON."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose Kafka authorization posture from an offline ACL export."""

    findings = analyze_kafka_acl_file(path)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("kafka-history")
def diagnose_kafka_history(
    path: str = typer.Argument(..., help="Path to Kafka runtime history YAML or JSON."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose Kafka trends from historical runtime snapshots."""

    findings = analyze_kafka_history_file(path)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("kafka-runtime")
def diagnose_kafka_runtime(
    path: str = typer.Argument(..., help="Path to Kafka runtime snapshot YAML or JSON."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose Kafka runtime signals from an offline incident snapshot."""

    findings = analyze_runtime_file(path)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("deployment-events")
def diagnose_deployment_events(
    path: str = typer.Argument(..., help="Path to deployment events YAML or JSON."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Inspect deployment events for runtime correlation."""

    findings = analyze_deployment_events_file(path)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("flow")
def diagnose_flow(
    path: str = typer.Argument(..., help="Path to a flow runtime snapshot YAML."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose cross-system runtime flow degradation."""

    findings = analyze_flow_file(path)
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("kubernetes")
def diagnose_kubernetes(
    namespace: str = typer.Option(None, help="Namespace to analyze, defaults to all namespaces."),
    context: str = typer.Option(None, help="kubectl context to use."),
    kubeconfig: str = typer.Option(None, help="Path to kubeconfig."),
    html: bool = typer.Option(True, help="Generate browser-based HTML report."),
    open_report: bool = typer.Option(True, help="Open HTML report in browser."),
    output: str = typer.Option("terminal", help="Output format: terminal or json."),
):
    """Diagnose Kubernetes runtime operational behavior."""

    findings = analyze_kubernetes_cluster(
        namespace=namespace,
        context=context,
        kubeconfig=kubeconfig,
    )
    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@diagnose_app.command("all")
def diagnose_all(
    static_path: str = typer.Option(
        None,
        "--static-path",
        help="Static config path: Terraform, Helm, Kubernetes YAML, Kafka, CI/CD, cloud, topology.",
    ),
    snapshot_path: str = typer.Option(
        None,
        "--snapshot",
        help="Runtime snapshot path for API, database, storage, flow, Kubernetes, or Kafka signals.",
    ),
    flow_path: str = typer.Option(None, "--flow", help="Flow runtime snapshot path."),
    prometheus_path: str = typer.Option(
        None, "--prometheus", help="Prometheus collector config path."
    ),
    opentelemetry_path: str = typer.Option(
        None, "--opentelemetry", help="OpenTelemetry export YAML or JSON path."
    ),
    schema_registry_path: str = typer.Option(
        None, "--schema-registry", help="Schema Registry collector config path."
    ),
    kafka_acl_path: str = typer.Option(
        None, "--kafka-acls", help="Kafka ACL export YAML or JSON path."
    ),
    kafka_history_path: str = typer.Option(
        None, "--kafka-history", help="Kafka runtime history YAML or JSON path."
    ),
    deployment_events_path: str = typer.Option(
        None, "--deployment-events", help="Deployment events YAML or JSON path."
    ),
    prometheus_timeout: int = typer.Option(
        5, "--prometheus-timeout", help="Prometheus query timeout in seconds."
    ),
    schema_registry_timeout: int = typer.Option(
        5, "--schema-registry-timeout", help="Schema Registry query timeout in seconds."
    ),
    kafka_bootstrap_server: str = typer.Option(
        None, "--kafka-bootstrap-server", help="Kafka bootstrap server."
    ),
    kafka_security_protocol: str = typer.Option("PLAINTEXT"),
    kafka_ca_cert: str = typer.Option(None),
    kafka_client_cert: str = typer.Option(None),
    kafka_client_key: str = typer.Option(None),
    kafka_topic: str = typer.Option(None),
    kafka_consumer_group: str = typer.Option(None),
    kafka_max_topics: int = typer.Option(50),
    kafka_max_groups: int = typer.Option(20),
    kafka_churn_samples: int = typer.Option(1),
    kafka_churn_interval_seconds: float = typer.Option(0),
    kubernetes_live: bool = typer.Option(
        False, "--kubernetes-live", help="Collect live Kubernetes runtime signals."
    ),
    kubernetes_namespace: str = typer.Option(None),
    kubernetes_context: str = typer.Option(None),
    kubernetes_kubeconfig: str = typer.Option(None),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Diagnose all provided Beacon domains in one deterministic pass."""

    findings = collect_all_domain_findings(
        static_path=static_path,
        snapshot_path=snapshot_path,
        flow_path=flow_path,
        prometheus_path=prometheus_path,
        opentelemetry_path=opentelemetry_path,
        schema_registry_path=schema_registry_path,
        kafka_acl_path=kafka_acl_path,
        kafka_history_path=kafka_history_path,
        deployment_events_path=deployment_events_path,
        prometheus_timeout=prometheus_timeout,
        schema_registry_timeout=schema_registry_timeout,
        kafka_bootstrap_server=kafka_bootstrap_server,
        kafka_security_protocol=kafka_security_protocol,
        kafka_ca_cert=kafka_ca_cert,
        kafka_client_cert=kafka_client_cert,
        kafka_client_key=kafka_client_key,
        kafka_topic=kafka_topic,
        kafka_consumer_group=kafka_consumer_group,
        kafka_max_topics=kafka_max_topics,
        kafka_max_groups=kafka_max_groups,
        kafka_churn_samples=kafka_churn_samples,
        kafka_churn_interval_seconds=kafka_churn_interval_seconds,
        kubernetes_live=kubernetes_live,
        kubernetes_namespace=kubernetes_namespace,
        kubernetes_context=kubernetes_context,
        kubernetes_kubeconfig=kubernetes_kubeconfig,
    )

    emit_diagnostics(findings, html=html, open_report=open_report, output=output)


@readiness_app.callback()
def readiness_default(
    ctx: typer.Context,
    config: str = typer.Option(None, "--config", help="Path to beacon.yaml."),
    output: str = typer.Option(None, help="Override output format."),
):
    """Run project-local readiness when no subcommand is provided."""
    if ctx.invoked_subcommand is not None:
        return

    data, config_path = load_project_config(config)
    if not config_path:
        typer.echo("No beacon.yaml found. Run `beacon init` or use a subcommand.")
        raise typer.Exit(code=1)

    run_configured_readiness(data, config_path, output=output)


@readiness_app.command("kafka")
def readiness_kafka(
    bootstrap_server: str = typer.Option(None),
    security_protocol: str = typer.Option("PLAINTEXT"),
    ca_cert: str = typer.Option(None),
    client_cert: str = typer.Option(None),
    client_key: str = typer.Option(None),
    access_config: str = typer.Option(None),
    topic: str = typer.Option(None),
    consumer_group: str = typer.Option(None),
    max_topics: int = typer.Option(50),
    max_groups: int = typer.Option(20),
    churn_samples: int = typer.Option(1),
    churn_interval_seconds: float = typer.Option(0),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
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
        access_config=access_config,
        churn_samples=churn_samples,
        churn_interval_seconds=churn_interval_seconds,
    )

    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


@readiness_app.command("kafka-acls")
def readiness_kafka_acls(
    path: str = typer.Argument(..., help="Path to Kafka ACL export YAML or JSON."),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze Kafka authorization readiness from an offline ACL export."""

    emit_readiness(
        analyze_kafka_acl_file(path),
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
    )


@readiness_app.command("kafka-history")
def readiness_kafka_history(
    path: str = typer.Argument(..., help="Path to Kafka runtime history YAML or JSON."),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze Kafka readiness trends from historical runtime snapshots."""

    emit_readiness(
        analyze_kafka_history_file(path),
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
    )


@readiness_app.command("all")
def readiness_all(
    static_path: str = typer.Option(
        None,
        "--static-path",
        help="Static config path: Terraform, Helm, Kubernetes YAML, Kafka, CI/CD, cloud, topology.",
    ),
    snapshot_path: str = typer.Option(
        None,
        "--snapshot",
        help="Runtime snapshot path for API, database, storage, flow, Kubernetes, or Kafka signals.",
    ),
    flow_path: str = typer.Option(None, "--flow", help="Flow runtime snapshot path."),
    prometheus_path: str = typer.Option(
        None, "--prometheus", help="Prometheus collector config path."
    ),
    opentelemetry_path: str = typer.Option(
        None, "--opentelemetry", help="OpenTelemetry export YAML or JSON path."
    ),
    schema_registry_path: str = typer.Option(
        None, "--schema-registry", help="Schema Registry collector config path."
    ),
    kafka_acl_path: str = typer.Option(
        None, "--kafka-acls", help="Kafka ACL export YAML or JSON path."
    ),
    kafka_history_path: str = typer.Option(
        None, "--kafka-history", help="Kafka runtime history YAML or JSON path."
    ),
    deployment_events_path: str = typer.Option(
        None, "--deployment-events", help="Deployment events YAML or JSON path."
    ),
    prometheus_timeout: int = typer.Option(
        5, "--prometheus-timeout", help="Prometheus query timeout in seconds."
    ),
    schema_registry_timeout: int = typer.Option(
        5, "--schema-registry-timeout", help="Schema Registry query timeout in seconds."
    ),
    kafka_bootstrap_server: str = typer.Option(
        None, "--kafka-bootstrap-server", help="Kafka bootstrap server."
    ),
    kafka_security_protocol: str = typer.Option("PLAINTEXT"),
    kafka_ca_cert: str = typer.Option(None),
    kafka_client_cert: str = typer.Option(None),
    kafka_client_key: str = typer.Option(None),
    kafka_topic: str = typer.Option(None),
    kafka_consumer_group: str = typer.Option(None),
    kafka_max_topics: int = typer.Option(50),
    kafka_max_groups: int = typer.Option(20),
    kafka_churn_samples: int = typer.Option(1),
    kafka_churn_interval_seconds: float = typer.Option(0),
    kubernetes_live: bool = typer.Option(
        False, "--kubernetes-live", help="Collect live Kubernetes runtime signals."
    ),
    kubernetes_namespace: str = typer.Option(None),
    kubernetes_context: str = typer.Option(None),
    kubernetes_kubeconfig: str = typer.Option(None),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze production readiness across all provided Beacon domains."""

    findings = collect_all_domain_findings(
        static_path=static_path,
        snapshot_path=snapshot_path,
        flow_path=flow_path,
        prometheus_path=prometheus_path,
        opentelemetry_path=opentelemetry_path,
        schema_registry_path=schema_registry_path,
        kafka_acl_path=kafka_acl_path,
        kafka_history_path=kafka_history_path,
        deployment_events_path=deployment_events_path,
        prometheus_timeout=prometheus_timeout,
        schema_registry_timeout=schema_registry_timeout,
        kafka_bootstrap_server=kafka_bootstrap_server,
        kafka_security_protocol=kafka_security_protocol,
        kafka_ca_cert=kafka_ca_cert,
        kafka_client_cert=kafka_client_cert,
        kafka_client_key=kafka_client_key,
        kafka_topic=kafka_topic,
        kafka_consumer_group=kafka_consumer_group,
        kafka_max_topics=kafka_max_topics,
        kafka_max_groups=kafka_max_groups,
        kafka_churn_samples=kafka_churn_samples,
        kafka_churn_interval_seconds=kafka_churn_interval_seconds,
        kubernetes_live=kubernetes_live,
        kubernetes_namespace=kubernetes_namespace,
        kubernetes_context=kubernetes_context,
        kubernetes_kubeconfig=kubernetes_kubeconfig,
    )

    emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
    )


@readiness_app.command("static")
def readiness_static(
    path: str,
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze infrastructure production readiness."""

    findings = scan_path(path)
    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


@readiness_app.command("kubernetes")
def readiness_kubernetes(
    namespace: str = typer.Option(None),
    context: str = typer.Option(None),
    kubeconfig: str = typer.Option(None),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze Kubernetes runtime production readiness."""

    findings = analyze_kubernetes_cluster(
        namespace=namespace,
        context=context,
        kubeconfig=kubeconfig,
    )

    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


@readiness_app.command("flow")
def readiness_flow(
    path: str = typer.Argument(..., help="Path to a flow runtime snapshot YAML."),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze cross-system runtime flow readiness."""

    findings = analyze_flow_file(path)

    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


@readiness_app.command("snapshot")
def readiness_snapshot(
    path: str = typer.Argument(..., help="Path to a runtime snapshot YAML."),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze API, database, storage, flow, or Kubernetes runtime readiness."""

    findings = analyze_runtime_snapshot_file(path)

    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


@readiness_app.command("prometheus")
def readiness_prometheus(
    path: str = typer.Argument(..., help="Path to Prometheus collector config YAML."),
    timeout: int = typer.Option(5, help="Prometheus query timeout in seconds."),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze runtime readiness from Prometheus signals."""

    findings = analyze_prometheus_config(path, timeout=timeout)

    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


@readiness_app.command("opentelemetry")
def readiness_opentelemetry(
    path: str = typer.Argument(..., help="Path to OpenTelemetry export YAML or JSON."),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze runtime readiness from OpenTelemetry exports."""

    findings = analyze_opentelemetry_file(path)

    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


@readiness_app.command("schema-registry")
def readiness_schema_registry(
    path: str = typer.Argument(..., help="Path to Schema Registry collector config YAML."),
    timeout: int = typer.Option(5, help="Schema Registry query timeout in seconds."),
    environment: str = typer.Option(
        None, "--environment", help="Readiness profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for deterministic interpretation.",
    ),
    html: bool = typer.Option(True),
    open_report: bool = typer.Option(True),
    output: str = typer.Option("terminal"),
):
    """Analyze Kafka Schema Registry production readiness."""

    findings = analyze_schema_registry_config(path, timeout=timeout)

    policy = load_policy()
    findings = apply_policy_to_findings(findings, policy)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )


if __name__ == "__main__":
    configure_logging()
    app()
