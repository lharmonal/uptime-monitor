variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for uptime check results"
  type        = string
  default     = "uptime-monitor-results"
}

variable "sns_topic_name" {
  description = "SNS topic name for downtime alerts"
  type        = string
  default     = "uptime-monitor-alerts"
}

variable "lambda_function_name" {
  description = "Lambda function name"
  type        = string
  default     = "uptime-monitor"
}

variable "alert_email" {
  description = "Email address to receive downtime alerts"
  type        = string
}
