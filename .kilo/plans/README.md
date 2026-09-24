# rlgym fork — plan index

This repo (`D:/RLBotTraining/rlgym`) is the rlgym Python fork. Active plans for it:

- **T10 — Mutator Parity (this repo, Python):** widen `GameConfig` + pass every field through to
  `rsim.MutatorConfig` in `RocketSimEngine.set_state`.
  [T10 - Mutator Parity (rlgym glue).md](./T10%20-%20Mutator%20Parity%20(rlgym%20glue).md)
- **T11 — Native Game Modes (this repo, Python):** mode-aware multi-arena engine (`set_mode`),
  native goal callbacks, carry `hsInfo` through `GameState`.
  [T11 - Native Game Modes (rlgym arena routing).md](./T11%20-%20Native%20Game%20Modes%20(rlgym%20arena%20routing).md)

Serial within this repo: T10 → T11 (both edit `rocketsim_engine.py`).

Cross-repo contracts: T10's widened `GameConfig` field set = what custombot's T12 sampler writes;
T11's engine surface (`set_mode`, hsInfo fields) = what custombot `main.py`/`obs.py` consume. The
custombot master index lives at
`D:/RLBotTraining/custombot/.kilo/plans/Deferred Game-Mode Work - Remaining Tasks and Order.md`.

**Before editing this repo: read the
[Fork & Backup Protocol](D:/RLBotTraining/custombot/.kilo/plans/Fork%20&%20Backup%20Protocol.md)** —
capture `git remote -v`/`status`/`diff`, report divergence vs upstream, get the user's fork URL,
push an initial backup commit, only then edit source.
