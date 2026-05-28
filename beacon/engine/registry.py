class RuleRegistry:
    def __init__(self):
        self.rules = {}

    def register(self, rule):
        if rule.rule_id in self.rules:
            raise ValueError(f"Duplicate rule_id registered: {rule.rule_id}")

        self.rules[rule.rule_id] = rule

    def get_all(self):
        return list(self.rules.values())

    def get_for_resource(self, resource):
        return [
            rule
            for rule in self.rules.values()
            if rule.enabled and resource.type in rule.supported_resource_types
        ]


registry = RuleRegistry()
