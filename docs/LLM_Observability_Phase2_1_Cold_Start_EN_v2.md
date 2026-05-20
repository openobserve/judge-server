# OpenObserve LLM Observability · Phase 2.1 Design Specification v2

> **Module**: Cold Start — Built-in Score Configs, Built-in LLM Judge Scorers, Reference Remote Judge Server
>
> **Version**: v2.0 (2026-05-19, full rewrite)
> **Status**: Implementation specification, pending review
> **Predecessor document**: [Phase 2 Online Eval Spec v1.3](./LLM_Observability_Phase2_Online_Eval_v1_3_EN.md)
> **Sub-documents referenced by this spec**:
> - [01_provider_setup_bar_and_modal.md](./01_provider_setup_bar_and_modal.md) — Visual design of the Provider setup bar and Modal
> - [02_quick_setup_remote_judge_server.md](./02_quick_setup_remote_judge_server.md) — Visual design of the Quick Setup flow
> - [03_builtin_score_configs_and_scorers.md](./03_builtin_score_configs_and_scorers.md) — Full definitions of built-in Score Configs and Scorers

---

## §0 Overview

Phase 2.1 adds three coordinated capabilities on top of the already-released Phase 2.0 Online Eval module, together solving the **cold-start problem of an empty list** that new users face when they first enter the Online Eval module:

1. **Built-in Score Configs (12) + built-in LLM Judge Scorers (8)** as seed data, inserted into the database the first time an organization accesses the Online Eval module. Full inventory and prompts in [sub-doc 03](./03_builtin_score_configs_and_scorers.md).
2. **Provider setup bar + Modal**, shown when a user's built-in LLM Judge Scorers lack a Provider, guiding the user to bind one. Visual design in [sub-doc 01](./01_provider_setup_bar_and_modal.md).
3. **Quick Setup flow** that lets the user create 8 Remote Scorers at once through a single Modal, pointing to a Remote Judge Server the user deploys themselves (independent repository `openobserve/eval-judges`). Visual design in [sub-doc 02](./02_quick_setup_remote_judge_server.md); the reference server's implementation goals and API definition are in §4 of this document.

### Core design principles

- **Built-in data = ordinary data.** Once built-in Score Configs and Scorers are inserted into an organization's database, they are completely indistinguishable from user-created objects. No `built_in` column, no UI marker, no special API. Users can delete, modify, or replace them.
- **No guidance state is maintained.** Whether the Banner is shown and which form of the Modal is displayed are fully determined by the current database state. Every visit is judged independently. No dismiss flag, no return tracking.
- **No schema changes.** Reuses Phase 2.0's `score_config`, `scorer`, and `meta` tables. The new "has been seeded" flag is written into the `settings` JSON column of the `meta` table.
- **Phase 2.0 is purely additive.** No Phase 2.0 product object, table, or behavior is modified.

---

## §1 Interaction Design

This section describes the **state determination logic and transitions** of the three components: Banner, Provider setup Modal, and Quick Setup Modal. For visual details, copy, component hierarchy, mockups, etc., see [sub-doc 01](./01_provider_setup_bar_and_modal.md) and [sub-doc 02](./02_quick_setup_remote_judge_server.md).

### §1.1 Global state variables

The guidance logic depends on the following three queries, **recomputed every time the Scorers tab is entered**:

```sql
-- A. Total Scorer count and count of Scorers without a Provider, in the org
SELECT
  COUNT(*) AS scorers_total,
  COUNT(*) FILTER (WHERE provider_id IS NULL) AS scorers_unbound
FROM scorer
WHERE org_id = $org_id;

-- B. Total Provider count in the org
SELECT COUNT(*) AS providers_total
FROM provider
WHERE org_id = $org_id;
```

Derived values:

| Derived value | Computation | Meaning |
|---|---|---|
| `has_scorers` | `scorers_total > 0` | Whether the org has any Scorers |
| `all_unbound` | `scorers_unbound = scorers_total` | Whether all Scorers are unbound from a Provider |
| `has_providers` | `providers_total > 0` | Whether the org has any Providers |

### §1.2 Banner display determination

**Banner display condition**:

```
show_banner = has_scorers AND all_unbound
```

That is: **the Banner is shown if and only if the org has at least one Scorer AND every Scorer is missing a Provider**.

