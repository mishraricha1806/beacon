resource "aws_db_instance" "checkout" {
  identifier              = "checkout-prod"
  publicly_accessible     = false
  backup_retention_period = 0
  deletion_protection     = false
  storage_encrypted       = false
  multi_az                = false
}

resource "aws_s3_bucket" "archive" {
  bucket = "checkout-prod-archive"
}

resource "aws_iam_role_policy_attachment" "node_admin" {
  role       = "eks-node-role"
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
