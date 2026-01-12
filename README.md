# FEGO '84 Election Voting Platform (Release 1.0)

This repository is the **commencement codebase** based on the attached Sprint Plan.
It implements a working foundation for:
- Public landing page + About Us
- Voter login (registered voters only)
- Voter member area with **one vote per post** (no vote edits)
- Election open/close enforcement (server-side)
- Candidate restriction (candidate cannot vote in their own post)
- 30-minute inactivity logout
- Django Admin for managing elections, posts, candidates, voters, and content blocks
- **Sprint D implemented:** voter register import from `.ods` + admin permission controls
- **Sprint E implemented:** aggregate-only results screens + CSV exports + participation report + tie-break workflow + archive snapshots
- **Sprint F implemented:** security hardening defaults, UAT scripts, production runbook, and production docker compose

## Tech stack
- Python 3.12
- Django (server-rendered UI)
- PostgreSQL
- Docker / Docker Compose

> Note: The Sprint Plan also allows a React/Next.js frontend. For the fastest first delivery, this starter uses **Django templates**. You can add a separate Next.js frontend later without changing the core data model.

## Quick start (Docker)
1. Copy env example:
   ```bash
   cp .env.example .env
   ```
2. Start:
   ```bash
   docker compose up --build
   ```
3. Create an admin user:
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```
4. Open:
   - App: http://localhost:8000
   - Admin: http://localhost:8000/admin

## Sprint E: Results, participation, exports, tie-break
In Django Admin:
- Open an **Election** and use the links:
  - Results (aggregate)
  - Participation
  - Results CSV
  - Participation CSV
- If a post is tied, you can create a tie-break post using the **Create Tie-break Post** button.
  Tie-breaks are new posts (rounds), so the "vote once per post" rule remains true.

## Sprint F: Production deployment
This repo includes:
- `docker-compose.prod.yml` (Gunicorn + Nginx + Postgres)
- `.env.production.example`
- `deploy/nginx/nginx.conf`
- `scripts/entrypoint.sh`

Run (example):
```bash
cp .env.production.example .env
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

See `docs/RUNBOOK.md` and `docs/UAT_SCRIPTS.md`.

## Data entry (Admin)
1. Create an **Election** with status = OPEN, and start/end times.
2. Create **Posts** for that election (President, Vice President, etc.)
3. Create **Candidates** for each post.
4. Create **Users** for voters (role=VOTER) and set passwords.

### Sprint D: Import voter register from `.ods`
1. In Django Admin, go to **Accounts → Users**.
2. Click **Import Voter Register (.ods)**.
3. Upload a file with a header row. Required column: `username`.
   Optional columns: `first_name`, `last_name`, `email`, `membership_no`, `active`, `password`, `is_candidate`.
4. The import will show a per-row report and also write an audit event `VOTER_IMPORT`.

## Key rule
- A voter can vote **once** per post. Votes cannot be changed.

### Sprint D: Admin permission controls
- Super Admins have full access.
- Admin Members can be granted fine-grained flags via **Accounts → Admin Permissions**:
  - manage elections/posts/candidates/voters/content, view audit.

> Note: The Votes table in Django Admin is intentionally **Super Admin only** because it reveals individual selections.

## Docs
- `docs/UAT_SCRIPTS.md`
- `docs/RUNBOOK.md`
- `docs/DEPLOYMENT.md`
