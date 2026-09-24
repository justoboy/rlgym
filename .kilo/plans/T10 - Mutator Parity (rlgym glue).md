# T10 — Mutator Parity (rlgym Python glue): widen GameConfig + pass-through MutatorConfig

Status: NEW actionable plan. Renumbered from the old T10. **Python-only** — edits the local rlgym
fork's `rocketsim_engine.py` + `game_config.py`. NO C++ change, NO wheel rebuild. **No dependency on
T9** — this is the rlgym half of the mutator feature and can start immediately, in parallel with
T9/T12 (custombot repo). Read
[Fork & Backup Protocol](D:/RLBotTraining/custombot/.kilo/plans/Fork%20&%20Backup%20Protocol.md)
FIRST: the implementer must capture `git remote -v` / `git status` / `git diff` for the rlgym fork,
report divergence, get the user's fork URL, push an initial backup commit, THEN edit.

## Key finding (verified in the local repos)

- `rocketsim/src/Sim/MutatorConfig/MutatorConfig.h` ALREADY models nearly every mutator: `gravity`
  (Vec), `carMass`, `carWorldFriction/Restitution`, `ballMass`, `ballMaxSpeed`, `ballDrag`,
  `ballWorldFriction/Restitution` (= bounciness), `jumpAccel`, `jumpImmediateForce`,
  `boostAccelGround/Air` (= boost strength), `boostUsedPerSecond`, `respawnDelay`,
  `bumpCooldownTime`, `boostPadCooldown_Big/Small`, `ballHitExtraForceScale`, `bumpForceScale`,
  `ballRadius` (= ball size), `unlimitedFlips/unlimitedDoubleJumps`, `demoMode`, `enableTeamDemos`,
  `goalBaseThresholdY`.
- The installed wheel bindings (`RocketSim.pyi`) already expose all of these on `rsim.MutatorConfig`
  (snake_case).
- The ONLY gap: rlgym's `rocketsim_engine.py` `set_state()` maps just TWO fields (`gravity`,
  `boost_used_per_second`) from rlgym's 3-field `GameConfig`.

**Conclusion: HIGH feasibility, pure Python glue in the rlgym fork. No C++/CLion work.**

## Sub-steps

1. **rlgym: widen `GameConfig`** (`rlgym/rocket_league/api/game_config.py`): add fields mirroring
   `rsim.MutatorConfig`: `ball_radius, ball_mass, ball_max_speed, ball_drag, ball_world_friction,
   ball_world_restitution, car_world_friction, car_world_restitution, jump_accel,
   jump_immediate_force, boost_accel_ground, boost_accel_air, respawn_delay, bump_cooldown_time,
   boost_pad_cooldown_big, boost_pad_cooldown_small, ball_hit_extra_force_scale, bump_force_scale,
   unlimited_flips, unlimited_double_jumps, demo_mode, enable_team_demos` (raw values preferred,
   defaults from `common_values`).
2. **rlgym: pass-through in `RocketSimEngine.set_state`**: build `rsim.MutatorConfig()` and copy
   EVERY `GameConfig` field onto it; `create_base_state()` fills defaults from
   `rlgym.rocket_league.common_values`.
3. **custombot: sampler sets the widened config** — `ModeSamplerMutator`/`MutatorSamplerMutator`
   samples per-episode mutator combos and writes them into `state.config`; obs query scalars (T12)
   read the same holder. Enum-code → raw-value tables live in `custombot/constants.py`.
4. **replay_decoder**: decode per-match mutator values from replay JSON into the widened
   `GameConfig` (soccar replays: mostly defaults; heatseeker already = unlimited boost).
5. **Install as source of truth**: `pip install -e D:/RLBotTraining/rlgym` into custombot's `.venv`
   (replaces the site-packages copy). No wheel rebuild for T10's scalar set.

## Mapping table (conditioning scalar → MutatorConfig field)

| conditioning scalar | MutatorConfig field(s) | default (RL) |
|---|---|---|
| gravity | `gravity` (Vec z; scale × -GRAVITY) | -940.8 |
| boost (unlimited) | `boost_used_per_second = 0` | 950 |
| boost strength | `boost_accel_ground` / `boost_accel_air` (×1/1.5/2/10) | 991.2 / 900 |
| ball max speed | `ball_max_speed` | 2300 (slow/fast/super_fast tiers) |
| ball size | `ball_radius` | 91.25 (small/large/gigantic tiers) |
| ball bounciness | `ball_world_friction` / `ball_world_restitution` | 0.6 / 0.6 (tiers) |
| ball type | `ball_radius` + `ball_mass` approximates cube/puck/basketball | — |

## Risks / gotchas

- rlgym fork is currently consumed as a site-packages copy; switching to editable install must not
  break `spike_rush.py`'s `SpikeRushEngine(RocketSimEngine)` subclass (it calls `super().set_state`).
- Keep soccar default path byte-identical: defaults must equal current hardcoded behavior.

## Verification

Probe script toggles each mutator in isolation and asserts sim behavior changes (low gravity →
higher jump apex; small ball → radius; high bounciness → higher restitution bounce height; boost
strength → measured accel); `debug_mode_setters.py` extended to fabricate mutator combos;
`debug_ppo.py` green with widened config.
