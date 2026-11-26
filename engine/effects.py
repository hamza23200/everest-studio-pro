"""
Everest Studio Pro - Mathematical Effect Engine.
Implements procedural, wave, rain, normalized spiral, and reactive lighting algorithms.
All effects take 2D coordinates (x, y) in standard keyboard units and return RGBColor.
"""

import math
import colorsys
import random
from typing import Any, Dict, List, Optional, Tuple
from openrgb.utils import RGBColor


def clamp(val: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    return max(min_val, min(max_val, val))


def hsv_to_rgb(h: float, s: float, v: float) -> RGBColor:
    """Converts normalized HSV (0..1) to OpenRGB RGBColor."""
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, clamp(s), clamp(v))
    return RGBColor(int(r * 255), int(g * 255), int(b * 255))


def blend_colors(c1: RGBColor, c2: RGBColor, t: float) -> RGBColor:
    """Linearly blends between c1 (t=0) and c2 (t=1)."""
    factor = clamp(t)
    r = int(c1.red + (c2.red - c1.red) * factor)
    g = int(c1.green + (c2.green - c1.green) * factor)
    b = int(c1.blue + (c2.blue - c1.blue) * factor)
    return RGBColor(r, g, b)


def scale_brightness(c: RGBColor, brightness: float) -> RGBColor:
    """Scales an RGBColor by a brightness factor (0.0 to 1.0)."""
    b = clamp(brightness)
    return RGBColor(int(c.red * b), int(c.green * b), int(c.blue * b))


def _calc_laser_wave_intensity(
    x: float,
    y: float,
    now: float,
    laser_y: float,
    origin_x: float,
    t0: float,
    laser_speed: float,
    laser_decay: float,
    pulse_width: float,
) -> float:
    """Calculates intensity for a single laser wave with strict Y-axis row lock."""
    if abs(y - laser_y) > 0.15:
        return 0.0

    dt = now - t0
    if dt < 0.0:
        return 0.0

    dist = abs(x - origin_x)
    wave_head = laser_speed * dt
    delta = wave_head - dist
    tail_len = max(0.1, laser_speed * laser_decay)

    if 0.0 <= delta < tail_len:
        decay_progress = delta / tail_len
        return (1.0 - decay_progress) ** 2.0
    if -pulse_width <= delta < 0.0:
        return 1.0 + (delta / pulse_width)
    return 0.0


def calculate_crosshair_intensity(
    x: float,
    y: float,
    now: float,
    active_crosshairs: List[Dict[str, float]],
    speed: float,
    decay: float,
) -> float:
    """Calculates horizontal + vertical crosshair beam intensity from keystrokes."""
    if not active_crosshairs:
        return 0.0
    safe_speed = max(5.0, float(speed))
    safe_decay = max(0.05, float(decay))
    max_val = 0.0
    for ch in active_crosshairs:
        ox, oy, t0 = ch["x"], ch["y"], ch["t0"]
        on_row = abs(y - oy) <= 0.15
        on_col = abs(x - ox) <= 0.65
        if not (on_row or on_col):
            continue
        dist = 0.0 if (on_row and on_col) else (abs(x - ox) if on_row else abs(y - oy))
        dt = (now - t0) - (dist / safe_speed)
        if 0.0 <= dt < safe_decay:
            val = (1.0 - (dt / safe_decay)) ** 1.6
            if val > max_val:
                max_val = val
    return clamp(max_val)


def calculate_explosion_color(
    x: float,
    y: float,
    now: float,
    active_explosions: List[Dict[str, Any]],
    speed: float,
    decay: float,
    idle_base: RGBColor,
    strike_color: RGBColor,
    react_factor: float,
) -> Tuple[RGBColor, float]:
    """Calculates high-energy radial blast, white hot core, and ember sparks."""
    if not active_explosions:
        return idle_base, 0.0
    safe_speed = max(4.0, float(speed))
    safe_decay = max(0.08, float(decay))
    max_wave = 0.0
    max_core = 0.0
    max_ember = 0.0
    coord_hash_base = int(round(x * 7.0 + y * 13.0)) * 2654435761

    for exp in active_explosions:
        dt = now - exp["t0"]
        if dt < 0.0 or dt >= safe_decay:
            continue
        dist = math.hypot(x - exp["x"], y - exp["y"])
        if dt < 0.08 and dist < 1.8:
            c_val = (1.0 - (dt / 0.08)) * (1.0 - (dist / 1.8))
            if c_val > max_core:
                max_core = c_val

        wave_r = safe_speed * dt
        ring_w = 1.1
        delta = abs(dist - wave_r)
        if delta < ring_w:
            w_val = ((1.0 - (delta / ring_w)) ** 1.4) * (1.0 - (dt / safe_decay))
            if w_val > max_wave:
                max_wave = w_val

        if dist < 4.5 and dt > 0.04:
            h = ((coord_hash_base ^ int(exp["seed"])) & 0xFF) / 255.0
            if h > 0.62:
                flicker = 0.65 + 0.35 * math.sin(now * 28.0 + h * 10.0)
                e_val = ((h - 0.62) / 0.38) * (1.0 - (dt / safe_decay)) * (1.0 - (dist / 4.5)) * flicker
                if e_val > max_ember:
                    max_ember = e_val

    wave_peak = clamp(max(max_wave, max_ember))
    core_peak = clamp(max_core)
    r = min(255, int(idle_base.red + strike_color.red * react_factor * wave_peak + 255.0 * react_factor * core_peak))
    g = min(255, int(idle_base.green + strike_color.green * react_factor * wave_peak + 255.0 * react_factor * core_peak))
    b = min(255, int(idle_base.blue + strike_color.blue * react_factor * wave_peak + 255.0 * react_factor * core_peak))
    return RGBColor(r, g, b), max(wave_peak, core_peak)


