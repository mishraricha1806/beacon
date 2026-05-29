resource "aws_s3_bucket" "customer_exports" {
  bucket = "customer-exports-prod"
}

resource "aws_s3_bucket_public_access_block" "customer_exports" {
  bucket                  = aws_s3_bucket.customer_exports.id
  block_public_acls       = false
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_security_group" "public_api" {
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "orders" {
  publicly_accessible    = true
  backup_retention_period = 0
}

resource "aws_instance" "api" {
  ami           = "ami-123456"
  instance_type = "t3.micro"
}
