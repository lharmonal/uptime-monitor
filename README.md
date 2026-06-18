# Uptime Monitor

A serverless AWS system that checks whether websites are up every 5 minutes, logs every result to DynamoDB, and sends an email alert via SNS when a site goes down.

## Architecture

```
EventBridge (cron) → Lambda (Python) → DynamoDB (all results)
                                      → SNS (email on DOWN)
```

**EventBridge** triggers the Lambda on a `rate(5 minutes)` schedule — no server needs to be running between checks.

**Lambda** makes an HTTP GET request to each URL, records the status code and response, then writes the result to DynamoDB regardless of outcome. If a site is DOWN, it also publishes an alert to SNS.

**DynamoDB** stores every check result with `url` as the partition key and `checked_at` (ISO timestamp) as the sort key. This means you can query the full history for any URL in time order. On-demand billing mode keeps costs near zero at this scale.

**SNS** delivers email alerts when a site is unreachable or returns a non-2xx status. The topic decouples the Lambda from the delivery mechanism — swapping email for Slack or PagerDuty would only require adding a new subscription.

## Why serverless?

The traditional approach would be an EC2 instance running a cron job. That means paying for a server 24/7 even though the actual work takes ~1 second every 5 minutes. With Lambda, you pay only for execution time — at this scale, it runs entirely within the AWS free tier.

## Infrastructure as Code

All AWS resources are defined in Terraform under `terraform/`. Running `terraform apply` provisions everything from scratch:

- IAM role with least-privilege permissions (only `dynamodb:PutItem`, `sns:Publish`, and CloudWatch Logs write access)
- Lambda function with the monitor code zipped and deployed automatically
- DynamoDB table
- SNS topic and email subscription
- EventBridge rule and Lambda invoke permission
- CloudWatch log group with 14-day retention

## Project structure

```
uptime-monitor/
├── lambda/
│   └── monitor.py        # URL checker, DynamoDB writer, SNS alerter
└── terraform/
    ├── main.tf            # All AWS resources
    ├── variables.tf       # Configurable inputs
    └── outputs.tf         # Resource names and ARNs after apply
```

## Setup

**Prerequisites:** AWS CLI configured, Terraform installed.

```bash
cd terraform
terraform init
terraform apply -var="alert_email=you@example.com"
```

To add or remove URLs being monitored, edit `URLS_TO_MONITOR` in `lambda/monitor.py` and re-run `terraform apply`.

## Design decisions

- **No hardcoded ARNs or table names** — all config comes from environment variables set by Terraform at deploy time
- **Every result logged, not just failures** — DynamoDB gets a row for every check so you have a full uptime history, not just an alert log
- **Least-privilege IAM** — the Lambda role can only write to DynamoDB, publish to SNS, and write logs; it has no broader AWS access
- **`AWS_REGION` not set manually** — Lambda sets this automatically; overriding it causes conflicts
