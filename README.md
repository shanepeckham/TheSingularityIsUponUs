# Release Flow Framework

A self-contained, pluggable framework for automated code improvement using GitHub Copilot SDK. This framework creates a continuous improvement loop that evaluates your codebase, implements changes, raises PRs, and optionally auto-merges them.

## 🔒 Security

This framework implements comprehensive security measures to protect against common vulnerabilities:

- **Command Injection Prevention**: All subprocess calls use parameterized arguments
- **Path Traversal Protection**: File paths are validated and sanitized
- **Token Security**: GitHub tokens never exposed in logs or error messages
- **Input Validation**: All user input sanitized with length limits
- **Resource Limits**: Protection against DoS via large files or inputs

See [SECURITY.md](SECURITY.md) for detailed security documentation.

## Features

- **Automated Code Improvement**: Use Copilot to analyze and improve your codebase
- **PR Workflow**: Automatically create branches, commits, and pull requests
- **CI Integration**: Wait for CI checks before merging
- **Continuous Mode**: Run multiple improvement iterations automatically
- **Highly Configurable**: Customize every aspect of the workflow
- **Easy Integration**: Drop into any Python project
- **Callbacks**: Hook into the workflow for custom integrations

## Quick Start

### Installation

Copy the `release_flow` folder into your project, or install as a package:

```bash
# Option 1: Copy the folder
cp -r release_flow /path/to/your/project/

# Option 2: Install as editable package
cd release_flow
pip install -e .
```

### Dependencies

```bash
pip install PyGithub github-copilot-sdk python-dotenv
```

### Authentication

Set your GitHub token:

```bash
# Option 1: Environment variable
export GITHUB_TOKEN="your_token_here"

# Option 2: .env file
echo 'GITHUB_TOKEN=your_token_here' >> .env

# Option 3: GitHub CLI (token auto-detected)
gh auth login
```

### Basic Usage

#### Command Line

```bash
# Single improvement
python -m release_flow --repo owner/repo --prompt "Add error handling"

# Continuous mode with auto-merge
python -m release_flow --repo owner/repo --continuous --auto-merge

# Custom iterations and delay
python -m release_flow --repo owner/repo --continuous -i 5 -d 1800 --auto-merge
```

#### Python API

```python
import asyncio
from release_flow import ReleaseFlow, ReleaseFlowConfig

# Simple usage
config = ReleaseFlowConfig(repo="owner/repo")
flow = ReleaseFlow(config)

# Run single iteration
result = asyncio.run(flow.run_single_iteration(
    prompt="Improve error handling",
    auto_merge=True
))

print(f"PR: #{result['pr_number']}")
```

## Configuration

### ReleaseFlowConfig

The main configuration class with all options:

```python
from pathlib import Path
from release_flow import (
    ReleaseFlowConfig,
    GitConfig,
    CopilotConfig,
    PRConfig,
    ContinuousConfig,
)

config = ReleaseFlowConfig(
    # Required
    repo="owner/repo",
    
    # Optional
    local_path=Path("."),
    github_token="...",  # Falls back to GITHUB_TOKEN env or gh CLI
    
    # Custom prompts for continuous mode
    prompts=[
        "Fix security vulnerabilities",
        "Add unit tests",
        "Improve documentation",
    ],
    
    # Sub-configurations
    git=GitConfig(
        main_branch="main",
        branch_prefix="copilot-improvement",
        commit_prefix="🤖 Copilot:",
        auto_stash=True,
        force_reset=True,
    ),
    
    copilot=CopilotConfig(
        timeout=300,
        fallback_to_cli=True,
        cli_command="copilot",
    ),
    
    pr=PRConfig(
        title_prefix="🤖 Copilot:",
        auto_request_review=True,
        merge_method="squash",  # "merge", "squash", or "rebase"
        wait_for_ci=True,
        ci_timeout=600,
        delete_branch_after_merge=True,
    ),
    
    continuous=ContinuousConfig(
        max_iterations=10,
        delay_between_runs=3600,  # 1 hour
        stop_on_failure=False,
    ),
)
```

### Callbacks

Hook into the workflow with callbacks:

```python
def on_iteration_start(iteration: int, prompt: str):
    print(f"Starting iteration {iteration}: {prompt}")

def on_pr_created(pr_number: int, url: str):
    # Send notification, update dashboard, etc.
    slack_notify(f"New PR: {url}")

def on_error(e: Exception) -> bool:
    log_error(e)
    return True  # Continue, or False to stop

config = ReleaseFlowConfig(
    repo="owner/repo",
    on_iteration_start=on_iteration_start,
    on_pr_created=on_pr_created,
    on_error=on_error,
)
```

## CLI Options

