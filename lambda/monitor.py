import json
import urllib.request
import urllib.error
import boto3
import os
from datetime import datetime, timezone

# The list of URLs you want to monitor
URLS_TO_MONITOR = [
    "https://www.google.com",
    "https://www.github.com",
    "https://httpstat.us/500"  # this one intentionally returns an error so we can test alerting
]

# How long to wait for a response before considering the site down (in seconds)
TIMEOUT_SECONDS = 10

def check_url(url):
    """
    Sends an HTTP GET request to a URL and returns whether it's up or down.
    Returns a dictionary with the result.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UptimeMonitor/1.0"})
        response = urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)
        status_code = response.getcode()

        # Any 2xx status code means the site is up
        if 200 <= status_code < 300:
            return {
                "url": url,
                "status": "UP",
                "status_code": status_code,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "url": url,
                "status": "DOWN",
                "status_code": status_code,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }

    except urllib.error.HTTPError as e:
        # Server responded but with an error code (4xx, 5xx)
        return {
            "url": url,
            "status": "DOWN",
            "status_code": e.code,
            "error": str(e.reason),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    except urllib.error.URLError as e:
        # Couldn't reach the server at all (DNS failure, timeout, etc.)
        return {
            "url": url,
            "status": "DOWN",
            "status_code": None,
            "error": str(e.reason),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        # Catches connection resets, malformed responses, and other unexpected errors
        return {
            "url": url,
            "status": "DOWN",
            "status_code": None,
            "error": str(e),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

def save_result_to_dynamodb(result):
    """
    Saves a check result to DynamoDB.
    We'll set up the actual table in the next phase.
    """
    dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE", "uptime-monitor-results"))

    table.put_item(Item={
        "url": result["url"],
        "checked_at": result["checked_at"],
        "status": result["status"],
        "status_code": str(result["status_code"]) if result.get("status_code") is not None else "N/A",
        "error": result.get("error", "none")
    })

def send_alert(result):
    """
    Sends an SNS alert when a site is down.
    We'll hook up the actual SNS topic in the next phase.
    """
    sns = boto3.client("sns", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    topic_arn = os.environ.get("SNS_TOPIC_ARN")

    if not topic_arn:
        print("SNS_TOPIC_ARN not set, skipping alert")
        return

    message = f"""
    ALERT: Site is DOWN

    URL: {result['url']}
    Status Code: {result.get('status_code', 'N/A')}
    Error: {result.get('error', 'N/A')}
    Checked At: {result['checked_at']}
    """

    sns.publish(
        TopicArn=topic_arn,
        Subject=f"Uptime Alert: {result['url']} is DOWN",
        Message=message
    )

def lambda_handler(event, context):
    """
    Main entry point. AWS calls this function when the Lambda runs.
    """
    print(f"Starting uptime checks at {datetime.now(timezone.utc).isoformat()}")
    
    results = []

    for url in URLS_TO_MONITOR:
        print(f"Checking {url}...")
        result = check_url(url)
        print(f"Result: {result['status']} - {url}")

        # Save every result to DynamoDB regardless of status
        save_result_to_dynamodb(result)

        # Only alert if the site is down
        if result["status"] == "DOWN":
            send_alert(result)

        results.append(result)

    print(f"Completed {len(results)} checks")
    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }