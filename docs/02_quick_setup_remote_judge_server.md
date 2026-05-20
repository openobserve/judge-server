# Design Spec: Quick Setup — Add Remote Judge Server (Phase 2.1)

> **Module**: OpenObserve LLM Observability → Evals → Scorers tab
> **Component**: Multi-step modal for bulk-creating Remote Scorers
>   pointing at a self-hosted judge server
> **Reference**: Phase 2.1 Cold Start spec §4.5
> **Sibling component**: Provider Setup Bar & Modal (see
>   `01_provider_setup_bar_and_modal.md`)
> **Audience**: Visual designer

---

## 1. Context

OpenObserve ships a separate reference implementation called
`openobserve/eval-judges` — a Docker-deployable HTTP server that
implements OpenObserve's Remote Scorer protocol. This server lets
users run LLM evaluation entirely within their own environment (no
data leaving), which is the strategic value behind this feature.

This **Quick Setup modal** lets users bulk-create up to 8 Remote
Scorers, each pointing at a running instance of the reference server,
in one streamlined flow — instead of creating each scorer manually
through the standard "+ New scorer" path.

Conceptually the modal does three things, all in a single screen:

1. Tell the user how to deploy the server (Docker command snippet)
2. Collect connection details (URL, auth token)
3. Create scorers one by one with real-time progress feedback

The flow uses **streaming sequential execution** — when the user
clicks Create, scorers are created one at a time with live status
updates, not batched into a single request. This gives onboarding
users a visible sense of progress and stops cleanly on the first
failure.

## 2. Entry Points

The modal opens from:

1. The Provider Setup Modal's "Add Remote Server →" button (in either
   Card A2 or Card B2 — see sibling spec)
2. A persistent "Quick setup" link/button in the Scorers tab toolbar,
   visible at all times next to "+ New scorer"
3. Direct URL navigation (a Quick Setup deeplink in docs)

All three open the same modal in the same initial state.

## 3. Modal Frame

- **Single modal**, all sections stacked vertically (not a wizard,
  no Step 1/2/3 indicator, no Back/Next buttons)
- **Width**: ~720–820px (same as Provider Setup Modal for visual
  consistency)
- **Max height**: ~85% viewport, internal scroll if content overflows
- **Padding**: 24–32px internal padding
- **Corner radius, shadow, overlay**: same as Provider Setup Modal
- **Header**: title at top-left, ✕ close at top-right, thin separator
  line below header
- **No Cancel button at bottom** (✕ in header is the dismiss path)
- **No bottom-right primary action button** in the default state — the
  Create button lives at the bottom of Section 3 (Scorer Selection)

## 4. Three Sections (Vertically Stacked)

The modal has three sections, vertically stacked, each clearly
separated. The user fills them top-to-bottom.

### Section 1 — Deploy the Server

The first thing a new user needs to know: "you need to start the
server first." This section shows a Docker command they can copy and
run.

**Content:**

```
Start the reference judge server in your environment.
Already running? Skip to connection details below.

┌────────────────────────────────────────────────────────────────┐
│  docker run -d \                                               │
│    -p 8000:8000 \                                              │
│    -e O2_JUDGE_PROVIDER=openai \                               │
│    -e O2_JUDGE_API_KEY=sk-... \                                │
│    -e O2_JUDGE_MODEL=gpt-4o-mini \                             │
│    openobserve/eval-judges:latest                              │
└────────────────────────────────────────────────────────────────┘
                                                  [ Copy command ]

Using a local model or different provider? See deployment guide →
```

**Composition:**

- **Intro line** (regular text): `Start the reference judge server
  in your environment.`
- **Skip hint** (smaller, lighter text): `Already running? Skip to
  connection details below.`
- **Code block**:
  - Monospace font
  - Dark background (OpenObserve's standard code block style — if
    one exists; otherwise a light gray background works too)
  - Subtle border or rounded corners
  - Comfortable padding inside the block
  - The command shown above is the canonical OpenAI version — this
    is what most users will start with
- **Copy command button**:
  - Positioned at top-right or bottom-right of the code block (per
    OpenObserve convention for code blocks)
  - Secondary outlined button, small size
  - Click: copies the entire command text to clipboard
  - Brief tooltip/toast "Copied!" on click
