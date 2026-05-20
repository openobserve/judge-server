# Architecture

How the judge-server is laid out and what happens when a request
arrives. Pairs with the user-facing README.

## Directory layout

```
judge-server/
├── pyproject.toml            project metadata, deps, build config
├── Dockerfile                multi-stage container build (build → slim runtime, non-root)
├── README.md                 user-facing: deploy, providers, env vars, API
├── ARCHITECTURE.md           this file
├── .env.example              all env vars + an example block per provider
├── .gitignore, .dockerignore
├── src/judge_server/
│   ├── __init__.py           exposes __version__ and API_VERSION
│   ├── __main__.py           `python -m judge_server` entry; loads env + starts uvicorn
│   ├── app.py                FastAPI app factory + the 3 route handlers
│   ├── auth.py               Bearer-token dependency (constant-time compare)
│   ├── config.py             Settings.from_env() — reads/validates O2_JUDGE_* env vars
│   ├── models.py             Pydantic schemas for /evaluate, /health, /version
│   ├── backends/
│   │   ├── base.py           LLMBackend ABC + LLMResult + LLMTimeout/LLMTransportError
│   │   └── litellm_backend.py  unified backend; routes ~100 providers via LiteLLM
│   └── scorers/
│       ├── prompts.py        the 8 canonical prompts (verbatim text constants)
│       ├── registry.py       Scorer dataclass + REGISTRY of all 8 + render/parse glue
│       └── parser.py         extracts <reasoning>/<score>/<category>/<value> tags
└── tests/
    ├── conftest.py           FakeBackend (in-memory LLMBackend) + shared fixtures
    ├── test_routes.py        end-to-end /version, /health, /evaluate behavior
    ├── test_backend.py       provider routing + config validation
    ├── test_parser.py        XML-tag parser edge cases
    └── test_scorers.py       registry consistency guard (Pattern A/B, value type)
```

## What each module owns

### Top-level

- **`pyproject.toml`** — declares deps (`fastapi`, `uvicorn`, `pydantic`,
  `litellm`), the `judge-server` console script, and Hatch as the
  build backend. `[project.optional-dependencies].dev` holds pytest.
- **`Dockerfile`** — two stages: `python:3.12-slim` `pip install` into
  `/install`, then copy artifacts into a clean slim image. Runs as
  uid 10001. Default `CMD` is `python -m judge_server`.

### `src/judge_server/`

- **`__init__.py`** — `__version__ = "0.1.0"`, `API_VERSION = "v1"`.
  Read by `/version` and `/health`.
- **`__main__.py`** — process entry point. Calls `Settings.from_env()`,
  builds the app, hands it to `uvicorn.run()`. Exits with code 2 on
  config error.
- **`config.py`** — `Settings` dataclass + `from_env()` classmethod.
  Reads every `O2_JUDGE_*` env var, validates them (token required,
  backend name shape, `openai_compatible` requires URL, timeout > 0),
  and freezes them into an immutable `Settings`.
- **`auth.py`** — `make_auth_dependency(settings)` returns a FastAPI
  dependency that parses `Authorization: Bearer <token>` and
  constant-time-compares it to `settings.auth_token`. Both
  missing/malformed and wrong-token cases raise HTTP 401.
- **`models.py`** — Pydantic models: `EvaluateRequest`,
  `EvaluateResponse` (+ `EvaluateResponseMetadata`), `HealthResponse`,
  `VersionResponse`. These define the API contract on the wire.
- **`app.py`** — `create_app(settings, backend=...)` factory:
  1. Builds the LiteLLM backend (or accepts a test double).
  2. Registers a `RequestValidationError` → 400 handler (spec lists
     400 for "missing required fields", not the FastAPI default 422).
  3. Defines the 3 routes — `/version` (public), `/health` (auth),
     `/evaluate` (auth + scorer dispatch + LLM call + parse).

### `src/judge_server/backends/`

- **`base.py`** — the abstract contract any backend implements:
  `async complete(prompt: str) → LLMResult`. Plus two exception
  classes used to translate upstream failures into HTTP status codes
  (`LLMTimeout` → 504, `LLMTransportError` → 502).
- **`litellm_backend.py`** — the only concrete backend. Builds a
  LiteLLM model string from `(provider, model)` (`openai` stays bare;
  `openai_compatible` becomes `openai/<model>`; everything else gets
  the `<provider>/` prefix). Calls `litellm.acompletion()` with
  `temperature=0`, maps `litellm.Timeout` and the connection/API
  errors back to our exception types. `build_backend(settings)`
  is the factory used by `app.py`.

### `src/judge_server/scorers/`

- **`prompts.py`** — 8 module-level string constants
  (`HALLUCINATION`, `ANSWER_RELEVANCE`, …). The OpenObserve canonical
  prompt text — do not paraphrase in place. Each contains `{{input}}`
  and/or `{{output}}` placeholders.
- **`registry.py`** — `Scorer` dataclass holding `name`, `kind`
  (`numeric` / `categorical` / `boolean`), `prompt_template`,
  `requires_input`, and `categorical_labels`. Exposes:
  - `render(input_text, output_text)` → substitutes placeholders.
  - `parse(llm_text)` → dispatches to the right `parser.parse_*`.
  - `REGISTRY: dict[str, Scorer]` keyed by name; populated from a
    module-level tuple.
