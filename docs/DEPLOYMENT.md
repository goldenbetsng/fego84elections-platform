# Deployment Guide — FEGO '84 Election Voting Platform (Release 1.0)

This guide covers:
- Deploying a **Test/Staging** environment for UAT
- Deploying **Production Release 1.0**
- Required environment variables
- Domain/HTTPS and CSRF settings

## 1) Quick choice

- **Staging/Test** (UAT & rehearsal): use `docker-compose.yml`
- **Production** (Release 1.0): use `docker-compose.prod.yml`

## 2) Environment variables

The app reads config from environment variables.

### Required (production)
- `SECRET_KEY` — long random value
- `ENVIRONMENT=production`
- `DEBUG=0`
- `ALLOWED_HOSTS` — comma-separated hostnames (e.g. `vote.fego84.org`)
- `POSTGRES_HOST=db`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

### Recommended (production)
- `SECURE_PROXY_SSL_HEADER=1` if TLS terminates at a proxy/load-balancer
- `SECURE_SSL_REDIRECT=1`
- `SECURE_HSTS_SECONDS=31536000`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS=1`
- `SECURE_HSTS_PRELOAD=1`
- `CSRF_TRUSTED_ORIGINS` — comma-separated origins with scheme, e.g.
  - `https://vote.fego84.org`

Use `.env.production.example` as your starting point.

## 3) Staging/Test deployment

1. Copy env file:
   ```bash
   cp .env.example .env
   ```
2. Start:
   ```bash
   docker compose up --build -d
   ```
3. Create admin:
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```
4. Open:
   - App: `http://<server>:8000`
   - Admin: `http://<server>:8000/admin`

## 4) Production deployment (Release 1.0)

### 4.1) First-time setup

1. Copy prod env template:
   ```bash
   cp .env.production.example .env
   ```
2. Edit `.env`:
   - set `SECRET_KEY`
   - set `ALLOWED_HOSTS`
   - set `CSRF_TRUSTED_ORIGINS`
   - set Postgres credentials
3. Start production stack:
   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```
4. Create admin:
   ```bash
   docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
   ```

### 4.2) Static files

Production compose shares a Docker volume named `staticfiles` between `web` and `nginx`.
`/app/scripts/entrypoint.sh` runs `collectstatic` automatically on container startup.

## 5) HTTPS / TLS

`docker-compose.prod.yml` publishes port **80**. You have two common options:

### Option A (recommended): TLS terminated by an external reverse proxy
Use a managed proxy (e.g., Cloudflare) or a host reverse proxy (Caddy/Traefik/Nginx) that terminates TLS and forwards to port 80.

Set:
- `SECURE_PROXY_SSL_HEADER=1`
- `CSRF_TRUSTED_ORIGINS=https://your-domain`
- `ALLOWED_HOSTS=your-domain`

### Option B: add TLS to the container stack
You can extend nginx with certbot or swap nginx for Caddy. This is optional and not included by default.

## 6) Backups

See `docs/RUNBOOK.md` for Postgres backup/restore commands.

## 7) Rollback

If a deploy goes wrong:
1. Revert to the previous git tag/zip.
2. Redeploy containers.
3. Restore DB from your most recent backup if necessary.

## 8) Notes on CSRF and domains

If you change domain names between staging and production, you must update both:
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS` (must include scheme: `https://...`)
