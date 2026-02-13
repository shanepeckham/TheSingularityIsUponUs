"""
Operator module for the Release Flow framework.

The Operator is a second LLM that acts as a "product owner" and judge,
using a DIFFERENT model from the self-improving agent. It:
1. Assesses the codebase for functionality gaps and quality issues
2. Defines a prioritised roadmap of improvements
3. Generates actionable prompts for the self-improving agent (writes to prompts.txt)
4. Evaluates changes made by the agent after each iteration (LLM-as-judge)
5. Continuously refines the roadmap based on progress

This separation of concerns — one model proposes changes, another evaluates —
prevents self-reinforcing blind spots and improves overall quality.
"""

import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import OperatorConfig, ReleaseFlowConfig

logger = logging.getLogger(__name__)

# Lazy import for Copilot SDK
CopilotClient = None


def _ensure_copilot() -> None:
    """Ensure Copilot SDK is available."""
    global CopilotClient
    if CopilotClient is None:
        try:
            from copilot.client import CopilotClient as _CopilotClient
            CopilotClient = _CopilotClient
        except ImportError:
            logger.info("Installing github-copilot-sdk...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "github-copilot-sdk"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                from copilot.client import CopilotClient as _CopilotClient
                CopilotClient = _CopilotClient
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Failed to install github-copilot-sdk: "
                    f"{e.stderr.decode() if e.stderr else str(e)}"
                ) from e


class OperatorError(Exception):
    """Exception raised for Operator errors."""
    pass


