#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Execution Module
Componentes de execução de ordens e tracking de posições
"""

import logging

logger = logging.getLogger(__name__)

# Importações seguras dos componentes
OrderExecutor = None
OrderExecutionResult = None
PositionTracker = None
ExitManager = None
ExitCondition = None

try:
    from .order_executor import OrderExecutor, OrderExecutionResult
    logger.debug("OrderExecutor importado")
except ImportError as e:
    logger.debug(f"OrderExecutor não disponível: {e}")

try:
    from .position_tracker import PositionTracker
    logger.debug("PositionTracker importado")
except ImportError as e:
    logger.debug(f"PositionTracker não disponível: {e}")

try:
    from .exit_manager import ExitManager, ExitCondition
    logger.debug("ExitManager importado")
except ImportError as e:
    logger.debug(f"ExitManager não disponível: {e}")

# Exporta apenas o que está disponível
available_exports = []

if OrderExecutor:
    available_exports.extend(['OrderExecutor', 'OrderExecutionResult'])
if PositionTracker:
    available_exports.append('PositionTracker')
if ExitManager:
    available_exports.extend(['ExitManager', 'ExitCondition'])

__all__ = available_exports

def get_available_components():
    """Retorna componentes disponíveis"""
    return {
        'order_executor': OrderExecutor is not None,
        'position_tracker': PositionTracker is not None,
        'exit_manager': ExitManager is not None,
        'total_available': len(available_exports)
    }