# GW2Radar MVP 0.1 研制规范

```text
项目名称：GW2Radar
版本：MVP 0.1
版本主题：Legendary Goal Intelligence Edition
中文名：个人传奇目标情报图谱版
目标受众：Codex / Cursor / OpenCode 开发代理
文档用途：作为 GW2Radar MVP 0.1 的研发输入规范、任务边界、验收标准和代码实现约束
```

---

## 1. 版本定位

GW2Radar MVP 0.1 的目标不是构建完整 GW2 工具站，也不是复刻 GW2Efficiency、MetaBattle 或 Wiki。

MVP 0.1 只验证一条最小闭环：

```text
玩家目标
→ 目标需求
→ 玩家已有资源
→ 缺口计算
→ 行动建议
→ Markdown 报告
```

一句话定位：

> GW2Radar MVP 0.1 是一个以 Legendary Goal 为核心的个人游戏情报图谱原型，能够基于账号状态和目标需求，生成缺口清单、材料保留建议和每日/每周行动建议。

---

## 2. MVP 0.1 核心目标

本版本只做以下核心能力：

```text
1. 建立 GW2Radar 基础工程骨架；
2. 建立 Entity / Attribute / Relation / Action / Evidence 基础本体；
3. 建立关系型图谱存储模型；
4. 支持 mock GW2 account 数据；
5. 支持 mock Legendary Goal 数据；
6. 计算目标缺口；
7. 生成 HOLD / BUY / FARM / DO_DAILY / RESERVE_FOR_GOAL 等 Action；
8. 生成 Markdown 格式的个人目标情报报告；
9. 提供基础 FastAPI 接口；
10. 提供 pytest 自动化测试。
```

本版本不追求真实 GW2 API 全量接入。真实 API client 可以保留接口骨架，MVP 验收以 mock 数据闭环为准。

---

## 3. 非目标范围

MVP 0.1 明确不做以下内容：

```text
1. 不做完整前端 UI；
2. 不做登录系统；
3. 不做用户账号体系；
4. 不做真实支付；
5. 不做完整交易所历史价格；
6. 不做 Build Fit 分析；
7. 不做 Patch Impact 分析；
8. 不做公会团队分析；
9. 不做自动游戏操作；
10. 不做自动交易、自动下单、自动刷材料、外挂 Overlay 或任何违反游戏规则的自动化行为。
```

所有建议必须是信息分析与手动行动建议。

---

## 4. 技术栈要求

```text
Language: Python 3.11+
Backend: FastAPI
Schema: Pydantic v2
Database ORM: SQLAlchemy 2.x
Migration: Alembic
Database: SQLite for MVP
Testing: pytest
Report: Markdown
Package: pyproject.toml
Style: type hints required
```

MVP 0.1 允许先不接 Neo4j。图谱通过 `entities`、`relations`、`evidence`、`player_state`、`actions` 等表实现。

---

## 5. 推荐项目结构

```text
gw2radar/
├── README.md
├── pyproject.toml
├── .env.example
├── docs/
│   ├── ontology/
│   │   ├── GW2_ONTOLOGY_CORE.md
│   │   ├── ENTITY_TYPES.md
│   │   ├── ATTRIBUTE_SCHEMA.md
│   │   ├── RELATION_TYPES.md
│   │   ├── ACTION_SCHEMA.md
│   │   └── INFERENCE_RULES.md
│   ├── graph/
│   │   ├── GRAPH_PIPELINE.md
│   │   ├── EVIDENCE_MODEL.md
│   │   └── LEGENDARY_GOAL_GRAPH.md
│   └── mvp/
│       └── MVP_0_1_LEGENDARY_GOAL.md
├── src/
│   └── gw2radar/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── goals.py
│       │       ├── actions.py
│       │       └── reports.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py
│       ├── db/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── session.py
│       │   └── init_db.py
│       ├── ingest/
│       │   ├── __init__.py
│       │   ├── gw2_api_client.py
│       │   └── mock_loader.py
│       ├── ontology/
│       │   ├── __init__.py
│       │   ├── entity_types.py
│       │   ├── relation_types.py
│       │   ├── action_types.py
│       │   └── schemas.py
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── entity_store.py
│       │   ├── relation_store.py
│       │   ├── graph_builder.py
│       │   └── graph_query.py
│       ├── inference/
│       │   ├── __init__.py
│       │   ├── goal_gap.py
│       │   ├── material_policy.py
│       │   ├── action_generator.py
│       │   └── action_ranker.py
│       ├── reports/
│       │   ├── __init__.py
│       │   └── markdown_report.py
│       └── fixtures/
│           ├── mock_account.json
│           ├── mock_goal_aurora.json
│           ├── mock_items.json
│           └── mock_tasks.json
└── tests/
    ├── test_ontology.py
    ├── test_graph_builder.py
    ├── test_goal_gap.py
    ├── test_material_policy.py
    ├── test_action_generator.py
    └── test_markdown_report.py
```

