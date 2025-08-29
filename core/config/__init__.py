
# core/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Module - Sistema principal do bot de trading
Estrutura modular reorganizada para melhor manutenção
"""

# Managers
from .managers.base_manager import BaseManager, ConfigurableManager, StatefulManager
from .managers.position_manager import PositionManager

# Position Components
from .position.sizing import (
    BasePositionSizer, PositionSizingResult, PositionSizerFactory,
    TraditionalPositionSizer, VolatilityPositionSizer, KellyPositionSizer
)
from .position.execution import (
    OrderExecutor, OrderExecutionResult, PositionTracker, 
    ExitManager, ExitCondition
)

# Safety Systems
from .safety import KillSwitch, KillSwitchTrigger, CircuitBreakerManager

# Configuration
from .config import ConfigManager, HotReloadManager

# Bot Factory
from .bot.bot_factory import BotFactory

__version__ = "2.0.0"

__all__ = [
    # Core Managers
    'BaseManager',
    'ConfigurableManager', 
    'StatefulManager',
    'PositionManager',
    
    # Position Sizing
    'BasePositionSizer',
    'PositionSizingResult',
    'PositionSizerFactory',
    'TraditionalPositionSizer',
    'VolatilityPositionSizer',
    'KellyPositionSizer',
    
    # Position Execution
    'OrderExecutor',
    'OrderExecutionResult',
    'PositionTracker',
    'ExitManager',
    'ExitCondition',
    
    # Safety
    'KillSwitch',
    'KillSwitchTrigger',
    'CircuitBreakerManager',
    
    # Configuration
    'ConfigManager',
    'HotReloadManager',
    
    # Bot Creation
    'BotFactory'
]