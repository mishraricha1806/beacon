# Beacon CI/CD Integration

Use Beacon as a read-only production-readiness gate before release.

The recommended CI path is Docker because teams can run Beacon without Python,
source code, or local installation.

## CI-native result formats

Static readiness scans can emit SARIF 2.1.0 and JUnit XML alongside Beacon's versioned JSON evidence:

```bash
beacon readiness static . \
  --environment prod \
  --no-html \
  --no-open-report \
  --output json \
  --ci \
  --fail-on high \
  --evidence-output beacon-reports/beacon-release-evidence.json \
  --sarif-output beacon-reports/beacon-results.sarif \
  --junit-output beacon-reports/beacon-results.xml
```

SARIF results contain stable `beaconFindingFingerprint/v1` identifiers so code-scanning systems can correlate the same finding between runs. Policy waivers are represented as accepted external suppressions. JUnit failures follow `--fail-on`; Beacon analysis errors remain JUnit errors and use process exit code `2`.

## Changed-risk comparison

Compare an accepted baseline with the current release evidence:

```bash
beacon compare \
  .beacon/baseline-release-evidence.json \
  beacon-reports/beacon-release-evidence.json \
  --output json \
  --markdown-output beacon-reports/beacon-comparison.md
```

New evidence uses stable risk fingerprints, so wording improvements do not appear as resolved and recreated risks. Unversioned legacy evidence remains comparable using the original title/category identity.

The reusable action accepts the optional input `baseline-evidence`. It writes JSON and Markdown comparisons before enforcing the saved readiness exit code, ensuring reports are available for review even when the gate fails. Baseline changes require human review and must not be used to silently accept new risk.

## Exit Codes

```text
0 = configured gate passed
1 = readiness risk crossed the configured severity threshold
2 = analysis was blocked by collector, parsing, or input errors
```

Typical release gate:

```bash
beacon readiness --ci --fail-on high --output json --no-html --no-open-report
```

Use `--fail-on critical` for a softer rollout, then move to `--fail-on high`
when teams are ready.

## Docker Command

Run against project-local `beacon.yaml`:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness \
  --config /workspace/project/beacon.yaml \
  --ci \
  --fail-on high \
  --output json \
  --evidence-output /workspace/project/beacon-evidence.json \
  --no-html \
  --no-open-report
```

Run against a static infra folder:

```bash
docker run --rm \
  -v "$PWD:/workspace/project:ro" \
  ghcr.io/mishraricha1806/beacon:latest readiness static \
  /workspace/project/infra \
  --environment prod \
  --ci \
  --fail-on high \
  --output json \
  --evidence-output /workspace/project/beacon-evidence.json \
  --no-html \
  --no-open-report
```

In JSON output, the CI/change-ticket evidence is here:

```text
readiness_summary.release_evidence
```

Or write only the evidence pack to a standalone file:

```bash
beacon readiness --evidence-output beacon-evidence.json
```

Compare two release evidence files to see whether a change improved or
regressed readiness:

```bash
beacon compare beacon-evidence-before.json beacon-evidence-after.json
beacon compare beacon-evidence-before.json beacon-evidence-after.json --output json
```

## GitHub Actions

```yaml
name: Beacon readiness

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  readiness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Beacon readiness gate
        run: |
          docker run --rm \
            -v "$PWD:/workspace/project:ro" \
            ghcr.io/mishraricha1806/beacon:latest readiness \
            --config /workspace/project/beacon.yaml \
            --ci \
            --fail-on high \
            --output json \
            --evidence-output /workspace/project/beacon-evidence.json \
            --no-html \
            --no-open-report | tee beacon-readiness.json

      - name: Upload Beacon evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: beacon-readiness
          path: |
            beacon-readiness.json
            beacon-evidence.json
```

For pull requests, keep a previous evidence artifact from your baseline branch
and compare it with the current run:

```bash
beacon compare beacon-evidence-main.json beacon-evidence.json --output json
```

## GitLab CI

```yaml
beacon_readiness:
  stage: test
  image: docker:27
  services:
    - docker:27-dind
  script:
    - |
      docker run --rm \
        -v "$CI_PROJECT_DIR:/workspace/project:ro" \
        ghcr.io/mishraricha1806/beacon:latest readiness \
        --config /workspace/project/beacon.yaml \
        --ci \
        --fail-on high \
        --output json \
        --evidence-output /workspace/project/beacon-evidence.json \
        --no-html \
        --no-open-report | tee beacon-readiness.json
  artifacts:
    when: always
    paths:
      - beacon-readiness.json
      - beacon-evidence.json
```

If your GitLab runner already runs job containers with Docker unavailable, use
the Beacon image directly:

```yaml
beacon_readiness:
  stage: test
  image: ghcr.io/mishraricha1806/beacon:latest
  script:
    - beacon readiness --config beacon.yaml --ci --fail-on high --output json --evidence-output beacon-evidence.json --no-html --no-open-report | tee beacon-readiness.json
  artifacts:
    when: always
    paths:
      - beacon-readiness.json
      - beacon-evidence.json
```

## Jenkins Pipeline

```groovy
pipeline {
  agent any

  stages {
    stage('Beacon readiness') {
      steps {
        sh '''
          docker run --rm \
            -v "$PWD:/workspace/project:ro" \
            ghcr.io/mishraricha1806/beacon:latest readiness \
            --config /workspace/project/beacon.yaml \
            --ci \
            --fail-on high \
            --output json \
            --evidence-output /workspace/project/beacon-evidence.json \
            --no-html \
            --no-open-report | tee beacon-readiness.json
        '''
      }
      post {
        always {
          archiveArtifacts artifacts: 'beacon-readiness.json, beacon-evidence.json', allowEmptyArchive: true
        }
      }
    }
  }
}
```

## Staged Rollout

Start with a non-blocking evidence run:

```bash
beacon readiness --output json --no-html --no-open-report
```

Then soft gate only critical blockers:

```bash
beacon readiness --ci --fail-on critical --output json --no-html --no-open-report
```

Then enforce high and critical risks:

```bash
beacon readiness --ci --fail-on high --output json --no-html --no-open-report
```

## Recommended `beacon.yaml`

```yaml
project: checkout-service
environment:
  name: prod-us-east
  profile: prod
  criticality: high
  owner: platform-team

readiness:
  include:
    - ./infra
    - ./k8s
    - ./kafka

policy:
  waivers:
    - rule_id: kafka.topic.partitions.low
      resource: orders.retry
      reason: Ordered retry topic; one partition is intentional.
      expires: 2026-12-31

ci:
  enabled: true
  fail_on: high

report:
  format:
    - json
  evidence_output: ./beacon-evidence.json
  open: false
```