---

## 6. 本体设计要求

MVP 0.1 必须实现四类核心对象：

```text
Entity    游戏实体
Attribute 实体属性
Relation  实体关系
Action    可执行建议动作
Evidence  证据来源
```

### 6.1 EntityType

必须至少支持：

```python
class EntityType(str, Enum):
    ACCOUNT = "account"
    CHARACTER = "character"
    GOAL = "goal"
    ITEM = "item"
    MATERIAL = "material"
    CURRENCY = "currency"
    ACHIEVEMENT = "achievement"
    COLLECTION = "collection"
    TASK = "task"
    ACTION = "action"
    TRADING_POST_PRICE = "trading_post_price"
    SOURCE = "source"
    EVIDENCE = "evidence"
```

### 6.2 RelationType

必须至少支持：

```python
class RelationType(str, Enum):
    REQUIRES = "requires"
    CONSUMES = "consumes"
    PRODUCES = "produces"
    USED_IN = "used_in"
    OWNED_BY = "owned_by"
    HAS_PRICE = "has_price"
    MISSING_FOR_GOAL = "missing_for_goal"
    ADVANCES_GOAL = "advances_goal"
    BLOCKS_GOAL = "blocks_goal"
    RESERVES_FOR_GOAL = "reserves_for_goal"
    ACQUIRED_BY = "acquired_by"
```

### 6.3 ActionType

必须至少支持：

```python
class ActionType(str, Enum):
    BUY = "buy"
    FARM = "farm"
    CRAFT = "craft"
    HOLD = "hold"
    RESERVE_FOR_GOAL = "reserve_for_goal"
    SELL_SURPLUS = "sell_surplus"
    DO_DAILY = "do_daily"
    DO_WEEKLY = "do_weekly"
    COMPLETE_ACHIEVEMENT = "complete_achievement"
    WATCH_PRICE = "watch_price"
    GENERATE_DAILY_PLAN = "generate_daily_plan"
    GENERATE_WEEKLY_PLAN = "generate_weekly_plan"
```

---

## 7. 数据库模型要求

MVP 0.1 至少实现以下数据表。

### 7.1 entities

```text
id: string primary key
type: string
canonical_name: string
external_id: string nullable
properties_json: JSON
created_at: datetime
updated_at: datetime
```

### 7.2 relations

```text
id: string primary key
subject_id: string
predicate: string
object_id: string
properties_json: JSON
evidence_id: string nullable
confidence: float
valid_from: datetime nullable
valid_to: datetime nullable
created_at: datetime
```

### 7.3 evidence

```text
id: string primary key
source: string
source_url: string nullable
fetched_at: datetime
raw_hash: string nullable
raw_payload: JSON nullable
confidence: float
```

### 7.4 player_state

```text
id: string primary key
account_id: string
entity_id: string
quantity: float
location: string nullable
observed_at: datetime
```

### 7.5 actions

```text
id: string primary key
action_type: string
title: string
description: string nullable
target_entity_id: string nullable
target_goal_id: string nullable
priority_score: float
urgency: string
properties_json: JSON
explanation: string
created_at: datetime
```

---

## 8. Mock 数据要求

必须提供一组可以完整跑通 MVP 的 mock 数据。

### 8.1 mock account

示例账号：

```json
{
  "account_id": "mock:account:lee",
  "wallet_gold": 120,
  "materials": {
    "gw2:item:mystic_coin": 120,
    "gw2:item:mystic_clover": 34,
    "gw2:item:glob_of_ectoplasm": 180
  },
  "currencies": {
    "gw2:currency:unbound_magic": 800
  },
  "achievements": {
    "gw2:achievement:aurora_step_x": 0
  }
}
```

