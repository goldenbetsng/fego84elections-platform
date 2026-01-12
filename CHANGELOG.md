# Changelog

## 1.0.0 — Release 1.0
- Public landing page + About Us
- Voter login (registered voters only)
- Voter member area with **one vote per post** (no vote edits)
- Election open/close enforcement (server-side)
- Candidate restriction (candidate cannot vote in their own post)
- 30-minute inactivity logout
- Voter register import from `.ods` with per-row report + audit event
- Admin permission controls (Super Admin + Admin Members with flags)
- Aggregate-only results + participation report
- CSV exports for results and participation
- Tie-break workflow (creates a new post/round with only tied candidates)
- Archive snapshots (aggregate results + participation)
- Production deployment packaging (Gunicorn + Nginx + Postgres)
- Security hardening defaults (HSTS/secure cookies/CSP)
- UAT scripts and operations runbook
