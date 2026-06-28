---
name: IaC coverage readiness
about: Discuss how Beacon should detect unmanaged cloud resources outside Terraform state
title: "What should Beacon do when cloud resources exist outside Terraform state?"
labels: iac-coverage, product-feedback
---

## Question

What does the IaC coverage pack need to do for real infrastructure estates,
especially when teams have many Terraform state files, accounts, projects, or
workspaces?

## Current implementation areas

- `beacon/iac_coverage.py`
- `packs/iac-coverage-readiness/`

These files contain the current resource diffing, ownership detection, and
disposition logic.

## What Beacon is trying to answer

```text
What important cloud resources exist outside Terraform state, who owns them,
what risk do they create, and what should we do next?
```

## What feedback would help?

- Do you compare live cloud inventory against one state file, many state files,
  Terraform Cloud workspaces, or exported inventory indexes?
- Which unmanaged resources should be high risk?
- Which resources should be ignored as managed-service internals?
- What ownership metadata should Beacon require?
- Should Beacon recommend import, delete, tag, quarantine, or manual review?
- What large-organization workflow would make this useful?

## Safe evidence

Paste redacted inventory/state examples or describe your workflow. Please remove
account IDs, secrets, tokens, private hostnames, and production data.
