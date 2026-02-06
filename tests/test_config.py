"""
Tests for configuration classes.
"""

import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    ReleaseFlowConfig,
    GitConfig,
    CopilotConfig,
    PRConfig,
    ContinuousConfig,
    DEFAULT_PROMPTS,
)


class TestGitConfig:
    """Tests for GitConfig dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        config = GitConfig()
        assert config.main_branch == "main"
        assert config.branch_prefix == "copilot-improvement"
        assert config.commit_prefix == "🤖 Copilot:"
        assert config.auto_stash is True
        assert config.force_reset is True
    
    def test_custom_values(self):
        """Test custom values can be set."""
        config = GitConfig(
            main_branch="master",
            branch_prefix="ai-improvement",
            auto_stash=False,
        )
        assert config.main_branch == "master"
        assert config.branch_prefix == "ai-improvement"
        assert config.auto_stash is False


class TestCopilotConfig:
    """Tests for CopilotConfig dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        config = CopilotConfig()
        assert config.timeout == 300
        assert config.fallback_to_cli is True
        assert config.cli_command == "copilot"
    
    def test_custom_timeout(self):
        """Test custom timeout can be set."""
        config = CopilotConfig(timeout=600)
        assert config.timeout == 600


class TestPRConfig:
    """Tests for PRConfig dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        config = PRConfig()
        assert config.title_prefix == "🤖 Copilot:"
        assert config.auto_request_review is True
        assert config.merge_method == "squash"
        assert config.wait_for_ci is True
        assert config.ci_timeout == 600
        assert config.delete_branch_after_merge is True
    
    def test_custom_merge_method(self):
        """Test custom merge method can be set."""
        config = PRConfig(merge_method="rebase")
        assert config.merge_method == "rebase"


class TestContinuousConfig:
    """Tests for ContinuousConfig dataclass."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        config = ContinuousConfig()
        assert config.max_iterations == 10
        assert config.delay_between_runs == 3600
        assert config.stop_on_failure is False
    
    def test_custom_iterations(self):
        """Test custom iterations can be set."""
        config = ContinuousConfig(max_iterations=5, delay_between_runs=60)
        assert config.max_iterations == 5
        assert config.delay_between_runs == 60


class TestReleaseFlowConfig:
    """Tests for ReleaseFlowConfig dataclass."""
    
    def test_minimal_config(self):
        """Test minimal valid configuration."""
        config = ReleaseFlowConfig(repo="owner/repo")
        assert config.repo == "owner/repo"
        assert isinstance(config.local_path, Path)
        assert isinstance(config.git, GitConfig)
        assert isinstance(config.copilot, CopilotConfig)
        assert isinstance(config.pr, PRConfig)
        assert isinstance(config.continuous, ContinuousConfig)
    
    def test_invalid_repo_format(self):
        """Test that invalid repo format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repo format"):
            ReleaseFlowConfig(repo="invalid-repo")
    
    def test_empty_repo(self):
        """Test that empty repo raises ValueError."""
        with pytest.raises(ValueError, match="Repository name is required"):
            ReleaseFlowConfig(repo="")
    
    def test_invalid_merge_method(self):
        """Test that invalid merge method raises ValueError."""
        with pytest.raises(ValueError, match="Invalid merge_method"):
            ReleaseFlowConfig(
                repo="owner/repo",
                pr=PRConfig(merge_method="invalid")
            )
    
    def test_custom_prompts(self):
        """Test custom prompts can be set."""
        prompts = ["Fix bugs", "Add tests"]
        config = ReleaseFlowConfig(repo="owner/repo", prompts=prompts)
        assert config.prompts == prompts
    
    def test_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        config = ReleaseFlowConfig(repo="owner/repo", local_path=".")
        assert isinstance(config.local_path, Path)
    
    def test_callbacks(self):
        """Test that callbacks can be set."""
        def on_start(iteration: int, prompt: str):
            pass
        
        def on_end(iteration: int, result: dict):
            pass
        
        config = ReleaseFlowConfig(
            repo="owner/repo",
            on_iteration_start=on_start,
            on_iteration_end=on_end,
        )
        assert config.on_iteration_start is on_start
        assert config.on_iteration_end is on_end


class TestDefaultPrompts:
    """Tests for default prompts."""
    
    def test_default_prompts_exist(self):
        """Test that default prompts are defined."""
        assert len(DEFAULT_PROMPTS) > 0
        assert all(isinstance(p, str) for p in DEFAULT_PROMPTS)
    
    def test_default_prompts_content(self):
        """Test that default prompts have meaningful content."""
        assert any("security" in p.lower() for p in DEFAULT_PROMPTS)
        assert any("test" in p.lower() for p in DEFAULT_PROMPTS)
        assert any("error" in p.lower() for p in DEFAULT_PROMPTS)
