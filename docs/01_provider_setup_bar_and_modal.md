# Design Spec: Provider Setup Bar & Modal (Phase 2.1)

> **Module**: OpenObserve LLM Observability → Evals → Scorers tab
> **Component**: Cold-start onboarding for built-in LLM Judge Scorers
> **Reference**: Phase 2.1 Cold Start spec §4.4
> **Audience**: Visual designer

---

## 1. Context

OpenObserve ships 8 built-in LLM Judge Scorers as seed data when a user
first visits the Online Eval module (the Evals section in the sidebar).
These scorers come with empty `provider_id` fields — they need a model
provider (OpenAI, Anthropic, etc.) to actually run.

This component guides the user to bind a provider so the built-in
scorers become functional. It has two layers:

- **A setup bar** in the Scorers tab toolbar area — a single-line
  callout that says "you have unconfigured scorers, click here."
- **A modal** that opens when the bar is clicked — offers two paths
  (configure/bind a provider, or add a remote judge server).

The design must honor OpenObserve's visual language: restrained,
information-dense, low decoration, low color saturation.

## 2. Visibility Rules

The setup bar only appears when:

- There are existing built-in scorers in the organization, AND
- None of them are bound to a provider

The moment any one scorer gets bound (via the modal or any other path),
the bar disappears. The bar carries no state — it only reflects the
current data.

There is no "dismiss" button on the bar. The bar is non-blocking; users
who don't want to act on it can simply ignore it.

## 3. Setup Bar

### 3.1 Placement

In the **Scorers tab** of the Evals page. The bar sits in its own
horizontal row, **above the toolbar row** (which contains search,
filters, and the "+ New scorer" button). It spans the full width of
the content area.

The bar pushes the toolbar and table down by its height (approximately
one row, ~48–56px). When the bar disappears (all scorers bound), the
toolbar returns to its normal position.

