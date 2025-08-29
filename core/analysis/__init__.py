#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analysis Module - Componentes de análise de mercado
"""

import logging

logger = logging.getLogger(__name__)

# Importações seguras
AnalysisManager = None

try:
    from .managers import AnalysisManager
    logger.debug("AnalysisManager importado")
except ImportError as e:
    logger.debug(f"AnalysisManager não disponível: {e}")

# Exporta apenas o que está disponível
available_exports = []

if AnalysisManager:
    available_exports.append('AnalysisManager')

__all__ = available_exports

def get_available_components():
    """Retorna componentes disponíveis"""
    return {
        'analysis_manager': AnalysisManager is not None,
        'total_available': len(available_exports)
    }