def heatmap_color(heat: float, base_factor: float, react_factor: float) -> RGBColor:
    """Maps normalized heat (0..1) across a thermal gradient (cold blue -> cyan -> yellow -> red -> white)."""
    h = clamp(heat)
    c_cold = RGBColor(10, 24, 72)
    c_cyan = RGBColor(0, 215, 230)
    c_warm = RGBColor(255, 190, 0)
    c_hot = RGBColor(255, 40, 20)
    c_white = RGBColor(255, 245, 230)

    if h < 0.33:
        col = blend_colors(c_cold, c_cyan, h / 0.33)
    elif h < 0.66:
        col = blend_colors(c_cyan, c_warm, (h - 0.33) / 0.33)
    elif h < 0.90:
        col = blend_colors(c_warm, c_hot, (h - 0.66) / 0.24)
    else:
        col = blend_colors(c_hot, c_white, (h - 0.90) / 0.10)

    eff_b = base_factor + (max(base_factor, react_factor) - base_factor) * h
    return scale_brightness(col, eff_b)


class EffectRenderer:
    """Calculates per-key LED colors based on active effect settings and elapsed time."""

    def __init__(self):
        # 16 column phases and randomized velocity factors for Falling Matrix Code
        self.matrix_phases: List[float] = [random.uniform(0.0, 6.0) for _ in range(16)]
        self.matrix_speeds: List[float] = [random.uniform(0.85, 1.20) for _ in range(16)]

        # Phase 1 v3.0 stateful pools (updated once per frame via step_frame)
        self._last_step_time: float = 0.0
        self.cosmic_stars: List[Dict[str, float]] = []
        self.storm_strikes: List[Dict[str, float]] = []
        self.storm_thunderclap: Optional[Dict[str, float]] = None
        self._storm_next_strike: float = 0.0
        self._storm_next_clap: float = 0.0
        self.active_glitch: Optional[Dict[str, Any]] = None
        self._next_glitch_time: float = 0.0
        self.meteors: List[Dict[str, Any]] = []

    def step_frame(
        self,
        effect_name: str,
        now: float,
        bounds: Tuple[float, float, float, float],
        params: Dict[str, Any],
    ):
        """Advances stateful particle/event pools once per rendered frame."""
        dt = clamp(now - self._last_step_time, 0.001, 0.15) if self._last_step_time > 0.0 else (1.0 / 35.0)
        self._last_step_time = now
        x_min, x_max, _, _ = bounds

        if effect_name == "cosmic_drift":
            self._step_cosmic_stars(now, x_min, x_max, float(params.get("star_density", 5.0)))
        elif effect_name == "thunderstorm":
            self._step_thunderstorm(now, x_min, x_max, float(params.get("storm_intensity", 5.0)))
        elif effect_name == "system_malfunction":
            self._step_malfunction(now, float(params.get("glitch_freq", 5.0)))
        elif effect_name == "meteor_shower":
            self._step_meteors(
                dt,
                x_min,
                x_max,
                int(params.get("meteor_count", 6)),
                float(params.get("speed", 5.0)),
                str(params.get("mode_type", "dual")),
                params.get("color_a", RGBColor(0, 212, 255)),
                params.get("color_b", RGBColor(138, 43, 226)),
            )

    def _step_cosmic_stars(self, now: float, x_min: float, x_max: float, star_density: float):
        self.cosmic_stars = [s for s in self.cosmic_stars if (now - s["t0"]) < s["life"]]
        target = 3 + int(clamp(star_density, 1.0, 10.0) * 1.5)
        while len(self.cosmic_stars) < target:
            self.cosmic_stars.append({
                "x": random.uniform(x_min, x_max),
                "y": random.uniform(0.3, 4.7),
                "t0": now + random.uniform(0.0, 0.25),
                "life": random.uniform(0.9, 2.4),
                "peak": random.uniform(0.65, 1.0),
            })

    def _step_thunderstorm(self, now: float, x_min: float, x_max: float, storm_intensity: float):
        intensity = clamp(storm_intensity, 1.0, 10.0)
        self.storm_strikes = [s for s in self.storm_strikes if (now - s["t0"]) < s["dur"]]
        if self.storm_thunderclap and (now - self.storm_thunderclap["t0"]) >= self.storm_thunderclap["dur"]:
            self.storm_thunderclap = None

        if now >= self._storm_next_strike:
            self.storm_strikes.append({
                "x": random.uniform(x_min + 0.5, x_max - 0.5),
                "y": random.uniform(0.5, 4.5),
                "t0": now,
                "dur": 0.28,
                "radius": random.uniform(1.8, 3.2),
            })
            base_gap = 1.65 - (intensity * 0.13)
            self._storm_next_strike = now + max(0.18, random.uniform(base_gap * 0.5, base_gap * 1.4))

        if now >= self._storm_next_clap:
            self.storm_thunderclap = {"t0": now, "dur": 0.42}
            clap_gap = 9.0 - (intensity * 0.65)
            self._storm_next_clap = now + max(1.8, random.uniform(clap_gap * 0.7, clap_gap * 1.3))

    def _step_malfunction(self, now: float, glitch_freq: float):
        freq = clamp(glitch_freq, 1.0, 10.0)
        if self.active_glitch and (now - self.active_glitch["t0"]) >= self.active_glitch["dur"]:
            self.active_glitch = None

        if self.active_glitch is None and now >= self._next_glitch_time:
            row_count = random.choice((1, 1, 2))
            rows = set(random.sample(range(5), row_count))
            glitch_col = random.choice((
                RGBColor(255, 30, 66),
                RGBColor(255, 255, 255),
                RGBColor(0, 240, 255),
            ))
            dur = random.uniform(0.06, 0.18)
            self.active_glitch = {
                "t0": now,
                "dur": dur,
                "rows": rows,
                "color": glitch_col,
                "jitter": random.uniform(-1.5, 1.5),
            }
            base_gap = 1.9 - (freq * 0.16)
            self._next_glitch_time = now + dur + max(0.12, random.uniform(base_gap * 0.4, base_gap * 1.3))

    def _spawn_meteor(
        self, x_min: float, x_max: float, speed: float, mode_type: str,
        color_a: RGBColor, color_b: RGBColor, initial: bool = False,
    ) -> Dict[str, Any]:
        width = max(8.0, x_max - x_min)
        from_top = random.random() < 0.7
        if from_top:
            mx = random.uniform(x_min - 2.0, x_max + 2.0)
            my = random.uniform(-0.8, 2.0) if initial else -0.8
        else:
            mx = x_min - 1.5
            my = random.uniform(0.0, 3.8)
        angle = random.uniform(0.32, 0.95)
        vel = (5.0 + clamp(speed, 1.0, 10.0) * 1.6) * random.uniform(0.85, 1.2)
        vx = math.cos(angle) * vel
        vy = math.sin(angle) * vel
        if mode_type == "rainbow":
            col = hsv_to_rgb(random.random(), 0.95, 1.0)
        else:
            col = blend_colors(color_a, color_b, random.uniform(0.0, 0.7))
        return {
            "x": mx, "y": my, "vx": vx, "vy": vy,
            "tail": random.uniform(2.5, 4.5), "color": col,
            "x_max_bound": x_max + 3.0, "width": width,
        }

    def _step_meteors(
        self, dt: float, x_min: float, x_max: float, meteor_count: int,
        speed: float, mode_type: str, color_a: RGBColor, color_b: RGBColor,
    ):
        target = max(4, min(10, int(meteor_count)))
        updated: List[Dict[str, Any]] = []
        for m in self.meteors:
            m["x"] += m["vx"] * dt
            m["y"] += m["vy"] * dt
            if m["x"] <= (x_max + 4.5) and m["y"] <= 7.5:
                updated.append(m)
        while len(updated) < target:
            updated.append(
                self._spawn_meteor(x_min, x_max, speed, mode_type, color_a, color_b, initial=(len(self.meteors) == 0))
            )
        self.meteors = updated[:target]

    # --------------------------------------------------------------------------
    # 1. STATIC & OFF
    # --------------------------------------------------------------------------
    @staticmethod
    def render_static(color: RGBColor, brightness: float) -> RGBColor:
        return scale_brightness(color, brightness)

    @staticmethod
    def render_off() -> RGBColor:
        return RGBColor(0, 0, 0)

    # --------------------------------------------------------------------------
    # 2. COLOR WAVE (Continuous 2D Directional Propagation)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_color_wave(x: float, y: float, t: float, direction: str,
                          speed: float, mode_type: str, color_a: RGBColor,
                          color_b: RGBColor, brightness: float) -> RGBColor:
        """
        Direction vectors:
          'right': (1.0, 0.0), 'left': (-1.0, 0.0), 'down': (0.0, 1.0),
          'up': (0.0, -1.0), 'diagonal': (0.707, 0.707)
        """
        dir_map = {
            "right": (1.0, 0.0),
            "left": (-1.0, 0.0),
            "down": (0.0, 1.0),
            "up": (0.0, -1.0),
            "diagonal": (0.707, 0.707)
        }
        dx, dy = dir_map.get(direction.lower(), (1.0, 0.0))

        spatial_freq = 0.125
        wave_speed = 0.25 + (speed * 0.28)

        proj = (x * dx) + (y * dy)
        phase = (proj * spatial_freq - t * wave_speed) % 1.0

        if mode_type == "rainbow":
            color = hsv_to_rgb(phase, 1.0, 1.0)
        elif mode_type == "dual":
            blend_factor = 0.5 * (1.0 + math.sin(2.0 * math.pi * phase))
            color = blend_colors(color_a, color_b, blend_factor)
        else:  # single color
            wave_val = (0.5 * (1.0 + math.sin(2.0 * math.pi * phase))) ** 1.5
            color = scale_brightness(color_a, wave_val)

        return scale_brightness(color, brightness)

    # --------------------------------------------------------------------------
    # 3. TORNADO (Normalized Aspect Ratio & Clockwise/CCW Directions)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_tornado(x: float, y: float, t: float, clockwise: bool,
                       speed: float, mode_type: str, color_a: RGBColor,
                       color_b: RGBColor, brightness: float) -> RGBColor:
        # Center of keyboard: cx = 7.25, cy = 2.0
        cx, cy = 7.25, 2.0
        # Normalize coordinates to eliminate elliptical distortion
        x_norm = (x - cx) / 7.25
        y_norm = (y - cy) / 2.0

        angle = math.atan2(y_norm, x_norm)  # -pi to +pi
        r = math.hypot(x_norm, y_norm)

        # Speed 1..10 maps to 0.25..2.5 rotations/sec
        rot_speed = 0.15 + (speed * 0.22)

        if clockwise:
            phase = ((angle / (2.0 * math.pi)) - (rot_speed * t) + (r * 0.8)) % 1.0
        else:
            phase = ((-angle / (2.0 * math.pi)) - (rot_speed * t) + (r * 0.8)) % 1.0

        if mode_type == "rainbow":
            color = hsv_to_rgb(phase, 1.0, 1.0)
        elif mode_type == "dual":
            blend = 0.5 * (1.0 + math.sin(2.0 * math.pi * phase))
            color = blend_colors(color_a, color_b, blend)
        else:
            intensity = (0.5 * (1.0 + math.sin(2.0 * math.pi * phase))) ** 1.6
            color = scale_brightness(color_a, intensity)

        return scale_brightness(color, brightness)

    # --------------------------------------------------------------------------
    # 4. BREATHING & PULSE
    # --------------------------------------------------------------------------
    @staticmethod
    def render_breathing(t: float, speed: float, mode_type: str,
                         color_a: RGBColor, color_b: RGBColor,
                         brightness: float) -> RGBColor:
        freq = 0.18 + (speed * 0.15)
        factor = 0.5 * (1.0 + math.sin(2.0 * math.pi * freq * t))
        intensity = factor ** 1.8

        if mode_type == "rainbow":
            hue = (t * 0.08) % 1.0
            color = hsv_to_rgb(hue, 1.0, intensity)
        elif mode_type == "dual":
            color = blend_colors(color_a, color_b, factor)
            color = scale_brightness(color, intensity)
        else:
            color = scale_brightness(color_a, intensity)

        return scale_brightness(color, brightness)

    # --------------------------------------------------------------------------
    # 5. SNAPPY AULA LASER (Configurable Speed & Decay)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_laser(x: float, y: float, now: float,
                     active_rows: Dict[Any, Tuple[float, ...]],
                     laser_speed: float, pulse_width: float,
                     laser_decay: float, mode_type: str,
                     color_a: RGBColor, color_b: RGBColor,
                     brightness: float) -> RGBColor:
        """
        Single Color mode: Idle = Black (0,0,0), Strike = Color A.
        Dual Color mode:   Idle = Color B, Strike = Color A.
        Enforces strict row lock: illuminated keys must reside on the exact same physical Y row.
        """
        idle_base = color_b
        strike_col = color_a

        if not active_rows:
            return scale_brightness(idle_base, brightness)

        max_intensity = 0.0
        for laser_y_key, row_data in list(active_rows.items()):
            if len(row_data) >= 3:
                ox, ly, t0 = row_data[0], row_data[1], row_data[2]
            elif len(row_data) == 2:
                ox, t0 = row_data
                try:
                    ly_val = float(laser_y_key)
                    ly = ly_val + 0.5 if abs(ly_val - round(ly_val)) < 0.01 else ly_val
                except (ValueError, TypeError):
                    continue
            else:
                continue

            intensity = _calc_laser_wave_intensity(
                x, y, now, ly, ox, t0, laser_speed, laser_decay, pulse_width
            )
            if intensity > max_intensity:
                max_intensity = intensity

        if max_intensity > 0.0:
            color = blend_colors(idle_base, strike_col, clamp(max_intensity))
        else:
            color = idle_base

        return scale_brightness(color, brightness)

    # --------------------------------------------------------------------------
    # 6. FALLING MATRIX CODE (Custom Colors & Void Background)
    # --------------------------------------------------------------------------
    def render_matrix_rain(self, x: float, y: float, t: float,
                           matrix_speed: float, mode_type: str,
                           color_a: RGBColor, color_b: RGBColor,
                           void_color: RGBColor, brightness: float) -> RGBColor:
        """
        matrix_speed: 2.0 to 15.0 rows/s
        mode_type:
          - 'matrix_classic' or 'single': Classic Neon Green (#00FF66) head + Dark Green (#003B10) tail
          - 'dual': Color A head + Color B tail + Void Black base
          - 'rainbow': Rainbow head & tail per column
        """
        col_idx = int(round(x)) % len(self.matrix_phases)
        drop_vel = max(1.0, matrix_speed) * self.matrix_speeds[col_idx]
        col_phase = self.matrix_phases[col_idx]

        # Drops fall down y in range 0..4 (wrap around 6.5 units)
        y_head = (t * drop_vel * 0.45 + col_phase) % 6.5
        delta = y_head - y

        if mode_type == "dual":
            head_col = color_a
            tail_col = color_b
            bg_col = void_color
        elif mode_type == "rainbow":
            hue = (col_idx / 15.0 + t * 0.1) % 1.0
            head_col = hsv_to_rgb(hue, 0.3, 1.0)
            tail_col = hsv_to_rgb(hue, 1.0, 0.35)
            bg_col = RGBColor(0, 0, 0)
        else:  # Classic Matrix
            head_col = RGBColor(180, 255, 200)
            tail_col = RGBColor(0, 59, 16)
            bg_col = RGBColor(0, 0, 0)

        if 0.0 <= delta <= 2.6:
            if delta < 0.4:
                # Bright spark head transitioning to upper stream
                mid_col = color_a if mode_type == "dual" else RGBColor(0, 255, 102)
                color = blend_colors(head_col, mid_col, delta / 0.4)
            else:
                mid_col = color_a if mode_type == "dual" else RGBColor(0, 255, 102)
                decay = (delta - 0.4) / 2.2
                stream_col = blend_colors(mid_col, tail_col, decay)
                color = blend_colors(stream_col, bg_col, decay ** 1.5)
        else:
            color = bg_col

        return scale_brightness(color, brightness)

    # --------------------------------------------------------------------------
    # 7. EXPANDING RIPPLE (Concentric Circular Wavefronts)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_ripple(x: float, y: float, now: float,
                      active_ripples: List[Dict[str, float]],
                      ripple_speed: float, ripple_width: float,
                      ripple_decay: float, mode_type: str,
                      color_a: RGBColor, color_b: RGBColor,
                      brightness: float) -> RGBColor:
        """
        Renders a hollow, expanding circular ring with focused origin
        and natural physical attenuation.
        """
        # Base color equals color_b (base_color) so inactive keys render self.base_color, not (0, 0, 0)
        base_color = color_b
        react_color = color_a

        safe_decay = max(0.05, ripple_decay)

        max_intensity = 0.0
        for w in active_ripples:
            dt = now - w["t0"]
            if dt >= safe_decay or dt < 0.0:
                continue

            dist = math.hypot(x - w["x"], y - w["y"])
            wave_r = ripple_speed * dt

            # 1. Dynamic ring width: starts tight at origin (0.7u) and expands to 1.3u
            ring_width = min(1.3, 0.7 + (dt * 1.2))

            # 2. Distance from the moving wave crest
            delta = abs(dist - wave_r)

            if delta < ring_width:
                # Smooth cosine bell curve across the ring (zero at inner and outer edges)
                norm = delta / ring_width
                ring_shape = 0.5 * (1.0 + math.cos(math.pi * norm))

                # Temporal linear fade
                time_fade = 1.0 - (dt / safe_decay)

                # Natural physical dissipation (energy spreads as circumference grows)
                attenuation = 1.0 / (1.0 + 0.12 * dist)

                val = ring_shape * time_fade * attenuation
                if val > max_intensity:
                    max_intensity = val

        if max_intensity > 0.0:
            final_intensity = clamp(max_intensity)
            color = blend_colors(base_color, react_color, final_intensity)
        else:
            color = base_color

        return scale_brightness(color, brightness)

    # --------------------------------------------------------------------------
    # 8. SINGLE-KEY REACTIVE (Configurable Linger / Decay)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_punch(idx: int, now: float,
                     active_punches: Dict[int, float],
                     punch_decay: float, mode_type: str,
                     color_a: RGBColor, color_b: RGBColor,
                     brightness: float) -> RGBColor:
        """
        punch_decay: 0.10 to 2.50 seconds (default 0.35s)
        Intensity: 1.0 - (dt / punch_decay)
        """
        # Idle base equals color_b (base_color) so inactive keys render self.base_color, not (0, 0, 0)
        idle_base = color_b
        strike_col = color_a

        if idx not in active_punches:
            return scale_brightness(idle_base, brightness)

        dt = now - active_punches[idx]
        safe_decay = max(0.05, punch_decay)
        if dt < safe_decay:
            intensity = clamp(1.0 - (dt / safe_decay))
            color = blend_colors(idle_base, strike_col, intensity)
        else:
            color = idle_base

        return scale_brightness(color, brightness)

    # --------------------------------------------------------------------------
    # 9. CUSTOM PER-KEY
    # --------------------------------------------------------------------------
    @staticmethod
    def render_custom_key(idx: int, custom_colors: Dict[int, RGBColor],
                          default_color: RGBColor, brightness: float) -> RGBColor:
        c = custom_colors.get(idx, default_color)
        return scale_brightness(c, brightness)

    # --------------------------------------------------------------------------
    # 10. ROW SWEEP (Serpentine Row-by-Row Horizontal Trail)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_row_sweep(
        x: float, y: float, t: float, x_min: float, x_max: float,
        sweep_speed: float, trail_len: float, mode_type: str,
        color_a: RGBColor, color_b: RGBColor, brightness: float,
    ) -> RGBColor:
        idle = RGBColor(0, 0, 0) if mode_type == "single" else color_b
        row_span = max(8.0, (x_max - x_min) + 2.0)
        head_total = (t * max(3.0, sweep_speed)) % (5.0 * row_span)
        active_row = int(head_total // row_span)
        head_x = (x_min - 0.5) + (head_total % row_span)
        key_row = max(0, min(4, int(y)))

        intensity = 0.0
        if key_row == active_row:
            dist_behind = head_x - x
            safe_trail = max(1.0, trail_len)
            if 0.0 <= dist_behind <= safe_trail:
                intensity = (1.0 - (dist_behind / safe_trail)) ** 1.5
            elif -0.8 <= dist_behind < 0.0:
                intensity = 1.0 + (dist_behind / 0.8)

        col = blend_colors(idle, color_a, clamp(intensity)) if intensity > 0.0 else idle
        return scale_brightness(col, brightness)

    # --------------------------------------------------------------------------
    # 11. WATERFALL (Continuous Downward Y-Axis Cascade with Shimmer)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_waterfall(
        x: float, y: float, t: float, speed: float, mode_type: str,
        color_a: RGBColor, color_b: RGBColor, brightness: float,
    ) -> RGBColor:
        flow_vel = 0.35 + (speed * 0.22)
        shimmer = 0.08 * math.sin(x * 0.4 + t * 1.8)
        phase = ((y * 0.20) - (t * flow_vel) + shimmer) % 1.0
        if mode_type == "rainbow":
            col = hsv_to_rgb(phase, 0.95, 1.0)
        else:
            blend_t = 0.5 * (1.0 + math.sin(2.0 * math.pi * phase))
            col = blend_colors(color_a, color_b, blend_t)
        return scale_brightness(col, brightness)

    # --------------------------------------------------------------------------
    # 12. AURORA (Northern Lights — 3 Overlapping 2D Sine Waves)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_aurora(
        x: float, y: float, t: float, speed: float, wave_scale: float, brightness: float,
    ) -> RGBColor:
        drift = (0.25 + speed * 0.14) * t
        ws = max(0.4, wave_scale)
        w1 = math.sin((x * 0.32 * ws) + drift + math.sin(y * 0.55 * ws + drift * 0.4))
        w2 = math.sin((x * 0.21 * ws - y * 0.45 * ws) - drift * 0.72)
        w3 = math.sin(((x + y) * 0.18 * ws) + drift * 0.51)
        val = (w1 * 0.45 + w2 * 0.35 + w3 * 0.20 + 1.0) * 0.5  # normalized 0..1

        # High-saturation Northern Lights palette in HSV space (no gray/white muddiness)
        # Emerald (~0.40) -> Teal (~0.52) -> Deep Blue (~0.63) -> Violet (~0.76)
        hue = 0.40 + clamp(val) * 0.36
        shimmer = clamp(0.68 + 0.32 * ((val * 2.0 - 1.0) ** 2))
        col = hsv_to_rgb(hue, 0.95, shimmer ** 1.15)
        return scale_brightness(col, brightness)

    # --------------------------------------------------------------------------
    # 13. GRADIENT BREATHING (Dual Gradient with Ocular Min Floor Curve)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_gradient_breathing(
        x: float, y: float, t: float, x_min: float, x_max: float,
        speed: float, min_floor_pct: float,
        color_a: RGBColor, color_b: RGBColor, brightness: float,
    ) -> RGBColor:
        span = max(1.0, x_max - x_min)
        grad_t = clamp(((x - x_min) / span) * 0.8 + ((y / 5.0) * 0.2))
        base_col = blend_colors(color_a, color_b, grad_t)

        freq = 0.16 + (speed * 0.14)
        raw = 0.5 * (1.0 + math.sin(2.0 * math.pi * freq * t))
        floor_val = clamp(min_floor_pct / 100.0, 0.0, 0.65)
        env = floor_val + (1.0 - floor_val) * (raw ** 1.8)
        return scale_brightness(base_col, env * brightness)

    # --------------------------------------------------------------------------
    # 14. COSMIC DRIFT (Drifting Nebula + Independent Star Twinkle Pool)
    # --------------------------------------------------------------------------
    def render_cosmic_drift(
        self, x: float, y: float, t: float, speed: float, brightness: float,
    ) -> RGBColor:
        drift = (0.18 + speed * 0.11) * t
        n1 = 0.5 * (1.0 + math.sin(x * 0.22 + y * 0.28 + drift))
        n2 = 0.5 * (1.0 + math.cos(x * 0.16 - y * 0.35 - drift * 0.65))
        neb_mix = clamp(0.55 * n1 + 0.45 * n2)

        navy = RGBColor(10, 14, 48)
        indigo = RGBColor(48, 22, 112)
        nebula = RGBColor(115, 28, 155)
        bg = blend_colors(navy, indigo, clamp(neb_mix * 1.4)) if neb_mix < 0.6 else blend_colors(indigo, nebula, (neb_mix - 0.6) / 0.4)

        star_peak = 0.0
        for s in self.cosmic_stars:
            dt = t - s["t0"]
            if dt < 0.0 or dt >= s["life"]:
                continue
            d = math.hypot(x - s["x"], y - s["y"])
            if d < 1.1:
                env = math.sin(math.pi * (dt / s["life"]))
                val = env * (1.0 - (d / 1.1)) * s["peak"]
                if val > star_peak:
                    star_peak = val

        col = blend_colors(bg, RGBColor(255, 255, 255), clamp(star_peak)) if star_peak > 0.0 else bg
        return scale_brightness(col, brightness)

    # --------------------------------------------------------------------------
    # 15. THUNDERSTORM (Stormy Base + Cluster Lightning + Full-Board Clap)
    # --------------------------------------------------------------------------
    def render_thunderstorm(self, x: float, y: float, now: float, brightness: float) -> RGBColor:
        ambient = RGBColor(7, 20, 43)
        flash = 0.0

        for s in self.storm_strikes:
            dt = now - s["t0"]
            if 0.0 <= dt < s["dur"]:
                d = math.hypot(x - s["x"], y - s["y"])
                if d < s["radius"]:
                    # Fast 2-pulse flicker envelope
                    norm_t = dt / s["dur"]
                    pulse = abs(math.sin(norm_t * 2.0 * math.pi)) * (1.0 - norm_t * 0.65)
                    val = pulse * (1.0 - (d / s["radius"])) ** 1.3
                    if val > flash:
                        flash = val

        if self.storm_thunderclap:
            cdt = now - self.storm_thunderclap["t0"]
            cdur = self.storm_thunderclap["dur"]
            if 0.0 <= cdt < cdur:
                norm_c = cdt / cdur
                clap_pulse = (abs(math.sin(norm_c * 2.5 * math.pi)) * (1.0 - norm_c)) * 0.85
                if clap_pulse > flash:
                    flash = clap_pulse

        col = blend_colors(ambient, RGBColor(220, 238, 255), clamp(flash)) if flash > 0.0 else ambient
        return scale_brightness(col, brightness)

    def get_thunderclap_edge_color(self, ex: float, ey: float, now: float, edge_factor: float) -> RGBColor:
        """Drives perimeter diffusers cleanly during thunderstorm claps & nearby strikes."""
        ambient = RGBColor(7, 20, 43)
        flash = 0.0
        if self.storm_thunderclap:
            cdt = now - self.storm_thunderclap["t0"]
            cdur = self.storm_thunderclap["dur"]
            if 0.0 <= cdt < cdur:
                norm_c = cdt / cdur
                flash = abs(math.sin(norm_c * 2.5 * math.pi)) * (1.0 - norm_c) * 0.75
        for s in self.storm_strikes:
            dt = now - s["t0"]
            if 0.0 <= dt < s["dur"]:
                d = math.hypot(ex - s["x"], ey - s["y"])
                if d < s["radius"] * 1.25:
                    norm_t = dt / s["dur"]
                    val = abs(math.sin(norm_t * 2.0 * math.pi)) * (1.0 - norm_t) * (1.0 - d / (s["radius"] * 1.25)) * 0.5
                    if val > flash:
                        flash = val
        col = blend_colors(ambient, RGBColor(220, 238, 255), clamp(flash)) if flash > 0.0 else ambient
        return scale_brightness(col, edge_factor)

    # --------------------------------------------------------------------------
    # 16. SYSTEM MALFUNCTION (Cyberpunk Idle + Row Flicker Glitches)
    # --------------------------------------------------------------------------
    def render_system_malfunction(
        self, x: float, y: float, now: float, x_min: float, x_max: float,
        color_a: RGBColor, color_b: RGBColor, brightness: float,
    ) -> RGBColor:
        span = max(1.0, x_max - x_min)
        grad_t = clamp((x - x_min) / span + 0.12 * math.sin(now * 1.4 + y))
        idle = blend_colors(color_a, color_b, grad_t)

        g = self.active_glitch
        if g and (now - g["t0"]) < g["dur"]:
            key_row = max(0, min(4, int(y)))
            if key_row in g["rows"]:
                jitter_x = x + g["jitter"]
                flicker = 1.0 if int((now - g["t0"]) * 55.0 + jitter_x) % 2 == 0 else 0.35
                col = blend_colors(idle, g["color"], flicker)
                return scale_brightness(col, brightness)

        return scale_brightness(idle, brightness)

    # --------------------------------------------------------------------------
    # 17. DNA SPIRAL (Double-Helix 180-deg Counter-Arms Around Board Midpoint)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_dna_spiral(
        x: float, y: float, t: float, cx: float, cy: float, x_half: float,
        speed: float, twist_density: float, outward: bool,
        color_a: RGBColor, color_b: RGBColor, brightness: float,
    ) -> RGBColor:
        xn = (x - cx) / max(3.5, x_half)
        yn = (y - cy) / 2.2
        r = math.hypot(xn, yn)
        theta = math.atan2(yn, xn)

        rot = (0.6 + speed * 0.45) * t
        twist = 1.5 + twist_density * 0.55
        phase = theta - rot + ((-r * twist) if outward else (r * twist))

        arm1 = max(0.0, math.cos(phase)) ** 2.2
        arm2 = max(0.0, math.cos(phase + math.pi)) ** 2.2

        r_val = min(255, int(color_a.red * arm1 + color_b.red * arm2))
        g_val = min(255, int(color_a.green * arm1 + color_b.green * arm2))
        b_val = min(255, int(color_a.blue * arm1 + color_b.blue * arm2))
        return scale_brightness(RGBColor(r_val, g_val, b_val), brightness)

    # --------------------------------------------------------------------------
    # 18. METEOR SHOWER (Independent Particle Streaks & Tails)
    # --------------------------------------------------------------------------
    def render_meteor_shower(
        self, x: float, y: float, mode_type: str, color_b: RGBColor, brightness: float,
    ) -> RGBColor:
        bg = scale_brightness(color_b, 0.15) if mode_type == "dual" else RGBColor(0, 0, 0)
        best_intensity = 0.0
        best_col = bg

        for m in self.meteors:
            vmag = math.hypot(m["vx"], m["vy"])
            if vmag < 1e-4:
                continue
            ux, uy = m["vx"] / vmag, m["vy"] / vmag
            dx, dy = x - m["x"], y - m["y"]
            along = dx * ux + dy * uy
            perp = abs(dx * (-uy) + dy * ux)
            tail = m["tail"]

            if perp > 0.85 or along > 0.7 or along < -tail:
                continue

            radial = 1.0 - (perp / 0.85)
            if along >= -0.3:
                w = radial * (1.0 - max(0.0, along) / 0.7)
                c = blend_colors(m["color"], RGBColor(255, 255, 255), 0.7)
            else:
                decay = (1.0 - (abs(along) / tail)) ** 1.7
                w = radial * decay
                c = m["color"]

            if w > best_intensity:
                best_intensity = w
                best_col = c

        final_col = blend_colors(bg, best_col, clamp(best_intensity)) if best_intensity > 0.0 else bg
        return scale_brightness(final_col, brightness)

    # --------------------------------------------------------------------------
    # 19. WASAPI AUDIO EQUALIZER (Spectrum Bars / Bass Pulse)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_audio_equalizer(
        x: float,
        y: float,
        x_min: float,
        x_max: float,
        bands: List[float],
        bass_energy: float,
        style: str,
        mode_type: str,
        color_a: RGBColor,
        color_b: RGBColor,
        base_factor: float,
        react_factor: float,
    ) -> RGBColor:
        """Maps live FFT bands across active board X-range bottom-up, or pulses with bass."""
        idle_col = scale_brightness(color_b, base_factor)
        if not bands:
            return idle_col

        if style == "bass_pulse":
            amp = clamp(bass_energy)
            if amp <= 0.0:
                return idle_col
            if mode_type == "rainbow":
                span = max(1.0, x_max - x_min)
                hue = clamp((x - x_min) / span) * 0.85
                col = hsv_to_rgb(hue, 1.0, 1.0)
                return blend_colors(idle_col, scale_brightness(col, react_factor), amp)
            peak = scale_brightness(color_a, react_factor)
            return blend_colors(idle_col, peak, amp)

        span = max(1.0, x_max - x_min)
        norm_x = clamp((x - x_min) / span)
        b_idx = min(len(bands) - 1, max(0, int(norm_x * len(bands))))
        amp = clamp(bands[b_idx])
        if amp <= 0.0:
            return idle_col

        # Bottom row is y=4.5 (row_from_bottom=0), top row is y=0.5 (row_from_bottom=4)
        row_from_bottom = clamp(4.5 - y, 0.0, 4.0)
        lit_rows = amp * 5.0
        cell_level = clamp(lit_rows - row_from_bottom, 0.0, 1.0)
        if cell_level <= 0.0:
            return idle_col

        height_t = clamp((row_from_bottom + 0.5) / 5.0)
        if mode_type == "rainbow":
            bar_col = hsv_to_rgb(0.66 * (1.0 - height_t), 1.0, 1.0)
        else:
            bar_col = blend_colors(color_b, color_a, height_t)

        peak_col = scale_brightness(bar_col, react_factor)
        return blend_colors(idle_col, peak_col, cell_level)

    # --------------------------------------------------------------------------
    # 20. REAL-TIME SCREEN AMBILIGHT (2D Screen Grid + Perimeter Edge Mapping)
    # --------------------------------------------------------------------------
    @staticmethod
    def render_screen_ambilight(
        x: float,
        y: float,
        x_min: float,
        x_max: float,
        grid: Any,
        brightness: float,
    ) -> RGBColor:
        """Maps normalized key coordinates (x, y) to the smoothed (5, 20, 3) screen grid."""
        if grid is None:
            return RGBColor(0, 0, 0)
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0
        if rows == 0 or cols == 0:
            return RGBColor(0, 0, 0)

        span = max(1.0, x_max - x_min)
        col_idx = min(cols - 1, max(0, int(round(clamp((x - x_min) / span) * (cols - 1)))))
        row_idx = min(rows - 1, max(0, int(round(clamp(y / 5.0) * (rows - 1)))))
        px = grid[row_idx][col_idx]
        col = RGBColor(int(clamp(px[0], 0.0, 255.0)), int(clamp(px[1], 0.0, 255.0)), int(clamp(px[2], 0.0, 255.0)))
        return scale_brightness(col, brightness)

    @staticmethod
    def render_screen_edge(
        ex: float,
        ey: float,
        x_min: float,
        x_max: float,
        edges: Optional[Dict[str, Any]],
        factor: float,
    ) -> RGBColor:
        """Maps a perimeter diffuser coordinate to its matching monitor border strip."""
        if not edges:
            return RGBColor(0, 0, 0)
        span = max(1.0, x_max - x_min)
        if ey < 0.2:
            strip = edges.get("top")
            pos = clamp((ex - x_min) / span)
        elif ey > 4.8:
            strip = edges.get("bottom")
            pos = clamp((ex - x_min) / span)
        elif ex < (x_min + span * 0.5):
            strip = edges.get("left")
            pos = clamp(ey / 5.0)
        else:
            strip = edges.get("right")
            pos = clamp(ey / 5.0)

        if strip is None or len(strip) == 0:
            return RGBColor(0, 0, 0)
        idx = min(len(strip) - 1, max(0, int(round(pos * (len(strip) - 1)))))
        px = strip[idx]
        col = RGBColor(int(clamp(px[0], 0.0, 255.0)), int(clamp(px[1], 0.0, 255.0)), int(clamp(px[2], 0.0, 255.0)))
        return scale_brightness(col, factor)
