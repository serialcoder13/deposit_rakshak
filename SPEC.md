# Deposit Rakshak: Build Spec

**Tracks:** Vision + Agentic
**Stack:** FastAPI backend, React + Vite frontend shipped as a mobile PWA
**One-liner:** A shared, tamper-evident record of a flat's condition across a tenancy. At move-out an AI agent compares it with the move-in record, separates damage from normal wear and tear, checks the tenancy history, and proposes a deduction that both sides can check line by line.

This spec builds on the Property Damage Tracker high-level design. Section 12 lists what changed from that design and why.

**Companion docs:** [ARCHITECTURE.md](ARCHITECTURE.md) (system design and decisions), [SDLC.md](SDLC.md) (sprints, stories, tests, release) and [BOB_PLAYBOOK.md](BOB_PLAYBOOK.md) (the build as ready-to-paste IBM Bob prompts).

---

## 1. What we demo (the 90-second story)

1. **Move-in.** The owner shoots 4 fixed angles of a real room. The tenant reviews them on their own phone, adds a note ("chip on table corner already here") and signs. The record locks and shows its hash.
2. **During the tenancy.** A check-in report is already seeded: the tenant reported "damp stain near window, seepage from outside wall" two months ago.
3. **Damage happens.** We add a coffee stain on the table, a fake crack (tape) on wall A and a brown stain (sticker) near the window. A faded cushion stays as it is.
4. **Move-out.** The owner shoots the same 4 angles with the move-in photo shown as a ghost overlay.
5. **The agent runs live.** The trace streams on screen: it pairs the photos, inspects each pair, looks up item ages, checks the tenant's reports, prices the repairs and writes the summary.
6. **The result:**
   - Coffee stain: **damage**, charged after depreciation.
   - Crack: **damage**, charged.
   - Window stain: a new change, but it **matches the tenant's seepage report**, so it's the owner's responsibility and costs the tenant ₹0. *(This is the agentic moment.)*
   - Table chip: **pre-existing**, already in the tenant's move-in note.
   - Cushion: **normal wear**, no charge.
7. **Dispute.** The tenant disputes the crack. The deduction updates live on the owner's phone, and the settlement message is ready in English and Kannada.

Two phones on stage (owner and tenant) make it feel real.

---

## 2. Scope

### Must demo (MVP)
- Phone + OTP login (demo OTP is fixed), with a role per tenancy
- Seeded property with rooms, items and capture slots
- Guided in-app camera capture with fixed slots
- Tenant review, notes and sign-off on move-in, which locks the record with hashes
- Move-out capture with a ghost overlay of the move-in photo
- An agent run with a live trace that produces findings
- A deterministic score, cost estimate and proposed deduction
- Tenant accepts or disputes each finding, with live totals
- A settlement summary in English and Kannada, shared through a WhatsApp link

### Stretch (only if MVP is done)
- Property setup UI (the MVP uses seed data)
- Agent re-assesses a disputed finding using the tenant's note
- Damage region highlighted on the photo (from a model bounding box)
- PDF export with the hash audit trail
- Tenant check-in flow in the UI (the MVP seeds one report)
- Mediator view

### Out of scope
Payments, real SMS, legal advice, video walkthroughs, OpenCV alignment.

---

## 3. Personas and permissions

| Action | Owner | Tenant |
|---|---|---|
| Create property, rooms, items, slots | ✅ | ❌ |
| Create tenancy and invite tenant | ✅ | ❌ |
| Capture move-in and move-out photos | ✅ | ✅ (may add extra photos) |
| Add notes on a slot | ✅ | ✅ |
| Sign an inspection | ✅ | ✅ |
| File maintenance and check-in reports | ❌ | ✅ |
| Start the AI comparison | ✅ | ✅ |
| Accept or dispute a finding | ❌ | ✅ |
| Override cost on a finding (with a reason) | ✅ | ❌ |
| See everything on the tenancy | ✅ | ✅ (the tenant sees all that the owner sees) |

---

## 4. Architecture

