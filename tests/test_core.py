"""
Comprehensive unit tests for core.py module.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio

from release_flow.core import (
    _sanitize_branch_name,
    _sanitize_input,
    _validate_repo_name,
    _validate_path,
    ReleaseFlow,
    ReleaseFlowError,
    ConfigurationError,
    GitOperationError,
    CopilotError,
    PROperationError,
    copilot_session,
)
from release_flow.config import ReleaseFlowConfig


class TestSanitization:
    """Tests for sanitization functions."""
    
    def test_sanitize_branch_name_normal(self):
        """Test normal branch name sanitization."""
        assert _sanitize_branch_name("feature/test") == "feature/test"
        assert _sanitize_branch_name("bugfix-123") == "bugfix-123"
    
    def test_sanitize_branch_name_injection_prevention(self):
        """Test branch name injection prevention."""
        result = _sanitize_branch_name("test; rm -rf /")
        assert ";" not in result
        assert "rm" in result  # The words remain, but not as a command
        
        result = _sanitize_branch_name("test`whoami`")
        assert "`" not in result
        
        result = _sanitize_branch_name("test$(whoami)")
        assert "$" not in result
        assert "(" not in result
    
    def test_sanitize_branch_name_path_traversal(self):
        """Test branch name path traversal prevention."""
        result = _sanitize_branch_name("test/../../../etc/passwd")
        assert ".." not in result
    
    def test_sanitize_branch_name_length_limit(self):
        """Test branch name length limiting."""
        long_name = "a" * 200
        result = _sanitize_branch_name(long_name)
        assert len(result) <= 100
    
    def test_sanitize_branch_name_edge_cases(self):
        """Test branch name edge cases."""
        assert _sanitize_branch_name("") == ""
        result = _sanitize_branch_name("///")
        # Multiple slashes should be preserved but reduced
        assert result in ["/", "//", "///"]
        assert _sanitize_branch_name("---") == ""  # Consecutive dashes removed
    
    def test_sanitize_input_normal(self):
        """Test normal input sanitization."""
        assert _sanitize_input("Hello World") == "Hello World"
        assert _sanitize_input("Test\nLine") == "Test\nLine"
        assert _sanitize_input("Tab\there") == "Tab\there"
    
    def test_sanitize_input_control_characters(self):
        """Test control character removal."""
        result = _sanitize_input("test\x00null\x01control")
        assert "\x00" not in result
        assert "\x01" not in result
        assert "testnullcontrol" == result
    
    def test_sanitize_input_length_limit(self):
        """Test input length limiting."""
        long_input = "a" * 2000
        result = _sanitize_input(long_input, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_input_type_validation(self):
        """Test input type validation."""
        with pytest.raises(ValueError, match="Input must be a string"):
            _sanitize_input(123)
        
        with pytest.raises(ValueError, match="Input must be a string"):
            _sanitize_input(None)
        
        with pytest.raises(ValueError, match="Input must be a string"):
            _sanitize_input([])


class TestValidation:
    """Tests for validation functions."""
    
    def test_validate_repo_name_valid(self):
        """Test valid repository names."""
        assert _validate_repo_name("owner/repo")
        assert _validate_repo_name("microsoft/vscode")
        assert _validate_repo_name("user123/my-repo.test")
    
    def test_validate_repo_name_invalid_format(self):
        """Test invalid repository name formats."""
        with pytest.raises(ValueError, match="Invalid repository format"):
            _validate_repo_name("invalid")
        
        with pytest.raises(ValueError, match="Invalid repository format"):
            _validate_repo_name("no-slash")
        
        with pytest.raises(ValueError, match="Invalid repository format"):
            _validate_repo_name("owner/")
        
        with pytest.raises(ValueError, match="Invalid repository format"):
            _validate_repo_name("/repo")
    
    def test_validate_repo_name_injection(self):
        """Test repository name injection prevention."""
        with pytest.raises(ValueError, match="Invalid repository format"):
            _validate_repo_name("owner/repo; rm -rf /")
        
        with pytest.raises(ValueError, match="Invalid repository format"):
            _validate_repo_name("owner/repo`whoami`")
    
    def test_validate_repo_name_empty(self):
        """Test empty repository name validation."""
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_repo_name("")
        
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_repo_name(None)
    
    def test_validate_path_valid(self):
        """Test valid path validation."""
        current = Path.cwd()
        result = _validate_path(current)
        assert result.is_absolute()
        assert result == current.resolve()
    
    def test_validate_path_traversal_prevention(self):
        """Test path traversal prevention."""
        base = Path("/tmp/test")
        malicious = Path("/etc/passwd")
        
        with pytest.raises(ValueError, match="outside"):
            _validate_path(malicious, base_path=base)


class TestReleaseFlowInit:
    """Tests for ReleaseFlow initialization."""
    
    @patch('release_flow.core.Github')
    @patch('release_flow.core._ensure_github')
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'test_token'}, clear=True)
    def test_init_with_valid_config(self, mock_ensure, mock_github_class):
        """Test initialization with valid configuration."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github
        
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            github_token="test_token"
        )
        
        flow = ReleaseFlow(config)
        
        assert flow.repo == "owner/repo"
        assert flow.github_token == "test_token"
        assert flow.local_path.is_absolute()
    
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'test_token'}, clear=True)
    def test_init_with_invalid_repo(self):
        """Test initialization with invalid repository raises error during config creation."""
        # The error should be raised by ReleaseFlowConfig, not ReleaseFlow
        with pytest.raises(ValueError, match="Invalid repository format"):
            config = ReleaseFlowConfig(
                repo="invalid-repo",
                local_path=Path.cwd(),
                github_token="test_token"
            )
    
    @patch.dict('os.environ', {}, clear=True)
    def test_init_without_token(self):
        """Test initialization without GitHub token."""
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            github_token=None
        )
        
        with pytest.raises(ConfigurationError, match="GITHUB_TOKEN not set"):
            ReleaseFlow(config)
    
    @patch('release_flow.core.Github')
    @patch('release_flow.core._ensure_github')
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'test_token'}, clear=True)
    def test_init_with_dict_config(self, mock_ensure, mock_github_class):
        """Test initialization with dictionary configuration."""
        mock_github = Mock()
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github
        
        config_dict = {
            "repo": "owner/repo",
            "local_path": Path.cwd(),
            "github_token": "test_token"
        }
        
        flow = ReleaseFlow(config_dict)
        assert flow.repo == "owner/repo"


