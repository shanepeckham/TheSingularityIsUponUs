# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-06

### 🔒 Security

This release includes comprehensive security hardening to protect against common vulnerabilities.

#### Added

- **Command Injection Prevention**
  - All subprocess calls now use parameterized arguments (`shell=False`)
  - Input sanitization functions: `_sanitize_branch_name()`, `_sanitize_input()`
  - Regular expression validation for all user-controlled inputs
  - Length limits on all string inputs to prevent buffer overflow

- **Path Traversal Protection**
  - `_validate_path()` function validates and resolves all file paths
  - Path resolution prevents symlink attacks
  - Base path validation prevents access outside repository
  - File type validation in prompts file loader

- **Token Security**
  - GitHub tokens never printed to console or logs
  - Error messages sanitized to prevent token leakage
  - Exception handling prevents token exposure in stack traces
  - Secure token retrieval from environment or GitHub CLI

- **Input Validation**
  - `_validate_repo_name()` validates repository format against GitHub rules
  - Configuration validation in `ReleaseFlowConfig.__post_init__()`
  - Timeout value validation (must be positive)
  - Maximum iterations validation (must be positive)
  - Prompt sanitization with length limits
  - Branch name sanitization with character restrictions

- **Resource Exhaustion Prevention**
  - File size limits for prompts files (1MB maximum)
  - Line count limits for text files (1000 lines maximum)
  - Input length limits across all functions
  - Branch name length limits (100 characters)
  - Prompt length limits (2000 characters)

- **Security Testing**
  - `test_security.py` with comprehensive security test suite
  - Tests for sanitization functions
  - Tests for validation functions
  - Tests for configuration validation
  - Tests for injection prevention

- **Security Documentation**
  - `SECURITY.md` with detailed security policy
  - Security best practices guide
  - Security checklist for deployment
  - Vulnerability reporting guidelines

#### Changed

- **core.py**
  - Added `re` import for regex validation
  - Added security validation functions (lines 56-127)
  - Updated `__init__()` with input validation (lines 167-186)
  - Updated `create_branch()` with sanitization (lines 244-265)
  - Updated `evaluate_and_implement()` with sanitization (lines 267-291)
  - Updated `_fallback_copilot_cli()` with sanitization (lines 326-364)
  - Updated `commit_changes()` with sanitization (lines 376-410)
  - Updated `create_pull_request()` with sanitization (lines 412-463)

- **cli.py**
  - Updated `load_prompts_from_file()` with security checks (lines 150-193)
  - Added file size validation
  - Added line count limits
  - Added file type validation
  - Added encoding validation
  - Updated `main()` with input validation (lines 161-233)
  - Added path existence checks
  - Added repository format validation

- **config.py**
  - Enhanced `__post_init__()` with comprehensive validation (lines 147-173)
  - Added repository format validation
  - Added timeout value validation
  - Added iteration count validation
  - Added delay value validation

- **README.md**
  - Added security section highlighting protection measures
  - Added security best practices section
  - Added testing instructions
  - Updated requirements section with security notes

#### Fixed

- Command injection vulnerability through unsanitized branch names
- Command injection vulnerability through unsanitized commit messages
- Path traversal vulnerability in prompts file loading
- Token exposure in error messages and logs
- Lack of input validation on repository names
- Lack of input validation on user prompts
- Resource exhaustion via large prompts files
- Missing subprocess security (shell=True usage)

### 📝 Documentation

- Added `SECURITY.md` with comprehensive security documentation
- Added security section to README
- Added `test_security.py` with test coverage
- Added inline comments for security-critical code
- Added docstrings for all security functions

### ✅ Testing

- All security tests passing
- Python syntax validation passing
- Import tests passing
- Function tests passing
- Configuration validation tests passing

### 🔄 Backward Compatibility

All changes maintain full backward compatibility:
- No breaking API changes
- Existing configurations continue to work
- Additional validation may reject previously accepted invalid inputs (security improvement)
- No changes to CLI interface
- No changes to callback signatures

### 📊 Impact Summary

**Files Modified**: 4
- `core.py`: Added 71 lines of security code, modified 10 functions
- `cli.py`: Modified 2 functions with security improvements
- `config.py`: Enhanced validation in `__post_init__()`
- `README.md`: Added security documentation sections

**Files Added**: 3
- `SECURITY.md`: Comprehensive security policy (147 lines)
- `CHANGELOG.md`: Version history and changes (This file)
- `test_security.py`: Security test suite (190 lines)

**Security Vulnerabilities Fixed**: 8
1. Command injection via branch names
2. Command injection via commit messages
3. Command injection via prompts
4. Path traversal in file operations
5. Token exposure in logs/errors
6. Lack of repository name validation
7. Resource exhaustion via large files
8. Unsafe subprocess execution

### 🎯 Testing Recommendations

1. **Run security tests**:
   ```bash
   python test_security.py
   ```

2. **Validate syntax**:
   ```bash
   python -m py_compile *.py
   ```

3. **Test with invalid inputs**:
   - Try malformed repository names
   - Try injection attempts in prompts
   - Try path traversal in file paths
   - Verify error messages don't leak tokens

4. **Integration testing**:
   - Test with real GitHub repository (non-production)
   - Verify branch creation with special characters
   - Verify PR creation with sanitized content
   - Test prompts file loading with large files

### 🚀 Upgrade Instructions

No special upgrade steps required. Simply update your files:

```bash
# If installed as package
pip install --upgrade release-flow

# If using local files
git pull origin main
python test_security.py  # Verify everything works
```

### ⚠️ Breaking Changes

None. All changes are backward compatible.

### 📚 Additional Resources

- Security documentation: [SECURITY.md](SECURITY.md)
- Test suite: [test_security.py](test_security.py)
- README updates: [README.md](README.md)

---

For questions or security concerns, please contact the maintainers.
