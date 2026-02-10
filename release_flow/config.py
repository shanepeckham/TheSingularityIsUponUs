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
    
    model: Optional[str] = None
    """Model to use (e.g., 'gpt-4o', 'claude-3.5-sonnet'). None uses default."""
    
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
class OperatorConfig:
    """Configuration for the Operator (LLM-as-judge / product owner).

    The Operator uses a *different* model from the self-improving agent to
    provide independent assessment, roadmap definition, and change evaluation.
    """

    enabled: bool = False
    """Whether the Operator is active. When False the agent runs unsupervised."""

    model: Optional[str] = "claude-3.5-sonnet"
    """Model for the Operator. MUST differ from CopilotConfig.model."""

    timeout: int = 300
    """Timeout in seconds for Operator LLM calls."""

    judge_after_iteration: bool = True
    """When True, the Operator judges every iteration's changes."""

    generate_prompts_before_run: bool = True
    """When True, the Operator runs a full assessment and writes prompts.txt
    before the continuous run begins."""

    update_prompts_after_run: bool = True
    """When True, the Operator refreshes prompts.txt after all iterations
    complete, incorporating follow-up items from judging."""

    prompts_file: str = "prompts.txt"
    """Path to the prompts file the Operator manages."""

    stop_on_fail_verdict: bool = False
    """When True, stop the continuous run if the Operator gives a FAIL verdict."""


@dataclass
class ReleaseFlowConfig:
    """Main configuration for the Release Flow framework.

    ⚠️  EXPERIMENTAL — This framework uses unmanaged AI to autonomously
    modify code, create PRs, and optionally merge them. AI-generated
    changes may introduce bugs or security vulnerabilities. Always
    review PRs before merging in production repositories.
    """
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
    
    operator: OperatorConfig = field(default_factory=OperatorConfig)
    """Operator (LLM-as-judge / product owner) configuration."""
    
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
        
        # Validate repository format
        if self.repo:
            import re
            pattern = r'^[a-zA-Z0-9][-a-zA-Z0-9]{0,38}/[a-zA-Z0-9_.-]{1,100}$'
            if not re.match(pattern, self.repo):
                raise ValueError(
                    f"Invalid repository format: '{self.repo}'. "
                    "Expected format: 'owner/name' (e.g., 'microsoft/vscode')"
                )
        
        # Validate timeout values are positive
        if hasattr(self.copilot, 'timeout') and self.copilot.timeout <= 0:
            raise ValueError("Copilot timeout must be positive")
        
        if hasattr(self.pr, 'ci_timeout') and self.pr.ci_timeout <= 0:
            raise ValueError("CI timeout must be positive")
        
        # Validate continuous config
        if hasattr(self.continuous, 'max_iterations') and self.continuous.max_iterations <= 0:
            raise ValueError("Max iterations must be positive")
        
        if hasattr(self.continuous, 'delay_between_runs') and self.continuous.delay_between_runs < 0:
            raise ValueError("Delay between runs cannot be negative")
        
        # Validate operator config
        if hasattr(self.operator, 'timeout') and self.operator.timeout <= 0:
            raise ValueError("Operator timeout must be positive")
        
        # Enforce model separation when operator is enabled
        if self.operator.enabled and self.copilot.model and self.operator.model:
            if self.copilot.model == self.operator.model:
                raise ValueError(
                    f"Operator model must differ from agent model. "
                    f"Both are set to '{self.copilot.model}'. "
                    f"Use a different model for independent evaluation."
                )


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