Why "all unbound" rather than "any unbound": the Banner's purpose is cold-start guidance. Once the user has bound any one Scorer, they've grasped the workflow and no longer need guidance. The Banner is not shown in half-completed states (if remaining Scorers are unbound, the user can handle them via the Scorer detail page).

**Banner location**: Inside the Scorers tab, on its own row above the toolbar (Search, Filter, + New scorer), spanning the full content area width.

**Banner content**: Single line of text + right-side arrow; the whole row is clickable. Clicking opens the Provider setup Modal.

**Dismissal mechanism**: The Banner carries no close button. It is shown when the state condition is met and disappears naturally when the state changes (any Scorer is bound to a Provider).

Detailed visual spec is in [sub-doc 01 §3](./01_provider_setup_bar_and_modal.md#3-setup-bar).

### §1.3 Provider setup Modal

Opens when the user clicks the Banner. Two forms based on `has_providers`:

| Condition | Modal form | Primary options |
|---|---|---|
| `has_providers = false` (no Providers in org) | **Form A** | "Configure a model provider" (navigate away, create Provider) / "Add a Remote Judge Server" (open Quick Setup) |
| `has_providers = true` (org has Providers) | **Form B** | "Bind an existing provider" (inline dropdown to pick a Provider and bulk-bind) / "Add a Remote Judge Server" (open Quick Setup) |

Both forms are two side-by-side cards of equal width and equal visual weight. ✕ in the top-right corner of the Modal closes it.

**Form A key interactions**:

- Click "Configure Provider →" → navigate to the Provider creation page, Modal closes. **No return state is maintained** — the user returns to the Scorers tab on their own after creating the Provider.
- Once back on the Scorers tab, since `has_providers` is now true, the Banner is still shown (`all_unbound` is still true), but clicking it now opens Form B.
- This is a "two-journey" design: first create the Provider, then bind it to Scorers. Each journey is independent and complete; no intermediate state.

**Form B key interactions**:

- The card contains an inline Provider dropdown listing all Providers in the org (sorted by name alphabetically).
- After selecting a Provider and clicking "Bind to all scorers", the backend executes a bulk update:
  ```sql
  UPDATE scorer
  SET provider_id = $selected_provider_id, updated_at = NOW()
  WHERE org_id = $org_id AND provider_id IS NULL;
  ```
- Modal closes, the Scorer list refreshes, and a brief toast appears at the top: `{N} scorers bound to {provider_name}`.
- The Banner disappears naturally (`all_unbound` becomes false).

**The right-hand card is identical in both forms**: "Add a Remote Judge Server" → closes the current Modal and opens the Quick Setup Modal.

Detailed visual spec, copy, and edge cases are in [sub-doc 01 §4](./01_provider_setup_bar_and_modal.md#4-setup-modal).

### §1.4 Quick Setup Modal

The Quick Setup Modal lets the user **create 8 Remote Scorers at once**, each pointing to the user-deployed reference Remote Judge Server.

**Entry points**:
1. The "Add Remote Server →" button on the right-hand card of the Provider setup Modal
2. A permanent entry on the Scorers tab toolbar (a "Quick setup" link next to "+ New scorer")
3. Direct URL navigation

**Modal single-page structure** (not a wizard; all sections are arranged vertically on the same screen):

| Section | Content |
|---|---|
| Section 1 — Deploy the server | Docker command snippet (OpenAI version as default) + Copy button + deployment docs link (→ GitHub README) |
| Section 2 — Connection details | Server URL input + Auth token input (password style) + Test connection button + test result display |
| Section 3 — Scorers to create | Collapsed by default as "All 8 scorers (default)". When expanded, lists 8 dimensions; existing Scorer names are disabled and tagged "already exists". The Create scorers primary button sits at the bottom |

**On clicking Create scorers, the Modal enters execution mode (streaming, one-at-a-time creation)**:

- Sections 1 and 2 become read-only
- Section 3's checkbox list **transforms into a progress list**, each row with a status icon:
  - ⏳ pending
  - ⟳ in progress (with spinner animation)
  - ✓ created (success)
  - ✗ failed (with brief error displayed next to it)
- The frontend **strictly serially** calls the create API N times, updating the corresponding row after each completion
- If any Scorer fails → stop the remaining ones immediately, show a detailed error message, with buttons: [Retry] [Cancel]

**Retry behavior**: Uses the current URL and token, continues from the failed Scorer, does not reprocess the ones that already succeeded. **The user cannot modify the URL/token in execution mode** — to change them, they must Cancel and start over.

**Cancel behavior**:
- Immediately aborts the in-flight HTTP request
- Closes the Modal
- Already-created Scorers remain in the database (no rollback)
- No toast, no confirmation dialog
- The next time the user re-enters Quick Setup, the already-created Scorers appear in Section 3 as disabled "already exists" entries.

**On full success**: "All N scorers created successfully." appears at the bottom along with a Done button. Clicking Done closes the Modal, refreshes the Scorer list (newly created Scorers highlighted for 3–5 seconds), and shows a top toast `N remote scorers created`.

**Idempotency semantics**: Existing Scorer names are disabled in Section 3 and never enter the execution queue. **Existing Scorers' token and URL are not updated** — Quick Setup is always additive and never modifies existing data. Users who need to rotate the token do so manually via the Scorer detail page.

Detailed visual spec, error copy, and state machine are in [sub-doc 02](./02_quick_setup_remote_judge_server.md).

### §1.5 State flow diagram of the three components

```
User enters Scorers tab
    │
    ▼
Run queries, compute show_banner
    │
    ├──── false ──→ No Banner, Scorer list shown directly
    │
    └──── true ───→ Banner shown
                       │
                       │ (user clicks)
                       ▼
                  Provider setup Modal opens
                       │
              ┌────────┴────────┐
              │                  │
       has_providers=false   has_providers=true
              │                  │
              ▼                  ▼
          Form A             Form B
              │                  │
   ┌──────────┼──────────┐    ┌──┴────────────┐
   │          │          │    │                │
   ▼          ▼          ▼    ▼                ▼
"Configure  "Add      ✕   "Bind"          "Add Remote"
 Provider"  Remote"            │
   │        Server"            ▼
   ▼          │           Backend bulk bind
Navigate away  │           Banner disappears
(no return)    │
   │          │
   └──────────┴────────────────────────┐
                                        ▼
                              Quick Setup Modal
                                        │
                              (full flow in [sub-doc 02])
```

---

## §2 Built-in Score Configs and Scorers

Full definitions are in [sub-doc 03](./03_builtin_score_configs_and_scorers.md). This section gives only a high-level overview so the reader of the main spec can quickly grasp the scope.

### §2.1 Overview of the 12 built-in Score Configs

| Category | Count | Dimensions | Type distribution |
|---|---|---|---|
| Span-level (with Scorer) | 8 | hallucination, answer_relevance, coherence, helpfulness, instruction_following, toxicity, bias, output_format | 4 numeric + 2 categorical + 2 boolean |
| Trace-level (Score Config only; Scorer awaits Phase 3.1) | 4 | context_relevance, context_recall, faithfulness, answer_correctness | 4 numeric |

The mixed type distribution is deliberate: each dimension's type is chosen to match its natural granularity. Bias is a yes/no judgment, toxicity is a graded spectrum, hallucination is a continuous quality score. Forcing all to numeric would make a bias value of "0.37" uninterpretable.

### §2.2 Overview of the 8 built-in LLM Judge Scorers

- **Scorer name matches the corresponding Score Config name** (different tables, independent unique namespaces).
- Each Scorer carries a complete English judge prompt template.
- Default model settings: `temperature = 0`, structured output enabled.
- Default input mapping follows OpenTelemetry GenAI semantic conventions: `gen_ai.prompt`, `gen_ai.completion`.
- `provider_id` is initially empty; it's bound through the Provider setup Modal.

### §2.3 Scorer restriction for trace-level Score Configs

In the Scorer creation form, when the user selects a trace-level Score Config as the target:

- LLM Judge Scorer type **is not selectable** (greyed out; hover tooltip says "Trace-level Scorers ship in Phase 3.1")
- Code Scorer type **is not selectable** (same)
- Remote Scorer type **is selectable** — the user can implement trace-value extraction themselves and integrate via the Remote Scorer protocol

For the full inventory, field definitions, attribution list, and full prompt text, see [sub-doc 03](./03_builtin_score_configs_and_scorers.md).

---

## §3 Seed Data Loading Mechanism

### §3.1 Trigger: Per-org Lazy Seed

Seed data is **not inserted into all orgs at once on OpenObserve startup**; instead, it is lazy-loaded on each org's **first call to any list API of the Online Eval module**.

Trigger points: any of the following API handler entry points calls `builtin_seed::seed_for_org(db, org_id)`:

- `GET /api/{org_id}/eval/score_configs`
- `GET /api/{org_id}/eval/scorers`
- `GET /api/{org_id}/eval/jobs`

The exact endpoints to trigger from are determined at implementation time based on the current handler list. The principle is to cover every list endpoint a user might call when first entering the Online Eval module.

### §3.2 Loading flow

```
Execution steps of seed_for_org(db, org_id):

1. Fast path: check if the meta table's settings JSON has the `online_eval_seeded` key
   ├── present → return immediately (this is the path on every visit for already-seeded
   │              orgs; cost is one SELECT)
   └── absent  → continue

2. Check the deployment-level opt-out config `disable_builtin_seed`
   ├── true  → return skipped
   └── false → continue

3. Acquire an in-process Mutex for this org_id (avoids duplicate inserts from
   concurrent first-time visits within the same process)

4. Re-check the flag under lock (another request may have completed seeding)

5. Check whether the org's score_config table has any rows
   ├── yes (org upgraded from Phase 2.0, already has its own configs)
   │   → write flag {"skipped": "pre_existing_data", "at": ...}
   │   → return skipped (respect existing user data)
   └── no  → continue

6. Within a single Postgres transaction:
   - INSERT 12 Score Configs into the score_config table
   - INSERT 8 LLM Judge Scorers into the scorer table
   - Write flag {"seeded_at": ..., "version": "2.1.0"} into the meta table
   - Commit the transaction

7. Handle cross-process race:
   - If the transaction commit fails with a Postgres unique violation (SQLSTATE 23505)
   - Then another OpenObserve instance has already completed seeding
   - Catch the error, write flag {"via": "race_loser_recovery"}
   - Return success
```

### §3.3 Deterministic UUID derivation

The UUIDs of built-in Score Configs and Scorers are determined by code constants, using a fixed namespace UUID + UUID v5 derivation:

- Namespace UUID: `4f3a8c12-7b2e-4d91-a5f6-1c8d9e3b7a04` (hardcoded, never changes)
- Score Config UUID: `uuid_v5(NAMESPACE, "score_config." + name)`
- Scorer UUID: `uuid_v5(NAMESPACE, "scorer." + name)`

The **sole purpose of fixed UUIDs is to make foreign-key associations at seed insertion deterministic** — `scorer.score_config_id` directly references the UUID computed from code constants at insert time, without needing a two-step "insert, then query id, then insert" dance. The fixed UUID **is not a product identity**; users never see it, and the product never exposes it.

### §3.4 Flag storage

The `online_eval_seeded` flag is written to a top-level key of the `settings` JSON column in the `meta` table:

```json
{
  "online_eval_seeded": {
    "seeded_at": "2026-05-19T10:23:11Z",
    "version": "2.1.0"
  }
}
```

Product code checks only the **presence** of the flag, not the value. The value is informational, useful for operations and support diagnostics.

The flag payload has three forms:

| Scenario | Payload |
|---|---|
| Normal first-time seed | `{"seeded_at": "...", "version": "2.1.0"}` |
| Skipped due to existing Score Configs | `{"skipped": "pre_existing_data", "at": "..."}` |
| Cross-process race-loser recovery | `{"seeded_at": "...", "via": "race_loser_recovery"}` |

### §3.5 No re-seeding of deleted data

Once the flag is set, **OpenObserve never re-seeds**, even if the user later deletes all built-in Score Configs and Scorers. Deletion is the user's explicit choice, and OpenObserve respects it.

If the user wants to "restore the built-ins", they can:
- Manually delete the `online_eval_seeded` flag from the meta table via SQL (operational task)
- Or reference the source `BUILTIN_SEED.md` doc and manually create the Score Configs and Scorers they need

The main product **provides no "restore built-ins" button**. Rationale: a restore mechanism would reintroduce the conceptual distinction between "built-in vs. user-created", violating the "built-in is ordinary data" design principle.

### §3.6 Catalog integrity check at migration time

The SeaORM migration runs `verify_catalog_integrity()` once at startup:

- Verify the 12 Score Config names are unique
- Verify the 8 Scorer names are unique
- Verify each Scorer's `score_config_id` points to a real Score Config
- Verify all Score Configs referenced by Scorers have `level = "span"` (trace Scorers are out of scope for Phase 2.1)

**The migration phase performs no DB writes.** It only ensures consistency of the seed constant data at the code level — if someone later adds a new dimension and gets it wrong (e.g., a Scorer pointing to a non-existent Score Config), startup fails immediately rather than the error surfacing only on first access to the Online Eval module.

---

## §4 Reference Remote Judge Server

### §4.1 Implementation goals

`openobserve/eval-judges` is an **independent public repository**, decoupled from the OpenObserve main product. Goals:

- Users deploy an HTTP service in their own environment with a single `docker run` command
- The service implements the Remote Scorer protocol defined in Phase 2 Online Eval Spec §4.4
- Users can create Remote Scorers in OpenObserve pointing to the service's URL
- The service covers the same 8 span-level dimensions seeded in the main repo (trace dimensions await Phase 3.1)

**Strategic value**: The reference server is OpenObserve's core differentiator in the LLM observability market for air-gapped / private-deployment customers. Competitors like Langfuse and Braintrust don't ship an out-of-the-box, customer-deployable Judge Server.

### §4.2 Two deployment modes

The reference server switches between two modes via environment variables:

**Mode X: Call externally hosted Provider**

```
O2_JUDGE_PROVIDER=openai
O2_JUDGE_API_KEY=sk-...
O2_JUDGE_MODEL=gpt-4o-mini
```

The server internally calls a hosted API like OpenAI / Anthropic for scoring. Trace content **does leave** the customer environment (sent to the external LLM API).

Use case: quick onboarding; customers who already have commercial LLM API compliance agreements signed.

**Mode Y: Call local model endpoint**

```
O2_JUDGE_PROVIDER=openai_compatible
O2_JUDGE_URL=http://internal-llm:8000/v1
O2_JUDGE_MODEL=llama-3.1-70b-instruct
```

The server internally calls an OpenAI-compatible endpoint (Ollama, vLLM, in-house inference cluster). Trace content **never leaves** the customer environment.

Use case: air-gapped, data-sensitive, strict compliance.

Both modes coexist in the same Docker image and are switched by environment variable.

### §4.3 API definition

The reference server exposes the following HTTP endpoints:

#### `POST /evaluate`

**Purpose**: Run scoring on a single span/trace input.

**Request**:

```http
POST /evaluate
Authorization: Bearer <token>
Content-Type: application/json

{
  "scorer_name": "hallucination",
  "input": "<span's input field, optional>",
  "output": "<span's output field>",
  "expected": "<optional, ground truth for Experiment mode>",
  "metadata": {
    "additional_context": "..."
  }
}
```

**Field descriptions**:

| Field | Type | Required | Description |
|---|---|---|---|
| `scorer_name` | string | yes | The key that routes to which internal judge implementation. Allowed values are the 8 dimension names the reference server implements (matching the main repo's Score Config names) |
| `input` | string | no | The scoring input (e.g., user question). Whether it's required depends on `scorer_name` |
| `output` | string | yes | The scoring output (e.g., model response) |
| `expected` | string | no | Ground truth content; required only in Experiment mode or for certain dimensions (e.g., answer_correctness) |
| `metadata` | object | no | Pass-through field; the reference server may use or ignore it |

**Response**:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "value": 0.73,
  "metadata": {
    "reason": "<judge's chain-of-thought>",
    "model": "gpt-4o-mini",
    "elapsed_ms": 1245
  }
}
```

**Field descriptions**:

| Field | Type | Description |
|---|---|---|
| `value` | number / string / boolean | The scoring result. Type matches the Score Config's value_type (numeric → number; categorical → string; boolean → boolean) |
| `metadata.reason` | string | The judge's reasoning; useful for OpenObserve-side debugging and display |
| `metadata.model` | string | The LLM model name actually used |
| `metadata.elapsed_ms` | integer | Server-internal scoring time |

**Error responses**:

| HTTP status | Description |
|---|---|
| 400 | Invalid request body (missing required fields, unsupported scorer_name) |
| 401 | Missing or invalid Authorization header / token |
| 500 | Server-internal error (LLM API call failed, parsing failed, etc.) |
| 502 | Server-to-downstream-LLM-API communication failure |
| 504 | Server timeout when calling the LLM |

#### `GET /health`

**Purpose**: Health check, used by the "Test connection" button in the OpenObserve Quick Setup flow.

**Request**:

```http
GET /health
Authorization: Bearer <token>
```

**Response (success)**:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ok",
  "version": "0.1.0",
  "backend": "openai",
  "model": "gpt-4o-mini"
}
```

**Response (failure)**: standard HTTP status codes such as 401 / 503.

#### `GET /version`

**Purpose**: Returns the server version, used by OpenObserve for compatibility checks.

**Request**: No Authorization required.

**Response**:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "version": "0.1.0",
  "api_version": "v1"
}
```

`api_version` is used on the OpenObserve side for protocol compatibility checks. Server versions within the same `api_version` are forward-compatible with the main product.

### §4.4 Implementation recommendation

**The first version can consider using DeepEval to simplify development.** DeepEval (Apache 2.0 license) has already implemented LLM-Judge scoring logic for several dimensions including hallucination, bias, toxicity, and answer_relevance. The first version of the reference server can:

1. Use Python + FastAPI as the HTTP framework
2. Delegate the actual scoring internally to DeepEval
3. Adapt the API contract at the FastAPI layer (OpenObserve Remote Scorer protocol ↔ DeepEval calls)
4. Backend abstraction layer supports switching between Mode X and Mode Y

This is **an implementation choice for fast shipping**, **not a long-term commitment**. The API contract in §4.3 is the lasting artifact. In the future it can be replaced by:

- Internalizing the prompts (extracted under Apache 2.0 / MIT) and calling the LLM API directly without DeepEval
- Migrating to a non-Python language (e.g., Rust for performance)
- Any such change is transparent to all consumers of the reference server because the API contract is unchanged

**Architecture, file structure, CI, Dockerfile, test strategy**, and other concrete designs are **out of scope for this document** — handled by an independent design doc in the `openobserve/eval-judges` repo. This document only constrains the API contract and implementation goals.

### §4.5 Repository scope constraint

The `CONTRIBUTING.md` in the `openobserve/eval-judges` repo carries a hard scope constraint:

> This repository hosts 10–15 general-purpose scoring dimensions (the initial 8 span dimensions + trace dimensions added after Phase 3.1). Vertical domains (medical safety, legal accuracy, financial compliance), specific languages (Chinese grammar, Japanese honorifics), and specific use cases (RAG-specific variants, Agent trajectory scoring) are **out of scope for this repository**. Contributors are encouraged to fork the repo to host vertical or specialized judge sets following the same API contract — such forks will interoperate with OpenObserve as drop-in Remote Scorers, with no additional integration work required.

This constraint protects OpenObserve's "unopinionated infrastructure" position at the repo level.

### §4.6 Versioning and release cadence

The reference server is **versioned independently** from the main OpenObserve product. Its release cadence is expected to be faster than the main product (small project, narrow API surface). Tag convention follows semver. API contract stability is managed by the major version (forward-compatible within the same major).

Cross-references between the main product (OpenObserve) and the reference server are done through the `/version` endpoint. The Quick Setup flow calls `/version` when creating a Remote Scorer to capture the server version, storing it in the Remote Scorer's metadata for later diagnostics.

---

## §5 Implementation Path

### §5.1 Work breakdown

Phase 2.1 breaks into 5 independent work items:

| Item | Dependencies | Estimated effort |
|---|---|---|
| **A. 12 Score Configs + 8 Scorers content** ([sub-doc 03](./03_builtin_score_configs_and_scorers.md), completed) | None | Done |
| **B. Seed data loading mechanism** (per-org lazy seed + flag write + integrity check migration) | A | 3–5 days |
| **C. Provider setup bar + Modal + one-shot bind API** (frontend + backend) | None (parallel to A, B) | 5–7 days |
| **D. Reference Remote Judge Server repo** (`openobserve/eval-judges`) | A (shares prompt content) | 2–3 weeks |
| **E. Quick Setup UI flow** (frontend) | D (needs server API ready) | 5–7 days |

A through C are pure main-repo work and can ship independently as a v2.1 patch release, not blocked by D and E. D is a new repo and can be developed in parallel by another engineer. E depends on D being ready.

### §5.2 Release options

**Option α (recommended): A + B + C as v2.1, D + E as v2.2**

- **v2.1** (~2–3 weeks out): seed data + Provider guidance. Immediately improves onboarding for all v2.0 users.
- **v2.2** (~5–7 weeks after v2.1): reference Remote Judge Server + Quick Setup. Standalone marketable story: "OpenObserve now ships a Docker-deployable judge server for air-gapped LLM scoring".

Two release moments, two narrative beats. The work can run back-to-back without idle time (D can start as soon as A is done), so two releases take the same total time as one combined release.

**Option β: A + B + C + D + E together as v2.1**

- Single release, total ~5–7 weeks. Stronger single-shot promotional effect.
- Sacrifices the intermediate visibility milestone.

The choice between α and β depends on the team's release-cadence preference. The technical work is identical; only the release packaging differs.

### §5.3 Compatibility with existing Phase 2.0 deployments

For existing v2.0 deployments upgraded to v2.1:

- **Orgs that have already created their own Score Configs**: the lazy seed flow detects that the `score_config` table is non-empty, writes the flag `{"skipped": "pre_existing_data"}`, and **does not insert seed data**. The user's existing choices are respected.
- **Orgs that have not yet created any Score Configs** (which, given the cold-start problem, may be a sizable share): they receive the seed batch on first access to the Online Eval module. This is the intended behavior.

A deployment-level config flag `disable_builtin_seed = true` is provided for operators who want to fully opt out of seeding.

---

## §6 Relationship to Other Phases

### §6.1 Relationship to Phase 2.0

Phase 2.1 is **purely additive** with respect to Phase 2.0:

- Does not modify any Phase 2.0 product object, table, or behavior
- Does not revise, retract, or contradict any Phase 2.0 decision
- The very fact that the seed-data approach is feasible is precisely because Phase 2.0 made Score Configs and Scorers first-class user-owned objects with full CRUD — "built-in" requires no special API surface and no schema marker

### §6.2 Relationship to Phase 2.5

Phase 2.5 (Annotation Queue + Dataset + Prompt Management UI) is completely independent of Phase 2.1 and can run in parallel. No shared dependencies; they modify different parts of the product.

The one positive interaction: Phase 2.5's Annotation Queue UI renders forms based on the Score Config schema. The existence of the 12 built-in Score Configs gives Phase 2.5 real test fixtures available from day one, sparing it the trouble of synthesizing test data.

### §6.3 Relationship to Phase 3.1

Phase 3.1's Trace Scorer (cross-span scoring covering RAG / Agent / multi-step) will make the 4 trace-level Score Configs shipped by Phase 2.1 actually usable.

Specifically:

- Phase 2.1 ships 4 trace Score Configs with **no corresponding Scorers**
- Phase 3.1 introduces the Trace Scorer product object (supporting cross-span value extraction), and through the same lazy-seed mechanism (with a different flag key `trace_eval_seeded`), appends corresponding LLM Judge Trace Scorers for orgs that have trace Score Configs
- More RAG-specific trace dimensions can ship synchronously as Phase 3.1 increments

The design choices in Phase 2.1 — deterministic UUID derivation, per-org lazy seed + flag mechanism, no added schema markers — are **deliberately designed to be reusable for Phase 3.1 with no modifications**. The mechanism is extensible.

---

## §Appendix A Key Design Decisions Recap

| ID | Decision | Section |
|---|---|---|
| `§ColdStart-D1` | No column is added to distinguish "built-in vs. user-created"; built-in data is indistinguishable from user data at both the data layer and the product layer. Fixed UUIDs are only an implementation mechanism for foreign-key association at seed insertion, not a product identity | §0, §3.3 |
| `§ColdStart-D2` | Built-in data is not versioned and not upgraded. Revisions only affect orgs that first cold-start in the future | §3.5 |
| `§ColdStart-D3` | At the UI level, built-in and user-created objects are visually indistinguishable (no chip, badge, segmentation, privileged ordering, or read-only state) | §1, [03] |
| `§ColdStart-D4` | 12 built-in dimensions: 8 span (with Scorer) + 4 trace (Score Config only, await Phase 3.1); type distribution is 4 numeric + 2 categorical + 2 boolean + 4 numeric (trace) | §2, [03] |
| `§ColdStart-D5` | Provider guidance uses explicit user actions for Provider creation/binding; no `default_provider` concept introduced, no return-state tracking after Banner navigation | §1.3 |
| `§ColdStart-D6` | Seed insertion uses per-org lazy seed + a settings JSON flag in the meta table (`online_eval_seeded`); once set, the flag is never re-seeded | §3.1, §3.5 |
| `§ColdStart-D7` | Quick Setup is idempotent: existing Scorers are skipped; token and URL are not updated; rotating a token is done via the Scorer detail page | §1.4 |
| `§ColdStart-D8` | The reference judge server ships in an independent repo and is never bundled into the main binary | §4.1 |
| `§ColdStart-D9` | A deployment-level opt-out (`disable_builtin_seed`) is provided for operators wanting a clean install | §5.3 |
| `§ColdStart-D10` | Phase 2.1 is purely additive w.r.t. Phase 2.0; no Phase 2.0 decision is revised | §6.1 |
| `§ColdStart-D11` | The reference server's API contract is identical to any other Remote Scorer's; it is not a privileged backend | §4.3 |
| `§ColdStart-D12` | The reference server hosts only 10–15 general dimensions; vertical/domain dimensions are encouraged as community forks | §4.5 |
| `§ColdStart-D13` | LLM Judge Scorers and Remote Scorers coexist after Quick Setup; users prune them manually | §1.4 |
| `§ColdStart-D14` | Attribution lives only in source comments and maintenance docs, never in the user database, never in the UI | [03] §2.4 |
| `§ColdStart-D15` | Built-in LLM Judge Scorer names match the corresponding Score Config names (different tables, independent namespaces) | §2.2, [03] §2 |
| `§ColdStart-D16` | The database backend considered is Postgres only; unique-violation detection is based on SQLSTATE 23505 | §3.2 |
| `§ColdStart-D17` | Banner trigger condition is "all Scorers unbound" (option P), not "any Scorer unbound". Rationale: the Banner is for cold-start guidance; once the user has bound any one, they've grasped the workflow | §1.2 |
| `§ColdStart-D18` | Quick Setup creates Scorers one-at-a-time streaming; on failure, stops and shows Retry/Cancel; Retry continues from the failed item and does not reprocess successful ones | §1.4 |
| `§ColdStart-D19` | The first version of the reference server may use DeepEval to simplify development; the API contract is stable and the internal implementation can be replaced later | §4.4 |

---

## §Appendix B Glossary

| Term | Definition |
|---|---|
| Built-in (colloquial) | Score Configs and Scorers that OpenObserve inserts for new orgs via the seed mechanism. **Not** a product category — there is no marker at the data or product layer distinguishing built-in from user-created. |
| Seed data | The 12 Score Configs and 8 LLM Judge Scorers that OpenObserve ships as code constants. Lazy-inserted into an org's database the first time it accesses the Online Eval module. |
| Lazy seed | The deferred seed-insertion flow executed on an org's first access. See §3.1. |
| Banner | The non-blocking notice bar inside the Scorers tab indicating that "built-in Scorers need to bind to a Provider". Clicking opens the Provider setup Modal. See §1.2 and [sub-doc 01](./01_provider_setup_bar_and_modal.md). |
| Provider setup Modal | The Modal opened by clicking the Banner; has two forms (A: no Provider; B: has Provider). See §1.3 and [sub-doc 01](./01_provider_setup_bar_and_modal.md). |
| Quick Setup Modal | The Modal for creating 8 Remote Scorers at once pointing to the reference Remote Judge Server. See §1.4 and [sub-doc 02](./02_quick_setup_remote_judge_server.md). |
| Reference Remote Judge Server | An independent HTTP service located in `openobserve/eval-judges` that implements the Remote Scorer protocol. See §4. |
| Mode X | The reference server is configured to call an externally hosted LLM API (OpenAI, Anthropic, etc.). See §4.2. |
| Mode Y | The reference server is configured to call a customer-hosted OpenAI-compatible endpoint (local model); data does not leave the environment. See §4.2. |
| `online_eval_seeded` | The flag written into an org's `settings` JSON in the meta table, indicating that the org has completed Phase 2.1 seeding. See §3.4. |
| `trace_eval_seeded` | A flag key reserved for Phase 3.1, indicating that the org has completed seeding of trace dimensions (TBD). |
| Fixed namespace UUID | The hardcoded UUID `4f3a8c12-7b2e-4d91-a5f6-1c8d9e3b7a04`, used to derive stable UUIDs for all seed data via UUID v5. See §3.3. |
