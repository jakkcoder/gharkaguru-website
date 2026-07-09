# Website SQLite + GCS backend

Cloud Run now runs **nginx (SPA) + FastAPI** in one container.

## What gets stored

GCS object: `gs://vertex-ai-learning-487906-gharka-leads/website.db`

| Table | Purpose |
|-------|---------|
| `users` | Parent/student + teacher phone logins |
| `sessions` | Bearer tokens from `/api/auth/otp/send` |
| `teacher_applications` | Drafts + submitted teacher registrations |
| `inquiries` | Tutor inquiries + homepage lead inquiries |
| `enquiries` | Student dashboard enquiry list |

Uploads (photos / ID docs) go to:
`gs://vertex-ai-learning-487906-gharka-leads/website-uploads/`

## API (same contracts as the React clients)

- `POST /v1/api/auth/otp/send` — phone login (no OTP), creates user + session
- `POST /v1/api/teacher/application/draft` — save draft
- `GET  /v1/api/teacher/application` — application status
- `POST /v1/api/teacher/register` — multipart final submit
- `POST /v1/api/inquiry` / `/lead-inquiry`
- `GET  /v1/api/enquiries`
- `GET  /v1/api/admin/stats` — quick counts

Every write syncs `website.db` back to GCS (lock + generation).

## Local API only

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATA_DIR=/tmp/website-data PULL_ON_STARTUP=false PYTHONPATH=.
python -m uvicorn app.main:app --reload --port 8081
```

## Deploy

```bash
bash scripts/deploy_cloud_run.sh
```
