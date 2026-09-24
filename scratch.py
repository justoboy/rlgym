import numpy as np
import RocketSim as rsim
from rlgym.rocket_league.sim.rocketsim_engine import RocketSimEngine
from rlgym.rocket_league.api import GameState, PhysicsObject, Car
from rlgym.rocket_league.common_values import BLUE_TEAM


def make_car(team, pos):
    car = Car()
    car.team_num = team
    car.hitbox_type = 0
    car.physics = PhysicsObject()
    car.physics.position = np.array(pos, dtype=np.float32)
    car.physics.linear_velocity = np.zeros(3, dtype=np.float32)
    car.physics.angular_velocity = np.zeros(3, dtype=np.float32)
    car.physics.rotation_mtx = np.eye(3, dtype=np.float32)
    car.boost_amount = 100.0
    car.demo_respawn_timer = 0.0
    car.wheels_with_contact = (True, True, True, True)
    car.supersonic_time = 0.0
    car.boost_active_time = 0.0
    car.handbrake = 0.0
    car.has_jumped = False
    car.is_holding_jump = False
    car.is_jumping = False
    car.jump_time = 0.0
    car.has_flipped = False
    car.has_double_jumped = False
    car.air_time_since_jump = 0.0
    car.flip_time = 0.0
    car.flip_torque = np.zeros(3, dtype=np.float32)
    car.is_autoflipping = False
    car.autoflip_timer = 0.0
    car.autoflip_direction = 0.0
    car.ball_touches = 0
    return car


def run_and_hit(mode):
    eng = RocketSimEngine(game_mode=mode)
    gs = eng.create_base_state()
    gs.ball.position = np.array([0, 0, 93.15], dtype=np.float32)
    gs.ball.linear_velocity = np.zeros(3, dtype=np.float32)
    gs.ball.angular_velocity = np.zeros(3, dtype=np.float32)
    gs.ball.rotation_mtx = np.eye(3, dtype=np.float32)
    # Car right behind the ball, moving +Y into it to force a hit
    car = make_car(BLUE_TEAM, [0, -80, 17])
    car.physics.linear_velocity = np.array([0, 2000, 0], dtype=np.float32)
    gs.cars = {"blue": car}
    gs.boost_pad_timers = np.zeros(len(eng._arena.get_boost_pads()), dtype=np.float32)
    eng.set_state(gs, {})
    out = None
    for _ in range(60):
        # throttle=1, steer=0, pitch=0,yaw=0,roll=0, jump=0, boost=1, handbrake=0
        act = np.zeros((1, 8), dtype=np.float32)
        act[0, 0] = 1.0
        act[0, 6] = 1.0
        out = eng.step({"blue": act}, {})
        if out.ball.heatseeker_target_dir != 0:
            break
    return out


print("=== HEATSEEKER: hit ball -> target_dir flips (homing LIVE) ===")
hs = run_and_hit(rsim.GameMode.HEATSEEKER)
print("  heatseeker_target_dir =", hs.ball.heatseeker_target_dir, "(expect non-zero, e.g. 1.0)")
print("  heatseeker_target_speed =", hs.ball.heatseeker_target_speed)

print("\n=== SOCCAR: hit ball -> target_dir stays 0 (no homing) ===")
sc = run_and_hit(rsim.GameMode.SOCCAR)
print("  heatseeker_target_dir =", sc.ball.heatseeker_target_dir, "(expect 0.0)")

print("\nDONE")
