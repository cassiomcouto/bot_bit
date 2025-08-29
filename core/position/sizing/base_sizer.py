# core/position/sizing/base_sizer.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Position Sizer - Interface para algoritmos de position sizing
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
from decimal import Decimal

class PositionSizingResult:
    """Resultado do cálculo de position sizing"""
    
    def __init__(self, size: float, method: str, details: Dict[str, Any]):
        self.size = size
        self.method = method
        self.details = details
        self.confidence = details.get('confidence', 1.0)
        self.risk_amount = details.get('risk_amount', 0.0)

class BasePositionSizer(ABC):
    """Interface base para algoritmos de position sizing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def calculate_size(self, symbol: str, price: float, balance: float, 
                      signal_confidence: float = 1.0, **kwargs) -> PositionSizingResult:
        """Calcula tamanho da posição"""
        pass
    
    def validate_size(self, size: float, min_size: float, max_size: float, 
                     step_size: float) -> float:
        """Valida e ajusta tamanho da posição"""
        # Aplica step size
        if step_size > 0:
            size = round(size / step_size) * step_size
        
        # Aplica limites
        size = max(min_size, min(size, max_size))
        
        return size


# core/position/sizing/traditional_sizer.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traditional Position Sizer - Método tradicional baseado em % do saldo
"""

from .base_sizer import BasePositionSizer, PositionSizingResult

class TraditionalPositionSizer(BasePositionSizer):
    """Position sizer tradicional baseado em percentual do saldo"""
    
    def calculate_size(self, symbol: str, price: float, balance: float, 
                      signal_confidence: float = 1.0, **kwargs) -> PositionSizingResult:
        """Calcula tamanho usando método tradicional"""
        
        # Configurações
        risk_per_trade_pct = kwargs.get('risk_per_trade_pct', 2.0)
        leverage = kwargs.get('leverage', 2)
        
        # Cálculo básico
        risk_amount = balance * (risk_per_trade_pct / 100)
        position_value = risk_amount * leverage
        base_size = position_value / price
        
        # Ajuste por confiança (opcional)
        confidence_multiplier = 0.5 + (signal_confidence * 0.5)  # 0.5 a 1.0
        adjusted_size = base_size * confidence_multiplier
        
        details = {
            'method': 'traditional',
            'balance': balance,
            'risk_per_trade_pct': risk_per_trade_pct,
            'risk_amount': risk_amount,
            'leverage': leverage,
            'position_value': position_value,
            'base_size': base_size,
            'confidence_multiplier': confidence_multiplier,
            'confidence': signal_confidence
        }
        
        return PositionSizingResult(adjusted_size, 'traditional', details)


# core/position/sizing/volatility_sizer.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Volatility-Adjusted Position Sizer - Baseado no sistema atual
"""

import logging
from .base_sizer import BasePositionSizer, PositionSizingResult
from .traditional_sizer import TraditionalPositionSizer

logger = logging.getLogger(__name__)

class VolatilityPositionSizer(BasePositionSizer):
    """Position sizer ajustado por volatilidade (migrado do arquivo atual)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.traditional_sizer = TraditionalPositionSizer(config)
        
        # Configurações específicas de volatilidade
        self.target_vol = self._get_config('position_sizing.target_volatility_pct', 2.0)
        self.vol_adjustment_factor = self._get_config('position_sizing.vol_adjustment_factor', 0.5)
        self.min_multiplier = self._get_config('position_sizing.min_size_multiplier', 0.3)
        self.max_multiplier = self._get_config('position_sizing.max_size_multiplier', 2.5)
        
    def _get_config(self, path: str, default=None):
        """Helper para configuração"""
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def calculate_size(self, symbol: str, price: float, balance: float, 
                      signal_confidence: float = 1.0, **kwargs) -> PositionSizingResult:
        """Calcula tamanho ajustado por volatilidade"""
        
        # Começa com cálculo tradicional
        traditional_result = self.traditional_sizer.calculate_size(
            symbol, price, balance, signal_confidence, **kwargs
        )
        base_size = traditional_result.size
        
        # Análise de volatilidade
        volatility_analysis = self._analyze_volatility(symbol)
        
        # Multiplicadores
        vol_multiplier = self._calculate_volatility_multiplier(volatility_analysis)
        kelly_multiplier = self._calculate_kelly_multiplier(kwargs.get('trade_history', []))
        confidence_multiplier = self._calculate_confidence_multiplier(signal_confidence)
        
        # Multiplicador total
        total_multiplier = vol_multiplier * kelly_multiplier * confidence_multiplier
        total_multiplier = max(self.min_multiplier, min(self.max_multiplier, total_multiplier))
        
        # Tamanho final
        adjusted_size = base_size * total_multiplier
        
        # Detalhes combinados
        details = traditional_result.details.copy()
        details.update({
            'volatility_analysis': volatility_analysis,
            'vol_multiplier': vol_multiplier,
            'kelly_multiplier': kelly_multiplier,
            'confidence_multiplier': confidence_multiplier,
            'total_multiplier': total_multiplier,
            'base_size': base_size,
            'method': 'volatility_adjusted'
        })
        
        return PositionSizingResult(adjusted_size, 'volatility_adjusted', details)
    
    def _analyze_volatility(self, symbol: str) -> Dict[str, Any]:
        """Análise básica de volatilidade - pode ser expandida"""
        # Implementação simplificada - em produção conectaria com dados reais
        return {
            'current_vol': 2.5,
            'regime': 'normal',
            'vol_percentile': 0.5
        }
    
    def _calculate_volatility_multiplier(self, vol_analysis: Dict) -> float:
        """Calcula multiplicador de volatilidade"""
        current_vol = vol_analysis.get('current_vol', self.target_vol)
        
        if current_vol > 0:
            vol_multiplier = self.target_vol / current_vol
        else:
            vol_multiplier = 1.0
        
        return max(0.3, min(2.5, vol_multiplier))
    
    def _calculate_kelly_multiplier(self, trade_history: list) -> float:
        """Kelly criterion básico"""
        if len(trade_history) < 10:
            return 1.0
        
        # Implementação simplificada
        wins = [t for t in trade_history if t.get('pnl', 0) > 0]
        if not wins:
            return 0.5
        
        win_rate = len(wins) / len(trade_history)
        return max(0.1, min(2.0, win_rate * 1.5))
    
    def _calculate_confidence_multiplier(self, confidence: float) -> float:
        """Multiplicador baseado na confiança do sinal"""
        return max(0.5, min(1.3, 0.7 + confidence * 0.6))


