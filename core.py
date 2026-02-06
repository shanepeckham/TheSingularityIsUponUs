"""
Core Release Flow implementation.

This module contains the main ReleaseFlow class that orchestrates
the automated release process using GitHub Copilot SDK.
"""

import asyncio
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Lazy imports for optional dependencies
Github = None
GithubException = None
CopilotClient = None


def _ensure_github():
    """Ensure PyGithub is installed and imported."""
    global Github, GithubException
    if Github is None:
        try:
            from github import Github as _Github, GithubException as _GithubException
            Github = _Github
            GithubException = _GithubException
        except ImportError:
            print("Installing PyGithub...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub"])
            from github import Github as _Github, GithubException as _GithubException
            Github = _Github
            GithubException = _GithubException


def _ensure_copilot():
    """Ensure Copilot SDK is installed and imported."""
    global CopilotClient
    if CopilotClient is None:
        try:
            from copilot.client import CopilotClient as _CopilotClient
            CopilotClient = _CopilotClient
        except ImportError:
            print("Installing github-copilot-sdk...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "github-copilot-sdk"])
            from copilot.client import CopilotClient as _CopilotClient
            CopilotClient = _CopilotClient


class ReleaseFlowError(Exception):
    """Custom exception for release flow errors."""
    pass


class ReleaseFlow:
    """
    Automated release flow using GitHub Copilot SDK.
    
    This class provides a complete CI/CD automation pipeline that:
    1. Evaluates a codebase using Copilot with a given prompt
    2. Implements recommended changes
    3. Creates a feature branch and commits changes
    4. Opens a pull request
    5. Waits for CI checks
    6. Merges the PR (optionally)
    7. Repeats with the next prompt
    
    Example:
        ```python
        from release_flow import ReleaseFlow, ReleaseFlowConfig
        
        config = ReleaseFlowConfig(
            repo="owner/repo",
            local_path=Path("."),
        )
        
        flow = ReleaseFlow(config)
        
        # Single iteration
        result = await flow.run_single_iteration(
            prompt="Add error handling",
            auto_merge=True
        )
        
        # Continuous mode
        results = await flow.run_continuous(auto_merge=True)
        ```
    """
    
    def __init__(self, config):
        """
        Initialize the release flow.
        
        Args:
            config: ReleaseFlowConfig instance with all settings.
        """
        from .config import ReleaseFlowConfig, DEFAULT_PROMPTS
        
        if isinstance(config, dict):
            config = ReleaseFlowConfig(**config)
        
        self.config = config
        self.local_path = config.local_path
        self.repo = config.repo
        
        # Get GitHub token
        self.github_token = config.github_token or os.environ.get("GITHUB_TOKEN")
        if not self.github_token:
            self.github_token = self._get_gh_token()
        
        if not self.github_token:
            raise ReleaseFlowError(
                "GITHUB_TOKEN not set. Either set the environment variable, "
                "pass it in config, or run 'gh auth login'"
            )
        
        # Initialize GitHub client
        _ensure_github()
        self.github = Github(self.github_token)
        self.gh_repo = self.github.get_repo(self.repo)
        
        # Copilot client (initialized lazily)
        self.copilot_client = None
        
        # Run tracking
        self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Use default prompts if none provided
        if not config.prompts:
            config.prompts = DEFAULT_PROMPTS.copy()
    
    def _get_gh_token(self) -> Optional[str]:
        """Try to get GitHub token from gh CLI."""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    async def initialize_copilot(self):
        """Initialize the Copilot SDK client."""
        _ensure_copilot()
        print("🚀 Initializing Copilot SDK...")
        self.copilot_client = CopilotClient()
        await self.copilot_client.start()
        print("✅ Copilot SDK initialized")
    
    async def close_copilot(self):
        """Close the Copilot SDK client."""
        if self.copilot_client:
            await self.copilot_client.stop()
            self.copilot_client = None
    
    def run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """
        Run a git command in the local repo.
        
        Args:
            *args: Git command arguments.
            check: Whether to raise on non-zero exit code.
            
        Returns:
            CompletedProcess instance.
        """
        return subprocess.run(
            ["git", *args],
            cwd=self.local_path,
            capture_output=True,
            text=True,
            check=check
        )
    
    def ensure_clean_state(self):
        """Ensure the repo is in a clean state on the main branch."""
        main_branch = self.config.git.main_branch
        print(f"🔄 Ensuring clean git state on {main_branch}...")
        
        if self.config.git.auto_stash:
            self.run_git("stash", "--include-untracked", check=False)
        
        self.run_git("checkout", main_branch, check=False)
        
        print("⬇️ Pulling latest code...")
        self.run_git("fetch", "origin")
        self.run_git("pull", "origin", main_branch, "--rebase", check=False)
        
        if self.config.git.force_reset:
            self.run_git("reset", "--hard", f"origin/{main_branch}")
        
        print(f"✅ Repository is clean and up to date")
    
    def create_branch(self, prompt: str) -> str:
        """
        Create a new branch for the changes.
        
        Args:
            prompt: The improvement prompt (used to generate branch name).
            
        Returns:
            The branch name.
        """
        prefix = self.config.git.branch_prefix
        words = prompt.lower().split()[:4]
        branch_suffix = "-".join(w for w in words if w.isalnum())[:30]
        branch_name = f"{prefix}/{self.run_id}-{branch_suffix}"
        
        print(f"🌿 Creating branch: {branch_name}")
        self.run_git("checkout", "-b", branch_name)
        
        return branch_name
    
    async def evaluate_and_implement(self, prompt: str) -> dict:
        """
        Use Copilot SDK to evaluate the codebase and implement changes.
        
        Args:
            prompt: The improvement prompt.
            
        Returns:
            Dict with files_changed, summary, and recommendations.
        """
        print(f"\n🤖 Evaluating codebase with prompt:\n   '{prompt}'")
        
        full_prompt = f"""
You are analyzing and improving the codebase at {self.local_path}.

Task: {prompt}

Please:
1. First, analyze the codebase structure and identify areas for improvement
2. Provide specific recommendations with file paths and line numbers
3. Implement the recommended changes directly to the files
4. Ensure all changes maintain backward compatibility
5. Add or update tests if applicable
6. Update documentation if needed

After making changes, provide a summary of:
- Files modified
- Changes made
- Testing recommendations
- Any breaking changes (should be none)
"""
        
        try:
            session = await self.copilot_client.create_session({
                "working_directory": str(self.local_path),
            })
            
            response = await session.send_and_wait(
                {"prompt": full_prompt},
                timeout=self.config.copilot.timeout
            )
            
            await session.destroy()
            
            print("📝 Copilot response received")
            
            response_content = ""
            if response and hasattr(response, 'data'):
                if hasattr(response.data, 'content'):
                    response_content = response.data.content
                else:
                    response_content = str(response.data)
            elif response:
                response_content = str(response)
            
            result = self.run_git("status", "--porcelain")
            changed_files = [
                line.split()[-1] for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            
            return {
                "files_changed": changed_files,
                "summary": response_content,
                "recommendations": prompt,
            }
            
        except Exception as e:
            print(f"⚠️ Copilot evaluation failed: {e}")
            if self.config.copilot.fallback_to_cli:
                return await self._fallback_copilot_cli(prompt)
            raise
    
    async def _fallback_copilot_cli(self, prompt: str) -> dict:
        """Fallback method using Copilot CLI directly."""
        print("🔄 Using Copilot CLI fallback...")
        
        try:
            result = subprocess.run(
                [self.config.copilot.cli_command, "--non-interactive", "-m", prompt],
                cwd=self.local_path,
                capture_output=True,
                text=True,
                timeout=self.config.copilot.timeout,
            )
            
            git_result = self.run_git("status", "--porcelain")
            changed_files = [
                line.split()[-1] for line in git_result.stdout.strip().split("\n")
                if line.strip()
            ]
            
            return {
                "files_changed": changed_files,
                "summary": result.stdout,
                "recommendations": prompt,
            }
            
        except subprocess.TimeoutExpired:
            raise ReleaseFlowError(f"Copilot CLI timed out after {self.config.copilot.timeout}s")
        except FileNotFoundError:
            raise ReleaseFlowError(
                f"Copilot CLI '{self.config.copilot.cli_command}' not found. "
                "Install from: https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli"
            )
    
    def commit_changes(self, prompt: str, files_changed: list) -> bool:
        """
        Commit the changes made by Copilot.
        
        Args:
            prompt: The improvement prompt.
            files_changed: List of changed files.
            
        Returns:
            True if changes were committed, False if no changes.
        """
        if not files_changed:
            print("ℹ️ No changes to commit")
            return False
        
        print(f"📦 Committing {len(files_changed)} changed files...")
        
        self.run_git("add", "-A")
        
        prefix = self.config.git.commit_prefix
        commit_msg = f"""{prefix} {prompt[:50]}{'...' if len(prompt) > 50 else ''}

Automated improvement by Release Flow.

Files changed:
{chr(10).join(f'- {f}' for f in files_changed[:20])}
{'... and more' if len(files_changed) > 20 else ''}

Run ID: {self.run_id}
"""
        
        self.run_git("commit", "-m", commit_msg)
        print("✅ Changes committed")
        return True
    
    def push_branch(self, branch_name: str):
        """Push the branch to origin."""
        print(f"⬆️ Pushing branch {branch_name}...")
        self.run_git("push", "-u", "origin", branch_name)
        print("✅ Branch pushed")
    
    def create_pull_request(self, branch_name: str, prompt: str, summary: str) -> int:
        """
        Create a pull request on GitHub.
        
        Args:
            branch_name: The source branch.
            prompt: The improvement prompt.
            summary: Summary of changes.
            
        Returns:
            The PR number.
        """
        print("📋 Creating pull request...")
        
        prefix = self.config.pr.title_prefix
        pr_title = f"{prefix} {prompt[:60]}{'...' if len(prompt) > 60 else ''}"
        
        pr_body = f"""## Automated Improvement by Release Flow

### Prompt
> {prompt}

### Summary
{summary[:2000] if summary else 'See commits for details.'}

### Review Checklist
- [ ] Changes are appropriate and safe
- [ ] Tests pass (if applicable)
- [ ] No breaking changes introduced
- [ ] Documentation updated (if needed)

---
*This PR was automatically generated by Release Flow.*
*Run ID: {self.run_id}*
"""
        
        try:
            pr = self.gh_repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=self.config.git.main_branch,
            )
            print(f"✅ Pull request created: #{pr.number}")
            print(f"   URL: {pr.html_url}")
            
            if self.config.on_pr_created:
                self.config.on_pr_created(pr.number, pr.html_url)
            
            return pr.number
        except GithubException as e:
            raise ReleaseFlowError(f"Failed to create PR: {e}")
    
    def request_review(self, pr_number: int):
        """Request a Copilot review on the PR."""
        if not self.config.pr.auto_request_review:
            return
        
        print(f"👀 Requesting review for PR #{pr_number}...")
        pr = self.gh_repo.get_pull(pr_number)
        pr.create_issue_comment(
            "🤖 @github-copilot please review this PR for:\n"
            "- Security issues\n"
            "- Code quality\n"
            "- Potential bugs\n"
            "- Test coverage\n"
        )
        print("✅ Review requested")
    
    def wait_for_checks(self, pr_number: int) -> bool:
        """
        Wait for CI checks to complete.
        
        Args:
            pr_number: The PR number.
            
        Returns:
            True if checks passed, False otherwise.
        """
        if not self.config.pr.wait_for_ci:
            return True
        
        print(f"⏳ Waiting for CI checks on PR #{pr_number}...")
        
        pr = self.gh_repo.get_pull(pr_number)
        start_time = time.time()
        timeout = self.config.pr.ci_timeout
        
        while time.time() - start_time < timeout:
            commits = list(pr.get_commits())
            if not commits:
                time.sleep(10)
                continue
            
            last_commit = commits[-1]
            combined_status = last_commit.get_combined_status()
            
            if combined_status.state == "success":
                print("✅ All checks passed")
                return True
            elif combined_status.state == "failure":
                print("❌ Checks failed")
                return False
            elif combined_status.state == "pending":
                print(f"   Status: pending - waiting...")
                time.sleep(30)
            else:
                print("ℹ️ No CI checks configured, proceeding...")
                return True
        
        print("⚠️ Timeout waiting for checks")
        return False
    
    def merge_pull_request(self, pr_number: int, auto_merge: bool = False) -> bool:
        """
        Merge the pull request.
        
        Args:
            pr_number: The PR number.
            auto_merge: Whether to actually merge (vs just report).
            
        Returns:
            True if merged, False otherwise.
        """
        if not auto_merge:
            print(f"ℹ️ Auto-merge disabled. Please review PR #{pr_number} manually.")
            return False
        
        print(f"🔀 Merging PR #{pr_number}...")
        
        pr = self.gh_repo.get_pull(pr_number)
        
        try:
            pr.merge(
                merge_method=self.config.pr.merge_method,
                commit_message=f"🤖 Merged Release Flow improvement (Run: {self.run_id})",
            )
            print("✅ PR merged successfully")
            
            if self.config.pr.delete_branch_after_merge:
                try:
                    ref = self.gh_repo.get_git_ref(f"heads/{pr.head.ref}")
                    ref.delete()
                    print(f"🗑️ Deleted branch {pr.head.ref}")
                except:
                    pass
            
            return True
        except GithubException as e:
            print(f"⚠️ Failed to merge: {e}")
            return False
    
    def run_build(self) -> bool:
        """Run the build/test process after merge."""
        print("🔨 Running build/test...")
        
        try:
            self.ensure_clean_state()
            
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-v", "--tb=short"],
                cwd=self.local_path,
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                print("✅ Build/tests passed")
                return True
            else:
                print(f"⚠️ Tests failed:\n{result.stdout}\n{result.stderr}")
                return False
                
        except Exception as e:
            print(f"ℹ️ Build step skipped: {e}")
            return True
    
    async def run_single_iteration(
        self,
        prompt: str,
        auto_merge: bool = False,
    ) -> dict:
        """
        Run a single iteration of the release flow.
        
        Args:
            prompt: The improvement prompt.
            auto_merge: Whether to auto-merge after CI passes.
            
        Returns:
            Dict with results.
        """
        result = {
            "prompt": prompt,
            "run_id": self.run_id,
            "branch": None,
            "pr_number": None,
            "merged": False,
            "success": False,
            "error": None,
        }
        
        try:
            await self.initialize_copilot()
            self.ensure_clean_state()
            
            branch_name = self.create_branch(prompt)
            result["branch"] = branch_name
            
            changes = await self.evaluate_and_implement(prompt)
            
            if self.commit_changes(prompt, changes["files_changed"]):
                self.push_branch(branch_name)
                
                pr_number = self.create_pull_request(
                    branch_name, prompt, changes["summary"]
                )
                result["pr_number"] = pr_number
                
                self.request_review(pr_number)
                
                checks_passed = self.wait_for_checks(pr_number)
                
                if checks_passed and auto_merge:
                    result["merged"] = self.merge_pull_request(pr_number, auto_merge=True)
                    if result["merged"]:
                        self.run_build()
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Error: {e}")
            
            if self.config.on_error:
                should_continue = self.config.on_error(e)
                if not should_continue:
                    raise
        
        finally:
            await self.close_copilot()
        
        return result
    
    async def run_continuous(
        self,
        prompts: list[str] = None,
        auto_merge: bool = False,
    ) -> list[dict]:
        """
        Run the release flow continuously.
        
        Args:
            prompts: List of prompts (uses config.prompts if not provided).
            auto_merge: Whether to auto-merge PRs.
            
        Returns:
            List of result dicts for each iteration.
        """
        prompts = prompts or self.config.prompts
        max_iterations = self.config.continuous.max_iterations
        delay = self.config.continuous.delay_between_runs
        
        print("\n" + "=" * 60)
        print("🔄 STARTING CONTINUOUS RELEASE FLOW")
        print("=" * 60)
        print(f"Max iterations: {max_iterations}")
        print(f"Delay between runs: {delay}s")
        print(f"Auto-merge: {auto_merge}")
        print(f"Prompts: {len(prompts)}")
        print("=" * 60 + "\n")
        
        results = []
        
        for iteration in range(max_iterations):
            prompt = prompts[iteration % len(prompts)]
            
            print(f"\n{'=' * 60}")
            print(f"📍 ITERATION {iteration + 1}/{max_iterations}")
            print(f"{'=' * 60}\n")
            
            if self.config.on_iteration_start:
                self.config.on_iteration_start(iteration, prompt)
            
            self.run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            result = await self.run_single_iteration(
                prompt=prompt,
                auto_merge=auto_merge,
            )
            results.append(result)
            
            if self.config.on_iteration_end:
                self.config.on_iteration_end(iteration, result)
            
            if not result["success"] and self.config.continuous.stop_on_failure:
                print("⛔ Stopping due to failure")
                break
            
            if iteration < max_iterations - 1:
                print(f"\n⏰ Waiting {delay}s before next iteration...")
                await asyncio.sleep(delay)
        
        self._print_summary(results)
        return results
    
    def _print_summary(self, results: list[dict]):
        """Print a summary of all iterations."""
        print("\n" + "=" * 60)
        print("📊 RELEASE FLOW SUMMARY")
        print("=" * 60)
        
        for i, r in enumerate(results, 1):
            status = "✅" if r["success"] else "❌"
            merged = "🔀" if r["merged"] else "⏸️"
            print(f"{status} Iteration {i}: {r['prompt'][:40]}... "
                  f"PR: #{r['pr_number'] or 'N/A'} {merged}")
