from beacon.engine.models import Resource


def normalize_kafka_config(data, source):
    resources = []
    kafka_data = data.get("kafka", data)

    for topic in kafka_data.get("topics", []):
        resources.append(
            Resource(
                type="kafka_topic",
                name=topic.get("name", "unknown-topic"),
                domain="kafka",
                source=source,
                attributes={
                    "replication_factor": topic.get("replication_factor"),
                    "partitions": topic.get("partitions"),
                    "retention_ms": topic.get("retention_ms"),
                    "retention_bytes": topic.get("retention_bytes"),
                    "cleanup_policy": topic.get("cleanup_policy"),
                    "min_insync_replicas": topic.get("min_insync_replicas"),
                    "segment_bytes": topic.get("segment_bytes"),
                    "max_message_bytes": topic.get("max_message_bytes"),
                },
            )
        )

    for broker in kafka_data.get("brokers", []):
        resources.append(
            Resource(
                type="kafka_broker_config",
                name=str(broker.get("id", broker.get("name", "unknown-broker"))),
                domain="kafka",
                source=source,
                attributes={
                    "default_replication_factor": broker.get(
                        "default_replication_factor"
                    ),
                    "offsets_topic_replication_factor": broker.get(
                        "offsets_topic_replication_factor"
                    ),
                    "transaction_state_log_replication_factor": broker.get(
                        "transaction_state_log_replication_factor"
                    ),
                    "log_retention_bytes": broker.get("log_retention_bytes"),
                    "auto_create_topics_enable": broker.get(
                        "auto_create_topics_enable"
                    ),
                },
            )
        )

    return resources


def normalize_terraform_config(data, source):
    resources = []
    terraform_resources = data.get("resource", [])

    for block in terraform_resources:
        for resource_type, instances in block.items():
            resource_type = normalize_hcl_identifier(resource_type)

            for name, config in instances.items():
                name = normalize_hcl_identifier(name)

                if is_object_storage_resource(resource_type):
                    resources.append(
                        Resource(
                            type="object_storage_bucket",
                            name=name,
                            domain="object_storage",
                            source=source,
                            attributes={
                                "provider_resource_type": resource_type,
                                "config": config,
                            },
                        )
                    )

                if is_iam_resource(resource_type):
                    resources.append(
                        Resource(
                            type="iam_policy",
                            name=name,
                            domain="cloud_identity",
                            source=source,
                            attributes={
                                "provider_resource_type": resource_type,
                                "config": config,
                                "raw_config": str(config),
                            },
                        )
                    )

                if is_cloud_resource(resource_type):
                    resources.append(
                        Resource(
                            type="cloud_resource",
                            name=name,
                            domain="cloud",
                            source=source,
                            attributes={
                                "provider_resource_type": resource_type,
                                "config": config,
                            },
                        )
                    )

    return resources


def normalize_terraform_json(data, source):
    resources = []

    for item in iter_terraform_json_resources(data):
        resource_type = item.get("type")
        name = item.get("name", "unknown-resource")
        values = item.get("values", {})

        if is_object_storage_resource(resource_type):
            resources.append(
                Resource(
                    type="object_storage_bucket",
                    name=name,
                    domain="object_storage",
                    source=source,
                    attributes={
                        "provider_resource_type": resource_type,
                        "config": values,
                    },
                )
            )

        if is_iam_resource(resource_type):
            resources.append(
                Resource(
                    type="iam_policy",
                    name=name,
                    domain="cloud_identity",
                    source=source,
                    attributes={
                        "provider_resource_type": resource_type,
                        "config": values,
                        "raw_config": str(values),
                    },
                )
            )

        if is_cloud_resource(resource_type):
            resources.append(
                Resource(
                    type="cloud_resource",
                    name=name,
                    domain="cloud",
                    source=source,
                    attributes={
                        "provider_resource_type": resource_type,
                        "config": values,
                    },
                )
            )

    return resources


def iter_terraform_json_resources(data):
    if not isinstance(data, dict):
        return

    for change in data.get("resource_changes", []):
        after = change.get("change", {}).get("after")

        if after is None:
            continue

        yield {
            "type": change.get("type"),
            "name": change.get("name"),
            "values": after,
        }

    planned_values = data.get("planned_values", {})
    yield from iter_terraform_value_resources(planned_values)

    values = data.get("values", {})
    yield from iter_terraform_value_resources(values)


def iter_terraform_value_resources(values):
    root_module = values.get("root_module") if isinstance(values, dict) else None

    if not isinstance(root_module, dict):
        return

    yield from iter_terraform_module_resources(root_module)


def iter_terraform_module_resources(module):
    for resource in module.get("resources", []):
        yield {
            "type": resource.get("type"),
            "name": resource.get("name"),
            "values": resource.get("values", {}),
        }

    for child in module.get("child_modules", []):
        yield from iter_terraform_module_resources(child)


