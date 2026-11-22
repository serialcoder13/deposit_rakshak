# Deposit Rakshak: IBM Bob Playbook

Ready-to-paste prompts for building Deposit Rakshak with IBM Bob, one task per prompt, in order.

---

## How to use

1. Open this repo in Bob. Keep `SPEC.md`, `ARCHITECTURE.md` and `SDLC.md` in the repo root, because every prompt points at them.
2. Put the **Project rules** below wherever Bob takes project or custom instructions. If you can't find that, paste them at the top of each new chat.
3. **One task per chat.** Ask Bob to show its plan first, then let it write the code.
4. **Review every diff** before accepting it, and run the "Done when" check.
5. Tasks within a lane run in order. Lanes run in parallel: Backend (B), AI (A), Frontend (F).

---

## Project rules (paste once)

```
You are building "Deposit Rakshak", a hackathon app. The source of truth is
SPEC.md (requirements, data model, API, agent, scoring) and ARCHITECTURE.md
(structure and decisions). Read the sections each task names before coding.

Stack: backend = Python 3.11+, FastAPI, SQLModel on SQLite, Uvicorn, PyJWT,
pytest. Frontend = React 18 + TypeScript + Vite + vite-plugin-pwa + React Query,
mobile first. Layout: backend/app/... and frontend/src/... as in SPEC §13.

Rules:
- Follow the field names, routes, statuses and enums in SPEC exactly.
- Money is computed only in backend/app/scoring.py. The LLM never computes costs.
- Only backend/app/llm.py talks to the LLM provider. Config comes from env (.env, never committed).
- Keep it simple: no extra frameworks, no queues, no websockets.
- Small files, clear names, type hints. No placeholder TODOs in delivered code.
- After coding, tell me exactly how to run and verify the task.
```

---

## Phase 0 (everyone, 10 min)

**T1 Tunnel + camera check (QA):** run any page on port 8000, expose it with `cloudflared tunnel --url http://localhost:8000`, and open it on both phones. Confirm HTTPS works.
**T2 Golden photos (QA):** shoot 5 before/after pairs in the venue (stain, crack, wear, unchanged, mismatched angle) and save them to `backend/tests/golden/`.
**T3 Rate card (Product):** fill the checked rates and sources into SPEC §10.
**A0 Provider check (AI):** confirm one image call works with the chosen provider and key.

---

## Backend lane

### B1 Scaffold, models, seed
```
Read SPEC §5, §13, §14 and ARCHITECTURE §3.
Create backend/ with app/main.py, config.py (pydantic-settings, reads .env),
db.py (SQLite at data/app.db), models.py (every table in SPEC §5 with the exact
fields and enums), and seed.py (python -m app.seed wipes and reseeds the demo
data in SPEC §14, including the rate card rows and the maintenance report).
Add requirements.txt and .env.example. GET /api/health returns {"ok": true}.
```
**Done when:** `python -m app.seed` runs twice without errors and `/api/health` returns ok.

### B2 Auth
```
Read SPEC §7 (Auth) and ARCHITECTURE §8.
Implement POST /api/auth/otp/request, POST /api/auth/otp/verify (OTP from
DEMO_OTP, default 123456; returns a JWT and the user) and GET /api/me (the user
plus tenancies with role owner or tenant). Add a get_current_user dependency
and a helper require_tenancy_role(tenancy_id, roles).
```
**Done when:** you can log in as the seeded owner and tenant and `/api/me` shows each one's role.

### B3 Properties and tenancies (read side)
```
Read SPEC §3 and §7 (Property, Tenancy).
Implement GET /api/properties, GET /api/properties/{id} (rooms, items, slots
in order), GET /api/tenancies/{id} (inspections with status, maintenance
reports, latest run id), POST /api/tenancies/{id}/issues. Enforce the
permissions in SPEC §3.
```
**Done when:** the tenant can read their tenancy, and a user outside the tenancy gets 403.

### B4 Integrity and scoring, tests first
```
Read SPEC §6 and §10.
First write pytest tests, then implement:
- app/integrity.py: sha256_bytes(data), lock_hash(photo_hashes, note_texts,
  owner_signed_at, tenant_signed_at) that is order-independent.
- app/scoring.py: pure functions for penalty(severity), depreciation(age_at_move_in,
  tenancy_months, useful_life) with floor 0.2, finding_cost(rate, quantity,
  depreciation), item_score, property_score (weighted by replacement_cost),
  and totals(findings, deposit) returning damage_pct, proposed, agreed,
  disputed and refund, using the status rules and deposit cap in SPEC §10.
```
**Done when:** `pytest` passes, including the depreciation floor, the deposit cap and the totals for each status.

