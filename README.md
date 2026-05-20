# OpenObserve Reference Remote Judge Server

A Docker-deployable HTTP server that implements OpenObserve's Remote
Scorer protocol. Runs the eight built-in LLM-Judge dimensions
(hallucination, answer_relevance, coherence, helpfulness,
instruction_following, toxicity, bias, output_format) entirely
inside your environment.

## Quick start

```bash
docker run -d \
  -p 8000:8000 \
  -e O2_JUDGE_AUTH_TOKEN=$(openssl rand -hex 24) \
  -e O2_JUDGE_PROVIDER=openai \
  -e O2_JUDGE_API_KEY=sk-... \
  -e O2_JUDGE_MODEL=gpt-4o-mini \
  openobserve/eval-judges:latest
```

## Supported providers

LiteLLM under the hood, so anything LiteLLM supports works. Common
ones below. Set `O2_JUDGE_PROVIDER` to the provider name and
`O2_JUDGE_MODEL` to the model — that's it.

| Provider | `O2_JUDGE_PROVIDER` | Extra env vars |
|---|---|---|
| OpenAI | `openai` | — |
| Anthropic Claude | `anthropic` | — |
| Google AI Studio (Gemini) | `gemini` | — |
| Google Vertex AI | `vertex_ai` | `GOOGLE_APPLICATION_CREDENTIALS`, `VERTEXAI_PROJECT`, `VERTEXAI_LOCATION` |
| AWS Bedrock | `bedrock` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION_NAME` |
| Azure OpenAI | `azure` | `O2_JUDGE_URL`, `AZURE_API_VERSION` |
| Cohere | `cohere` | — |
| Mistral | `mistral` | — |
| Groq | `groq` | — |
| DeepSeek | `deepseek` | — |
| Together AI | `together_ai` | — |
| Fireworks AI | `fireworks_ai` | — |
| Ollama (local) | `ollama` | `O2_JUDGE_URL` (e.g. `http://host:11434`) |
| Any OpenAI-compatible endpoint | `openai_compatible` | `O2_JUDGE_URL` (must include `/v1`) |
| Any other LiteLLM provider | the provider's LiteLLM name | as documented at <https://docs.litellm.ai> |

Concrete examples for each in `.env.example`.

### Examples

**Anthropic Claude:**

```bash
docker run -d -p 8000:8000 \
  -e O2_JUDGE_AUTH_TOKEN=$(openssl rand -hex 24) \
  -e O2_JUDGE_PROVIDER=anthropic \
  -e O2_JUDGE_API_KEY=sk-ant-... \
  -e O2_JUDGE_MODEL=claude-3-5-sonnet-20241022 \
  openobserve/eval-judges:latest
```

**Local Ollama:**

```bash
docker run -d -p 8000:8000 \
  -e O2_JUDGE_AUTH_TOKEN=$(openssl rand -hex 24) \
  -e O2_JUDGE_PROVIDER=ollama \
  -e O2_JUDGE_API_KEY=unused \
  -e O2_JUDGE_MODEL=llama3 \
  -e O2_JUDGE_URL=http://host.docker.internal:11434 \
  openobserve/eval-judges:latest
```

**AWS Bedrock:**

