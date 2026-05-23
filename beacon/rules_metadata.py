"""Rule metadata registry for Beacon.

Each rule_id maps to metadata used for UI, provenance, and governance.
This is intentionally lightweight for now; later this can be loaded from YAML
or a database and include author, version, and links to remediation docs.
"""

RULES = {
    "kafka.topic.replication_factor.min": {
        "title": "Kafka topic replication factor below recommended minimum",
        "description": "Production Kafka topics should use replication_factor >= 3 for high availability.",
        "severity_default": "CRITICAL",
        "category": "resiliency",
        "author": "beacon.rules",
        "recommendation": "Set replication_factor=3 for production topics."
    },
    "kafka.topic.retention_bytes.missing": {
        "title": "Kafka topic missing retention_bytes",
        "description": "Missing retention_bytes can allow topics to grow uncontrollably if producer volume increases.",
        "severity_default": "HIGH",
        "category": "storage_sustainability",
        "author": "beacon.rules",
        "recommendation": "Set retention_bytes based on broker disk capacity and expected throughput."
    },
    "aws.s3.public_access_block.weak": {
        "title": "S3 public access block is weak",
        "description": "S3 public access block settings are disabled or set to permissive values, which may expose buckets publicly.",
        "severity_default": "CRITICAL",
        "category": "operational_safety",
        "author": "beacon.rules",
        "recommendation": "Block public access unless there is an explicit approved exception."
    }
}

