from beacon.scanner import scan_file, scan_path


def test_kubernetes_hardening_and_disruption_rules_are_scanned(tmp_path):
    manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments
  namespace: prod
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: payments
    spec:
      hostNetwork: true
      containers:
        - name: api
          image: payments:1.0.0
          securityContext:
            allowPrivilegeEscalation: true
"""
    path = tmp_path / "deployment.yaml"
    path.write_text(manifest)

    findings = scan_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "k8s.workload.topology_spread.missing" in rule_ids
    assert "k8s.workload.pod_disruption_budget.missing" in rule_ids
    assert "k8s.workload.network_policy.missing" in rule_ids
    assert "k8s.workload.host_namespace.enabled" in rule_ids
    assert "k8s.container.run_as_non_root.missing" in rule_ids
    assert "k8s.container.allow_privilege_escalation.enabled" in rule_ids
    assert "k8s.container.read_only_root_filesystem.disabled" in rule_ids
    assert "k8s.container.seccomp_profile.missing" in rule_ids


def test_kubernetes_hardening_rules_respect_secure_manifests(tmp_path):
    manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payments
  namespace: prod
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: payments
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: payments
      containers:
        - name: api
          image: payments@sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            seccompProfile:
              type: RuntimeDefault
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: payments-pdb
  namespace: prod
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: payments
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: payments
  namespace: prod
spec:
  podSelector:
    matchLabels:
      app: payments
  policyTypes:
    - Ingress
"""
    path = tmp_path / "secure-deployment.yaml"
    path.write_text(manifest)

    findings = scan_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "k8s.workload.topology_spread.missing" not in rule_ids
    assert "k8s.workload.pod_disruption_budget.missing" not in rule_ids
    assert "k8s.workload.network_policy.missing" not in rule_ids
    assert "k8s.container.run_as_non_root.missing" not in rule_ids
    assert "k8s.container.allow_privilege_escalation.enabled" not in rule_ids
    assert "k8s.container.read_only_root_filesystem.disabled" not in rule_ids
    assert "k8s.container.seccomp_profile.missing" not in rule_ids


def test_cicd_supply_chain_and_governance_rules_are_scanned(tmp_path):
    workflow = """
name: Release
on:
  push:
    branches: [main]
jobs:
  deploy-prod:
    runs-on: ubuntu-latest
    permissions: write-all
    steps:
      - uses: actions/checkout@v4
      - uses: vendor/deploy-action@v2
      - run: ./deploy production
"""
    path = tmp_path / "release.yaml"
    path.write_text(workflow)

    findings = scan_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "cicd.github.third_party_actions.unpinned" in rule_ids
    assert "cicd.deployment.timeout.missing" in rule_ids
    assert "cicd.deployment.concurrency.missing" in rule_ids


def test_cloud_and_iam_readiness_rules_are_scanned(tmp_path):
    inventory = """
cloud_inventory:
  resources:
    - type: aws_db_instance
      name: prod-db
      config:
        publicly_accessible: false
        backup_retention_period: 7
        multi_az: false
        region: us-east-1
        tags:
          environment: production
    - type: aws_autoscaling_group
      name: api-asg
      config:
        desired_capacity: 4
        max_size: 4
        min_size: 2
        region: us-east-1
        tags:
          environment: production
    - type: aws_vpc_endpoint
      name: ssm-endpoint
      config:
        private_dns_enabled: false
        region: us-east-1
        tags:
          environment: production
    - type: aws_instance
      name: api-node
      config:
        monitoring: true
        region: us-east-1
        tags:
          environment: production
    - type: cloud_quota_profile
      name: compute-quota
      config:
        quota_limit: 10
        required_capacity: 9
        reserved_buffer: 2
    - type: aws_iam_policy
      name: admin-policy
      config:
        policy:
          Version: "2012-10-17"
          Statement:
            - Effect: Allow
              Action: "*"
              Resource: "*"
"""
    path = tmp_path / "cloud.yaml"
    path.write_text(inventory)

    findings = scan_file(str(path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "cloud.database.rds.multi_az.disabled" in rule_ids
    assert "cloud.database.rds.private_subnet.missing" in rule_ids
    assert "cloud.compute.autoscaling.capacity.insufficient" in rule_ids
    assert "cloud.network.vpc_endpoint.private_dns.disabled" in rule_ids
    assert "cloud.quota.headroom.insufficient" in rule_ids
    assert "cloud.region.high_availability.missing" in rule_ids
    assert "iam.permissions.wildcard" in rule_ids
    assert "iam.admin_or_owner.excessive" in rule_ids


def test_cross_domain_readiness_correlations_are_added(tmp_path):
    (tmp_path / "cloud.tf").write_text(
        """
resource \"aws_security_group\" \"open\" {
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = \"tcp\"
    cidr_blocks = [\"0.0.0.0/0\"]
  }
}

resource \"aws_db_instance\" \"db\" {
  publicly_accessible    = true
  backup_retention_period = 0
}

resource \"aws_s3_bucket\" \"public_bucket\" {
  bucket = \"public-bucket\"
}

resource \"aws_s3_bucket_public_access_block\" \"public_bucket\" {
  bucket                  = aws_s3_bucket.public_bucket.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}
"""
    )
    (tmp_path / "release.yaml").write_text(
        """
name: Release
on:
  pull_request_target:
  push:
    branches: [main]
permissions: write-all
jobs:
  deploy-prod:
    runs-on: ubuntu-latest
    steps:
      - uses: vendor/deploy-action@v2
      - run: ./deploy production
"""
    )
    (tmp_path / "capacity.yaml").write_text(
        """
cloud_inventory:
  resources:
    - type: cloud_quota_profile
      name: compute-quota
      config:
        quota_limit: 10
        required_capacity: 9
        reserved_buffer: 2
    - type: aws_autoscaling_group
      name: api-asg
      config:
        desired_capacity: 4
        max_size: 4
        min_size: 2
"""
    )

    findings = scan_path(str(tmp_path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "readiness.correlation.internet_exposed_database" in rule_ids
    assert "readiness.correlation.storage_data_exposure" in rule_ids
    assert "readiness.correlation.uncontrolled_production_deploy" in rule_ids
    assert "readiness.correlation.capacity_plan_mismatch" in rule_ids
