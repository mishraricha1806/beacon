import fnmatch
import re
from collections import defaultdict

from beacon.intelligence.context import service_matching_aliases, service_matching_patterns

CONFIDENCE_BY_SCORE = [
    (80, "HIGH"),
    (45, "MEDIUM"),
    (15, "LOW"),
]

FLOW_PATH_ORDER = {
    "api": 10,
    "kafka": 20,
    "producer": 20,
    "consumer": 30,
    "database": 40,
    "storage": 50,
    "deployment": 5,
}

SERVICE_SUFFIXES = (
    "-api",
    "-service",
    "-svc",
    "-consumer",
    "-producer",
    "-worker",
    "-app",
)


def build_flow_bottleneck_rankings(findings, intelligence_context=None):
    flow_scores = defaultdict(lambda: defaultdict(new_component_score))
    flow_context = defaultdict(new_flow_context)
    topology_context = {}
    matching_aliases = service_matching_aliases(intelligence_context)
    matching_patterns = service_matching_patterns(intelligence_context)

    for finding in findings:
        apply_finding(flow_scores, finding)
        capture_flow_context(flow_context, finding)
        capture_topology_context(topology_context, finding)

    apply_service_matching_overrides(topology_context, matching_aliases)

    rankings = []
    for flow, components in sorted(flow_scores.items()):
        context = flow_context.get(flow, {})
        merge_context(
            context,
            topology_context_for_flow(
                topology_context,
                flow,
                matching_patterns=matching_patterns,
            ),
        )
        ranked = []
        for component, score_data in components.items():
            component_type = score_data["component_type"] or component
            ranked.append(
                {
                    "rank": 0,
                    "component": component,
                    "component_type": component_type,
                    "score": score_data["score"],
                    "confidence": confidence_for_score(score_data["score"]),
                    "status": status_for_score(score_data["score"]),
                    "reason": score_data["reasons"][0],
                    "evidence": score_data["evidence"][:5],
                    "evidence_used": evidence_used(score_data),
                    "evidence_missing": evidence_missing(component_type, score_data),
                    "inspect_next": inspect_next(component_type, score_data),
                    "source_findings": source_findings(score_data),
                }
            )

        ranked.sort(key=lambda item: (-item["score"], item["component"]))
        for index, item in enumerate(ranked, start=1):
            item["rank"] = index

        if ranked:
            top_bottleneck = ranked[0]["component"]
            rankings.append(
                {
                    "flow": flow,
                    "owner": context.get("owner"),
                    "criticality": context.get("criticality"),
                    "business_impact": context.get("business_impact"),
                    "blast_radius": context.get("blast_radius"),
                    "affected_services": context.get("affected_services") or [],
                    "top_bottleneck": top_bottleneck,
                    "top_confidence": ranked[0]["confidence"],
                    "incident_priority": incident_priority(
                        ranked[0]["score"],
                        context.get("criticality"),
                        len(context.get("affected_services") or []),
                    ),
                    "flow_path": build_flow_path(ranked, top_bottleneck),
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


def new_flow_context():
    return {
        "owner": None,
        "criticality": None,
        "business_impact": None,
        "blast_radius": None,
        "affected_services": [],
    }


def capture_flow_context(flow_context, finding):
    evidence = finding.get("evidence") or {}
    flow = evidence.get("flow") or "unknown-flow"
    context = flow_context[flow]

    for key in ("owner", "criticality", "business_impact", "blast_radius"):
        if context.get(key) in (None, "", [], {}) and evidence.get(key) not in (
            None,
            "",
            [],
            {},
        ):
            context[key] = evidence.get(key)

    affected = evidence.get("affected_services") or []
    if isinstance(affected, str):
        affected = [affected]
    for service in affected:
        if service not in context["affected_services"]:
            context["affected_services"].append(service)


def capture_topology_context(topology_context, finding):
    if finding.get("domain") != "topology":
        return

    evidence = finding.get("evidence") or {}
    service = evidence.get("service")
    if not service:
        return

    service_key = str(service)
    context = topology_context.setdefault(service_key, new_flow_context())
    merge_context(
        context,
        {
            "owner": evidence.get("owner"),
            "criticality": evidence.get("criticality"),
            "business_impact": evidence.get("business_impact"),
            "blast_radius": topology_blast_radius(evidence),
            "affected_services": evidence.get("dependents") or [],
        },
    )

    for key in service_match_keys(service_key):
        topology_context[key] = context

    for alias in evidence.get("aliases") or []:
        for key in service_match_keys(alias):
            topology_context[key] = context


def apply_service_matching_overrides(topology_context, aliases):
    for canonical, alias_values in (aliases or {}).items():
        context = topology_context_for_flow(topology_context, canonical)
        if not context:
            continue

        if isinstance(alias_values, str):
            alias_values = [alias_values]

        for alias in alias_values or []:
            for key in service_match_keys(alias):
                topology_context[key] = context


def topology_blast_radius(evidence):
    dependents = evidence.get("dependents") or []
    if not dependents and not evidence.get("dependent_count"):
        return None
    return {
        "dependent_count": evidence.get("dependent_count", len(dependents)),
        "dependents": dependents,
        "impact": evidence.get("business_impact")
        or "A failure can affect dependent services in the topology graph.",
    }


def topology_context_for_flow(topology_context, flow, matching_patterns=None):
    if not flow:
        return {}
    pattern_context = topology_context_for_pattern(
        topology_context,
        flow,
        matching_patterns or {},
    )
    if pattern_context:
        return pattern_context

    flow_keys = service_match_keys(flow)
    for key in flow_keys:
        if key in topology_context:
            return topology_context[key]

    normalized_flow = normalize_context_key(flow)
    for service_key, context in topology_context.items():
        normalized_service = normalize_context_key(service_key)
        if service_keys_related(normalized_flow, normalized_service):
            return context

    return {}


def topology_context_for_pattern(topology_context, flow, patterns):
    normalized_flow = normalize_context_key(flow)
    for pattern, canonical in patterns.items():
        normalized_pattern = normalize_pattern_key(pattern)
        if not fnmatch.fnmatch(normalized_flow, normalized_pattern):
            continue

        canonical_values = canonical if isinstance(canonical, list) else [canonical]
        for canonical_value in canonical_values:
            context = topology_context_for_flow(topology_context, canonical_value)
            if context:
                return context

    return {}


def merge_context(target, source):
    if not source:
        return target

    for key in ("owner", "criticality", "business_impact", "blast_radius"):
        value = source.get(key)
        if target.get(key) in (None, "", [], {}) and value not in (None, "", [], {}):
            target[key] = value

    for service in source.get("affected_services") or []:
        if service not in target["affected_services"]:
            target["affected_services"].append(service)

    return target


def normalize_context_key(value):
    value = str(value or "").strip().lower().replace("_", "-")
    value = value.replace(":", "/")
    if "/" in value:
        value = value.rsplit("/", 1)[1]
    return value.replace(".", "-")


def normalize_pattern_key(value):
    value = str(value or "").strip().lower().replace("_", "-")
    value = value.replace(":", "/")
    if "/" in value:
        value = value.rsplit("/", 1)[1]
    return value.replace(".", "-")


def service_match_keys(value):
    normalized = normalize_context_key(value)
    if not normalized:
        return set()

    keys = {normalized}
    for suffix in SERVICE_SUFFIXES:
        if normalized.endswith(suffix):
            keys.add(normalized[: -len(suffix)])

    parts = [part for part in normalized.split("-") if part]
    if len(parts) > 1:
        keys.add(parts[0])
        keys.add("-".join(parts[:2]))

    return {key for key in keys if key}


def service_keys_related(flow_key, service_key):
    if not flow_key or not service_key:
        return False
    if flow_key == service_key:
        return True
    flow_keys = service_match_keys(flow_key)
    service_keys = service_match_keys(service_key)
    if flow_keys.intersection(service_keys):
        return True
    return flow_key.startswith(service_key + "-") or service_key.startswith(flow_key + "-")


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
            "file": finding.get("file"),
            "anchor": finding_anchor_id(finding),
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


def incident_priority(score, criticality, affected_count):
    criticality = str(criticality or "").lower()
    if criticality in {"critical", "tier-0", "tier_0", "tier0"} and score >= 45:
        return "P1"
    if score >= 80 and affected_count >= 3:
        return "P1"
    if score >= 80:
        return "P2"
    if score >= 45:
        return "P3"
    return "P4"


def build_flow_path(components, top_bottleneck):
    ordered = sorted(
        components,
        key=lambda item: (
            FLOW_PATH_ORDER.get(str(item.get("component_type") or "").lower(), 90),
            item.get("component") or "",
        ),
    )
    path = []
    seen = set()

    for component in ordered:
        name = component.get("component")
        component_type = component.get("component_type") or name
        key = (name, component_type)
        if key in seen:
            continue
        seen.add(key)
        path.append(
            {
                "component": name,
                "component_type": component_type,
                "status": component.get("status"),
                "confidence": component.get("confidence"),
                "is_bottleneck": is_bottleneck_component(component, top_bottleneck),
                "label": flow_path_label(component),
                "evidence_used": component.get("evidence_used") or [],
                "evidence_missing": component.get("evidence_missing") or [],
                "inspect_next": component.get("inspect_next") or [],
                "source_findings": component.get("source_findings") or [],
            }
        )

    return path


def is_bottleneck_component(component, top_bottleneck):
    component_name = component.get("component")
    component_type = component.get("component_type")
    return component_name == top_bottleneck or component_type == top_bottleneck


def flow_path_label(component):
    component_type = component.get("component_type") or "component"
    component_name = component.get("component")
    if component_name and component_name != component_type:
        return f"{component_name} ({component_type})"
    return str(component_name or component_type)


def evidence_used(score_data):
    used = []
    for item in score_data.get("evidence", [])[:5]:
        rule_id = item.get("rule_id")
        title = item.get("title") or rule_id
        severity = item.get("severity")
        if not rule_id and not title:
            continue
        label = f"{severity}: {title}" if severity else title
        if label not in used:
            used.append(label)
    return used


def source_findings(score_data):
    sources = []
    seen = set()
    for item in score_data.get("evidence", [])[:8]:
        key = (item.get("rule_id"), item.get("title"), item.get("file"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "rule_id": item.get("rule_id"),
                "severity": item.get("severity"),
                "title": item.get("title") or item.get("rule_id"),
                "file": item.get("file"),
                "anchor": item.get("anchor"),
            }
        )
    return sources


def finding_anchor_id(finding):
    base = "|".join(
        str(value or "")
        for value in (
            finding.get("rule_id"),
            finding.get("title"),
            finding.get("file"),
        )
    )
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-").lower()
    return f"finding-{slug or 'unknown'}"


def evidence_missing(component_type, score_data):
    component_type = str(component_type or "").lower()
    rule_ids = {item.get("rule_id") for item in score_data.get("evidence", [])}

    missing_by_type = {
        "api": [
            "API latency and error trend before/after the incident window",
            "retry and timeout rates by endpoint",
            "recent deployment or feature-flag changes",
        ],
        "kafka": [
            "broker request latency, queue pressure, and network saturation",
            "producer rate and payload-size trend",
            "under-replicated/offline partition evidence",
        ],
        "consumer": [
            "consumer processing latency and thread/concurrency saturation",
            "consumer group state, rebalance count, and member churn",
            "downstream dependency latency seen by the consumer",
        ],
        "database": [
            "database connection pool utilization",
            "slow query, lock wait, and transaction latency evidence",
            "storage and I/O saturation by database node",
        ],
        "storage": [
            "capacity trend and time-to-full estimate",
            "IOPS/throughput saturation by volume or bucket",
            "backup freshness and restore test evidence",
        ],
        "deployment": [
            "deployment diff and rollout timeline",
            "before/after latency, error, and lag metrics",
            "rollback readiness and feature-flag status",
        ],
    }
    missing = missing_by_type.get(
        component_type,
        ["component-specific telemetry and recent change context"],
    )

    if "flow.runtime.downstream_db_bottleneck" in rule_ids and component_type == "database":
        return missing[:2]
    if "flow.runtime.cascading_latency" in rule_ids and component_type in {"api", "consumer"}:
        return missing[:2]
    return missing


def inspect_next(component_type, score_data):
    component_type = str(component_type or "").lower()
    actions_by_type = {
        "api": [
            "Inspect endpoint latency, timeout, and retry dashboards first.",
            "Compare errors with the last deployment or configuration change.",
        ],
        "kafka": [
            "Check broker health, request latency, and partition-level lag before scaling.",
            "Validate producer throughput and payload-size changes.",
        ],
        "consumer": [
            "Check consumer processing time, group stability, and downstream call latency.",
            "Review recent consumer deployments and rebalance activity.",
        ],
        "database": [
            "Inspect connection pools, slow queries, locks, and storage I/O first.",
            "Avoid scaling Kafka before validating downstream database pressure.",
        ],
        "storage": [
            "Check capacity growth, IOPS saturation, and backup freshness.",
            "Create temporary headroom only after identifying the growth driver.",
        ],
        "deployment": [
            "Review the deployment diff, rollout health, and rollback safety.",
            "Compare before/after metrics for the changed service.",
        ],
    }
    return actions_by_type.get(
        component_type,
        ["Inspect component health, saturation, and recent changes."],
    )


def build_flow_impact_summaries(rankings):
    summaries = []
    for ranking in rankings:
        affected = ranking.get("affected_services") or []
        blast_radius = ranking.get("blast_radius") or {}
        summaries.append(
            {
                "flow": ranking.get("flow"),
                "owner": ranking.get("owner") or "unknown",
                "criticality": ranking.get("criticality") or "unknown",
                "business_impact": ranking.get("business_impact")
                or default_business_impact(ranking),
                "incident_priority": ranking.get("incident_priority"),
                "top_bottleneck": ranking.get("top_bottleneck"),
                "top_confidence": ranking.get("top_confidence"),
                "affected_services": affected,
                "affected_service_count": len(affected),
                "blast_radius": blast_radius,
                "summary": flow_impact_sentence(ranking, affected, blast_radius),
            }
        )
    return summaries


def default_business_impact(ranking):
    flow = ranking.get("flow") or "this flow"
    bottleneck = ranking.get("top_bottleneck") or "a component"
    return f"Runtime degradation in {flow} is most likely constrained by {bottleneck}."


def flow_impact_sentence(ranking, affected, blast_radius):
    flow = ranking.get("flow") or "unknown flow"
    bottleneck = ranking.get("top_bottleneck") or "unknown component"
    owner = ranking.get("owner") or "unknown owner"
    criticality = ranking.get("criticality") or "unknown criticality"
    priority = ranking.get("incident_priority") or "P4"
    affected_count = len(affected)
    user_impact = ""
    if isinstance(blast_radius, dict):
        user_impact = blast_radius.get("user_impact") or blast_radius.get("impact") or ""

    sentence = (
        f"{flow} is {criticality} and owned by {owner}; Beacon ranks {bottleneck} "
        f"as the most likely bottleneck with {priority} incident priority."
    )
    if affected_count:
        sentence += f" {affected_count} dependent service(s) are in the blast radius."
    if user_impact:
        sentence += f" Business impact: {user_impact}"
    return sentence
