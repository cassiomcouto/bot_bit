#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regime Detection - Sistema de Detecção de Regimes de Mercado
Identifica automaticamente condições de mercado e ajusta estratégias
"""

import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Tipos de regimes de mercado"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down" 
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"
    CONSOLIDATION = "consolidation"

@dataclass
class RegimeAnalysis:
    """Resultado da análise de regime"""
    primary_regime: MarketRegime
    secondary_regimes: List[MarketRegime]
    confidence: float
    trend_strength: float
    volatility_regime: str
    support_resistance_levels: Dict[str, float]
    regime_duration_minutes: int
    recommendations: Dict[str, any]

class RegimeDetector:
    """Detector de regimes de mercado em tempo real"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.regime_history = {}
        self.last_analysis = {}
        
        # Parâmetros de detecção
        self.regime_config = self._get_config('regime_detection', {})
        self.enabled = self.regime_config.get('enabled', True)
        
        # Thresholds para classificação
        self.trend_threshold = self.regime_config.get('trend_threshold', 0.02)  # 2%
        self.volatility_threshold = self.regime_config.get('volatility_threshold', 0.03)  # 3%
        self.breakout_threshold = self.regime_config.get('breakout_threshold', 0.015)  # 1.5%
        self.ranging_threshold = self.regime_config.get('ranging_threshold', 0.01)  # 1%
        
        # Períodos de análise
        self.short_period = self.regime_config.get('short_period_hours', 4)
        self.medium_period = self.regime_config.get('medium_period_hours', 24)
        self.long_period = self.regime_config.get('long_period_hours', 72)
        
        logger.info(f"Regime Detector inicializado - Enabled: {self.enabled}")
        
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
    
    def analyze_market_regime(self, symbol: str) -> Optional[RegimeAnalysis]:
        """Analisa regime atual do mercado para um símbolo"""
        if not self.enabled:
            return None
            
        try:
            # Obtém dados históricos
            df_short = self._fetch_market_data(symbol, "1h", self.short_period)
            df_medium = self._fetch_market_data(symbol, "4h", self.medium_period // 4)
            df_long = self._fetch_market_data(symbol, "1d", self.long_period // 24)
            
            if df_short.empty or df_medium.empty or df_long.empty:
                logger.warning(f"Dados insuficientes para análise de regime: {symbol}")
                return None
            
            # Calcula indicadores de regime
            trend_analysis = self._analyze_trend(df_short, df_medium, df_long)
            volatility_analysis = self._analyze_volatility(df_short, df_medium)
            support_resistance = self._find_support_resistance(df_medium)
            breakout_analysis = self._analyze_breakouts(df_short, support_resistance)
            
            # Determina regime principal
            primary_regime, confidence = self._determine_primary_regime(
                trend_analysis, volatility_analysis, breakout_analysis
            )
            
            # Identifica regimes secundários
            secondary_regimes = self._identify_secondary_regimes(
                trend_analysis, volatility_analysis, breakout_analysis
            )
            
            # Gera recomendações
            recommendations = self._generate_regime_recommendations(
                primary_regime, trend_analysis, volatility_analysis
            )
            
            # Calcula duração do regime
            duration = self._estimate_regime_duration(symbol, primary_regime)
            
            analysis = RegimeAnalysis(
                primary_regime=primary_regime,
                secondary_regimes=secondary_regimes,
                confidence=confidence,
                trend_strength=trend_analysis['strength'],
                volatility_regime=volatility_analysis['regime'],
                support_resistance_levels=support_resistance,
                regime_duration_minutes=duration,
                recommendations=recommendations
            )
            
            # Armazena no histórico
            self._update_regime_history(symbol, analysis)
            
            logger.info(f"Regime detectado para {symbol}: {primary_regime.value} (confiança: {confidence:.2f})")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na análise de regime para {symbol}: {e}")
            return None
    
    def _fetch_market_data(self, symbol: str, interval: str, periods: int) -> pd.DataFrame:
        """Busca dados históricos da exchange"""
        try:
            api_symbol = symbol.replace('/', '-')
            url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
            
            params = {
                "symbol": api_symbol,
                "interval": interval,
                "limit": min(periods, 1000)  # Limite da API
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
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados para {symbol}: {e}")
            return pd.DataFrame()
    
    def _analyze_trend(self, df_short: pd.DataFrame, df_medium: pd.DataFrame, 
                      df_long: pd.DataFrame) -> Dict:
        """Analisa tendência em múltiplos timeframes"""
        analysis = {
            'direction': 'neutral',
            'strength': 0.0,
            'short_term': 'neutral',
            'medium_term': 'neutral', 
            'long_term': 'neutral',
            'consistency': 0.0
        }
        
        try:
            # Análise de tendência para cada timeframe
            timeframes = [
                ('short', df_short, 4),
                ('medium', df_medium, 6), 
                ('long', df_long, 3)
            ]
            
            trends = {}
            
            for tf_name, df, periods in timeframes:
                if len(df) < periods:
                    trends[tf_name] = {'direction': 'neutral', 'strength': 0.0}
                    continue
                
                # Calcula mudança percentual
                start_price = df['close'].iloc[-periods]
                end_price = df['close'].iloc[-1]
                change_pct = ((end_price - start_price) / start_price) * 100
                
                # Classifica tendência
                if change_pct > self.trend_threshold * 100:
                    direction = 'up'
                elif change_pct < -self.trend_threshold * 100:
                    direction = 'down'
                else:
                    direction = 'neutral'
                
                # Calcula força da tendência
                strength = min(abs(change_pct) / (self.trend_threshold * 100), 3.0) / 3.0
                
                trends[tf_name] = {
                    'direction': direction,
                    'strength': strength,
                    'change_pct': change_pct
                }
                
                analysis[f'{tf_name}_term'] = direction
            
            # Determina tendência geral
            directions = [trends[tf]['direction'] for tf in trends]
            up_count = directions.count('up')
            down_count = directions.count('down')
            
            if up_count >= 2:
                analysis['direction'] = 'up'
            elif down_count >= 2:
                analysis['direction'] = 'down'
            else:
                analysis['direction'] = 'neutral'
            
            # Calcula força média
            avg_strength = np.mean([trends[tf]['strength'] for tf in trends])
            analysis['strength'] = avg_strength
            
            # Calcula consistência (concordância entre timeframes)
            consistency = max(up_count, down_count) / len(directions)
            analysis['consistency'] = consistency
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na análise de tendência: {e}")
            return analysis
    
    def _analyze_volatility(self, df_short: pd.DataFrame, df_medium: pd.DataFrame) -> Dict:
        """Analisa regime de volatilidade"""
        analysis = {
            'regime': 'normal',
            'current_vol': 0.0,
            'vol_percentile': 0.0,
            'expanding': False
        }
        
        try:
            # Calcula volatilidade realizada (retornos de 1h)
            returns = df_short['close'].pct_change().dropna()
            current_vol = returns.rolling(24).std().iloc[-1] * np.sqrt(24) * 100  # Anualizada
            
            # Calcula volatilidade histórica (lookback de 30 períodos)
            if len(df_medium) >= 30:
                historical_vols = []
                for i in range(10, len(df_medium)):
                    period_returns = df_medium['close'].iloc[i-10:i].pct_change().dropna()
                    if len(period_returns) > 0:
                        vol = period_returns.std() * np.sqrt(6) * 100  # 4h -> anualizada
                        historical_vols.append(vol)
                
                if historical_vols:
                    vol_percentile = (np.searchsorted(sorted(historical_vols), current_vol) / 
                                    len(historical_vols))
                    
                    # Classifica regime
                    if vol_percentile > 0.8:
                        regime = 'high'
                    elif vol_percentile < 0.2:
                        regime = 'low'
                    else:
                        regime = 'normal'
                    
                    analysis.update({
                        'regime': regime,
                        'current_vol': current_vol,
                        'vol_percentile': vol_percentile
                    })
            
            # Verifica se volatilidade está expandindo
            if len(returns) >= 48:  # 48h de dados
                recent_vol = returns.iloc[-24:].std() * np.sqrt(24) * 100
                prev_vol = returns.iloc[-48:-24].std() * np.sqrt(24) * 100
                expanding = recent_vol > prev_vol * 1.2
                analysis['expanding'] = expanding
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na análise de volatilidade: {e}")
            return analysis
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Identifica níveis de suporte e resistência"""
        levels = {'support': 0.0, 'resistance': 0.0}
        
        try:
            if len(df) < 20:
                return levels
            
            # Encontra máximos e mínimos locais
            highs = df['high'].rolling(window=5, center=True).max()
            lows = df['low'].rolling(window=5, center=True).min()
            
            local_highs = df[df['high'] == highs]['high'].values
            local_lows = df[df['low'] == lows]['low'].values
            
            if len(local_highs) > 0 and len(local_lows) > 0:
                # Resistência: média dos maiores máximos
                resistance = np.mean(sorted(local_highs)[-3:])
                # Suporte: média dos menores mínimos  
                support = np.mean(sorted(local_lows)[:3])
                
                levels = {
                    'support': float(support),
                    'resistance': float(resistance)
                }
            
            return levels
            
        except Exception as e:
            logger.error(f"Erro ao encontrar suporte/resistência: {e}")
            return levels
    
    def _analyze_breakouts(self, df: pd.DataFrame, sr_levels: Dict) -> Dict:
        """Analisa breakouts de níveis importantes"""
        analysis = {
            'breakout_type': 'none',
            'breakout_strength': 0.0,
            'volume_confirmation': False
        }
        
        try:
            if len(df) < 10 or not sr_levels['support'] or not sr_levels['resistance']:
                return analysis
            
            current_price = df['close'].iloc[-1]
            resistance = sr_levels['resistance']
            support = sr_levels['support']
            
            # Verifica breakout de resistência
            if current_price > resistance * (1 + self.breakout_threshold):
                analysis['breakout_type'] = 'resistance'
                strength = (current_price - resistance) / resistance
                analysis['breakout_strength'] = min(strength / self.breakout_threshold, 2.0)
                
            # Verifica breakout de suporte
            elif current_price < support * (1 - self.breakout_threshold):
                analysis['breakout_type'] = 'support'
                strength = (support - current_price) / support
                analysis['breakout_strength'] = min(strength / self.breakout_threshold, 2.0)
            
            # Confirma com volume (últimas 3 barras vs média de 10)
            if len(df) >= 13:
                recent_volume = df['volume'].iloc[-3:].mean()
                avg_volume = df['volume'].iloc[-13:-3].mean()
                if recent_volume > avg_volume * 1.5:
                    analysis['volume_confirmation'] = True
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na análise de breakouts: {e}")
            return analysis
    
    def _determine_primary_regime(self, trend_analysis: Dict, vol_analysis: Dict, 
                                breakout_analysis: Dict) -> Tuple[MarketRegime, float]:
        """Determina o regime primário com base nas análises"""
        
        # Verifica breakouts primeiro (prioridade alta)
        if breakout_analysis['breakout_strength'] > 1.0:
            confidence = min(breakout_analysis['breakout_strength'], 2.0) / 2.0
            if breakout_analysis['breakout_type'] == 'resistance':
                return MarketRegime.BREAKOUT_UP, confidence * 0.8
            elif breakout_analysis['breakout_type'] == 'support':
                return MarketRegime.BREAKOUT_DOWN, confidence * 0.8
        
        # Verifica regimes de volatilidade
        if vol_analysis['regime'] == 'high' and vol_analysis['expanding']:
            confidence = vol_analysis['vol_percentile']
            return MarketRegime.HIGH_VOLATILITY, confidence * 0.7
        
        # Verifica tendências
        trend_direction = trend_analysis['direction']
        trend_strength = trend_analysis['strength']
        consistency = trend_analysis['consistency']
        
        if trend_direction == 'up' and trend_strength > 0.6:
            confidence = (trend_strength * consistency + consistency) / 2
            return MarketRegime.TRENDING_UP, confidence
        elif trend_direction == 'down' and trend_strength > 0.6:
            confidence = (trend_strength * consistency + consistency) / 2
            return MarketRegime.TRENDING_DOWN, confidence
        
        # Verifica ranging/consolidação
        if (trend_strength < 0.3 and vol_analysis['regime'] in ['normal', 'low']):
            confidence = 1.0 - trend_strength  # Quanto menor a tendência, mais confiante no ranging
            if vol_analysis['regime'] == 'low':
                return MarketRegime.LOW_VOLATILITY, confidence * 0.8
            else:
                return MarketRegime.RANGING, confidence * 0.6
        
        # Default: consolidação
        return MarketRegime.CONSOLIDATION, 0.4
    
    def _identify_secondary_regimes(self, trend_analysis: Dict, vol_analysis: Dict, 
                                  breakout_analysis: Dict) -> List[MarketRegime]:
        """Identifica regimes secundários"""
        secondary = []
        
        # Adiciona regime de volatilidade se não for primário
        if vol_analysis['regime'] == 'high':
            secondary.append(MarketRegime.HIGH_VOLATILITY)
        elif vol_analysis['regime'] == 'low':
            secondary.append(MarketRegime.LOW_VOLATILITY)
        
        # Adiciona tendências fracas
        if trend_analysis['strength'] > 0.3:
            if trend_analysis['direction'] == 'up':
                secondary.append(MarketRegime.TRENDING_UP)
            elif trend_analysis['direction'] == 'down':
                secondary.append(MarketRegime.TRENDING_DOWN)
        
        return secondary
    
    def _generate_regime_recommendations(self, regime: MarketRegime, trend_analysis: Dict, 
                                       vol_analysis: Dict) -> Dict:
        """Gera recomendações de trading baseadas no regime"""
        recommendations = {
            'strategy_adjustments': {},
            'risk_adjustments': {},
            'timing_adjustments': {},
            'indicator_adjustments': {}
        }
        
        if regime == MarketRegime.TRENDING_UP:
            recommendations.update({
                'strategy_adjustments': {
                    'favor_long': True,
                    'avoid_mean_reversion': True,
                    'use_momentum': True
                },
                'risk_adjustments': {
                    'increase_position_size': 1.2,
                    'wider_stops': True,
                    'trail_stops': True
                },
                'indicator_adjustments': {
                    'lower_rsi_oversold': 25,
                    'favor_macd_bullish': True
                }
            })
            
        elif regime == MarketRegime.TRENDING_DOWN:
            recommendations.update({
                'strategy_adjustments': {
                    'favor_short': True,
                    'avoid_mean_reversion': True,
                    'use_momentum': True
                },
                'risk_adjustments': {
                    'increase_position_size': 1.2,
                    'wider_stops': True,
                    'trail_stops': True
                },
                'indicator_adjustments': {
                    'higher_rsi_overbought': 75,
                    'favor_macd_bearish': True
                }
            })
            
        elif regime == MarketRegime.RANGING:
            recommendations.update({
                'strategy_adjustments': {
                    'use_mean_reversion': True,
                    'avoid_breakouts': False,
                    'scalping_friendly': True
                },
                'risk_adjustments': {
                    'tighter_stops': True,
                    'quick_profits': True,
                    'reduce_position_size': 0.8
                },
                'indicator_adjustments': {
                    'use_bb_extremes': True,
                    'rsi_extremes': True
                }
            })
            
        elif regime == MarketRegime.HIGH_VOLATILITY:
            recommendations.update({
                'strategy_adjustments': {
                    'reduce_frequency': True,
                    'wait_for_confirmation': True
                },
                'risk_adjustments': {
                    'reduce_position_size': 0.6,
                    'wider_stops': True,
                    'faster_exits': True
                },
                'timing_adjustments': {
                    'longer_cooldown': True,
                    'avoid_news_times': True
                }
            })
            
        elif regime in [MarketRegime.BREAKOUT_UP, MarketRegime.BREAKOUT_DOWN]:
            recommendations.update({
                'strategy_adjustments': {
                    'momentum_follow': True,
                    'quick_entry': True,
                    'volume_confirmation': True
                },
                'risk_adjustments': {
                    'increase_position_size': 1.5,
                    'trail_stops_aggressive': True
                }
            })
        
        return recommendations
    
    def _estimate_regime_duration(self, symbol: str, regime: MarketRegime) -> int:
        """Estima há quanto tempo o regime está ativo (em minutos)"""
        if symbol not in self.regime_history:
            return 0
        
        history = self.regime_history[symbol]
        if not history:
            return 0
        
        # Conta quantos períodos consecutivos do mesmo regime
        consecutive_count = 0
        for entry in reversed(history[-10:]):  # Últimas 10 análises
            if entry['regime'] == regime:
                consecutive_count += 1
            else:
                break
        
        # Estima duração (assumindo análise a cada hora)
        return consecutive_count * 60
    
    def _update_regime_history(self, symbol: str, analysis: RegimeAnalysis):
        """Atualiza histórico de regimes"""
        if symbol not in self.regime_history:
            self.regime_history[symbol] = []
        
        entry = {
            'timestamp': datetime.now(),
            'regime': analysis.primary_regime,
            'confidence': analysis.confidence,
            'trend_strength': analysis.trend_strength
        }
        
        self.regime_history[symbol].append(entry)
        
        # Mantém apenas últimas 48 entradas (2 dias se analisado de hora em hora)
        if len(self.regime_history[symbol]) > 48:
            self.regime_history[symbol] = self.regime_history[symbol][-48:]
    
    def get_current_regime(self, symbol: str) -> Optional[MarketRegime]:
        """Retorna o regime atual de um símbolo"""
        if symbol in self.last_analysis:
            return self.last_analysis[symbol].primary_regime
        return None
    
    def should_analyze(self, symbol: str, interval_minutes: int = 60) -> bool:
        """Verifica se deve fazer nova análise de regime"""
        if symbol not in self.last_analysis:
            return True
        
        last_time = self.last_analysis.get(f"{symbol}_timestamp", datetime.min)
        time_since = (datetime.now() - last_time).total_seconds() / 60
        
        return time_since >= interval_minutes
    
    def get_regime_stats(self) -> Dict:
        """Retorna estatísticas dos regimes detectados"""
        stats = {
            'symbols_tracked': len(self.regime_history),
            'enabled': self.enabled,
            'regime_counts': {},
            'avg_confidence': 0.0
        }
        
        all_regimes = []
        confidences = []
        
        for symbol_history in self.regime_history.values():
            for entry in symbol_history[-24:]:  # Últimas 24h
                regime = entry['regime'].value
                all_regimes.append(regime)
                confidences.append(entry['confidence'])
        
        if all_regimes:
            from collections import Counter
            stats['regime_counts'] = dict(Counter(all_regimes))
            stats['avg_confidence'] = np.mean(confidences)
        
        return stats