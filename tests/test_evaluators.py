"""Tests for non-heuristic evaluators: ExactMatch, Rubric, PythonCallback, LLMJudge."""

from __future__ import annotations

import asyncio
from unittest import mock

import pytest

from autark.core.models import EvalCase, EvalResult, RunResult
from autark.evaluation.judge import (
    ExactMatchEvaluator,
    LLMJudgeEvaluator,
    PythonCallbackEvaluator,
    RubricEvaluator,
)
from autark.evaluation.rubrics import DEFAULT_AGENT_RUBRIC, RubricDimension

# ---------------------------------------------------------------------------
# ExactMatchEvaluator
# ---------------------------------------------------------------------------

class TestExactMatchEvaluator:
    def test_exact_match_pass(self):
        evaluator = ExactMatchEvaluator()
        case = EvalCase(case_id="c1", input_text="2+3", expected_output="5")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="5")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "pass"
        assert eval_result.scores["overall"] == 1.0
        assert eval_result.grade == "A"

    def test_exact_match_case_insensitive(self):
        evaluator = ExactMatchEvaluator(ignore_case=True)
        case = EvalCase(case_id="c1", input_text="", expected_output="Hello")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="hello")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "pass"
        assert eval_result.scores["overall"] == 1.0

    def test_exact_match_fail(self):
        evaluator = ExactMatchEvaluator()
        case = EvalCase(case_id="c1", input_text="", expected_output="correct")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="wrong")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "fail"
        assert eval_result.scores["overall"] == 0.0

    def test_exact_match_error_status(self):
        evaluator = ExactMatchEvaluator()
        case = EvalCase(case_id="c1", input_text="", expected_output="ignored")
        result = RunResult(case_id="c1", artifact_id="a1", status="error", output="")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "fail"
        assert eval_result.scores["overall"] == 0.0
        assert eval_result.failure_category == "execution_error"

    def test_exact_match_whitespace_difference(self):
        evaluator = ExactMatchEvaluator(ignore_whitespace=True)
        case = EvalCase(case_id="c1", input_text="", expected_output="  hello  ")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="hello")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "pass"


# ---------------------------------------------------------------------------
# RubricEvaluator
# ---------------------------------------------------------------------------

class TestRubricEvaluator:
    def test_with_default_rubric(self):
        dims = list(DEFAULT_AGENT_RUBRIC)
        evaluator = RubricEvaluator(dims)
        case = EvalCase(case_id="c1", input_text="", expected_output="5")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="5")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert isinstance(eval_result, EvalResult)
        assert "overall" in eval_result.scores
        for dim in dims:
            assert dim.name in eval_result.scores

    def test_pass_with_high_scores(self):
        dims = [RubricDimension("correctness", 1.0, "Is the answer correct?")]
        evaluator = RubricEvaluator(dims, score_fn=lambda d, o, e: 1.0 if o == e else 0.0)
        case = EvalCase(case_id="c1", input_text="", expected_output="yes")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="yes")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "pass"
        assert eval_result.scores["overall"] == 1.0

    def test_fail_with_low_scores(self):
        dims = [RubricDimension("correctness", 1.0, "")]
        evaluator = RubricEvaluator(dims, score_fn=lambda d, o, e: 0.0)
        case = EvalCase(case_id="c1", input_text="", expected_output="yes")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="no")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "fail"

    def test_error_status(self):
        evaluator = RubricEvaluator([RubricDimension("task", 1.0, "")])
        case = EvalCase(case_id="c1", input_text="", expected_output="")
        result = RunResult(case_id="c1", artifact_id="a1", status="error", output="", trajectory="boom")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "fail"
        assert eval_result.failure_category == "execution_error"

    def test_empty_output(self):
        dims = list(DEFAULT_AGENT_RUBRIC)
        evaluator = RubricEvaluator(dims)
        case = EvalCase(case_id="c1", input_text="", expected_output="something")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "fail"
        assert eval_result.failure_category == "empty_output"


# ---------------------------------------------------------------------------
# PythonCallbackEvaluator
# ---------------------------------------------------------------------------

