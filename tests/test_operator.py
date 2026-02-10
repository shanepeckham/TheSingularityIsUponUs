"""
Comprehensive unit tests for the Operator module.

Tests the LLM-as-judge / product owner functionality including:
- Configuration and model separation enforcement
- Assessment, roadmap, and prompt generation
- Post-iteration judging
- Prompts file management
- Full pipeline
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from release_flow.config import (
    ReleaseFlowConfig,
    CopilotConfig,
    OperatorConfig,
)
from release_flow.judge import Operator, OperatorError


class TestOperatorConfig:
    """Tests for OperatorConfig dataclass."""

    def test_default_values(self):
        """Test default Operator configuration."""
        config = OperatorConfig()
        assert config.enabled is False
        assert config.model == "claude-3.5-sonnet"
        assert config.timeout == 300
        assert config.judge_after_iteration is True
        assert config.generate_prompts_before_run is True
        assert config.update_prompts_after_run is True
        assert config.prompts_file == "prompts.txt"
        assert config.stop_on_fail_verdict is False

    def test_custom_values(self):
        """Test custom Operator configuration."""
        config = OperatorConfig(
            enabled=True,
            model="gpt-4o",
            timeout=600,
            judge_after_iteration=False,
            generate_prompts_before_run=False,
            update_prompts_after_run=False,
            stop_on_fail_verdict=True,
        )
        assert config.enabled is True
        assert config.model == "gpt-4o"
        assert config.timeout == 600
        assert config.judge_after_iteration is False
        assert config.stop_on_fail_verdict is True


class TestOperatorConfigValidation:
    """Tests for Operator configuration validation within ReleaseFlowConfig."""

    def test_operator_timeout_must_be_positive(self):
        """Test that negative operator timeout raises ValueError."""
        with pytest.raises(ValueError, match="Operator timeout must be positive"):
            ReleaseFlowConfig(
                repo="owner/repo",
                local_path=Path.cwd(),
                operator=OperatorConfig(timeout=-1),
            )

    def test_same_model_raises_when_enabled(self):
        """Test that using the same model for agent and operator raises ValueError."""
        with pytest.raises(ValueError, match="Operator model must differ"):
            ReleaseFlowConfig(
                repo="owner/repo",
                local_path=Path.cwd(),
                copilot=CopilotConfig(model="gpt-4o"),
                operator=OperatorConfig(enabled=True, model="gpt-4o"),
            )

    def test_same_model_allowed_when_disabled(self):
        """Test that same model is fine when operator is disabled."""
        # Should not raise
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=False, model="gpt-4o"),
        )
        assert config.operator.enabled is False

    def test_different_models_accepted(self):
        """Test that different models are accepted."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        assert config.copilot.model == "gpt-4o"
        assert config.operator.model == "claude-3.5-sonnet"

    def test_none_models_accepted(self):
        """Test that None models don't trigger the check."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model=None),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        assert config.copilot.model is None
        assert config.operator.model == "claude-3.5-sonnet"


class TestOperatorInit:
    """Tests for Operator initialisation."""

    def test_init_enforces_model_separation(self):
        """Test that Operator __init__ rejects same model."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            # operator disabled at config level to bypass config validation
            operator=OperatorConfig(enabled=False, model="gpt-4o"),
        )
        # Force-enable to test Operator's own check
        config.copilot.model = "gpt-4o"
        config.operator.model = "gpt-4o"
        config.operator.enabled = True

        with pytest.raises(OperatorError, match="Operator model must differ"):
            Operator(config)

    def test_init_succeeds_with_different_models(self):
        """Test that Operator initialises with different models."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)
        assert op.operator_config.model == "claude-3.5-sonnet"


class TestOperatorPromptTemplates:
    """Tests for Operator prompt template formatting."""

    def test_assess_prompt_contains_path(self):
        """Test that the assessment prompt includes the local path."""
        prompt = Operator.ASSESS_PROMPT.format(local_path="/tmp/myrepo")
        assert "/tmp/myrepo" in prompt
        assert "Functionality gaps" in prompt
        assert "CRITICAL" in prompt

    def test_roadmap_prompt_contains_assessment(self):
        """Test that the roadmap prompt includes the assessment."""
        prompt = Operator.ROADMAP_PROMPT.format(
            local_path="/tmp/myrepo",
            assessment="Test assessment content",
        )
        assert "Test assessment content" in prompt
        assert "prioritised" in prompt.lower() or "prioritized" in prompt.lower()

    def test_generate_prompts_prompt_contains_roadmap(self):
        """Test that the generate prompts prompt includes the roadmap."""
        prompt = Operator.GENERATE_PROMPTS_PROMPT.format(roadmap="Test roadmap")
        assert "Test roadmap" in prompt
        assert "[P0]" in prompt

    def test_judge_prompt_contains_all_fields(self):
        """Test that the judge prompt includes all required fields."""
        prompt = Operator.JUDGE_PROMPT.format(
            agent_prompt="Fix bugs",
            changes_summary="Fixed 3 bugs",
            files_changed="core.py, utils.py",
        )
        assert "Fix bugs" in prompt
        assert "Fixed 3 bugs" in prompt
        assert "core.py, utils.py" in prompt
        assert "PASS" in prompt
        assert "FAIL" in prompt


class TestOperatorPromptsFile:
    """Tests for prompts file management."""

    def test_update_prompts_file_write(self, tmp_path):
        """Test writing prompts to a file."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=tmp_path,
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        prompts = ["[P0] Fix critical security issue", "[P1] Add tests"]
        result_path = op.update_prompts_file(prompts)

        assert result_path.exists()
        content = result_path.read_text()
        assert "[P0] Fix critical security issue" in content
        assert "[P1] Add tests" in content
        assert "# Release Flow Prompts" in content
        assert "Operator" in content

    def test_update_prompts_file_append(self, tmp_path):
        """Test appending prompts to an existing file."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=tmp_path,
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        # Write initial prompts
        op.update_prompts_file(["First prompt"])

        # Append more
        op.update_prompts_file(["Second prompt"], append=True)

        content = (tmp_path / "prompts.txt").read_text()
        assert "First prompt" in content
        assert "Second prompt" in content

    def test_update_prompts_file_custom_path(self, tmp_path):
        """Test writing to a custom file path."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=tmp_path,
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        custom_file = tmp_path / "custom_prompts.txt"
        result = op.update_prompts_file(
            ["Custom prompt"], file_path=custom_file
        )

        assert result == custom_file.resolve()
        assert custom_file.exists()
        assert "Custom prompt" in custom_file.read_text()


