variable "aws_region" {
  description = "AWS region to deploy resources into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix used for naming every resource"
  type        = string
  default     = "docklight-rag"
}

variable "environment" {
  description = "Deployment environment tag (e.g. dev, staging, production)"
  type        = string
  default     = "production"
}