```
 Owner phone (PWA)      Tenant phone (PWA)
        \                    /
         \  HTTPS + JWT     /
          v                v
     +---------------------------+
     |   FastAPI  (/api/...)     |
     |  routers: auth, property, |
     |  tenancy, inspection,     |
     |  findings, runs (SSE)     |
     +-----+---------------+-----+
           |               |
     SQLite (SQLModel)   ./data/photos/<sha256>.jpg
           |
     Agent worker (FastAPI BackgroundTasks, in-process)
           |
     Vision LLM API (provider set in config)
```

- **Thin API, async agent.** `POST /compare` returns a `run_id` immediately. The agent runs in a background task and writes `AgentStep` rows. The UI follows them over Server-Sent Events (SSE).
- **No queue or broker** for the hackathon. FastAPI `BackgroundTasks` is enough. A real deployment would move to Celery or RQ with Postgres and S3.
- **One LLM adapter module** (`llm.py`) holds the provider call, so the team can switch providers (watsonx, Claude or another) in one place.
- **HTTPS is required for the camera on phones.** Hosting is the laptop only, exposed by ngrok's free static domain (ARCHITECTURE §6). Test it in the first 15 minutes.

---

## 5. Data model

IDs are UUID strings and times are UTC ISO 8601. ✱ marks fields added to the original design.

| Entity | Fields |
|---|---|
| **User** | id, phone, name |
| **Property** | id, owner_id, address, city |
| **Room** | id, property_id, name, order |
| **Item** | id, room_id, type (`wall`, `floor`, `table`, `fan`, `geyser`, `wardrobe`, `cushion`...), material, age_years_at_move_in, useful_life_years ✱, replacement_cost |
| **CaptureSlot** ✱ | id, room_id, item_id (optional), label ("Wall A, facing window"), order, guidance ("Stand at door, phone landscape") |
| **Tenancy** | id, property_id, owner_id, tenant_id, start_date, end_date, deposit, monthly_rent ✱, invite_code ✱ |
| **Inspection** | id, tenancy_id, type (`move_in`, `checkin`, `move_out`), status (`draft`, `awaiting_signatures`, `locked`), signed_by_owner_at, signed_by_tenant_at, lock_hash ✱ |
| **Photo** | id, inspection_id, slot_id, taken_by ✱, url, sha256, captured_at, device_meta (JSON) |
| **SlotNote** ✱ | id, inspection_id, slot_id, author_id, text, created_at |
| **MaintenanceReport** ✱ | id, tenancy_id, item_id or slot_id, description, photo_id (optional), reported_at, category (`seepage`, `plumbing`, `electrical`, `structural`, `other`) |
| **RateCard** ✱ | id, change_type, item_type, severity (1 to 3), unit (`sqft`, `piece`, `job`), rate_inr, source (who checked it, where) |
| **Finding** | id, run_id ✱, move_out_inspection_id, item_id, slot_id ✱, before_photo_id, after_photo_id, change_type, classification (`damage`, `wear`, `pre_existing`, `owner_responsibility` ✱, `none`), severity (0 to 3), confidence, region_description, reasoning, cited_evidence ✱ (note or report IDs), quantity, depreciation_factor ✱, est_cost, owner_override_cost ✱, status (`proposed`, `needs_review`, `accepted`, `disputed`), tenant_note ✱, owner_note ✱ |
| **AgentRun** ✱ | id, tenancy_id, status (`running`, `done`, `failed`), started_at, finished_at, summary_en, summary_kn |
| **AgentStep** ✱ | id, run_id, seq, kind (`thought`, `tool_call`, `tool_result`, `error`), tool_name, payload (JSON), created_at |

**Pairing rule:** a move-out photo pairs with the move-in photo that has the same `slot_id`. No image matching is needed.

**Default item:** every room has a "Walls and floor" item, so a slot without a specific item still has an age and a replacement cost.

---

## 6. Integrity (tamper-evidence)

