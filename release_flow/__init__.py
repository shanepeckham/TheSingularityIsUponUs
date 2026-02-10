"""
Release Flow Framework

An automated release flow using GitHub Copilot SDK that evaluates,
improves, and deploys code changes through pull requests.

Quick Start:
    ```python
    from release_flow import ReleaseFlow, ReleaseFlowConfig
    
    config = ReleaseFlowConfig(
        repo="owner/repo",
        prompts=["Improve error handling", "Add tests"],
    )
    
    flow = ReleaseFlow(config)
    result = await flow.run_single_iteration("Fix security issues")
    ```

Command Line:
    ```bash
    python -m release_flow --repo owner/repo --prompt "Add tests"
    python -m release_flow --repo owner/repo --continuous --auto-merge
    ```
"""

__version__ = "1.0.0"
__author__ = "Release Flow Contributors"

from .config import (
    ReleaseFlowConfig,
    GitConfig,
    CopilotConfig,
    PRConfig,
    ContinuousConfig,
    OperatorConfig,
    DEFAULT_PROMPTS,
)

from .core import (
    ReleaseFlow,
    ReleaseFlowError,
    ConfigurationError,
    GitOperationError,
    CopilotError,
    PROperationError,
)

# Operator imports are lazy — the module is only loaded when explicitly accessed.
# This keeps the operator fully optional at runtime.


def __getattr__(name: str):
    """Lazy-load Operator and OperatorError on first access."""
    if name in ("Operator", "OperatorError"):
        from .judge import Operator, OperatorError  # noqa: F811
        globals()["Operator"] = Operator
        globals()["OperatorError"] = OperatorError
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Version
    "__version__",
    # Config classes
    "ReleaseFlowConfig",
    "GitConfig",
    "CopilotConfig",
    "PRConfig",
    "ContinuousConfig",
    "OperatorConfig",
    "DEFAULT_PROMPTS",
    # Core classes
    "ReleaseFlow",
    "ReleaseFlowError",
    "ConfigurationError",
    "GitOperationError",
    "CopilotError",
    "PROperationError",
    # Operator (lazy-loaded)
    "Operator",
    "OperatorError",
]