def normalize_hcl_identifier(value):
    if not isinstance(value, str):
        return value

    return value.strip('"')


def is_object_storage_resource(resource_type):
    return resource_type in {
        "aws_s3_bucket",
        "aws_s3_bucket_public_access_block",
        "google_storage_bucket",
        "azurerm_storage_account",
    }


def is_iam_resource(resource_type):
    return resource_type in {
        "aws_iam_policy",
        "google_project_iam_binding",
        "azurerm_role_assignment",
    }


def is_cloud_resource(resource_type):
    return resource_type in {
        "aws_security_group",
        "aws_db_instance",
        "aws_instance",
    }


def normalize_kubernetes_config(data, source):
    if not isinstance(data, dict):
        return []

    kind = data.get("kind")
    metadata = data.get("metadata", {})
    name = metadata.get("name", "unknown-workload")

    if kind not in {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet"}:
        return []

    spec = data.get("spec", {})
    template = spec.get("template", {})
    pod_spec = template.get("spec", {})
    containers = pod_spec.get("containers", [])
    replicas = spec.get("replicas")

    resources = []

    for container in containers:
        security_context = container.get("securityContext", {})

        resources.append(
            Resource(
                type="k8s_workload_container",
                name=name,
                domain="kubernetes",
                source=source,
                attributes={
                    "kind": kind,
                    "replicas": replicas,
                    "container": container.get("name", "unknown-container"),
                    "image": container.get("image", ""),
                    "resources": container.get("resources", {}),
                    "has_readiness_probe": "readinessProbe" in container,
                    "has_liveness_probe": "livenessProbe" in container,
                    "privileged": security_context.get("privileged"),
                },
            )
        )

    return resources


def normalize_yaml_document(data, source):
    if not isinstance(data, dict):
        return []

    if "topics" in data or "kafka" in data:
        return normalize_kafka_config(data, source)

    if "kind" in data and "apiVersion" in data:
        return normalize_kubernetes_config(data, source)

    if "jobs" in data:
        return normalize_cicd_workflow(data, source)

    runtime_resources = normalize_runtime_sections(data, source)

    if runtime_resources:
        return runtime_resources

    if "cloud_inventory" in data:
        return normalize_cloud_inventory(data.get("cloud_inventory", {}), source)

    if "topology" in data:
        return normalize_topology(data.get("topology", {}), source)

    return []


def normalize_runtime_sections(data, source):
    resources = []

    if "kubernetes_runtime" in data:
        resources.extend(
            normalize_kubernetes_runtime(data.get("kubernetes_runtime", {}), source)
        )

    if "flow_runtime" in data:
        resources.extend(normalize_flow_runtime(data.get("flow_runtime", {}), source))

    if "api_runtime" in data:
        resources.extend(normalize_api_runtime(data.get("api_runtime", {}), source))

    if "database_runtime" in data:
        resources.extend(
            normalize_database_runtime(data.get("database_runtime", {}), source)
        )

    if "storage_runtime" in data:
        resources.extend(
            normalize_storage_runtime(data.get("storage_runtime", {}), source)
        )

    return resources


def normalize_api_runtime(data, source):
    if not isinstance(data, dict):
        return []

    services = data.get("services", [])

    if not services and data.get("name"):
        services = [data]

    resources = []

    for service in services:
        resources.append(
            Resource(
                type="api_runtime_service",
                name=service.get("name", "unknown-api"),
                domain="api",
                source=source,
                attributes={
                    "latency_p95_ms": service.get("latency_p95_ms"),
                    "error_rate_percent": service.get("error_rate_percent"),
                    "timeout_rate_percent": service.get("timeout_rate_percent"),
                    "retry_rate_percent": service.get("retry_rate_percent"),
                    "saturation_percent": service.get("saturation_percent"),
                    "recent_deployment": service.get("recent_deployment", False),
                },
            )
        )

    return resources


def normalize_database_runtime(data, source):
    if not isinstance(data, dict):
        return []

    databases = data.get("databases", [])

    if not databases and data.get("name"):
        databases = [data]

    resources = []

    for database in databases:
        resources.append(
            Resource(
                type="database_runtime_instance",
                name=database.get("name", "unknown-database"),
                domain="database",
                source=source,
                attributes={
                    "engine": database.get("engine"),
                    "latency_ms": database.get("latency_ms"),
                    "connection_pool_utilization_percent": database.get(
                        "connection_pool_utilization_percent"
                    ),
                    "lock_waits_high": database.get("lock_waits_high", False),
                    "replication_lag_seconds": database.get(
                        "replication_lag_seconds"
                    ),
                    "storage_used_percent": database.get("storage_used_percent"),
                },
            )
        )

    return resources


def normalize_storage_runtime(data, source):
    if not isinstance(data, dict):
        return []

    resources = []

    for item in data.get("resources", []):
        resources.append(
            Resource(
                type="storage_runtime_resource",
                name=item.get("name", "unknown-storage"),
                domain="storage",
                source=source,
                attributes={
                    "resource_type": item.get("type"),
                    "used_percent": item.get("used_percent"),
                    "growth_percent_7d": item.get("growth_percent_7d"),
                    "iops_saturation_percent": item.get("iops_saturation_percent"),
                    "backup_age_hours": item.get("backup_age_hours"),
                },
            )
        )

    return resources


def normalize_flow_runtime(data, source):
    if not isinstance(data, dict):
        return []

    flow_name = data.get("name", "unknown-flow")
    signals = data.get("signals", {})

    resources = [
        Resource(
            type="flow_runtime",
            name=flow_name,
            domain="flow",
            source=source,
            attributes={
                "name": flow_name,
                "signals": signals,
                "components": data.get("components", {}),
            },
        )
    ]

    for component_name, component in data.get("components", {}).items():
        if not isinstance(component, dict):
            continue

        resources.append(
            Resource(
                type="flow_component_runtime",
                name=component_name,
                domain="flow",
                source=source,
                attributes={
                    "flow": flow_name,
                    "component_type": component.get("type"),
                    "signals": component.get("signals", {}),
                    "depends_on": component.get("depends_on", []) or [],
                },
            )
        )

    return resources


def normalize_cloud_inventory(data, source):
    if not isinstance(data, dict):
        return []

    resources = []

    for item in data.get("resources", []):
        resource_type = item.get("type")
        name = item.get("name", "unknown-resource")
        config = item.get("config", item)

        if is_object_storage_resource(resource_type):
            resources.append(
                Resource(
                    type="object_storage_bucket",
                    name=name,
                    domain="object_storage",
                    source=source,
                    attributes={
                        "provider_resource_type": resource_type,
                        "config": config,
                    },
                )
            )

        if is_iam_resource(resource_type):
            resources.append(
                Resource(
                    type="iam_policy",
                    name=name,
                    domain="cloud_identity",
                    source=source,
                    attributes={
                        "provider_resource_type": resource_type,
                        "config": config,
                        "raw_config": str(config),
                    },
                )
            )

        if is_cloud_resource(resource_type):
            resources.append(
                Resource(
                    type="cloud_resource",
                    name=name,
                    domain="cloud",
                    source=source,
                    attributes={
                        "provider_resource_type": resource_type,
                        "config": config,
                    },
                )
            )

    return resources


def normalize_topology(data, source):
    if not isinstance(data, dict):
        return []

    services = data.get("services", [])
    service_names = {service.get("name") for service in services}
    dependents_by_service = {name: [] for name in service_names if name}

    for service in services:
        service_name = service.get("name")

        for dependency in service.get("depends_on", []) or []:
            if dependency in dependents_by_service:
                dependents_by_service[dependency].append(service_name)

    resources = []

    for service in services:
        name = service.get("name", "unknown-service")
        resources.append(
            Resource(
                type="topology_service",
                name=name,
                domain="topology",
                source=source,
                attributes={
                    "owner": service.get("owner"),
                    "criticality": service.get("criticality"),
                    "instances": service.get("instances"),
                    "depends_on": service.get("depends_on", []) or [],
                    "dependents": dependents_by_service.get(name, []),
                },
            )
        )

    return resources


def normalize_kubernetes_runtime(data, source):
    if not isinstance(data, dict):
        return []

    resources = []

    for node in data.get("nodes", []):
        pressure = []

        for key in ("memory_pressure", "disk_pressure", "pid_pressure"):
            if node.get(key) is True:
                pressure.append(key)

        resources.append(
            Resource(
                type="k8s_runtime_node",
                name=node.get("name", "unknown-node"),
                domain="kubernetes",
                source=source,
                attributes={
                    "ready": node.get("ready"),
                    "pressure": pressure,
                },
            )
        )

    for pod in data.get("pods", []):
        resources.append(
            Resource(
                type="k8s_runtime_pod",
                name=pod.get("name", "unknown-pod"),
                domain="kubernetes",
                source=source,
                attributes={
                    "namespace": pod.get("namespace"),
                    "phase": pod.get("phase"),
                    "restart_count": pod.get("restart_count", 0),
                    "waiting_reason": pod.get("waiting_reason"),
                },
            )
        )

    for deployment in data.get("deployments", []):
        resources.append(
            Resource(
                type="k8s_runtime_deployment",
                name=deployment.get("name", "unknown-deployment"),
                domain="kubernetes",
                source=source,
                attributes={
                    "namespace": deployment.get("namespace"),
                    "desired_replicas": deployment.get("desired_replicas"),
                    "available_replicas": deployment.get("available_replicas"),
                },
            )
        )

    return resources


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
