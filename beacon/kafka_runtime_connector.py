from confluent_kafka.admin import AdminClient


def finding(severity, title, impact, recommendation, file="runtime-kafka"):
    return {
        "severity": severity,
        "title": title,
        "impact": impact,
        "recommendation": recommendation,
        "file": file
    }


def build_admin_config(
    bootstrap_server,
    security_protocol="PLAINTEXT",
    ca_cert=None,
    client_cert=None,
    client_key=None,
):
    config = {
        "bootstrap.servers": bootstrap_server,
        "security.protocol": security_protocol,
        "socket.timeout.ms": 3000,
        "request.timeout.ms": 3000,
        "metadata.max.age.ms": 30000,
    }

    if security_protocol in ["SSL", "SASL_SSL"]:
        if ca_cert:
            config["ssl.ca.location"] = ca_cert
        if client_cert:
            config["ssl.certificate.location"] = client_cert
        if client_key:
            config["ssl.key.location"] = client_key

    return config


def analyze_kafka_cluster(
    bootstrap_server,
    security_protocol="PLAINTEXT",
    ca_cert=None,
    client_cert=None,
    client_key=None,
):
    findings = []

    try:
        config = build_admin_config(
            bootstrap_server=bootstrap_server,
            security_protocol=security_protocol,
            ca_cert=ca_cert,
            client_cert=client_cert,
            client_key=client_key,
        )

        admin_client = AdminClient(config)

        metadata = admin_client.list_topics(timeout=3)

        broker_count = len(metadata.brokers)
        topic_count = len([
            topic for topic in metadata.topics.keys()
            if not topic.startswith("__")
        ])

        findings.append(finding(
            "LOW",
            "Kafka cluster connection successful",
            f"Beacon connected successfully. Brokers detected: {broker_count}, user topics detected: {topic_count}.",
            "Beacon used read-only metadata access. No Kafka mutation operation was performed."
        ))

        if broker_count < 3:
            findings.append(finding(
                "HIGH",
                f"Kafka cluster has only {broker_count} broker(s)",
                "Low broker count can reduce resiliency and limit safe replication for production workloads.",
                "Use at least 3 brokers for production Kafka clusters where high availability is required."
            ))

        if topic_count > 200:
            findings.append(finding(
                "MEDIUM",
                f"Kafka cluster has high topic count: {topic_count}",
                "Large topic count can increase controller metadata load and operational complexity.",
                "Review topic lifecycle, ownership, retention, and whether old topics can be retired."
            ))

    except Exception as e:
        findings.append(finding(
            "ERROR",
            "Kafka cluster connection failed",
            str(e),
            "Check bootstrap server, network access, security protocol, certificates, and firewall rules."
        ))

    return findings