### B5 Inspections: create, upload, notes, ghost
```
Read SPEC §6, §7 (Inspections) and ARCHITECTURE §4.1.
Implement POST /api/tenancies/{id}/inspections (a move_out needs a locked
move_in), GET /api/inspections/{id} (slots with photo, notes, captured flag),
POST /api/inspections/{id}/photos (multipart; re-hash the bytes, return 422 on
a mismatch; store data/photos/<sha256>.jpg; one current photo per slot),
POST /api/inspections/{id}/notes, GET /api/inspections/{id}/ghost/{slot_id}
(the move-in photo for that slot). Serve photos at /api/photos/{sha256}.
```
**Done when:** an upload with a correct hash is stored, and a wrong hash gets 422.

### B6 Sign and lock
```
Read SPEC §6 and ARCHITECTURE §5.
Implement POST /api/inspections/{id}/sign. Every slot needs a photo first.
Record the signer's time and move to awaiting_signatures. When both have
signed, compute lock_hash with integrity.py and set status locked. Any write
to a locked inspection returns 409.
```
**Done when:** after both sign, the status is `locked` with a hash, and another upload returns 409.

### B7 Report, findings, static PWA
```
Read SPEC §7 (Reports), §10 and ARCHITECTURE §2 (one origin).
Implement GET /api/tenancies/{id}/report (findings with before and after photo
URLs and cited evidence, item and property scores, totals from scoring.py,
summaries from the latest run) and PATCH /api/findings/{id} (tenant: status
accepted or disputed plus tenant_note; owner: owner_override_cost plus
owner_note). Recompute totals on each read. Serve backend/app/static as the
SPA at / with a fallback to index.html for client routes.
```
**Done when:** a dispute changes the agreed and disputed totals in `/report`.

---

## AI lane

### A1 LLM adapter + vision contract
```
Read SPEC §8 and §9 and ARCHITECTURE §9 (ADR 7).
Create app/llm.py with two async functions:
- vision_compare(before_bytes, after_bytes, context) -> dict, validated against
  the JSON contract in SPEC §9 (pydantic model); retry once on invalid JSON.
- chat_with_tools(messages, tools, system) -> the provider's response, normalised
  to {text, tool_calls:[{id,name,arguments}], stop}.
Provider comes from LLM_PROVIDER and related env vars. Put the prompts in
app/agent/prompts.py. Add scripts/golden.py, which runs vision_compare on every
pair in tests/golden/ and prints the JSON.
```
**Done when:** `scripts/golden.py` prints valid JSON for all 5 golden pairs, and the mismatched pair returns `pair_usable: false`.

### A2 Agent tools
```
Read SPEC §8 (Tools, Decision rules) and §10.
Create app/agent/tools.py implementing list_pairs, inspect_pair, get_item
(age at move-out = age at move-in + tenancy months / 12), get_slot_notes,
get_maintenance_reports, estimate_cost (uses scoring.py and the RateCard
table; returns the breakdown), flag_retake, record_finding (applies the
confidence < 0.6 -> needs_review rule) and finish. Export JSON-schema
definitions for each tool, plus one dispatcher execute(name, args, run_ctx).
```
**Done when:** each tool can be called directly from a test script against the seed data.

### A3 Agent loop + run API + SSE
```
Read SPEC §8 (Loop, Trace) and ARCHITECTURE §4.2 and §5.
Create app/agent/loop.py: the tool-use loop using llm.chat_with_tools, at most
40 iterations and 3 minutes, running parallel tool calls with at most 4 at once,
writing an AgentStep (thought, tool_call, tool_result, error) with a short
human-readable label for each event, then calling scoring for totals. Add
routes: POST /api/tenancies/{id}/compare (starts the run as a BackgroundTask
and returns run_id) and GET /api/runs/{id}/events (SSE: stream steps by seq,
then a final "done" or "failed" event).
```
**Done when:** a run on the staged tenancy streams steps with `curl -N` and produces the 5 expected outcomes in SPEC §1.

### A4 Demo mode
```
Read SPEC §14 (fallback).
Add a recorder that saves a finished run (steps and findings) to
data/demo_run.json. When DEMO_MODE=1, POST /compare replays that file
through the same SSE stream with realistic delays and writes the same
findings, without calling the LLM.
```
**Done when:** with Wi-Fi off and `DEMO_MODE=1`, the full report flow still works.

