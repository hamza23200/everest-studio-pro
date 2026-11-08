"""
Everest Studio Pro - Mathematical Effect Engine.
Implements procedural, wave, rain, normalized spiral, and reactive lighting algorithms.
All effects take 2D coordinates (x, y) in standard keyboard units and return RGBColor.
"""

import math
import colorsys
import random
from typing import Dict, List, Tuple
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


class EffectRenderer:
    """Calculates per-key LED colors based on active effect settings and elapsed time."""

    def __init__(self):
        # 16 column phases and randomized velocity factors for Falling Matrix Code
        self.matrix_phases: List[float] = [random.uniform(0.0, 6.0) for _ in range(16)]
        self.matrix_speeds: List[float] = [random.uniform(0.85, 1.20) for _ in range(16)]

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
                     active_rows: Dict[int, Tuple[float, float]],
                     laser_speed: float, pulse_width: float,
                     laser_decay: float, mode_type: str,
                     color_a: RGBColor, color_b: RGBColor,
                     brightness: float) -> RGBColor:
        """
        Single Color mode: Idle = Black (0,0,0), Strike = Color A.
        Dual Color mode:   Idle = Color B, Strike = Color A.
        """
        # Idle base equals color_b (base_color) so inactive keys render self.base_color, not (0, 0, 0)
        idle_base = color_b
        strike_col = color_a

        row = int(round(y))
        if row not in active_rows:
            return scale_brightness(idle_base, brightness)

        ox, t0 = active_rows[row]
        dt = now - t0
        dist = abs(x - ox)
        wave_head = laser_speed * dt
        delta = wave_head - dist
        tail_len = max(0.1, laser_speed * laser_decay)

        intensity = 0.0
        if 0.0 <= delta < tail_len:
            # Quadratic/exponential trail decay
            decay_progress = delta / tail_len
            intensity = (1.0 - decay_progress) ** 2.0
        elif -pulse_width <= delta < 0.0:
            # Soft leading crest
            intensity = 1.0 + (delta / pulse_width)

        if intensity > 0.0:
            intensity = clamp(intensity)
            color = blend_colors(idle_base, strike_col, intensity)
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