```
┌─ Scorers tab content area ─────────────────────────────────────────┐
│                                                                     │
│  ┌─── SETUP BAR (this component) ───────────────────────────────┐  │
│  │  ⓘ  Configure provider for built-in scorers              →  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Scorers           [Search...]  [All types ▼]    [+ New scorer]    │
│  ────────────────────────────────────────────────────────────────  │
│  #    NAME                  TYPE         PROVIDER       ...        │
│  01   hallucination          llm_judge    —                         │
│  02   answer_relevance       llm_judge    —                         │
│  ...                                                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Visual Style — "Mid emphasis"

The bar should be noticeable but not jarring. Reference points:

- More visible than a passive status chip
- Less visible than a "warning" alert with high-contrast yellow/orange

**Composition:**

- **Background**: Light blue tint (low saturation, harmonizing with
  OpenObserve's primary deep blue but very pale — think 5–10% opacity
  of the primary color, not a separate hue)
- **Left edge accent**: A solid 4px vertical stripe in OpenObserve's
  primary blue, full height of the bar
- **Border**: None, or extremely subtle (1px in a very light blue if
  needed for separation from the background page)
- **Corner radius**: Match the rest of OpenObserve's UI components
  (table, cards) — typically 4–8px
- **No shadow** (keep with OpenObserve's flat, light feel)

**Content layout:**

- Left-aligned **info icon** (ⓘ), in a tone matching the primary blue
  but slightly lighter
- **Text** immediately to the right of the icon, vertically centered
- **Chevron-right arrow (→)** at the far right, indicating the bar is
  a clickable entry point
- Comfortable horizontal padding (around 16–20px on each end)
- Comfortable vertical padding (around 12–16px top and bottom)

**Hover state:**

- Background tint deepens slightly (e.g., from 5% to 8% opacity of
  primary color) to indicate the whole bar is clickable
- Cursor changes to pointer across the entire bar (not just the arrow)

**Active/pressed state:**

- Background tint deepens a touch more
- Optionally a subtle inset effect

### 3.3 Content

Exact text:

```
ⓘ  Configure provider for built-in scorers                       →
```

- Icon: ⓘ (info symbol)
- Text: "Configure provider for built-in scorers"
- Arrow: → (chevron right) at far right

The text is the same in both Modal Form A and Form B contexts — the
bar doesn't differentiate between "no provider exists" and "providers
exist but unbound." That differentiation happens inside the modal.

### 3.4 Click Behavior

Clicking anywhere on the bar opens the setup modal. The bar itself
does not disappear when the modal opens — it remains in place behind
the modal overlay, so when the user closes the modal, the bar is
still there (assuming the binding state hasn't changed).

## 4. Setup Modal

The modal opens centered on screen with a semi-transparent overlay
behind it (typical modal pattern). It has two structural forms based
on whether the organization has any providers configured.

### 4.1 Common Modal Frame

- **Width**: Around 720–820px (wide enough to hold two side-by-side
  cards comfortably)
- **Max height**: Around 80% of viewport, scrollable if needed (rare
  for this modal — content fits on most screens)
- **Padding**: Generous internal padding (24–32px)
- **Corner radius**: Same as other OpenObserve modals
- **Shadow**: Standard modal elevation shadow
- **Background**: White (or OpenObserve's standard modal background)
- **Overlay**: Standard modal overlay (typically 30–50% black opacity)

**Header:**

- Title at top-left
- ✕ close button at top-right
- Optional thin separator line below header

**No Cancel button at the bottom** — the ✕ in the header serves as
the dismiss path.

### 4.2 Modal Form A — Organization Has No Providers

This form appears when the user clicks the setup bar and the
organization currently has zero providers configured.

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Set up scorer provider                                          ✕  │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                      │
│  The built-in LLM Judge scorers need a model provider to run.       │
│  Choose how to set them up:                                          │
│                                                                      │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐ │
│  │                               │  │                               │ │
│  │  Configure a model provider  │  │  Add a Remote Judge Server   │ │
│  │                               │  │                               │ │
│  │  Connect OpenAI, Anthropic,  │  │  Run a self-hosted judge     │ │
│  │  or a compatible provider.   │  │  server with no data leaving │ │
│  │  All built-in scorers will   │  │  your environment.            │ │
│  │  be bound to it              │  │  Recommended for air-gapped  │ │
│  │  automatically.               │  │  deployments.                 │ │
│  │                               │  │                               │ │
│  │                               │  │                               │ │
│  │  [ Configure Provider → ]    │  │  [ Add Remote Server → ]     │ │
│  │                               │  │                               │ │
│  └──────────────────────────────┘  └──────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Title**: `Set up scorer provider`

**Intro paragraph** (below the header separator):

```
The built-in LLM Judge scorers need a model provider to run. Choose how to set them up:
```

**Two side-by-side option cards** (equal width, equal visual weight):

#### Card A1: "Configure a model provider"

- **Card title** (bold): `Configure a model provider`
- **Card body**: `Connect OpenAI, Anthropic, or a compatible provider. All built-in scorers will be bound to it automatically.`
- **Card button**: `Configure Provider →` (secondary outlined button)
- Click: navigates user away to the Provider creation page. The modal
  closes when navigation happens. No return-flow is maintained — user
  finds their own way back.

#### Card A2: "Add a Remote Judge Server"

- **Card title** (bold): `Add a Remote Judge Server`
- **Card body**: `Run a self-hosted judge server with no data leaving your environment. Recommended for air-gapped deployments.`
- **Card button**: `Add Remote Server →` (secondary outlined button)
- Click: closes this modal, opens the Quick Setup modal (separate
  component, designed in a sibling spec).

### 4.3 Modal Form B — Organization Has Providers but Scorers Unbound

This form appears when the user clicks the setup bar and the
organization has at least one provider configured (so the user has
done the "create provider" step already, just hasn't bound it to
built-in scorers yet).

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Set up scorer provider                                          ✕  │
│                                                                      │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                      │
│  The built-in LLM Judge scorers are not bound to a provider.        │
│  Choose how to set them up:                                          │
│                                                                      │
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐ │
│  │                               │  │                               │ │
│  │  Bind an existing provider   │  │  Add a Remote Judge Server   │ │
│  │                               │  │                               │ │
│  │  Select one of your          │  │  Run a self-hosted judge     │ │
│  │  configured providers and    │  │  server with no data leaving │ │
│  │  bind it to all built-in     │  │  your environment.            │ │
│  │  scorers at once.            │  │  Recommended for air-gapped  │ │
│  │                               │  │  deployments.                 │ │
│  │                               │  │                               │ │
│  │  Provider                    │  │                               │ │
│  │  ┌─────────────────────────┐ │  │                               │ │
│  │  │ Select provider     ▼  │ │  │                               │ │
│  │  └─────────────────────────┘ │  │                               │ │
│  │                               │  │                               │ │
│  │  [ Bind to all scorers ]    │  │  [ Add Remote Server → ]     │ │
│  │                               │  │                               │ │
│  └──────────────────────────────┘  └──────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Title**: `Set up scorer provider`

**Intro paragraph**:

```
The built-in LLM Judge scorers are not bound to a provider. Choose how to set them up:
```

(Note the subtle difference from Form A: "are not bound to a provider"
vs "need a model provider to run". This phrasing acknowledges that the
user has already set up providers — they just need to bind them.)

#### Card B1: "Bind an existing provider"

- **Card title** (bold): `Bind an existing provider`
- **Card body**: `Select one of your configured providers and bind it to all built-in scorers at once.`
- **Inline form element**: a labeled dropdown
  - **Label**: `Provider`
  - **Dropdown placeholder**: `Select provider`
  - **Dropdown options**: list of all providers in the org, formatted as
    `<provider_name> (<provider_type>)`, e.g.:
    - `OpenAI Production (openai)`
    - `Local Llama (openai_compatible)`
    - `Anthropic Claude (anthropic)`
  - **Sort order**: alphabetical by provider name
- **Card button**: `Bind to all scorers` (primary solid button, in
  OpenObserve's primary blue)
- **Button disabled state**: when no provider is selected in the
  dropdown, the button is disabled (grayed out, non-clickable)
- **Button loading state**: when clicked, button shows a loading
  spinner until the bind operation completes
- Click (when enabled): executes batch bind on the backend, closes
  modal, shows toast, refreshes the scorer list. The setup bar
  disappears because the visibility condition is no longer met.

#### Card B2: "Add a Remote Judge Server"

Identical to Card A2 in Form A.

### 4.4 After Successful Bind (Form B)

The modal closes. A toast appears for ~3 seconds at the standard toast
position (typically top-right or bottom-right per OpenObserve's
existing toast convention):

```
8 scorers bound to OpenAI Production
```

The `8` is the actual count of scorers updated (always 8 in a fresh
seed state, but might be different in edge cases — show the actual
count returned by the backend). The `OpenAI Production` is the name
of the provider the user selected.

The scorer list refreshes to reflect the new `provider` values. The
setup bar is gone.

### 4.5 Modal Close Behavior

The ✕ button in the header closes the modal without any side effects
in either Form A or Form B. The setup bar remains visible (because the
underlying state hasn't changed). User can click the bar again
anytime to reopen the modal.

Pressing Escape key has the same effect as clicking ✕.

Clicking outside the modal (on the overlay) also closes the modal —
this is standard OpenObserve modal behavior, not a special case.

## 5. State Diagram

```
Scorers tab loaded
       │
       ▼
  ┌──────────────────────────────────────────┐
  │  Check: has_scorers AND all_unbound?     │
  └──────────────────────────────────────────┘
       │
       ├──── No ────→ No setup bar shown
       │
       └──── Yes ───→ Setup bar shown
                          │
                          │ (user clicks bar)
                          ▼
                  ┌────────────────────────┐
                  │  Check: total_providers │
                  └────────────────────────┘
                          │
              ┌───────────┴────────────┐
              │                         │
              ▼                         ▼
        total = 0                  total > 0
              │                         │
              ▼                         ▼
       Modal Form A              Modal Form B
              │                         │
        ┌─────┴─────┬─────┐       ┌─────┴────────┬──────┐
        │           │     │       │              │      │
        ▼           ▼     ▼       ▼              ▼      ▼
   Configure   Add Remote ✕   Bind (select  Add Remote ✕
   Provider    Server         provider +    Server
   (navigate)  (open Quick    confirm)      (open Quick
               Setup modal)   │             Setup modal)
                              ▼
                          Backend bind
                          + toast
                          + refresh list
                          + bar disappears
