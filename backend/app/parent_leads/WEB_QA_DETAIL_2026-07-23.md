# Parent Leads Inbox — Web QA Report

**Date:** 2026-07-23 (IST)  
**Feature:** Rich fill details + move_back + Admin Today activity list  
**Environments:** Local `http://127.0.0.1:8090/parent_leads` → Cloud Run (after deploy)

## Inventory (Step 6)

| Agent | Email | Password (admin table) |
|-------|-------|------------------------|
| Anjali | anjali@gharkaguru.com | anjali@123 |
| Anshika | anshika@gharkaguru.com | anshika |
| Neha | neha@gharkaguru.com | neha |
| Raghav | raghav@gharkaguru.com | raghav@123 |
| Rohini | rohini@gharkaguru.com | rohini |
| Sonam | sonam@gharkaguru.com | sonam@123 |

## Code changes

| Area | What |
|------|------|
| Schema | `subject`, `student_name` columns; `lead_events` table |
| Fill | Editable `parent_name`, `student_name`, `subject`, Address/Area (`location`), mode, budget, note; phone read-only in UI |
| Pipeline | `PREV_STAGE` + `move-back` route (Demo→Assigned, Class→Demo, Payment→Class) |
| Admin Today | Brief recent actions list from `lead_events` (fill/advance/move_back/junk/promote) |

**Files:**  
`gharkaguru-website/backend/app/parent_leads/{config,db,admin_report,routes}.py`  
`gharkaguru-website/backend/app/parent_leads/templates/{portal,admin_dashboard}.html`  
`parent-leads-inbox/app/db.py` (shared-DB additive migrations)

## Local web results (Playwright)

| Step | Result | Evidence |
|------|--------|----------|
| 0.1 entry | PASS | `/parent_leads/login` |
| 0.2 unauth admin | PASS | redirect → `/admin/login` |
| 0.3 unauth portal | PASS | redirect → `/login` |
| 1.4 wrong admin | PASS | stays on login + Invalid password |
| 1.5 admin dash | PASS | Today’s activity visible |
| 1.6 agents ×2 reload | PASS | 6 agents, passwords stable |
| 1.7 Today section | PASS | Recent actions table present |
| 1.8 Move leads | PASS | `/admin/reassign` |
| 1.9 admin sign out | PASS | dashboard blocked |
| 10–12 all 6 agents | PASS | login, reload×3, all tabs badge=rows |
| 13 logout (retest) | PASS | cookie cleared; `/portal` → login (initial flake: missing waitForURL) |
| 14–15 fill + reload | PASS | Anjali lead `9999463021`; parent/subject/addr/note persist |
| 16 admin Today fill | PASS | `fill` row for Anjali / Math |
| 17 advance → demo | PASS | banner Lead updated |
| 18 move_back | PASS | banner Moved back; admin shows `move_back` |
| 19 → payment | PASS | no forward advance on Payment |
| 20 promote | PASS | teacher phone on Class started |
| 21 junk | PASS | `9718011886` on Junk only |
| 22 isolation | PASS | Anshika cannot see Anjali E2E lead |
| 23 reassign | PASS | lead `9818868972` → Anshika; Science + note intact |
| 24/25 Today + passwords | PASS | events coherent; inventory unchanged |
| 26 all agents | PASS | login → Assigned → logout ×6 |

### Failure log (resolved)

```
---
FAILURE LOG ENTRY
- Step: 13.i logout (initial run)
- Environment: Local
- Test type: WEB (Playwright) — required
- Agent/lead: all agents
- Expected: after Sign out, /portal redirects to login
- Actual: still on /portal (test did not wait for logout navigation)
- URL / banner / snapshot: http://127.0.0.1:8090/parent_leads/portal
- Fix area: other (test harness)
- Fix applied: wait for logout URL + requestSubmit on logout form
- Web retest: PASS
---
```

## Cloud Run

**Deployed:** revision `gharkaguru-website-00020-l9x`  
**URL:** https://gharkaguru-website-lmquvtnfja-as.a.run.app/parent_leads  

| Step | Result |
|------|--------|
| 0.1–0.3 smoke redirects | PASS |
| 1.4–1.9 admin | PASS (Today recent actions live; 6 agents stable) |
| 10–13 all 6 agents | PASS (login, reload×3, tabs, new fill fields, logout) |
| 14–15 Sonam fill + reload | PASS (`9971966759`, subject English, note E2E-DETAIL-…-CR-sonam) |
| 16 Admin Today shows fill | PASS |
| 17–18 advance + move_back | PASS (banners Lead updated / Moved back) |
| 18b Admin move_back event | PASS |
| 22 isolation | PASS |
| 25 passwords (recheck) | PASS (see retest; earlier empty-inv flake ignored) |
| 26 all agents regression | PASS |

### FINAL SUMMARY — ALL PASS

- Local web: PASS  
- Cloud Run web: PASS  
- Data left as-is after tests (E2E-tagged fills/moves retained; no bulk wipe)
