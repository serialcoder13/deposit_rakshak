# Deposit Rakshak: UI and Usability Iterations (Bob prompts)

The app works end to end but looks like a scaffold. These 10 iterations turn it into something an owner and a tenant can actually use, with a polished, demo-ready look.

**How to run them**
- **One iteration per Bob chat.** Paste the Project rules from BOB_PLAYBOOK.md first, then the iteration prompt.
- **After each iteration,** check it on a phone (ngrok on port 5173) before starting the next one.
- **If a screen looks off,** take a phone screenshot and give it to Bob with "fix what looks wrong against the Design System in UI_ITERATIONS.md".
- **Order matters for 1–3.** After that, the Frontend person runs 4–9 while the AI person finishes the agent (iteration 7A).
- **Short on time?** Do 1, 2, 2B, 3, 4, 6, 7, then 9. Skip 5, 8 and 10.

---

## The two journeys (what "usable" means)

| Stage | Owner (Ravi) sees | Tenant (Meera) sees |
|---|---|---|
| 0. Set up | **"Add your flat"**: address, layout, invite tenant by phone | **Invite card**: Accept or Decline |
| 1. Move-in record | **"Record the flat"**: guided capture, 4 shots | "Waiting for Ravi to record the flat" |
| 2. Sign | "Waiting for Meera to review" (live) | **"Review and sign"**: add "already there" notes, then sign |
| 3. Living | Deposit held, sealed record 🔒, issues the tenant reported | **"Report an issue"** (leak, seepage…), deposit protected 🛡 |
| 4. Move-out | **"Start move-out"**: capture with ghost overlay | "Move-out in progress" (live) |
| 5. AI check | **"Run AI check"**: live agent trace | Same trace, live |
| 6. Review | Findings, can override cost with a reason | **Accept or dispute** each finding |
| 7. Settled | Refund to pay, share | Refund due, share |

**Rule:** every screen shows exactly **one primary "next action"** for the logged-in role. Nobody should ever wonder what to tap next.

---

## Design System (every prompt refers to this)

**Feel:** "Rakshak" means protector. The look should feel premium, safe and alive: a deep indigo-to-violet gradient, a shield motif, glass cards on the gradient, white cards on a soft background, and springy motion. Think of a modern fintech app.

| Token | Value |
|---|---|
| Brand gradient | `from-indigo-600 via-violet-600 to-fuchsia-500` (hero headers, primary buttons) |
| Owner accent | indigo `#4F46E5` |
| Tenant accent | teal `#0D9488` |
| Highlight | saffron `#F59E0B` (disputes, attention) |
| Success / Danger | emerald `#10B981` / rose `#E11D48` |
| Page background | `#F6F7FB` with 2 blurred gradient blobs at the top |
| Text | slate-900 headings, slate-500 secondary |
| Cards | white, `rounded-3xl`, soft shadow `0 8px 30px rgba(15,23,42,.08)`, padding 20 |
| Glass (on gradient) | `bg-white/10 backdrop-blur-xl border border-white/20` |
| Fonts | **Plus Jakarta Sans** for headings and numbers, **Inter** for body (Google Fonts) |
| Numbers | `tabular-nums`. Money always `₹` + `toLocaleString('en-IN')`, e.g. ₹1,50,000 |
| Tap targets | at least 48px. Primary button full width, `rounded-2xl`, height 56 |
| Motion | framer-motion: page enter fade + slide up 12px, list stagger 0.05s, buttons `whileTap={{scale:0.97}}`, number count-up on money |
| Icons | lucide-react only. No emoji in the UI chrome. |
| Safe areas | respect `env(safe-area-inset-*)` for notched phones |

**Classification chips (used everywhere):**
| Classification | Colour | Icon | Label |
|---|---|---|---|
| damage | rose | `AlertTriangle` | Damage |
| wear | slate | `Hourglass` | Normal wear |
| pre_existing | sky | `History` | Already there |
| owner_responsibility | violet | `ShieldCheck` | Owner's repair |
| needs_review | amber | `Eye` | Needs review |
| none | emerald | `CheckCircle2` | No change |

