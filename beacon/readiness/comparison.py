def compare_release_evidence(before, after):
    before_blocking = risk_index(before.get("blocking_risks") or [])
    after_blocking = risk_index(after.get("blocking_risks") or [])
    before_major = risk_index(before.get("major_risks") or [])
    after_major = risk_index(after.get("major_risks") or [])

    before_score = numeric_score(before.get("score"))
    after_score = numeric_score(after.get("score"))
    score_delta = None
    if before_score is not None and after_score is not None:
        score_delta = after_score - before_score

    new_blockers = sorted(
        (after_blocking[key] for key in after_blocking.keys() - before_blocking.keys()),
        key=risk_sort_key,
    )
    resolved_blockers = sorted(
        (before_blocking[key] for key in before_blocking.keys() - after_blocking.keys()),
        key=risk_sort_key,
    )
    new_major_risks = sorted(
        (after_major[key] for key in after_major.keys() - before_major.keys()),
        key=risk_sort_key,
    )
    resolved_major_risks = sorted(
        (before_major[key] for key in before_major.keys() - after_major.keys()),
        key=risk_sort_key,
    )

    verdict = comparison_verdict(
        score_delta=score_delta,
        new_blockers=new_blockers,
        resolved_blockers=resolved_blockers,
        before_decision=before.get("decision"),
        after_decision=after.get("decision"),
    )

    before_counts = before.get("counts") or {}
    after_counts = after.get("counts") or {}

    return {
        "verdict": verdict,
        "before": {
            "decision": before.get("decision"),
            "score": before.get("score"),
            "environment": before.get("environment"),
            "survivability": before.get("survivability"),
        },
        "after": {
            "decision": after.get("decision"),
            "score": after.get("score"),
            "environment": after.get("environment"),
            "survivability": after.get("survivability"),
        },
        "score_delta": score_delta,
        "decision_changed": before.get("decision") != after.get("decision"),
        "new_blocking_risks": new_blockers,
        "resolved_blocking_risks": resolved_blockers,
        "new_major_risks": new_major_risks,
        "resolved_major_risks": resolved_major_risks,
        "counts_delta": count_deltas(before_counts, after_counts),
        "summary": comparison_summary(
            verdict,
            score_delta,
            new_blockers,
            resolved_blockers,
            before.get("decision"),
            after.get("decision"),
        ),
    }


def risk_index(risks):
    indexed = {}
    for risk in risks:
        indexed[risk_identity(risk)] = {
            "severity": risk.get("severity"),
            "title": risk.get("title"),
            "category": risk.get("category"),
            "affected_count": risk.get("affected_count", 0),
            "recommendation": risk.get("recommendation"),
            "examples": risk.get("examples", [])[:5],
        }
    return indexed


def risk_identity(risk):
    return (
        str(risk.get("title") or "").strip().lower(),
        str(risk.get("category") or "").strip().lower(),
    )


def risk_sort_key(risk):
    severity_order = {"ERROR": 0, "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "INFO": 5}
    return (
        severity_order.get(str(risk.get("severity") or "").upper(), 99),
        str(risk.get("title") or ""),
    )


def numeric_score(value):
    if isinstance(value, (int, float)):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def count_deltas(before_counts, after_counts):
    keys = sorted(set(before_counts) | set(after_counts))
    return {key: (after_counts.get(key, 0) or 0) - (before_counts.get(key, 0) or 0) for key in keys}


def comparison_verdict(
    score_delta,
    new_blockers,
    resolved_blockers,
    before_decision,
    after_decision,
):
    if new_blockers or (score_delta is not None and score_delta < 0):
        return "REGRESSED"
    if before_decision != after_decision and after_decision == "READY":
        return "IMPROVED"
    if resolved_blockers or (score_delta is not None and score_delta > 0):
        return "IMPROVED"
    return "UNCHANGED"


def comparison_summary(
    verdict,
    score_delta,
    new_blockers,
    resolved_blockers,
    before_decision,
    after_decision,
):
    pieces = [f"Readiness {verdict.lower()}."]
    if score_delta is not None:
        direction = (
            "increased" if score_delta > 0 else "decreased" if score_delta < 0 else "stayed flat"
        )
        pieces.append(f"Score {direction} by {abs(score_delta)} point(s).")
    if before_decision != after_decision:
        pieces.append(f"Decision changed from {before_decision} to {after_decision}.")
    if new_blockers:
        pieces.append(f"{len(new_blockers)} new production blocker(s) appeared.")
    if resolved_blockers:
        pieces.append(f"{len(resolved_blockers)} production blocker(s) were resolved.")
    return " ".join(pieces)