```

## 6. Edge Cases

### 6.1 Provider deleted while modal is open

User opens Form B modal, sees one provider in the dropdown. While
their modal is open, another tab/user deletes that provider. User
selects it and clicks Bind — backend returns an error.

**Handling**: Show inline error message in the card, near the button:
"Selected provider no longer exists. Refresh and try again." Don't
auto-refresh — let the user reopen.

### 6.2 All scorers were deleted while bar is shown

User in tab A is looking at the setup bar (8 unbound scorers). In tab
B they delete all scorers. Tab A's bar is still visible because it
hasn't refreshed.

**Handling**: not a critical case. Next refresh of tab A will hide the
bar. No real-time sync needed.

### 6.3 Click bar, then state changes before modal opens

Extremely rare race condition. Modal opens with whatever state was
detected at click time. If user tries to bind and the state has
changed (e.g., scorers got deleted), backend returns "no scorers to
bind" — show error message.

### 6.4 Provider dropdown is empty in Form B

Shouldn't happen by definition (Form B is shown precisely because
providers exist). If somehow shown empty, dropdown disabled, button
disabled, no inline error needed — the situation will resolve itself
on next refresh which will switch to Form A.

## 7. Accessibility

- The setup bar must be keyboard-accessible: focusable, with Enter
  triggering the modal-open action
- Modal traps keyboard focus while open
- ✕ button has appropriate aria-label (`Close dialog`)
- Provider dropdown is a proper combobox with full keyboard navigation
- Modal title is associated with the modal via aria-labelledby
- The info icon in the bar has an accessible name ("Setup notice")

## 8. Responsive Behavior

OpenObserve is primarily a desktop application. For viewport widths
narrower than ~720px:

- The setup bar remains a single horizontal row but text may truncate
  with ellipsis (preserve the arrow on the right)
- The modal cards stack vertically instead of side-by-side
- Modal width becomes ~95% viewport width

For viewport widths above 720px, the two-card horizontal layout is
the canonical presentation.

## 9. Out of Scope

This spec does **not** cover:

- The "Add Remote Judge Server" flow (Quick Setup) — that is a
  separate component with its own multi-step modal, designed in a
  sibling spec
- The Provider creation page itself — that already exists in
  OpenObserve and is reused here without modification
- The Scorer list / table styling — this spec assumes the existing
  Scorer table renders normally below the setup bar
- Any per-scorer provider editing — that happens in scorer detail
  views, separate from this onboarding flow

## 10. Mockup Deliverables Requested

From this spec, produce mockups for:

1. **Setup bar — default state** (within the Scorers tab context)
2. **Setup bar — hover state**
3. **Modal Form A — full layout** (no providers)
4. **Modal Form B — full layout, dropdown closed** (providers exist)
5. **Modal Form B — dropdown open, showing 3+ provider options**
6. **Modal Form B — Bind button in loading state**
7. **Toast — success state, "8 scorers bound to OpenAI Production"**
8. **(Optional) Modal cards stacked vertically — narrow viewport**

For each mockup:

- Show the immediate surrounding context (page header, tabs, sidebar
  if applicable) so placement is unambiguous
- Light theme only (OpenObserve has unified dark mode handling, not in
  scope for this design pass)
- Pixel-precise spacing, colors aligned to OpenObserve's existing
  design system

## 11. Reference Screenshot

The Scorers tab lives within the Evals section. For the surrounding
visual context (sidebar, page header, tab strip, table style), refer
to the existing Evals page screenshot supplied with this spec.

Key visual cues from the reference:

- Sidebar with icon + label, "Evals" item active
- Page header: "Evaluations" h1 + small gray description
- Tab strip: Quality / Jobs / Scorers / Score Configs, with count
  badges
- Toolbar row: section title on the left, search/filters/primary
  action on the right
- Table style: minimal borders, status chips with low-saturation
  colors, action icons (pencil, trash) on the right

The setup bar should fit naturally into this language — feel like it
belongs in the same product, not like it was bolted on.
