# Project Rules: custombot

## Scratch files (pre-authorized, no approval needed)

- `scratch.bat` is an editable shell-command wrapper the agent may invoke and EDIT
  freely: use it to run shell commands such as `git`, `dir`, `copy`, etc. by editing
  its body to the command(s) needed, then calling `scratch.bat`.
- `scratch.py` is editable workspace-local Python for running/importing project code
  and reading debug output. Run it directly with `.venv/Scripts/python.exe scratch.py`
  (auto-approved) — no wrapper needed.
- Both files are trusted scratch space: rewrite them freely per task and prefer them over inline commands to minimize user interaction.
- Within reason: do not damage the user's computer or codebase; follow professional
  LLM-agent safety guidelines (no destructive deletes, no global installs, no
  exfiltration, no rm -rf of anything outside the workspace).

## Git backups (run via scratch.bat)

- To make a git snapshot, edit `scratch.bat` to contain the git commands (e.g.
  `git add -A` + `git commit -m "Backup: <state>"`) and invoke `scratch.bat`.
- Before any major/risky code change, commit a backup snapshot.
- After completing a major change, commit again with a descriptive message.
- Never rewrite history (no reset/rebase/filter-branch); only new commits.

## Todo tracking

- Always use markdown checklists in `update_todo_list` (lines like `- [x] done` /
  `- [ ] pending`), never JSON arrays.
- Keep the checklist updated at each step; the todo list is the durable record of
  progress since chat history can be lost.

## General

- Windows + cmd.exe environment; use cmd-compatible commands.
- Prefer the `read_file` tool for reading files over shell commands.
- Project: Rocket League PPO bot (rlgym new-API + RocketSim), soccar-first, with
  replay pretraining (IDM -> BC -> RL), per-player profile tracker, snapshot opponent
  pool, and forward-state-prediction auxiliary task.
