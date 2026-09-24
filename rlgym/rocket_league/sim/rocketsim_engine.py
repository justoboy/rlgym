import os
from typing import Any, Dict, List, Optional

import RocketSim as rsim
import numpy as np
from rlgym.api import TransitionEngine, AgentID
from rlgym.rocket_league.api import Car, GameConfig, GameState, PhysicsObject
from rlgym.rocket_league.common_values import (
    BOOST_CONSUMPTION_RATE, GRAVITY,
    DEFAULT_CAR_MASS, DEFAULT_CAR_WORLD_FRICTION, DEFAULT_CAR_WORLD_RESTITUTION,
    DEFAULT_JUMP_ACCEL, DEFAULT_JUMP_IMMEDIATE_FORCE,
    DEFAULT_BOOST_ACCEL_GROUND, DEFAULT_BOOST_ACCEL_AIR,
    DEFAULT_RESPAWN_DELAY, DEFAULT_BUMP_COOLDOWN_TIME,
    DEFAULT_BOOST_PAD_COOLDOWN_BIG, DEFAULT_BOOST_PAD_COOLDOWN_SMALL,
    DEFAULT_BALL_RADIUS, DEFAULT_BALL_MASS, DEFAULT_BALL_MAX_SPEED, DEFAULT_BALL_DRAG,
    DEFAULT_BALL_WORLD_FRICTION, DEFAULT_BALL_WORLD_RESTITUTION,
    DEFAULT_BALL_HIT_EXTRA_FORCE_SCALE, DEFAULT_BUMP_FORCE_SCALE,
    DEFAULT_UNLIMITED_FLIPS, DEFAULT_UNLIMITED_DOUBLE_JUMPS,
    DEFAULT_DEMO_MODE, DEFAULT_ENABLE_TEAM_DEMOS,
)