@pytest.mark.asyncio
class TestCopilotSession:
    """Tests for Copilot session management."""
    
    async def test_copilot_session_context_manager(self):
        """Test copilot session context manager."""
        mock_flow = Mock()
        mock_flow.initialize_copilot = AsyncMock()
        mock_flow.close_copilot = AsyncMock()
        
        async with copilot_session(mock_flow) as flow:
            assert flow == mock_flow
            mock_flow.initialize_copilot.assert_called_once()
        
        mock_flow.close_copilot.assert_called_once()
    
    async def test_copilot_session_cleanup_on_error(self):
        """Test copilot session cleanup on error."""
        mock_flow = Mock()
        mock_flow.initialize_copilot = AsyncMock()
        mock_flow.close_copilot = AsyncMock()
        
        with pytest.raises(ValueError):
            async with copilot_session(mock_flow):
                raise ValueError("Test error")
        
        mock_flow.close_copilot.assert_called_once()


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""
    
    def test_exception_inheritance(self):
        """Test exception inheritance structure."""
        assert issubclass(ConfigurationError, ReleaseFlowError)
        assert issubclass(GitOperationError, ReleaseFlowError)
        assert issubclass(CopilotError, ReleaseFlowError)
        assert issubclass(PROperationError, ReleaseFlowError)
        assert issubclass(ReleaseFlowError, Exception)
    
    def test_exception_messages(self):
        """Test exception messages."""
        error = ConfigurationError("Test config error")
        assert str(error) == "Test config error"
        
        error = GitOperationError("Test git error")
        assert str(error) == "Test git error"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
