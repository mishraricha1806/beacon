# Beacon Pilot Scorecard Template (Weekly)

Date: __________
Week #: __________
Team / Business Unit: __________
Owner: __________
Environment(s): dev / test / staging / prod

## 1) Weekly Summary

- pilot status: green / yellow / red
- top improvement this week:
- top risk this week:
- leadership ask:

## 2) Scope and Adoption

- target pipelines in pilot: __________
- pipelines onboarded: __________
- pipelines with active readiness gate: __________
- environment profiles active: dev / test / staging / prod
- domain coverage active this week:
  - static config: yes / no
  - kubernetes manifest readiness: yes / no
  - kafka config readiness: yes / no
  - api gateway readiness: yes / no
  - database readiness: yes / no
  - cloud quota readiness: yes / no
  - security/compliance config readiness: yes / no

## 3) Gate Performance Metrics

- total readiness runs: __________
- pass rate (%): __________
- blocked runs: __________
- soft-block runs: __________
- warning-only runs: __________
- first-attempt pass rate (%): __________

## 4) Blocker Quality Metrics

- total blockers raised: __________
- unique blocker categories: __________
- high-confidence blockers: __________
- false positives (count): __________
- false positive rate (%): __________
- blocker precision assessment (1-5): __________

## 5) Remediation and Exception Metrics

- blockers remediated this week: __________
- median remediation lead time (days): __________
- open blockers older than SLA: __________
- new policy exceptions requested: __________
- exceptions with owner assigned (%): __________
- exceptions with expiry defined (%): __________
- expired exceptions still open (count): __________

## 6) Release Risk Outcomes

- failed releases this week (pilot scope): __________
- rolled-back releases this week: __________
- config-caused incidents this week: __________
- sev1/sev2 incidents linked to readiness gaps: __________
- estimated incidents prevented (qualitative): low / medium / high

## 7) Top Blocker Categories (Top 5)

| Rank | Rule ID | Category | Count | Environment | Owner | ETA |
|---|---|---|---:|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |

## 8) Policy and Governance Health

- policy profile changes this week: yes / no
- policy drift detected: yes / no
- approvals completed for policy changes: yes / no
- compliance controls validated this week: yes / no
- audit-ready evidence bundle generated: yes / no

## 9) Team Feedback (Qualitative)

- what worked well:
- what slowed teams down:
- confusing findings/rules:
- recommended rule tuning:
- onboarding/documentation gaps:

## 10) Weekly Decision and Next Actions

- weekly readiness confidence: low / medium / high
- recommendation for next week:
  - continue as-is
  - tighten gate
  - tune rules
  - add domain coverage
  - pause and remediate

### Action List

| Action | Owner | Due Date | Status |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

---

## Optional Appendix A - KPI Trend (Week over Week)

| Metric | Week N-2 | Week N-1 | Week N | Trend |
|---|---:|---:|---:|---|
| Pass rate (%) |  |  |  |  |
| First-attempt pass rate (%) |  |  |  |  |
| Blocked runs |  |  |  |  |
| False positive rate (%) |  |  |  |  |
| Median remediation lead time |  |  |  |  |
| Failed releases |  |  |  |  |
| Rolled-back releases |  |  |  |  |

## Optional Appendix B - Pilot Exit Readiness Checklist

- [ ] deterministic gate is active on at least one production path
- [ ] false positive rate is within agreed threshold
- [ ] remediation SLA adherence is acceptable
- [ ] exception workflow (owner + expiry) is operational
- [ ] leadership sign-off obtained for next phase rollout