---

## Frontend lane

### F1 PWA scaffold, API client, login
```
Read SPEC §11 and ARCHITECTURE §2 and §6.
Create frontend/ with Vite + React + TypeScript, vite-plugin-pwa (name
"Deposit Rakshak", theme colour, icons, standalone), React Router and React Query.
The Vite dev server proxies /api to http://localhost:8000. Create src/api.ts
with a typed fetch wrapper and a stored JWT. Build the Login screen (phone,
OTP, hint "use 123456"). Mobile-first CSS, large tap targets.
Add an npm script that builds and copies dist/ to ../backend/app/static.
```
**Done when:** you can log in on a phone through the tunnel and add the app to the home screen.

### F2 Home + Tenancy
```
Read SPEC §11 screens 2 and 3.
Home: the owner sees properties and tenancies; the tenant sees their tenancy
with a status timeline (Move-in signed 🔒, Check-ins, Move-out, Settled).
Tenancy: deposit, rent, dates, inspections with status, buttons to start or
continue move-in or move-out, and Compare when the move-out is complete.
```
**Done when:** both users see the right screens and buttons for their role.

### F3 Camera capture component
```
Read SPEC §6 and §11 screen 4.
Build components/Camera.tsx: a full-screen rear camera using getUserMedia
(environment facing), shutter, and retake. There is no file input or gallery
picker. On capture: draw to canvas, resize to 1280px on the long side, export
JPEG at quality 0.8, compute SHA-256 of those exact bytes with
crypto.subtle, then upload to POST /api/inspections/{id}/photos with slot_id,
sha256, captured_at and device_meta (userAgent, screen size).
```
**Done when:** a photo shot on a phone appears on the backend with a matching hash.

### F4 Guided capture flow + ghost overlay
```
Read SPEC §11 screen 4 and ARCHITECTURE §4.1.
Capture page: walk through the slots in order showing label, guidance and
progress ("3 of 4"), with a note button per slot. For move_out and checkin
inspections, show the ghost image from GET /api/inspections/{id}/ghost/{slot_id}
over the live camera at 40% opacity with a slider.
```
**Done when:** the move-in photo lines up visibly over the live camera during move-out.

### F5 Review and sign
```
Read SPEC §11 screen 5 and §6.
A grid of slot photos with their notes. Either party can add a note per slot.
A Sign button (disabled until every slot has a photo). Once locked, show a 🔒
badge, the first 8 characters of lock_hash and both signature times.
```
**Done when:** after both phones sign, both show the lock badge with the same hash.

### F6 Agent run screen
```
Read SPEC §8 (Trace) and §11 screen 6.
Start a run with POST /compare, then open an EventSource on
/api/runs/{id}/events. Show the steps as a live list with icons by kind
(🔍 👁 📝 📂 ✅ 💰 🧾), per-slot progress chips, and a "Thinking…" state.
On "done", navigate to the Report. If SSE fails, fall back to polling.
```
**Done when:** the trace streams on the phone through the tunnel.

### F7 Report + finding cards + dispute
```
Read SPEC §10 and §11 screen 7.
A condition score dial, damage %, and a bar for deposit, proposed, agreed,
disputed and refund. Finding cards show before and after photos side by side
(tap to swipe), a classification chip (Damage, Wear, Pre-existing, Owner's
responsibility, Needs review), severity, confidence, cited notes and reports,
and the cost breakdown (rate × quantity × depreciation). The tenant gets Accept
and Dispute (with a note); the owner gets an override field with a reason.
Poll /report every 3 seconds so both phones stay in sync.
```
**Done when:** a dispute on the tenant phone changes the totals on the owner phone within 5 seconds.

### F8 Settlement
```
Read SPEC §11 screen 8.
Final totals, refund due, and the summary in English and Kannada with a
language toggle. A Share button opens https://wa.me/?text=<encoded summary>.
```
**Done when:** WhatsApp opens on the phone with the Kannada text intact.

---

## Integration points (agree on these early)

| Contract | Owner | Used by |
|---|---|---|
| `/api/inspections/{id}` response shape | B5 | F3, F4, F5 |
| `/api/tenancies/{id}/report` response shape | B7 | F7, F8 |
| SSE event shape `{seq, kind, label, tool_name, payload}` | A3 | F6 |
| Finding classification and status enums | SPEC §5 | Everyone |

Ask Bob to put the response models in `backend/app/schemas.py` first (B5 and B7), and share that file with the frontend lane, so `api.ts` types match.
