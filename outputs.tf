output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "config_test_security_group_id" {
  description = "Security Group ID for AWS Config restricted-ssh test"
  value       = aws_security_group.config_test.id
}

output "remediation_test_security_group_id" {
  description = "Security Group ID for Lambda auto remediation test"
  value       = aws_security_group.remediation_test.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.remediate_sg.function_name
}

output "eventbridge_rule_name" {
  description = "EventBridge rule name"
  value       = aws_cloudwatch_event_rule.sg_ingress_change.name
}

output "config_rule_name" {
  description = "AWS Config restricted-ssh rule name"
  value       = aws_config_config_rule.restricted_ssh.name
}

output "sns_topic_arn" {
  description = "SNS Topic ARN"
  value       = aws_sns_topic.remediation.arn
}

output "audit_bucket_name" {
  description = "S3 bucket for CloudTrail and AWS Config logs"
  value       = aws_s3_bucket.audit.id
}