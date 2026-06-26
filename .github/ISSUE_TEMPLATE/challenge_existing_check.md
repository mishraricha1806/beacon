---
name: Challenge an existing check
about: Tell us where a Beacon rule is too noisy, too strict, unclear, or wrong
title: "[Challenge check]: "
labels: rule-feedback
assignees: ""
---

## Which Beacon check are you challenging?

Paste the rule ID or finding title if you have it.

Example:

```text
kafka.topic.partitions.low
```

## What seems wrong?

- [ ] False positive
- [ ] Severity is too high
- [ ] Severity is too low
- [ ] Recommendation is wrong or incomplete
- [ ] Should depend on dev/test/prod environment
- [ ] Should be grouped with another root cause
- [ ] Other:

## What was the real-world context?

Example:

```text
This is a single-partition ordered workflow topic, so low partition count is intentional.
```

## What should Beacon do instead?

Describe the better behavior, downgrade, grouping, exception, or recommendation.

## Safe evidence

Paste a redacted finding, config snippet, or screenshot if useful. Please remove secrets, tokens, private hostnames, and production data.

