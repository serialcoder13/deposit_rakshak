# Deposit Rakshak: SDLC (2-hour hackathon)

A compressed, time-boxed agile cycle: **4 micro-sprints**, each ending with a working gate. IBM Bob writes most of the code. People own requirements, review, tests and the demo.

| Doc | Role in the cycle |
|---|---|
| [SPEC.md](SPEC.md) | Requirements and detailed design |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and decisions |
| [BOB_PLAYBOOK.md](BOB_PLAYBOOK.md) | Build tasks as ready-to-paste Bob prompts |
| This file | Process, stories, tests, release |

---

## 1. Phases and gates

| Phase | Time | Output | Gate (must be true to move on) |
|---|---|---|---|
| **0. Plan** | 0:00–0:10 | Roles assigned, provider chosen, repo created with the docs | LLM key works on one image call. The tunnel opens the camera on both phones. |
| **1. Sprint 1: Foundations** | 0:10–0:40 | Models, seed, auth, photo upload with hash, PWA shell, camera screen | A photo taken on a phone shows up in `data/photos` with a matching hash |
| **2. Sprint 2: Records** | 0:40–1:05 | Sign and lock, ghost overlay, `scoring.py` with tests, `inspect_pair` on real pairs | Move-in locks with a hash. Scoring tests pass. One real pair returns valid JSON. |
| **3. Sprint 3: Agent + report** | 1:05–1:30 | Agent loop + tools + SSE, report screen, findings PATCH | A full run on the staged room shows findings and totals on both phones |
| **4. Hardening + demo** | 1:30–1:50 | Bug fixes, recorded fallback run, rehearsal | Two clean end-to-end rehearsals |
| **Freeze** | 1:50–2:00 | No new code | |

**Cut line at 1:15** (see SPEC §15): drop the overlay slider, then SSE (switch to polling), then the Kannada summary, then the owner override.

---

## 2. Roles (team of 4)

| Role | Owns | Bob tasks |
|---|---|---|
| Backend | API, DB, integrity, scoring | B1–B7 |
| Frontend | PWA, camera, screens | F1–F7 |
| AI / Agent | `llm.py`, prompts, agent loop, prompt tuning | A1–A4 |
| Product / QA / Pitch | Stories, rate card checks, test photos, tunnel, slides, rehearsal | T1–T3 |

With 3 people, the AI person also takes the pitch.

---

## 3. User stories and acceptance criteria

**US1: Log in.** As an owner or tenant, I log in with my phone number.
- Given a seeded phone number, when I enter OTP 123456, then I land on Home and see my tenancy with my role.

**US2: Move-in capture.** As an owner, I capture each slot with the in-app camera.
- Given a draft move-in, when I shoot a slot, then the photo uploads and the slot shows ✓.
- The capture screen offers no gallery picker.
- If the hash the server computes doesn't match, the upload is rejected with 422.

**US3: Tenant review and notes.** As a tenant, I review the move-in photos and add notes.
- Given a draft move-in, when I add "chip on the corner already here" to the Table slot, then the owner sees the note.

**US4: Sign and lock.** As owner and tenant, we both sign and the record locks.
- Given all slots have photos, when both have signed, then the status is `locked`, a 🔒 badge and hash prefix show, and any further upload returns 409.

**US5: Move-out with ghost overlay.** As an owner, I see the old photo while framing the new one.
- Given a locked move-in, when I open a move-out slot, then the move-in photo appears at about 40% opacity over the live camera.

**US6: Run the agent.** As either party, I start the comparison and watch it work.
- When I tap Compare, then trace steps appear within 5 seconds and the run ends with `done` in under 3 minutes.

**US7: Explainable findings.** As either party, I see each finding with its evidence.
- Each card shows before and after photos, a classification, severity, confidence, the cited notes or reports, and the cost breakdown (rate × quantity × depreciation).
- A change covered by a move-in note is `pre_existing`. A change matching a tenant maintenance report is `owner_responsibility` at ₹0. Confidence below 0.6 is `needs_review` and isn't charged.

