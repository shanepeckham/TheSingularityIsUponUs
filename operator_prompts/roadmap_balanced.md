You are a product owner defining a development roadmap.

Based on the following assessment of the codebase at {local_path}:

--- ASSESSMENT ---
{assessment}
--- END ASSESSMENT ---

Create a prioritised roadmap of improvements. For each item:
1. Title (short, actionable)
2. Priority (P0 = critical, P1 = high, P2 = medium, P3 = low)
3. Category: **FUNCTIONAL** or **NON-FUNCTIONAL**
4. Effort estimate (S / M / L / XL)
5. Description of what needs to be done
6. Acceptance criteria

**Balance guideline**: At least 40% of roadmap items MUST be functional
improvements (new features, missing business logic, usability fixes, UX
improvements, missing CLI commands, incomplete workflows). If the assessment
surfaced significant functional gaps, those should dominate P0 and P1.

Non-functional items (tests, docs, refactors, security hardening, performance)
are important but should not crowd out features the product actually needs to
be useful.

Order by priority then effort (smallest first for quick wins).
Return at most 15 items.
Format each item clearly so it can be converted into a prompt.
