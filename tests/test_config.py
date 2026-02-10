"""
Unit tests for config.py module.
"""

import pytest
import sys
from pathlib import Path

from release_flow.config import (
    GitConfig,
    CopilotConfig,
    PRConfig,
    ContinuousConfig,
    OperatorConfig,
    ReleaseFlowConfig,
    DEFAULT_PROMPTS,
)


class TestGitConfig:
    """Tests for GitConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = GitConfig()
        assert config.main_branch == "main"
        assert config.branch_prefix == "copilot-improvement"
        assert config.commit_prefix == "🤖 Copilot:"
        assert config.auto_stash is True
        assert config.force_reset is True
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = GitConfig(
            main_branch="master",
            branch_prefix="feature",
            commit_prefix="Auto:",
            auto_stash=False,
            force_reset=False,
        )
        assert config.main_branch == "master"
        assert config.branch_prefix == "feature"
        assert config.commit_prefix == "Auto:"
        assert config.auto_stash is False
        assert config.force_reset is False


class TestCopilotConfig:
    """Tests for CopilotConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = CopilotConfig()
        assert config.timeout == 300
        assert config.fallback_to_cli is True
        assert config.cli_command == "copilot"
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = CopilotConfig(
            timeout=600,
            fallback_to_cli=False,
            cli_command="gh-copilot",
        )
        assert config.timeout == 600
        assert config.fallback_to_cli is False
        assert config.cli_command == "gh-copilot"


class TestPRConfig:
    """Tests for PRConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = PRConfig()
        assert config.title_prefix == "🤖 Copilot:"
        assert config.auto_request_review is True
        assert config.merge_method == "squash"
        assert config.wait_for_ci is True
        assert config.ci_timeout == 600
        assert config.delete_branch_after_merge is True
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = PRConfig(
            title_prefix="[AUTO]",
            auto_request_review=False,
            merge_method="merge",
            wait_for_ci=False,
            ci_timeout=300,
            delete_branch_after_merge=False,
        )
        assert config.title_prefix == "[AUTO]"
        assert config.auto_request_review is False
        assert config.merge_method == "merge"
        assert config.wait_for_ci is False
        assert config.ci_timeout == 300
        assert config.delete_branch_after_merge is False


class TestContinuousConfig:
    """Tests for ContinuousConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ContinuousConfig()
        assert config.max_iterations == 10
        assert config.delay_between_runs == 3600
        assert config.stop_on_failure is False
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = ContinuousConfig(
            max_iterations=5,
            delay_between_runs=1800,
            stop_on_failure=True,
        )
        assert config.max_iterations == 5
        assert config.delay_between_runs == 1800
        assert config.stop_on_failure is True


