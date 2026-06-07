# Beacon Demo Video Script

Target length: 4 to 6 minutes.

Audience: platform engineers, SREs, backend engineers, Kafka owners, engineering
managers evaluating production-readiness tooling.

## Core Message

Beacon helps teams answer:

```text
Is this distributed system production-ready, and if not, what should we fix first?
```

Beacon is not a dashboard, log store, or generic AI chatbot. Beacon is a
deterministic operational reasoning layer for production readiness and runtime
diagnostics.

## Recording Setup

Open two terminal tabs:

```bash
cd /Users/richamishra/IdeaProjects/beacon
```

Set the terminal font large enough for video, around 16 to 18 pt.

Optional cleanup before recording:

```bash
clear
rm -rf reports/project-demo
```

## Scene 1: Product Intro

Approx time: 30 seconds.

Say:

```text
Beacon is a production-readiness and operational intelligence tool for
distributed systems. It helps engineering teams check infrastructure before
production and diagnose runtime degradation during incidents.

The goal is simple: run Beacon before production, and ask Beacon why the system
is degrading.
```

Show:

```bash
beacon --help
```

Point out:

- `init`
- `doctor`
- `readiness`
- `diagnose`
- `run`

## Scene 2: Project-Local Setup

Approx time: 45 seconds.

Say:

```text
Beacon is project-local and config-driven. A team can add beacon.yaml to a repo
and then run short commands instead of long CLI flags.
```

Show:

```bash
cat beacon.yaml
```

Then:

```bash
beacon doctor
```

Point out:

- Beacon found `beacon.yaml`
- report directory is writable
- optional tools like Helm/kubectl are checked
- named workflows are detected

## Scene 3: Production Readiness

Approx time: 75 seconds.

Say:

```text
Now Beacon checks whether this project is production-ready. It scans configured
infrastructure inputs, applies environment context, groups repeated risks, and
produces a readiness decision.
```

Show:

```bash
beacon readiness
```

Point out:

- production readiness score
- decision: ready or not ready
- top risks
- grouped root-cause risks
- next best actions
- environment-aware interpretation

Suggested explanation:

```text
Beacon does not just count every repeated topic issue as a separate root cause.
It groups derivative findings so engineers see the real operational risks first.
```

## Scene 4: JSON For Automation

Approx time: 30 seconds.

Say:

```text
The same readiness result can be emitted as JSON for CI/CD, release gates, or
internal developer platforms.
```

Show:

```bash
beacon readiness --output json | head -40
```

## Scene 5: Kafka Runtime Incident Diagnosis

Approx time: 75 seconds.

Say:

```text
Beacon also supports runtime diagnostics. Kafka is the first deep domain because
Kafka incidents are operationally painful and hard to explain from dashboards
alone.
```

Show:

```bash
beacon run kafka-incident-demo
```

Point out:

- incident diagnosis
- evidence quality
- likely cause
- first actions
- runbook
- evidence still missing

Suggested explanation:

```text
Beacon is careful about evidence. If Kafka lag exists but database telemetry is
missing, Beacon will not blindly claim a database bottleneck. It reports what it
knows and what evidence is still needed.
```

## Scene 6: Flow Intelligence

Approx time: 60 seconds.

Say:

```text
Flow intelligence is where Beacon starts correlating across systems: API,
Kafka, consumers, database, storage, and deployments.
```

Show:

```bash
beacon run flow-demo
```

Point out:

- cross-system bottleneck ranking
- downstream database bottleneck hypothesis
- cascading latency explanation
- deployment correlation

## Scene 7: Full Demo Command

Approx time: 45 seconds.

Say:

```text
For a full product demo, Beacon ships a local demo script. It runs production
readiness, environment-aware readiness, Kafka incident diagnosis, flow
intelligence, and release confidence checks.
```

Show:

```bash
scripts/demo_project.sh
```

If the output is too long for the video, stop after the first few sections and
say:

```text
The full script also writes JSON artifacts under reports/project-demo.
```

Show:

```bash
ls reports/project-demo
```

## Scene 8: Close

Approx time: 30 seconds.

Say:

```text
Beacon's moat is deterministic operational reasoning. AI can explain the result
later, but the findings, scores, and recommendations are rule-backed and
evidence-backed first.

The product promise is: run Beacon before production, and ask Beacon why the
system is degrading.
```

## Short Version Commands

Use this sequence for a clean 4-minute video:

```bash
beacon --help
cat beacon.yaml
beacon doctor
beacon readiness
beacon run kafka-incident-demo
beacon run flow-demo
```

## Longer Version Commands

Use this for a deeper technical video:

```bash
beacon --help
cat beacon.yaml
beacon doctor
beacon readiness
beacon readiness --output json | head -40
beacon run kafka-incident-demo
beacon run flow-demo
scripts/demo_project.sh
ls reports/project-demo
```

## Video Title Ideas

- Beacon: Production Readiness For Distributed Systems
- Run Beacon Before Production
- Diagnosing Kafka And Distributed System Risk With Beacon
- Beacon Demo: Readiness, Runtime Diagnostics, And Flow Intelligence

## Thumbnail Text

```text
Is this production ready?
Ask Beacon.
```

## Description For Sharing

```text
Beacon is a production-readiness and operational intelligence tool for
distributed systems. It scans infrastructure and runtime signals across Kafka,
Kubernetes, Terraform, storage, IAM, CI/CD, and service flows to produce
readiness decisions, grouped risks, root-cause hypotheses, and next operational
actions.
```
