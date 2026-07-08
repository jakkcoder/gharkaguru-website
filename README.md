# GharKaGuru (Frontend)

Frontend for **GharKaGuru** — home tuition matching.

## Production: static site on gharkaguru.com (GCS bucket)

The website builds to plain static files (HTML/CSS/JS). No server needed.

```bash
cd tutornest_frontend
npm ci
npm run build:bucket
gcloud storage rsync -r dist/ gs://YOUR-BUCKET/
```

Full guide: **[DEPLOY_BUCKET.md](./DEPLOY_BUCKET.md)**

Production API default: `https://api.gharkaguru.com/v1` (set in `.env.production`).

---

## Local dev

### With Docker (no local Node required)

```bash
docker compose --profile dev up web-dev
```

Open `http://localhost:5173`.

### With Node

```bash
npm install
npm run dev
```

Uses MSW mocks by default. To hit a local gateway:

```bash
echo 'VITE_API_BASE_URL=http://localhost:8080/v1' > .env.local
echo 'VITE_DISABLE_MSW=true' >> .env.local
npm run dev
```

---

## Notes

- **Auth**: phone login returns `{ token, role }` directly.
- **Routing**: React Router (client-side); bucket hosting uses `404.html` fallback.
- **Styling**: Tailwind CSS.

## Optional: Docker / VM deploy

See `README_deploy.md` if you prefer Nginx-in-Docker instead of a bucket.