1. **Camera only.** The capture screen uses `getUserMedia`, with no file picker, so photos can't come from the gallery. *(This is a deterrent, not proof. We say so honestly in the pitch.)*
2. **The client hashes the exact bytes it uploads.** It resizes to 1280 px JPEG at quality 0.8 first, then computes SHA-256 with `crypto.subtle`. The server re-hashes, rejects a mismatch, and stores the file as `<sha256>.jpg`.
3. **Locking.** When both parties have signed, `lock_hash = sha256(sorted photo hashes + sorted note texts + both signature timestamps)`. After that, any write to a locked inspection returns **409**.
4. **The UI shows** a 🔒 badge, the first 8 characters of the lock hash, and both signature times.

---

## 7. API

Prefix `/api`. JSON in and out unless noted. Auth is `Authorization: Bearer <jwt>`.

**Auth**
| Method | Path | Notes |
|---|---|---|
| POST | `/auth/otp/request` | `{phone}`. Demo mode does not send an SMS. |
| POST | `/auth/otp/verify` | `{phone, otp}`, returns `{token, user}`. The demo OTP is `123456`. |
| GET | `/me` | The user plus their tenancies, with a role on each |

**Property and setup** (the MVP uses seed data; the UI is stretch)
| Method | Path |
|---|---|
| POST, GET | `/properties` |
| GET | `/properties/{id}` (returns rooms, items and slots) |
| POST | `/properties/{id}/rooms`, `/rooms/{id}/items`, `/rooms/{id}/slots` |

**Tenancy**
| Method | Path | Notes |
|---|---|---|
| POST | `/properties/{id}/tenancies` | `{tenant_phone, deposit, monthly_rent, start_date}`, returns an invite link |
| POST | `/tenancies/join` | `{invite_code}` |
| GET | `/tenancies/{id}` | Includes inspections, reports and the latest run |

**Inspections**
| Method | Path | Notes |
|---|---|---|
| POST | `/tenancies/{id}/inspections` | `{type}`. A move-out needs a locked move-in first. |
| GET | `/inspections/{id}` | Slots with photo, notes, and capture status |
| POST | `/inspections/{id}/photos` | Multipart: `slot_id, file, sha256, captured_at, device_meta` |
| GET | `/inspections/{id}/ghost/{slot_id}` | The move-in photo used as the overlay |
| POST | `/inspections/{id}/notes` | `{slot_id, text}` |
| POST | `/inspections/{id}/sign` | Locks the inspection when both have signed |

**Reports, runs and findings**
| Method | Path | Notes |
|---|---|---|
| POST | `/tenancies/{id}/issues` | A maintenance or check-in report |
| POST | `/tenancies/{id}/compare` | Starts the agent and returns `{run_id}` |
| GET | `/runs/{id}/events` | **SSE** stream of `AgentStep` rows, ending with `done` |
| GET | `/tenancies/{id}/report` | Findings, scores, totals and summaries |
| PATCH | `/findings/{id}` | Tenant: `{status: accepted or disputed, tenant_note}`. Owner: `{owner_override_cost, owner_note}`. |
| POST | `/findings/{id}/reassess` | Stretch: the agent re-looks using the dispute note |
| GET, PUT | `/rate-card` | |
| GET | `/tenancies/{id}/report.pdf` | Stretch |

**Errors:** `401` for no token, `403` for the wrong role, `404` for not found, `409` for a locked inspection or wrong state, `422` for a hash mismatch or validation failure.

---

## 8. The agent (agentic track)

### Why it's an agent, not a single call
The model decides what to look at next, pulls in more evidence (item age, tenant notes, maintenance history), asks for a retake when the photos don't line up, and builds its case step by step. **Money is never decided by the model.** Costs come from deterministic code, so every rupee is explainable.

### Loop
- A tool-use loop on the vision LLM, capped at **40 iterations** with a **3-minute** limit.
- The model can request several pair inspections at once. They run concurrently, at most 4 at a time.
- Every tool call and result is written as an `AgentStep` and streamed to the UI.

