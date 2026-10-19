# Terraform manages the AWS "data plane" (S3, DynamoDB, ECR, IAM, Secrets
# Manager). The Kubernetes cluster itself is created separately with eksctl
# (see infra/eks-cluster.yaml) -- a common real-world split where
# application infra lives in Terraform and the cluster lifecycle is owned
# by a cluster-specific tool. Both are equally valid; this repo shows both.

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and fill in before running `terraform init` in a real team
  # setting, so state isn't just a local file:
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "docklight-rag/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

# ---------------- S3: raw document storage ----------------
resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-documents-${var.environment}"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------- DynamoDB: documents, users, conversations ----------------
resource "aws_dynamodb_table" "documents" {
  name         = "${var.project_name}-documents-metadata"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "doc_id"

  attribute {
    name = "doc_id"
    type = "S"
  }
  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user_id-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }
}

resource "aws_dynamodb_table" "users" {
  name         = "${var.project_name}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }
  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }
}

resource "aws_dynamodb_table" "conversations" {
  name         = "${var.project_name}-conversations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "conversation_id"

  attribute {
    name = "conversation_id"
    type = "S"
  }
}

# ---------------- ECR: container image repositories ----------------
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}-frontend"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

# ---------------- Secrets Manager: Pinecone key + JWT secret ----------------
resource "aws_secretsmanager_secret" "app_secrets" {
  name = "${var.project_name}/${var.environment}/secrets"
}

# ---------------- IAM: least-privilege policy for the backend/worker pods ----------------
resource "aws_iam_policy" "app_permissions" {
  name   = "${var.project_name}-app-permissions"
  policy = file("${path.module}/../iam-policy.json")
}
