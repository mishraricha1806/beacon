OBJECT_STORAGE_RESOURCE_TYPES = {
    "aws_s3_bucket",
    "aws_s3_bucket_public_access_block",
    "google_storage_bucket",
    "azurerm_storage_account",
}

IAM_RESOURCE_TYPES = {
    "aws_iam_policy",
    "aws_iam_role_policy_attachment",
    "aws_iam_user_policy_attachment",
    "aws_iam_group_policy_attachment",
    "google_project_iam_binding",
    "azurerm_role_assignment",
}

CLOUD_RESOURCE_TYPES = {
    "aws_security_group",
    "aws_db_instance",
    "aws_instance",
    "aws_autoscaling_group",
    "aws_vpc_endpoint",
    "azurerm_mssql_server",
    "azurerm_mysql_flexible_server",
    "azurerm_postgresql_flexible_server",
    "azurerm_key_vault",
    "azurerm_private_endpoint",
    "google_compute_firewall",
    "google_container_cluster",
    "google_sql_database_instance",
    "cloud_quota_profile",
}


def normalize_hcl_identifier(value):
    if not isinstance(value, str):
        return value

    return value.strip('"')


def is_object_storage_resource(resource_type):
    return resource_type in OBJECT_STORAGE_RESOURCE_TYPES


def is_iam_resource(resource_type):
    return resource_type in IAM_RESOURCE_TYPES


def is_cloud_resource(resource_type):
    return resource_type in CLOUD_RESOURCE_TYPES
