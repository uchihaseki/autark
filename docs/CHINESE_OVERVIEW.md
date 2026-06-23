# AUTARK 项目方向与进度总览

## 一句话定位

**AUTARK 是一个通用、安全的 agent 自进化框架。**

它不绑定任何具体 LLM、不绑定 AutoRTD，也不限定 prompt。artifact 可以是 prompt、policy、workflow、tool config、rubric 等任意 agent 资产。

## 系统架构流程图

```text
                            ┌──────────────────────────────────────────────────────────────┐
                            │                        AUTARK CLI                            │
                            │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐           │
                            │  │   run   │ │   eval   │ │ propose  │ │audit │           │
                            │  │ (全闭环) │ │(运行+评测)│ │(生成变更) │ │(日志) │           │
                            │  └────┬────┘ └────┬─────┘ └────┬─────┘ └───┬───┘           │
                            └───────┼──────────┼────────────┼─────────────┼───────────────┘
                                    │          │            │             │
                                    ▼          ▼            ▼             ▼
    ┌───────────────────────────────────────────────────────────────────────────────────┐
    │                            EvolutionEngine (进化引擎)                               │
    │                                                                                   │
    │   run_eval()                run_propose()              run_validate()              │
    │   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐            │
    │   │ ① load cases     │    │ ⑦ load eval state│    │ ⑪ load proposals │            │
    │   │ ② run agent      │───▶│ ⑧ select strategy│───▶│ ⑫ stage artifact │            │
    │   │ ③ evaluate       │    │ ⑨ propose change │    │ ⑬ rerun validate │            │
    │   │ ④ extract signals│    │ ⑩ save proposals │    │ ⑭ accept/reject  │            │
    │   │ ⑤ save eval_state│    └──────────────────┘    │ ⑮ save decisions │            │
    │   └────────┬─────────┘                             │ ⑯ commit/rollback│           │
    │            │                                       └────────┬─────────┘            │
    └────────────┼────────────────────────────────────────────────┼──────────────────────┘
                 │                                                │
                 ▼                                                ▼
    ┌────────────────────────┐              ┌────────────────────────────────┐
    │      Adapter 层        │              │         Audit 层               │
    │                        │              │                                │
    │  ┌──────────────────┐  │              │  ┌────────────────────────┐    │
    │  │  CaseProvider    │  │              │  │   JsonlEventLog         │    │
    │  │  AgentRunner     │  │              │  │   (JSONL 事件日志)       │    │
    │  │  Evaluator       │  │              │  └────────────────────────┘    │
    │  │  SignalExtractor │  │              │  ┌────────────────────────┐    │
    │  │  StrategySelector│  │              │  │   FeedbackRepo          │    │
    │  │  ChangeProposer  │  │              │  │   (反馈持久化)           │    │
    │  │  ArtifactStore   │  │              │  └────────────────────────┘    │
    │  │  ValidationGate  │  │              └────────────────────────────────┘
    │  │  AuditStore      │  │
    │  └──────────────────┘  │
    └────────────────────────┘

    ┌────────────────────────────────────────────────────────────────────────────────────┐
    │                                Proposer 层                                          │
    │                                                                                    │
    │  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────────┐  │
    │  │ DeterministicProposer│  │ExternalCommandProposer│  │   ClaudeCodeProposer      │  │
    │  │                      │  │                      │  │                            │  │
    │  │  规则生成 prompt     │  │  JSON stdin/stdout    │  │  claude -p 结构化 prompt  │  │
    │  │  无外部依赖          │  │  接任意外部 CLI       │  │  解析 JSON → CandidateChange│  │
    │  └──────────────────────┘  └──────────────────────┘  └────────────────────────────┘  │
    └────────────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────────────────────────────┐
    │                              中间状态持久化                                          │
    │                                                                                    │
    │  eval ──▶ .autark/output/eval_state.json                                           │
    │                 │                                                                  │
    │                 ▼                                                                  │
    │  propose ──▶ .autark/output/proposals.json                                         │
    │                 │                                                                  │
    │                 ▼                                                                  │
    │  validate ──▶ .autark/output/decisions.json                                        │
    │                                                                                    │
    │  audit ──▶ .autark/output/events.jsonl                                             │
    └────────────────────────────────────────────────────────────────────────────────────┘

    ┌────────────────────────────────────────────────────────────────────────────────────┐
    │                              核心数据流闭环                                          │
    │                                                                                    │
    │  EvalCase ──▶ RunResult ──▶ EvalResult ──▶ Signal ──▶ Strategy                    │
    │                                                       │                            │
    │                                                       ▼                            │
    │   Audit ◀── ValidationDecision ◀── CandidateChange ◀── Proposer                    │
    │                                                   (读取 ArtifactSnapshot)           │
    └────────────────────────────────────────────────────────────────────────────────────┘
```

## 当前总进度

项目处于 **0.1.0 MVP → 0.2.0 开源化完成** 的里程碑。核心骨架完备，开源基础设施已全部搭建，CLI 五个子命令全部可用，三个 Proposer 全部实现，测试 31 个全部通过。

