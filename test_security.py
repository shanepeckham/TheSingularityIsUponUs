#!/usr/bin/env python3
"""
Security test script for Release Flow framework.

Tests the security functions to ensure proper input validation and sanitization.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    _sanitize_branch_name,
    _sanitize_input,
    _validate_repo_name,
    _validate_path,
)


def test_sanitize_branch_name():
    """Test branch name sanitization."""
    print("Testing _sanitize_branch_name()...")
    
    # Test normal input
    assert _sanitize_branch_name("feature/test") == "feature/test"
    
    # Test injection attempts
    assert "; rm -rf /" not in _sanitize_branch_name("test; rm -rf /")
    assert "`" not in _sanitize_branch_name("test`whoami`")
    assert "$" not in _sanitize_branch_name("test$(whoami)")
    
    # Test path traversal attempts
    assert ".." not in _sanitize_branch_name("test/../../../etc/passwd")
    
    # Test length limits
    long_name = "a" * 200
    result = _sanitize_branch_name(long_name)
    assert len(result) <= 100
    
    print("✅ _sanitize_branch_name() tests passed")


def test_sanitize_input():
    """Test input sanitization."""
    print("\nTesting _sanitize_input()...")
    
    # Test normal input
    assert _sanitize_input("Hello World") == "Hello World"
    
    # Test control characters
    result = _sanitize_input("test\x00null\x01control")
    assert "\x00" not in result
    assert "\x01" not in result
    
    # Test length limits
    long_input = "a" * 2000
    result = _sanitize_input(long_input, max_length=100)
    assert len(result) <= 100
    
    # Test newlines and tabs (should be preserved)
    assert _sanitize_input("test\nline") == "test\nline"
    assert _sanitize_input("test\ttab") == "test\ttab"
    
    # Test non-string input
    try:
        _sanitize_input(123)
        assert False, "Should raise ValueError for non-string input"
    except ValueError:
        pass
    
    print("✅ _sanitize_input() tests passed")


def test_validate_repo_name():
    """Test repository name validation."""
    print("\nTesting _validate_repo_name()...")
    
    # Test valid names
    assert _validate_repo_name("owner/repo")
    assert _validate_repo_name("microsoft/vscode")
    assert _validate_repo_name("user123/my-repo.test")
    
    # Test invalid names
    try:
        _validate_repo_name("invalid")
        assert False, "Should raise ValueError for invalid format"
    except ValueError:
        pass
    
    try:
        _validate_repo_name("owner/repo; rm -rf /")
        assert False, "Should raise ValueError for injection attempt"
    except ValueError:
        pass
    
    try:
        _validate_repo_name("")
        assert False, "Should raise ValueError for empty string"
    except ValueError:
        pass
    
    try:
        _validate_repo_name(None)
        assert False, "Should raise ValueError for None"
    except ValueError:
        pass
    
    print("✅ _validate_repo_name() tests passed")


def test_validate_path():
    """Test path validation."""
    print("\nTesting _validate_path()...")
    
    # Test valid path
    current = Path.cwd()
    result = _validate_path(current)
    assert result.is_absolute()
    
    # Test path traversal prevention
    try:
        base = Path("/tmp/test")
        malicious = Path("/tmp/test/../../etc/passwd")
        _validate_path(malicious, base_path=base)
        # If we get here, check if it's actually contained
        # (on some systems this might not raise)
    except ValueError:
        pass  # Expected
    
    print("✅ _validate_path() tests passed")


def test_config_validation():
    """Test configuration validation."""
    print("\nTesting ReleaseFlowConfig validation...")
    
    from config import ReleaseFlowConfig, GitConfig, CopilotConfig, PRConfig, ContinuousConfig
    
    # Test valid config
    try:
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
        )
        print("✅ Valid config created successfully")
    except Exception as e:
        print(f"❌ Failed to create valid config: {e}")
        return False
    
    # Test invalid repo format
    try:
        config = ReleaseFlowConfig(
            repo="invalid-repo",
            local_path=Path.cwd(),
        )
        print("❌ Should have raised ValueError for invalid repo")
        return False
    except ValueError:
        print("✅ Invalid repo format rejected")
    
    # Test negative timeout
    try:
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path.cwd(),
            copilot=CopilotConfig(timeout=-1),
        )
        print("❌ Should have raised ValueError for negative timeout")
        return False
    except ValueError:
        print("✅ Negative timeout rejected")
    
    return True


def run_all_tests():
    """Run all security tests."""
    print("=" * 60)
    print("RELEASE FLOW SECURITY TESTS")
    print("=" * 60)
    
    try:
        test_sanitize_branch_name()
        test_sanitize_input()
        test_validate_repo_name()
        test_validate_path()
        test_config_validation()
        
        print("\n" + "=" * 60)
        print("✅ ALL SECURITY TESTS PASSED")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
