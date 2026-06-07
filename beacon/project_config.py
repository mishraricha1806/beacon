from pathlib import Path

import yaml


CONFIG_FILENAMES = ("beacon.yaml", "beacon.yml", ".beacon.yaml")


def discover_config(start_path=None):
    """Find a Beacon project config by walking from cwd toward filesystem root."""
    current = Path(start_path or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        for filename in CONFIG_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return candidate

    return None


def load_project_config(path=None, start_path=None):
    config_path = Path(path).resolve() if path else discover_config(start_path)
    if not config_path:
        return None, None

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{config_path} must contain a YAML mapping.")

    return data, config_path


def resolve_config_path(config_path, value):
    if value is None:
        return None

    path = Path(value).expanduser()
    if path.is_absolute():
        return str(path)

    return str((config_path.parent / path).resolve())


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def config_environment(config):
    environment = config.get("environment")
    if isinstance(environment, dict):
        return environment.get("name") or environment.get("profile")
    return environment


def config_environment_model(config):
    environment = config.get("environment") or {}
    if isinstance(environment, str):
        environment = {"name": environment}

    services = as_list(environment.get("services"))
    dependencies = environment.get("dependencies") or {}
    if not isinstance(dependencies, dict):
        dependencies = {}

    return {
        "name": environment.get("name") or config.get("project") or "unknown",
        "profile": environment.get("profile") or environment.get("name"),
        "criticality": environment.get("criticality") or config.get("criticality") or "medium",
        "business_flows": as_list(environment.get("business_flows")),
        "services": services,
        "service_count": len(services),
        "dependencies": dependencies,
        "dependency_domains": sorted(dependencies),
        "rto": environment.get("rto"),
        "rpo": environment.get("rpo"),
        "owner": environment.get("owner") or config.get("owner"),
    }


def config_context_path(config, config_path):
    intelligence = config.get("intelligence") or {}
    context = intelligence.get("context") or config.get("context")
    return resolve_config_path(config_path, context)


def config_report_options(config):
    report = config.get("report") or {}
    formats = set(as_list(report.get("format") or ["html", "terminal"]))
    return {
        "html": "html" in formats,
        "open_report": bool(report.get("open", False)),
        "output": "json" if formats == {"json"} else "terminal",
    }


def config_readiness_includes(config, config_path):
    readiness = config.get("readiness") or {}
    includes = as_list(readiness.get("include") or readiness.get("paths") or ["."])
    return [resolve_config_path(config_path, item) for item in includes]


def config_live_inputs(config, config_path):
    live = config.get("live") or {}
    if not isinstance(live, dict):
        return {}

    kafka = live.get("kafka") or {}
    kubernetes = live.get("kubernetes") or {}
    schema_registry = live.get("schema_registry") or live.get("schema-registry") or {}
    runtime = live.get("runtime") or {}

    return {
        "kafka_bootstrap_server": kafka.get("bootstrap_server"),
        "kafka_security_protocol": kafka.get("security_protocol") or "PLAINTEXT",
        "kafka_ca_cert": resolve_config_path(config_path, kafka.get("ca_cert")),
        "kafka_client_cert": resolve_config_path(config_path, kafka.get("client_cert")),
        "kafka_client_key": resolve_config_path(config_path, kafka.get("client_key")),
        "kafka_topic": kafka.get("topic"),
        "kafka_consumer_group": kafka.get("consumer_group"),
        "kafka_max_topics": kafka.get("max_topics", 50),
        "kafka_max_groups": kafka.get("max_groups", 20),
        "kubernetes_live": bool(kubernetes.get("enabled", False)),
        "kubernetes_namespace": kubernetes.get("namespace"),
        "kubernetes_context": kubernetes.get("context"),
        "kubernetes_kubeconfig": resolve_config_path(config_path, kubernetes.get("kubeconfig")),
        "schema_registry_path": resolve_config_path(config_path, schema_registry.get("config")),
        "snapshot_path": resolve_config_path(config_path, runtime.get("snapshot")),
        "flow_path": resolve_config_path(config_path, runtime.get("flow")),
        "prometheus_path": resolve_config_path(config_path, runtime.get("prometheus")),
        "opentelemetry_path": resolve_config_path(config_path, runtime.get("opentelemetry")),
        "kafka_acl_path": resolve_config_path(config_path, kafka.get("acls")),
        "kafka_history_path": resolve_config_path(config_path, kafka.get("history")),
        "deployment_events_path": resolve_config_path(
            config_path, runtime.get("deployment_events")
        ),
    }


def config_tasks(config):
    tasks = config.get("tasks") or {}
    if not isinstance(tasks, dict):
        raise ValueError("tasks must be a YAML mapping.")
    return tasks


def starter_config():
    return """project: beacon-demo
environment:
  name: dev
  profile: dev
  criticality: medium
  owner: platform-team
  rto: 4h
  rpo: 24h
  business_flows:
    - demo-checkout
  services:
    - checkout-api
    - payment-worker
  dependencies:
    kafka:
      clusters:
        - demo-kafka
    kubernetes:
      clusters:
        - local-dev
    storage:
      buckets:
        - customer-exports

readiness:
  include:
    - ./examples/supported
  exclude:
    - ./reports
    - ./.terraform

intelligence:
  context: ./examples/supported/intelligence/context.yaml

report:
  format:
    - terminal
    - html
  open: false

live:
  runtime:
    snapshot: ./examples/supported/runtime/all-runtime.yaml
    flow: ./examples/supported/runtime/flow-runtime.yaml
    deployment_events: ./examples/supported/deployments/events.yaml
    opentelemetry: ./examples/supported/opentelemetry/checkout-otel.yaml
  kafka:
    acls: ./examples/supported/kafka/acls.yaml
    history: ./examples/supported/kafka/history.yaml
  schema_registry:
    config: ./examples/supported/kafka/schema-registry.yaml

tasks:
  prod-check:
    command: readiness
    environment: prod

  dev-check:
    command: readiness
    environment: dev

  kafka-incident-demo:
    command: diagnose kafka-runtime
    path: ./examples/supported/kafka/scenarios/quota-throttle-runtime.yaml
"""
