output "s3_bucket_name" {
  value = aws_s3_bucket.documents.bucket
}

output "dynamodb_documents_table" {
  value = aws_dynamodb_table.documents.name
}

output "dynamodb_users_table" {
  value = aws_dynamodb_table.users.name
}

output "dynamodb_conversations_table" {
  value = aws_dynamodb_table.conversations.name
}

output "ecr_backend_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "app_secrets_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}

output "app_iam_policy_arn" {
  value = aws_iam_policy.app_permissions.arn
}
