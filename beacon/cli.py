# Beacon runtime Kafka connector is read-only by design.
# Do NOT add produce, consume, alter, delete, offset-reset, or mutation operations here.
# Allowed operations:
# - list topic metadata
# - describe topic configs
# - describe cluster metadata
import logging
import json
import os
import time
from pathlib import Path
import shutil

import typer

from beacon.contracts import validate_release_evidence
from beacon.ci_export import write_ci_artifacts
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
from beacon.iac_coverage import analyze_iac_coverage
from beacon.readiness.kafka.readiness_engine import calculate_readiness
from beacon.readiness.comparison import compare_release_evidence, format_comparison_markdown
from beacon.engine import metadata_registry as rules_registry
from beacon.packs import (
    get_pack,
    list_packs,
    pack_rules_with_metadata,
    pack_summary,
    validate_pack,
)
from rich.table import Table
from beacon.diagnose.diagnostic_engine import build_diagnostic_summary
from beacon.intelligence.context import load_intelligence_context
from beacon.policy import (
    apply_policy_bundle_to_findings,
    apply_policy_to_findings,
    load_policy,
    load_policy_bundle,
    merge_policy_bundles,
    readiness_exit_code,
)
from beacon.project_config import (
    as_list,
    config_ci_options,
    config_context_path,
    config_environment,
    config_environment_model,
    config_live_inputs,
    config_policy_bundle,
    config_policy_path,
    config_readiness_includes,
    config_report_options,
    config_tasks,
    discover_config,
    load_project_config,
    resolve_config_path,
    starter_config,
)
from beacon.readiness.correlations import augment_readiness_findings


from beacon.readiness.readiness_reporter import print_readiness_summary

LOGGER = logging.getLogger(__name__)

app = typer.Typer(help="Beacon - Operational intelligence for modern infrastructure.")

diagnose_app = typer.Typer(help="Runtime operational diagnostics.")

app.add_typer(diagnose_app, name="diagnose")

readiness_app = typer.Typer(
    help="Production readiness analysis.",
    invoke_without_command=True,
)

app.add_typer(readiness_app, name="readiness")

rules_app = typer.Typer(help="Rules metadata and management.")
app.add_typer(rules_app, name="rules")

packs_app = typer.Typer(help="Inspectable readiness packs.")
app.add_typer(packs_app, name="packs")


def effective_policy_bundle(policy_path=None, config=None, config_path=None):
    policy_path = option_value(policy_path)
    bundles = [load_policy_bundle(policy_path), {"rules": load_policy()}]

    if config is not None:
        configured_policy_path = config_policy_path(config, config_path)
        if configured_policy_path and configured_policy_path != policy_path:
            bundles.append(load_policy_bundle(configured_policy_path))
        bundles.append(config_policy_bundle(config))

    return merge_policy_bundles(*bundles)


def apply_runtime_policy(findings, policy_path=None, config=None, config_path=None):
    return apply_policy_bundle_to_findings(
        findings, effective_policy_bundle(policy_path, config, config_path)
    )


def maybe_exit_for_ci(summary, ci=False, fail_on=None, config=None):
    ci_options = config_ci_options(config or {}) if config else {}
    fail_on = option_value(fail_on)
    effective_fail_on = fail_on or ci_options.get("fail_on")
    ci_enabled = bool(option_value(ci)) or bool(ci_options.get("enabled")) or bool(fail_on)

    if not ci_enabled:
        return

    raise typer.Exit(code=readiness_exit_code(summary, effective_fail_on or "critical"))


def write_release_evidence(summary, evidence_output=None, config_path=None):
    evidence_output = option_value(evidence_output)
    if not evidence_output:
        return

    path = Path(evidence_output).expanduser()
    if not path.is_absolute() and config_path is not None:
        path = Path(config_path).parent / path

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary.get("release_evidence") or {}, indent=2) + "\n",
        encoding="utf-8",
    )


def load_release_evidence(path):
    evidence_path = Path(path).expanduser()
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    return validate_release_evidence(payload, allow_legacy=True)


