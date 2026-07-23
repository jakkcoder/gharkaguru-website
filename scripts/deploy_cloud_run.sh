#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-vertex-ai-learning-487906}"
REGION="${REGION:-asia-southeast1}"
SERVICE="${SERVICE:-gharkaguru-website}"
REPOSITORY="${REPOSITORY:-cloud-run-source-deploy}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE}:latest"
SA_EMAIL="${SA_EMAIL:-954888342020-compute@developer.gserviceaccount.com}"
BUCKET="${BUCKET:-vertex-ai-learning-487906-gharka-leads}"
WEBSITE_DB_GCS="${WEBSITE_DB_GCS:-gs://${BUCKET}/website.db}"
FINALIZED_DEALS_DB_GCS="${FINALIZED_DEALS_DB_GCS:-gs://${BUCKET}/finalized_deals.db}"
FINALIZED_DEALS_PASSWORD="${FINALIZED_DEALS_PASSWORD:-khus@123}"
PARENT_LEADS_DB_GCS="${PARENT_LEADS_DB_GCS:-gs://${BUCKET}/parent-leads-inbox/parent_leads.db}"
PARENT_LEADS_ADMIN_PASSWORD="${PARENT_LEADS_ADMIN_PASSWORD:-khus@123}"
LEADS_START_DATE="${LEADS_START_DATE:-2026-07-19}"
UPLOADS_GCS_PREFIX="${UPLOADS_GCS_PREFIX:-gs://${BUCKET}/website-uploads}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Ensuring GCS website.db exists (empty seed if missing)"
if ! gsutil -q stat "$WEBSITE_DB_GCS"; then
  TMP_DB="$(mktemp /tmp/websiteXXXX.db)"
  python3 - "$TMP_DB" <<'PY'
import sqlite3
import sys

conn = sqlite3.connect(sys.argv[1])
conn.executescript(
    """
CREATE TABLE IF NOT EXISTS users (
  phone TEXT PRIMARY KEY, role TEXT NOT NULL, created_at TEXT NOT NULL, last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY, phone TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS teacher_applications (
  reference_id TEXT PRIMARY KEY, phone TEXT NOT NULL UNIQUE, status TEXT NOT NULL,
  profile_completion_percent INTEGER NOT NULL DEFAULT 0, data_json TEXT NOT NULL DEFAULT '{}',
  idempotency_key TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS inquiries (
  inquiry_id TEXT PRIMARY KEY, kind TEXT NOT NULL, contact_phone TEXT NOT NULL,
  tutor_id TEXT, class_level TEXT, subject TEXT, message TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS enquiries (
  id TEXT PRIMARY KEY, phone TEXT, tutor_id TEXT, tutor_name TEXT, subject TEXT,
  message TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL
);
"""
)
conn.commit()
conn.close()
print("seeded", sys.argv[1])
PY
  gsutil cp "$TMP_DB" "$WEBSITE_DB_GCS"
  rm -f "$TMP_DB"
fi

echo "==> Ensuring GCS finalized_deals.db exists (empty seed if missing)"
if ! gsutil -q stat "$FINALIZED_DEALS_DB_GCS"; then
  TMP_FD="$(mktemp /tmp/finalizedXXXX.db)"
  python3 - "$TMP_FD" <<'PY'
import sqlite3
import sys

conn = sqlite3.connect(sys.argv[1])
conn.executescript(
    """
CREATE TABLE IF NOT EXISTS finalized_deals (
  id TEXT PRIMARY KEY,
  parent_name TEXT NOT NULL DEFAULT '',
  parent_phone TEXT NOT NULL DEFAULT '',
  parent_class TEXT NOT NULL DEFAULT '',
  parent_location TEXT NOT NULL DEFAULT '',
  parent_mode TEXT NOT NULL DEFAULT '',
  teacher_name TEXT NOT NULL DEFAULT '',
  teacher_phone TEXT NOT NULL DEFAULT '',
  teacher_subject TEXT NOT NULL DEFAULT '',
  teacher_notes TEXT NOT NULL DEFAULT '',
  finalized_amount REAL,
  class_start_date TEXT NOT NULL,
  submitted_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_finalized_deals_start ON finalized_deals(class_start_date);
CREATE INDEX IF NOT EXISTS idx_finalized_deals_deleted ON finalized_deals(deleted_at);
"""
)
conn.commit()
conn.close()
print("seeded", sys.argv[1])
PY
  gsutil cp "$TMP_FD" "$FINALIZED_DEALS_DB_GCS"
  rm -f "$TMP_FD"
fi

echo "==> Granting storage access to $SA_EMAIL"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin" \
  --project="$PROJECT_ID" >/dev/null || true

ENV_FILE="$(mktemp /tmp/website-env.XXXXXX.yaml)"
cat > "$ENV_FILE" <<EOF
GOOGLE_CLOUD_PROJECT: "${PROJECT_ID}"
WEBSITE_DB_GCS: "${WEBSITE_DB_GCS}"
FINALIZED_DEALS_DB_GCS: "${FINALIZED_DEALS_DB_GCS}"
FINALIZED_DEALS_PASSWORD: "${FINALIZED_DEALS_PASSWORD}"
GCS_LEADS_BUCKET: "${BUCKET}"
GCS_PARENT_LEADS_DB_OBJECT: "parent-leads-inbox/parent_leads.db"
PARENT_LEADS_ADMIN_PASSWORD: "${PARENT_LEADS_ADMIN_PASSWORD}"
LEADS_START_DATE: "${LEADS_START_DATE}"
PARENT_LEADS_META_SYNC: "true"
PAGE_ID: "347244005670587"
META_API_VERSION: "v25.0"
LEADS_OVERLAP_SECONDS: "3600"
PARENT_FORM_IDS_EXTRA: "${PARENT_FORM_IDS_EXTRA:-}"
UPLOADS_GCS_PREFIX: "${UPLOADS_GCS_PREFIX}"
DATA_DIR: "/tmp/website-data"
PULL_ON_STARTUP: "true"
CORS_ORIGINS: "https://gharkaguru.com,https://www.gharkaguru.com,https://gharkaguru-website-lmquvtnfja-as.a.run.app,https://gharkaguru-website-954888342020.asia-southeast1.run.app"
EOF

echo "==> Building and pushing image: $IMAGE"
gcloud builds submit --tag "$IMAGE" --project="$PROJECT_ID"

echo "==> Deploying Cloud Run service: $SERVICE"
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --platform=managed \
  --service-account="$SA_EMAIL" \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=900 \
  --max-instances=3 \
  --env-vars-file="$ENV_FILE" \
  --set-secrets="PAGE_ACCESS_TOKEN=PAGE_ACCESS_TOKEN:latest"

rm -f "$ENV_FILE"

URL="$(gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')"
echo
echo "Deployed: $URL"
echo "Health:   ${URL}/healthz"
echo "API:      ${URL}/v1/api/health"
echo "Stats:    ${URL}/v1/api/admin/stats"
echo "Deals:    ${URL}/finilized_deals"
echo "Parent Leads: ${URL}/parent_leads/admin/login"
echo "DB:       ${WEBSITE_DB_GCS}"
echo "Deals DB: ${FINALIZED_DEALS_DB_GCS}"
echo "Parent Leads DB: ${PARENT_LEADS_DB_GCS}"
