# AWS Infrastructure as Code Example (Terraform)
# This is a template for your AWS resources

# RDS Database
resource "aws_db_instance" "scrum_db" {
  identifier     = "scrum-database"
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.micro"
  
  allocated_storage = 20
  storage_type      = "gp2"
  
  db_name  = "scrum_db"
  username = "admin"
  password = var.db_password
  
  skip_final_snapshot = false
}

# S3 Bucket
resource "aws_s3_bucket" "scrum_files" {
  bucket = "scrum-app-files"
}

# Output
output "rds_endpoint" {
  value = aws_db_instance.scrum_db.endpoint
}
