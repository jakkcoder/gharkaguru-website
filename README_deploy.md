# GharKaGuru — Deployment Guide (`README_deploy.md`)

This guide explains how to deploy the GharKaGuru frontend on **any server** (VPS / bare metal / cloud VM) and how to connect it to your **DNS + main website URL**.

GharKaGuru is a **static SPA** built with Vite and served by **Nginx** inside a Docker container.

---

## 1) Prerequisites

### Server requirements
- **Linux server** (Ubuntu 22.04+ recommended)
- **Public IP** address (IPv4 recommended; IPv6 optional)
- Ports open:
  - **80/tcp** (HTTP)
  - **443/tcp** (HTTPS)

### Software on the server
- Docker Engine + Docker Compose plugin installed

On Ubuntu:

```bash
sudo apt update -y
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update -y
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

---

## 2) Get the code onto the server

Option A — Git clone:

```bash
git clone <YOUR_REPO_URL> tutornest-deploy
cd tutornest-deploy/tutornest
```

Option B — Copy files:
- Copy the whole project folder to the server and `cd` into `tutornest/`.

---

## 3) Deploy (simple, production-like)

GharKaGuru includes a production image in `tutornest/Dockerfile` (build stage + Nginx runtime).

### Build & run with docker compose

```bash
cd tutornest
docker compose up --build -d web
```

This starts the container and exposes it on:
- `http://SERVER_IP:5174` (default)

If you want a different port, set:

```bash
FRONTEND_WEB_PORT=8081 docker compose up --build -d web
```

### Verify it is serving

```bash
curl -I http://127.0.0.1:5174
```

You should see `HTTP/1.1 200 OK`.

---

## 4) Put it on your real domain (DNS + reverse proxy)

### Recommended: use a subdomain (fastest + cleanest)

Example: `tutornest.yourdomain.com`

1) **DNS**: create an `A` record:
   - **Type**: A
   - **Name/Host**: `tutornest` (or `app`)
   - **Value**: `YOUR_SERVER_PUBLIC_IPV4`
   - **TTL**: 300 (or default)

2) **Reverse proxy** (Nginx on the server) from `:80/:443` → GharKaGuru container `:5174` (default)

Install Nginx:

```bash
sudo apt update -y
sudo apt install -y nginx
```

Create Nginx site:

```bash
sudo nano /etc/nginx/sites-available/tutornest.conf
```

Paste (replace domain):

```nginx
server {
  listen 80;
  server_name tutornest.yourdomain.com;

  location / {
    proxy_pass http://127.0.0.1:5174;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/tutornest.conf /etc/nginx/sites-enabled/tutornest.conf
sudo nginx -t
sudo systemctl reload nginx
```

Now `http://gharkaguru.yourdomain.com` should serve the app.

---

## 5) Add HTTPS (Let’s Encrypt)

Install Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Issue certificate:

```bash
sudo certbot --nginx -d tutornest.yourdomain.com
```

Certbot will auto-configure HTTPS and renewals.

---

## 6) Using your *main* website URL (root domain)

You have two common integration patterns:

### Option A (recommended): **Subdomain**
- Main site stays at `https://yourdomain.com`
- GharKaGuru at `https://gharkaguru.yourdomain.com`

This is the least risky approach for SPAs and avoids path-routing edge cases.

### Option B: Serve GharKaGuru under a path, e.g. `https://yourdomain.com/gharkaguru`

This requires **additional app changes** because Vite + React Router need a base path.

If you want path-based deployment, do one of these:
- **Best**: keep GharKaGuru as a subdomain.
- **If you must use a path**:
  - set Vite `base: '/tutornest/'`
  - set React Router basename `/tutornest`
  - adjust Nginx to `try_files` for that subpath

If you tell me the exact desired path (example: `/tutor` or `/tutornest`), I can implement the required code changes safely.

---

## 7) Pointing DNS (quick reference)

### Subdomain → server IP (typical)
- `A  tutornest   YOUR_IPV4`
- (optional) `AAAA tutornest YOUR_IPV6`

### Root domain → server IP
- `A  @  YOUR_IPV4`
- (optional) `AAAA @ YOUR_IPV6`

### If your DNS provider uses “CNAME flattening”
- You can set root `@` to a CNAME-like value (provider-specific). Otherwise prefer A record.

**Propagation**: usually minutes, sometimes up to 24 hours depending on TTL and resolver caches.

---

## 8) Ops: update, restart, logs

From `tutornest/` on the server:

### Update to latest code and redeploy
```bash
git pull
docker compose up --build -d web
```

### Logs
```bash
docker compose logs -f web
```

### Stop
```bash
docker compose down
```

---

## 9) Troubleshooting

### “Site loads but routes 404 on refresh”
That means the reverse proxy isn’t SPA-aware. Ensure:
- If you proxy to GharKaGuru container (recommended), Nginx in the container already has `try_files ... /index.html`.
- If you’re serving files directly, you must add SPA fallback (`try_files $uri /index.html`).

### DNS points correctly but domain doesn’t open
- Confirm security group / firewall allows ports **80/443**
- Confirm Nginx is running: `sudo systemctl status nginx`
- Confirm GharKaGuru container is running: `docker ps`

---

## 10) What to tell me so I can finalize your exact setup

Reply with:
- Your domain: `yourdomain.com`
- Desired URL for GharKaGuru:
  - subdomain (`gharkaguru.yourdomain.com`) **or**
  - path (`yourdomain.com/gharkaguru`)
- Your server OS (Ubuntu/Debian/CentOS) and whether you already have Nginx/Caddy running for your main site

Then I can tailor the exact Nginx/Caddy config for your environment.

