import importlib

BUILTIN_RULE_MODULES = (
    "beacon.rules.api_runtime_registered_rules",
    "beacon.rules.cicd_registered_rules",
    "beacon.rules.cloud_registered_rules",
    "beacon.rules.database_runtime_registered_rules",
    "beacon.rules.flow_registered_rules",
    "beacon.rules.iam_registered_rules",
    "beacon.rules.kafka_registered_rules",
    "beacon.rules.kubernetes_registered_rules",
    "beacon.rules.kubernetes_runtime_registered_rules",
    "beacon.rules.storage_registered_rules",
    "beacon.rules.storage_runtime_registered_rules",
    "beacon.rules.topology_registered_rules",
)

_LOADING_BUILTINS = False


def ensure_builtin_rules_loaded():
    global _LOADING_BUILTINS
    if registry.rules or _LOADING_BUILTINS:
        return

    _LOADING_BUILTINS = True
    try:
        for module_name in BUILTIN_RULE_MODULES:
            importlib.import_module(module_name)
    finally:
        _LOADING_BUILTINS = False


class RuleRegistry:
    def __init__(self):
        self.rules = {}

    def register(self, rule):
        if rule.rule_id in self.rules:
            raise ValueError(f"Duplicate rule_id registered: {rule.rule_id}")

        self.rules[rule.rule_id] = rule

    def get_all(self):
        ensure_builtin_rules_loaded()
        return list(self.rules.values())

    def get_by_id(self, rule_id):
        ensure_builtin_rules_loaded()
        return self.rules.get(rule_id)

    def get_for_resource(self, resource):
        ensure_builtin_rules_loaded()
        return [
            rule
            for rule in self.rules.values()
            if rule.enabled and resource.type in rule.supported_resource_types
        ]

    def clear(self):
        self.rules = {}


registry = RuleRegistry()


def register_rule(rule):
    registry.register(rule)


def get_rules():
    ensure_builtin_rules_loaded()
    return registry.get_all()
