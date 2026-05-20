# OpenObserve LLM Observability · Phase 2.1 设计规范 v2

> **模块名称**：冷启动 —— 预置 Score Config、预置 LLM Judge Scorer、参考 Remote Judge Server
>
> **版本**：v2.0（2026-05-19，完全重写）
> **状态**：实施规范，待评审
> **前置文档**：[Phase 2 Online Eval Spec v1.3](./LLM_Observability_Phase2_Online_Eval_v1_3_EN.md)
> **被本文档引用的子文档**：
> - [01_provider_setup_bar_and_modal.md](./01_provider_setup_bar_and_modal.md) —— Provider 引导条与 Modal 的视觉设计
> - [02_quick_setup_remote_judge_server.md](./02_quick_setup_remote_judge_server.md) —— Quick Setup 流程的视觉设计
> - [03_builtin_score_configs_and_scorers.md](./03_builtin_score_configs_and_scorers.md) —— 预置 Score Config 与 Scorer 的完整定义

---

## §0 概述

Phase 2.1 在已发版的 Phase 2.0 Online Eval 模块之上，新增三项相互配合的能力，共同解决新用户首次进入 Online Eval 模块时**面对空列表的冷启动问题**：

1. **预置 Score Config（12 个）+ 预置 LLM Judge Scorer（8 个）**作为种子数据，在组织首次访问 Online Eval 模块时插入数据库。详细清单与 prompt 在 [03 子文档](./03_builtin_score_configs_and_scorers.md)。
2. **Provider 引导条 + Modal**，当用户的预置 LLM Judge Scorer 缺少 Provider 时显示，引导用户绑定 Provider。详细视觉设计在 [01 子文档](./01_provider_setup_bar_and_modal.md)。
3. **Quick Setup 流程**，让用户通过单个 Modal 一次性创建 8 个 Remote Scorer，指向用户自行部署的参考 Remote Judge Server（独立仓库 `openobserve/eval-judges`）。详细视觉设计在 [02 子文档](./02_quick_setup_remote_judge_server.md)，参考 server 的实现目标与 API 定义见本文档 §4。

### 核心设计原则

- **预置数据 = 普通数据**。预置 Score Config 与 Scorer 一旦插入组织的数据库，与用户自建的对象完全无别。无 `built_in` 列，无 UI 标记，无特殊 API。用户可删除、修改、替换。
- **不维护引导状态**。Banner 是否显示、Modal 显示哪个形态，完全由当前数据库状态决定。每次访问独立判断，无 dismiss 标记、无回流跟踪。
- **无 schema 变更**。复用 Phase 2.0 的 `score_config` 表、`scorer` 表、`meta` 表。新增的"是否已 seed"flag 写入 meta 表 settings JSON 列。
- **Phase 2.0 纯增量**。不修改任何 Phase 2.0 产品对象、表、行为。

---

## §1 交互设计

本节描述 Banner、Provider 引导 Modal、Quick Setup Modal 三个组件的**状态判定逻辑与跳转关系**。视觉细节、文案、组件层级、mockup 等参见 [01 子文档](./01_provider_setup_bar_and_modal.md) 与 [02 子文档](./02_quick_setup_remote_judge_server.md)。

### §1.1 全局状态量

引导逻辑依赖以下三个查询，**每次进入 Scorers 标签时重新计算**：

```sql
-- A. 组织内 Scorer 总数 与 未绑 Provider 的 Scorer 数量
SELECT 
  COUNT(*) AS scorers_total,
  COUNT(*) FILTER (WHERE provider_id IS NULL) AS scorers_unbound
FROM scorer
WHERE org_id = $org_id;

-- B. 组织内 Provider 总数
SELECT COUNT(*) AS providers_total
FROM provider
WHERE org_id = $org_id;
```

派生量：

| 派生量 | 计算方式 | 含义 |
|---|---|---|
| `has_scorers` | `scorers_total > 0` | 组织内是否有 Scorer |
| `all_unbound` | `scorers_unbound = scorers_total` | 是否所有 Scorer 都未绑 Provider |
| `has_providers` | `providers_total > 0` | 组织内是否有 Provider |

### §1.2 Banner 显示判定

**Banner 显示条件**：

```
show_banner = has_scorers AND all_unbound
```

也就是：**当且仅当组织内至少有一个 Scorer，且所有 Scorer 都没有绑定 Provider 时**，显示 Banner。