```
usage: release_flow [-h] --repo REPO (--prompt PROMPT | --continuous)
                    [--auto-merge] [--iterations N] [--delay SECONDS]
                    [--path PATH] [--prompts-file FILE] [--main-branch BRANCH]
                    [--no-wait-ci] [--merge-method METHOD] [--timeout SECONDS]
                    [--stop-on-failure]

Options:
  --repo, -r         Target repository (owner/name)
  --prompt, -p       Single improvement prompt
  --continuous, -c   Run in continuous mode
  --auto-merge, -m   Auto-merge PRs after CI passes
  --iterations, -i   Max iterations (default: 10)
  --delay, -d        Delay between iterations in seconds (default: 3600)
  --path             Local repo path (default: .)
  --prompts-file     File with prompts (one per line)
  --main-branch      Main branch name (default: main)
  --no-wait-ci       Skip CI check waiting
  --merge-method     Merge method: merge, squash, rebase (default: squash)
  --timeout          Copilot timeout in seconds (default: 300)
  --stop-on-failure  Stop if an iteration fails
```

## Custom Prompts File

Create a file with one prompt per line:

```text
# prompts.txt
# Lines starting with # are ignored

Review security vulnerabilities and fix them
Add comprehensive error handling
Improve test coverage for edge cases
Refactor for better maintainability
Update deprecated dependencies
```

Use with:

```bash
python -m release_flow --repo owner/repo --prompts-file prompts.txt --continuous
```

## Workflow

1. **Initialize**: Connect to GitHub and Copilot SDK
2. **Clean State**: Stash changes, checkout main, pull latest
3. **Create Branch**: Create a feature branch from main
4. **Evaluate**: Send prompt to Copilot, let it analyze and modify code
5. **Commit**: Stage and commit changes
6. **Push**: Push branch to origin
7. **Create PR**: Open a pull request with details
8. **Request Review**: Ask Copilot to review the PR
9. **Wait for CI**: Poll until CI checks pass
10. **Merge**: Squash merge the PR (if auto-merge enabled)
11. **Loop**: Repeat with the next prompt (continuous mode)

## Integration Examples

### GitHub Actions

```yaml
# .github/workflows/release-flow.yml
name: Release Flow

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:
    inputs:
      prompt:
        description: 'Improvement prompt'
        required: false

jobs:
  improve:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install PyGithub github-copilot-sdk python-dotenv
      
      - name: Run Release Flow
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if [ -n "${{ github.event.inputs.prompt }}" ]; then
            python -m release_flow --repo ${{ github.repository }} \
              --prompt "${{ github.event.inputs.prompt }}" --auto-merge
          else
            python -m release_flow --repo ${{ github.repository }} \
              --continuous --iterations 1 --auto-merge
          fi
```

### Programmatic Integration

```python
import asyncio
from release_flow import ReleaseFlow, ReleaseFlowConfig

async def run_improvements():
    config = ReleaseFlowConfig(
        repo="my-org/my-repo",
        prompts=[
            "Analyze this codebase and suggest architectural improvements",
            "Find and fix potential memory leaks",
            "Add input validation where missing",
        ],
        continuous=ContinuousConfig(
            max_iterations=3,
            delay_between_runs=60,  # 1 minute for testing
        ),
    )
    
    flow = ReleaseFlow(config)
    results = await flow.run_continuous(auto_merge=False)
    
    # Process results
    for r in results:
        if r["success"] and r["pr_number"]:
            print(f"Review needed: https://github.com/my-org/my-repo/pull/{r['pr_number']}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_improvements())
```

## File Structure

```
release_flow/
├── __init__.py      # Package exports
├── __main__.py      # python -m release_flow support
├── cli.py           # Command-line interface
├── config.py        # Configuration dataclasses
├── core.py          # Main ReleaseFlow class
├── pyproject.toml   # Package configuration
└── README.md        # This file
```

## Requirements

- Python 3.10+
- GitHub token with `repo` and `workflow` permissions
- GitHub Copilot subscription (for Copilot SDK)
- Git installed locally

## Security

This framework has been hardened against common security vulnerabilities:

- ✅ Command injection prevention
- ✅ Path traversal protection  
- ✅ Token exposure prevention
- ✅ Input validation and sanitization
- ✅ Resource exhaustion protection
- ✅ Subprocess security

For detailed security information, see [SECURITY.md](SECURITY.md).

### Security Best Practices

1. Store tokens securely using environment variables or GitHub CLI
2. Only run on trusted repositories
3. Enable branch protection and require code reviews
4. Monitor PR creation activity
5. Use prompts from trusted sources only

## Testing

Run security tests:

```bash
python test_security.py
```

Run syntax validation:

```bash
python -m py_compile *.py
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or PR.
