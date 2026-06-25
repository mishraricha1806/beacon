resource "aws_db_instance" "checkout" {
  identifier              = "checkout-prod"
  publicly_accessible     = false
  backup_retention_period = 0
  deletion_protection     = false
  multi_az                = false
}

resource "aws_s3_bucket" "archive" {
  bucket = "checkout-prod-archive"
}
