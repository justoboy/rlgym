from dataclasses import dataclass

from .utils import create_default_init


@dataclass(init=False)
class GameConfig:
    # Per-car config (CarConfig)
    dodge_deadzone: float  # TODO move to car?

    # World / global mutators
    gravity: float  # multiplier on the default downward gravity (1 = normal)
    boost_consumption: float  # multiplier on default boost usage rate (1 = normal, 0 = unlimited)

    # Car mutators
    car_mass: float  # raw mass (RL default 180)
    car_world_friction: float  # car<->world friction (RL default 0.3)
    car_world_restitution: float  # car<->world restitution (RL default 0.3)
    jump_accel: float  # raw jump hold acceleration (RL default 4375/3)
    jump_immediate_force: float  # raw jump impulse force (RL default 875/3)
    boost_accel_ground: float  # raw ground boost accel (RL default 2975/3)
    boost_accel_air: float  # raw air boost accel (RL default 3175/3)
    respawn_delay: float  # seconds to respawn after demo (RL default 3)
    bump_cooldown_time: float  # seconds of bump cooldown (RL default 0.25)
    boost_pad_cooldown_big: float  # big pad cooldown seconds (RL default 10)
    boost_pad_cooldown_small: float  # small pad cooldown seconds (RL default 4)
    unlimited_flips: bool  # allow flips without boost
    unlimited_double_jumps: bool  # allow double jumps without boost
    demo_mode: int  # DemoMode enum (0 NORMAL, 1 ON_CONTACT, 2 DISABLED)
    enable_team_demos: bool  # allow demolishing teammates

    # Ball mutators
    ball_radius: float  # raw ball radius in uu (RL default 91.25)
    ball_mass: float  # raw ball mass (RL default 30)
    ball_max_speed: float  # raw ball max speed (RL default 6000)
    ball_drag: float  # raw ball drag (RL default 0.03)
    ball_world_friction: float  # ball<->world friction (RL default 0.35)
    ball_world_restitution: float  # ball<->world restitution / bounciness (RL default 0.6)
    ball_hit_extra_force_scale: float  # scale of extra hit force (RL default 1)
    bump_force_scale: float  # scale of bump force (RL default 1)

    __slots__ = tuple(__annotations__)

    exec(create_default_init(__slots__))
