from beacon.engine.models import Resource


def normalize_cicd_workflow(data, source):
    if not isinstance(data, dict):
        return []

    jobs = data.get("jobs", {})

    if not isinstance(jobs, dict):
        return []

    workflow = data.get("name", "unknown-workflow")
    triggers = normalize_workflow_triggers(data)
    trigger_config = data.get("on", data.get(True, {}))
    workflow_permissions = data.get("permissions")
    workflow_concurrency = data.get("concurrency")
    resources = []

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue

        job_permissions = job.get("permissions", workflow_permissions)
        environment = job.get("environment")
        steps = job.get("steps", [])
        step_uses = [step.get("uses") for step in steps if isinstance(step, dict)]

        resources.append(
            Resource(
                type="cicd_workflow_job",
                name=job_name,
                domain="cicd",
                source=source,
                attributes={
                    "workflow": workflow,
                    "triggers": triggers,
                    "trigger_config": trigger_config,
                    "permissions": job_permissions,
                    "permissions_specified": job_permissions is not None,
                    "environment": environment,
                    "deploy_like": is_deploy_like_job(job_name, job, steps),
                    "timeout_minutes": job.get("timeout-minutes"),
                    "concurrency": job.get("concurrency", workflow_concurrency),
                    "step_uses": [value for value in step_uses if value],
                },
            )
        )

    return resources


def normalize_workflow_triggers(data):
    raw_triggers = data.get("on", data.get(True, []))

    if isinstance(raw_triggers, str):
        return [raw_triggers]

    if isinstance(raw_triggers, list):
        return raw_triggers

    if isinstance(raw_triggers, dict):
        return list(raw_triggers.keys())

    return []


def is_deploy_like_job(job_name, job, steps):
    text = " ".join(
        [
            job_name,
            str(job.get("name", "")),
            str(job.get("environment", "")),
            str(job.get("uses", "")),
            str(steps),
        ]
    ).lower()

    return any(word in text for word in ["deploy", "release", "production", "prod"])
