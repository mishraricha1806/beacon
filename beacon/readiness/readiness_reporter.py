from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def print_readiness_summary(summary):
    console.print("\n[bold cyan]Beacon Production Readiness[/bold cyan]\n")

    if summary.get("score_status") == "BLOCKED_BY_ANALYSIS_ERROR":
        console.print(
            f"[bold]Production Readiness Score:[/bold] BLOCKED ({summary['score']}/100 raw signal score)"
        )
    else:
        console.print(f"[bold]Production Readiness Score:[/bold] {summary['score']}/100")
    console.print(f"[bold]Operational Survivability:[/bold] {summary['survivability']}\n")

    if summary.get("release_gate"):
        gate = summary["release_gate"]
        console.print(f"[bold]{gate['question']}[/bold] {gate['answer']}")
        console.print(f"- Decision: {gate['decision']}")
        console.print(f"- Score: {gate['score']}/100")
        if gate.get("why_not"):
            console.print("- Why not:")
            for reason in gate["why_not"][:3]:
                console.print(f"  - {reason}")
        if gate.get("fix_first"):
            console.print("- Fix first:")
            for action in gate["fix_first"][:3]:
                console.print(f"  - {action}")
        console.print(f"- Business risk: {gate['business_risk']}\n")

    console.print(f"[bold]Business Summary:[/bold] {summary['business_summary']}")
    console.print(f"[bold]Recommended Action:[/bold] {summary['recommended_action']}\n")

    if summary.get("environment"):
        console.print(f"[bold]Environment:[/bold] {summary['environment']}")
    if (summary.get("intelligence_context") or {}).get("loaded"):
        context = summary["intelligence_context"]
        console.print(
            "[bold]Intelligence Context:[/bold] "
            f"{context.get('organization') or 'loaded'} "
            f"(topic patterns: {context.get('topic_patterns', 0)}, "
            f"rule overrides: {context.get('rule_overrides', 0)})"
        )
    if summary.get("risk_points") is not None:
        console.print(
            "[bold]Weighted Risk Points:[/bold] "
            f"{summary['risk_points']} "
            f"({summary.get('score_formula', 'weighted severity model')})"
        )
    if summary.get("suppressed_duplicate_count"):
        console.print(
            "[bold]Grouped/Deduplicated Signals:[/bold] "
            f"{summary['suppressed_duplicate_count']} repeated derivative finding(s)"
        )
    if summary.get("raw_critical") is not None:
        console.print(
            "[bold]Raw Critical/High Before Interpretation:[/bold] "
            f"{summary['raw_critical']}/{summary['raw_high']}"
        )
    console.print()

    console.print(f"[bold]Critical Findings:[/bold] {summary['critical']}")
    console.print(f"[bold]High Findings:[/bold] {summary['high']}")
    console.print(f"[bold]Medium Findings:[/bold] {summary['medium']}")
    console.print(f"[bold]Low Findings:[/bold] {summary['low']}\n")
    if summary.get("error"):
        console.print(f"[bold]Error Findings:[/bold] {summary['error']}")
    console.print(f"[bold]Production Decision:[/bold] {summary['production_decision']}")
    console.print(f"[bold]Primary Risk Area:[/bold] {summary['primary_risk_area']}\n")

    if summary.get("readiness_evidence_quality"):
        quality = summary["readiness_evidence_quality"]
        console.print("[bold]Readiness Evidence Quality:[/bold]")
        console.print(f"- Status: {quality.get('status')} ({quality.get('score')}/100)")
        console.print(f"- Reason: {quality.get('reason')}")
        if quality.get("strengths"):
            console.print("- Evidence strengths:")
            for strength in quality["strengths"][:3]:
                console.print(f"  - {strength}")
        if quality.get("context_gaps"):
            console.print("- Context gaps:")
            for gap in quality["context_gaps"][:3]:
                console.print(f"  - {gap}")
        console.print()

    if summary.get("release_evidence"):
        evidence = summary["release_evidence"]
        blockers = evidence.get("production_blockers") or {}
        counts = evidence.get("counts") or {}
        console.print(f"[bold]{blockers.get('question', 'What blocks production?')}[/bold]")
        console.print(f"- Status: {blockers.get('status', 'Unknown')}")
        console.print(f"- Decision: {blockers.get('decision', summary.get('production_decision'))}")
        console.print(f"- Score: {blockers.get('score', summary.get('score'))}/100")
        if blockers.get("blockers"):
            console.print("- Blockers:")
            for risk in blockers["blockers"][:5]:
                affected = risk.get("affected_count", 0)
                suffix = f" ({affected} affected)" if affected else ""
                console.print(f"  - {risk['severity']}: {risk['title']}{suffix}")
        else:
            console.print("- Blockers: none")
        if blockers.get("fix_first"):
            console.print("- Fix first:")
            for action in blockers["fix_first"][:3]:
                console.print(f"  - {action}")
        if blockers.get("business_impact"):
            console.print(f"- Business impact: {blockers['business_impact']}")
        console.print()

        console.print("[bold]Release Evidence Pack:[/bold]")
        console.print(
            "- Domains covered: " + ", ".join(evidence.get("domains_covered") or ["none"])
        )
        console.print(f"- Evidence files scanned: {len(evidence.get('evidence_files') or [])}")
        console.print(
            "- Blocking risks: "
            f"{len(evidence.get('blocking_risks') or [])}; "
            f"major risks: {len(evidence.get('major_risks') or [])}; "
            f"waived findings: {counts.get('waived_findings', 0)}"
        )
        console.print()

    if summary.get("fix_plan"):
        fix_table = Table(title="Fix Plan")
        fix_table.add_column("#")
        fix_table.add_column("Severity")
        fix_table.add_column("Disposition")
        fix_table.add_column("Risk")
        fix_table.add_column("Action")
        fix_table.add_column("Validation")

        for item in summary["fix_plan"][:8]:
            fix_table.add_row(
                str(item.get("rank", "")),
                item.get("severity", ""),
                item.get("disposition", ""),
                item.get("title", ""),
                item.get("action", ""),
                "; ".join(item.get("validation_needed", [])[:2]),
            )

        console.print(fix_table)
        console.print()

    if summary.get("environment_readiness"):
        environment = summary["environment_readiness"]
        console.print("[bold]Environment Readiness:[/bold]")
        console.print(f"- Environment: {environment['name']}")
        if environment.get("profile"):
            console.print(f"- Profile: {environment['profile']}")
        if environment.get("criticality"):
            console.print(f"- Criticality: {environment['criticality']}")
        if environment.get("owner"):
            console.print(f"- Owner: {environment['owner']}")
        console.print(f"- Verdict: {environment['verdict']}")
        console.print(f"- Confidence: {environment['confidence']}")
        if environment.get("business_flows"):
            console.print("- Business flows: " + ", ".join(environment["business_flows"][:3]))
        if environment.get("dependency_domains"):
            console.print("- Dependencies: " + ", ".join(environment["dependency_domains"]))
        if environment.get("blocked_dimensions"):
            console.print("- Blocked/high-risk domains:")
            for dimension in environment["blocked_dimensions"][:4]:
                console.print(
                    f"  - {dimension['title']} ({dimension['status']}, "
                    f"{dimension['max_severity']})"
                )
        if environment.get("coverage_gaps"):
            console.print("- Coverage gaps:")
            for gap in environment["coverage_gaps"][:3]:
                console.print(f"  - {gap}")
        console.print()

    if summary.get("distributed_system_readiness"):
        distributed = summary["distributed_system_readiness"]
        console.print("[bold]Distributed System Readiness:[/bold]")
        console.print(f"- Verdict: {distributed['verdict']}")
        console.print(f"- Confidence: {distributed['confidence']}")
        if distributed.get("domains_observed"):
            console.print("- Domains observed: " + ", ".join(distributed["domains_observed"]))
        if distributed.get("critical_paths"):
            console.print("- Critical paths:")
            for path in distributed["critical_paths"][:3]:
                console.print(f"  - {path}")
        if distributed.get("release_blockers"):
            console.print("- Release blockers:")
            for blocker in distributed["release_blockers"][:3]:
                owner = f", owner={blocker['owner']}" if blocker.get("owner") else ""
                service = f", service={blocker['service']}" if blocker.get("service") else ""
                console.print(
                    f"  - {blocker['severity']}: {blocker['title']} "
                    f"({blocker.get('disposition')}{service}{owner})"
                )
        if distributed.get("accepted_exception_candidates"):
            console.print("- Accepted exception candidates:")
            for candidate in distributed["accepted_exception_candidates"][:3]:
                console.print(f"  - {candidate['title']}")

        dimension_table = Table(title="Distributed Readiness Dimensions")
        dimension_table.add_column("Dimension")
        dimension_table.add_column("Status")
        dimension_table.add_column("Max Severity")
        dimension_table.add_column("Findings")

        for dimension in distributed.get("dimensions", []):
            dimension_table.add_row(
                dimension["title"],
                dimension["status"],
                dimension["max_severity"],
                str(dimension["finding_count"]),
            )

        console.print(dimension_table)
        console.print()

    if summary.get("architect_assessment"):
        assessment = summary["architect_assessment"]
        console.print("[bold]Architect Assessment:[/bold]")
        console.print(f"- Verdict: {assessment['verdict']}")
        console.print(f"- Confidence: {assessment['confidence']}")
        console.print(f"- Context: {assessment['environment_context']}")
        console.print(f"- Score: {assessment['score_explanation']}")

        if assessment.get("material_risks"):
            console.print("- Material risks:")
            for risk in assessment["material_risks"][:3]:
                affected = risk.get("affected_count", 0)
                console.print(f"  - {risk['severity']}: {risk['title']} " f"({affected} affected)")

        if assessment.get("context_gaps"):
            console.print("- Context gaps:")
            for gap in assessment["context_gaps"][:3]:
                console.print(f"  - {gap}")

        if assessment.get("accepted_assumptions"):
            console.print("- Accepted assumptions:")
            for assumption in assessment["accepted_assumptions"][:3]:
                console.print(f"  - {assumption}")

        console.print()

    if summary.get("operational_decisions"):
        console.print("[bold]Operational Decisions[/bold]")
        for decision in summary["operational_decisions"][:5]:
            title = (
                f"#{decision.get('rank', '')} "
                f"{decision.get('decision_label') or decision.get('target') or 'Decision'}"
            )
            console.print(
                Panel(
                    decision_panel_text(decision),
                    title=title,
                    border_style=decision_border_style(decision),
                )
            )
        console.print()

    if summary.get("grouped_risks"):
        grouped_table = Table(title="Grouped Root-Cause Risks")
        grouped_table.add_column("Severity")
        grouped_table.add_column("Category")
        grouped_table.add_column("Risk")
        grouped_table.add_column("Affected")
        grouped_table.add_column("Why It Matters")
        grouped_table.add_column("Evidence")
        grouped_table.add_column("Fix First")
        grouped_table.add_column("Examples")

        for risk in summary["grouped_risks"][:10]:
            quality = risk.get("evidence_quality") or {}
            grouped_table.add_row(
                risk["severity"],
                risk.get("business_category", ""),
                risk["title"],
                str(risk.get("affected_count", 0)),
                risk.get("why_this_matters", ""),
                f"{quality.get('status', 'UNKNOWN')} ({quality.get('score', 0)}/100)",
                risk.get("recommendation", ""),
                ", ".join(risk.get("examples", [])[:3]),
            )

        console.print(grouped_table)

    if summary.get("business_categories"):
        business_table = Table(title="Business Risk Categories")
        business_table.add_column("Category")
        business_table.add_column("Risk")
        business_table.add_column("Risk Points")
        business_table.add_column("Grouped Findings")

        for category, data in summary["business_categories"].items():
            business_table.add_row(
                category,
                data["risk"],
                str(data["risk_points"]),
                str(data["findings"]),
            )

        console.print(business_table)

    table = Table(title="Production Readiness Categories")
    table.add_column("Category")
    table.add_column("Risk")
    table.add_column("Finding Count")

    for category, data in summary["categories"].items():
        table.add_row(category.replace("_", " ").title(), data["risk"], str(data["findings"]))

    console.print("[bold]Top Reasons:[/bold]")
    for reason in summary["top_reasons"]:
        console.print(f"- {reason}")

    console.print("\n[bold]Next Best Actions:[/bold]")
    for action in summary["next_best_actions"]:
        console.print(f"- {action}")

    if summary.get("root_cause_hypotheses"):
        console.print("\n[bold]Root Cause Hypotheses:[/bold]")
        for hypothesis in summary["root_cause_hypotheses"][:3]:
            console.print(
                f"- {hypothesis['confidence']}: {hypothesis['title']} "
                f"(score {hypothesis['score']})"
            )

    if summary.get("kafka_report"):
        console.print("\n[bold]Kafka Readiness Sections:[/bold]")
        for section in summary["kafka_report"]["sections"]:
            counts = section["severity_counts"]
            console.print(
                f"- {section['title']}: {section['finding_count']} finding(s) "
                f"(Critical {counts.get('CRITICAL', 0)}, High {counts.get('HIGH', 0)}, "
                f"Medium {counts.get('MEDIUM', 0)})"
            )

    console.print()

    console.print(table)