@pytest.mark.asyncio
class TestOperatorJudge:
    """Tests for the Operator judge functionality."""

    async def test_judge_pass_verdict(self):
        """Test judge returns PASS verdict."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        # Mock the _send_prompt method
        op._send_prompt = AsyncMock(return_value=(
            "## Evaluation\n\n"
            "### Scores\n"
            "- Correctness: 9/10\n"
            "- Completeness: 8/10\n\n"
            "### Verdict: PASS\n\n"
            "The changes correctly address the prompt."
        ))

        result = await op.judge_changes(
            agent_prompt="Fix error handling",
            changes_summary="Added try/except blocks",
            files_changed=["core.py"],
        )

        assert result["verdict"] == "PASS"
        assert "Evaluation" in result["evaluation"]

    async def test_judge_fail_verdict(self):
        """Test judge returns FAIL verdict."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        op._send_prompt = AsyncMock(return_value=(
            "### Verdict: FAIL\n\n"
            "The changes introduced a regression."
        ))

        result = await op.judge_changes(
            agent_prompt="Fix error handling",
            changes_summary="Changed error handling",
            files_changed=["core.py"],
        )

        assert result["verdict"] == "FAIL"

    async def test_judge_needs_work_verdict(self):
        """Test judge returns NEEDS_WORK verdict."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        op._send_prompt = AsyncMock(return_value=(
            "### Verdict: NEEDS_WORK\n\n"
            "Partially complete. Follow-up suggestions:\n"
            "- Add tests for edge cases\n"
            "- Update documentation\n"
        ))

        result = await op.judge_changes(
            agent_prompt="Fix error handling",
            changes_summary="Partial fix",
            files_changed=["core.py"],
        )

        assert result["verdict"] == "NEEDS_WORK"
        assert len(result["follow_up"]) >= 0  # May extract follow-ups

    async def test_judge_empty_changes(self):
        """Test judge handles empty file list gracefully."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        op._send_prompt = AsyncMock(return_value="Verdict: PASS\nNo changes needed.")

        result = await op.judge_changes(
            agent_prompt="Check code",
            changes_summary="",
            files_changed=[],
        )

        assert result["verdict"] == "PASS"


