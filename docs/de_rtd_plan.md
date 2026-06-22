# AUTARK 去 RTD 化改造计划

## 背景

AUTARK 的定位调整为：**通用 agent 评测与自进化内核**，不再以 AutoRTD / RTD Evolver 为主要迁移目标。

原 `rtd_evolver` 只作为历史参考，用来借鉴闭环思想：

`Case -> Agent Run -> Evaluation -> Signal -> Strategy -> Change Proposal -> Validation -> Commit/Audit`

新项目不再依赖：

- AutoRTD graph
- RTD 业务指标
- `SKILL.md`
- `LocalSkillStore`
- RTD judge prompt
- RTD failure category

## 当前目标

首个可运行 demo 改为 **Prompt Agent 自进化**。

首版目标：

- 输入一组通用任务 case。
- 使用当前 prompt/policy 运行一个简单 agent。
- 对 agent 输出进行评测。
- 从失败样本提取 signal。
- 选择 evolution strategy。
- 通过 proposer 生成 prompt patch。
- 在 failing + holdout cases 上验证。
- dry-run 或 commit 到 artifact。
- 记录完整 audit log。

## 核心原则

1. **Core 不能出现 RTD 概念**
   - 禁止 `RTD`、`AutoRTD`、`SKILL.md`、`skill_name`、`LocalSkillStore` 出现在 core 层。
   - core 只认 `artifact_id`、`EvalCase`、`RunResult`、`EvalResult`、`Signal`、`Strategy`、`ArtifactSnapshot`、`EvolutionContext`、`CandidateChange`。

2. **Adapter 只做场景接线**
   - 每个 adapter 自己提供 runner、evaluator、artifact store、strategy pack、validation gate。
   - core 不 import adapter。

3. **Artifact 泛化**
   - artifact 可以是 prompt、policy、workflow yaml、tool config、rubric。
   - 首版只实现文本 artifact。

4. **Evaluation 泛化**
   - 默认维度：`task_success`、`answer_quality`、`constraint_satisfaction`、`overall`。
   - adapter 可以注入自定义 rubric。

5. **Change Proposal 泛化**
   - 不生成 `gep_result.json`。
   - 统一生成 `CandidateChange`，包含文本 patch、rationale、validation plan。

## 项目入口

主入口：

```bash
autark run
```

主命令跑完整闭环：

`load cases -> run agent -> evaluate -> extract signals -> select strategies -> propose changes -> validate -> commit/audit`

首版已围绕 `run` 实现；后续预留：

```bash
autark eval      # 只运行 agent + evaluator，不生成修改
autark propose   # 基于已有 eval/signal 生成候选修改
autark validate  # 验证候选修改，不提交
autark audit     # 查看 event log / feedback repo
```

推荐运行：

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

提交真实修改时显式开启：

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --commit
```

默认行为必须是 dry-run。

## 修复动力单元

AUTARK 不强绑定 Claude Code，也不强绑定任何具体 code agent。

core 中的 proposer 边界是：

```python
class ChangeProposer(Protocol):
    def propose(
        self,
        signal: Signal,
        strategy: Strategy,
        artifact: ArtifactSnapshot,
        context: EvolutionContext,
    ) -> CandidateChange:
        ...
```

输入：

- `Signal`：哪里失败。
- `Strategy`：使用什么修复策略。
- `ArtifactSnapshot`：当前 prompt/policy/workflow/code 片段。
- `EvolutionContext`：case、eval evidence、constraints、历史上下文。

输出：

- `CandidateChange`。

proposer 不允许直接提交文件，必须交给 AUTARK stage、validate、commit/rollback。

### 已规划 proposer

- `DeterministicProposer`
  - 默认启用。
  - 不依赖 LLM。
  - 用规则生成 prompt patch。

- `ExternalCommandProposer`
  - 通过 JSON stdin/stdout 接入任意外部 agent CLI。
  - 适合接内部 agent、Codex、Gemini CLI、自研脚本。

- `ClaudeCodeProposer`
  - 当前是 stub。
  - 未来可接 Claude Code，但不能成为 core 依赖。

## 当前代码状态

已经落地：

```text
src/autark/core/models.py          # EvalCase/RunResult/EvalResult/Signal/Strategy/ArtifactSnapshot/EvolutionContext/CandidateChange
src/autark/core/protocols.py       # CaseProvider/AgentRunner/Evaluator/SignalExtractor/StrategySelector/ChangeProposer/ArtifactStore/RerunValidationGate/AuditStore
src/autark/core/engine.py          # EvolutionEngine.run_cycle
src/autark/proposers/              # deterministic/external-command/claude-code stub
src/autark/adapters/prompt_agent/  # prompt-agent adapter
src/autark/evaluation/             # generic heuristic evaluator/rubric/metrics
src/autark/signals/                # generic threshold signal extractor
src/autark/strategies/             # strategy selector/store/gene model
src/autark/artifacts/              # in-memory/file artifact store
src/autark/audit/                  # JSONL event log / feedback repo
examples/prompt_agent/             # prompt-agent demo
```

RTD 相关代码目前不从 `autark.adapters` 默认导出，后续可删除或移为 legacy reference。

## 清理清单

下一步需要继续清理：

1. 检查全项目是否还有默认 `output_correctness`、`sop_coverage`、`skill_name`、`SKILL.md` 语义。
2. 完善 CLI 的 `eval/propose/validate/audit` 子命令。

## 测试清单

已新增/应保留：

```text
tests/test_prompt_agent_cycle.py
tests/test_signal_extractor.py
tests/test_strategy_selector.py
tests/test_file_artifact_store.py
tests/test_validation_gate.py
```

验收命令：

```bash
cd /data/shuo/workspace/code/autark
PYTHONPATH=src pytest -q
```

## 最终验收

完成后 AUTARK 应满足：

- 可以在没有 `copilot/algo` 的环境中运行。
- 可以在没有 AutoRTD 的环境中运行。
- 可以在没有 LLM 的环境中跑通 deterministic self-evolution demo。
- core 层没有 RTD 业务语义。
- prompt-agent demo 能体现完整自进化闭环。
- Claude Code/外部 code agent 只是 proposer backend，不是框架依赖。
- 后续接 LLM judge、tool-use agent、workflow agent 时不需要改 core。