### 8.2 mock goal: Aurora

示例目标：

```json
{
  "goal_id": "gw2:goal:aurora",
  "name": "Aurora",
  "goal_type": "legendary_trinket",
  "requirements": [
    {
      "entity_id": "gw2:item:mystic_coin",
      "type": "item",
      "required_quantity": 77
    },
    {
      "entity_id": "gw2:item:mystic_clover",
      "type": "item",
      "required_quantity": 77
    },
    {
      "entity_id": "gw2:currency:unbound_magic",
      "type": "currency",
      "required_quantity": 3000
    },
    {
      "entity_id": "gw2:achievement:aurora_step_x",
      "type": "achievement",
      "required_quantity": 1
    }
  ]
}
```

### 8.3 mock tasks

示例任务：

```json
[
  {
    "task_id": "gw2:task:bitterfrost_daily",
    "name": "Bitterfrost Frontier Daily Route",
    "action_type": "do_daily",
    "produces": [
      {
        "entity_id": "gw2:currency:unbound_magic",
        "estimated_quantity": 250
      }
    ],
    "estimated_minutes": 20,
    "repeatability": "daily",
    "requires_group": false
  }
]
```

---

## 9. 推理规则要求

### 9.1 Goal Gap 推理

输入：

```text
Goal requirements
Account owned quantities
```

输出：

```text
completed requirements
missing requirements
surplus quantities
MISSING_FOR_GOAL relations
```

规则：

```text
if owned_quantity >= required_quantity:
    missing_quantity = 0
else:
    missing_quantity = required_quantity - owned_quantity
```

### 9.2 Material Policy 推理

必须生成以下策略：

```text
1. 如果材料被 active goal 需要，生成 HOLD 或 RESERVE_FOR_GOAL；
2. 如果材料已有数量不足，生成 BUY / FARM / CRAFT 候选；
3. 如果材料可交易且非目标所需，才允许生成 SELL_SURPLUS；
4. MVP 0.1 中默认不主动建议出售 Legendary 相关材料。
```

### 9.3 Action 生成规则

必须实现：

```text
1. 缺 Mystic Clover：生成 WATCH_PRICE 或 BUY 候选；
2. 缺 Unbound Magic：如果存在可产出 task，生成 DO_DAILY / FARM；
3. 已有 Mystic Coin 且目标需要：生成 HOLD / RESERVE_FOR_GOAL；
4. 缺 Achievement：生成 COMPLETE_ACHIEVEMENT；
5. 所有 Action 必须有 explanation；
6. 所有 Action 必须有 priority_score。
```

### 9.4 Action Ranking

MVP 简化排序规则：

```text
base_score = 0.5

if action advances active goal:
    +0.2
if action resolves missing requirement:
    +0.2
if action is daily or time-gated:
    +0.1
if action has low estimated time:
    +0.05
if action protects required material:
    +0.1
```

score 上限为 1.0。

---

## 10. FastAPI 接口要求

MVP 0.1 至少提供以下 API。

### 10.1 health

```http
GET /health
```

返回：

```json
{"status": "ok"}
```

### 10.2 load mock data

```http
POST /mock/load
```

功能：加载 mock account、goal、items、tasks。

### 10.3 get goals

```http
GET /goals
```

返回当前目标列表。

### 10.4 get goal gap

```http
GET /goals/{goal_id}/gap
```

返回目标缺口分析。

### 10.5 generate actions

```http
POST /goals/{goal_id}/actions/generate
```

返回生成的 Action 列表。

### 10.6 get report

```http
GET /reports/{goal_id}/markdown
```

返回 Markdown 报告文本。

---

## 11. Markdown 报告要求

必须生成如下结构：

```markdown
# GW2Radar MVP 0.1 Daily Goal Report

## Account Summary

## Active Goal

## Goal Progress

## Completed Requirements

## Missing Requirements

## Reserved / Do Not Sell Materials

## Recommended Actions Today

## Recommended Actions This Week

## Evidence Notes
```

报告必须包含：