为什么是"全部未绑"而不是"任意未绑"：Banner 的目的是冷启动引导。用户一旦绑定了任意一个 Scorer，说明他已经掌握了操作方法，不再需要引导。半完成状态下不再显示 Banner（如果剩余 Scorer 未绑定，用户可以走 Scorer 详情页面手动处理）。

**Banner 位置**：Scorers 标签内，工具栏（搜索、过滤、+ New scorer）上方独立一行，横跨内容区域宽度。

**Banner 内容**：单行文字 + 右侧箭头，整行可点击。点击后弹出 Provider 引导 Modal。

**关闭机制**：Banner 不携带关闭按钮。Banner 在状态满足时显示，状态变化（任一 Scorer 绑定 Provider）时自然消失。

详细视觉规范参见 [01 子文档 §3](./01_provider_setup_bar_and_modal.md#3-setup-bar)。

### §1.3 Provider 引导 Modal

用户点击 Banner 后弹出。根据 `has_providers` 显示两种形态：

| 条件 | Modal 形态 | 主要选项 |
|---|---|---|
| `has_providers = false`（组织无 Provider） | **形态 A** | "Configure a model provider"（跳走，去创建 Provider） / "Add a Remote Judge Server"（打开 Quick Setup） |
| `has_providers = true`（组织有 Provider） | **形态 B** | "Bind an existing provider"（内嵌 dropdown 选 Provider 后批量绑定） / "Add a Remote Judge Server"（打开 Quick Setup） |

两种形态都是两张并排卡片，等宽，等视觉权重。Modal 右上角 ✕ 关闭。

**形态 A 关键交互**：

- 点击 "Configure Provider →" → 跳转到 Provider 创建页面，Modal 关闭。**不维护回流**——用户创建完 Provider 后自行返回 Scorers 标签。
- 返回 Scorers 标签后，由于 `has_providers` 变为 true，Banner 仍显示（`all_unbound` 仍为 true），但点击 Banner 时弹出的是形态 B。
- 这是一次"两次旅程"的设计：先创建 Provider，再绑定到 Scorer。每次旅程都是独立完整的，无中间状态。

**形态 B 关键交互**：

- 卡片内嵌 Provider dropdown，列出该组织所有 Provider（按 name 字母排序）。
- 选择 Provider 并点击 "Bind to all scorers" 后，后端执行批量更新：
  ```sql
  UPDATE scorer
  SET provider_id = $selected_provider_id, updated_at = NOW()
  WHERE org_id = $org_id AND provider_id IS NULL;
  ```
- Modal 关闭，Scorer 列表刷新，顶部短暂 toast：`{N} scorers bound to {provider_name}`。
- Banner 自然消失（`all_unbound` 变为 false）。

**两种形态的右侧卡片相同**："Add a Remote Judge Server" → 关闭当前 Modal，打开 Quick Setup Modal。

详细视觉规范、文案、边界情况参见 [01 子文档 §4](./01_provider_setup_bar_and_modal.md#4-setup-modal)。

### §1.4 Quick Setup Modal

Quick Setup Modal 让用户**一次性创建 8 个 Remote Scorer**，每个指向用户自行部署的参考 Remote Judge Server。

**入口**：
1. Provider 引导 Modal 右侧卡片的 "Add Remote Server →" 按钮
2. Scorers 标签工具栏永久入口（与 "+ New scorer" 平级的 "Quick setup" 链接）
3. 直接 URL 导航

**Modal 单页结构**（非 wizard，所有段落同屏纵向排列）：

| 段落 | 内容 |
|---|---|
| Section 1 — Deploy the server | Docker 命令片段（OpenAI 版本作为默认）+ Copy 按钮 + 部署文档链接（→ GitHub README） |
| Section 2 — Connection details | Server URL 输入框 + Auth token 输入框（密码风格） + Test connection 按钮 + 测试结果显示 |
| Section 3 — Scorers to create | 默认折叠为 "All 8 scorers (default)"。展开后列出 8 个维度，已存在的 Scorer 名禁用并标 "already exists"。最下方为 Create scorers 主按钮 |

**Create scorers 点击后进入执行模式（流式逐个创建）**：

- Section 1、2 转为只读
- Section 3 的复选框列表**转换为进度列表**，每行带状态 icon：
  - ⏳ pending（等待中）
  - ⟳ in progress（进行中，spinner 动画）
  - ✓ created（成功）
  - ✗ failed（失败，旁边显示简短错误）
- 前端**严格串行**调用 N 次创建 API，每次完成后更新对应行
- 任一 Scorer 失败 → 立即停止后续，显示详细错误说明，下方按钮：[Retry] [Cancel]

**Retry 行为**：使用当前 URL 与 token，从失败的那个 Scorer 继续，不重复处理已成功的。**用户不能在执行模式下修改 URL/token**——要改必须 Cancel 重来。

**Cancel 行为**：
- 立即中断当前进行中的 HTTP 请求
- Modal 关闭
- 已创建的 Scorer 保留在数据库（无回滚）
- 无 toast，无确认弹窗
- 用户下次再进 Quick Setup 时，已创建的 Scorer 在 Section 3 显示为 "already exists" 禁用状态

**全部成功后**：底部出现 "All N scorers created successfully." + Done 按钮。点 Done 关闭 Modal、刷新 Scorer 列表（新 Scorer 高亮 3–5 秒）、顶部 toast `N remote scorers created`。

**幂等性语义**：已存在的 Scorer name 在 Section 3 即被禁用，不会进入执行队列。**已存在的 Scorer 不更新 token、不更新 URL**——Quick Setup 永远是 additive，不修改已有数据。需要 rotate token 的用户走 Scorer 详情页手动改。

详细视觉规范、错误文案、状态机参见 [02 子文档](./02_quick_setup_remote_judge_server.md)。

### §1.5 三个组件的状态流转图

```
用户进入 Scorers 标签
    │
    ▼
执行查询，计算 show_banner
    │
    ├──── false ──→ 无 Banner，直接显示 Scorer 列表
    │
    └──── true ───→ 显示 Banner
                       │
                       │（用户点击）
                       ▼
                  弹出 Provider 引导 Modal
                       │
              ┌────────┴────────┐
              │                  │
       has_providers=false   has_providers=true
              │                  │
              ▼                  ▼
          形态 A             形态 B
              │                  │
   ┌──────────┼──────────┐    ┌──┴────────────┐
   │          │          │    │                │
   ▼          ▼          ▼    ▼                ▼
"Configure  "Add      ✕   "Bind"          "Add Remote"
 Provider"  Remote"            │
   │        Server"            ▼
   ▼          │           后端批量绑定
跳走（不回流） │           Banner 消失
   │          │
   └──────────┴────────────────────────┐
                                        ▼
                              Quick Setup Modal
                                        │
                              （详细流程见 [02 子文档]）
```

---

## §2 预置 Score Config 与 Scorer

完整定义在 [03 子文档](./03_builtin_score_configs_and_scorers.md)。本节仅给出高层概览，供主文档读者快速理解范围。

### §2.1 12 个预置 Score Config 概览

| 类别 | 数量 | 维度 | 类型分布 |
|---|---|---|---|
| Span-level（带 Scorer） | 8 | hallucination, answer_relevance, coherence, helpfulness, instruction_following, toxicity, bias, output_format | 4 numeric + 2 categorical + 2 boolean |
| Trace-level（仅 Score Config，Scorer 等 Phase 3.1） | 4 | context_relevance, context_recall, faithfulness, answer_correctness | 4 numeric |

混合类型分布是刻意设计：每个维度按其天然粒度选择类型。Bias 是是/否判断，toxicity 是分级谱系，hallucination 是连续质量分数。强制全 numeric 会让 bias 的 0.37 分缺乏可解释性。

### §2.2 8 个预置 LLM Judge Scorer 概览

- **Scorer name 与对应 Score Config 同名**（不同表，独立 unique 命名空间）。
- 每个 Scorer 携带完整 English judge prompt 模板。
- 默认 model settings：`temperature = 0`，启用结构化输出。
- 默认 input mapping 遵循 OpenTelemetry GenAI 语义约定：`gen_ai.prompt`、`gen_ai.completion`。
- `provider_id` 初始为空，通过 Provider 引导 Modal 绑定。

### §2.3 Trace-level Score Config 的 Scorer 限制

在 Scorer 创建表单中，当用户选择 trace-level Score Config 作为目标时：

- LLM Judge Scorer 类型 **不可选**（灰掉，鼠标悬停提示"Trace-level Scorers 在 Phase 3.1 上线"）
- Code Scorer 类型 **不可选**（同上）
- Remote Scorer 类型 **可选**——用户可以自行实现 trace 取值并通过 Remote Scorer 协议对接

完整清单、字段定义、attribution 列表、完整 prompt 全文参见 [03 子文档](./03_builtin_score_configs_and_scorers.md)。

---

## §3 种子数据加载机制

### §3.1 触发方式：Per-org Lazy Seed

种子数据**不在 OpenObserve 启动时一次性插入所有组织**，而是在每个组织**首次访问 Online Eval 模块的任一列表 API 时**懒加载。

触发点：以下任一 API 的 handler 入口调用 `builtin_seed::seed_for_org(db, org_id)`：

- `GET /api/{org_id}/eval/score_configs`
- `GET /api/{org_id}/eval/scorers`
- `GET /api/{org_id}/eval/jobs`

具体哪些 endpoint 触发，由实施时按现有 handler 列表确定。原则是覆盖所有用户首次进入 Online Eval 模块时会调用的列表 endpoint。

### §3.2 加载流程

```
seed_for_org(db, org_id) 的执行步骤：

1. Fast path: 检查 meta 表 settings JSON 中是否有 `online_eval_seeded` key
   ├── 有 → 立即返回（这是已 seed 过的组织上每次访问的路径，开销为一次 SELECT）
   └── 无 → 继续

2. 检查部署级 opt-out 配置 `disable_builtin_seed`
   ├── true → 返回 skipped
   └── false → 继续

3. 获取该 org_id 的进程内 Mutex（避免同进程内并发首次访问引发重复插入）

4. 加锁后重新检查 flag（另一个请求可能已 seed 完成）

5. 检查该组织 score_config 表是否已有任意行
   ├── 有（Phase 2.0 升级来的组织，已建过自己的 config） 
   │   → 写入 flag {"skipped": "pre_existing_data", "at": ...}
   │   → 返回 skipped（尊重用户已有数据）
   └── 无 → 继续

6. 在单一 Postgres 事务内：
   - INSERT 12 个 Score Config 到 score_config 表
   - INSERT 8 个 LLM Judge Scorer 到 scorer 表
   - 在 meta 表写入 flag {"seeded_at": ..., "version": "2.1.0"}
   - 事务 commit

7. 处理跨进程 race：
   - 事务 commit 失败且错误为 Postgres unique violation (SQLSTATE 23505)
   - 说明另一个 OpenObserve 实例已 seed 完成
   - 捕获错误，写入 flag {"via": "race_loser_recovery"}
   - 返回成功
```

### §3.3 固定 UUID 派生

预置 Score Config 与 Scorer 的 UUID 由代码常量决定，使用固定命名空间 UUID + UUID v5 派生：

- 命名空间 UUID：`4f3a8c12-7b2e-4d91-a5f6-1c8d9e3b7a04`（写死在代码中，永不变更）
- Score Config UUID：`uuid_v5(NAMESPACE, "score_config." + name)`
- Scorer UUID：`uuid_v5(NAMESPACE, "scorer." + name)`

固定 UUID 的**唯一目的是让种子插入时的外键关联是确定性的**——`scorer.score_config_id` 在插入时直接引用代码常量计算出的 UUID，无需"插入后查询 id 再插入"两步走。固定 UUID **不是产品身份**，用户看不到、产品不暴露。

### §3.4 Flag 存储

`online_eval_seeded` flag 写入 meta 表 `settings` JSON 列的顶级 key：

```json
{
  "online_eval_seeded": {
    "seeded_at": "2026-05-19T10:23:11Z",
    "version": "2.1.0"
  }
}
```

产品代码只检查 flag **存在性**，不读取值。值是信息性的，便于运维和支持团队诊断。

Flag payload 三种形态：

| 场景 | Payload |
|---|---|
| 正常首次 seed | `{"seeded_at": "...", "version": "2.1.0"}` |
| 已有 Score Config 跳过 | `{"skipped": "pre_existing_data", "at": "..."}` |
| 跨进程 race 失败者恢复 | `{"seeded_at": "...", "via": "race_loser_recovery"}` |

### §3.5 不重新 seed 已删除的数据

Flag 一旦设置，**OpenObserve 永远不重新 seed**，即使用户后续删除全部预置 Score Config 与 Scorer。删除是用户的明确选择，OpenObserve 尊重它。

如果用户希望"恢复预置"，他可以：
- 手动 SQL 删除 meta 表中的 `online_eval_seeded` flag（运维操作）
- 或参考源码 `BUILTIN_SEED.md` 文档手动创建所需 Score Config 与 Scorer

主产品**不提供"恢复预置"按钮**。理由：恢复机制会重新引入"预置 vs 用户创建"的概念区分，违反"预置即普通数据"的设计原则。

### §3.6 Migration 阶段的 Catalog 完整性检查

SeaORM migration 在启动时执行一次 `verify_catalog_integrity()`：

- 校验 12 个 Score Config name 唯一
- 校验 8 个 Scorer name 唯一
- 校验每个 Scorer 的 `score_config_id` 指向真实的 Score Config
- 校验所有 Scorer 引用的 Score Config 都是 `level = "span"`（trace Scorer 不在 Phase 2.1 范围）

**Migration 阶段不做任何 DB 写入**。它只确保代码层面的种子常量数据一致——如果未来有人加新维度时写错（如 Scorer 指向不存在的 Score Config），启动期立即失败，而不是首次访问 Online Eval 模块时才暴露。

---

## §4 参考 Remote Judge Server

### §4.1 实现目标

`openobserve/eval-judges` 是一个**独立公开仓库**，与 OpenObserve 主产品解耦。目标：

- 用户在自己的环境内通过单一 `docker run` 命令部署一个 HTTP 服务
- 服务实现 Phase 2 Online Eval Spec §4.4 定义的 Remote Scorer 协议
- 用户可在 OpenObserve 中创建 Remote Scorer，指向该服务的 URL
- 服务覆盖与主仓库种子相同的 8 个 span-level 维度（Trace 维度等 Phase 3.1）

**战略价值**：参考 server 是 OpenObserve 在 LLM observability 市场上对 air-gapped / 私有部署客户的核心差异化点。Langfuse、Braintrust 等竞品都没有开箱即用的、客户可独立部署的 Judge Server。

### §4.2 两种部署模式

参考 server 通过环境变量切换两种工作模式：

**模式 X：调用外部托管 Provider**

```
O2_JUDGE_PROVIDER=openai
O2_JUDGE_API_KEY=sk-...
O2_JUDGE_MODEL=gpt-4o-mini
```

server 内部调用 OpenAI / Anthropic 等托管 API 完成评分。trace 内容**会离开**客户环境（传给外部 LLM API）。

适用场景：快速上手；客户已签订商用 LLM API 合规协议。

**模式 Y：调用本地模型 endpoint**

```
O2_JUDGE_PROVIDER=openai_compatible
O2_JUDGE_URL=http://internal-llm:8000/v1
O2_JUDGE_MODEL=llama-3.1-70b-instruct
```

server 内部调用 OpenAI 兼容 endpoint（Ollama、vLLM、自有推理集群）。trace 内容**永不离开**客户环境。

适用场景：air-gapped、数据敏感、合规要求严格。

两种模式在同一个 Docker 镜像中共存，通过环境变量切换。

### §4.3 API 定义

参考 server 暴露以下 HTTP 端点：

#### `POST /evaluate`

**功能**：对单个 span/trace 输入执行评分。

**请求**：

```http
POST /evaluate
Authorization: Bearer <token>
Content-Type: application/json

{
  "scorer_name": "hallucination",
  "input": "<span 的 input 字段，可选>",
  "output": "<span 的 output 字段>",
  "expected": "<可选，Experiment 模式下提供 ground truth>",
  "metadata": {
    "additional_context": "..."
  }
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scorer_name` | string | 是 | 路由到内部哪个 judge 实现的关键字。可选值为参考 server 实现的 8 个维度名（与主仓库 Score Config name 一致） |
| `input` | string | 否 | 评分的输入内容（如用户问题）。是否需要取决于 scorer_name |
| `output` | string | 是 | 评分的输出内容（如模型输出） |
| `expected` | string | 否 | Ground truth 内容，仅 Experiment 模式或部分维度（如 answer_correctness）需要 |
| `metadata` | object | 否 | 透传字段，参考 server 可选择使用或忽略 |

**响应**：

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "value": 0.73,
  "metadata": {
    "reason": "<judge 的 chain-of-thought>",
    "model": "gpt-4o-mini",
    "elapsed_ms": 1245
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `value` | number / string / boolean | 评分结果。类型按 Score Config 的 value_type 返回（numeric → number；categorical → string；boolean → boolean） |
| `metadata.reason` | string | judge 的推理过程，方便 OpenObserve 端调试与展示 |
| `metadata.model` | string | 实际使用的 LLM 模型名 |
| `metadata.elapsed_ms` | integer | server 内部评分耗时 |

**错误响应**：

| HTTP 状态 | 说明 |
|---|---|
| 400 | 请求体无效（缺少必填字段、scorer_name 不支持） |
| 401 | Authorization 头缺失或 token 无效 |
| 500 | server 内部错误（LLM API 调用失败、解析失败等） |
| 502 | server 与下游 LLM API 通信失败 |
| 504 | server 调用 LLM 超时 |

#### `GET /health`

**功能**：健康检查，供 OpenObserve Quick Setup 流程的 "Test connection" 按钮使用。

**请求**：

```http
GET /health
Authorization: Bearer <token>
```

**响应（成功）**：

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

**响应（失败）**：401 / 503 等标准 HTTP 状态码。

#### `GET /version`

**功能**：返回 server 版本号，供 OpenObserve 端兼容性检查使用。

**请求**：无需 Authorization。

**响应**：

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "version": "0.1.0",
  "api_version": "v1"
}
```

`api_version` 用于 OpenObserve 端做协议兼容性判断。同一 `api_version` 内的 server 版本对主产品前向兼容。

### §4.4 实施建议

**首版可考虑使用 DeepEval 简化开发**。DeepEval（Apache 2.0 协议）已经实现了 hallucination、bias、toxicity、answer_relevance 等多个维度的 LLM-Judge 评分逻辑。参考 server 首版可以：

1. 使用 Python + FastAPI 作为 HTTP 框架
2. 内部委托给 DeepEval 完成具体评分
3. 在 FastAPI 层做 API 契约适配（OpenObserve Remote Scorer 协议 ↔ DeepEval 调用）
4. Backend 抽象层支持 Mode X 与 Mode Y 切换

这是一个**快速发版的实施选择**，**不是长期承诺**。§4.3 的 API 契约才是持久的产物。未来可以替换为：

- 把 prompt 内化（按 Apache 2.0 / MIT 协议提取），直接调用 LLM API 不经 DeepEval
- 迁移到非 Python 语言（如 Rust 提升性能）
- 任何上述变化对参考 server 的所有消费者透明，因为 API 契约不变

**架构、文件结构、CI、Dockerfile、测试策略**等具体设计**不在本文档范围**——由 `openobserve/eval-judges` 仓库的独立设计文档处理。本文档只约束 API 契约和实施目标。

### §4.5 仓库范围约束

`openobserve/eval-judges` 仓库的 `CONTRIBUTING.md` 携带一条硬性范围约束：

> 本仓库托管 10–15 个通用评分维度（首版 8 个 span 维度 + Phase 3.1 之后追加的 trace 维度）。垂直领域（医疗安全、法律准确性、金融合规）、特定语言（中文语法、日语敬语）、特定 use case（RAG 专用变体、Agent trajectory 评分）的维度**不在本仓库范围内**。鼓励贡献者 fork 本仓库托管垂直或专用 judge 集合，遵循同样的 API 契约——这些 fork 将以 drop-in Remote Scorer 形式与 OpenObserve 互操作，无需任何额外集成工作。

这条约束在仓库层面保护 OpenObserve "unopinionated infrastructure" 立场。

### §4.6 版本化与发版节奏

参考 server 与主 OpenObserve 产品**独立版本化**。其发版节奏预期比主产品更快（小项目、API 表面窄）。tag 约定遵循 semver。API 契约的稳定性由主版本号管理（同 major 内前向兼容）。

主产品（OpenObserve）与参考 server 间的交叉引用通过 `/version` 端点完成。Quick Setup 流程在创建 Remote Scorer 时调用 `/version` 捕获 server 版本，存入 Remote Scorer 的 metadata，便于后续诊断。

---

## §5 实施路径

### §5.1 工作分解

Phase 2.1 可分解为 5 个独立工作项：

| 项 | 依赖 | 估算工作量 |
|---|---|---|
| **A. 12 个 Score Config + 8 个 Scorer 内容**（[03 子文档](./03_builtin_score_configs_and_scorers.md) 已完成） | 无 | 已完成 |
| **B. 种子数据加载机制**（per-org lazy seed + flag 写入 + integrity check migration） | A | 3–5 天 |
| **C. Provider 引导条 + Modal + 一次性绑定 API**（前端 + 后端） | 无（与 A、B 并行） | 5–7 天 |
| **D. 参考 Remote Judge Server 仓库**（`openobserve/eval-judges`） | A（共享 prompt 内容） | 2–3 周 |
| **E. Quick Setup UI 流程**（前端） | D（需要 server API 就绪） | 5–7 天 |

A 到 C 是纯主仓库工作，可作为 v2.1 patch release 独立 ship，不依赖 D 和 E。D 是新仓库，可由另一个工程师并行开发。E 依赖 D 就绪。

### §5.2 发版选项

**选项 α（推荐）：A + B + C 作为 v2.1，D + E 作为 v2.2**

- **v2.1**（约 2–3 周后）：种子数据 + Provider 引导。立刻改善所有 v2.0 用户的 onboarding 体验。
- **v2.2**（约 v2.1 之后 5–7 周）：参考 Remote Judge Server + Quick Setup。独立可营销叙事："OpenObserve 现在 ship 一个 Docker 可部署的 judge server，用于 air-gapped LLM 评分"。

两个发版时点，两个叙事节奏。工作可无空闲串行（D 在 A 完成后即可启动），因此两次发版总时间与一次性发版相同。

**选项 β：A + B + C + D + E 一起作为 v2.1**

- 一次发版，总计约 5–7 周。单次宣传效应更强。
- 牺牲了中间可见性里程碑。

α 与 β 的选择取决于团队对发版节奏的偏好。技术工作相同，仅发版打包不同。

### §5.3 与现有 Phase 2.0 部署的兼容性

现有 v2.0 部署升级到 v2.1 后：

- **已建过自己的 Score Config 的组织**：lazy seed 流程检测到 `score_config` 表非空，写入 flag `{"skipped": "pre_existing_data"}`，**不插入预置数据**。尊重用户已有选择。
- **还没建过任何 Score Config 的组织**（鉴于冷启动问题，可能数量不少）：首次访问 Online Eval 模块时收到种子批次。这是预期行为。

提供部署级配置 flag `disable_builtin_seed = true`，给希望完全 opt-out 种子的运维。

---

## §6 与其他 Phase 的关系

### §6.1 对 Phase 2.0 的关系

Phase 2.1 对 Phase 2.0 **纯增量**：

- 不修改任何 Phase 2.0 产品对象、表、行为
- 不修订、不撤回、不矛盾任何 Phase 2.0 决策
- 种子数据方式之所以可行，恰恰是因为 Phase 2.0 把 Score Config 和 Scorer 作为带完整 CRUD 的一等用户拥有对象——"预置"不需要任何特殊 API 表面，也不需要任何 schema 标记

### §6.2 对 Phase 2.5 的关系

Phase 2.5（Annotation Queue + Dataset + Prompt Management UI）与 Phase 2.1 完全独立、可并行。无共享依赖、修改产品的不同部分。

唯一的正向交互：Phase 2.5 的 Annotation Queue UI 基于 Score Config schema 渲染表单。12 个预置 Score Config 的存在给 Phase 2.5 提供了第一天就能用的真实测试 fixture，免去合成测试数据的麻烦。

### §6.3 对 Phase 3.1 的关系

Phase 3.1 的 Trace Scorer（跨 span 评分，覆盖 RAG / Agent / 多步骤）将让 Phase 2.1 ship 的 4 个 trace-level Score Config 真正可用。

具体而言：

- Phase 2.1 ship 4 个 trace Score Config，**无对应 Scorer**
- Phase 3.1 引入 Trace Scorer 产品对象（支持跨 span 取值），同时通过同一套 lazy seed 机制（不同的 flag key `trace_eval_seeded`），为存在 trace Score Config 的组织追加对应的 LLM Judge Trace Scorer
- 可同步 ship 更多 RAG 专属 trace 维度作为 Phase 3.1 增量

Phase 2.1 的设计选择——固定 UUID 派生、per-org lazy seed + flag 机制、不增加任何 schema 标记——**有意设计为可无修改地用于 Phase 3.1**。机制可扩展。

---

## §附录 A 关键设计决策回顾

| ID | 决策 | 章节 |
|---|---|---|
| `§ColdStart-D1` | 不增加任何区分"预置 vs 用户创建"的列；预置数据与用户数据在数据层和产品层完全无别。固定 UUID 仅用作种子插入时的外键关联实现手段，不是产品身份 | §0, §3.3 |
| `§ColdStart-D2` | 预置数据不做版本化、不做升级。修订只影响未来首次冷启动的组织 | §3.5 |
| `§ColdStart-D3` | UI 层面预置与用户创建对象完全无视觉区分（无 chip、badge、分段、特权排序、只读状态） | §1, [03] |
| `§ColdStart-D4` | 12 个预置维度：8 个 span（带 Scorer）+ 4 个 trace（仅 Score Config，等 Phase 3.1）；类型分布 4 numeric + 2 categorical + 2 boolean + 4 numeric（trace） | §2, [03] |
| `§ColdStart-D5` | Provider 引导使用 Provider 创建/绑定时的显式动作；不引入 `default_provider` 概念，不维护 Banner 跳转后的回流状态 | §1.3 |
| `§ColdStart-D6` | 种子插入采用 per-org lazy seed + meta 表 settings JSON flag (`online_eval_seeded`)；flag 一旦设置永不重新种子 | §3.1, §3.5 |
| `§ColdStart-D7` | Quick Setup 幂等：已存在的 Scorer 跳过，不更新 token、不更新 URL；要 rotate token 走 Scorer 详情页 | §1.4 |
| `§ColdStart-D8` | 参考 judge server 在独立仓库 ship，永不打包进主二进制 | §4.1 |
| `§ColdStart-D9` | 提供部署级 opt-out（`disable_builtin_seed`）给希望清洁安装的运维 | §5.3 |
| `§ColdStart-D10` | Phase 2.1 对 Phase 2.0 纯增量；不修订任何 Phase 2.0 决策 | §6.1 |
| `§ColdStart-D11` | 参考 server 的 API 契约与任何其他 Remote Scorer 完全相同；不是特权后端 | §4.3 |
| `§ColdStart-D12` | 参考 server 仅托管 10–15 个通用维度；垂直/领域维度鼓励作为社区 fork | §4.5 |
| `§ColdStart-D13` | Quick Setup 后 LLM Judge Scorer 和 Remote Scorer 共存；由用户手动精简 | §1.4 |
| `§ColdStart-D14` | Attribution 仅保留在源码注释和维护文档，不进入用户数据库、不进入 UI | [03] §2.4 |
| `§ColdStart-D15` | 预置 LLM Judge Scorer 的 name 与对应 Score Config 同名（不同表，独立命名空间） | §2.2, [03] §2 |
| `§ColdStart-D16` | 数据库 backend 只考虑 Postgres；unique violation 检测基于 SQLSTATE 23505 | §3.2 |
| `§ColdStart-D17` | Banner 触发条件为"所有 Scorer 都没绑 Provider"（方案 P），而非"任意 Scorer 没绑"。理由：Banner 的目的是冷启动引导，用户绑了任意一个说明已掌握操作方法 | §1.2 |
| `§ColdStart-D18` | Quick Setup 流式逐个创建，失败时停止并显示 Retry/Cancel；Retry 从失败处继续，已成功的不重复 | §1.4 |
| `§ColdStart-D19` | 参考 server 首版可使用 DeepEval 简化开发；API 契约稳定，内部实现可后续替换 | §4.4 |

---

## §附录 B 术语表

| 术语 | 定义 |
|---|---|
| 预置 / Built-in（口语） | 由 OpenObserve 通过种子机制为新组织插入的 Score Config 和 Scorer。**不是**一个产品类别——数据层和产品层无任何标记区分预置与用户创建。 |
| 种子数据 / Seed data | OpenObserve ship 的 12 个 Score Config 和 8 个 LLM Judge Scorer 的代码常量。组织首次访问 Online Eval 模块时 lazy 插入数据库。 |
| Lazy seed | Per-org 首次访问时的延迟种子插入流程。详见 §3.1。 |
| Banner（提示条） | Scorers 标签内的非阻塞提示条，提示"预置 Scorer 需要绑定 Provider"。点击后弹出 Provider 引导 Modal。详见 §1.2、[01 子文档](./01_provider_setup_bar_and_modal.md)。 |
| Provider 引导 Modal | 用户点击 Banner 后弹出的 Modal，分两种形态（A：无 Provider；B：有 Provider）。详见 §1.3、[01 子文档](./01_provider_setup_bar_and_modal.md)。 |
| Quick Setup Modal | 一次性创建 8 个 Remote Scorer 指向参考 Remote Judge Server 的 Modal。详见 §1.4、[02 子文档](./02_quick_setup_remote_judge_server.md)。 |
| 参考 Remote Judge Server | 位于 `openobserve/eval-judges` 的独立 HTTP 服务，实现 Remote Scorer 协议。详见 §4。 |
| 模式 X | 参考 server 配置为调用外部托管 LLM API（OpenAI、Anthropic 等）。详见 §4.2。 |
| 模式 Y | 参考 server 配置为调用客户托管的 OpenAI 兼容 endpoint（本地模型）；数据不出环境。详见 §4.2。 |
| `online_eval_seeded` | 写入组织 meta 表 settings JSON 的 flag，标识该组织已完成 Phase 2.1 种子加载。详见 §3.4。 |
| `trace_eval_seeded` | Phase 3.1 预留的 flag key，标识该组织已完成 trace 维度的种子加载（TBD）。 |
| 固定命名空间 UUID | 写死在代码中的 UUID `4f3a8c12-7b2e-4d91-a5f6-1c8d9e3b7a04`，用于通过 UUID v5 派生所有种子数据的稳定 UUID。详见 §3.3。 |
