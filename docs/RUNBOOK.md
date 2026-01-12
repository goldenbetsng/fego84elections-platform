# Operations Runbook — FEGO '84 Election Voting Platform (Release 1.0)

## Scope
This runbook covers normal election operations:
- configure election, posts, candidates, and voters
- open and close voting
- run tie-break rounds
- export results and participation
- create archive snapshots
- perform basic backups/restore

## Roles
- **Super Admin**: full access (recommended: 1–2 people)
- **Admin Member**: limited access (permission flags)

## Before election day
### 1) Create or import voters
Option A (recommended): **ODS import**
1. Admin → **Accounts → Users** → **Import Voter Register (.ods)**
2. Upload `.ods` with header row and at least: `username,first_name,last_name,password,active`
3. Confirm import report looks correct

Option B: create voters manually (not recommended for large lists)
1. Admin → **Accounts → Users** → Add
2. Set role=VOTER, set password

### 2) Create election
1. Admin → **Elections → Elections** → Add
2. Set:
   - status = `DRAFT` while configuring
   - start_at / end_at times (Europe/London)
3. Save

### 3) Create posts and candidates
1. Admin → **Elections → Posts**
   - create the posts/categories (President, Vice President, etc.)
   - set display_order
2. Admin → **Elections → Candidates**
   - add candidates per post
   - mark inactive candidates if required
3. If a candidate is also a system user, link the candidate `user` field.
   - This enables the server rule: **candidate cannot vote in that post**.

### 4) Content blocks
Admin → **Content Blocks**
- banner text
- scrolling announcement
- intro copy
- About Us copy
- footer text

## Open voting
1. Confirm start_at and end_at are correct.
2. Set Election status to `OPEN`.
3. Verify voter flow:
   - voter can login
   - voter can vote once per post
   - voter cannot vote in a post they are a candidate for

## During voting
### Handling common issues
- **Voter cannot login**: confirm user exists, is_active=True, role=VOTER, and password set.
- **Voter sees "Voting is not open"**: check election status/window and that the post is_active=True.
- **Voter claims they voted wrong**: votes cannot be edited. See tie-break guidance if a rerun is needed.

### Monitoring
Admin should use **Participation** (YES/NO + timestamps) to track turnout without exposing ballot selections.

## Close voting
1. Set Election status to `CLOSED`.
2. Confirm vote pages show "Voting is not open".
3. Generate exports:
   - Results CSV
   - Participation CSV
4. Create an **Archive Snapshot**.

## Tie-break procedure
This system preserves the rule: **one vote per voter per post**.
Tie-breaks are implemented as a **new Post (round)**.

1. On Results (aggregate), if a post is tied, click **Create Tie-break Post**.
2. Confirm new post is created: "(Tie-break Round N)" containing only tied candidates.
3. Set tie-break post status to `OPEN`.
   - You may set start_at / end_at on the post.
4. Allow voting in the tie-break post.
5. Close the tie-break post:
   - set its status to `CLOSED`, or set end_at in the past.
6. Export results and create another Archive Snapshot.

## Backups
### Postgres backup (docker)
```bash
docker compose -f docker-compose.prod.yml exec db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

### Restore
```bash
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

## Incident response (minimal)
1. **Lock down admin access**: change admin passwords; disable accounts if necessary.
2. **Capture evidence**: export audit logs and keep backups.
3. **Rotate secrets**: change SECRET_KEY and DB password if compromise suspected.
4. **Notify stakeholders** and document actions.