```text
1. 当前目标名称；
2. 总体进度百分比；
3. 已满足需求；
4. 缺口清单；
5. 不建议出售材料；
6. 今日行动建议；
7. 本周行动建议；
8. 每条 Action 的 explanation。
```

---

## 12. 测试要求

必须提供 pytest，并覆盖以下测试。

```text
test_ontology.py
- EntityType 包含 GOAL / ITEM / CURRENCY / ACTION
- RelationType 包含 REQUIRES / MISSING_FOR_GOAL / ADVANCES_GOAL
- ActionType 包含 HOLD / BUY / FARM / DO_DAILY

test_graph_builder.py
- 可以创建 Goal entity
- 可以创建 REQUIRES relation
- 可以创建 OWNED_BY 或 player_state

test_goal_gap.py
- Mystic Coin 已满足
- Mystic Clover 有缺口
- Unbound Magic 有缺口
- Achievement 有缺口

test_material_policy.py
- Mystic Coin 被建议 HOLD
- 目标材料不会被建议 SELL_SURPLUS

test_action_generator.py
- 缺 Unbound Magic 时生成 DO_DAILY
- 缺 Achievement 时生成 COMPLETE_ACHIEVEMENT
- 所有 Action 都有 explanation

test_markdown_report.py
- 报告包含 Active Goal
- 报告包含 Missing Requirements
- 报告包含 Recommended Actions Today
```

验收命令：

```bash
pytest
uvicorn gw2radar.api.main:app --reload
```

---

## 13. Codex 执行任务

```text
当前任务：实现 GW2Radar MVP 0.1 Legendary Goal Intelligence Edition。

请按照本文档创建项目骨架、基础本体、数据库模型、mock 数据、推理规则、Action 生成器、Markdown 报告生成器和 pytest 测试。

开发原则：
1. 先保证 mock 数据完整闭环；
2. 再保留真实 GW2 API client 骨架；
3. 不做复杂 UI；
4. 不做自动游戏操作；
5. 所有建议必须可解释；
6. 所有图谱关系必须能关联到 evidence 或 mock evidence；
7. pytest 必须全部通过。

交付物：
1. 可运行 Python 项目；
2. FastAPI 服务；
3. SQLite 数据模型；
4. mock 数据加载器；
5. Goal gap 计算器；
6. Action 生成器；
7. Markdown report 生成器；
8. docs/ontology 文档；
9. docs/mvp/MVP_0_1_LEGENDARY_GOAL.md；
10. pytest 测试。
```

---

## 14. 验收标准

MVP 0.1 完成时必须满足：

```text
1. 项目可以安装；
2. FastAPI 可以启动；
3. /health 返回 ok；
4. /mock/load 可以加载 mock 数据；
5. /goals 可以看到 Aurora 目标；
6. /goals/{goal_id}/gap 可以看到缺口；
7. /goals/{goal_id}/actions/generate 可以生成 Action；
8. /reports/{goal_id}/markdown 可以生成 Markdown 报告；
9. pytest 全部通过；
10. 没有任何游戏自动化、交易自动化或客户端干预逻辑。
```

---

## 15. MVP 0.1 最小成功样例

使用 mock 数据后，系统应能生成类似结果：

```text
Active Goal: Aurora
Progress: partial

Completed:
- Mystic Coin: required 77, owned 120

Missing:
- Mystic Clover: required 77, owned 34, missing 43
- Unbound Magic: required 3000, owned 800, missing 2200
- Aurora Collection Step X: required 1, completed 0

Recommended Actions Today:
1. Do Bitterfrost Frontier Daily Route
   Reason: It produces Unbound Magic and advances Aurora.

2. Hold Mystic Coin
   Reason: Mystic Coin is required by Aurora and should be reserved.

3. Complete Aurora Collection Step X
   Reason: This achievement is missing and blocks the goal.
```

---

## 16. 后续版本边界

MVP 0.1 完成后，后续版本可以扩展：

```text
MVP 0.2 Returner Report
MVP 0.3 Build Fit Graph
MVP 0.4 Market Radar
MVP 0.5 Patch Impact Radar
MVP 0.6 Guild Readiness Console
```

但 MVP 0.1 不提前实现这些功能，只保留合理接口扩展点。
