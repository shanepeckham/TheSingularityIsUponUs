You are converting a roadmap into actionable prompts for a self-improving code agent.

--- ROADMAP ---
{roadmap}
--- END ROADMAP ---

For each roadmap item, write a single, self-contained prompt that instructs the
agent to implement the improvement. The prompt must:
- Be specific and actionable — tell the agent exactly what to do
- Reference file paths where relevant
- Include acceptance criteria so the agent knows when the task is done
- Be at most 500 characters

**Balance rule**: The resulting prompt list MUST contain a mix of functional and
non-functional work. If the roadmap is dominated by non-functional items, convert
at least 40% of the prompts into functional improvements by:
- Adding missing features or commands
- Implementing incomplete business logic
- Improving user-facing behaviour or error messages
- Adding missing CLI options or workflow steps

Functional prompts should appear BEFORE non-functional prompts at the same
priority level.

Return ONLY the prompts, one per line. No numbering, no blank lines, no commentary.
Prefix each prompt with its priority and category in brackets,
e.g. [P0 FUNCTIONAL], [P1 NON-FUNCTIONAL], etc.
Order from highest to lowest priority, with functional items first within each tier.
