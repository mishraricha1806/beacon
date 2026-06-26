import json

from beacon.iac_coverage import analyze_iac_coverage


def test_iac_coverage_detects_unmanaged_cloud_resources(tmp_path):
    inventory = {
        "resources": [
            {
                "type": "aws_instance",
                "name": "api",
                "id": "i-managed",
                "tags": {"owner": "platform"},
                "cost_30d": 5,
            },
            {
                "type": "aws_opensearch_domain",
                "name": "claims-search",
                "arn": "arn:aws:es:us-east-1:123456789012:domain/claims-search",
                "account_id": "123456789012",
                "region": "us-east-1",
                "tags": {},
                "activity_30d": True,
                "cost_30d": 100,
                "config": {
                    "domain_name": "claims-search",
                    "network_exposure": "public",
                },
            },
        ]
    }
    state = {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "type": "aws_instance",
                        "name": "api",
                        "values": {"id": "i-managed", "name": "api"},
                    }
                ]
            }
        }
    }

    inventory_path = tmp_path / "inventory.json"
    state_path = tmp_path / "state.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")

    findings = analyze_iac_coverage(str(inventory_path), str(state_path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "iac_coverage.resource.unmanaged" in rule_ids
    assert "iac_coverage.resource.owner_missing" in rule_ids
    assert "iac_coverage.resource.active_unmanaged" in rule_ids
    assert "iac_coverage.resource.public_unmanaged" in rule_ids
    assert "iac_coverage.resource.sensitive_unmanaged" in rule_ids
    assert not any(finding["evidence"]["resource_name"] == "api" for finding in findings)


def test_iac_coverage_uses_owner_registry(tmp_path):
    inventory = {
        "resources": [
            {
                "type": "aws_s3_bucket",
                "name": "legacy-exports",
                "config": {"bucket": "legacy-exports"},
            }
        ]
    }
    state = {"values": {"root_module": {"resources": []}}}
    owners = {"owners": {"aws_s3_bucket.legacy-exports": {"owner": "data-platform"}}}

    inventory_path = tmp_path / "inventory.json"
    state_path = tmp_path / "state.json"
    owners_path = tmp_path / "owners.yaml"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    owners_path.write_text(
        "owners:\n  aws_s3_bucket.legacy-exports:\n    owner: data-platform\n",
        encoding="utf-8",
    )

    findings = analyze_iac_coverage(str(inventory_path), str(state_path), str(owners_path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "iac_coverage.resource.unmanaged" in rule_ids
    assert "iac_coverage.resource.sensitive_unmanaged" in rule_ids
    assert "iac_coverage.resource.owner_missing" not in rule_ids


def test_iac_coverage_normalizes_aws_config_inventory_export(tmp_path):
    inventory = {
        "configurationItems": [
            {
                "resourceType": "AWS::OpenSearchService::Domain",
                "resourceId": "claims-search",
                "resourceName": "claims-search",
                "accountId": "123456789012",
                "awsRegion": "us-east-1",
                "arn": "arn:aws:es:us-east-1:123456789012:domain/claims-search",
                "tags": [{"key": "environment", "value": "prod"}],
                "configuration": json.dumps(
                    {
                        "DomainName": "claims-search",
                        "Endpoint": "search-claims.example.us-east-1.es.amazonaws.com",
                    }
                ),
            }
        ]
    }
    state = {"values": {"root_module": {"resources": []}}}

    inventory_path = tmp_path / "aws-config.json"
    state_path = tmp_path / "state.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")

    findings = analyze_iac_coverage(str(inventory_path), str(state_path))
    rule_ids = {finding["rule_id"] for finding in findings}
    evidence = findings[0]["evidence"]

    assert evidence["resource_type"] == "aws_opensearch_domain"
    assert evidence["resource_name"] == "claims-search"
    assert evidence["account_id"] == "123456789012"
    assert evidence["region"] == "us-east-1"
    assert "iac_coverage.resource.public_unmanaged" in rule_ids
    assert "iac_coverage.resource.sensitive_unmanaged" in rule_ids


def test_iac_coverage_normalizes_steampipe_or_cloudquery_rows(tmp_path):
    inventory = {
        "rows": [
            {
                "__table": "aws_s3_bucket",
                "name": "legacy-exports",
                "arn": "arn:aws:s3:::legacy-exports",
                "account_id": "123456789012",
                "region": "us-east-1",
                "tags": {"owner": "data-platform"},
                "monthly_cost": "12.25",
            }
        ]
    }
    state = {"values": {"root_module": {"resources": []}}}

    inventory_path = tmp_path / "rows.json"
    state_path = tmp_path / "state.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")

    findings = analyze_iac_coverage(str(inventory_path), str(state_path))
    rule_ids = {finding["rule_id"] for finding in findings}

    assert "iac_coverage.resource.unmanaged" in rule_ids
    assert "iac_coverage.resource.active_unmanaged" in rule_ids
    assert "iac_coverage.resource.sensitive_unmanaged" in rule_ids
    assert "iac_coverage.resource.owner_missing" not in rule_ids
