#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Module - Sistema modular de bots de trading
Fornece factory pattern e classes base para diferentes tipos de bot
"""

from .base_bot import BaseBot, BotConfig, BotType, BotStatus, BotMetrics
from .bot_factory import BotFactory, BotRegistry, BotTemplate, get_bot_factory, create_bot, create_futures_bot
from .futures_bot import FuturesBot

__version__ = "2.0.0"

__all__ = [
    # Core Classes
    'BaseBot',
    'BotConfig', 
    'BotType',
    'BotStatus',
    'BotMetrics',
    
    # Factory System
    'BotFactory',
    'BotRegistry',
    'BotTemplate',
    
    # Specific Bot Types
    'FuturesBot',
    
    # Convenience Functions
    'get_bot_factory',
    'create_bot',
    'create_futures_bot'
]