- **`parser.py`** — pure regex extraction. `parse_numeric` clamps to
  `[0.0, 1.0]`; `parse_categorical` is case-/whitespace-tolerant with
  a substring fallback (handles "category: low"); `parse_boolean`
  accepts true/false/yes/no. Raises `ScoreParseError` (→ HTTP 500)
  when the LLM output doesn't have the expected tags.

### `tests/`

- **`conftest.py`** — `FakeBackend(LLMBackend)` that records prompts
  and returns canned text; `settings` / `make_client` / `client` /
  `auth_headers` fixtures. Nothing in the test suite hits a real LLM.
- **`test_routes.py`** — every route, every error code: auth 401,
  unknown scorer 400, missing input 400, validation 400 (not 422),
  numeric/categorical/boolean success, unparseable 500, timeout 504,
  transport error 502.
- **`test_backend.py`** — parametrized `build_model_string` table for
  10 providers, plus `Settings.from_env()` validation rules.
- **`test_parser.py`** — clamp behavior, case tolerance, missing-tag
  errors.
- **`test_scorers.py`** — drift guard for the registry: all 8 names
  present, Pattern A/B (`requires_input`) matches the expected
  assignment, kind (numeric/categorical/boolean) matches expected.

## Startup flow

```
docker run … openobserve/eval-judges:latest
        │
        ▼
CMD ["python", "-m", "judge_server"]
        │
        ▼
__main__.main()
   ├── logging.basicConfig(INFO)
   ├── Settings.from_env()              # config.py — reads O2_JUDGE_* env vars
   ├── create_app(settings)             # app.py
   │      ├── build_backend(settings)   # backends/litellm_backend.py
   │      ├── make_auth_dependency(settings)   # auth.py
   │      ├── register exception handler (422 → 400)
   │      └── register /version, /health, /evaluate
   └── uvicorn.run(app, host, port)     # bind 0.0.0.0:8000 by default
```

Any `ConfigError` during `Settings.from_env()` exits with code 2 and
a one-line error on stderr — fail-fast, never start a half-configured
server.

## Request flow — `POST /evaluate`

```
Client
  │  POST /evaluate
  │  Authorization: Bearer <token>
  │  {scorer_name, input?, output, expected?, metadata?}
  ▼
FastAPI
  ├── require_bearer dependency           (auth.py)
  │     constant-time compare → 401 if wrong
  ├── Pydantic body validation             (models.EvaluateRequest)
  │     RequestValidationError → 400      (app.py handler)
  ▼
route handler (app.py / post_evaluate)
  ├── REGISTRY.get(scorer_name)            (scorers/registry.py)
  │     not found → 400
  ├── if scorer.requires_input and not body.input → 400
  ├── scorer.render(input_text, output_text)
  │     substitutes {{input}}, {{output}}
  ├── backend.complete(prompt)             (backends/litellm_backend.py)
  │     ├── litellm.acompletion(model=<provider>/<model>, temp=0, …)
  │     ├── litellm.Timeout                       → LLMTimeout → 504
  │     ├── APIConnectionError / ServiceUnavail   → LLMTransportError → 502
  │     └── other APIError                        → LLMTransportError → 502
  ├── elapsed_ms = perf_counter() diff
  ├── scorer.parse(llm_text)               (scorers/parser.py)
  │     ScoreParseError → 500
  │     numeric  → float ∈ [0.0, 1.0]
  │     categorical → one of the scorer's labels
  │     boolean → True/False
  ▼
EvaluateResponse JSON
  {
    "value": <number|string|bool>,
    "metadata": {
      "reason": "<reasoning tag content>",
      "model": "<actual model name from upstream>",
      "elapsed_ms": <int>
    }
  }
```

## Request flow — `GET /health` & `GET /version`

- `GET /version` — public. Returns `{version, api_version}` straight
  from `judge_server.__init__`.
- `GET /health` — Bearer required. Returns `{status: "ok", version,
  backend, model}` from the frozen `Settings`. **Does not call the
  upstream LLM** — it confirms the server is up and configured, not
  that the LLM is reachable. (Upstream reachability surfaces on the
  first real `/evaluate` call as a 502/504.)

## Adding a new scorer

1. Add a prompt constant to `scorers/prompts.py`. Follow the
   five-section structure of the existing prompts (task / input
   region / rubric / notes / chain-of-thought).
2. Append a `Scorer(...)` entry to the `_ALL` tuple in
   `scorers/registry.py`. Pick `kind` based on what the prompt asks
   the LLM to emit (`<score>`, `<category>`, or `<value>`).
3. Add a row to `tests/test_scorers.py`'s expectation tables so the
   drift guard covers it.
4. If the prompt is adapted from an open-source library, keep
   attribution in `scorers/prompts.py` source comments only — never
   into the user database or the product UI.

## Adding a new backend

The current architecture has one concrete backend
(`LiteLLMBackend`) that already covers ~100 providers. You only need
a new backend if a provider isn't reachable through LiteLLM. If so:

1. Create `src/judge_server/backends/<name>_backend.py` implementing
   `LLMBackend.complete()`. Translate upstream timeout / connection
   errors into `LLMTimeout` / `LLMTransportError`.
2. Decide how it's selected — extend the `O2_JUDGE_PROVIDER` value range or
   add a new env var.
3. Route to it from `build_backend()` in
   `backends/__init__.py` (or `litellm_backend.py` where the
   default factory lives today).