- **Deployment guide link** (regular text + link):
  - `Using a local model or different provider? See deployment guide →`
  - Link points to the `openobserve/eval-judges` README on GitHub
  - The link arrow → is small and inline (not a button)

**Why no Mode X / Mode Y tabs:** The difference between using OpenAI
vs a local model is just different environment variables. Splitting
them into tabs would over-emphasize this as a product-level choice.
A single canonical command + a link to the README covers both cases
without ceremony.

### Section 2 — Connection Details

```
Server URL    [ http://localhost:8000                    ]
Auth token    [ ************                         👁  ]
              [ Test connection ]
              ✓ Connected. Server v0.1.2
```

**Composition:**

- **Server URL** field:
  - Label: `Server URL`
  - Placeholder: `http://localhost:8000`
  - Standard text input
  - Validation: must be a non-empty URL-like string; do NOT force
    https (air-gapped users routinely use http for internal services)
- **Auth token** field:
  - Label: `Auth token`
  - Standard password-style input (masked by default)
  - 👁 icon button at right edge of input to toggle visibility
  - Validation: must be non-empty
- **Test connection** button:
  - Secondary outlined button
  - Disabled until both URL and token are non-empty
  - Click: calls `GET <server>/health` with the provided token
- **Test result** displayed on a new line below the button:
  - Default state: hidden (no message)
  - Testing state: `⟳ Testing connection...` (spinner + text)
  - Success: `✓ Connected. Server v0.1.2` (green check icon, neutral
    or success color text)
  - Failure variants:
    - `✗ Authentication failed (401). Check the token.` (red ✗ icon,
      error color text)
    - `✗ Could not reach server. Check the URL and that the server
      is running.`
    - `✗ Server returned an unexpected response.` (for malformed
      responses)
    - `✗ Connection timeout.`
  - One-line result is sufficient; no large error blocks
- **No "recommended to test first" hint** — the button's presence is
  enough

**Important:** Test connection is **optional**, not gating. The
Create button in Section 3 can be clicked without successfully
testing first.

### Section 3 — Scorer Selection

Lists the 8 built-in span dimensions. User selects which to create
as Remote Scorers.

**Composition:**

- **Section heading**: `Scorers to create`
- **Default mode** (collapsed list, shows a summary line + toggle):

  ```
  Scorers to create
  ☑ All 8 scorers (default)        [ Select individually ]
  ```

  - "All 8 scorers (default)" is a labeled checkbox, default checked
  - "Select individually" is a text link/button on the same row
  - Click "Select individually" → expand to show the full list

- **Expanded mode** (after clicking "Select individually"):

  ```
  Scorers to create
  ☑ hallucination          → will create "hallucination_remote"
  ☑ answer_relevance       → will create "answer_relevance_remote"
  ☑ coherence              → will create "coherence_remote"
  ☑ helpfulness            → will create "helpfulness_remote"
  ☑ instruction_following  → will create "instruction_following_remote"
  ☑ toxicity               → will create "toxicity_remote"
  ☑ bias                   → will create "bias_remote"
  ☑ output_format          → will create "output_format_remote"

  [ Select all ]  [ Clear all ]               [ Collapse ▲ ]
  ```

  Each row:
  - Checkbox
  - Dimension name (e.g., `hallucination`)
  - Arrow `→`
  - Resulting scorer name in quotes (e.g., `"hallucination_remote"`)
  - The arrow and result-name use a slightly lighter/muted text color
    than the dimension name

  Below the list:
  - `Select all` and `Clear all` text links on the left
  - `Collapse ▲` link on the right to return to the default
    collapsed mode

**Already-existing scorers**:

If any of the 8 scorer names (`hallucination_remote`, etc.) already
exist in the org (perhaps from a previous Quick Setup attempt or
manual creation), they appear in the expanded list as:

```
☐ toxicity               → "toxicity_remote" already exists
```

- Checkbox is **disabled** (not just unchecked — visually grayed out
  and unclickable)
- Text after `→` reads: `"<scorer_name>" already exists` in lighter
  text
- The dimension name is also dimmed
- These rows are skipped in the create flow — they don't appear in
  the progress list