class RocketSimEngine(TransitionEngine[AgentID, GameState, np.ndarray]):
    """
    A headless Rocket League TransitionEngine backed by RocketSim.

    Mode-aware: one rsim.Arena is built per GameMode and cached; the active mode is
    selected via set_mode(). Native goal callbacks and native (random, mirrored)
    kickoff resets are used for every mode, so no Python kickoff fabrication is needed.
    """

    def __init__(self, rlbot_delay=True, game_mode: rsim.GameMode = rsim.GameMode.SOCCAR):
        """
        A headless Rocket League TransitionEngine backed by RocketSim.

        :param rlbot_delay: Enables RLBot-like 1 tick delay for actions.
            This forces the first action of the episode to no-op
        :param game_mode: The initial RocketSim GameMode to run
        """
        try:
            cur_dir = os.path.dirname(os.path.realpath(__file__))
            rsim.init(os.path.join(cur_dir, 'collision_meshes'))
        except Exception:
            pass
        self._rlbot_delay = rlbot_delay
        self._game_mode = game_mode
        self._arenas: Dict[rsim.GameMode, rsim.Arena] = {}
        self._state = None
        self._tick_count = None
        self._game_config = None
        self._cars: Dict[AgentID, rsim.Car] = {}
        self._agent_ids: Dict[int, AgentID] = {}
        self._hitboxes: Dict[int, int] = {}
        self._touches: Dict[int, int] = {}
        # Native goal latch (edge): set by the goal-score callback, consumed by _get_state.
        self._pending_goal_scored: bool = False
        self._pending_scoring_team: Optional[int] = None
        # Sticky guard so a goal is reported exactly once (edge) even though the core
        #  re-fires the callback every tick the ball remains inside the goal.
        self._goal_reported: bool = False
        # Build the initial mode's arena.
        self._get_or_create_arena(game_mode)

    @property
    def _arena(self) -> rsim.Arena:
        return self._arenas[self._game_mode]

    def _get_or_create_arena(self, game_mode: rsim.GameMode) -> rsim.Arena:
        arena = self._arenas.get(game_mode)
        if arena is None:
            arena = rsim.Arena(game_mode)
            arena.set_ball_touch_callback(self._ball_touch_callback)
            arena.set_goal_score_callback(self._goal_score_callback)
            self._arenas[game_mode] = arena
        return arena

    @property
    def game_mode(self) -> rsim.GameMode:
        return self._game_mode

    def set_mode(self, game_mode: rsim.GameMode) -> None:
        """
        Switch the active game mode. Builds (and caches) the arena for that mode on
        first use and routes all subsequent step/set_state/_get_state calls to it.
        """
        self._get_or_create_arena(game_mode)
        self._game_mode = game_mode

    @property
    def agents(self) -> List[AgentID]:
        return list(self._cars.keys())

    @property
    def max_num_agents(self) -> int:
        return 1337

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def config(self) -> Dict[str, Any]:
        # TODO allow hooking rsim via this config?
        return {
            'rlbot_delay': self._rlbot_delay
        }

    @config.setter
    def config(self, value: Dict[str, Any]):
        self._rlbot_delay = value.get('rlbot_delay', self._rlbot_delay)

    def step(self, actions: Dict[AgentID, np.ndarray], shared_info: Dict[str, Any]) -> GameState:
        if len(self._cars) == 0:
            steps = 1
        elif len(actions) != len(self._cars):
            raise KeyError("Expected actions for {} agents but received {}.".format(len(self._cars), len(actions)))
        else:
            action = next(iter(actions.values()))
            if len(action.shape) != 2:
                raise ValueError("Expected action of shape (N, 8) but received {}".format(action.shape))

            steps = action.shape[0]

        for step in range(steps):
            if self._rlbot_delay:
                self._arena.step(1)

            for agent_id, action in actions.items():
                controls = rsim.CarControls()
                controls.throttle = action[step, 0]
                controls.steer = action[step, 1]
                controls.pitch = action[step, 2]
                controls.yaw = action[step, 3]
                controls.roll = action[step, 4]
                controls.jump = bool(action[step, 5])
                controls.boost = bool(action[step, 6])
                controls.handbrake = bool(action[step, 7])

                self._cars[agent_id].set_controls(controls)

            if not self._rlbot_delay:
                self._arena.step(1)

            self._tick_count += 1

        return self._get_state()

    def set_state(self, desired_state: GameState, shared_info: Dict[str, Any]) -> GameState:
        self._tick_count = desired_state.tick_count

        config = desired_state.config
        mutators = rsim.MutatorConfig()
        mutators.gravity = rsim.Vec(0, 0, config.gravity * -GRAVITY)
        mutators.boost_used_per_second = config.boost_consumption * BOOST_CONSUMPTION_RATE
        mutators.car_mass = config.car_mass
        mutators.car_world_friction = config.car_world_friction
        mutators.car_world_restitution = config.car_world_restitution
        mutators.jump_accel = config.jump_accel
        mutators.jump_immediate_force = config.jump_immediate_force
        mutators.boost_accel_ground = config.boost_accel_ground
        mutators.boost_accel_air = config.boost_accel_air
        mutators.respawn_delay = config.respawn_delay
        mutators.bump_cooldown_time = config.bump_cooldown_time
        mutators.boost_pad_cooldown_big = config.boost_pad_cooldown_big
        mutators.boost_pad_cooldown_small = config.boost_pad_cooldown_small
        mutators.ball_radius = config.ball_radius
        mutators.ball_mass = config.ball_mass
        mutators.ball_max_speed = config.ball_max_speed
        mutators.ball_drag = config.ball_drag
        mutators.ball_world_friction = config.ball_world_friction
        mutators.ball_world_restitution = config.ball_world_restitution
        mutators.ball_hit_extra_force_scale = config.ball_hit_extra_force_scale
        mutators.bump_force_scale = config.bump_force_scale
        mutators.unlimited_flips = config.unlimited_flips
        mutators.unlimited_double_jumps = config.unlimited_double_jumps
        mutators.demo_mode = config.demo_mode
        mutators.enable_team_demos = config.enable_team_demos
        self._arena.set_mutator_config(mutators)
        self._game_config = desired_state.config

        ball_state = rsim.BallState()
        ball_state.pos = rsim.Vec(*desired_state.ball.position)
        ball_state.vel = rsim.Vec(*desired_state.ball.linear_velocity)
        ball_state.ang_vel = rsim.Vec(*desired_state.ball.angular_velocity)
        try:
            ball_state.rot_mat = rsim.RotMat(*desired_state.ball.rotation_mtx.transpose().flatten())
        except ValueError:
            pass
        # Carry heatseeker info through (defaults are inactive / soccar-irrelevant).
        if desired_state.ball.heatseeker_target_dir is not None:
            ball_state.heatseeker_target_dir = desired_state.ball.heatseeker_target_dir
        if desired_state.ball.heatseeker_target_speed is not None:
            ball_state.heatseeker_target_speed = desired_state.ball.heatseeker_target_speed
        if desired_state.ball.heatseeker_time_since_hit is not None:
            ball_state.heatseeker_time_since_hit = desired_state.ball.heatseeker_time_since_hit
        self._arena.ball.set_state(ball_state)

        # TODO reuse cars? We'd have to check the hitbox
        for car in self._arena.get_cars():
            self._arena.remove_car(car)
        self._cars.clear()
        self._agent_ids.clear()
        self._hitboxes.clear()
        self._touches.clear()
        # Seed the goal latch from the desired state so a restored/replayed goal is reported
        #  by the subsequent _get_state call (edge semantics preserved).
        self._pending_goal_scored = bool(desired_state.goal_scored)
        self._pending_scoring_team = desired_state.scoring_team
        # If the restored state already has a goal, treat it as already-reported so the core's
        #  per-tick re-fire doesn't double-report.
        self._goal_reported = bool(desired_state.goal_scored)

        for agent_id, desired_car in desired_state.cars.items():
            car_config = rsim.CarConfig(desired_car.hitbox_type)
            car_config.dodge_deadzone = config.dodge_deadzone
            car: rsim.Car = self._arena.add_car(desired_car.team_num, car_config)
            self._cars[agent_id] = car
            self._agent_ids[car.id] = agent_id
            self._hitboxes[car.id] = desired_car.hitbox_type
            self._touches[car.id] = 0

        # This loop looks dumb here but we need to create the cars before setting the state
        #  so we know the full AgentID->RSimID mapping
        for agent_id, desired_car in desired_state.cars.items():
            self._set_car_state(self._cars[agent_id], desired_car)

        # TODO check if the order is correct, I think mtheall's bindings handle it internally
        for idx, pad in enumerate(self._arena.get_boost_pads()):
            pad_state = rsim.BoostPadState()
            pad_state.cooldown = desired_state.boost_pad_timers[idx]
            pad.set_state(pad_state)

        return self._get_state()

    def reset_kickoff(self) -> GameState:
        """
        Reset the active arena to a native, random (but mirrored) kickoff for the active
        game mode. Replaces the old Python KickoffMutator fabrication for every mode.
        Returns the resulting GameState.
        """
        self._arena.reset_kickoff()
        self._tick_count = 0
        # A fresh kickoff means no goal is pending and the next goal should be reportable.
        self._pending_goal_scored = False
        self._pending_scoring_team = None
        self._goal_reported = False
        return self._get_state()

    def _get_state(self) -> GameState:
        gs = GameState()
        gs.tick_count = self._tick_count
        gs.config = self._game_config

        ball_state = self._arena.ball.get_state()
        gs.ball = PhysicsObject()
        gs.ball.position = ball_state.pos.as_numpy()
        gs.ball.linear_velocity = ball_state.vel.as_numpy()
        gs.ball.angular_velocity = ball_state.ang_vel.as_numpy()
        gs.ball.rotation_mtx = np.ascontiguousarray(ball_state.rot_mat.as_numpy().reshape(3, 3).transpose())
        # Carry heatseeker info (native, mode-aware; inactive for soccar).
        gs.ball.heatseeker_target_dir = ball_state.heatseeker_target_dir
        gs.ball.heatseeker_target_speed = ball_state.heatseeker_target_speed
        gs.ball.heatseeker_time_since_hit = ball_state.heatseeker_time_since_hit

        # Native goal latch (edge): consume the pending goal and clear it for the next step.
        gs.goal_scored = self._pending_goal_scored
        gs.scoring_team = self._pending_scoring_team
        self._pending_goal_scored = False
        self._pending_scoring_team = None

        gs.cars = {}
        for agent_id, rsim_car in self._cars.items():
            car_state = rsim_car.get_state()

            car = Car()
            car.team_num = rsim_car.team
            car.hitbox_type = self._hitboxes[rsim_car.id]

            car.physics = PhysicsObject()
            car.physics.position = car_state.pos.as_numpy()
            car.physics.linear_velocity = car_state.vel.as_numpy()
            car.physics.angular_velocity = car_state.ang_vel.as_numpy()
            car.physics.rotation_mtx = np.ascontiguousarray(car_state.rot_mat.as_numpy().reshape(3, 3).transpose())

            car.demo_respawn_timer = car_state.demo_respawn_timer
            car.wheels_with_contact = car_state.wheels_with_contact
            car.supersonic_time = car_state.supersonic_time
            car.boost_amount = car_state.boost
            car.boost_active_time = car_state.time_spent_boosting
            car.handbrake = car_state.handbrake_val

            car.has_jumped = car_state.has_jumped
            car.is_holding_jump = car_state.last_controls.jump
            car.is_jumping = car_state.is_jumping
            car.jump_time = car_state.jump_time

            car.has_flipped = car_state.has_flipped
            car.has_double_jumped = car_state.has_double_jumped
            car.air_time_since_jump = car_state.air_time_since_jump
            car.flip_time = car_state.flip_time
            car.flip_torque = car_state.flip_rel_torque.as_numpy()

            car.is_autoflipping = car_state.is_auto_flipping
            car.autoflip_timer = car_state.auto_flip_timer
            car.autoflip_direction = car_state.auto_flip_torque_scale

            car.bump_victim_id = self._agent_ids[car_state.car_contact_id] if car_state.car_contact_cooldown_timer > 0 else None
            car.ball_touches = self._touches[rsim_car.id]
            self._touches[rsim_car.id] = 0

            gs.cars[agent_id] = car

        # TODO check if the order is correct, I think mtheall's bindings handle it internally
        boost_pads = self._arena.get_boost_pads()
        gs.boost_pad_timers = np.empty(len(boost_pads), dtype=np.float32)
        for idx, pad in enumerate(boost_pads):
            pad_state = pad.get_state()
            gs.boost_pad_timers[idx] = pad_state.cooldown

        self._state = gs
        return gs

    def _set_car_state(self, car: rsim.Car, desired_car: Car):
        car_state = rsim.CarState()
        car_state.pos = rsim.Vec(*desired_car.physics.position)
        car_state.vel = rsim.Vec(*desired_car.physics.linear_velocity)
        car_state.ang_vel = rsim.Vec(*desired_car.physics.angular_velocity)
        car_state.rot_mat = rsim.RotMat(*desired_car.physics.rotation_mtx.transpose().flatten())

        car_state.demo_respawn_timer = desired_car.demo_respawn_timer
        car_state.is_demoed = desired_car.is_demoed
        car_state.wheels_with_contact = desired_car.wheels_with_contact
        car_state.is_on_ground = desired_car.on_ground
        car_state.supersonic_time = desired_car.supersonic_time
        car_state.boost = desired_car.boost_amount
        car_state.time_spent_boosting = desired_car.boost_active_time
        car_state.handbrake_val = desired_car.handbrake

        car_state.has_jumped = desired_car.has_jumped
        car_state.last_controls.jump = desired_car.is_holding_jump
        car_state.is_jumping = desired_car.is_jumping
        car_state.jump_time = desired_car.jump_time

        car_state.has_flipped = desired_car.has_flipped
        car_state.is_flipping = desired_car.is_flipping
        car_state.has_double_jumped = desired_car.has_double_jumped
        car_state.air_time_since_jump = desired_car.air_time_since_jump
        car_state.flip_time = desired_car.flip_time
        car_state.flip_rel_torque = rsim.Vec(*desired_car.flip_torque)

        car_state.is_auto_flipping = desired_car.is_autoflipping
        car_state.auto_flip_timer = desired_car.autoflip_timer
        car_state.auto_flip_torque_scale = desired_car.autoflip_direction

        if desired_car.bump_victim_id is not None:
            car_state.car_contact_id = self._cars[desired_car.bump_victim_id].id
            # Do we want to set the bump cooldown too?

        car.set_state(car_state)

    def _ball_touch_callback(self, arena: rsim.Arena, car: rsim.Car, data):
        self._touches[car.id] += 1

    def _goal_score_callback(self, arena: rsim.Arena, team: int, data):
        # The core re-fires this every tick the ball is inside the goal; report exactly once (edge).
        if self._goal_reported:
            return
        self._goal_reported = True
        self._pending_goal_scored = True
        self._pending_scoring_team = int(team)

    def create_base_state(self) -> GameState:
        gs = GameState()
        gs.tick_count = 0
        gs.goal_scored = False
        gs.scoring_team = None

        gs.config = GameConfig()
        gs.config.gravity = 1
        gs.config.boost_consumption = 1
        gs.config.dodge_deadzone = 0.5

        gs.config.car_mass = DEFAULT_CAR_MASS
        gs.config.car_world_friction = DEFAULT_CAR_WORLD_FRICTION
        gs.config.car_world_restitution = DEFAULT_CAR_WORLD_RESTITUTION
        gs.config.jump_accel = DEFAULT_JUMP_ACCEL
        gs.config.jump_immediate_force = DEFAULT_JUMP_IMMEDIATE_FORCE
        gs.config.boost_accel_ground = DEFAULT_BOOST_ACCEL_GROUND
        gs.config.boost_accel_air = DEFAULT_BOOST_ACCEL_AIR
        gs.config.respawn_delay = DEFAULT_RESPAWN_DELAY
        gs.config.bump_cooldown_time = DEFAULT_BUMP_COOLDOWN_TIME
        gs.config.boost_pad_cooldown_big = DEFAULT_BOOST_PAD_COOLDOWN_BIG
        gs.config.boost_pad_cooldown_small = DEFAULT_BOOST_PAD_COOLDOWN_SMALL
        gs.config.unlimited_flips = DEFAULT_UNLIMITED_FLIPS
        gs.config.unlimited_double_jumps = DEFAULT_UNLIMITED_DOUBLE_JUMPS
        gs.config.demo_mode = DEFAULT_DEMO_MODE
        gs.config.enable_team_demos = DEFAULT_ENABLE_TEAM_DEMOS

        gs.config.ball_radius = DEFAULT_BALL_RADIUS
        gs.config.ball_mass = DEFAULT_BALL_MASS
        gs.config.ball_max_speed = DEFAULT_BALL_MAX_SPEED
        gs.config.ball_drag = DEFAULT_BALL_DRAG
        gs.config.ball_world_friction = DEFAULT_BALL_WORLD_FRICTION
        gs.config.ball_world_restitution = DEFAULT_BALL_WORLD_RESTITUTION
        gs.config.ball_hit_extra_force_scale = DEFAULT_BALL_HIT_EXTRA_FORCE_SCALE
        gs.config.bump_force_scale = DEFAULT_BUMP_FORCE_SCALE

        gs.ball = PhysicsObject()
        gs.cars = {}
        gs.boost_pad_timers = np.zeros(len(self._arena.get_boost_pads()), dtype=np.float32)

        return gs

    def close(self) -> None:
        pass
