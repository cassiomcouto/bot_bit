#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Volatility-Adjusted Position Sizing - Sistema Dinâmico de Dimensionamento
Ajusta tamanho das posições baseado em volatilidade, correlação e condições de mercado
"""

import logging
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from enum import Enum

logger = logging.getLogger(__name__)

class VolatilityRegime(Enum):
    """Regimes de volatilidade para position sizing"""
    VERY_LOW = "very_low"      # < percentil 20
    LOW = "low"                # percentil 20-40
    NORMAL = "normal"          # percentil 40-60
    HIGH = "high"              # percentil 60-80
    EXTREME = "extreme"        # > percentil 80

class VolatilityPositionSizer:
    """Sistema inteligente de dimensionamento baseado em volatilidade"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.volatility_cache = {}
        self.correlation_cache = {}
        
        # Configurações do sistema
        self.sizing_config = self._get_config('position_sizing', {})
        self.enabled = self.sizing_config.get('enabled', True)
        
        # Parâmetros de volatilidade
        self.lookback_periods = self.sizing_config.get('volatility_lookback', 30)
        self.vol_adjustment_factor = self.sizing_config.get('vol_adjustment_factor', 0.5)
        self.target_vol = self.sizing_config.get('target_volatility_pct', 2.0)
        
        # Risk budgeting
        self.max_portfolio_risk = self.sizing_config.get('max_portfolio_risk_pct', 10.0)
        self.correlation_threshold = self.sizing_config.get('correlation_threshold', 0.7)
        
        # Limites de segurança
        self.min_size_multiplier = self.sizing_config.get('min_size_multiplier', 0.3)
        self.max_size_multiplier = self.sizing_config.get('max_size_multiplier', 2.5)
        
        # Kelly Criterion
        self.use_kelly = self.sizing_config.get('use_kelly_criterion', True)
        self.kelly_lookback = self.sizing_config.get('kelly_lookback_trades', 20)
        
        logger.info(f"Volatility Position Sizer inicializado - Enabled: {self.enabled}")
        logger.info(f"Target volatility: {self.target_vol}%, Max portfolio risk: {self.max_portfolio_risk}%")
    
    def _get_config(self, path: str, default=None):
        """Obtém configuração aninhada"""
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def calculate_optimal_position_size(self, symbol: str, base_size: float, 
                                      current_price: float, signal_confidence: float,
                                      trade_history: List[Dict] = None) -> Tuple[float, Dict]:
        """
        Calcula tamanho ótimo da posição considerando volatilidade e outros fatores
        
        Args:
            symbol: Par de trading
            base_size: Tamanho base calculado pelo método tradicional
            current_price: Preço atual
            signal_confidence: Confiança do sinal (0-1)
            trade_history: Histórico de trades para Kelly Criterion
            
        Returns:
            Tuple[novo_tamanho, detalhes_calculo]
        """
        if not self.enabled:
            return base_size, {'method': 'disabled', 'multiplier': 1.0}
        
        try:
            # Calcula volatilidade atual
            vol_analysis = self._analyze_volatility(symbol)
            
            # Calcula Kelly Criterion se habilitado
            kelly_multiplier = 1.0
            if self.use_kelly and trade_history:
                kelly_multiplier = self._calculate_kelly_multiplier(trade_history)
            
            # Ajuste por volatilidade
            vol_multiplier = self._calculate_volatility_multiplier(vol_analysis)
            
            # Ajuste por confiança do sinal
            confidence_multiplier = self._calculate_confidence_multiplier(signal_confidence)
            
            # Verificação de correlação (se há outras posições)
            correlation_multiplier = self._calculate_correlation_multiplier(symbol)
            
            # Ajuste por regime de mercado (se disponível)
            regime_multiplier = self._calculate_regime_multiplier(symbol)
            
            # Multiplicador final
            total_multiplier = (vol_multiplier * 
                              kelly_multiplier * 
                              confidence_multiplier * 
                              correlation_multiplier * 
                              regime_multiplier)
            
            # Aplica limites de segurança
            total_multiplier = max(self.min_size_multiplier, 
                                 min(self.max_size_multiplier, total_multiplier))
            
            # Calcula novo tamanho
            adjusted_size = base_size * total_multiplier
            
            # Detalhes do cálculo
            calculation_details = {
                'method': 'volatility_adjusted',
                'base_size': base_size,
                'adjusted_size': adjusted_size,
                'total_multiplier': total_multiplier,
                'components': {
                    'volatility': vol_multiplier,
                    'kelly': kelly_multiplier,
                    'confidence': confidence_multiplier,
                    'correlation': correlation_multiplier,
                    'regime': regime_multiplier
                },
                'volatility_analysis': vol_analysis
            }
            
            logger.info(f"Position sizing para {symbol}:")
            logger.info(f"  Base: {base_size:.4f} -> Adjusted: {adjusted_size:.4f}")
            logger.info(f"  Multiplier: {total_multiplier:.3f} (Vol: {vol_multiplier:.3f}, Kelly: {kelly_multiplier:.3f})")
            logger.info(f"  Vol regime: {vol_analysis.get('regime', 'unknown')}")
            
            return adjusted_size, calculation_details
            
        except Exception as e:
            logger.error(f"Erro no cálculo de position sizing: {e}")
            return base_size, {'method': 'error', 'error': str(e)}
    
    def _analyze_volatility(self, symbol: str) -> Dict:
        """Analisa volatilidade histórica e atual"""
        try:
            # Verifica cache
            cache_key = f"{symbol}_vol"
            if cache_key in self.volatility_cache:
                cached_data, cache_time = self.volatility_cache[cache_key]
                if (datetime.now() - cache_time).total_seconds() < 300:  # 5 min cache
                    return cached_data
            
            # Busca dados históricos
            df = self._fetch_historical_data(symbol, "1h", self.lookback_periods * 2)
            
            if df.empty or len(df) < self.lookback_periods:
                logger.warning(f"Dados insuficientes para análise de volatilidade: {symbol}")
                return {'regime': 'unknown', 'current_vol': 0.0, 'vol_percentile': 0.5}
            
            # Calcula retornos horários
            returns = df['close'].pct_change().dropna()
            
            # Volatilidade atual (últimas 24h)
            current_vol = returns.iloc[-24:].std() * np.sqrt(24) * 100  # Anualizada em %
            
            # Volatilidade histórica (rolling windows)
            rolling_vols = []
            for i in range(24, len(returns), 6):  # A cada 6 horas
                if i + 24 <= len(returns):
                    vol = returns.iloc[i:i+24].std() * np.sqrt(24) * 100
                    rolling_vols.append(vol)
            
            if not rolling_vols:
                return {'regime': 'unknown', 'current_vol': current_vol, 'vol_percentile': 0.5}
            
            # Percentil da volatilidade atual
            vol_percentile = np.searchsorted(sorted(rolling_vols), current_vol) / len(rolling_vols)
            
            # Classifica regime de volatilidade
            if vol_percentile >= 0.8:
                regime = VolatilityRegime.EXTREME
            elif vol_percentile >= 0.6:
                regime = VolatilityRegime.HIGH
            elif vol_percentile >= 0.4:
                regime = VolatilityRegime.NORMAL
            elif vol_percentile >= 0.2:
                regime = VolatilityRegime.LOW
            else:
                regime = VolatilityRegime.VERY_LOW
            
            analysis = {
                'regime': regime.value,
                'current_vol': current_vol,
                'vol_percentile': vol_percentile,
                'avg_vol': np.mean(rolling_vols),
                'vol_ratio': current_vol / np.mean(rolling_vols) if rolling_vols else 1.0
            }
            
            # Cache resultado
            self.volatility_cache[cache_key] = (analysis, datetime.now())
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na análise de volatilidade: {e}")
            return {'regime': 'unknown', 'current_vol': 0.0, 'vol_percentile': 0.5}
    
    def _fetch_historical_data(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """Busca dados históricos da exchange"""
        try:
            api_symbol = symbol.replace('/', '-')
            url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
            
            params = {
                "symbol": api_symbol,
                "interval": interval,
                "limit": min(limit, 1000)
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("code") != 0:
                return pd.DataFrame()
            
            klines = data.get("data", [])
            if not klines:
                return pd.DataFrame()
            
            df_data = []
            for kline in klines:
                df_data.append([
                    kline['time'],
                    float(kline['open']),
                    float(kline['high']),
                    float(kline['low']),
                    float(kline['close']),
                    float(kline['volume'])
                ])
            
            df = pd.DataFrame(df_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados históricos: {e}")
            return pd.DataFrame()
    
    def _calculate_volatility_multiplier(self, vol_analysis: Dict) -> float:
        """Calcula multiplicador baseado na volatilidade"""
        try:
            vol_regime = vol_analysis.get('regime', 'normal')
            current_vol = vol_analysis.get('current_vol', self.target_vol)
            
            # Método 1: Volatility targeting
            if current_vol > 0:
                vol_target_multiplier = self.target_vol / current_vol
            else:
                vol_target_multiplier = 1.0
            
            # Método 2: Regime-based adjustment
            regime_adjustments = {
                VolatilityRegime.VERY_LOW.value: 1.3,    # Aumenta em baixa vol
                VolatilityRegime.LOW.value: 1.1,
                VolatilityRegime.NORMAL.value: 1.0,
                VolatilityRegime.HIGH.value: 0.8,        # Reduz em alta vol
                VolatilityRegime.EXTREME.value: 0.5      # Reduz muito em vol extrema
            }
            
            regime_multiplier = regime_adjustments.get(vol_regime, 1.0)
            
            # Combina métodos com peso configurável
            combined_multiplier = (vol_target_multiplier * self.vol_adjustment_factor + 
                                 regime_multiplier * (1 - self.vol_adjustment_factor))
            
            return max(0.3, min(2.5, combined_multiplier))
            
        except Exception as e:
            logger.debug(f"Erro no cálculo de volatilidade: {e}")
            return 1.0
    
    def _calculate_kelly_multiplier(self, trade_history: List[Dict]) -> float:
        """Calcula multiplicador usando Kelly Criterion"""
        try:
            if len(trade_history) < 10:  # Mínimo de trades
                return 1.0
            
            # Usa últimos N trades
            recent_trades = trade_history[-self.kelly_lookback:]
            
            # Calcula win rate e payoff ratio
            wins = [t for t in recent_trades if t.get('pnl', 0) > 0]
            losses = [t for t in recent_trades if t.get('pnl', 0) < 0]
            
            if not wins or not losses:
                return 1.0
            
            win_rate = len(wins) / len(recent_trades)
            avg_win = np.mean([t['pnl'] for t in wins])
            avg_loss = abs(np.mean([t['pnl'] for t in losses]))
            
            if avg_loss == 0:
                return 1.0
            
            payoff_ratio = avg_win / avg_loss
            
            # Kelly formula: f* = (bp - q) / b
            # onde: b = payoff ratio, p = win rate, q = loss rate
            kelly_fraction = (payoff_ratio * win_rate - (1 - win_rate)) / payoff_ratio
            
            # Aplica Kelly fracionário (25% do Kelly ótimo para segurança)
            fractional_kelly = max(0.1, min(2.0, kelly_fraction * 0.25))
            
            logger.debug(f"Kelly analysis - WR: {win_rate:.2f}, PR: {payoff_ratio:.2f}, Kelly: {fractional_kelly:.2f}")
            
            return fractional_kelly
            
        except Exception as e:
            logger.debug(f"Erro no Kelly Criterion: {e}")
            return 1.0
    
    def _calculate_confidence_multiplier(self, signal_confidence: float) -> float:
        """Ajusta tamanho baseado na confiança do sinal"""
        try:
            # Mapeia confiança (0-1) para multiplicador (0.5-1.5)
            # Confiança alta = posições maiores
            base_multiplier = 0.5 + signal_confidence
            
            # Curva mais suave para evitar extremos
            if signal_confidence > 0.8:
                multiplier = 1.3
            elif signal_confidence > 0.7:
                multiplier = 1.1
            elif signal_confidence > 0.6:
                multiplier = 1.0
            elif signal_confidence > 0.5:
                multiplier = 0.9
            else:
                multiplier = 0.7
            
            return multiplier
            
        except Exception:
            return 1.0
    
    def _calculate_correlation_multiplier(self, symbol: str) -> float:
        """Ajusta tamanho considerando correlação com outras posições"""
        try:
            # Por enquanto, implementação simplificada
            # Em produção, calcularia correlação real entre ativos do portfólio
            
            # Se BTC/ETH/SOL estão correlacionados (~0.7+), reduz tamanho
            crypto_majors = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
            
            if symbol in crypto_majors:
                # Assumindo correlação alta entre majors
                return 0.9  # Reduz 10% por correlação
            
            return 1.0  # Sem ajuste para outros pares
            
        except Exception:
            return 1.0
    
    def _calculate_regime_multiplier(self, symbol: str) -> float:
        """Ajusta tamanho baseado no regime de mercado (se disponível)"""
        try:
            # Tenta obter regime do market analyzer se disponível
            # Por enquanto, implementação básica
            
            # Pode ser expandido para integrar com regime_detection
            return 1.0
            
        except Exception:
            return 1.0
    
    def calculate_portfolio_risk(self, positions: List[Dict], proposed_position: Dict) -> Dict:
        """Calcula risco total do portfólio incluindo nova posição"""
        try:
            current_risk = sum(pos.get('risk_amount', 0) for pos in positions)
            proposed_risk = proposed_position.get('risk_amount', 0)
            total_risk = current_risk + proposed_risk
            
            portfolio_value = self._get_config('advanced.paper_trading.initial_balance_usdt', 100.0)
            risk_percentage = (total_risk / portfolio_value) * 100
            
            risk_analysis = {
                'current_risk': current_risk,
                'proposed_additional_risk': proposed_risk,
                'total_portfolio_risk': total_risk,
                'risk_percentage': risk_percentage,
                'max_allowed_risk': self.max_portfolio_risk,
                'within_limits': risk_percentage <= self.max_portfolio_risk,
                'remaining_risk_budget': max(0, (self.max_portfolio_risk * portfolio_value / 100) - total_risk)
            }
            
            return risk_analysis
            
        except Exception as e:
            logger.error(f"Erro no cálculo de risco do portfólio: {e}")
            return {'within_limits': True, 'error': str(e)}
    
    def suggest_position_adjustment(self, symbol: str, current_size: float, 
                                  market_conditions: Dict) -> Tuple[float, str]:
        """Sugere ajuste de posição existente baseado em mudanças nas condições"""
        try:
            vol_analysis = self._analyze_volatility(symbol)
            current_vol_regime = vol_analysis.get('regime', 'normal')
            
            # Regras de ajuste
            if current_vol_regime == VolatilityRegime.EXTREME.value:
                # Em volatilidade extrema, reduz posição
                suggested_size = current_size * 0.6
                reason = f"Reduzindo posição devido à volatilidade extrema ({vol_analysis.get('current_vol', 0):.1f}%)"
            
            elif current_vol_regime == VolatilityRegime.VERY_LOW.value:
                # Em volatilidade muito baixa, pode aumentar
                suggested_size = current_size * 1.2
                reason = f"Aumentando posição devido à baixa volatilidade ({vol_analysis.get('current_vol', 0):.1f}%)"
            
            else:
                # Sem ajuste necessário
                suggested_size = current_size
                reason = "Sem ajuste necessário - volatilidade dentro do normal"
            
            return suggested_size, reason
            
        except Exception as e:
            logger.error(f"Erro ao sugerir ajuste: {e}")
            return current_size, "Erro no cálculo de ajuste"
    
    def get_sizing_statistics(self) -> Dict:
        """Retorna estatísticas do sistema de sizing"""
        return {
            'enabled': self.enabled,
            'target_volatility': self.target_vol,
            'max_portfolio_risk': self.max_portfolio_risk,
            'use_kelly': self.use_kelly,
            'cache_size': len(self.volatility_cache),
            'vol_adjustment_factor': self.vol_adjustment_factor,
            'size_limits': {
                'min_multiplier': self.min_size_multiplier,
                'max_multiplier': self.max_size_multiplier
            }
        }