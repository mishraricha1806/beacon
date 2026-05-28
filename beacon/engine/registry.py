class RuleRegistry:
    def __init__(self):
        self.rules = {}

    def register(self, rule):
        if rule.rule_id in self.rules:
            raise ValueError(f"Duplicate rule_id registered: {rule.rule_id}")

        self.rules[rule.rule_id] = rule

    def get_all(self):
        return list(self.rules.values())

    def get_by_id(self, rule_id):
        return self.rules.get(rule_id)

    def get_for_resource(self, resource):
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
    return registry.get_all()
