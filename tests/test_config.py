"""
Unit tests for config.py module.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    GitConfig,
    CopilotConfig,
    PRConfig,
    ContinuousConfig,
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
