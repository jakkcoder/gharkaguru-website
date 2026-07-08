# Deploy gharkaguru.com to a Cloud Bucket

The GharKaGuru website is a **static SPA** after build — plain HTML, CSS, and JS files you upload to Google Cloud Storage (or any static host). No Node server or Docker required for the website itself.

The backend API runs separately (e.g. `https://api.gharkaguru.com`).

---

## 1. Build static files

```bash
cd tutornest_frontend
npm ci
npm run build:bucket
```

This produces a `dist/` folder ready to upload. It:

- Bakes in the production API URL (`https://api.gharkaguru.com/v1` from `.env.production`)
- Disables dev mocks (MSW)
- Creates `404.html` (copy of `index.html`) so client-side routes work on GCS

To use a different API URL at build time:

```bash
VITE_API_BASE_URL=https://your-api.example/v1 npm run build:bucket
```

---

## 2. Create a GCS bucket

```bash
export PROJECT_ID=your-gcp-project
export BUCKET=gharkaguru-website

gcloud storage buckets create "gs://${BUCKET}" \
  --project="${PROJECT_ID}" \
  --location=asia-south1 \
  --uniform-bucket-level-access
```

---

## 3. Upload the site

```bash
gcloud storage rsync -r dist/ "gs://${BUCKET}/" --delete-unmatched-destination-objects
```

Re-run this command after every deploy to push updates.

---

## 4. Map gharkaguru.com (recommended: Cloud CDN + Load Balancer)

For a custom domain with HTTPS on a bucket, use a **backend bucket** behind Cloud CDN:

1. Cloud Console → **Network services** → **Load balancing**
2. Create an HTTPS load balancer with a **Backend bucket** pointing at `gs://gharkaguru-website`
3. Enable **Cloud CDN**
4. Add your SSL certificate for `gharkaguru.com` and `www.gharkaguru.com`
5. Point DNS **A record** for `gharkaguru.com` to the load balancer IP

In the backend bucket settings, set:

- **404 response**: serve `404.html` (already in your upload)

This lets routes like `/search`, `/tutor/abc`, etc. work when users refresh or share links.

### Simpler (no custom domain yet)

Enable **Static website** on the bucket (Configuration → Website configuration):

- Main page: `index.html`
- Not found page: `404.html`

Access via `https://storage.googleapis.com/gharkaguru-website/index.html` until DNS is wired up.

---

## 5. Backend API (required)

The static site calls your API at build time URL. Default: `https://api.gharkaguru.com/v1`.

Ensure:

- API is deployed and reachable
- **CORS** allows `https://gharkaguru.com` and `https://www.gharkaguru.com`
- Tutor photos are served from the API (`/photo/:tutorId`)

Point `api.gharkaguru.com` DNS to your gateway/load balancer.

---

## 6. CI/CD (optional)

A GitHub Actions workflow can build and upload on every merge to `main`. See `.github/workflows/cd_gcs_website.yml`.

Required secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER` + `GCP_SERVICE_ACCOUNT_EMAIL` (or `GCP_SA_KEY`)
- `GCS_WEBSITE_BUCKET` — e.g. `gharkaguru-website`

---

## Local preview

```bash
npm run build:bucket
npx vite preview
```

Open `http://localhost:4173`.

---

## What stays dynamic?

Search, login, tutor profiles, enquiries, and dashboards all call the live API from the browser. Only the **UI shell** is static files in the bucket — this is the standard pattern for SPAs on GCS/S3/CloudFront.
