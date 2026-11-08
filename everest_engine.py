"""
Deprecated duplicate: EverestEngine is unified in engine.lighting_engine.
Redirected for clean matrix and lighting execution.
"""
from engine.lighting_engine import LightingEngineThread, LightingEngine
from engine.matrix import KeyboardMatrix, KEY_DEFINITIONS, EDGE_INDICES, SWITCH_INDICES
from engine.effects import EffectRenderer

EverestEngine = LightingEngineThread