```bash
docker run -d -p 8000:8000 \
  -e O2_JUDGE_AUTH_TOKEN=$(openssl rand -hex 24) \
  -e O2_JUDGE_PROVIDER=bedrock \
  -e O2_JUDGE_API_KEY=unused \
  -e O2_JUDGE_MODEL=anthropic.claude-3-sonnet-20240229-v1:0 \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  -e AWS_REGION_NAME=us-east-1 \
  openobserve/eval-judges:latest
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `O2_JUDGE_AUTH_TOKEN` | yes | Bearer token clients must present |
| `O2_JUDGE_PROVIDER` | yes | LiteLLM provider name (see table above) |
| `O2_JUDGE_API_KEY` | yes | Primary credential. For providers without a single API key (Bedrock, Vertex), set any non-empty placeholder here and supply provider-specific env vars |
| `O2_JUDGE_MODEL` | yes | Model name as the provider expects it |
| `O2_JUDGE_URL` | depends | Required for `openai_compatible`; optional override for `ollama`, `azure`, and any self-hosted variant |
| `O2_JUDGE_TIMEOUT_SECONDS` | no | LLM call timeout, default `60` |
| `O2_JUDGE_HOST` | no | Bind host, default `0.0.0.0` |
| `O2_JUDGE_PORT` | no | Bind port, default `8000` |

## API

Three endpoints. Bodies are JSON; auth is `Authorization: Bearer <token>`
matched against `O2_JUDGE_AUTH_TOKEN`.

### `POST /evaluate`

Score a single span. Bearer required.

**Request:**

```http
POST /evaluate
Authorization: Bearer <token>
Content-Type: application/json

{
  "scorer_name": "hallucination",
  "input": "What is the capital of France?",
  "output": "The capital of France is Paris.",
  "expected": "Paris",
  "metadata": {"trace_id": "abc-123"}
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `scorer_name` | string | yes | One of the supported dimensions (table below) |
| `input` | string | depends | Required for scorers that judge input+output; optional for output-only scorers |
| `output` | string | yes | The model output being scored |
| `expected` | string | no | Ground truth, for scorers that compare against a reference |
| `metadata` | object | no | Pass-through, ignored by the server |

**Response (200 OK):**

```json
{
  "value": 0.15,
  "metadata": {
    "reason": "The output's claim that Paris is the capital is supported by the input.",
    "model": "gpt-4o-mini",
    "elapsed_ms": 1245
  }
}
```

| Field | Type | Description |
|---|---|---|
| `value` | number / string / boolean | Type matches the scorer's value type (table below) |
| `metadata.reason` | string | The judge's reasoning, from the LLM's `<reasoning>` tag |
| `metadata.model` | string | Model name actually used upstream |
| `metadata.elapsed_ms` | integer | Server-internal scoring time |

**Supported scorers:**

| `scorer_name` | value type | range / labels | `input` required |
|---|---|---|---|
| `hallucination` | number | 0.0 – 1.0 | yes |
| `answer_relevance` | number | 0.0 – 1.0 | yes |
| `coherence` | number | 0.0 – 1.0 | no |
| `helpfulness` | number | 0.0 – 1.0 | yes |
| `instruction_following` | string | `low` / `medium` / `high` | yes |
| `toxicity` | string | `low` / `medium` / `high` | no |
| `bias` | boolean | true / false | no |
| `output_format` | boolean | true / false | yes |

**Errors:**

| Status | Cause |
|---|---|
| 400 | Invalid body, unsupported `scorer_name`, or missing `input` for a scorer that requires it |
| 401 | Missing or invalid Bearer token |
| 500 | LLM returned a response we couldn't parse into the expected shape |
| 502 | Upstream LLM connection / API error |
| 504 | Upstream LLM timed out |

### `GET /health`

Confirms the server is up and configured. Does **not** call the
upstream LLM — upstream reachability surfaces on the first real
`/evaluate` call as a 502/504. Bearer required.

**Response (200 OK):**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "backend": "openai",
  "model": "gpt-4o-mini"
}
```

### `GET /version`

Server version. No auth.

**Response (200 OK):**

```json
{
  "version": "0.1.0",
  "api_version": "v1"
}
```

`api_version` is the major version of the Remote Scorer protocol —
clients can use it for compatibility checks.

## Project structure

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the directory layout,
per-file responsibilities, startup flow, and the lifecycle of a
`/evaluate` request.

## Development

Requires [uv](https://docs.astral.sh/uv/). Install once:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then:

```bash
uv sync --extra dev
uv run pytest
uv run python -m judge_server  # serves on $O2_JUDGE_HOST:$O2_JUDGE_PORT
```

## Scope

This repo hosts 10–15 general-purpose scoring dimensions. Vertical,
domain-specific, or language-specific judges are out of scope —
contributors are encouraged to fork.
