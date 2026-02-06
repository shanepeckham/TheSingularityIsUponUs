#!/usr/bin/env python3
"""
Test script to verify security features of the Release Flow framework.

This script demonstrates that security vulnerabilities have been fixed.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from security import (
    SecurityError,
    validate_repo_name,
    validate_path,
    validate_branch_name,
    sanitize_git_arg,
    sanitize_prompt,
    sanitize_commit_message,
    redact_token,
    validate_package_name,
)


def test_security_features():
    """Run security feature tests."""
    print("🔒 Testing Release Flow Security Features\n")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    # Test 1: Command Injection Prevention
    print("\n1. Command Injection Prevention")
    test_cases = [
        ("main; rm -rf /", "semicolon injection"),
        ("main && ls", "double ampersand"),
        ("main | cat /etc/passwd", "pipe injection"),
        ("main `whoami`", "backtick injection"),
        ("main $(whoami)", "dollar paren injection"),
    ]
    
    for test_input, description in test_cases:
        try:
            sanitize_git_arg(test_input)
            print(f"   ❌ FAILED: {description} not blocked")
            failed += 1
        except SecurityError:
            print(f"   ✅ PASSED: {description} blocked")
            passed += 1
    
    # Test 2: Path Traversal Prevention
    print("\n2. Path Traversal Prevention")
    base_dir = Path.cwd()
    test_cases = [
        ("../../../etc/passwd", "parent directory traversal"),
        ("/etc/passwd", "absolute path outside base"),
    ]
    
    for test_input, description in test_cases:
        try:
            result = validate_path(test_input, base_dir)
            # Check if result is actually outside base_dir
            try:
                result.relative_to(base_dir)
                print(f"   ❌ FAILED: {description} not blocked")
                failed += 1
            except ValueError:
                print(f"   ❌ FAILED: {description} not blocked")
                failed += 1
        except SecurityError:
            print(f"   ✅ PASSED: {description} blocked")
            passed += 1
    
    # Test 3: Repository Name Validation
    print("\n3. Repository Name Validation")
    test_cases = [
        ("invalid", "missing owner/name format"),
        ("owner/name/extra", "too many slashes"),
        ("../../../etc/passwd", "path traversal in repo"),
        ("owner/name; ls", "command injection in repo"),
    ]
    
    for test_input, description in test_cases:
        try:
            validate_repo_name(test_input)
            print(f"   ❌ FAILED: {description} not blocked")
            failed += 1
        except SecurityError:
            print(f"   ✅ PASSED: {description} blocked")
            passed += 1
    
    # Test 4: Token Redaction
    print("\n4. Token Redaction")
    tokens = [
        ("ghp_1234567890abcdefghijklmnopqrstuvwxyz", "classic token"),
        ("github_pat_" + "A" * 82, "fine-grained token"),
        ("gho_1234567890abcdefghijklmnopqrstuvwxyz", "OAuth token"),
    ]
    
    for token, description in tokens:
        text = f"Error: Authentication failed with token {token}"
        redacted = redact_token(text, token)
        if token not in redacted and ("REDACTED" in redacted or "..." in redacted):
            print(f"   ✅ PASSED: {description} redacted")
            passed += 1
        else:
            print(f"   ❌ FAILED: {description} not redacted")
            failed += 1
    
    # Test 5: Branch Name Validation
    print("\n5. Branch Name Validation")
    test_cases = [
        ("feature/..", "double dot"),
        ("feature@{", "at brace"),
        ("feature\\test", "backslash"),
        ("feature~1", "tilde"),
        ("feature:test", "colon"),
        ("feature?test", "question mark"),
        ("feature*test", "asterisk"),
    ]
    
    for test_input, description in test_cases:
        try:
            validate_branch_name(test_input)
            print(f"   ❌ FAILED: {description} not blocked")
            failed += 1
        except SecurityError:
            print(f"   ✅ PASSED: {description} blocked")
            passed += 1
    
    # Test 6: Package Name Validation
    print("\n6. Package Name Validation")
    test_cases = [
        ("../../etc/passwd", "path traversal"),
        ("package; rm -rf /", "command injection"),
        ("pack${IFS}age", "variable expansion"),
        ("pack`whoami`age", "command substitution"),
    ]
    
    for test_input, description in test_cases:
        try:
            validate_package_name(test_input)
            print(f"   ❌ FAILED: {description} not blocked")
            failed += 1
        except SecurityError:
            print(f"   ✅ PASSED: {description} blocked")
            passed += 1
    
    # Test 7: Prompt Sanitization
    print("\n7. Prompt Sanitization")
    test_cases = [
        ("", "empty prompt"),
        ("A" * 20000, "excessive length"),
        ("\x00\x01\x02" * 100, "excessive control chars"),
    ]
    
    for test_input, description in test_cases:
        try:
            sanitize_prompt(test_input)
            print(f"   ❌ FAILED: {description} not blocked")
            failed += 1
        except SecurityError:
            print(f"   ✅ PASSED: {description} blocked")
            passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"\n📊 Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   Total:  {passed + failed}")
    
    if failed == 0:
        print(f"\n🎉 All security tests passed!")
        return 0
    else:
        print(f"\n⚠️  Some security tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(test_security_features())
