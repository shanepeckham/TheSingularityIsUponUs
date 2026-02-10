#!/usr/bin/env python3
"""
Command-line interface for the Release Flow framework.

Usage:
    # Single prompt mode
    python -m release_flow --prompt "Add error handling"
    
    # Continuous mode (reads from prompts.txt by default)
    python -m release_flow --continuous --auto-merge
    
    # With custom prompts file
    python -m release_flow --prompts-file custom.txt --continuous
    
Environment Variables (required):
    GITHUB_REPO_OWNER - Repository owner (e.g., 'microsoft')
    GITHUB_REPO_NAME  - Repository name (e.g., 'vscode')
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="release_flow",
        description="Automated Release Flow using GitHub Copilot SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single improvement
  %(prog)s --prompt "Add error handling"
  
  # Run continuous mode (uses prompts.txt by default)
  %(prog)s --continuous --auto-merge
  
  # Use custom prompts file
  %(prog)s --prompts-file custom.txt --continuous

Environment Variables:
  GITHUB_TOKEN       GitHub personal access token (or use 'gh auth login')
  GITHUB_REPO_OWNER  Repository owner (e.g., 'microsoft')
  GITHUB_REPO_NAME   Repository name (e.g., 'vscode')
"""
    )
    
    # Mode selection (not required - defaults to prompts.txt if exists)
    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument(
        "--prompt", "-p",
        type=str,
        help="Single prompt to evaluate and implement",
    )
    mode_group.add_argument(
        "--continuous", "-c",
        action="store_true",
        help="Run in continuous mode (uses prompts.txt by default)",
    )
    mode_group.add_argument(
        "--assess",
        action="store_true",
        help="Run Operator assessment only (no agent work). "
             "Analyses the codebase, defines a roadmap, and writes prompts.txt.",
    )
    
    # Optional arguments
    parser.add_argument(
        "--auto-merge", "-m",
        action="store_true",
        help="Automatically merge PRs after CI passes",
    )
    
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=10,
        help="Maximum iterations in continuous mode (default: 10)",
    )
    
    parser.add_argument(
        "--delay", "-d",
        type=int,
        default=3600,
        help="Delay between iterations in seconds (default: 3600)",
    )
    
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Local path to the repository (default: current directory)",
    )
    
    parser.add_argument(
        "--prompts-file",
        type=str,
        default="prompts.txt",
        help="Path to file with prompts (default: prompts.txt)",
    )
    
    parser.add_argument(
        "--main-branch",
        type=str,
        default="main",
        help="Main branch name (default: main)",
    )
    
    parser.add_argument(
        "--no-wait-ci",
        action="store_true",
        help="Don't wait for CI checks",
    )
    
    parser.add_argument(
        "--merge-method",
        type=str,
        choices=["merge", "squash", "rebase"],
        default="squash",
        help="PR merge method (default: squash)",
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout for Copilot operations in seconds (default: 300)",
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Copilot model to use (e.g., 'gpt-4o', 'claude-3.5-sonnet')",
    )
    
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop continuous mode if an iteration fails",
    )
    
    # --- Operator (LLM-as-judge / product owner) options ---
    operator_group = parser.add_argument_group(
        "Operator options",
        "Configure the Operator: a second LLM that acts as product owner and judge.",
    )
    operator_group.add_argument(
        "--with-operator",
        action="store_true",
        help="Enable the Operator (LLM-as-judge). "
             "The Operator assesses the codebase, generates prompts, "
             "and judges each iteration's changes.",
    )
    operator_group.add_argument(
        "--operator-model",
        type=str,
        default="claude-3.5-sonnet",
        help="Model for the Operator (must differ from --model). "
             "Default: claude-3.5-sonnet",
    )
    operator_group.add_argument(
        "--operator-timeout",
        type=int,
        default=300,
        help="Timeout for Operator LLM calls in seconds (default: 300)",
    )
    operator_group.add_argument(
        "--no-operator-judge",
        action="store_true",
        help="Disable post-iteration judging by the Operator",
    )
    operator_group.add_argument(
        "--stop-on-fail-verdict",
        action="store_true",
        help="Stop continuous mode if the Operator gives a FAIL verdict",
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 1.0.0",
    )
    
    return parser


