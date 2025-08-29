#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Module
Sistema de posições com sizing e execution
"""

import logging

logger = logging.getLogger(__name__)

# Importações seguras dos submódulos
# Position sizing
BasePositionSizer = None
PositionSizingResult = None
PositionSizerFactory = None

try:
    from .sizing import BasePositionSizer, PositionSizingResult, PositionSizerFactory
    logger.debug("Position sizing components importados")
except ImportError as e:
    logger.debug(f"Position sizing não disponível: {e}")

# Position execution
OrderExecutor = None
OrderExecutionResult = None
PositionTracker = None
ExitManager = None
ExitCondition = None

try:
    from .execution import OrderExecutor, OrderExecutionResult, PositionTracker, ExitManager, ExitCondition
    logger.debug("Position execution components importados")
except ImportError as e:
    logger.debug(f"Position execution não disponível: {e}")

# Exporta apenas o que está disponível
available_exports = []

if BasePositionSizer:
    available_exports.extend(['BasePositionSizer', 'PositionSizingResult', 'PositionSizerFactory'])

if OrderExecutor:
    available_exports.extend(['OrderExecutor', 'OrderExecutionResult', 'PositionTracker', 'ExitManager', 'ExitCondition'])

__all__ = available_exports

def get_available_components():
    """Retorna status dos componentes de posição"""
    return {
        'sizing_available': BasePositionSizer is not None,
        'execution_available': OrderExecutor is not None,
        'total_components': len(available_exports)
    }