The collapsed-mode summary line accounts for this: if 3 scorers
already exist, the default summary reads `All 5 available scorers
(default)` instead of `All 8 scorers`.

**Create scorers button** (at bottom of Section 3):

```
[ Create scorers ]
```

- Primary solid button, in OpenObserve's primary blue
- Disabled when:
  - URL or token in Section 2 is empty
  - No scorer is checked in Section 3
- Enabled otherwise
- Click: transitions modal into Execution Mode (see Section 5)

## 5. Execution Mode

Once the user clicks "Create scorers", the modal transitions into a
new visual state. This is the streaming execution view.

### 5.1 Transition

- Section 1 (Docker command) and Section 2 (Connection) become
  **visually disabled** — fields grayed out and uneditable, but
  still visible so the user has context
- The optional approach: collapse Sections 1 and 2 into thin headers
  showing just the section title and a `▼` to expand (read-only).
  Either way, focus shifts to Section 3
- Section 3's scorer list **transforms** into a progress list:
  checkboxes disappear, each row gets a status icon
- Section header changes from `Scorers to create` to
  `Creating scorers...`

### 5.2 Progress List Visual States

Each scorer row has a status icon and a status label.

**Pending** (waiting to be processed):

```
⏳  hallucination_remote
```

- Icon: hourglass or empty circle (something signaling "queued")
- Text color: muted/gray

**In progress** (currently being created):

```
⟳  answer_relevance_remote                creating...
```

- Icon: spinner (animated rotation)
- Text color: normal
- Suffix label: `creating...` in lighter text

**Success**:

```
✓  hallucination_remote                   created
```

- Icon: green check
- Text color: normal
- Suffix label: `created` in lighter text

**Failed**:

```
✗  toxicity_remote                        Connection timeout
```

- Icon: red ✗
- Text color: normal (dimension name)
- Suffix label: short error description in error color (red)

The list animates row-by-row as execution proceeds. Visually, the
user sees ⏳ → ⟳ → ✓ for each row in sequence.

### 5.3 Sequence

Execution is **strictly sequential**:

1. Frontend has a queue of N selected scorers (already-existing ones
   excluded)
2. Frontend sends `POST /scorers` for the first one
3. On response (success or failure), update the row's status icon
4. If success, move to the next; if failure, stop and show error UI
5. Repeat until queue is exhausted or a failure happens

This means total time is ~`200ms × N`. For 8 scorers, ~1.6 seconds —
acceptable for an onboarding flow, and the progressive feedback is
worth the time.

### 5.4 Failure State

When any scorer fails, execution stops immediately. The failed row
shows the ✗ state with a short error suffix. Below the progress
list, a detailed error block appears:

```
✓  hallucination_remote                   created
✓  answer_relevance_remote                created
✓  coherence_remote                       created
✓  helpfulness_remote                     created
✓  instruction_following_remote           created
✗  toxicity_remote                        Connection timeout
⏳  bias_remote
⏳  output_format_remote

────────────────────────────────────────────────────

Stopped due to error.

The server timed out while creating toxicity_remote. Check the
server is reachable and try again.

[ Retry ]      [ Cancel ]
```

**Detailed error block** (below the progress list, above the
buttons):

- Section title: `Stopped due to error.` (one bold line)
- Detailed description: 1–2 sentences explaining what happened and
  suggested action
- Error description varies by error type:
  - 401: `The server rejected the authentication token. Check the
    token value and try again.`
  - Network timeout: `The server timed out while creating
    {scorer_name}. Check the server is reachable and try again.`
  - Connection refused: `Could not connect to the server. Check the
    URL and that the server is running.`
  - 5xx server errors: `The server returned an error
    (HTTP {status}). Check server logs and try again.`
  - Unexpected response shape: `The server returned an unexpected
    response. This may be a version mismatch.`
  - Other: `An unexpected error occurred: {message}`

**Buttons**:

- `[ Retry ]` — secondary outlined or primary outlined button
- `[ Cancel ]` — text button (lowest visual weight)

### 5.5 Retry Behavior

Click Retry:

- Resumes execution from the **failed scorer onward** (does NOT
  re-process successfully-created ones)