def load_prompts_from_file(filepath: str) -> list[str]:
    """
    Load prompts from a text file (one per line).
    
    Args:
        filepath: Path to the prompts file.
        
    Returns:
        List of sanitized prompts.
        
    Raises:
        ValueError: If file path is invalid or file is too large.
    """
    from pathlib import Path
    
    try:
        # Validate the file path to prevent path traversal
        file_path = Path(filepath).resolve()
        
        # Security: Check file size to prevent DoS via huge files
        max_size = 1024 * 1024  # 1MB
        if file_path.stat().st_size > max_size:
            raise ValueError(f"Prompts file too large (max {max_size} bytes)")
        
        # Security: Only read from regular files
        if not file_path.is_file():
            raise ValueError(f"Not a regular file: {filepath}")
        
        prompts = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # Limit lines processed to prevent DoS
                if line_num > 1000:
                    raise ValueError("Too many lines in prompts file (max 1000)")
                
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith("#"):
                    # Sanitize each prompt
                    sanitized = line[:1000]  # Limit prompt length
                    prompts.append(sanitized)
        
        if not prompts:
            raise ValueError("No valid prompts found in file")
        
        return prompts
        
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"Failed to read prompts file '{filepath}': {e}") from e


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Import here to avoid circular imports
    from .config import (
        ReleaseFlowConfig,
        GitConfig,
        CopilotConfig,
        PRConfig,
        ContinuousConfig,
        OperatorConfig,
    )
    from .core import ReleaseFlow
    
    # Build configuration
    prompts = []
    
    # Load prompts from file (defaults to prompts.txt)
    prompts_file = Path(args.prompts_file)
    if prompts_file.exists():
        try:
            prompts = load_prompts_from_file(str(prompts_file))
            print(f"ℹ️  Loaded {len(prompts)} prompts from {prompts_file}")
        except ValueError as e:
            print(f"❌ Error loading prompts file: {e}")
            sys.exit(1)
    elif args.prompts_file != "prompts.txt":
        # User specified a custom file that doesn't exist
        print(f"❌ Prompts file not found: {args.prompts_file}")
        sys.exit(1)
    elif args.continuous:
        print("❌ Error: prompts.txt not found. Create it or use --prompts-file")
        sys.exit(1)
    
    # Get repository from environment variables
    repo_owner = os.environ.get("GITHUB_REPO_OWNER")
    repo_name = os.environ.get("GITHUB_REPO_NAME")
    
    if not repo_owner or not repo_name:
        print("❌ Error: GITHUB_REPO_OWNER and GITHUB_REPO_NAME must be set in environment or .env file")
        sys.exit(1)
    
    repo = f"{repo_owner}/{repo_name}"
    
    # Determine mode
    if not args.prompt and not args.continuous and not args.assess:
        # Default to continuous mode if prompts.txt exists
        if prompts:
            args.continuous = True
            print("ℹ️  Running in continuous mode (prompts.txt found)")
        else:
            print("❌ Error: Specify --prompt, --continuous, or --assess, or create prompts.txt")
            sys.exit(1)
    
    # Validate path
    try:
        local_path = Path(args.path).resolve()
        if not local_path.exists():
            print(f"❌ Path does not exist: {local_path}")
            sys.exit(1)
    except (OSError, RuntimeError) as e:
        print(f"❌ Invalid path: {e}")
        sys.exit(1)
    
    # Enable operator if --assess or --with-operator
    operator_enabled = args.with_operator or args.assess
    
    config = ReleaseFlowConfig(
        repo=repo,
        local_path=local_path,
        prompts=prompts,
        git=GitConfig(
            main_branch=args.main_branch,
        ),
        copilot=CopilotConfig(
            timeout=args.timeout,
            model=args.model,
        ),
        pr=PRConfig(
            merge_method=args.merge_method,
            wait_for_ci=not args.no_wait_ci,
        ),
        continuous=ContinuousConfig(
            max_iterations=args.iterations,
            delay_between_runs=args.delay,
            stop_on_failure=args.stop_on_failure,
        ),
        operator=OperatorConfig(
            enabled=operator_enabled,
            model=args.operator_model,
            timeout=args.operator_timeout,
            judge_after_iteration=not args.no_operator_judge,
            generate_prompts_before_run=operator_enabled,
            update_prompts_after_run=operator_enabled,
            stop_on_fail_verdict=args.stop_on_fail_verdict,
        ),
    )
    
    # Initialize the release flow
    try:
        flow = ReleaseFlow(config)
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    
    # Run
    if args.assess:
        # Operator-only mode: assess, roadmap, generate prompts
        from .judge import Operator
        operator = Operator(config)
        result = asyncio.run(operator.run_full_assessment(update_prompts=True))
        
        print(f"\n✅ Operator assessment complete")
        print(f"   Prompts written to: {result.get('prompts_file', 'N/A')}")
        print(f"   Total prompts generated: {len(result.get('prompts', []))}")
        
        if result.get("assessment"):
            print(f"\n{'=' * 60}")
            print("📋 ASSESSMENT SUMMARY")
            print(f"{'=' * 60}")
            print(result["assessment"][:2000])
        
        if result.get("roadmap"):
            print(f"\n{'=' * 60}")
            print("🗺️  ROADMAP")
            print(f"{'=' * 60}")
            print(result["roadmap"][:2000])
    
    elif args.continuous:
        results = asyncio.run(flow.run_continuous(
            auto_merge=args.auto_merge,
        ))
        
        # Exit with error if any iteration failed
        if any(not r["success"] for r in results):
            sys.exit(1)
    else:
        result = asyncio.run(flow.run_single_iteration(
            prompt=args.prompt,
            auto_merge=args.auto_merge,
        ))
        
        if result["success"]:
            print(f"\n✅ Release flow completed successfully!")
            if result["pr_number"]:
                print(f"   PR: https://github.com/{repo}/pull/{result['pr_number']}")
        else:
            print(f"\n❌ Release flow failed: {result['error']}")
            sys.exit(1)


if __name__ == "__main__":
    main()