# core/position/sizing/kelly_sizer.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kelly Criterion Position Sizer - Implementação pura do Kelly Criterion
"""

import numpy as np
from .base_sizer import BasePositionSizer, PositionSizingResult

class KellyPositionSizer(BasePositionSizer):
    """Position sizer baseado no Kelly Criterion"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_trades = config.get('kelly.min_trades', 20)
        self.kelly_fraction = config.get('kelly.fraction', 0.25)  # 25% do Kelly ótimo
        
    def calculate_size(self, symbol: str, price: float, balance: float, 
                      signal_confidence: float = 1.0, **kwargs) -> PositionSizingResult:
        """Calcula tamanho usando Kelly Criterion"""
        
        trade_history = kwargs.get('trade_history', [])
        
        if len(trade_history) < self.min_trades:
            # Fallback para método conservador
            conservative_size = balance * 0.01 / price  # 1% do saldo
            return PositionSizingResult(
                conservative_size, 
                'kelly_fallback',
                {'reason': 'insufficient_trades', 'trades_count': len(trade_history)}
            )
        
        # Calcula Kelly
        kelly_fraction = self._calculate_kelly_fraction(trade_history)
        
        # Aplica Kelly fracionário
        optimal_fraction = kelly_fraction * self.kelly_fraction
        position_size = (balance * optimal_fraction) / price
        
        # Limita para segurança
        max_position_pct = kwargs.get('max_position_pct', 10.0)
        max_size = (balance * max_position_pct / 100) / price
        position_size = min(position_size, max_size)
        
        details = {
            'kelly_fraction': kelly_fraction,
            'fractional_kelly': self.kelly_fraction,
            'optimal_fraction': optimal_fraction,
            'trades_analyzed': len(trade_history),
            'max_position_limit': max_size,
            'method': 'kelly'
        }
        
        return PositionSizingResult(position_size, 'kelly', details)
    
    def _calculate_kelly_fraction(self, trades: list) -> float:
        """Calcula fração do Kelly Criterion"""
        if not trades:
            return 0.01
        
        # Separa wins/losses
        wins = [t['pnl'] for t in trades if t.get('pnl', 0) > 0]
        losses = [abs(t['pnl']) for t in trades if t.get('pnl', 0) < 0]
        
        if not wins or not losses:
            return 0.01
        
        # Parâmetros Kelly
        win_prob = len(wins) / len(trades)
        loss_prob = 1 - win_prob
        avg_win = np.mean(wins)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 0.01
        
        # Fórmula Kelly: f* = (bp - q) / b
        # onde b = avg_win/avg_loss, p = win_prob, q = loss_prob
        b = avg_win / avg_loss
        kelly_f = (b * win_prob - loss_prob) / b
        
        # Limita entre 0 e 0.5 (50% max)
        return max(0.01, min(0.5, kelly_f))


# core/position/sizing/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Sizing Module - Algoritmos de dimensionamento de posições
"""

from .base_sizer import BasePositionSizer, PositionSizingResult
from .traditional_sizer import TraditionalPositionSizer
from .volatility_sizer import VolatilityPositionSizer
from .kelly_sizer import KellyPositionSizer

# Factory para diferentes estratégias
class PositionSizerFactory:
    """Factory para criar position sizers"""
    
    _sizers = {
        'traditional': TraditionalPositionSizer,
        'volatility': VolatilityPositionSizer,
        'kelly': KellyPositionSizer
    }
    
    @classmethod
    def create(cls, sizer_type: str, config: dict) -> BasePositionSizer:
        """Cria position sizer do tipo especificado"""
        if sizer_type not in cls._sizers:
            raise ValueError(f"Position sizer '{sizer_type}' não suportado. Opções: {list(cls._sizers.keys())}")
        
        return cls._sizers[sizer_type](config)
    
    @classmethod
    def get_available_sizers(cls) -> list:
        """Retorna lista de sizers disponíveis"""
        return list(cls._sizers.keys())

__all__ = [
    'BasePositionSizer',
    'PositionSizingResult', 
    'TraditionalPositionSizer',
    'VolatilityPositionSizer',
    'KellyPositionSizer',
    'PositionSizerFactory'
]