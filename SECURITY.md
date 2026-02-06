# Security Best Practices

## Overview

The Release Flow framework implements multiple security controls to protect against common vulnerabilities. This document outlines the security features and best practices for using the framework safely.

## Security Features

### 1. Input Validation and Sanitization

All user inputs are validated and sanitized to prevent injection attacks:

- **Repository names**: Validated against GitHub naming conventions
- **File paths**: Checked for path traversal attempts and restricted to base directories
- **Git arguments**: Sanitized to prevent command injection
- **Prompts**: Length-limited and checked for malicious content
- **Branch names**: Validated against Git naming rules

### 2. Token Protection

GitHub tokens are handled securely:

- Tokens are automatically redacted from error messages and logs
- No tokens are included in commit messages or PR descriptions
- Pattern matching detects and redacts multiple GitHub token formats (ghp_, github_pat_, gho_)
- Error messages sanitize all output before display

### 3. Command Injection Prevention

All subprocess calls use secure practices:

- Arguments are passed as lists (not strings) to prevent shell interpretation
- Git commands have timeout limits to prevent denial-of-service
- Package installations are validated before execution
- No user input is passed directly to shell commands

### 4. Path Traversal Protection

File system operations are restricted:

- All paths are validated and resolved to absolute paths
- Paths are checked to ensure they stay within the repository directory
- Symlink attacks are mitigated through path resolution
- File operations have size limits

### 5. Timeout Controls

All external operations have timeout limits:

- Git operations: 5 minutes
- Copilot SDK calls: Configurable (default 5 minutes, max 1 hour)
- Package installations: 5 minutes
- GitHub CLI token retrieval: 30 seconds

### 6. Package Installation Security

Automatic package installations are protected:

- Package names are validated against PyPI naming rules
- Suspicious patterns are rejected
- Installations use explicit `--` separator to prevent option injection
- Timeout limits prevent hanging installations

## Usage Recommendations

### 1. Token Management

**Best practices:**
- Use environment variables or `.env` files for tokens (never commit `.env`)
- Prefer GitHub CLI authentication (`gh auth login`) when possible
- Rotate tokens regularly
- Use fine-grained tokens with minimum required permissions

**Required permissions:**
- `repo` - Repository read/write
- `workflow` - For CI integration (if using auto-merge)

### 2. Repository Permissions

Only run Release Flow on repositories you trust and have permission to modify:

```python
# Good: Your own repository
config = ReleaseFlowConfig(repo="yourname/yourrepo")

# Caution: Ensure you have write access
config = ReleaseFlowConfig(repo="organization/repo")
```

### 3. Prompt Safety

While prompts are sanitized, follow these guidelines:

- Keep prompts focused and specific
- Avoid extremely large prompts (> 10KB)
- Review changes before merging
- Use `auto_merge=False` for sensitive changes

### 4. Local Repository Safety

Ensure your local repository is in a safe location:

```python
# Good: Explicit, validated path
config = ReleaseFlowConfig(
    repo="owner/repo",
    local_path=Path("/path/to/safe/directory")
)

# Avoid: Untrusted user input
# user_path = input("Enter path: ")  # Don't do this
```

### 5. Continuous Mode Safety

When using continuous mode:

- Set reasonable iteration limits
- Use appropriate delays between runs
- Enable `stop_on_failure` for critical repositories
- Monitor PR creation and review them regularly

```python
config = ReleaseFlowConfig(
    repo="owner/repo",
    continuous=ContinuousConfig(
        max_iterations=5,  # Limit iterations
        delay_between_runs=3600,  # 1 hour between runs
        stop_on_failure=True,  # Stop on errors
    )
)
```

## Error Handling

The framework implements secure error handling:

- Exceptions are caught and logged safely
- Sensitive information is redacted from error messages
- Stack traces don't expose tokens or credentials
- Failed operations are tracked without leaking data

## Security Testing

To test security features:

```python
from release_flow.security import (
    validate_repo_name,
    validate_path,
    sanitize_git_arg,
    SecurityError,
)

# Test repository validation
try:
    validate_repo_name("../../../etc/passwd")
except SecurityError:
    print("✓ Path traversal blocked")

# Test git argument sanitization
try:
    sanitize_git_arg("main; rm -rf /")
except SecurityError:
    print("✓ Command injection blocked")
```

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public issue
2. Email security concerns to the maintainers
3. Provide details about the vulnerability
4. Wait for a response before disclosing publicly

## Security Updates

The framework is regularly updated for security:

- Dependencies are checked for vulnerabilities
- Security patches are applied promptly
- Best practices are updated as threats evolve

## Compliance

The framework follows these security standards:

- OWASP Top 10 guidance
- GitHub Security Best Practices
- Principle of least privilege
- Defense in depth approach

## Limitations

Be aware of these limitations:

1. **Copilot SDK Trust**: The framework trusts Copilot SDK responses
2. **GitHub API**: Relies on GitHub's security for API calls
3. **Local Environment**: Cannot protect against compromised local systems
4. **Review Required**: Automated changes should still be reviewed by humans

## Example: Secure Setup

```python
import os
from pathlib import Path
from release_flow import ReleaseFlowConfig, ReleaseFlow

# Load token securely
token = os.environ.get("GITHUB_TOKEN")
if not token:
    raise ValueError("GITHUB_TOKEN not set")

# Validate paths
base_dir = Path(__file__).parent.resolve()

config = ReleaseFlowConfig(
    repo="owner/repo",
    local_path=base_dir,
    github_token=token,
    prompts=["Improve error handling"],  # Specific, safe prompts
)

# Use context manager for cleanup
flow = ReleaseFlow(config)

# Run with auto_merge disabled for review
result = await flow.run_single_iteration(
    prompt="Add input validation",
    auto_merge=False  # Manual review required
)

print(f"PR created: #{result['pr_number']}")
print("Please review changes before merging")
```

## Additional Resources

- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [Python Security Guide](https://python.readthedocs.io/en/stable/library/security_warnings.html)
