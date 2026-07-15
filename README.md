# chore-chart
Backend for ChoreChart Application 


## Architecture
<img width="830" height="277" alt="Screenshot 2026-07-15 at 2 35 50 AM" src="https://github.com/user-attachments/assets/9612eae3-92de-4fe6-a1e1-a56fea23ff55" />

## AWS Services Used
 
| Service | Role |
|---|---|
| **AWS Lambda** | Core logic — reads chores, sends emails | 
| **CloudFormation** | Infrastructure as Code | 
| **S3** | Stores Lambda code, chores list, email template, daily logs | 
| **EventBridge** | Scheduled daily trigger (cron rule) | 
| **SNS** | Email delivery to multiple recipients | 


## How it Works

1. **EventBridge** fires the Lambda every day at 10:30 AM CEST (UTC + 2hr) time
2. **Lambda** loads `chores.json` and `email_template.txt` from S3
3. For each recipient, Lambda picks 3 chores using a date+email seed so:
   - Every recipient gets a **different** set of chores
   - The same set is assigned for the whole day (idempotent retries)
4. Lambda publishes each personalised email to the **SNS topic**
5. SNS delivers to each confirmed subscriber
6. Lambda writes a **daily log** to `s3://bucket/logs/YYYY-MM-DD.json`

### Prerequisites
- AWS Account
- GitHub account
### Step 1 — Clone the repo
```bash
git clone https://github.com/tbhowmick17/chore-chart.git
cd chore-chart
```
 
### Step 2 — Add GitHub Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**
 
| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | From AWS |
| `AWS_SECRET_ACCESS_KEY` | From AWS |
| `AWS_SESSION_TOKEN` | From AWS |
| `RECIPIENT_EMAILS` | Comma-separated list |
 
### Step 3 — Push to deploy
```bash
git push origin main
```
 
The pipeline will:
1. Create the S3 bucket
2. Upload `handler.zip`, `chores.json`, `email_template.txt`
3. Deploy the CloudFormation stack (SNS, Lambda, EventBridge)
4. Subscribe all recipients to the SNS topic
5. Test invoke the Lambda

## Teardown
 
```bash
aws cloudformation delete-stack \
  --stack-name chore-chart \
  --region us-east-1
 
aws s3 rb s3://chore-scheduler-<ACCOUNT_ID>-us-east-1 --force
```

## Cost Estimate
 
| Service | Free Tier | Expected Usage |
|---|---|---|
| Lambda | 1M requests/month | ~30/month |
| EventBridge | 14M events/month | ~30/month |
| SNS | 1000 email notifications/month | ~90/month |
| S3 | 5GB storage | < 1MB |
 
**Estimated monthly cost: $0.00** within free tier limits.
