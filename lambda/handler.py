import json
import os
import random

import boto3
from datetime import datetime

sns_client = boto3.client("sns")
s3_client = boto3.client("s3")

NUM_CHORES = 3

def load_template_from_s3(bucket: str, key: str) -> str:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")

def load_chores_from_s3(bucket: str, key: str) -> list:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    data = json.loads(response["Body"].read().decode("utf-8"))
    return data["chores"]

def pick_chores_for_recipient(chores: list, recipient_email: str):
    today = datetime.now().strftime("%Y%m%d")
    seed = hash(f"{today}:{recipient_email}") & 0xFFFFFFFF
    rng = random.Random(seed)
    return rng.sample(chores, NUM_CHORES)

def log_assignments_to_s3(bucket: str, assignments: list):
    today = datetime.now().strftime("%Y-%m-%d")
    key = f"logs/{today}.json"
    log_entry = {
        "date": today,
        "generated_at": datetime.now().isoformat(),
        "assignments": assignments,
    }
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(log_entry, indent=2),
        ContentType="application/json",
    )
    print(f"[OK] Daily log written to s3://{bucket}/{key}")

def lambda_handler(event, context):
    topic_arn = os.environ["SNS_TOPIC_ARN"]
    schedule_name = os.environ.get("SCHEDULE_NAME", "Daily Chore Scheduler")
    bucket = os.environ["S3_BUCKET"]
    chores_key = os.environ.get("CHORES_KEY", "chores.json")
    template_key = os.environ.get("TEMPLATE_KEY", "email_template.txt")

    chores = load_chores_from_s3(bucket, chores_key)
    print(f"[OK] Loaded {len(chores)} chores from s3://{bucket}/{chores_key}")

    template = load_template_from_s3(bucket, template_key)
    print(f"[OK] Loaded email template from s3://{bucket}/{template_key}")

    recipients_raw = os.environ.get("RECIPIENT_EMAILS", "")
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    if not recipients:
        print("[WARN] No recipients configured in RECIPIENT_EMAILS env var.")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "No recipients configured"}),
        }

    now = datetime.now().strftime("%A, %B %d %Y at %H:%M UTC")
    results = []

    for recipient in recipients:
        chores_today = pick_chores_for_recipient(chores, recipient)
        chore_list = "\n".join(f"  {i+1}. {chore}" for i, chore in enumerate(chores_today))

        subject = f"Your Chores for {datetime.now().strftime('%A, %B %d')}"

        message = template.format(
            num_chores=NUM_CHORES,
            schedule_name=schedule_name,
            assigned_on=now,
            chore_list=chore_list,
        )

        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )

        print(f"[OK] Sent to {recipient} | MessageId: {response['MessageId']} | Chores: {chores_today}")
        results.append({
            "recipient": recipient,
            "messageId": response["MessageId"],
            "chores": chores_today,
        })

    # Write daily log to S3
    log_assignments_to_s3(bucket, results)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Chore notifications sent to {len(results)} recipient(s)",
            "results": results,
        }),
    }