#!/usr/bin/env python3
"""
Command-line interface for the Release Flow framework.

Usage:
    # Single prompt mode
    python -m release_flow --repo owner/repo --prompt "Add error handling"
    
    # Continuous mode
    python -m release_flow --repo owner/repo --continuous --auto-merge
    
    # With custom config file
    python -m release_flow --config release_flow.yaml
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
  %(prog)s --repo owner/repo --prompt "Add error handling"
  
  # Run continuous mode with auto-merge
  %(prog)s --repo owner/repo --continuous --auto-merge
  
  # Use custom prompts file
  %(prog)s --repo owner/repo --prompts-file prompts.txt --continuous

Environment Variables:
  GITHUB_TOKEN    GitHub personal access token (or use 'gh auth login')
"""
    )
    
    # Required arguments
    parser.add_argument(
        "--repo", "-r",
        type=str,
        required=True,
        help="Target repository in 'owner/name' format",
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--prompt", "-p",
        type=str,
        help="Single prompt to evaluate and implement",
    )
    mode_group.add_argument(
        "--continuous", "-c",
        action="store_true",
        help="Run in continuous mode with default or custom prompts",
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
        help="Path to file with prompts (one per line)",
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
        "--stop-on-failure",
        action="store_true",
        help="Stop continuous mode if an iteration fails",
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 1.0.0",
    )
    
    return parser


def load_prompts_from_file(filepath: str) -> List[str]:
    """
    Load prompts from a text file (one per line).
    
    Args:
        filepath: Path to the prompts file.
        
    Returns:
        List of prompts.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        IOError: If the file cannot be read.
    """
    if not Path(filepath).exists():
        raise FileNotFoundError(f"Prompts file not found: {filepath}")
    
    prompts = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith("#"):
                    prompts.append(line)
                    logger.debug(f"Loaded prompt {line_num}: {line[:50]}...")
        
        if not prompts:
            logger.warning(f"No valid prompts found in {filepath}")
        
        return prompts
    except IOError as e:
        raise IOError(f"Failed to read prompts file {filepath}: {e}")


def main() -> None:
    """
    Main entry point for the CLI.
    
    Exits with code 0 on success, 1 on failure.
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Import here to avoid circular imports
    from .config import (
        ReleaseFlowConfig,
        GitConfig,
        CopilotConfig,
        PRConfig,
        ContinuousConfig,
        DEFAULT_PROMPTS,
    )
    from .core import ReleaseFlow, ReleaseFlowError
    
    # Build configuration
    prompts = []
    if args.prompts_file:
        try:
            prompts = load_prompts_from_file(args.prompts_file)
            logger.info(f"Loaded {len(prompts)} prompts from {args.prompts_file}")
        except (FileNotFoundError, IOError) as e:
            logger.error(f"❌ {e}")
            print(f"❌ {e}")
            sys.exit(1)
    elif args.continuous:
        prompts = DEFAULT_PROMPTS.copy()
        logger.info(f"Using {len(prompts)} default prompts")
    
    # Validate repository format
    if "/" not in args.repo:
        logger.error(f"❌ Invalid repo format: '{args.repo}'. Expected 'owner/name'")
        print(f"❌ Invalid repo format: '{args.repo}'. Expected 'owner/name'")
        sys.exit(1)
    
    try:
        config = ReleaseFlowConfig(
            repo=args.repo,
            local_path=Path(args.path).resolve(),
            prompts=prompts,
            git=GitConfig(
                main_branch=args.main_branch,
            ),
            copilot=CopilotConfig(
                timeout=args.timeout,
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
        )
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    # Initialize the release flow
    try:
        flow = ReleaseFlow(config)
    except ReleaseFlowError as e:
        logger.error(f"❌ Failed to initialize: {e}")
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error during initialization: {e}", exc_info=True)
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    
    # Run
    try:
        if args.continuous:
            results = asyncio.run(flow.run_continuous(
                auto_merge=args.auto_merge,
            ))
            
            # Print summary
            successful = sum(1 for r in results if r["success"])
            logger.info(f"Completed {successful}/{len(results)} iterations successfully")
            
            # Exit with error if any iteration failed
            if any(not r["success"] for r in results):
                sys.exit(1)
        else:
            result = asyncio.run(flow.run_single_iteration(
                prompt=args.prompt,
                auto_merge=args.auto_merge,
            ))
            
            if result["success"]:
                logger.info("✅ Release flow completed successfully")
                print(f"\n✅ Release flow completed successfully!")
                if result["pr_number"]:
                    pr_url = f"https://github.com/{args.repo}/pull/{result['pr_number']}"
                    print(f"   PR: {pr_url}")
            else:
                logger.error(f"❌ Release flow failed: {result['error']}")
                print(f"\n❌ Release flow failed: {result['error']}")
                sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("\n⚠️ Interrupted by user")
        sys.exit(130)
    except ReleaseFlowError as e:
        logger.error(f"❌ Release flow error: {e}")
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