def option_value(value):
    if isinstance(value, typer.models.OptionInfo):
        return None
    return value


def emit_readiness(
    findings,
    html=True,
    open_report=True,
    output="terminal",
    environment=None,
    context_path=None,
    environment_model=None,
    policy_path=None,
    config=None,
    config_path=None,
    evidence_output=None,
    sarif_output=None,
    junit_output=None,
    fail_on="high",
):
    findings = apply_runtime_policy(
        findings,
        policy_path=policy_path,
        config=config,
        config_path=config_path,
    )
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
    write_release_evidence(
        readiness_summary,
        evidence_output=evidence_output,
        config_path=config_path,
    )
    write_ci_artifacts(
        readiness_summary.get("interpreted_findings") or findings,
        readiness_summary,
        sarif_output=option_value(sarif_output),
        junit_output=option_value(junit_output),
        fail_on=option_value(fail_on) or "high",
    )
    return readiness_summary


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
    return readiness_summary


def emit_diagnostics(
    findings,
    html=True,
    open_report=True,
    output="terminal",
    policy_path=None,
    environment=None,
    intelligence_context=None,
):
    findings = apply_runtime_policy(findings, policy_path=policy_path)
    diagnostic_summary = build_diagnostic_summary(
        findings,
        environment=environment,
        intelligence_context=intelligence_context,
    )
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
    kafka_request_timeout_ms=None,
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
                    request_timeout_ms=kafka_request_timeout_ms,
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