class Operator:
    """
    LLM-as-judge / product owner for the self-improving agent.

    The Operator uses a *different* model from the one used by the
    self-improving agent (ReleaseFlow). This deliberate model separation
    ensures independent evaluation and avoids echo-chamber effects.

    Responsibilities:
        - **Assess**: Analyse the codebase and identify gaps in functionality,
          test coverage, security, documentation and architecture.
        - **Roadmap**: Produce a prioritised list of improvements.
        - **Generate prompts**: Convert the roadmap into concrete prompts
          that the self-improving agent can execute, writing them to prompts.txt.
        - **Judge**: After the agent completes an iteration, evaluate the
          quality of the changes and decide whether further work is needed.

    Example::

        from release_flow.config import ReleaseFlowConfig, OperatorConfig
        from release_flow.operator import Operator

        config = ReleaseFlowConfig(
            repo="owner/repo",
            operator=OperatorConfig(model="claude-3.5-sonnet"),
            copilot=CopilotConfig(model="gpt-4o"),
        )
        operator = Operator(config)
        assessment = await operator.assess_codebase()
        roadmap = await operator.define_roadmap(assessment)
        operator.update_prompts_file(roadmap)
    """

    # ------------------------------------------------------------------ #
    # Prompt templates used by the Operator
    # ------------------------------------------------------------------ #

    ASSESS_PROMPT = """You are an expert product owner and technical lead reviewing a codebase.
Your job is to perform a thorough assessment of the project at: {local_path}

Analyse the following dimensions and provide a structured report:

1. **Functionality gaps** — What features are missing or incomplete?
2. **Test coverage** — Which modules or functions lack adequate tests?
3. **Security** — Are there vulnerabilities or missing hardening measures?
4. **Code quality** — Identify duplication, dead code, poor abstractions.
5. **Documentation** — Missing or outdated docstrings, README gaps.
6. **Architecture** — Structural weaknesses, tight coupling, scalability concerns.
7. **Error handling** — Missing or inconsistent error handling patterns.
8. **Performance** — Potential bottlenecks or inefficiencies.

For each finding, rate severity as CRITICAL / HIGH / MEDIUM / LOW.

Return your assessment as a structured report with clear headings.
"""

    ROADMAP_PROMPT = """You are a product owner defining a development roadmap.

Based on the following assessment of the codebase at {local_path}:

--- ASSESSMENT ---
{assessment}
--- END ASSESSMENT ---

Create a prioritised roadmap of improvements. For each item:
1. Title (short, actionable)
2. Priority (P0 = critical, P1 = high, P2 = medium, P3 = low)
3. Effort estimate (S / M / L / XL)
4. Description of what needs to be done
5. Acceptance criteria

Order by priority then effort (smallest first for quick wins).
Return at most 15 items.
Format each item clearly so it can be converted into a prompt.
"""

    GENERATE_PROMPTS_PROMPT = """You are converting a roadmap into actionable prompts for a self-improving code agent.

--- ROADMAP ---
{roadmap}
--- END ROADMAP ---

For each roadmap item, write a single, self-contained prompt that instructs the
agent to implement the improvement. The prompt must:
- Be specific and actionable — tell the agent exactly what to do
- Reference file paths where relevant
- Include acceptance criteria so the agent knows when the task is done
- Be at most 500 characters

Return ONLY the prompts, one per line. No numbering, no blank lines, no commentary.
Prefix each prompt with its priority in brackets, e.g. [P0], [P1], etc.
Order from highest to lowest priority.
"""

    JUDGE_PROMPT = """You are an expert code reviewer acting as a judge for automated code changes.

The self-improving agent was given this prompt:
> {agent_prompt}

It made the following changes:
--- CHANGES ---
{changes_summary}
--- END CHANGES ---

Files changed: {files_changed}

Evaluate the changes on these criteria (score each 1-10):
1. **Correctness** — Do the changes correctly address the prompt?
2. **Completeness** — Is the task fully done, or are there gaps?
3. **Code quality** — Are the changes clean, idiomatic, well-structured?
4. **Test coverage** — Were tests added or updated appropriately?
5. **Security** — Do the changes introduce any vulnerabilities?
6. **Documentation** — Were docs updated where needed?

Provide:
- An overall PASS / FAIL / NEEDS_WORK verdict
- A brief explanation of the verdict
- Specific feedback for any score below 7
- Suggestions for follow-up work (if any)

Return your evaluation as structured text.
"""

    # ------------------------------------------------------------------ #
    # Initialisation
    # ------------------------------------------------------------------ #

    def __init__(self, config: ReleaseFlowConfig):
        """
        Initialise the Operator.

        Args:
            config: The full ReleaseFlowConfig (operator settings are in config.operator).

        Raises:
            OperatorError: If the operator model is the same as the agent model.
        """
        self.config = config
        self.operator_config: OperatorConfig = config.operator
        self.local_path = Path(config.local_path).resolve()
        self.copilot_client = None

        # Enforce model separation
        agent_model = config.copilot.model
        operator_model = self.operator_config.model
        if agent_model and operator_model and agent_model == operator_model:
            raise OperatorError(
                f"Operator model must differ from agent model. "
                f"Both are set to '{agent_model}'. "
                f"Use a different model for independent evaluation."
            )

        # Load prompt templates from files when configured
        self._load_prompt_templates()

        logger.info(
            f"Operator initialised (model: {operator_model or 'default'}, "
            f"agent model: {agent_model or 'default'})")

    # ------------------------------------------------------------------ #
    # Prompt template loading
    # ------------------------------------------------------------------ #

    _PROMPT_FILE_MAP = {
        "assess.md": "ASSESS_PROMPT",
        "roadmap.md": "ROADMAP_PROMPT",
        "generate_prompts.md": "GENERATE_PROMPTS_PROMPT",
        "judge.md": "JUDGE_PROMPT",
    }

    def _load_prompt_templates(self) -> None:
        """Load prompt templates from the configured directory.

        For each recognised file (assess.md, roadmap.md, generate_prompts.md,
        judge.md) found in ``operator_prompts_dir``, the corresponding class-
        level prompt constant is overridden on *this* instance.  Files that
        are missing are silently skipped and the built-in default is kept.
        """
        prompts_dir_setting = self.operator_config.operator_prompts_dir
        if not prompts_dir_setting:
            return

        prompts_dir = Path(prompts_dir_setting)
        if not prompts_dir.is_absolute():
            prompts_dir = self.local_path / prompts_dir
        prompts_dir = prompts_dir.resolve()

        if not prompts_dir.is_dir():
            logger.warning(
                f"Operator prompts directory not found: {prompts_dir} "
                f"— using built-in defaults"
            )
            return

        # Security: ensure the directory is within the project tree
        try:
            prompts_dir.relative_to(self.local_path)
        except ValueError:
            raise OperatorError(
                f"Operator prompts directory must be inside the project: "
                f"{prompts_dir} is outside {self.local_path}"
            )

        loaded = 0
        for filename, attr in self._PROMPT_FILE_MAP.items():
            filepath = prompts_dir / filename
            if not filepath.is_file():
                continue
            # Security: reject files > 64 KB
            if filepath.stat().st_size > 65_536:
                raise OperatorError(
                    f"Operator prompt file too large (max 64 KB): {filepath}"
                )
            content = filepath.read_text(encoding="utf-8").strip()
            if content:
                setattr(self, attr, content)
                loaded += 1
                logger.info(f"Loaded operator prompt from {filepath}")

        if loaded:
            print(f"📄 Loaded {loaded} operator prompt(s) from {prompts_dir}")
        else:
            logger.info(
                f"No prompt files found in {prompts_dir} — using built-in defaults"
            )

    # ------------------------------------------------------------------ #
    # Copilot SDK lifecycle
    # ------------------------------------------------------------------ #

    async def _init_copilot(self) -> None:
        """Initialise the Copilot client for the Operator."""
        if self.copilot_client is not None:
            return
        _ensure_copilot()
        try:
            self.copilot_client = CopilotClient()
            await self.copilot_client.start()
            logger.info("Operator Copilot client started")
        except Exception as e:
            raise OperatorError(f"Failed to start Operator Copilot client: {e}") from e

    async def _close_copilot(self) -> None:
        """Close the Copilot client."""
        if self.copilot_client:
            try:
                await self.copilot_client.stop()
                logger.info("Operator Copilot client stopped")
            except Exception as e:
                logger.error(f"Error stopping Operator Copilot client: {e}")
            finally:
                self.copilot_client = None

    async def _send_prompt(self, prompt: str) -> str:
        """
        Send a prompt to the Operator's LLM and return the response text.

        Args:
            prompt: The fully-rendered prompt to send.

        Returns:
            The LLM response as a string.
        """
        await self._init_copilot()

        session_config = {"working_directory": str(self.local_path)}
        if self.operator_config.model:
            session_config["model"] = self.operator_config.model

        try:
            session = await self.copilot_client.create_session(session_config)
            response = await session.send_and_wait(
                {"prompt": prompt},
                timeout=self.operator_config.timeout,
            )
            await session.destroy()

            if response and hasattr(response, "data"):
                if hasattr(response.data, "content"):
                    return response.data.content
                return str(response.data)
            return str(response) if response else ""

        except Exception as e:
            raise OperatorError(f"Operator LLM call failed: {e}") from e

    # ------------------------------------------------------------------ #
    # Core capabilities
    # ------------------------------------------------------------------ #

    async def assess_codebase(self) -> str:
        """
        Perform a comprehensive assessment of the codebase.

        Returns:
            A structured assessment report as a string.
        """
        model_info = f" (model: {self.operator_config.model})" if self.operator_config.model else ""
        print(f"\n🔍 Operator{model_info}: Assessing codebase...")

        prompt = self.ASSESS_PROMPT.format(local_path=self.local_path)
        assessment = await self._send_prompt(prompt)

        print("📋 Assessment complete")
        logger.info(f"Assessment length: {len(assessment)} chars")
        return assessment

    async def define_roadmap(self, assessment: str) -> str:
        """
        Define a prioritised roadmap based on an assessment.

        Args:
            assessment: The assessment report from ``assess_codebase()``.

        Returns:
            A structured roadmap as a string.
        """
        print("🗺️  Operator: Defining roadmap...")

        prompt = self.ROADMAP_PROMPT.format(
            local_path=self.local_path,
            assessment=assessment,
        )
        roadmap = await self._send_prompt(prompt)

        print("📋 Roadmap defined")
        logger.info(f"Roadmap length: {len(roadmap)} chars")
        return roadmap

    async def generate_prompts(self, roadmap: str) -> list[str]:
        """
        Convert a roadmap into actionable prompts for the self-improving agent.

        Args:
            roadmap: The roadmap from ``define_roadmap()``.

        Returns:
            A list of prompt strings, ordered by priority.
        """
        print("✍️  Operator: Generating agent prompts...")

        prompt = self.GENERATE_PROMPTS_PROMPT.format(roadmap=roadmap)
        raw = await self._send_prompt(prompt)

        # Parse: one prompt per non-empty line
        prompts = [
            line.strip()
            for line in raw.strip().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        print(f"✅ Generated {len(prompts)} prompts for the agent")
        return prompts

    async def judge_changes(
        self,
        agent_prompt: str,
        changes_summary: str,
        files_changed: list[str],
    ) -> dict:
        """
        Evaluate changes made by the self-improving agent.

        Args:
            agent_prompt: The prompt that the agent was given.
            changes_summary: The agent's summary of its changes.
            files_changed: List of file paths that were modified.

        Returns:
            A dict with keys: verdict (PASS/FAIL/NEEDS_WORK), evaluation (str),
            scores (dict), follow_up (list[str]).
        """
        model_info = f" (model: {self.operator_config.model})" if self.operator_config.model else ""
        print(f"\n⚖️  Operator{model_info}: Judging changes...")

        prompt = self.JUDGE_PROMPT.format(
            agent_prompt=agent_prompt,
            changes_summary=changes_summary or "No summary provided.",
            files_changed=", ".join(files_changed) if files_changed else "None",
        )
        evaluation = await self._send_prompt(prompt)

        # Parse verdict from response
        verdict = "NEEDS_WORK"  # conservative default
        eval_upper = evaluation.upper()
        if "VERDICT" in eval_upper:
            if "PASS" in eval_upper and "FAIL" not in eval_upper:
                verdict = "PASS"
            elif "FAIL" in eval_upper:
                verdict = "FAIL"
            elif "NEEDS_WORK" in eval_upper or "NEEDS WORK" in eval_upper:
                verdict = "NEEDS_WORK"

        # Extract any follow-up suggestions
        follow_up: list[str] = []
        for line in evaluation.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and ("follow" in evaluation.lower() or "suggest" in evaluation.lower()):
                follow_up.append(stripped.lstrip("- ").strip())

        result = {
            "verdict": verdict,
            "evaluation": evaluation,
            "follow_up": follow_up,
        }

        icon = {"PASS": "✅", "FAIL": "❌", "NEEDS_WORK": "🔧"}.get(verdict, "❓")
        print(f"{icon} Verdict: {verdict}")

        if follow_up:
            print(f"   Follow-up items: {len(follow_up)}")

        return result

    # ------------------------------------------------------------------ #
    # Prompts file management
    # ------------------------------------------------------------------ #

    def update_prompts_file(
        self,
        prompts: list[str],
        *,
        file_path: Optional[Path] = None,
        append: bool = False,
    ) -> Path:
        """
        Write prompts to the prompts file (prompts.txt by default).

        Args:
            prompts: List of prompt strings to write.
            file_path: Override path to the prompts file.
            append: If True, append to existing file; otherwise overwrite.

        Returns:
            The path to the written file.
        """
        target = file_path or (self.local_path / "prompts.txt")
        target = target.resolve()

        header = (
            "# Release Flow Prompts — generated by Operator\n"
            f"# Generated: {datetime.now().isoformat()}\n"
            f"# Operator model: {self.operator_config.model or 'default'}\n"
            "# Each non-empty, non-comment line is a prompt for continuous mode\n"
            "#\n"
            "# META-GOAL: You are a self-improving code assistant. Your task is to\n"
            "# review the codebase and implement improvements based on the prioritised\n"
            "# roadmap defined by the Operator (product owner / judge).\n"
            "# Focus on meaningful, impactful changes.\n\n"
        )

        mode = "a" if append else "w"
        with open(target, mode, encoding="utf-8") as f:
            if not append:
                f.write(header)
            for p in prompts:
                f.write(f"{p}\n")

        action = "Appended to" if append else "Wrote"
        print(f"📝 {action} {len(prompts)} prompts → {target.name}")
        logger.info(f"{action} {len(prompts)} prompts to {target}")
        return target

    # ------------------------------------------------------------------ #
    # Full pipeline
    # ------------------------------------------------------------------ #

    async def run_full_assessment(self, *, update_prompts: bool = True) -> dict:
        """
        Run the full Operator pipeline: assess → roadmap → generate prompts.

        Args:
            update_prompts: If True, write the generated prompts to prompts.txt.

        Returns:
            Dict with assessment, roadmap, prompts, and prompts_file path.
        """
        try:
            assessment = await self.assess_codebase()
            roadmap = await self.define_roadmap(assessment)
            prompts = await self.generate_prompts(roadmap)

            prompts_file = None
            if update_prompts and prompts:
                prompts_file = self.update_prompts_file(prompts)

            return {
                "assessment": assessment,
                "roadmap": roadmap,
                "prompts": prompts,
                "prompts_file": str(prompts_file) if prompts_file else None,
            }
        finally:
            await self._close_copilot()

    async def post_iteration_review(
        self,
        iteration_result: dict,
    ) -> dict:
        """
        Review an iteration's results and optionally generate follow-up prompts.

        Called by ReleaseFlow after each iteration when the operator is enabled.

        Args:
            iteration_result: The result dict from ``ReleaseFlow.run_single_iteration()``.

        Returns:
            The judge's evaluation dict (verdict, evaluation, follow_up).
        """
        try:
            return await self.judge_changes(
                agent_prompt=iteration_result.get("prompt", ""),
                changes_summary=iteration_result.get("summary", ""),
                files_changed=iteration_result.get("files_changed", []),
            )
        finally:
            await self._close_copilot()
