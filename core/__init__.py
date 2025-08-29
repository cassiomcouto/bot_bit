#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Module - Sistema principal do bot de trading
VERSÃO MINIMAL - apenas o que realmente existe
"""

import logging

logger = logging.getLogger(__name__)

# === APENAS COMPONENTES QUE EXISTEM ===

# Managers (existem)
BaseManager = None
ConfigurableManager = None 
StatefulManager = None
PositionManager = None

try:
    from .managers.base_manager import BaseManager, ConfigurableManager, StatefulManager
    logger.debug("Base managers importados")
except ImportError as e:
    logger.debug(f"Base managers falhou: {e}")

try:
    from .managers.position_manager import PositionManager
    logger.debug("PositionManager importado")
except ImportError as e:
    logger.debug(f"PositionManager falhou: {e}")

# Risk Manager (mover para managers se necessário)
RiskManager = None
try:
    from .managers.risk_manager import RiskManager
    logger.debug("RiskManager importado de managers")
except ImportError:
    logger.debug("RiskManager não encontrado em managers")

# Bot Factory (existe)
BotFactory = None
try:
    from .bot.bot_factory import BotFactory
    logger.debug("BotFactory importado")
except ImportError as e:
    logger.debug(f"BotFactory falhou: {e}")

# AI Optimizer (existe)
AIConfigOptimizer = None
try:
    from .analysis.ai_optimizer import AIConfigOptimizer
    logger.debug("AIConfigOptimizer importado")
except ImportError as e:
    logger.debug(f"AIConfigOptimizer falhou: {e}")

# Metrics Calculator (pode existir)
calculate_portfolio_metrics = None
try:
    from .analysis.performance.metrics_calculator import calculate_portfolio_metrics
    logger.debug("MetricsCalculator importado")
except ImportError as e:
    logger.debug(f"MetricsCalculator falhou: {e}")

__version__ = "2.0.0"

# Exports dinâmicos - só o que foi importado com sucesso
available_exports = []

if BaseManager:
    available_exports.extend(['BaseManager', 'ConfigurableManager', 'StatefulManager'])
if PositionManager:
    available_exports.append('PositionManager')
if RiskManager:
    available_exports.append('RiskManager')
if BotFactory:
    available_exports.append('BotFactory')
if AIConfigOptimizer:
    available_exports.append('AIConfigOptimizer')
if calculate_portfolio_metrics:
    available_exports.append('calculate_portfolio_metrics')

__all__ = available_exports

def print_status():
    """Mostra status dos componentes"""
    print("=== CORE STATUS ===")
    components = {
        'BaseManager': BaseManager is not None,
        'PositionManager': PositionManager is not None,
        'RiskManager': RiskManager is not None,
        'BotFactory': BotFactory is not None,
        'AIConfigOptimizer': AIConfigOptimizer is not None,
        'calculate_portfolio_metrics': calculate_portfolio_metrics is not None
    }
    
    for name, available in components.items():
        status = "✅" if available else "❌"
        print(f"{status} {name}")
    
    print(f"Total disponíveis: {len(available_exports)}")
    print("===================")

# Log simples
logger.info(f"Core module loaded: {len(available_exports)} components available")