- The failed row's status icon goes back to ⟳ (in progress)
- Error block disappears
- Subsequent rows proceed normally

Retry uses the **current URL and token** in Section 2. The user
cannot modify URL/token while in Execution Mode. If they need to
change credentials, they must Cancel and reopen Quick Setup.

### 5.6 Cancel Behavior

Click Cancel (or ✕, or Escape):

- Frontend aborts the in-flight request, if any
- Modal closes immediately
- No confirmation dialog
- Already-created scorers remain in the database (they're committed
  individually, no rollback)
- No toast appears (the user saw the partial state inside the modal;
  a toast would be redundant)

If the user opens Quick Setup again afterward, the previously-created
scorers will appear as `already exists` in the Scorer Selection
section.

### 5.7 Success State (All Created)

When the last scorer succeeds:

```
✓  hallucination_remote                   created
✓  answer_relevance_remote                created
✓  coherence_remote                       created
✓  helpfulness_remote                     created
✓  instruction_following_remote           created
✓  toxicity_remote                        created
✓  bias_remote                            created
✓  output_format_remote                   created

────────────────────────────────────────────────────

All 8 scorers created successfully.

[ Done ]
```

**Completion block**:

- Confirmation line: `All N scorers created successfully.` (where N is
  the actual count of successful creations)
- Single button: `[ Done ]` — primary solid

Click Done:

- Modal closes
- Scorer list (the table below) refreshes to show the newly created
  scorers
- The new scorers are visually highlighted in the table for ~3–5
  seconds (a background color flash, or a "new" indicator that fades)
- Toast appears at the standard position: `N remote scorers created`
  (e.g., `8 remote scorers created`)

## 6. State Diagram

```
Modal opened
    │
    ▼
Initial state
   - Section 1 (Docker): expanded, copy + link visible
   - Section 2 (Form): empty, Test connection disabled
   - Section 3 (Scorers): collapsed default mode
   - Create button: disabled
    │
    │ (user fills URL + token, optionally tests connection,
    │  optionally expands and selects/deselects scorers)
    ▼
Ready state
   - URL + token non-empty
   - At least one scorer checked
   - Create button: enabled
    │
    │ (click Create)
    ▼
Execution mode
   - Sections 1 + 2 disabled (read-only)
   - Section 3 transformed to progress list
   - Sequential creation begins
    │
    ├──── Each scorer succeeds: row turns ✓, next starts
    │
    ├──── A scorer fails: row turns ✗, execution stops
    │           │
    │           ├──── User clicks Retry → resume from failed
    │           ├──── User clicks Cancel → close modal, keep created
    │           └──── User clicks ✕ / Esc → same as Cancel
    │
    └──── All scorers succeed → Success state with Done button
                                      │
                                      └─→ Click Done → close + refresh + toast
```

## 7. Behavior Detail: "Already Exists" Handling

This handling is purely UI — the actual create endpoint will return
a unique-violation error if it tries to create a duplicate, but the
frontend should prevent that by pre-filtering.

**On modal open**:

- Frontend fetches the current list of scorers in the org
- Checks which of the 8 canonical scorer names already exist
- Marks those rows in Section 3 as "already exists, disabled"
- The default summary line reflects the count: `All N available
  scorers (default)` where N = 8 − existing_count

**During execution**:

- Already-existing scorers are never in the queue
- They don't appear in the progress list
- If somehow a unique-violation occurs anyway (race condition with
  another tab/user creating a scorer), it appears as a failure with
  error description: `A scorer with this name already exists.
  Refresh and try again.`

## 8. Edge Cases

### 8.1 User has all 8 scorers already

- Section 3 default summary: `All scorers already exist. Nothing to
  create.`
- Create button: disabled with tooltip `All scorer names are already
  in use`
- Section 3 expanded view shows all 8 rows as "already exists"
- The user can still use the modal to test connection (informational
  value), but cannot create anything

### 8.2 Test connection succeeds but Create fails on first scorer

- This is rare (health check passes but create endpoint errors), but
  possible (e.g., the `/evaluate` endpoint has a different auth model)
- Treated as normal failure — show ✗, error block, Retry/Cancel

### 8.3 User edits URL/token after a partial execution