def decision_panel_text(decision):
    lines = [
        f"[bold]Action:[/bold] {decision.get('action', '')}",
        (
            "[bold]Target:[/bold] "
            f"{decision.get('target', '')} | "
            f"[bold]Disposition:[/bold] {decision.get('disposition', '')} | "
            f"[bold]Safety:[/bold] {decision.get('safety', '')} | "
            f"[bold]Confidence:[/bold] {decision.get('confidence', '')}"
        ),
    ]

    if decision.get("why"):
        lines.append(f"[bold]Why:[/bold] {decision['why']}")

    if decision.get("evidence_required"):
        lines.append(
            "[bold]Evidence required:[/bold] "
            + "; ".join(decision.get("evidence_required", [])[:3])
        )

    if decision.get("do_not_do"):
        lines.append("[bold]Do not do:[/bold] " + "; ".join(decision.get("do_not_do", [])[:2]))

    if decision.get("source_rule_ids"):
        lines.append("[bold]Source rules:[/bold] " + ", ".join(decision["source_rule_ids"][:3]))

    return "\n".join(lines)


def decision_border_style(decision):
    if decision.get("safety") == "CAUTION":
        return "yellow"
    if decision.get("decision_type") == "release_blocker":
        return "red"
    if decision.get("decision_type") == "monitor":
        return "green"
    return "cyan"
