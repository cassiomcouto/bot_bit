#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Module - Sistema principal do bot de trading
Importações seguras baseadas na estrutura real
"""

import logging

logger = logging.getLogger(__name__)

# === MANAGERS (SUA ESTRUTURA ATUAL) ===
BaseManager = None
ConfigurableManager = None
StatefulManager = None
PositionManager = None

try:
    from .managers.base_manager import BaseManager, ConfigurableManager, StatefulManager
    logger.debug("Base managers importados")
except ImportError as e:
    logger.debug(f"Base managers não disponíveis: {e}")

try:
    from .managers.position_manager import PositionManager
    logger.debug("PositionManager importado")
except ImportError as e:
    logger.debug(f"PositionManager não disponível: {e}")

# === BOT SYSTEM (SUA ESTRUTURA ATUAL) ===
BotFactory = None
BaseBot = None
FuturesBot = None
GridBot = None

try:
    from .bot.bot_factory import BotFactory
    logger.debug("BotFactory importado")
except ImportError as e:
    logger.debug(f"BotFactory não disponível: {e}")

try:
    from .bot.base_bot import BaseBot
    logger.debug("BaseBot importado")
except ImportError as e:
    logger.debug(f"BaseBot não disponível: {e}")

try:
    from .bot.futures_bot import FuturesBot
    logger.debug("FuturesBot importado")
except ImportError as e:
    logger.debug(f"FuturesBot não disponível: {e}")

# === ANALYSIS (SUA ESTRUTURA ATUAL) ===
AIConfigOptimizer = None
calculate_portfolio_metrics = None

try:
    from .analysis.ai_optimizer import AIConfigOptimizer
    logger.debug("AIConfigOptimizer importado")
except ImportError as e:
    logger.debug(f"AIConfigOptimizer não disponível: {e}")

try:
    from .analysis.performance.metrics_calculator import calculate_portfolio_metrics
    logger.debug("MetricsCalculator importado")
except ImportError as e:
    logger.debug(f"MetricsCalculator não disponível: {e}")

# === COMPONENTES OPCIONAIS ===
# Estes podem não existir na sua estrutura atual - importações seguras

# Position components
BasePositionSizer = None
PositionSizingResult = None
OrderExecutor = None

try:
    from .position.sizing import BasePositionSizer, PositionSizingResult
    logger.debug("Position sizing importado")
except ImportError as e:
    logger.debug(f"Position sizing não disponível: {e}")

try:
    from .position.execution import OrderExecutor
    logger.debug("Position execution importado")
except ImportError as e:
    logger.debug(f"Position execution não disponível: {e}")

# Safety systems
KillSwitch = None

try:
    from .safety import KillSwitch
    logger.debug("Safety systems importados")
except ImportError as e:
    logger.debug(f"Safety systems não disponíveis: {e}")

# Config systems
ConfigManager = None

try:
    from .config import ConfigManager
    logger.debug("Config systems importados")
except ImportError as e:
    logger.debug(f"Config systems não disponíveis: {e}")

__version__ = "2.0.0"

# === EXPORTS DINÂMICOS ===
# Só exporta o que realmente foi importado
available_exports = []

# Core managers
if BaseManager:
    available_exports.extend(['BaseManager', 'ConfigurableManager', 'StatefulManager'])
if PositionManager:
    available_exports.append('PositionManager')

# Bot system
if BotFactory:
    available_exports.append('BotFactory')
if BaseBot:
    available_exports.append('BaseBot')  
if FuturesBot:
    available_exports.append('FuturesBot')

# Analysis
if AIConfigOptimizer:
    available_exports.append('AIConfigOptimizer')
if calculate_portfolio_metrics:
    available_exports.append('calculate_portfolio_metrics')

# Optional components
if BasePositionSizer:
    available_exports.extend(['BasePositionSizer', 'PositionSizingResult'])
if OrderExecutor:
    available_exports.append('OrderExecutor')
if KillSwitch:
    available_exports.append('KillSwitch')
if ConfigManager:
    available_exports.append('ConfigManager')

__all__ = available_exports

def get_available_components():
    """Retorna status detalhado dos componentes"""
    return {
        'core_managers': {
            'BaseManager': BaseManager is not None,
            'PositionManager': PositionManager is not None
        },
        'bot_system': {
            'BotFactory': BotFactory is not None,
            'BaseBot': BaseBot is not None,
            'FuturesBot': FuturesBot is not None
        },
        'analysis': {
            'AIConfigOptimizer': AIConfigOptimizer is not None,
            'calculate_portfolio_metrics': calculate_portfolio_metrics is not None
        },
        'optional': {
            'position_components': BasePositionSizer is not None,
            'safety_systems': KillSwitch is not None,
            'config_systems': ConfigManager is not None
        },
        'total_available': len(available_exports)
    }

def print_status():
    """Imprime status dos componentes disponíveis"""
    components = get_available_components()
    
    print("=== CORE MODULE STATUS ===")
    for category, items in components.items():
        if category == 'total_available':
            continue
        
        print(f"\n{category.upper().replace('_', ' ')}:")
        for name, available in items.items():
            status = "✅" if available else "❌"
            print(f"  {status} {name}")
    
    print(f"\nTOTAL AVAILABLE: {components['total_available']}")
    if available_exports:
        print(f"EXPORTS: {', '.join(available_exports)}")
    print("==========================")

def create_bot_factory():
    """Cria bot factory se disponível"""
    if BotFactory:
        try:
            return BotFactory()
        except Exception as e:
            logger.error(f"Erro ao criar BotFactory: {e}")
            return None
    return None

# Informação de inicialização
logger.info(f"Core module loaded: {len(available_exports)} components available")