## 已完成内容

### 1. 核心引擎

| 模块 | 路径 | 状态 |
|------|------|------|
| 数据模型 | `src/autark/core/models.py` | EvalCase / RunResult / EvalResult / Signal / Strategy / CandidateChange / ValidationDecision / CycleReport / **EvalReport** 全部可用 |
| 协议接口 | `src/autark/core/protocols.py` | 10 个 Protocol 全部定义 |
| 进化引擎 | `src/autark/core/engine.py` | `run_cycle()` 完整闭环 + `run_eval()` / `run_propose()` / `run_validate()` 分阶段方法，`EngineConfig.output_dir` 持久化中间状态 |
| 异常 | `src/autark/core/exceptions.py` | AutarkError / AdapterError / ValidationError |

### 2. 功能模块

| 模块 | 路径 | 能力 |
|------|------|------|
| 评测 | `src/autark/evaluation/` | HeuristicEvaluator（规则评分）、weighted_overall / grade_from_score、可配置 rubric |
| 信号 | `src/autark/signals/` | ThresholdSignalExtractor（基于分数阈值提取失败信号） |
| 策略 | `src/autark/strategies/` | RegexStrategySelector、JsonStrategyStore、策略 preset |
| 提案 | `src/autark/proposers/` | **DeterministicProposer**（规则，无依赖）、**ExternalCommandProposer**（JSON stdin/stdout）、**ClaudeCodeProposer**（`claude -p` 结构化 prompt + JSON 解析） |
| 制品 | `src/autark/artifacts/` | FileArtifactStore（文件 + stage/commit/rollback）、InMemoryArtifactStore（测试用） |
| 验证 | `src/autark/validation/` | RerunValidationGate（重跑验证）、MetadataScoreValidationGate（轻量 score 比较） |
| 审计 | `src/autark/audit/` | JsonlEventLog（JSONL 事件日志）、FeedbackRepo |

### 3. Adapter

| Adapter | 用途 | 状态 |
|---------|------|------|
| `FakeAdapter` | 测试用，全内存 | 可用 |
| `PromptAgentAdapter` | 当前主 demo，prompt 作为 artifact | 可用，支持三种 proposer |
| `prompt-agent` 示例 | `examples/prompt_agent/` | cases.json + prompt.txt + README |

### 4. CLI（5 个子命令全部可用）

| 命令 | 用途 | 模式 |
|------|------|------|
| `autark run` | 完整自进化闭环 | human summary / `--json`，默认 dry-run，`--commit` 写入 |
| `autark eval` | 运行 + 评测 + 提取信号 | 保存 `eval_state.json` |
| `autark propose` | 读 eval 结果生成候选变更 | 保存 `proposals.json` |
| `autark validate` | 验证候选变更 | 默认 dry-run，`--commit` 写入，保存 `decisions.json` |
| `autark audit` | 查看事件日志 | human / JSON，`--limit` 控制条数 |

### 5. Proposer（3 个全部可用）

| Proposer | 方式 | `--proposer` 值 |
|----------|------|----------------|
| `DeterministicProposer` | 规则匹配，按 failure category 生成 append 操作 | `deterministic`（默认） |
| `ExternalCommandProposer` | JSON stdin/stdout，接任意外部 CLI 或脚本 | `external-command` |
| `ClaudeCodeProposer` | `claude -p` 结构化 prompt → 解析 JSON → CandidateChange | `claude-code` |

### 6. 开源基础设施

| 文件 | 状态 |
|------|------|
| `README.md` | ✅ 定位、quick start、架构、子命令、roadmap |
| `LICENSE` | ✅ MIT |
| `CONTRIBUTING.md` | ✅ 开发环境、PR checklist、adapter 贡献要求 |
| `SECURITY.md` | ✅ 漏洞报告、safe-by-default、禁止 misuse 清单 |
| `CHANGELOG.md` | ✅ 0.1.0 + Unreleased |
| `pyproject.toml` | ✅ classifiers、keywords、authors、urls 元数据已补全 |
| `.github/workflows/ci.yml` | ✅ Python 3.10/3.11/3.12 matrix |
| `.github/ISSUE_TEMPLATE/` | ✅ bug / feature / adapter proposal |
| `.github/pull_request_template.md` | ✅ |
| egg-info 清理 | ✅ 未被 git 跟踪，`.gitignore` 已有 `*.egg-info/` |

### 7. 文档

| 文档 | 内容 |
|------|------|
| `docs/architecture.md` | 架构分层、核心约束、组件清单 |
| `docs/de_rtd_plan.md` | 去 RTD 化改造计划（历史参考） |
| `docs/open_source_roadmap.md` | 开源成熟化路线图（7 阶段） |
| `docs/CHINESE_OVERVIEW.md` | 本文档，中文方向与进度总览 |
| `docs/quickstart.md` | 安装、demo、分阶段命令、troubleshooting |
| `docs/core-concepts.md` | 核心概念和 loop 解释 |
| `docs/adapter-guide.md` | 如何实现 adapter，protocol 说明，safety checklist |
| `docs/external-proposer-contract.md` | ExternalCommandProposer 的 JSON 契约 |