---

## Iteration 1: Design foundation and component kit

```
Read UI_ITERATIONS.md (Design System section) and SPEC §11.
Goal: replace the inline styles with a real design system and a reusable component kit.

1. Install: tailwindcss@3.4 postcss autoprefixer, framer-motion, lucide-react,
   sonner (toasts), canvas-confetti, clsx. Set up tailwind.config with the tokens
   from the Design System (colours, fonts, rounded-3xl, shadow "soft").
   Add the Google Fonts (Inter, Plus Jakarta Sans) in index.html. Set the body
   background and the blurred gradient blobs in index.css.
2. Create src/components/ui/:
   - Button (variants: primary gradient, secondary white, ghost, danger; sizes;
     loading spinner; whileTap spring; optional left icon)
   - Card, GlassCard
   - Chip and ClassificationChip (the table in the Design System)
   - StatusPill for inspection status (draft, awaiting_signatures, locked with a Lock icon)
   - Money (₹, en-IN grouping, optional count-up animation)
   - ProgressRing (animated SVG ring, value 0–100, centre label)
   - Stepper (vertical journey stepper: done / current / upcoming states)
   - BottomSheet (framer-motion, drag to close, backdrop)
   - Skeleton, EmptyState (icon + title + text + action)
   - RoleBadge (Owner indigo, Tenant teal)
   - AppShell: sticky top bar (back button, title, role badge, avatar menu with
     logout) + a page container (max-w-md, mx-auto, safe-area padding) +
     framer-motion page transition
3. Add src/lib/format.ts: money(), dateShort(), timeAgo(), shortHash().
4. Mount <Toaster /> from sonner in main.tsx.
5. Create public/logo.svg (a shield with a house inside, brand gradient) and use
   @vite-pwa/assets-generator to produce the PWA icons and apple-touch-icon.
   Update the manifest theme_color to #4F46E5.
6. Do not change any page logic yet. Only convert LoginPage to the new kit as a
   sample so I can see the style.
```
**Check:** the Login page looks premium on the phone, and the app icon shows when you Add to Home Screen.

---

## Iteration 2: Login and role-aware Home with "next action"

```
Read UI_ITERATIONS.md (The two journeys, Design System) and SPEC §3.
Goal: each role lands on a home screen that tells them exactly what to do next.

1. Login: full-height gradient hero with the shield logo, the title
   "Deposit Rakshak" and the tagline "Your deposit, protected." A phone field
   with a +91 prefix, then a 6-box OTP input (auto-advance, paste support,
   auto-submit). Below it, a "Demo" row with two big glass buttons:
   "Continue as Owner (Ravi)" and "Continue as Tenant (Meera)". These log in
   with the seeded phones 9999990001 / 9999990002 and OTP 123456 in one tap.
2. Create src/lib/journey.ts with a pure function
   getJourney(tenancy, role) -> { stages: [...8 stages (0 to 7) from the journeys table
   with state done/current/upcoming], nextAction: { title, subtitle, cta,
   to | onClick, tone } }. Derive it from the inspections' type and status,
   latest_run status, and findings status. Unit-test it with a few cases.
3. Backend: extend GET /api/me (or add GET /api/home) so each tenancy item
   includes property address, deposit, monthly_rent, the other party's name,
   and the stage. Update schemas.py and the api.ts types together.
4. Home (Owner): gradient hero "Good evening, Ravi", then a property card
   (address, tenant name, deposit as Money, stage chip), then a large
   "Next action" card with one primary button from getJourney.
5. Home (Tenant): hero with a big shield and "₹1,50,000 protected", a
   sealed-record status ("Move-in record sealed 🔒" or "Not sealed yet"), then
   the "Next action" card, then a compact journey Stepper.
6. Loading uses Skeletons. Errors use a toast plus an EmptyState with Retry.
```
**Check:** one tap logs in each role on two phones, and each home shows a different, correct next action.

---