### Tools
| Tool | Type | What it does |
|---|---|---|
| `list_pairs()` | DB | Slots with before and after photo IDs, item and room. Flags slots missing either photo. |
| `inspect_pair(slot_id)` | **Vision LLM** | Sends both images with the contract in §9 and returns structured JSON |
| `get_item(item_id)` | DB | Type, material, age at move-out (age at move-in plus tenancy length), useful life, replacement cost |
| `get_slot_notes(slot_id)` | DB | Notes from move-in ("already here") with author and time |
| `get_maintenance_reports(item_id or slot_id)` | DB | The tenant's earlier issue reports with dates |
| `estimate_cost(change_type, item_id, severity, quantity)` | **Code** | Rate card × quantity × depreciation. Returns a breakdown. |
| `flag_retake(slot_id, reason)` | DB | Marks the pair as needing a retake. No charge. |
| `record_finding({...})` | DB | Saves a finding with classification and the evidence it cites |
| `finish(summary_en, summary_kn)` | DB | Closes the run. Code computes the scores (§10). |

### Decision rules (in the system prompt)
1. **A change that a move-in note mentions** is classified `pre_existing`, citing the note.
2. **A change that matches an earlier tenant maintenance report** (same slot or item, a plausible cause such as seepage, plumbing or structural, reported before move-out) is classified `owner_responsibility` at ₹0, citing the report.
3. **Normal wear:** fading, light scuffs, or ageing consistent with the item's age and tenancy length. Classified `wear`, no penalty.
4. **Confidence below 0.6** sets the status to `needs_review`, and it isn't charged.
5. **Photos that don't match** (different angle, too dark, a different object) call `flag_retake`. Never guess.
6. **Be fair to both sides.** Real new damage is recorded even when it hurts the tenant.
7. **Every finding must cite** its photo pair, plus any notes or reports it relies on.

### Trace shown in the UI (example)
```
🔍 Pairing 4 slots: all have before and after photos
👁 Inspecting Wall A, Table, Window wall, Sofa (4 in parallel)
📝 Window wall: new brown stain, 18 cm, severity 2
📂 Checking the tenant's maintenance reports for Window wall
✅ Found "damp stain, seepage from outside wall" (12 Sep). Owner's responsibility, ₹0
📝 Table: chip at corner, already in the tenant's move-in note. Pre-existing
💰 Table coffee stain: polish, severity 1, 6-year-old table, depreciation 0.4, ₹480
🧾 4 findings, 1 needs review. Writing the summary
```

---

## 9. Vision prompt contract (`inspect_pair`)

**Input:** the before image (move-in), the after image (move-out), slot label, item type and material, item age, and tenancy length in months.

**Output (strict JSON):**
```json
{
  "pair_usable": true,
  "mismatch_reason": null,
  "changes": [
    {
      "change_type": "stain | crack | hole | broken | missing | discoloration | scuff | none",
      "region_description": "lower-left wall near the switchboard",
      "size_estimate": "about 20 cm wide",
      "is_normal_wear": false,
      "severity": 2,
      "confidence": 0.82,
      "bbox_after": [0.12, 0.55, 0.20, 0.18],
      "reasoning": "New dark stain not present in baseline"
    }
  ]
}
```
- **One pair can return several changes** (the original design allowed one). The table can have both a chip and a stain.
- `severity`: 0 none, 1 minor, 2 moderate, 3 severe.
- `bbox_after` is normalised `[x, y, w, h]` and optional. It's for the stretch highlight.
- When `pair_usable` is false, the agent must call `flag_retake`.
- The backend validates against the schema and retries once if the JSON is invalid.

---

## 10. Scoring and money (deterministic code, never the LLM)

**Severity penalty:** 0 → 0, 1 → 15, 2 → 40, 3 → 80. Only `damage` findings carry a penalty. `wear`, `pre_existing`, `owner_responsibility` and `none` carry 0.

**Item score:** 100 minus the worst penalty among that item's damage findings.

**Property condition score:** the average of item scores, weighted by each item's `replacement_cost`.

**Cost per damage finding:**
```
age_at_move_out = age_years_at_move_in + tenancy_months / 12
depreciation    = max(0.2, 1 - age_at_move_out / useful_life_years)
cost            = rate_card[change_type][item_type][severity] × quantity × depreciation
```
If the owner sets an `owner_override_cost`, it replaces the computed cost and the UI shows both, together with the owner's reason.