- Cannot happen in current design — Section 2 is read-only during
  Execution Mode
- To change them, user must Cancel and reopen Quick Setup

### 8.4 User opens Quick Setup, then provider gets deleted in another tab

- Quick Setup doesn't depend on providers (Remote Scorers don't use
  providers — they use the remote server's auth)
- No impact on this flow

### 8.5 Network failure mid-execution

- Same as any other failure — row turns ✗ with appropriate error
- User can Retry once network is back

### 8.6 Browser tab closed/refreshed during execution

- All committed scorers remain
- Modal state is lost (no persistence)
- On next visit, the partial state is visible in the Scorer list and
  in Quick Setup's "already exists" markers

## 9. Accessibility

- All sections keyboard-navigable in top-to-bottom order
- Test connection result is announced to screen readers (use ARIA
  live region for the result line)
- Progress list updates announced to screen readers as each row
  changes state (ARIA live region)
- Error block uses appropriate ARIA role (`alert` or `status`)
- ✕ button has accessible name (`Close dialog`)
- Code block content is selectable for users who prefer to copy
  manually rather than use the Copy button
- Modal traps focus while open

## 10. Responsive Behavior

OpenObserve is primarily desktop. For narrow viewports (<720px):

- Modal width becomes ~95% viewport
- Code block in Section 1 stays as-is but allows horizontal scroll
  (don't wrap the Docker command)
- Connection form fields stack normally
- Scorer Selection rows keep their layout (dimension name + arrow +
  result name fit on one line on most widths; if they don't,
  result name wraps to second line)
- Progress list rows similarly fit on one line

## 11. Visual Style Cohesion

Reference: Phase 2.1 Provider Setup Bar & Modal sibling spec, and
the existing OpenObserve Evaluations page screenshot.

This Quick Setup modal should feel like it shares its DNA with:

- The Provider Setup Modal: same modal frame (width, padding, header
  style, ✕ position), same card-driven structure where applicable
- The Evaluations page: same low-saturation status chip colors, same
  table-like alignment for the progress list, same typography scale

Where Quick Setup is necessarily different:

- Has a code block (Section 1) — OpenObserve may already have a code
  block style elsewhere (e.g., in docs or API examples). Reuse that.
- Has live progress updates (Section 5) — the spinner/check/cross
  icons should match whatever icon set OpenObserve uses (Quasar
  icons, Heroicons, or custom)
- Has form fields (Section 2) — these should match existing
  OpenObserve form field styles (input + label patterns)

## 12. Out of Scope

This spec does **not** cover:

- The Provider Setup Bar & Modal (sibling spec)
- The Scorer table itself
- Single-scorer creation via "+ New scorer" — that's a separate,
  existing flow
- The reference judge server's API/implementation details — only the
  client-side modal is covered here
- Editing existing Remote Scorers — handled by clicking into a
  scorer's detail page

## 13. Mockup Deliverables Requested

From this spec, produce mockups for:

1. **Initial state** — modal just opened, all sections visible, form
   empty, Create button disabled
2. **Section 1 detail** — Docker command block with Copy button and
   deployment guide link
3. **Section 2 detail** — connection form with successful Test
   connection result
4. **Section 2 detail — error variants** — show 2–3 different failure
   states of Test connection (401, network error, timeout)
5. **Section 3 collapsed default mode** — "All 8 scorers (default)"
   summary
6. **Section 3 expanded mode** — all 8 rows visible with their
   resulting names
7. **Section 3 expanded mode with "already exists" rows** — some rows
   disabled with "already exists" labels
8. **Execution mode — mid-execution** — Sections 1+2 disabled,
   progress list showing 3 ✓, 1 ⟳, 4 ⏳
9. **Execution mode — failure state** — progress list with mixed ✓ and
   ✗, error block visible, Retry/Cancel buttons
10. **Execution mode — all success** — all ✓, "All 8 scorers created
    successfully." line, Done button
11. **Success toast** — final toast appearance after Done

For each mockup:

- Show the immediate context (the modal in its overlay, with the
  Scorers tab visible behind the overlay)
- Light theme only (OpenObserve has unified dark mode handling)
- Pixel-precise spacing, colors aligned to OpenObserve's existing
  design system