## Iteration 2B: Open sign-up, create a property, invite a tenant by phone

**Test numbers** (any 10-digit number works, OTP is always `123456`):
| Who | Phone | Use it to |
|---|---|---|
| New owner | `9876500001` | Sign up, create a property, invite the tenant |
| New tenant | `9876500002` | Sign up and accept the invite |
| Seeded owner / tenant | `9999990001` / `9999990002` | The pre-built demo flat |

```
Read SPEC §3, §5, §7 and UI_ITERATIONS.md.
Goal: anyone can sign up with a phone number, an owner can create a property
and invite a tenant by phone, and the tenant accepts the invite.

BACKEND
1. Auth: POST /otp/request and /otp/verify must auto-create the user when the
   phone is new (no more 404). Normalise phones to 10 digits (strip spaces,
   "+91", leading 0); reject anything else with 422. OTP is settings.demo_otp
   (123456). The verify response includes is_new_user (true when name is empty).
2. PATCH /api/me {name} to set the display name.
3. models.py: Tenancy gains tenant_phone (str, required) and invite_status
   ("pending" | "accepted"); tenant_id stays nullable until accepted.
   Update schemas.py and api.ts. The SQLite schema changes, so tell me to delete
   backend/data/app.db and run python -m app.seed again. Update seed.py so the
   seeded tenancy is accepted.
4. backend/app/templates.py: property presets that create rooms, default items
   (with age_years_at_move_in, useful_life_years, replacement_cost) and capture
   slots (label + guidance):
   - "1BHK": Living room, Bedroom, Kitchen, Bathroom
   - "2BHK": Living room, Bedroom 1, Bedroom 2, Kitchen, Bathroom 1, Bathroom 2
   - "Single room" (demo): Wall A, Table top, Window wall, Sofa
   Each real room gets 2 to 3 slots (e.g. Living room: "Main wall", "Floor",
   "Window side"; Kitchen: "Counter", "Sink and tiles"; Bathroom: "Tiles",
   "Fittings"). Every room also gets the "Walls and floor" default item.
5. POST /api/properties {address, city, preset, item_age_years} creates the
   property from a preset; the caller becomes the owner.
6. POST /api/properties/{id}/tenancies {tenant_phone, tenant_name?, deposit,
   monthly_rent, start_date} (owner only) creates a pending tenancy. If a user
   with that phone already exists, the invite shows for them immediately.
7. GET /api/me returns tenancies (with role, address, stage) AND
   pending_invites: tenancies where tenant_phone == my phone and
   invite_status == "pending" (address, owner name, deposit, rent, start date).
8. POST /api/tenancies/{id}/accept (only for the invited phone) sets tenant_id,
   invite_status = accepted. POST /api/tenancies/{id}/decline deletes the
   pending invite.
9. Owner can see a pending tenancy, but move-in capture needs invite_status
   == accepted (409 otherwise, with a clear message).

FRONTEND (Design System from UI_ITERATIONS.md)
10. Login: any phone works. After verify, if is_new_user, show a one-field
    "What should we call you?" step (PATCH /api/me), then Home. Keep the two
    Demo buttons for the seeded flat.
11. Home empty state for a new user: two big choice cards, "I own a flat"
    (Building2 icon, goes to the property wizard) and "I'm renting" (KeyRound icon,
    explains "Ask your owner to invite your number" and shows the user's
    number with a copy button).
12. Property wizard, 3 steps with a progress bar and slide transitions:
    a) Address + city (default Bengaluru)
    b) Layout: tappable preset cards (1BHK, 2BHK, Single room) showing a
       room list preview, plus "How old is the paint and furniture?"
       (stepper: years)
    c) Invite tenant: tenant phone (+91), tenant name (optional), deposit,
       monthly rent (show "= N months' rent" live under the deposit), start
       date. Submit creates the property and then the tenancy.
    Finish with a success screen: "Invite sent to 98765 00002", plus a
    "Share on WhatsApp" button (wa.me text: "Ravi invited you to Deposit
    Rakshak for <address>. Open <app URL> and log in with this number.")
13. Tenant Home: pending invites appear at the top as a highlighted gradient
    card (owner name, address, deposit, rent) with "Accept" and "Decline".
    Accept shows a toast, then the tenancy appears with its next action.
14. Owner Home: a pending tenancy shows "Waiting for <name> to accept" with a
    pulsing dot and a "Resend on WhatsApp" button. Polling every 3s flips it
    live when the tenant accepts.
15. Owner can have several properties: Home lists them all, with a
    "+ Add property" button.
```
**Check:** on phone 1, sign up as `9876500001`, create a 1BHK and invite `9876500002`. On phone 2, sign up as `9876500002`, see the invite, and accept it. Phone 1 flips to "Accepted" within 3 seconds.

