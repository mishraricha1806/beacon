from beacon.diagnose.diagnostic_engine import build_diagnostic_summary


def finding(rule_id, evidence=None, severity="HIGH", domain="flow"):
    return {
        "rule_id": rule_id,
        "domain": domain,
        "category": "runtime_stability",
        "severity": severity,
        "title": rule_id,
        "impact": "impact",
        "recommendation": "recommendation",
        "file": "flow.yaml",
        "evidence": evidence or {},
        "tags": [],
    }


def test_flow_bottleneck_ranking_identifies_database_first():
    summary = build_diagnostic_summary(
        [
            finding(
                "flow.runtime.downstream_db_bottleneck",
                {
                    "flow": "checkout",
                    "kafka_broker_unhealthy": False,
                    "db_latency_ms": 900,
                },
            ),
            finding(
                "flow.runtime.component_unhealthy",
                {
                    "flow": "checkout",
                    "component": "consumer",
                    "component_type": "consumer",
                },
            ),
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]

    assert ranking["flow"] == "checkout"
    assert ranking["top_bottleneck"] == "database"
    assert ranking["top_confidence"] == "HIGH"
    assert ranking["components"][0]["component"] == "database"
    assert ranking["components"][0]["status"] == "likely_bottleneck"
    assert ranking["components"][0]["evidence_used"]
    assert ranking["components"][0]["source_findings"][0]["rule_id"] == (
        "flow.runtime.downstream_db_bottleneck"
    )
    assert ranking["components"][0]["source_findings"][0]["anchor"].startswith("finding-")
    assert "database connection pool utilization" in ranking["components"][0]["evidence_missing"]
    assert "Inspect connection pools" in ranking["components"][0]["inspect_next"][0]


def test_flow_bottleneck_ranking_identifies_retry_cascade_path():
    summary = build_diagnostic_summary(
        [
            finding(
                "flow.runtime.cascading_latency",
                {
                    "flow": "checkout",
                    "api_timeout_rate_percent": 5,
                    "consumer_retry_rate_percent": 12,
                    "kafka_consumer_lag_increasing": True,
                },
                severity="CRITICAL",
            )
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]
    components = [component["component"] for component in ranking["components"]]

    assert ranking["top_bottleneck"] == "api"
    assert components[:3] == ["api", "consumer", "kafka"]


def test_flow_bottleneck_ranking_carries_business_context_and_blast_radius():
    summary = build_diagnostic_summary(
        [
            finding(
                "flow.runtime.downstream_db_bottleneck",
                {
                    "flow": "checkout",
                    "owner": "team-checkout",
                    "criticality": "critical",
                    "business_impact": "Checkout payment completion can fail.",
                    "affected_services": ["payments", "orders", "fulfillment"],
                    "blast_radius": {"user_impact": "Customers cannot complete checkout."},
                    "kafka_broker_unhealthy": False,
                    "db_latency_ms": 1400,
                },
            )
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]
    impact = summary["flow_impact_summaries"][0]

    assert ranking["owner"] == "team-checkout"
    assert ranking["criticality"] == "critical"
    assert ranking["incident_priority"] == "P1"
    assert ranking["affected_services"] == ["payments", "orders", "fulfillment"]
    assert [node["component_type"] for node in ranking["flow_path"]] == [
        "kafka",
        "consumer",
        "database",
    ]
    assert ranking["flow_path"][-1]["is_bottleneck"] is True
    assert ranking["flow_path"][-1]["evidence_used"]
    assert ranking["flow_path"][-1]["evidence_missing"]
    assert ranking["flow_path"][-1]["inspect_next"]
    assert ranking["flow_path"][-1]["source_findings"][0]["file"] == "flow.yaml"
    assert impact["flow"] == "checkout"
    assert impact["owner"] == "team-checkout"
    assert impact["affected_service_count"] == 3
    assert "Customers cannot complete checkout" in impact["summary"]


def test_flow_path_orders_api_kafka_consumer_database_and_marks_bottleneck():
    summary = build_diagnostic_summary(
        [
            finding(
                "flow.runtime.cascading_latency",
                {
                    "flow": "checkout",
                    "api_timeout_rate_percent": 5,
                    "consumer_retry_rate_percent": 12,
                    "kafka_consumer_lag_increasing": True,
                },
                severity="CRITICAL",
            ),
            finding(
                "flow.runtime.component_unhealthy",
                {
                    "flow": "checkout",
                    "component": "orders-db",
                    "component_type": "database",
                },
            ),
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]
    path = ranking["flow_path"]

    assert [node["component_type"] for node in path] == [
        "api",
        "kafka",
        "consumer",
        "database",
    ]
    assert path[0]["is_bottleneck"] is True
    assert path[0]["label"] == "api"
    assert "API latency" in path[0]["evidence_missing"][0]
    for node in path:
        assert "evidence_used" in node
        assert "evidence_missing" in node
        assert "inspect_next" in node
        assert "source_findings" in node


def test_flow_ranking_imports_owner_and_blast_radius_from_topology_context():
    summary = build_diagnostic_summary(
        [
            finding(
                "topology.service.blast_radius.high",
                {
                    "service": "checkout",
                    "owner": "team-checkout",
                    "criticality": "critical",
                    "business_impact": "Checkout failure blocks payment capture.",
                    "dependents": ["payments", "orders", "fulfillment"],
                    "dependent_count": 3,
                },
                severity="HIGH",
                domain="topology",
            ),
            finding(
                "flow.runtime.downstream_db_bottleneck",
                {
                    "flow": "checkout",
                    "kafka_broker_unhealthy": False,
                    "db_latency_ms": 1400,
                },
            ),
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]
    impact = summary["flow_impact_summaries"][0]

    assert ranking["owner"] == "team-checkout"
    assert ranking["criticality"] == "critical"
    assert ranking["business_impact"] == "Checkout failure blocks payment capture."
    assert ranking["affected_services"] == ["payments", "orders", "fulfillment"]
    assert ranking["blast_radius"]["dependent_count"] == 3
    assert impact["affected_service_count"] == 3


def test_flow_ranking_matches_topology_context_by_alias():
    summary = build_diagnostic_summary(
        [
            finding(
                "topology.service.blast_radius.high",
                {
                    "service": "checkout",
                    "owner": "team-checkout",
                    "criticality": "critical",
                    "business_impact": "Checkout failure blocks payment capture.",
                    "dependents": ["payments", "orders"],
                    "dependent_count": 2,
                    "aliases": ["checkout-api"],
                },
                severity="HIGH",
                domain="topology",
            ),
            finding(
                "flow.runtime.downstream_db_bottleneck",
                {
                    "flow": "checkout-api",
                    "kafka_broker_unhealthy": False,
                    "db_latency_ms": 1400,
                },
            ),
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]

    assert ranking["flow"] == "checkout-api"
    assert ranking["owner"] == "team-checkout"
    assert ranking["criticality"] == "critical"
    assert ranking["affected_services"] == ["payments", "orders"]


def test_flow_ranking_matches_backstage_refs_namespaces_and_common_suffixes():
    summary = build_diagnostic_summary(
        [
            finding(
                "topology.service.blast_radius.high",
                {
                    "service": "component:default/checkout",
                    "owner": "team-checkout",
                    "criticality": "critical",
                    "business_impact": "Checkout is customer-facing.",
                    "dependents": ["mobile-checkout", "order-confirmation"],
                    "dependent_count": 2,
                },
                severity="HIGH",
                domain="topology",
            ),
            finding(
                "flow.runtime.downstream_db_bottleneck",
                {
                    "flow": "payments/checkout-api",
                    "kafka_broker_unhealthy": False,
                    "db_latency_ms": 1400,
                },
            ),
        ]
    )

    ranking = summary["flow_bottleneck_rankings"][0]

    assert ranking["flow"] == "payments/checkout-api"
    assert ranking["owner"] == "team-checkout"
    assert ranking["criticality"] == "critical"
    assert ranking["business_impact"] == "Checkout is customer-facing."


def test_flow_ranking_uses_organization_service_matching_overrides():
    summary = build_diagnostic_summary(
        [
            finding(
                "topology.service.blast_radius.high",
                {
                    "service": "checkout",
                    "owner": "team-checkout",
                    "criticality": "critical",
                    "dependents": ["payments", "orders"],
                    "dependent_count": 2,
                },
                severity="HIGH",
                domain="topology",
            ),
            finding(
                "flow.runtime.downstream_db_bottleneck",
                {
                    "flow": "claim-intake-edge",
                    "kafka_broker_unhealthy": False,
                    "db_latency_ms": 1400,
                },
            ),
        ],
        intelligence_context={
            "service_matching": {
                "aliases": {
                    "checkout": ["claim-intake-edge"],
                }
            }
        },
    )

    ranking = summary["flow_bottleneck_rankings"][0]

    assert ranking["flow"] == "claim-intake-edge"
    assert ranking["owner"] == "team-checkout"
    assert ranking["criticality"] == "critical"


def test_flow_ranking_uses_organization_service_matching_patterns():
    summary = build_diagnostic_summary(
        [
            finding(
                "topology.service.blast_radius.high",
                {
                    "service": "claims-platform",
                    "owner": "team-claims",
                    "criticality": "high",
                    "dependents": ["claims-api", "claims-reporting"],
                    "dependent_count": 2,
                },
                severity="HIGH",
                domain="topology",
            ),
            finding(
                "flow.runtime.downstream_db_bottleneck",
                {
                    "flow": "claims-route-consumer",
                    "kafka_broker_unhealthy": False,
                    "db_latency_ms": 1400,
                },
            ),
        ],
        intelligence_context={
            "service_matching": {
                "patterns": {
                    "claims-*-consumer": "claims-platform",
                }
            }
        },
    )

    ranking = summary["flow_bottleneck_rankings"][0]

    assert ranking["flow"] == "claims-route-consumer"
    assert ranking["owner"] == "team-claims"
    assert ranking["criticality"] == "high"
    assert ranking["affected_services"] == ["claims-api", "claims-reporting"]