class TestPythonCallbackEvaluator:

    async def _score_pass(self, case, run_result):
        return {"accuracy": 1.0, "overall": 1.0}

    async def _score_fail(self, case, run_result):
        return {"accuracy": 0.0, "overall": 0.0}

    async def _score_no_overall(self, case, run_result):
        return {"accuracy": 0.5, "completeness": 0.5}

    def test_callback_pass(self):
        evaluator = PythonCallbackEvaluator(self._score_pass)
        case = EvalCase(case_id="c1", input_text="", expected_output="")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "pass"
        assert eval_result.scores["overall"] == 1.0

    def test_callback_fail(self):
        evaluator = PythonCallbackEvaluator(self._score_fail)
        case = EvalCase(case_id="c1", input_text="", expected_output="")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        assert eval_result.status == "fail"

    def test_callback_auto_overall(self):
        evaluator = PythonCallbackEvaluator(self._score_no_overall, pass_threshold=0.4)
        case = EvalCase(case_id="c1", input_text="", expected_output="")
        result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="")
        eval_result = asyncio.run(evaluator.evaluate(case, result))
        # auto overall = (0.5 + 0.5) / 2 = 0.5
        assert eval_result.scores["overall"] == 0.5
        assert eval_result.status == "pass"  # 0.5 >= 0.4

    def test_callback_receives_case_and_result(self):
        received = {}

        async def capture(case, run_result):
            received["case"] = case
            received["result"] = run_result
            return {"overall": 1.0}

        evaluator = PythonCallbackEvaluator(capture)
        case = EvalCase(case_id="cap", input_text="test input", expected_output="expected")
        result = RunResult(case_id="cap", artifact_id="a1", status="ok", output="actual")
        asyncio.run(evaluator.evaluate(case, result))
        assert received["case"] is case
        assert received["result"] is result


# ---------------------------------------------------------------------------
# LLMJudgeEvaluator
# ---------------------------------------------------------------------------

class TestLLMJudgeEvaluator:

    def test_missing_import_raises_clear_error(self):
        with mock.patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="LLMJudgeEvaluator requires.*anthropic"):
                LLMJudgeEvaluator()

    def test_build_judge_prompt_contains_dimensions(self):
        # Simulate import so the class can be instantiated
        with mock.patch("autark.evaluation.judge._make_client"), \
             mock.patch.dict("sys.modules", {"anthropic": mock.MagicMock()}):
            dims = [RubricDimension("correctness", 1.0, "Is it correct?")]
            evaluator = LLMJudgeEvaluator(rubric=dims)
            case = EvalCase(case_id="c1", input_text="2+3", expected_output="5")
            result = RunResult(case_id="c1", artifact_id="a1", status="ok", output="5")
            prompt = evaluator._build_judge_prompt(case, result)
            assert "correctness" in prompt
            assert "2+3" in prompt
            assert "5" in prompt

    def test_parse_scores_valid_json(self):
        with mock.patch("autark.evaluation.judge._make_client"), \
             mock.patch.dict("sys.modules", {"anthropic": mock.MagicMock()}):
            evaluator = LLMJudgeEvaluator()
            scores = evaluator._parse_scores('{"task_success": 1.0, "answer_quality": 0.8}')
            assert scores == {"task_success": 1.0, "answer_quality": 0.8}

    def test_parse_scores_with_markdown_fences(self):
        with mock.patch("autark.evaluation.judge._make_client"), \
             mock.patch.dict("sys.modules", {"anthropic": mock.MagicMock()}):
            evaluator = LLMJudgeEvaluator()
            raw = "```json\n{\"task_success\": 0.9}\n```"
            scores = evaluator._parse_scores(raw)
            assert scores == {"task_success": 0.9}

    def test_parse_scores_fallback_regex(self):
        with mock.patch("autark.evaluation.judge._make_client"), \
             mock.patch.dict("sys.modules", {"anthropic": mock.MagicMock()}):
            evaluator = LLMJudgeEvaluator()
            raw = "Here is my evaluation: {\"task_success\": 0.7} and that's it."
            scores = evaluator._parse_scores(raw)
            assert scores == {"task_success": 0.7}

    def test_parse_scores_invalid_json_raises(self):
        with mock.patch("autark.evaluation.judge._make_client"), \
             mock.patch.dict("sys.modules", {"anthropic": mock.MagicMock()}):
            evaluator = LLMJudgeEvaluator()
            with pytest.raises(RuntimeError, match="could not parse JSON"):
                evaluator._parse_scores("not json at all")