def run_configured_readiness(
    config,
    config_path,
    environment=None,
    output=None,
    ci=False,
    fail_on=None,
    evidence_output=None,
):
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

    summary = emit_readiness(
        findings,
        html=report_options["html"],
        open_report=report_options["open_report"],
        output=report_options["output"],
        environment=effective_environment,
        context_path=context_path,
        environment_model=config_environment_model(config),
        config=config,
        config_path=config_path,
        evidence_output=evidence_output or report_options.get("evidence_output"),
    )
    maybe_exit_for_ci(summary, ci=ci, fail_on=fail_on, config=config)
    return summary


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
            ci=bool(task.get("ci", False)),
            fail_on=task.get("fail_on"),
            evidence_output=task.get("evidence_output"),
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
        governance = environment_model.get("service_governance") or {}
        if governance:
            marker = "[OK]" if governance.get("status") == "PASS" else "[WARN]"
            typer.echo(
                f"{marker} service governance: {governance.get('status')} "
                f"({governance.get('owned_service_count', 0)}/"
                f"{governance.get('service_count', 0)} owned)"
            )
            ci_options = config_ci_options(data)
            typer.echo(
                f"[OK] CI gate: {ci_options.get('fail_on')} "
                f"({ci_options.get('fail_on_source')})"
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


@app.command("compare")
def compare_evidence(
    before: str = typer.Argument(..., help="Previous Beacon release evidence JSON."),
    after: str = typer.Argument(..., help="New Beacon release evidence JSON."),
    output: str = typer.Option("terminal", help="Output format: terminal, json, or markdown."),
    markdown_output: str = typer.Option(
        None,
        "--markdown-output",
        help="Also write a Markdown comparison summary to this path.",
    ),
):
    """Compare two Beacon release evidence files."""

    comparison = compare_release_evidence(
        load_release_evidence(before),
        load_release_evidence(after),
    )
    markdown = format_comparison_markdown(comparison)
    markdown_output = option_value(markdown_output)
    if markdown_output:
        path = Path(markdown_output).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")

    if output == "json":
        typer.echo(json.dumps(comparison, indent=2))
        return

    if output == "markdown":
        typer.echo(markdown, nl=False)
        return

    if output != "terminal":
        raise typer.BadParameter("output must be one of: terminal, json, markdown")

    from rich.console import Console

    console = Console()
    console.print("[bold]Beacon Release Comparison[/bold]")
    console.print(comparison["summary"])
    console.print(
        f"Before: {comparison['before']['decision']} " f"({comparison['before']['score']}/100)"
    )
    console.print(
        f"After:  {comparison['after']['decision']} " f"({comparison['after']['score']}/100)"
    )

    if comparison["new_blocking_risks"]:
        print_risk_table(console, "New Production Blockers", comparison["new_blocking_risks"])
    if comparison["resolved_blocking_risks"]:
        print_risk_table(
            console,
            "Resolved Production Blockers",
            comparison["resolved_blocking_risks"],
        )
    if comparison["new_major_risks"]:
        print_risk_table(console, "New Major Risks", comparison["new_major_risks"])
    if comparison["resolved_major_risks"]:
        print_risk_table(console, "Resolved Major Risks", comparison["resolved_major_risks"])


def print_risk_table(console, title, risks):
    table = Table(title=title)
    table.add_column("Severity")
    table.add_column("Risk")
    table.add_column("Affected")
    table.add_column("Recommendation")

    for risk in risks:
        table.add_row(
            str(risk.get("severity") or ""),
            str(risk.get("title") or ""),
            str(risk.get("affected_count") or 0),
            str(risk.get("recommendation") or ""),
        )

    console.print(table)


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


@packs_app.command("list")
def list_readiness_packs(output: str = typer.Option("terminal", help="Output: terminal or json")):
    """List inspectable Beacon readiness packs."""
    packs = list_packs()

    if output == "json":
        typer.echo(json.dumps(packs, indent=2))
        return

    table = Table(title="Beacon Readiness Packs")
    table.add_column("Pack ID", style="bold")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Support")
    table.add_column("Rules")
    table.add_column("Gate")
    table.add_column("Summary")

    for pack_id, pack in sorted(packs.items()):
        summary = pack_summary(pack)
        table.add_row(
            pack_id,
            str(pack.get("name") or ""),
            str(pack.get("version") or ""),
            str(pack.get("status") or ""),
            str(pack.get("support_tier") or ""),
            str(summary["rule_count"]),
            str(summary["release_gate_rules"]),
            str(pack.get("summary") or "").strip(),
        )

    from rich.console import Console

    Console().print(table)


@packs_app.command("show")
def show_readiness_pack(
    pack_id: str = typer.Argument(..., help="Readiness pack id."),
    output: str = typer.Option("terminal", help="Output: terminal or json"),
):
    """Show readiness pack purpose, use cases, and validation status."""
    pack = get_pack(pack_id)
    if not pack:
        raise typer.BadParameter(f"Unknown readiness pack '{pack_id}'.")

    validation = validate_pack(pack)
    summary = pack_summary(pack)

    if output == "json":
        typer.echo(
            json.dumps({"pack": pack, "validation": validation, "summary": summary}, indent=2)
        )
        return

    from rich.console import Console

    console = Console()
    console.print(f"[bold]{pack.get('name') or pack_id}[/bold]")
    console.print(str(pack.get("summary") or "").strip())
    console.print(f"Manifest schema: {pack.get('schema_version') or 'unknown'}")
    console.print(f"Version: {pack.get('version') or 'unknown'}")
    console.print(f"Status: {pack.get('status') or 'unknown'}")
    console.print(f"Owner: {pack.get('owner') or 'unknown'}")
    console.print(f"Support tier: {pack.get('support_tier') or 'unknown'}")
    console.print(f"Engine compatible: {validation['engine_compatible']}")
    console.print(f"Rules: {validation['rule_count']}")
    console.print(f"Release-gate rules: {summary['release_gate_rules']}")
    console.print(f"Advisory/context rules: {summary['advisory_rules']}")

    if validation["missing_metadata"]:
        console.print("[bold red]Missing rule metadata:[/bold red]")
        for rule_id in validation["missing_metadata"]:
            console.print(f"- {rule_id}")
    else:
        console.print("[green]All pack rules have Beacon metadata.[/green]")

    if validation["errors"]:
        console.print("[bold red]Manifest errors:[/bold red]")
        for error in validation["errors"]:
            console.print(f"- {error}")

    if summary["severity_counts"]:
        console.print("\n[bold]Severity Coverage[/bold]")
        for severity, count in summary["severity_counts"].items():
            console.print(f"- {severity}: {count}")

    if summary["category_counts"]:
        console.print("\n[bold]Category Coverage[/bold]")
        for category, count in summary["category_counts"].items():
            console.print(f"- {category}: {count}")

    use_cases = pack.get("use_cases") or []
    if use_cases:
        console.print("\n[bold]Use Cases[/bold]")
        for use_case in use_cases:
            console.print(f"- {use_case}")

    non_goals = pack.get("non_goals") or []
    if non_goals:
        console.print("\n[bold]Non-Goals[/bold]")
        for non_goal in non_goals:
            console.print(f"- {non_goal}")


@packs_app.command("validate")
def validate_readiness_packs(
    pack_id: str = typer.Option(None, "--pack", help="Validate one pack id."),
    engine_version: str = typer.Option(
        None,
        "--engine-version",
        help="Validate compatibility against a specific Beacon semantic version.",
    ),
    output: str = typer.Option("terminal", help="Output: terminal or json."),
):
    """Validate pack manifests, fixtures, rule metadata, and engine compatibility."""
    packs = list_packs()
    if pack_id:
        pack = packs.get(pack_id)
        if not pack:
            raise typer.BadParameter(f"Unknown readiness pack '{pack_id}'.")
        packs = {pack_id: pack}

    validations = {
        current_id: validate_pack(pack, engine_version=engine_version)
        for current_id, pack in sorted(packs.items())
    }
    valid = all(result["valid"] for result in validations.values())

    if output == "json":
        typer.echo(json.dumps({"valid": valid, "packs": validations}, indent=2))
    elif output == "terminal":
        from rich.console import Console

        console = Console()
        for current_id, result in validations.items():
            marker = "[green]PASS[/green]" if result["valid"] else "[red]FAIL[/red]"
            console.print(
                f"{marker} {current_id}: {result['rule_count']} rules, "
                f"engine compatible={result['engine_compatible']}"
            )
            for error in result["errors"]:
                console.print(f"  - {error}")
            for rule_id in result["missing_metadata"]:
                console.print(f"  - Missing rule metadata: {rule_id}")
    else:
        raise typer.BadParameter("output must be one of: terminal, json")

    if not valid:
        raise typer.Exit(code=1)


@packs_app.command("rules")
def show_readiness_pack_rules(
    pack_id: str = typer.Argument(..., help="Readiness pack id."),
    output: str = typer.Option("terminal", help="Output: terminal or json"),
):
    """Show rule metadata included in a readiness pack."""
    pack = get_pack(pack_id)
    if not pack:
        raise typer.BadParameter(f"Unknown readiness pack '{pack_id}'.")

    rows = pack_rules_with_metadata(pack)

    if output == "json":
        typer.echo(json.dumps(rows, indent=2))
        return

    table = Table(title=f"{pack_id} Rules")
    table.add_column("Rule ID", style="bold")
    table.add_column("Severity")
    table.add_column("Category")
    table.add_column("Title")

    for row in rows:
        table.add_row(
            row["rule_id"],
            row["severity_default"],
            row["category"],
            row["title"],
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
    findings = apply_runtime_policy(findings)

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
    findings = apply_runtime_policy(findings)

    print_report(findings, html=html, open_report=open_report, output=output)


@app.command("ui")
def run_ui(
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface to bind."),
    port: int = typer.Option(8765, "--port", help="Port for the local web UI."),
    no_port_fallback: bool = typer.Option(
        False,
        "--no-port-fallback",
        help="Fail if the requested port is unavailable.",
    ),
):
    """Run the local Beacon readiness console."""
    from beacon.ui import build_server

    server, bound_port = build_server(
        host=host,
        port=port,
        allow_port_fallback=not no_port_fallback,
    )
    typer.echo(f"Beacon UI running at http://{host}:{bound_port}")
    server.serve_forever()


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
    request_timeout_ms: int = typer.Option(
        None,
        "--request-timeout-ms",
        help="Kafka AdminClient request timeout in milliseconds.",
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
        request_timeout_ms=request_timeout_ms,
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
    kafka_request_timeout_ms: int = typer.Option(
        None,
        "--kafka-request-timeout-ms",
        help="Kafka AdminClient request timeout in milliseconds.",
    ),
    kubernetes_live: bool = typer.Option(
        False, "--kubernetes-live", help="Collect live Kubernetes runtime signals."
    ),
    kubernetes_namespace: str = typer.Option(None),
    kubernetes_context: str = typer.Option(None),
    kubernetes_kubeconfig: str = typer.Option(None),
    environment: str = typer.Option(
        None, "--environment", help="Diagnostic environment profile: dev, test, staging, prod."
    ),
    context_path: str = typer.Option(
        None,
        "--context",
        help="Organization intelligence context YAML/JSON for service matching and deterministic interpretation.",
    ),
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
        kafka_request_timeout_ms=kafka_request_timeout_ms,
        kubernetes_live=kubernetes_live,
        kubernetes_namespace=kubernetes_namespace,
        kubernetes_context=kubernetes_context,
        kubernetes_kubeconfig=kubernetes_kubeconfig,
    )

    intelligence_context = load_intelligence_context(context_path)
    emit_diagnostics(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        intelligence_context=intelligence_context,
    )


@readiness_app.callback()
def readiness_default(
    ctx: typer.Context,
    config: str = typer.Option(None, "--config", help="Path to beacon.yaml."),
    output: str = typer.Option(None, help="Override output format."),
    ci: bool = typer.Option(
        False, "--ci", help="Exit non-zero when readiness crosses the configured threshold."
    ),
    fail_on: str = typer.Option(
        None,
        "--fail-on",
        help="CI threshold: none, critical, high, medium, or low.",
    ),
    evidence_output: str = typer.Option(
        None,
        "--evidence-output",
        help="Write readiness_summary.release_evidence to this JSON file.",
    ),
):
    """Run project-local readiness when no subcommand is provided."""
    if ctx.invoked_subcommand is not None:
        return

    data, config_path = load_project_config(config)
    if not config_path:
        typer.echo("No beacon.yaml found. Run `beacon init` or use a subcommand.")
        raise typer.Exit(code=1)

    run_configured_readiness(
        data,
        config_path,
        output=output,
        ci=ci,
        fail_on=fail_on,
        evidence_output=evidence_output,
    )


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
    request_timeout_ms: int = typer.Option(
        None,
        "--request-timeout-ms",
        help="Kafka AdminClient request timeout in milliseconds.",
    ),
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
    policy_path: str = typer.Option(None, "--policy", help="Policy and waiver YAML."),
    ci: bool = typer.Option(
        False, "--ci", help="Exit non-zero when readiness crosses the configured threshold."
    ),
    fail_on: str = typer.Option(
        None,
        "--fail-on",
        help="CI threshold: none, critical, high, medium, or low.",
    ),
    evidence_output: str = typer.Option(
        None,
        "--evidence-output",
        help="Write readiness_summary.release_evidence to this JSON file.",
    ),
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
        request_timeout_ms=request_timeout_ms,
    )

    findings = apply_runtime_policy(findings, policy_path=policy_path)

    intelligence_context = load_intelligence_context(context_path)
    readiness_summary = calculate_readiness(
        findings, environment=environment, intelligence_context=intelligence_context
    )

    summary = emit_readiness_report(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        readiness_summary=readiness_summary,
    )
    write_release_evidence(summary, evidence_output=evidence_output)
    maybe_exit_for_ci(summary, ci=ci, fail_on=fail_on)


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


@readiness_app.command("iac-coverage")
def readiness_iac_coverage(
    cloud_inventory: str = typer.Option(
        ...,
        "--cloud-inventory",
        help="Path to cloud inventory export YAML or JSON.",
    ),
    terraform_state: str = typer.Option(
        None,
        "--terraform-state",
        help="Path to one Terraform state JSON or plan/state-style JSON.",
    ),
    terraform_state_dir: str = typer.Option(
        None,
        "--terraform-state-dir",
        help="Directory of Terraform state JSON files. Beacon recursively indexes .tfstate, .tfstate.json, and .json files.",
    ),
    state_manifest: str = typer.Option(
        None,
        "--state-manifest",
        help="YAML/JSON manifest listing many Terraform state files or workspaces.",
    ),
    owners: str = typer.Option(
        None,
        "--owners",
        help="Optional ownership metadata YAML or JSON.",
    ),
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
    policy_path: str = typer.Option(None, "--policy", help="Policy and waiver YAML."),
    ci: bool = typer.Option(
        False, "--ci", help="Exit non-zero when readiness crosses the configured threshold."
    ),
    fail_on: str = typer.Option(
        None,
        "--fail-on",
        help="CI threshold: none, critical, high, medium, or low.",
    ),
    evidence_output: str = typer.Option(
        None,
        "--evidence-output",
        help="Write readiness_summary.release_evidence to this JSON file.",
    ),
):
    """Detect unmanaged cloud resources outside Terraform state."""

    if not any([terraform_state, terraform_state_dir, state_manifest]):
        raise typer.BadParameter(
            "Provide --terraform-state, --terraform-state-dir, or --state-manifest."
        )

    findings = analyze_iac_coverage(
        cloud_inventory_path=cloud_inventory,
        terraform_state_path=terraform_state,
        terraform_state_dir=terraform_state_dir,
        state_manifest_path=state_manifest,
        owners_path=owners,
    )
    summary = emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
        policy_path=policy_path,
        evidence_output=evidence_output,
    )
    maybe_exit_for_ci(summary, ci=ci, fail_on=fail_on)


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
    policy_path: str = typer.Option(None, "--policy", help="Policy and waiver YAML."),
    ci: bool = typer.Option(
        False, "--ci", help="Exit non-zero when readiness crosses the configured threshold."
    ),
    fail_on: str = typer.Option(
        None,
        "--fail-on",
        help="CI threshold: none, critical, high, medium, or low.",
    ),
    evidence_output: str = typer.Option(
        None,
        "--evidence-output",
        help="Write readiness_summary.release_evidence to this JSON file.",
    ),
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

    summary = emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
        policy_path=policy_path,
        evidence_output=evidence_output,
    )
    maybe_exit_for_ci(summary, ci=ci, fail_on=fail_on)


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
    policy_path: str = typer.Option(None, "--policy", help="Policy and waiver YAML."),
    ci: bool = typer.Option(
        False, "--ci", help="Exit non-zero when readiness crosses the configured threshold."
    ),
    fail_on: str = typer.Option(
        None,
        "--fail-on",
        help="CI threshold: none, critical, high, medium, or low.",
    ),
    evidence_output: str = typer.Option(
        None,
        "--evidence-output",
        help="Write readiness_summary.release_evidence to this JSON file.",
    ),
    sarif_output: str = typer.Option(
        None,
        "--sarif-output",
        help="Write SARIF 2.1.0 findings for code-scanning systems.",
    ),
    junit_output: str = typer.Option(
        None,
        "--junit-output",
        help="Write JUnit XML findings for CI test-report systems.",
    ),
):
    """Analyze infrastructure production readiness."""

    findings = scan_path(path)
    summary = emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
        policy_path=policy_path,
        evidence_output=evidence_output,
        sarif_output=sarif_output,
        junit_output=junit_output,
        fail_on=fail_on or "high",
    )
    maybe_exit_for_ci(summary, ci=ci, fail_on=fail_on)


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

    emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
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

    emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
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

    emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
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

    emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
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

    emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
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

    emit_readiness(
        findings,
        html=html,
        open_report=open_report,
        output=output,
        environment=environment,
        context_path=context_path,
    )


if __name__ == "__main__":
    configure_logging()
    app()
