# T11 — Native Game Modes (rlgym Python glue): real arenas + goal callbacks + hsInfo

Status: NEW actionable plan. Renumbered from the old T11. **Python-only** — edits the local rlgym
fork's `rocketsim_engine.py` + api types. NO C++ change, NO wheel rebuild (works on the installed
wheel). **Depends on T10** (same file, serial within the rlgym track). Read
[Fork & Backup Protocol](D:/RLBotTraining/custombot/.kilo/plans/Fork%20&%20Backup%20Protocol.md)
FIRST: capture rlgym fork `remote -v` / `status` / `diff`, report divergence, get fork URL, push
initial backup commit, THEN edit.

## Findings (verified)

1. **Heatseeker is native in the C++ core.** `Ball::_PreTickUpdate` implements the real homing ball
   (velocity-angle blend toward target net, UE3 rotator rounding, wall-bounce retarget, per-hit
   speed increment). `BallState.hsInfo` = `(yTargetDir, curTargetSpeed, timeSinceHit)` and the
   installed wheel exposes all three as `heatseeker_target_dir/speed/time_since_hit`.
   `Arena::ResetToRandomKickoff` already spawns heatseeker-legal kickoffs.
2. **Hoops/Snowday are native.** Hoops = own mesh + cylinder goal test in `Arena::IsBallScored`;
   snowday = slippery ball. Installed wheel `GameMode` enum currently exposes `SOCCAR, HOOPS,
   HEATSEEKER, SNOWDAY, THE_VOID` (DROPSHOT is native in the core but not yet bound — see T14).
3. **The core has NO ball-attach concept** (grep `attach|weld|carry` = 0 hits). Spike Rush/Gridiron
   carry is NOT native — that is a separate C++ feature in T13. Until T13 lands, spike rush stays
   the Python weld in `spike_rush.py`.
4. **rlgym glue is the bottleneck:** `RocketSimEngine.__init__` already takes `game_mode` but
   custombot never passes it → every episode runs soccar physics, homing never runs; `goal_scored`
   is hardcoded to the soccar y-plane; `GameState` can't carry `hsInfo`; one engine = one arena =
   one mode.

## Decisions

- **Python-only.** Heatseeker/hoops/snowday become REAL by building the arena with the right
  `GameMode` + native goal callbacks + native kickoff resets.
- custombot's old T1 (hoops geometry probe) and T2 (Python goal wrapper) are **retired** — the arena
  scores its own goals. T3's `goal_center/normal/radius` conditioning fields are **dropped**.
- `mode_setters.py`'s fabricated per-mode spawns are **retired** in favor of `arena.reset_kickoff`.

## Sub-steps

1. **rlgym fork — mode-aware engine.** Extend `RocketSimEngine` to build one `rsim.Arena(mode)` per
   mode in a dict and route `step`/`set_state`/`_get_state` to the arena for the active mode
   (active mode set via a `set_mode(mode)` the sampler mutator calls before each episode).
   `reset_kickoff(seed)` replaces Python kickoff fabrication for non-soccar modes; soccar keeps the
   `KickoffMutator` path byte-identical.
2. **rlgym fork — native goal plumbing.** In `_get_state`, replace the y-plane hack: register
   `set_goal_score_callback` on every arena; the callback latches a pending goal (scoring team)
   that `_get_state` writes into `gs.goal_scored` (edge, not level) and clears next step.
3. **rlgym fork — carry hsInfo.** Widen `PhysicsObject`/`GameState` with `heatseeker_target_dir`,
   `heatseeker_target_speed`, `heatseeker_time_since_hit`; copy in `_get_state`, restore in
   `set_state`. Defaults = inactive.
4. **custombot — pass the mode.** `make_env`/`SpikeRushEngine.__init__` pass `game_mode` through;
   `ModeSamplerMutator` calls `engine.set_mode(mode)` on reset. `mode_setters.py` shrinks to the
   soccar shim + sampler dispatch. `reward.py`/`scoreboard.py` read `gs.goal_scored` unchanged.
5. **custombot — obs cleanup.** Drop `goal_center/normal/radius` query slots; add the three hsInfo
   scalars to the query (signed y-dir + speed + time = 3 dims).
6. **Install:** `pip install -e D:/RLBotTraining/rlgym` (already required by T10). No wheel rebuild.
7. **Verification:** probe heatseeker (hit ball → `heatseeker_target_dir` flips, ball curves to
   net; soccar ball does NOT home); probe hoops (ball through cylinder fires callback; center
   y-plane does NOT score); probe snowday (ball slides, no rot); `debug_*` green; soccar byte-identical.

## Risks / gotchas

- `SpikeRushEngine(RocketSimEngine)` calls `super().set_state` — keep signatures stable when adding
  `set_mode`/multi-arena routing.
- Goal callback fires during `step`; latch exactly once per goal (edge).
- Multi-arena router: boost-pad arrays differ per arena (hoops fewer pads); obs pad slots come
  from the ACTIVE arena's pad count (fixed-slot zero-pad convention already handles it).
- `reset_kickoff(seed)` determinism: verify seed→spawn mapping matches replay expectations before
  deleting Python tables.

## Out of scope (→ T13)

Native ball-attach (Spike Rush weld + Gridiron roof-attach) is a C++ feature, isolated in
[T13 - Native Ball Attach (C++)](D:/RLBotTraining/rocketsim/.kilo/plans/T13%20-%20Native%20Ball%20Attach%20(C++).md).
