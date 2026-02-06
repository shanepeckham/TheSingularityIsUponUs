"""
Configuration classes for the Release Flow framework.

This module provides dataclasses for configuring the release flow,
making it easy to customize for different projects.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable


@dataclass
class GitConfig:
    """Configuration for Git operations."""
    
    main_branch: str = "main"
    """The main/default branch name (e.g., 'main' or 'master')."""
    
    branch_prefix: str = "copilot-improvement"
    """Prefix for feature branches created by the release flow."""
    
    commit_prefix: str = "🤖 Copilot:"
    """Prefix for commit messages."""
    
    auto_stash: bool = True
    """Whether to automatically stash changes before operations."""
    
    force_reset: bool = True
    """Whether to force reset to origin when ensuring clean state."""


@dataclass
class CopilotConfig:
    """Configuration for Copilot SDK integration."""
    
    timeout: int = 300
    """Timeout in seconds for Copilot operations."""
    
    fallback_to_cli: bool = True
    """Whether to fall back to Copilot CLI if SDK fails."""
    
    cli_command: str = "copilot"
    """The command to invoke Copilot CLI."""


@dataclass
class PRConfig:
    """Configuration for Pull Request creation and management."""
    
    title_prefix: str = "🤖 Copilot:"
    """Prefix for PR titles."""
    
    auto_request_review: bool = True
    """Whether to automatically request a Copilot review."""
    
    merge_method: str = "squash"
    """Merge method: 'merge', 'squash', or 'rebase'."""
    
    wait_for_ci: bool = True
    """Whether to wait for CI checks before merging."""
    
    ci_timeout: int = 600
    """Timeout in seconds for waiting for CI checks."""
    
    delete_branch_after_merge: bool = True
    """Whether to delete the branch after merging."""


@dataclass
class ContinuousConfig:
    """Configuration for continuous release flow mode."""
    
    max_iterations: int = 10
    """Maximum number of iterations to run."""
    
    delay_between_runs: int = 3600
    """Delay in seconds between iterations (default: 1 hour)."""
    
    stop_on_failure: bool = False
    """Whether to stop the flow if an iteration fails."""


@dataclass
class ReleaseFlowConfig:
    """
    Main configuration for the Release Flow framework.
    
    This dataclass combines all sub-configurations and provides
    sensible defaults for most use cases.
    
    Example:
        ```python
        from release_flow import ReleaseFlowConfig, ReleaseFlow
        
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path("."),
            prompts=["Fix security issues", "Add tests"],
        )
        
        flow = ReleaseFlow(config)
        ```
    """
    
    # Required settings
    repo: str = ""
    """Repository in 'owner/name' format (e.g., 'microsoft/vscode')."""
    
    local_path: Path = field(default_factory=Path.cwd)
    """Local path to the repository."""
    
    # Authentication
    github_token: Optional[str] = None
    """GitHub personal access token. Falls back to gh CLI if not set."""
    
    # Prompts for improvements
    prompts: list[str] = field(default_factory=list)
    """List of prompts during continuous mode."""
    
    # Sub-configurations
    git: GitConfig = field(default_factory=GitConfig)
    """Git-related configuration."""
    
    copilot: CopilotConfig = field(default_factory=CopilotConfig)
    """Copilot SDK configuration."""
    
    pr: PRConfig = field(default_factory=PRConfig)
    """Pull request configuration."""
    
    continuous: ContinuousConfig = field(default_factory=ContinuousConfig)
    """Continuous mode configuration."""
    
    # Callbacks (for custom integrations)
    on_iteration_start: Optional[Callable[[int, str], None]] = None
    """Callback called at the start of each iteration: (iteration, prompt)."""
    
    on_iteration_end: Optional[Callable[[int, dict], None]] = None
    """Callback called at the end of each iteration: (iteration, result)."""
    
    on_pr_created: Optional[Callable[[int, str], None]] = None
    """Callback when a PR is created: (pr_number, url)."""
    
    on_error: Optional[Callable[[Exception], bool]] = None
    """Callback on error. Return True to continue, False to stop."""
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if isinstance(self.local_path, str):
            self.local_path = Path(self.local_path)


# Default prompts for code improvement
DEFAULT_PROMPTS = [
    "Review this codebase for security vulnerabilities and implement fixes",
    "Identify code quality issues and refactor for better maintainability",
    "Add comprehensive error handling where missing",
    "Add or improve unit tests for untested functions",
    "Optimize performance bottlenecks",
    "Update documentation and add missing docstrings",
    "Check for and update deprecated dependencies",
]