### 8. 测试

**31 个测试全部通过（0.17s）**，覆盖：

| 测试文件 | 覆盖内容 |
|----------|---------|
| `test_engine_fake_adapter.py` | engine + fake adapter 闭环 |
| `test_prompt_agent_cycle.py` | prompt-agent 端到端闭环 |
| `test_file_artifact_store.py` | artifact 存储 load/stage/commit/rollback |
| `test_signal_extractor.py` | 信号提取逻辑 |
| `test_strategy_selector.py` | 策略匹配逻辑 |
| `test_validation_gate.py` | 验证门逻辑 |
| `test_cli.py` | 全部 5 个子命令（parser、human/JSON 输出、参数校验） |
| `test_proposers.py` | Deterministic / ExternalCommand / ClaudeCode（prompt 构建、JSON 契约、错误处理） |

## 当前架构总览

```text
src/autark/
  core/           models.py, protocols.py, engine.py, exceptions.py
  evaluation/     judge.py, metrics.py, rubrics.py
  signals/        extractor.py
  strategies/     selector.py, store.py, gene.py
  proposers/      deterministic.py (含 DeterministicProposer, ExternalCommandProposer, ClaudeCodeProposer)
  artifacts/      base.py, filesystem.py
  validation/     gate.py
  audit/          event_log.py, feedback_repo.py
  adapters/       fake.py, prompt_agent/
  cli/            main.py
```

核心设计原则：

1. **Core 保持领域中立** — 不出现 RTD、SKILL.md、特定 LLM provider、特定业务流程
2. **Adapter 负责领域接线** — 每个 adapter 自己提供 runner / evaluator / artifact store / strategy pack / validation gate
3. **安全默认** — dry-run 是默认行为，proposer 不直接提交 artifact，validation gate 可以拒绝回归
4. **可审计** — 每次 case 评测和 validation decision 都写入 JSONL 日志

## 待做事项（按优先级）

### 近期（0.2.0 收尾：准备 PyPI 发布）

- [ ] 跑通 GitHub Actions CI（等仓库推到 GitHub 后验证）
- [ ] 补 `CODE_OF_CONDUCT.md`
- [ ] 清理代码中可能的 RTD 残留语义（`output_correctness`、`sop_coverage` 等）
- [ ] PyPI 首次发布（TestPyPI → PyPI）

### 中期（0.3.0 里程碑：能力增强）

- [ ] 增加非 prompt-agent 的真实 adapter（例如 tool-use agent policy、workflow YAML、rubric 自进化）
- [ ] LLM judge evaluator（可选 integration）
- [ ] ClaudeCodeProposer 在真实 Claude Code 环境下的端到端验证
- [ ] 更强的 regression 报告（before/after case 对比表）
- [ ] 并行 case 执行
- [ ] flaky agent 的重复运行支持
- [ ] 中间状态 JSON Schema 定义

### 远期（1.0.0 里程碑：稳定发布）

- [ ] 稳定 public protocol 接口
- [ ] 语义化版本 + 兼容性声明
- [ ] 生产级文档
- [ ] 社区治理（label、maintainer checklist、贡献路径）

## 技术债务 & 风险

1. **ClaudeCodeProposer 需真实 Claude Code 验证** — prompt 构建和 JSON 解析逻辑已有测试覆盖，但尚未在真实 `claude` CLI 环境中端到端验证过，输出格式取决于 Claude 的实际行为。
2. **中间状态文件格式未正式定义 schema** — `eval_state.json` / `proposals.json` / `decisions.json` 目前是直接 `asdict` 序列化，没有 JSON Schema 约束，跨版本兼容性待定。
3. **缺少 flaky 处理** — agent 输出不确定时，单次运行结果不稳定，eval/propose/validate 可能产生噪声信号。
4. **只测试了 prompt-agent 和 fake adapter** — 没有真实场景（如 tool-use、workflow）的集成验证。
5. **`src/` 下的 `autark.egg-info/`** — 经确认未被 git 跟踪，`.gitignore` 已有 `*.egg-info/`，风险已解除。

## 推荐下一步行动

处于 **0.2.0 → 0.3.0** 的衔接点，建议按以下顺序推进：

1. **推到 GitHub，验证 CI** — 让 GitHub Actions 跑通 Python 3.10/3.11/3.12 matrix
2. **PyPI 首次发布** — 版本号建议 `0.2.0`，先发 TestPyPI 验证，再发正式 PyPI
3. **增加真实 adapter** — 比如 tool-use policy adapter 或 workflow YAML adapter，证明 AUTARK 不止能优化 prompt
4. **LLM judge evaluator** — 可选集成，让评测更接近真实场景
5. **ClaudeCodeProposer 真实环境验证** — 在安装了 Claude Code 的机器上端到端测试
