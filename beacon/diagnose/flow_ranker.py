from collections import defaultdict

CONFIDENCE_BY_SCORE = [
    (80, "HIGH"),
    (45, "MEDIUM"),
    (15, "LOW"),
]


def build_flow_bottleneck_rankings(findings):
    flow_scores = defaultdict(lambda: defaultdict(new_component_score))

    for finding in findings:
        apply_finding(flow_scores, finding)

    rankings = []
    for flow, components in sorted(flow_scores.items()):
        ranked = []
        for component, score_data in components.items():
            ranked.append(
                {
                    "rank": 0,
                    "component": component,
                    "component_type": score_data["component_type"] or component,
                    "score": score_data["score"],
                    "confidence": confidence_for_score(score_data["score"]),
                    "status": status_for_score(score_data["score"]),
                    "reason": score_data["reasons"][0],
                    "evidence": score_data["evidence"][:5],
                }
            )

        ranked.sort(key=lambda item: (-item["score"], item["component"]))
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index

        if ranked:
            rankings.append(
                {
                    "flow": flow,
                    "top_bottleneck": ranked[0]["component"],
                    "top_confidence": ranked[0]["confidence"],
                    "components": ranked[:6],
                }
            )

    return rankings


def new_component_score():
    return {
        "score": 0,
        "component_type": None,
        "reasons": [],
        "evidence": [],
    }


def apply_finding(flow_scores, finding):
    rule_id = finding.get("rule_id")
    evidence = finding.get("evidence") or {}
    flow = evidence.get("flow") or "unknown-flow"

    if rule_id == "flow.runtime.downstream_db_bottleneck":
        add_score(
            flow_scores,
            flow,
            "database",
            90,
            "Database latency is high while Kafka appears healthy.",
            finding,
            component_type="database",
        )
        add_score(
            flow_scores,
            flow,
            "consumer",
            35,
            "Consumer lag is increasing behind downstream processing.",
            finding,
            component_type="consumer",
        )
        if evidence.get("kafka_broker_unhealthy") is False:
            add_score(
                flow_scores,
                flow,
                "kafka",
                5,
                "Kafka broker health evidence makes Kafka less likely as the bottleneck.",
                finding,
                component_type="kafka",
            )
        return

    if rule_id == "flow.runtime.cascading_latency":
        add_score(
            flow_scores,
            flow,
            "api",
            75,
            "API timeouts are part of a cascading latency pattern.",
            finding,
            component_type="api",
        )
        add_score(
            flow_scores,
            flow,
            "consumer",
            65,
            "Consumer retries are amplifying the flow degradation.",
            finding,
            component_type="consumer",
        )
        add_score(
            flow_scores,
            flow,
            "kafka",
            30,
            "Kafka lag is participating in the cascade.",
            finding,
            component_type="kafka",
        )
        return

    if rule_id == "flow.runtime.deployment_correlated_degradation":
        add_score(
            flow_scores,
            flow,
            "deployment",
            70,
            "Recent deployment timing aligns with flow degradation.",
            finding,
            component_type="deployment",
        )
        if evidence.get("api_error_rate_percent") is not None:
            add_score(
                flow_scores,
                flow,
                "api",
                40,
                "API error or latency signals increased after deployment.",
                finding,
                component_type="api",
            )
        return

    if rule_id == "flow.runtime.component_unhealthy":
        component = evidence.get("component") or "unknown-component"
        add_score(
            flow_scores,
            flow,
            component,
            45,
            "Flow component is marked unhealthy.",
            finding,
            component_type=evidence.get("component_type"),
        )
        return

    if rule_id in {
        "database.runtime.latency.high",
        "database.runtime.connection_pool.exhaustion",
        "database.runtime.lock_contention.high",
    }:
        add_score(
            flow_scores,
            flow,
            "database",
            35,
            "Database runtime finding contributes bottleneck evidence.",
            finding,
            component_type="database",
        )
        return

    if rule_id in {
        "api.runtime.latency_p95.high",
        "api.runtime.error_rate.high",
        "api.runtime.timeout_rate.high",
        "api.runtime.retry_amplification",
    }:
        add_score(
            flow_scores,
            flow,
            "api",
            35,
            "API runtime finding contributes bottleneck evidence.",
            finding,
            component_type="api",
        )
        return

    if rule_id in {
        "kafka.consumer_group.lag.high",
        "kafka.history.consumer_lag.growing",
        "kafka.runtime.consumer_lag.increasing_under_pressure",
    }:
        add_score(
            flow_scores,
            flow,
            "consumer",
            30,
            "Kafka lag indicates consumers are not keeping up.",
            finding,
            component_type="consumer",
        )
        return

    if rule_id in {
        "storage.runtime.capacity.high",
        "storage.runtime.iops_saturation.high",
        "storage.runtime.growth_rate.high",
    }:
        add_score(
            flow_scores,
            flow,
            "storage",
            30,
            "Storage pressure contributes bottleneck evidence.",
            finding,
            component_type="storage",
        )


def add_score(
    flow_scores,
    flow,
    component,
    score,
    reason,
    finding,
    component_type=None,
):
    item = flow_scores[flow][component]
    item["score"] += score
    item["component_type"] = item["component_type"] or component_type
    if reason not in item["reasons"]:
        item["reasons"].append(reason)
    item["evidence"].append(
        {
            "rule_id": finding.get("rule_id"),
            "severity": finding.get("severity"),
            "title": finding.get("title"),
        }
    )


def confidence_for_score(score):
    for minimum, confidence in CONFIDENCE_BY_SCORE:
        if score >= minimum:
            return confidence
    return "LOW"


def status_for_score(score):
    if score >= 80:
        return "likely_bottleneck"
    if score >= 45:
        return "possible_bottleneck"
    if score >= 15:
        return "contributing_signal"
    return "unlikely"