---

## Iteration 3: Tenancy journey screen and fixing the capture start

```
Read UI_ITERATIONS.md and SPEC §7 (Inspections).
Goal: one screen that shows the whole tenancy story and drives the flow.

1. Bug fix: "Start Move-in/Move-out Capture" navigates to /inspections/new/...
   which does not exist. Instead call POST /api/tenancies/{id}/inspections,
   then navigate to /inspections/{id}/capture. Backend: if a non-locked
   inspection of that type already exists for this tenancy, return it instead
   of creating a duplicate.
2. TenancyPage redesign (AppShell):
   - Header card: address, both people (avatars + RoleBadge), deposit and rent
     as Money, start date, and the invite code with a copy button.
   - The vertical journey Stepper (8 stages (0 to 7)). The current stage is expanded and
     shows the role-specific action from getJourney. Done stages show a small
     summary (e.g. "Sealed 12 Sep · hash a1b2c3d4").
   - "Issues reported" section listing maintenance reports (category icon,
     date, text).
3. Tenant only: a floating "Report an issue" button that opens a BottomSheet
   with category chips (seepage, plumbing, electrical, structural, other), a
   slot picker, and a description, posting to POST /api/tenancies/{id}/issues.
   On success: a toast and the list updates.
4. Poll GET /api/tenancies/{id} every 3s so the other party's actions appear
   live. When the stage changes, show a toast like "Meera signed the move-in record".
```
**Check:** the owner starts move-in from the stepper, and the tenant's issue report appears on the owner's phone within 3 seconds.

---

## Iteration 4: Camera capture with ghost overlay (the vision showpiece)

```
Read SPEC §6, §11 screen 4 and UI_ITERATIONS.md.
Goal: a native-feeling, full-screen camera with guided slots and a ghost overlay.

1. src/components/Camera.tsx: getUserMedia({ video: { facingMode: 'environment',
   width: 1920 } }), a full-screen black video, and no file input or gallery picker.
   Handle denied permission with an EmptyState explaining how to allow the camera.
2. Viewfinder chrome on glass: top bar with ✕, the slot label pill, and
   progress dots (one per slot, filled when captured); white corner brackets
   framing the shot; the guidance text in a glass pill near the bottom.
3. Ghost overlay for move_out and checkin: load
   GET /api/inspections/{id}/ghost/{slot_id} on top of the video at 40%
   opacity, with a vertical opacity slider on the right and a hint
   "Line up with the old photo".
4. Shutter: a big round button with a ring. On press: a white flash animation,
   navigator.vibrate?.(30), freeze the frame, then show the preview with
   "Retake" and "Use photo".
5. On "Use photo": canvas resize to 1280px on the long side, JPEG quality 0.8,
   SHA-256 of those exact bytes with crypto.subtle, then upload (slot_id,
   sha256, captured_at, device_meta). Show a "Sealing…" state, then a chip
   "Sealed ✓ a1b2c3d4" for 1 second, then auto-advance to the next slot.
6. A "Note" button opens a BottomSheet to add a slot note (POST notes).
7. After the last slot: a success screen ("4 of 4 captured") with a button
   "Review and sign" going to /inspections/{id}/review.
8. Already-captured slots show a thumbnail in the progress dots. Tapping one
   jumps back to retake it (only while the inspection is not locked).
```
**Check:** on a real phone the camera opens, the overlay lines up, and each photo shows the "Sealed ✓" hash chip.