**US8: Dispute.** As a tenant, I accept or dispute each finding.
- When I dispute a finding, then the agreed deduction drops, the disputed total rises, and the owner's phone shows it within 5 seconds.

**US9: Settlement.** As either party, I share the result.
- The settlement screen shows the refund due and the summary in English and Kannada, and Share opens WhatsApp with the text.

**US10: Tenant maintenance report** (seeded for the MVP, UI is stretch).
- A report filed before move-out is used as evidence by the agent.

---

## 4. Definition of Done (per task)

- [ ] Meets the acceptance criteria of its story
- [ ] Runs against the seeded data without manual database edits
- [ ] No API keys or secrets in the frontend or in git
- [ ] Pure logic (`scoring.py`, `integrity.py`) has passing pytest tests
- [ ] A person read Bob's diff before accepting it
- [ ] Merged to `main` and the app still starts

---

## 5. Source control

- One repo, branch `main` is always runnable.
- Short-lived branches per task (`b3-sign-lock`, `f4-camera`). Merge at every sprint gate at the latest.
- Commit `.env.example`, never `.env`. Add `data/` to `.gitignore` except `data/demo_run.json`.
- Tag `demo-v1` at the freeze.

---

## 6. Test strategy

| Level | What | How | Who |
|---|---|---|---|
| Unit | `scoring.py`: penalties, depreciation floor 0.2, deposit cap, totals per status. `integrity.py`: same bytes give the same hash, and `lock_hash` is stable when inputs are reordered. | pytest, written **before** the code (Bob task B5) | Backend |
| API smoke | Login, create inspection, upload, sign twice, check the lock, 409 on a later upload | One pytest file using FastAPI `TestClient` | Backend |
| Vision golden set | 5 real before/after pairs from the venue: a stain, a crack, wear, an unchanged pair, a mismatched angle | Script that runs `inspect_pair` on each and prints the JSON. Check by eye. | AI |
| Agent scenario | The seeded tenancy with staged changes gives the 5 expected outcomes in SPEC §1 | Run 2 to 3 times and check it's consistent | AI |
| Device | Camera in installed PWA mode, overlay, upload over the tunnel, both phones in sync | Manual checklist (section 7) | QA |

---

## 7. Device test checklist

- [ ] Tunnel URL opens on both phones over HTTPS
- [ ] Camera permission prompt appears and the rear camera is used
- [ ] Add to Home Screen works and the camera still works in standalone mode
- [ ] Photo upload takes under 3 seconds over the venue Wi-Fi
- [ ] The ghost overlay lines up when standing at the marked spot
- [ ] The SSE trace streams through the tunnel (if not, switch to polling)
- [ ] A dispute on the tenant phone shows on the owner phone
- [ ] WhatsApp share opens with the Kannada text intact

---

## 8. Risk register

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Venue Wi-Fi or LLM latency | Medium | High | `DEMO_MODE` recorded run, phone hotspot as backup | AI |
| Camera blocked without HTTPS | High if untested | High | Test the tunnel in Phase 0 | QA |
| Vision misreads a staged change | Medium | Medium | Staged changes that are obvious (dark coffee stain, black tape crack), good light, golden set tuning | AI |
| Bob output drifts from the spec | Medium | Medium | Every prompt names the SPEC section. A person reviews each diff. | Everyone |
| Merge conflicts in a hurry | Medium | Medium | Separate folders per role, merge at gates | Backend |
| Running out of time | High | High | Cut line at 1:15, freeze at 1:50 | Product |

---

## 9. Release (demo) checklist

- [ ] `npm run build` copied into `backend/app/static`
- [ ] `python -m app.seed` run fresh just before the demo
- [ ] Staged room reset (stain, tape crack, window sticker removed) for the move-in shots, then reapplied
- [ ] Both phones logged in, PWA installed, brightness up, Do Not Disturb on
- [ ] `DEMO_MODE` fallback tested once
- [ ] Slides: Problem, Demo, How it works (agent trace + scoring), Impact, What's next