**Totals:**
| Figure | Rule |
|---|---|
| Damage % | Total damage cost ÷ total replacement value of inventoried items |
| Proposed deduction | Sum of `proposed` + `accepted` damage findings (excluding `disputed` and `needs_review`), capped at the deposit |
| Agreed deduction | Sum of `accepted` damage findings only, capped at the deposit |
| In dispute | Sum of `disputed` findings |
| Refund due | Deposit − agreed deduction |

**Rate card:** the team seeds it with **checked** Bengaluru rates and fills in the `source` column. No AI-generated numbers. Rows we need for the demo:

| change_type | item_type | Unit | Needs a checked rate for severity 1 / 2 / 3 |
|---|---|---|---|
| stain | table | job | ☐ |
| crack | wall | sqft | ☐ |
| stain | wall | sqft | ☐ |
| hole | wall | piece | ☐ |
| discoloration | cushion | piece | ☐ |
| broken | tile | piece | ☐ |

Default useful life in years (editable): wall paint 5, wooden furniture 10, fabric and cushions 3, tiles 15, fan 10, geyser 8.

---

## 11. Frontend (React + Vite PWA, mobile first)

**PWA:** use `vite-plugin-pwa` for the manifest, icons and offline app shell. Capture must work in standalone mode on Android Chrome and iOS Safari.

