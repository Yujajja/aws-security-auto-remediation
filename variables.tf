variable "aws_profile" {
  description = "AWS CLI profile name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "aws-security-auto-remediation"
}

variable "alert_email" {
  description = "Email address for SNS alarm notification"
  type        = string
}