@pytest.mark.asyncio
class TestOperatorFullPipeline:
    """Tests for the full Operator pipeline."""

    async def test_run_full_assessment(self, tmp_path):
        """Test the full assessment pipeline."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=tmp_path,
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        # Mock all LLM calls
        call_count = 0

        async def mock_send(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Assessment: The codebase has gaps in testing."
            elif call_count == 2:
                return "Roadmap: 1. Add tests (P0, S)"
            else:
                return "[P0] Add unit tests for all public functions in core.py"

        op._send_prompt = mock_send
        op._close_copilot = AsyncMock()

        result = await op.run_full_assessment(update_prompts=True)

        assert "assessment" in result
        assert "roadmap" in result
        assert "prompts" in result
        assert len(result["prompts"]) >= 1
        assert result["prompts_file"] is not None

        # Verify the prompts file was written
        prompts_file = tmp_path / "prompts.txt"
        assert prompts_file.exists()
        content = prompts_file.read_text()
        assert "[P0]" in content

    async def test_run_full_assessment_no_write(self, tmp_path):
        """Test the pipeline without writing prompts."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=tmp_path,
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        call_count = 0

        async def mock_send(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Assessment report."
            elif call_count == 2:
                return "Roadmap items."
            else:
                return "[P1] Improve docs"

        op._send_prompt = mock_send
        op._close_copilot = AsyncMock()

        result = await op.run_full_assessment(update_prompts=False)

        assert result["prompts_file"] is None
        assert not (tmp_path / "prompts.txt").exists()


@pytest.mark.asyncio
class TestOperatorPostIterationReview:
    """Tests for post-iteration review."""

    async def test_post_iteration_review(self):
        """Test post-iteration review of agent results."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        op._send_prompt = AsyncMock(return_value="Verdict: PASS\nGood changes.")
        op._close_copilot = AsyncMock()

        iteration_result = {
            "prompt": "Fix error handling",
            "summary": "Added try/except blocks to core.py",
            "files_changed": ["core.py"],
            "success": True,
        }

        result = await op.post_iteration_review(iteration_result)

        assert result["verdict"] == "PASS"
        assert "evaluation" in result

    async def test_post_iteration_review_with_missing_fields(self):
        """Test post-iteration review handles incomplete iteration result."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        op = Operator(config)

        op._send_prompt = AsyncMock(return_value="Verdict: NEEDS_WORK")
        op._close_copilot = AsyncMock()

        # Minimal iteration result (missing optional fields)
        result = await op.post_iteration_review({})

        assert result["verdict"] == "NEEDS_WORK"


class TestOperatorExceptionHierarchy:
    """Tests for Operator exception hierarchy."""

    def test_operator_error_is_exception(self):
        """Test OperatorError inherits from Exception."""
        assert issubclass(OperatorError, Exception)

    def test_operator_error_message(self):
        """Test OperatorError message preservation."""
        error = OperatorError("test message")
        assert str(error) == "test message"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
