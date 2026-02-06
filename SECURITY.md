# Security Policy

## Security Measures

This document describes the security measures implemented in the Release Flow framework to protect against common vulnerabilities.

## Implemented Security Features

### 1. Command Injection Prevention

**Vulnerability**: User-controlled input could be passed to shell commands, allowing arbitrary command execution.

**Mitigation**:
- All subprocess calls use list arguments instead of shell strings (`shell=False`)
- Branch names, commit messages, and prompts are sanitized using `_sanitize_branch_name()` and `_sanitize_input()`
- Regular expressions remove dangerous characters before passing to git commands
- Input length limits prevent buffer overflow attacks

**Files**: `core.py` lines 56-94, 244-265, 326-364, 376-430

### 2. Path Traversal Prevention

**Vulnerability**: Malicious file paths could access files outside the intended directory.

**Mitigation**:
- All paths validated using `_validate_path()` function
- Paths resolved to absolute paths and checked against base directory
- Symlink attacks prevented through proper path resolution
- File operations restricted to repository directory

**Files**: `core.py` lines 96-127, `cli.py` lines 150-193

### 3. Token Exposure Prevention

**Vulnerability**: GitHub tokens could be logged or displayed in error messages.

**Mitigation**:
- Tokens never printed to console or logs
- Error messages sanitized to remove token information
- Exception handling prevents token leakage in stack traces
- Token stored only in memory, not in files

**Files**: `core.py` lines 167-186

### 4. Input Validation

**Vulnerability**: Malformed or malicious input could cause crashes or security issues.

**Mitigation**:
- Repository names validated against GitHub's naming rules
- All user input sanitized with length limits
- Control characters and null bytes removed
- File upload size limits prevent DoS attacks
- Prompt files limited to 1000 lines and 1MB size

**Files**: `core.py` lines 70-94, `cli.py` lines 150-193, `config.py` lines 147-173

### 5. Subprocess Security

**Vulnerability**: Unsafe subprocess execution could lead to command injection.

**Mitigation**:
- All subprocess calls explicitly set `shell=False`
- Arguments passed as lists, not strings
- Timeout values prevent hanging processes
- Working directory explicitly set to prevent directory traversal
- Command output sanitized before display

**Files**: `core.py` lines 207-220, 326-364

### 6. Resource Exhaustion Prevention

**Vulnerability**: Large inputs or files could cause denial of service.

**Mitigation**:
- Input length limits enforced (prompts: 2000 chars, file names: 200 chars)
- File size limits for prompts files (1MB maximum)
- Maximum line limits for text files (1000 lines)
- Timeout values for all long-running operations
- Branch name length limited to 100 characters

**Files**: `core.py` lines 70-94, `cli.py` lines 150-193

## Security Best Practices

When using this framework:

1. **Token Management**:
   - Use environment variables or GitHub CLI for tokens
   - Never commit tokens to version control
   - Rotate tokens regularly
   - Use tokens with minimum required permissions

2. **Repository Access**:
   - Only run on trusted repositories
   - Review all PRs before merging
   - Enable branch protection rules
   - Require code review for auto-merge

3. **Input Validation**:
   - Validate prompts before passing to the framework
   - Use prompts files from trusted sources only
   - Review custom prompts for malicious content
   - Limit prompt complexity

4. **Monitoring**:
   - Monitor PR creation activity
   - Review commit history regularly
   - Set up alerts for unexpected changes
   - Audit merged PRs

## Reporting Security Issues

If you discover a security vulnerability in this framework, please:

1. **Do not** open a public issue
2. Email the maintainers directly
3. Include detailed reproduction steps
4. Allow time for a fix before disclosure

## Security Checklist

Before deploying this framework:

- [ ] Tokens stored securely (environment variables or secrets manager)
- [ ] Repository access properly configured
- [ ] Branch protection rules enabled
- [ ] PR review requirements configured
- [ ] Monitoring and alerting set up
- [ ] Regular security audits scheduled
- [ ] Dependencies up to date
- [ ] Input validation tested
- [ ] Error handling reviewed
- [ ] Logging configured (without sensitive data)

## Security Updates

Security improvements are continuously added. Always use the latest version and review the changelog for security-related updates.

## Dependencies Security

This framework depends on:
- `PyGithub`: GitHub API client - regularly updated
- `github-copilot-sdk`: Official GitHub Copilot SDK
- `python-dotenv`: Environment variable management

Regularly update dependencies to get security patches:

```bash
pip install --upgrade PyGithub github-copilot-sdk python-dotenv
```

## Version History

### v1.0.0 (Current)
- Initial security hardening
- Command injection prevention
- Path traversal protection
- Token exposure prevention
- Input validation and sanitization
- Subprocess security improvements
- Resource exhaustion prevention

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [Python Security Guide](https://python.readthedocs.io/en/stable/library/security.html)
