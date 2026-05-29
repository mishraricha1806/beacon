def test_engine_normalizer_facade_preserves_imports():
    from beacon.engine.normalizer import (
        normalize_kafka_config,
        normalize_runtime_sections,
        normalize_terraform_config,
        normalize_yaml_document,
    )

    assert normalize_kafka_config
    assert normalize_terraform_config
    assert normalize_yaml_document
    assert normalize_runtime_sections


def test_mixed_runtime_sections_are_normalized_by_domain_modules():
    from beacon.engine.normalizer import normalize_yaml_document

    resources = normalize_yaml_document(
        {
            "flow_runtime": {
                "name": "checkout",
                "signals": {"kafka_consumer_lag_increasing": True},
            },
            "api_runtime": {
                "services": [
                    {"name": "checkout-api", "latency_p95_ms": 1500}
                ]
            },
            "database_runtime": {
                "databases": [
                    {"name": "orders-db", "latency_ms": 700}
                ]
            },
        },
        "runtime.yaml",
    )

    resource_types = {resource.type for resource in resources}

    assert "flow_runtime" in resource_types
    assert "api_runtime_service" in resource_types
    assert "database_runtime_instance" in resource_types
