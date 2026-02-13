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

Return ONLY the prompts, one per line. No numbering, no blank lines, no commentary.
Prefix each prompt with its priority in brackets, e.g. [P0], [P1], etc.
Order from highest to lowest priority.
