# BMW Battery Intelligence

See `BMW_Visualizer/CLAUDE.md` for the main project documentation.

## gstack
- Use the /browse skill from gstack for all web browsing
- Never use mcp__claude-in-chrome__* tools
- Available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review, /design-consultation, /review, /ship, /browse, /qa, /qa-only, /design-review, /setup-browser-cookies, /retro, /debug, /document-release
- If gstack skills aren't working, run `cd .claude/skills/gstack && ./setup` to build the binary and register skills
- **Teammates (first-time setup):** requires [bun](https://bun.sh) — install with `curl -fsSL https://bun.sh/install | bash`, restart your terminal, then run `cd .claude/skills/gstack && ./setup`