---

## Iteration 5: Review, sign and the lock moment

```
Read SPEC §6, §11 screen 5 and UI_ITERATIONS.md.
Goal: make signing feel serious and the lock feel satisfying.

1. ReviewSignPage: a 2-column photo grid (rounded-2xl). Each tile shows the slot
   label and a note badge count. Tapping opens a full-screen viewer with notes.
2. Tenant: on each tile a quick action "Already there" opens a BottomSheet with
   preset notes ("chip", "stain", "crack", "scratch") plus free text.
3. A signature panel at the bottom: both parties with a status ("Signed 12:41" with a
   check, or "Waiting…" with a pulsing dot). The current user's action is a
   "Hold to sign" button: pressing fills a progress ring over 1.2s, then calls
   POST /sign. The button is disabled until every slot has a photo.
4. Poll every 3s. When the status becomes locked: a full-screen lock animation
   (the padlock closes with a spring, the gradient glow pulses), then the
   lock_hash types out character by character, with the text "Record sealed.
   Neither side can change it now." Then return to the Tenancy page.
5. Locked inspections show a permanent sealed banner with the hash and
   both signature times.
```
**Check:** the tenant holds to sign, and both phones show the lock animation and the same hash.

---

## Iteration 6: Report screen (the money moment)

```
Read SPEC §10, §11 screen 7 and UI_ITERATIONS.md.
Goal: a beautiful, explainable report where every rupee can be challenged.

1. Hero: the condition score in a large animated ProgressRing (colour by score:
   ≥80 emerald, ≥50 amber, else rose), with damage % underneath.
2. Deposit bar: a horizontal stacked bar for the deposit split into Refund
   (emerald), Agreed deduction (rose), Disputed (saffron), Pending (slate),
   with an animated width and a legend showing Money values (count-up).
3. Filter tabs: All · Charged · Not charged · Needs review · Disputed.
4. Finding card:
   - A before/after compare slider (draggable divider over the two photos,
     labelled "Move-in" / "Move-out"). Tap to open full screen.
   - The ClassificationChip, a severity dot scale (0–3), and confidence as a
     small bar.
   - Region description and reasoning (two lines, "More" expands).
   - An evidence row: chips for cited notes or reports ("Tenant note: chip
     already there", "Issue reported 12 Sep: seepage").
   - Cost: a big Money value. "How we got this" expands to show rate ×
     quantity × depreciation, item age and useful life. Owner overrides show the
     old value struck through plus the reason.
   - Tenant actions: "Accept" (emerald) and "Dispute" (opens a BottomSheet
     for the reason). Owner action: "Adjust cost" (opens a BottomSheet with
     amount + reason).
   - Not-charged cards (wear, already there, owner's repair) are visually
     calmer, with a ₹0 "Not charged" badge.
5. Poll /report every 3s. When totals change from the other phone, animate the
   numbers and show a toast ("Meera disputed: Crack on Wall A").
6. A bottom CTA "Go to settlement" once every damage finding is accepted or
   disputed.
```
**Check:** a dispute on the tenant phone animates the bar and toasts on the owner phone.

---

## Iteration 7A: Make the agent real (backend, AI person, run in parallel)

The agent loop and tools are still stubs that raise `NotImplementedError`, so Compare fails. Run tasks **A2, A3 and A4 from BOB_PLAYBOOK.md** now. If the real agent isn't ready when the UI is, use this to keep the frontend unblocked:

```
Create backend/data/demo_run.json by hand: a realistic sequence of ~14 agent
steps (kinds thought, tool_call, tool_result) and 5 findings for the seeded
tenancy matching SPEC §1 exactly (coffee stain on Table top = damage; crack on
Wall A = damage; brown stain on Window wall = owner_responsibility citing the
seeded seepage report; chip on Table top = pre_existing citing the move-in
note; faded Sofa cushion = wear). Use the seeded slot and item IDs looked up
at replay time by slot label. When DEMO_MODE=1, POST /compare replays it
through the same SSE stream with 400–900 ms delays and writes the findings.
```

