def finding(severity, title, impact, recommendation, file):
    return {
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file
    }


def evaluate_kafka_config(data, file):
    findings = []
    topics = data.get("topics", [])

    for topic in topics:
        name = topic.get("name", "unknown-topic")
        rf = topic.get("replication_factor")
        partitions = topic.get("partitions")
        retention_ms = topic.get("retention_ms")

        if rf is not None and rf < 3:
            findings.append(finding(
                "CRITICAL",
                f"Kafka topic '{name}' has replication factor {rf}",
                "A broker failure can make this topic unavailable and interrupt production workflows.",
                "Use replication_factor=3 for production topics.",
                file
            ))

        if partitions is not None and partitions < 3:
            findings.append(finding(
                "HIGH",
                f"Kafka topic '{name}' has low partition count",
                "Low partitions can limit consumer parallelism and reduce throughput.",
                "Use at least 3 partitions for production workloads, then tune based on throughput.",
                file
            ))

        if retention_ms is not None and retention_ms < 86400000:
            findings.append(finding(
                "MEDIUM",
                f"Kafka topic '{name}' has retention below 24 hours",
                "Short retention reduces replay capability during incidents.",
                "Use retention based on recovery and audit requirements.",
                file
            ))

    return findings


def evaluate_terraform_config(data, file):
    findings = []
    resources = data.get("resource", [])

    for block in resources:
        for resource_type, instances in block.items():

            if resource_type == "aws_s3_bucket_public_access_block":
                for name, config in instances.items():
                    if config.get("block_public_acls") is False or config.get("block_public_policy") is False:
                        findings.append(finding(
                            "CRITICAL",
                            f"S3 bucket public access protection is weak: {name}",
                            "Public exposure can lead to data leakage.",
                            "Enable all S3 public access block settings.",
                            file
                        ))

    return findings