class TestReleaseFlowConfig:
    """Tests for ReleaseFlowConfig dataclass."""
    
    def test_valid_config(self):
        """Test valid configuration creation."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
        )
        assert config.repo == "owner/repo"
        assert config.local_path == Path.cwd()
        assert config.github_token is None
        assert isinstance(config.git, GitConfig)
        assert isinstance(config.copilot, CopilotConfig)
        assert isinstance(config.pr, PRConfig)
        assert isinstance(config.continuous, ContinuousConfig)
        assert isinstance(config.operator, OperatorConfig)
    
    def test_invalid_repo_format(self):
        """Test invalid repository format validation."""
        with pytest.raises(ValueError, match="Invalid repository format"):
            ReleaseFlowConfig(
                repo="invalid-repo",
                local_path=Path.cwd(),
            )
    
    def test_string_path_conversion(self):
        """Test automatic string to Path conversion."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=".",
        )
        assert isinstance(config.local_path, Path)
    
    def test_negative_timeout_validation(self):
        """Test negative timeout validation."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ReleaseFlowConfig(
                repo="owner/repo",
                local_path=Path.cwd(),
                copilot=CopilotConfig(timeout=-1),
            )
    
    def test_negative_ci_timeout_validation(self):
        """Test negative CI timeout validation."""
        with pytest.raises(ValueError, match="CI timeout must be positive"):
            ReleaseFlowConfig(
                repo="owner/repo",
                local_path=Path.cwd(),
                pr=PRConfig(ci_timeout=-1),
            )
    
    def test_negative_max_iterations_validation(self):
        """Test negative max iterations validation."""
        with pytest.raises(ValueError, match="Max iterations must be positive"):
            ReleaseFlowConfig(
                repo="owner/repo",
                local_path=Path.cwd(),
                continuous=ContinuousConfig(max_iterations=-1),
            )
    
    def test_negative_delay_validation(self):
        """Test negative delay validation."""
        with pytest.raises(ValueError, match="Delay between runs cannot be negative"):
            ReleaseFlowConfig(
                repo="owner/repo",
                local_path=Path.cwd(),
                continuous=ContinuousConfig(delay_between_runs=-1),
            )
    
    def test_callbacks_optional(self):
        """Test that callbacks are optional."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
        )
        assert config.on_iteration_start is None
        assert config.on_iteration_end is None
        assert config.on_pr_created is None
        assert config.on_error is None
    
    def test_callbacks_assignment(self):
        """Test callback assignment."""
        def dummy_callback(*args):
            pass
        
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            on_iteration_start=dummy_callback,
            on_pr_created=dummy_callback,
        )
        assert config.on_iteration_start is dummy_callback
        assert config.on_pr_created is dummy_callback
    
    def test_custom_prompts(self):
        """Test custom prompts configuration."""
        custom_prompts = ["Prompt 1", "Prompt 2"]
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            prompts=custom_prompts,
        )
        assert config.prompts == custom_prompts
    
    def test_empty_prompts_list(self):
        """Test empty prompts list."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            prompts=[],
        )
        assert config.prompts == []


class TestDefaultPrompts:
    """Tests for default prompts."""
    
    def test_default_prompts_exist(self):
        """Test that default prompts are defined."""
        assert DEFAULT_PROMPTS is not None
        assert isinstance(DEFAULT_PROMPTS, list)
        assert len(DEFAULT_PROMPTS) > 0
    
    def test_default_prompts_are_strings(self):
        """Test that all default prompts are strings."""
        assert all(isinstance(p, str) for p in DEFAULT_PROMPTS)
    
    def test_default_prompts_not_empty(self):
        """Test that default prompts are not empty strings."""
        assert all(p.strip() for p in DEFAULT_PROMPTS)
    
    def test_default_prompts_coverage(self):
        """Test that default prompts cover key areas."""
        prompts_text = " ".join(DEFAULT_PROMPTS).lower()
        assert "security" in prompts_text
        assert "test" in prompts_text
        assert "error" in prompts_text
        assert "documentation" in prompts_text


class TestOperatorConfig:
    """Tests for OperatorConfig dataclass."""

    def test_default_values(self):
        """Test default Operator configuration values."""
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
        """Test custom Operator configuration values."""
        config = OperatorConfig(
            enabled=True,
            model="gpt-4o",
            timeout=600,
            judge_after_iteration=False,
            stop_on_fail_verdict=True,
        )
        assert config.enabled is True
        assert config.model == "gpt-4o"
        assert config.timeout == 600
        assert config.judge_after_iteration is False
        assert config.stop_on_fail_verdict is True

    def test_operator_in_release_flow_config(self):
        """Test OperatorConfig integration in ReleaseFlowConfig."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            operator=OperatorConfig(enabled=True, model="claude-3.5-sonnet"),
        )
        assert config.operator.enabled is True
        assert config.operator.model == "claude-3.5-sonnet"

    def test_model_separation_enforced(self):
        """Test that same model for agent and operator is rejected when enabled."""
        with pytest.raises(ValueError, match="Operator model must differ"):
            ReleaseFlowConfig(
                repo="owner/repo",
                local_path=Path.cwd(),
                copilot=CopilotConfig(model="gpt-4o"),
                operator=OperatorConfig(enabled=True, model="gpt-4o"),
            )

    def test_model_separation_not_enforced_when_disabled(self):
        """Test that same model is allowed when operator is disabled."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(model="gpt-4o"),
            operator=OperatorConfig(enabled=False, model="gpt-4o"),
        )
        assert config.operator.enabled is False

    def test_operator_timeout_validation(self):
        """Test operator timeout must be positive."""
        with pytest.raises(ValueError, match="Operator timeout must be positive"):
            ReleaseFlowConfig(
                repo="owner/repo",
                local_path=Path.cwd(),
                operator=OperatorConfig(timeout=-1),
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
