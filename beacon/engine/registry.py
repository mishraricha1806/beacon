RULE_REGISTRY = []


def register_rule(rule):
    RULE_REGISTRY.append(rule)


def get_rules():
    return RULE_REGISTRY