| # | Screen | Key elements |
|---|---|---|
| 1 | **Login** | Phone, OTP (demo shows "use 123456") |
| 2 | **Home** | Owner: properties and tenancies. Tenant: my tenancy, with a status timeline (Move-in signed 🔒, Check-ins, Move-out, Settled) |
| 3 | **Tenancy** | Deposit, rent, dates, invite link and QR, list of inspections, "Start move-out" |
| 4 | **Guided capture** | Full-screen camera, slot label and guidance, progress ("3 of 4"), shutter, retake, note button. For move-out and check-ins, a **ghost overlay** of the move-in photo with an opacity slider. |
| 5 | **Review and sign** | Grid of slot photos with notes. Tenant can add "already here" notes. Sign button, then 🔒 badge with hash prefix and times. |
| 6 | **Agent run** | The live trace (SSE), per-slot progress chips, "Thinking…" state |
| 7 | **Report** | Condition score dial, damage %, deposit / proposed / agreed / disputed / refund bar. Finding cards: before and after side by side (tap to swipe), a classification chip (Damage, Wear, Pre-existing, Owner's responsibility, Needs review), the cost with its depreciation breakdown, cited evidence, and Accept / Dispute buttons for the tenant. |
| 8 | **Settlement** | Final totals, summary in English and Kannada, share on WhatsApp (`wa.me` link), PDF (stretch) |

**State and data:** React Query for API calls, the browser's `EventSource` for the run trace, and a JWT in memory with localStorage for the demo.

**Live sync between the two phones:** both report screens poll `/report` every 3 seconds, so a dispute on the tenant phone shows on the owner phone. That's simpler than websockets.

---

## 12. Changes from the original design

| Original design | This spec | Why |
|---|---|---|
| Supabase or Firebase | FastAPI + SQLite + local disk | Team choice. Nothing extra to provision during a 2-hour build. |
| `angle_slot` string on Photo | A `CaptureSlot` entity | Slots carry a label, guidance and an item link, and pairing is by ID |
| One change per photo pair | A list of changes per pair | A single angle often shows more than one issue |
| Classification: damage, wear, none | Adds `pre_existing` and `owner_responsibility` | These are the tenant-protection outcomes. They come from notes and maintenance reports. |
| Severity 0–3 in the prompt, but none/minor/moderate/severe in scoring | Aligned: 0, 1, 2, 3 map to penalties 0, 15, 40, 80 | One scale everywhere |
| A worker that compares photos | A tool-using agent with a visible trace | Needed for the agentic track, and it makes every decision explainable |
| Item age is fixed | Age at move-out = age at move-in + tenancy length | Depreciation stays correct |

---

## 13. Repository layout

```
deposit-rakshak/
  backend/
    app/
      main.py            FastAPI app, CORS, static photo serving
      config.py          env: LLM provider + key, JWT secret, DEMO_MODE
      db.py, models.py   SQLModel tables (§5)
      auth.py            OTP + JWT
      routers/           auth, properties, tenancies, inspections, findings, runs
      agent/
        loop.py          tool-use loop, step logging, limits
        tools.py         the tools in §8
        prompts.py       system prompt + vision contract
      llm.py             the single provider adapter
      scoring.py         §10, pure functions
      integrity.py       hashing + lock_hash
      seed.py            demo users, property, slots, rate card, check-in report
    data/photos/
  frontend/
    src/
      pages/             one per screen in §11
      components/        Camera, GhostOverlay, FindingCard, TraceList, ScoreDial
      api.ts
    vite.config.ts       vite-plugin-pwa
  SPEC.md
```

---

## 14. Demo seed data

- **Users:** Owner (phone ending 0001) and Tenant (phone ending 0002). OTP 123456.
- **Property:** "Demo Flat, Koramangala" with one room, "Hackathon Room".
- **Items:** Walls and floor (paint, 4 years old, useful life 5), Table (wood, 6 years, useful life 10), Sofa cushion (fabric, 2 years, useful life 3).
- **Slots:** Wall A, Table top, Window wall, Sofa.
- **Tenancy:** deposit ₹1,50,000, rent ₹15,000, started 11 months ago.
- **Maintenance report:** Window wall, "Damp stain spreading near window, seepage from outside wall", category `seepage`, dated 2 months ago.
- **Move-in note** (added live in the demo): Table top, "small chip on the corner already here".

**Fallback:** if the LLM is slow or the venue Wi-Fi drops, `DEMO_MODE=1` replays a recorded agent run from a JSON file through the same SSE stream.

---

## 15. Two-hour build plan

Assumes 4 people. With 3, merge the Pitch role into the AI role.

| Time | Backend | Frontend | AI / Agent | Pitch / QA |
|---|---|---|---|---|
| 0:00–0:15 | Scaffold, models, seed | Vite PWA scaffold, routing | Pick provider, get key, test one image call | Set up HTTPS tunnel, test camera on both phones |
| 0:15–0:45 | Auth, inspections, photo upload + hash, sign/lock | Login, Home, **Camera capture** | `inspect_pair` + JSON validation on 3 real photo pairs | Shoot sample photo pairs, check rate card prices |
| 0:45–1:15 | Compare + SSE runs, report endpoint | Ghost overlay, Review and sign | Agent loop + tools + decision rules | Write the slides (problem, demo, how it works, impact) |
| 1:15–1:35 | Findings PATCH, `scoring.py` | Agent run screen, Report screen | Tune prompts on the staged room, record the fallback run | Rehearse the demo end to end |
| 1:35–1:50 | Bug fixes | Settlement + WhatsApp share | Kannada summary check | Final rehearsal, two phones charged |
| 1:50–2:00 | **Freeze.** Buffer only. | | | |

**Cut line at 1:15.** If behind, drop in this order: the ghost overlay slider (keep a fixed 40% overlay), live SSE (switch to polling), the Kannada summary, the owner cost override.

---

## 16. Pitch mapping to judging

- **Vision:** before-and-after reasoning, not just detection. It separates damage, wear and pre-existing marks, and flags pairs it can't trust.
- **Agentic:** multi-step evidence gathering (photos, item age, notes, maintenance history), retake requests, and a fully visible trace. The model proposes and code prices it.
- **Bengaluru impact:** deposits of 6 to 10 months' rent. Even a ₹20,000 dispute per move adds up across a city with millions of renters.
- **Trust:** both parties sign the record, hashes lock it, every rupee is explainable, and the AI never has the final word.

---

## 17. Open questions

1. **LLM provider:** do the hackathon rules require IBM watsonx (Granite or Llama vision)? This decides `llm.py`.
2. **Team size and roles** for §15.
3. **Bob:** must the code be written in IBM Bob, and does it have to appear in the demo?
4. **Who checks the rate card numbers,** and from which source (a painter's quote, an online rate list)?