## Iteration 7B: Agent run screen (the agentic showpiece)

```
Read SPEC §8 (Trace), §11 screen 6 and UI_ITERATIONS.md.
Goal: make the agent's thinking visible and exciting.

1. Top: a "Rakshak AI is inspecting" header with an animated gradient
   orb (pulsing, rotating conic gradient) and a timer.
2. A horizontal strip of slot cards (move-in thumbnail). The slot under
   inspection shows a scanning line sweeping over the photo and a glowing
   border. When done, it flips to show a ClassificationChip.
3. A live trace list (SSE /api/runs/{id}/events): each step slides in, with a
   lucide icon per tool (list_pairs: Layers; inspect_pair: ScanEye;
   get_slot_notes: StickyNote; get_maintenance_reports: FolderSearch; get_item:
   Package; estimate_cost: IndianRupee; record_finding: FilePlus2; flag_retake:
   RefreshCcw; finish: Sparkles). Show the human label in bold, with the
   tool_result summary in muted text underneath. Group parallel calls.
4. Live counters at the bottom: findings so far, ₹ proposed (count-up),
   pairs inspected x/4.
5. On "done": a confetti burst plus a "Report ready" card that auto-navigates
   to the report after 1.5s. On "failed": a friendly error card with Retry.
6. If EventSource errors, fall back to polling the run every 2s.
```
**Check:** the trace streams on the phone through ngrok, with the scanning animation, and the report opens at the end.

---

## Iteration 8: Settlement and share

```
Read SPEC §11 screen 8 and UI_ITERATIONS.md.
1. Hero: "Refund due to Meera" with a big Money count-up in emerald, and the deposit,
   agreed deduction and disputed amounts below.
2. A receipt-style card (dashed divider, perforated edge) listing each charged
   finding with its cost, then the sealed record hashes (move-in and move-out
   lock_hash, short) and both signature times.
3. A language toggle (English | ಕನ್ನಡ) switching the AI summary text.
4. A big "Share on WhatsApp" button (green, WhatsApp-like) opening
   https://wa.me/?text=<encoded summary + totals>. Also "Copy summary".
5. When nothing is disputed: a confetti burst once, and the badge "Settled
   fairly 🤝".
```
**Check:** WhatsApp opens with the Kannada text intact.

---

## Iteration 9: Polish pass (do this before the demo)

```
Read UI_ITERATIONS.md. Polish the whole app for the demo:
1. Backend: SPA fallback, so any non-/api path returns static/index.html (the
   current StaticFiles mount returns 404 when a deep link is refreshed).
2. Every page has a Skeleton loading state, an EmptyState, and a toast on errors
   (no raw "Error loading" text anywhere).
3. Consistent AppShell on every page, with back navigation that makes sense on each screen.
4. An offline banner when navigator.onLine is false.
5. Check every screen at 375px width: no horizontal scroll, text never cut
   off, tap targets at least 48px, safe-area padding at top and bottom.
6. Remove all leftover placeholder text ("implement in F3", IDs shown to the
   user, etc.). Show names and addresses instead of IDs.
7. Add subtle haptics (navigator.vibrate?.(15)) on primary actions.
```

---

## Iteration 10 (stretch): Damage highlight on the photo

```
When a finding has bbox_after, draw an animated rounded rectangle (rose,
pulsing glow) over that region on the move-out photo in the compare slider
and the full-screen viewer, with the change_type label pinned to it.
```

---

## Demo-day checklist for the UI

- [ ] Both phones logged in through the Demo buttons, PWA installed, brightness at maximum
- [ ] `python -m app.seed` run fresh, room staged
- [ ] Rehearse once: owner captures → tenant notes and signs → lock animation → move-out with ghost → AI run → dispute → settlement → WhatsApp
- [ ] `DEMO_MODE=1` fallback tested once
