#!/bin/bash
set -euo pipefail

PROJECT_ID="stock-portfolio-agent"
REGION="us-central1"
JOB_NAME="portfolio-agent"
SA_NAME="portfolio-agent-sa"

# 1. Create service account
gcloud iam service-accounts create $SA_NAME \
  --display-name="Portfolio Agent Service Account"

# 2. Grant permissions
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# 3. Store API keys in Secret Manager
gcloud secrets create alpha-vantage-key --replication-policy="automatic"
gcloud secrets create fmp-api-key --replication-policy="automatic"
gcloud secrets create finnhub-api-key --replication-policy="automatic"
gcloud secrets create sendgrid-api-key --replication-policy="automatic"
gcloud secrets create telegram-bot-token --replication-policy="automatic"
gcloud secrets create gemini-api-key --replication-policy="automatic"

echo "Now set secret values with:"
echo "  echo -n 'YOUR_KEY' | gcloud secrets versions add SECRET_NAME --data-file=-"

# 4. Build & push container
gcloud builds submit --tag gcr.io/$PROJECT_ID/$JOB_NAME

# 5. Deploy Cloud Run Job
gcloud run jobs create $JOB_NAME \
  --image gcr.io/$PROJECT_ID/$JOB_NAME \
  --region $REGION \
  --service-account $SA_EMAIL \
  --memory 512Mi \
  --cpu 1 \
  --task-timeout 300s \
  --max-retries 1 \
  --set-env-vars="RUN_TYPE=morning"

# 6. Create Cloud Scheduler jobs
# Morning briefing at 6:30 AM CT (11:30 UTC)
gcloud scheduler jobs create http morning-briefing \
  --schedule="30 11 * * 1-5" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
  --http-method=POST \
  --message-body='{"overrides":{"containerOverrides":[{"env":[{"name":"RUN_TYPE","value":"morning"}]}]}}' \
  --oauth-service-account-email=$SA_EMAIL \
  --location=$REGION

# Evening briefing at 7:00 PM CT (00:00 UTC next day)
gcloud scheduler jobs create http evening-briefing \
  --schedule="0 0 * * 2-6" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
  --http-method=POST \
  --message-body='{"overrides":{"containerOverrides":[{"env":[{"name":"RUN_TYPE","value":"evening"}]}]}}' \
  --oauth-service-account-email=$SA_EMAIL \
  --location=$REGION

echo "✅ Setup complete!"
