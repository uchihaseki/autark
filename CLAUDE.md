# CLAUDE.md

## 项目身份

**AUTARK** (Autonomous-Turing Adaptive Reinforcement Kernel) — 安全、可审计的 Agent 自进化框架。

当前版本 `0.2.0`，定位是 **通用 agent 评测与进化内核**，不绑定任何具体 agent 框架、LLM provider、或业务场景。目标是成为社区公认的"agent 改进循环"标准组件。

### 一句话定位

> Run agent cases → evaluate behavior → extract failure signals → propose changes → validate against regressions → audit every decision.

### 不是什么

- 不是 AutoML 系统
- 不是 benchmark 套件
- 不是 prompt optimizer only
- 不是 LangChain / CrewAI / AutoGen 的竞争者
- 不是 Claude Code 的 wrapper

AUTARK **补充**现有 agent 框架，为它们加上结构化的评估和进化循环。

---

## 架构总览

```
EvalCase → RunResult → EvalResult → Signal → Strategy → CandidateChange → ValidationDecision → Audit
```

### 分层结构

```
src/autark/
  core/           protocols.py, models.py, engine.py, exceptions.py  ← 领域中立内核
  evaluation/     judge.py, metrics.py, rubrics.py                   ← 可复用评估器
  signals/        extractor.py                                       ← 失败信号提取
  strategies/     selector.py, store.py, gene.py                     ← 策略匹配与定义
  proposers/      deterministic.py                                   ← 变更生成器
  artifacts/      base.py, filesystem.py                             ← 制品存储层
  validation/     gate.py                                            ← 验证门
  audit/          event_log.py                                       ← 审计日志
  adapters/       fake.py, prompt_agent/                             ← 领域适配器
  cli/            main.py                                            ← CLI 入口
```

### 核心约束（不可妥协）

1. **`autark.core` 必须保持领域中立** — 不得导入 RTD、SKILL.md、AutoRTD、或任何特定业务逻辑/provider SDK
2. **dry-run 是默认行为** — `--commit` 必须显式传入才会真正写制品
3. **Proposer 不得直接提交制品** — 只返回 `CandidateChange`，由引擎 staging → validation → commit/rollback
4. **所有领域行为放在 adapter 里** — core 只定义 protocol 和编排逻辑
5. **可审计性** — 每次 eval、每个 proposal、每个 validation decision 都要有 JSONL 日志

### 10 个扩展点（Protocol）

| Protocol | 职责 | 对应工厂方法 |
|---|---|---|
| `CaseProvider` | 加载 EvalCase 列表 | `adapter.case_provider()` |
| `AgentRunner` | 跑 agent 得到输出 | `adapter.agent_runner()` |
| `Evaluator` | 对输出打分 | `adapter.evaluator()` |
| `SignalExtractor` | 从失败中提取信号 | `adapter.signal_extractor()` |
| `StrategySelector` | 匹配修复策略 | `adapter.strategy_selector()` |
| `ChangeProposer` | 生成候选变更 | `adapter.change_proposer()` |
| `ArtifactStore` | 制品的 load/stage/commit/rollback | `adapter.artifact_store()` |
| `RerunValidationGate` | 验证变更不引入回归 | `adapter.validation_gate()` |
| `AuditStore` | 持久化审计事件 | `adapter.audit_store()` |
| `Adapter` | 组装以上所有组件 | — |

---

## 开发环境

```bash
# 安装
git clone https://github.com/uchihaseki/autark.git
cd autark
pip install -e ".[dev]"

# 运行测试（所有命令都从项目根目录执行）
PYTHONPATH=src pytest -q

# 类型检查
mypy src/autark

# Lint
ruff check src/ tests/

# 跑 demo
autark run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

**PYTHONPATH=src 是必需的**，因为代码在 src 布局下，所有测试和 CLI 调用都依赖它。

---

## 编码约定

- Python 3.10+，使用 `from __future__ import annotations` 和 `slots=True` dataclass
- 代码风格：ruff (E, F, I, N, W, UP)，line-length 150
- 类型检查：mypy，`disallow_untyped_defs = false`（不强制要求类型注解但推荐写）
- `autark.core` 中的公开 API 用 `@public_api(since="0.2.0")` 装饰器标记
- `async/await` — `AgentRunner.run_case()`、`Evaluator.evaluate()`、`RerunValidationGate.validate()` 都是异步的
- Protocol（`autark.core.protocols`）使用 `@runtime_checkable` + duck typing，不需要显式继承
- 命名：`snake_case` 文件和模块，`PascalCase` 类，dataclass 用 `slots=True`

### 制品操作格式

当前 `FileArtifactStore` 支持两种文本操作：
- `append` — 在制品末尾追加文本
- `replace` — 替换匹配文本

---

## 测试结构

```
tests/
  helpers.py                    ← AdapterTestSuite 基类（第三方 adapter 可复用）
  test_cli.py                   ← CLI 命令测试
  test_engine_fake_adapter.py  ← 引擎 + FakeAdapter 集成测试
  test_prompt_agent_cycle.py   ← prompt-agent 完整循环测试
  test_proposers.py            ← 三个 Proposer 的单元测试
  test_evaluators.py           ← 评估器测试
  test_signal_extractor.py     ← 信号提取测试
  test_strategy_selector.py    ← 策略选择测试
  test_validation_gate.py      ← 验证门测试
  test_file_artifact_store.py  ← 文件制品存储测试
```

### 为第三方 Adapter 写测试

`tests/helpers.py` 中的 `AdapterTestSuite` 提供 11 个标准化测试，第三方只需：

```python
class TestMyAdapter(AdapterTestSuite):
    def create_adapter(self, tmp_path: Path):
        from my_adapter import MyAdapter
        # 在 tmp_path 中准备最小 corpus + artifact
        return MyAdapter(...)
```

---

## 当前状态和路线图

### 已完成 (0.2.0, June 2026)

- Phase 0: 仓库卫生（README, LICENSE, CONTRIBUTING, SECURITY, CI, badges, issue/PR 模板）
- Phase 1: 可靠 MVP（83 tests, CI, mypy, ruff）
- Phase 2: 公开 API 和扩展模型（adapter 模板, AdapterTestSuite, schemas/, JSON 合约, TestPyPI 发布）

### 下一步 (0.3.0 — Stronger Evaluation and Validation)

- 并行 case 执行和 flaky agent 重试
- 多信号聚合（单次 proposal 处理多个失败 case）
- 更丰富的 evaluator 和 validation gate
- 至少一个 prompt-agent 之外的现实 adapter 示例
- 正式 PyPI 发布

详见 `docs/open_source_roadmap.md`。

---

## 贡献流程

1. 开 issue 讨论（bug report / feature request / adapter proposal）
2. Fork + PR，确保：
   - 变更动机清晰
   - 公共行为有文档
   - 测试通过 (`PYTHONPATH=src pytest -q`)
   - 新 adapter 不污染 `autark.core`
   - 新 proposer 只返回 `CandidateChange`，不直接提交
3. 外部服务/凭证/网络调用必须是可选的且有文档

---

## 项目原则

- **安全第一** — dry-run 默认，commit 显式，proposer 不直接写文件，验证失败回滚
- **内核小而稳** — `autark.core` 只放 protocol + model + engine，不膨胀
- **适配器优先** — 最佳接入方式就是写一个 adapter
- **一切可审查** — CLI 输出、JSON 报告、JSONL 审计日志都要能解释"发生了什么、为什么"
- **可选集成** — provider SDK（如 anthropic）通过 extras 安装，不做默认依赖
