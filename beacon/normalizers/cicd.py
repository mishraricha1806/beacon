from beacon.engine.models import Resource


def normalize_cicd_workflow(data, source):
    if not isinstance(data, dict):
        return []

    jobs = data.get("jobs", {})

    if not isinstance(jobs, dict):
        return []

    workflow = data.get("name", "unknown-workflow")
    triggers = normalize_workflow_triggers(data)
    workflow_permissions = data.get("permissions")
    resources = []

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue

        job_permissions = job.get("permissions", workflow_permissions)
        environment = job.get("environment")
        steps = job.get("steps", [])

        resources.append(
            Resource(
                type="cicd_workflow_job",
                name=job_name,
                domain="cicd",
                source=source,
                attributes={
                    "workflow": workflow,
                    "triggers": triggers,
                    "permissions": job_permissions,
                    "environment": environment,
                    "deploy_like": is_deploy_like_job(job_name, job, steps),
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
