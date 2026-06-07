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
    return config.get("environment")


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


def config_tasks(config):
    tasks = config.get("tasks") or {}
    if not isinstance(tasks, dict):
        raise ValueError("tasks must be a YAML mapping.")
    return tasks


def starter_config():
    return """project: beacon-demo
environment: dev
criticality: medium

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
