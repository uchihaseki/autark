# 快速开始

> English version: [Quickstart](quickstart.md)

本文档引导你从本地仓库运行 AUTARK 的 prompt-agent 演示（零外部依赖，无需 LLM）。

## 环境要求

- Python 3.10 或以上
- `pip`
- 能够运行 Python 命令的终端环境

当前演示不需要外部 LLM 提供商。

## 安装

```bash
git clone https://github.com/uchihaseki/autark.git
cd autark
pip install -e ".[dev]"
```

安装后你的环境中就会有 `autark` 命令行工具。

## 运行 Prompt-Agent 演示

```bash
autark run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

执行一个完整的演化循环：

```text
加载用例 -> 运行Agent -> 评估 -> 提取失败信号 -> 选择策略 -> 生成变更 -> 验证 -> 审计
```

## 默认 Dry-Run 模式

AUTARK 默认是 dry-run 模式。它会评估和验证候选变更，但**不会真正修改制品文件**，除非你显式传入 `--commit`。

在开发适配器、评估器、变更生成器和验证策略时，始终使用 dry-run。

## 提交已通过的变更

只有当你确认要将变更写入制品存储时，才使用 `--commit`：

```bash
autark run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --commit
```

## 输出

默认情况下，命令会打印人类可读的循环摘要：

```text
AUTARK cycle complete
  adapter: prompt-agent
  mode: dry-run
  cases: 2 total, 2 failed
  changes: 1 accepted, 0 rejected
```

当你需要在脚本或 CI 中使用时，传入 `--json` 获取机器可读的 JSON 报告：

```bash
autark run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output \
  --json
```

审计事件写入配置的输出目录，例如：

```text
.autark/output/events.jsonl
```

输出目录是运行时生成的状态文件，不应提交到版本控制。

## 分步执行

AUTARK 支持将循环拆分为独立阶段运行：

```bash
# 评估阶段 — 运行用例、打分、提取失败信号
autark eval \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output

# 变更生成阶段 — 从保存的评估状态生成候选变更
autark propose \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output

# 验证阶段 — 重新运行用例并对比分数（默认 dry-run）
autark validate \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output

# 审计 — 查看事件日志
autark audit --output-dir .autark/output
```

任意命令都可以加上 `--json` 获取机器可读输出。

## 备选方案：不安装直接运行

如果你不想安装包，可以用 `PYTHONPATH=src` 直接从源码运行：

```bash
PYTHONPATH=src python -m autark.cli.main run \
  --adapter prompt-agent \
  --corpus examples/prompt_agent/cases.json \
  --artifact-root examples/prompt_agent/artifacts \
  --output-dir .autark/output
```

## 运行测试

```bash
pytest -q
```

## 常见问题

### 导入错误

如果 Python 找不到 `autark` 模块，用 editable 模式安装：

```bash
pip install -e ".[dev]"
```

### 找不到 corpus 或 artifact 文件

检查 `--corpus` 和 `--artifact-root` 的路径是否相对于仓库根目录存在。

### 制品没有被修改

默认 dry-run 模式不会提交变更。确认你是否有意传入 `--commit`。

### 从 TestPyPI 安装

```bash
pip install --index-url https://test.pypi.org/simple/ autark
```

注意：pip 包本身不包含 `examples/` 目录，你需要单独 clone 仓库来获取演示文件。
