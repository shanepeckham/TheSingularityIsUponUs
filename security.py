"""
Security utilities for the Release Flow framework.

This module provides functions for secure input validation, sanitization,
and safe handling of sensitive data.
"""

import os
import re
import shlex
from pathlib import Path
from typing import Union, List, Optional


class SecurityError(Exception):
    """Raised when a security validation fails."""
    pass


def sanitize_git_arg(arg: str) -> str:
    """
    Sanitize a git command argument to prevent command injection.
    
    Args:
        arg: The argument to sanitize.
        
    Returns:
        The sanitized argument.
        
    Raises:
        SecurityError: If the argument contains dangerous characters.
    """
    # Reject arguments with potential command injection characters
    dangerous_chars = [';', '|', '&', '$', '`', '\n', '\r', '>', '<', '(', ')']
    for char in dangerous_chars:
        if char in arg:
            raise SecurityError(f"Potentially dangerous character '{char}' in git argument")
    
    # Additional check for shell metacharacters
    if arg.startswith('-') and not arg.startswith('--'):
        # Single dash options are fine, but validate them
        if not re.match(r'^-[a-zA-Z0-9]+$', arg):
            raise SecurityError(f"Invalid option format: {arg}")
    
    return arg


def validate_path(path: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """
    Validate a file path to prevent path traversal attacks.
    
    Args:
        path: The path to validate.
        base_dir: Optional base directory to restrict path to.
        
    Returns:
        The validated absolute path.
        
    Raises:
        SecurityError: If the path is invalid or outside base_dir.
    """
    try:
        path_obj = Path(path).resolve()
    except (ValueError, OSError) as e:
        raise SecurityError(f"Invalid path: {e}")
    
    # Check for path traversal attempts
    if base_dir:
        base_dir = Path(base_dir).resolve()
        try:
            path_obj.relative_to(base_dir)
        except ValueError:
            raise SecurityError(f"Path {path_obj} is outside base directory {base_dir}")
    
    return path_obj


def validate_repo_name(repo: str) -> str:
    """
    Validate a GitHub repository name.
    
    Args:
        repo: Repository name in 'owner/name' format.
        
    Returns:
        The validated repository name.
        
    Raises:
        SecurityError: If the repository name is invalid.
    """
    if not repo or '/' not in repo:
        raise SecurityError("Repository must be in 'owner/name' format")
    
    parts = repo.split('/')
    if len(parts) != 2:
        raise SecurityError("Repository must be in 'owner/name' format")
    
    owner, name = parts
    
    # GitHub allows alphanumeric, hyphens, underscores, and dots
    pattern = r'^[a-zA-Z0-9._-]+$'
    if not re.match(pattern, owner) or not re.match(pattern, name):
        raise SecurityError("Invalid repository name format")
    
    # Prevent excessively long names
    if len(owner) > 100 or len(name) > 100:
        raise SecurityError("Repository name components too long")
    
    return repo


def validate_branch_name(branch: str) -> str:
    """
    Validate a git branch name.
    
    Args:
        branch: The branch name to validate.
        
    Returns:
        The validated branch name.
        
    Raises:
        SecurityError: If the branch name is invalid.
    """
    if not branch or len(branch) > 255:
        raise SecurityError("Invalid branch name length")
    
    # Git branch names have specific rules
    # Cannot contain: .., @{, \, space at start/end, control chars, ~, ^, :, ?, *, [
    invalid_patterns = [
        r'\.\.',  # Double dots
        r'@\{',   # @{
        r'\\',    # Backslash
        r'^\s',   # Leading space
        r'\s$',   # Trailing space
        r'[\x00-\x1f\x7f]',  # Control characters
        r'[~^:?*\[]',  # Special git characters
        r'//',    # Double slash
        r'\.lock$',  # .lock suffix
        r'^/',    # Leading slash
        r'/$',    # Trailing slash
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, branch):
            raise SecurityError(f"Branch name contains invalid pattern: {pattern}")
    
    return branch


def sanitize_prompt(prompt: str, max_length: int = 10000) -> str:
    """
    Sanitize a user-provided prompt.
    
    Args:
        prompt: The prompt to sanitize.
        max_length: Maximum allowed length.
        
    Returns:
        The sanitized prompt.
        
    Raises:
        SecurityError: If the prompt is invalid.
    """
    if not prompt:
        raise SecurityError("Prompt cannot be empty")
    
    if len(prompt) > max_length:
        raise SecurityError(f"Prompt exceeds maximum length of {max_length}")
    
    # Remove null bytes
    prompt = prompt.replace('\x00', '')
    
    # Check for excessive control characters (potential binary data)
    control_chars = sum(1 for c in prompt if ord(c) < 32 and c not in '\n\r\t')
    if control_chars > len(prompt) * 0.1:  # More than 10% control characters
        raise SecurityError("Prompt contains excessive control characters")
    
    return prompt.strip()


def sanitize_commit_message(message: str) -> str:
    """
    Sanitize a commit message.
    
    Args:
        message: The commit message to sanitize.
        
    Returns:
        The sanitized message.
        
    Raises:
        SecurityError: If the message is invalid.
    """
    if not message:
        raise SecurityError("Commit message cannot be empty")
    
    # Remove null bytes and excessive control characters
    message = message.replace('\x00', '')
    
    # Git commit messages should be reasonable length
    if len(message) > 50000:
        raise SecurityError("Commit message too long")
    
    return message


def redact_token(text: str, token: Optional[str] = None) -> str:
    """
    Redact tokens from text to prevent accidental exposure.
    
    Args:
        text: The text that may contain tokens.
        token: Optional specific token to redact.
        
    Returns:
        Text with tokens redacted.
    """
    if not text:
        return text
    
    # Redact specific token if provided
    if token and len(token) > 8:
        text = text.replace(token, f"{token[:4]}...{token[-4:]}")
    
    # Redact common GitHub token patterns
    # Classic tokens: ghp_...
    text = re.sub(r'ghp_[a-zA-Z0-9]{36,}', 'ghp_****REDACTED****', text)
    # Fine-grained tokens: github_pat_...
    text = re.sub(r'github_pat_[a-zA-Z0-9_]{82,}', 'github_pat_****REDACTED****', text)
    # OAuth tokens: gho_...
    text = re.sub(r'gho_[a-zA-Z0-9]{36,}', 'gho_****REDACTED****', text)
    
    return text


def validate_timeout(timeout: int, min_val: int = 1, max_val: int = 3600) -> int:
    """
    Validate a timeout value.
    
    Args:
        timeout: The timeout in seconds.
        min_val: Minimum allowed value.
        max_val: Maximum allowed value.
        
    Returns:
        The validated timeout.
        
    Raises:
        SecurityError: If the timeout is invalid.
    """
    if not isinstance(timeout, int):
        raise SecurityError("Timeout must be an integer")
    
    if timeout < min_val or timeout > max_val:
        raise SecurityError(f"Timeout must be between {min_val} and {max_val} seconds")
    
    return timeout


def safe_subprocess_args(args: List[str]) -> List[str]:
    """
    Safely prepare subprocess arguments to prevent injection.
    
    Args:
        args: List of command arguments.
        
    Returns:
        Validated argument list.
        
    Raises:
        SecurityError: If arguments are invalid.
    """
    if not args:
        raise SecurityError("Command arguments cannot be empty")
    
    # Validate that args is actually a list
    if not isinstance(args, list):
        raise SecurityError("Arguments must be a list")
    
    # Ensure all arguments are strings
    validated = []
    for arg in args:
        if not isinstance(arg, str):
            raise SecurityError(f"All arguments must be strings, got {type(arg)}")
        validated.append(arg)
    
    return validated


def validate_package_name(package: str) -> str:
    """
    Validate a Python package name for installation.
    
    Args:
        package: The package name to validate.
        
    Returns:
        The validated package name.
        
    Raises:
        SecurityError: If the package name is invalid or suspicious.
    """
    if not package:
        raise SecurityError("Package name cannot be empty")
    
    # Basic PyPI package name validation
    # Allow: letters, numbers, hyphens, underscores, dots
    if not re.match(r'^[a-zA-Z0-9._-]+$', package):
        raise SecurityError("Invalid package name format")
    
    # Check length
    if len(package) > 214:  # PyPI limit
        raise SecurityError("Package name too long")
    
    # Prevent obvious malicious patterns
    suspicious = ['..', '//', '\\\\', '${', '`', '$(',  '&&', '||', ';']
    for pattern in suspicious:
        if pattern in package:
            raise SecurityError(f"Package name contains suspicious pattern: {pattern}")
    
    return package
