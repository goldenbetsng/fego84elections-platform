# UAT Scripts — FEGO '84 Election Voting Platform

These scripts validate the **Test/Staging** build before promoting it to **Production Release 1.0**.

## Roles
- **Super Admin**
- **Admin Member** (permission flags)
- **Voter**

## UAT-01 — Public pages and login
1. Visit **Home** and **About Us**; confirm pages load.
2. Confirm **Login** link is visible when logged out.
3. Attempt login with a non-existent username; expect safe error.

## UAT-02 — ODS voter import
1. In Admin, go to **Accounts → Users** and click **Import Voter Register (.ods)**.
2. Upload an ODS with a header row and at least columns: `username`, `first_name`, `last_name`.
3. Verify import report shows created/updated rows and any errors.
4. Verify an audit event exists with type `VOTER_IMPORT`.

## UAT-03 — Configure election
1. In Admin, create an **Election**:
   - status = `OPEN`
   - start_at = 10 minutes in the past
   - end_at = 60 minutes in the future
2. Create 3–6 **Posts** (President, Vice President, Secretary, etc.).
3. Create at least 2 **Candidates** per post.

## UAT-04 — Voting (one vote only)
1. Log in as a voter and go to **Member Area**.
2. Open a post and cast a vote.
3. Return to the same post and attempt to vote again; expect message: voting already done and cannot be changed.
4. Verify the dashboard shows the post as voted.

## UAT-05 — Candidate restriction
1. Mark a voter as a candidate for a specific post (Candidate record linked to that user).
2. Log in as that user and attempt to vote in the same post; expect block message.
3. Confirm the same user can vote in other posts where they are not a candidate.

## UAT-06 — Election close enforcement
1. Set election status to `CLOSED`.
2. Log in as a voter and attempt to access any post vote page; expect "voting is not open".

## UAT-07 — Results, participation, exports
1. In Admin, open the Election and click **Results (aggregate)**:
   - confirm counts per candidate are shown
   - confirm there is no per-voter ballot information
2. Click **Results CSV** and confirm file downloads.
3. Open **Participation** and confirm it shows YES/NO + cast timestamp only.
4. Click **Participation CSV** and confirm file downloads.

## UAT-08 — Tie-break workflow
1. Create a tied result (two candidates with equal votes) for a post.
2. In **Results (aggregate)**, click **Create Tie-break Post** for that post.
3. Verify a new post exists named "(Tie-break Round 1)" and contains only tied candidates.
4. Set the tie-break post status to `OPEN` (Post admin).
5. Confirm voters can vote once in the tie-break post.

## UAT-09 — Archive snapshot
1. In Admin, open the Election and click **Create Archive Snapshot**.
2. Verify a read-only archive record exists.

## UAT-10 — Permission checks for Admin Member
1. Create an ADMIN user (non-superadmin).
2. Grant only `can_view_results` and confirm:
   - can access results and participation pages
   - cannot create tie-break posts
3. Grant `can_manage_posts` and `can_manage_candidates` and confirm tie-break creation is allowed.

## Exit criteria
- All UAT scripts pass without workarounds.
- Exports work and do not expose per-voter ballot selections.
- One-vote rule, election window enforcement, and candidate restriction are all server-enforced.
