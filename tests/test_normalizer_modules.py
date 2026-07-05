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
            "api_runtime": {"services": [{"name": "checkout-api", "latency_p95_ms": 1500}]},
            "database_runtime": {"databases": [{"name": "orders-db", "latency_ms": 700}]},
        },
        "runtime.yaml",
    )

    resource_types = {resource.type for resource in resources}

    assert "flow_runtime" in resource_types
    assert "api_runtime_service" in resource_types
    assert "database_runtime_instance" in resource_types


def test_backstage_catalog_component_normalizes_to_topology_service():
    from beacon.engine.normalizer import normalize_yaml_document

    resources = normalize_yaml_document(
        {
            "apiVersion": "backstage.io/v1alpha1",
            "kind": "Component",
            "metadata": {
                "name": "checkout",
                "annotations": {
                    "beacon.io/criticality": "critical",
                    "beacon.io/business-impact": "Checkout failure blocks payment capture.",
                    "beacon.io/aliases": "checkout-api,checkout-consumer",
                },
            },
            "spec": {
                "type": "service",
                "owner": "group:team-checkout",
                "dependsOn": ["component:default/payments"],
            },
        },
        "catalog-info.yaml",
    )

    assert len(resources) == 1
    resource = resources[0]
    assert resource.type == "topology_service"
    assert resource.name == "checkout"
    assert resource.attributes["owner"] == "team-checkout"
    assert resource.attributes["criticality"] == "critical"
    assert resource.attributes["aliases"] == ["checkout-api", "checkout-consumer"]
    assert resource.attributes["depends_on"] == ["payments"]
    assert resource.attributes["backstage_entity_ref"] == "component:default/checkout"
