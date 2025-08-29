#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Análise Técnica - VERSÃO OTIMIZADA
Ajustes críticos para melhorar win rate e frequência de trades
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from models.data_classes import TradingSignal, SignalStrength, PositionSide
from datetime import datetime

logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    """Análise técnica otimizada para melhor performance"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.signal_count = 0
        self.analysis_count = 0
        self.first_analysis_time = None
        self.last_signal_time = None
    
    def _get_config(self, path: str, default=None):
        """Helper para acessar configuração aninhada"""
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def _check_contradictory_signals(self, indicators: Dict[str, Any], action: str) -> bool:
        """Verifica sinais contraditórios - MAIS FLEXÍVEL"""
        
        # Verifica se está desabilitado na config
        if not self._get_config('ai_futures.filters.contradictory_signals_check', True):
            return False
            
        contradictions = []
        critical_contradictions = 0  # Conta apenas contradições críticas
        
        if action in ['long', 'close_short']:
            # Para LONG, verificar contradições CRÍTICAS apenas
            if indicators.get('macd_bearish', False) and indicators.get('macd_histogram', 0) < -0.1:
                critical_contradictions += 1
                contradictions.append("MACD forte bearish")
            
            if indicators.get('rsi', 50) > 85:  # Apenas RSI MUITO alto
                critical_contradictions += 1
                contradictions.append(f"RSI extremo ({indicators['rsi']:.1f})")
            
            if indicators.get('ema_trend', '') == 'strong_bearish':  # Apenas tendência FORTE
                critical_contradictions += 1
                contradictions.append("EMA forte bearish")
                
        elif action in ['short', 'close_long']:
            # Para SHORT, verificar contradições CRÍTICAS apenas
            if indicators.get('macd_bullish', False) and indicators.get('macd_histogram', 0) > 0.1:
                critical_contradictions += 1
                contradictions.append("MACD forte bullish")
            
            if indicators.get('rsi', 50) < 15:  # Apenas RSI MUITO baixo
                critical_contradictions += 1
                contradictions.append(f"RSI extremo ({indicators['rsi']:.1f})")
            
            if indicators.get('ema_trend', '') == 'strong_bullish':  # Apenas tendência FORTE
                critical_contradictions += 1
                contradictions.append("EMA forte bullish")
        
        # Só rejeita se tiver 2+ contradições CRÍTICAS
        if critical_contradictions >= 2:
            logger.warning(f"Contradições críticas para {action}: {contradictions}")
            return True
        
        return False
    
    def calculate_technical_indicators(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """Calcula indicadores técnicos com validações"""
        if df.empty or len(df) < 30:  # Reduzido de 50 para 30
            logger.warning(f"Dados insuficientes: {len(df)} velas (mínimo: 30)")
            return {}
        
        indicators = {}
        
        try:
            # Análise básica
            current_price = float(df['close'].iloc[-1])
            indicators['current_price'] = current_price
            
            # Tendência de preço
            if len(df) >= 15:  # Reduzido de 20 para 15
                price_15_bars_ago = float(df['close'].iloc[-15])
                price_change_pct = ((current_price - price_15_bars_ago) / price_15_bars_ago) * 100
                indicators['price_trend_15'] = 'up' if price_change_pct > 0.8 else 'down' if price_change_pct < -0.8 else 'neutral'
                indicators['price_change_15_pct'] = price_change_pct
            
            # RSI - MAIS AGRESSIVO
            try:
                rsi_period = 14
                if len(df) >= rsi_period + 3:  # Reduzido requisito
                    rsi = RSIIndicator(close=df['close'], window=rsi_period)
                    current_rsi = float(rsi.rsi().iloc[-1])
                    indicators['rsi'] = current_rsi
                    
                    # RSI médio dos últimos 3 períodos (reduzido de 5)
                    rsi_values = rsi.rsi().iloc[-3:]
                    indicators['rsi_avg_3'] = float(rsi_values.mean())
                    
                    # RSI trend
                    if len(df) >= 2:
                        rsi_prev = float(rsi.rsi().iloc[-2])
                        indicators['rsi_rising'] = current_rsi > rsi_prev
                        indicators['rsi_delta'] = current_rsi - rsi_prev
                    
                    # Níveis mais agressivos
                    indicators['rsi_oversold_25'] = current_rsi < 25
                    indicators['rsi_overbought_75'] = current_rsi > 75
                    
                    logger.info(f"RSI: {current_rsi:.1f} (Média 3: {indicators['rsi_avg_3']:.1f})")
            except Exception as e:
                logger.debug(f"Erro no RSI: {e}")
            
            # MACD - MENOS RESTRITIVO
            try:
                if len(df) >= 30:  # Reduzido de 35 para 30
                    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
                    indicators['macd'] = float(macd.macd().iloc[-1])
                    indicators['macd_signal'] = float(macd.macd_signal().iloc[-1])
                    indicators['macd_histogram'] = float(macd.macd_diff().iloc[-1])
                    
                    # MACD trend
                    macd_hist_values = macd.macd_diff().iloc[-3:]  # Reduzido de 5 para 3
                    indicators['macd_histogram_avg_3'] = float(macd_hist_values.mean())
                    
                    if len(df) >= 2:
                        hist_prev = float(macd.macd_diff().iloc[-2])
                        indicators['macd_histogram_rising'] = indicators['macd_histogram'] > hist_prev
                        indicators['macd_bullish'] = indicators['macd_histogram'] > 0
                        indicators['macd_bearish'] = indicators['macd_histogram'] < 0
                        
                        # MACD mais sensível
                        indicators['macd_weak_bullish'] = indicators['macd_histogram'] > -0.1
                        indicators['macd_weak_bearish'] = indicators['macd_histogram'] < 0.1
                    
                    logger.info(f"MACD Hist: {indicators['macd_histogram']:.4f}")
            except Exception as e:
                logger.debug(f"Erro no MACD: {e}")
            
            # EMA - MENOS RESTRITIVO
            try:
                ema_short_period = self._get_config('ai_futures.ema.short_period', 9)
                ema_long_period = self._get_config('ai_futures.ema.long_period', 21)
                
                if len(df) >= max(ema_short_period, ema_long_period):
                    ema_short = EMAIndicator(close=df['close'], window=ema_short_period)
                    ema_long = EMAIndicator(close=df['close'], window=ema_long_period)
                    
                    indicators['ema_short'] = float(ema_short.ema_indicator().iloc[-1])
                    indicators['ema_long'] = float(ema_long.ema_indicator().iloc[-1])
                    
                    # EMA cross
                    indicators['ema_bullish'] = indicators['ema_short'] > indicators['ema_long']
                    indicators['ema_bearish'] = indicators['ema_short'] < indicators['ema_long']
                    
                    # Distância entre EMAs
                    ema_diff_pct = ((indicators['ema_short'] - indicators['ema_long']) / indicators['ema_long']) * 100
                    indicators['ema_diff_pct'] = ema_diff_pct
                    
                    # Preço vs EMAs
                    indicators['price_above_ema_short'] = current_price > indicators['ema_short']
                    indicators['price_above_ema_long'] = current_price > indicators['ema_long']
                    
                    # Trend - MENOS RESTRITIVO
                    if indicators['ema_bullish'] and indicators['price_above_ema_short'] and abs(ema_diff_pct) > 0.15:
                        indicators['ema_trend'] = 'strong_bullish'
                    elif indicators['ema_bullish']:
                        indicators['ema_trend'] = 'bullish'
                    elif indicators['ema_bearish'] and not indicators['price_above_ema_short'] and abs(ema_diff_pct) > 0.15:
                        indicators['ema_trend'] = 'strong_bearish'
                    elif indicators['ema_bearish']:
                        indicators['ema_trend'] = 'bearish'
                    else:
                        indicators['ema_trend'] = 'neutral'
                    
                    logger.info(f"EMA Trend: {indicators['ema_trend']} (Diff: {ema_diff_pct:.2f}%)")
            except Exception as e:
                logger.debug(f"Erro no EMA: {e}")
            
            # Bollinger Bands
            try:
                if len(df) >= 20:
                    bb = BollingerBands(close=df['close'], window=20, window_dev=2.0)
                    
                    indicators['bb_upper'] = float(bb.bollinger_hband().iloc[-1])
                    indicators['bb_middle'] = float(bb.bollinger_mavg().iloc[-1])
                    indicators['bb_lower'] = float(bb.bollinger_lband().iloc[-1])
                    
                    bb_range = indicators['bb_upper'] - indicators['bb_lower']
                    if bb_range > 0:
                        indicators['bb_position'] = (current_price - indicators['bb_lower']) / bb_range
                    else:
                        indicators['bb_position'] = 0.5
                    
                    # BB width (volatilidade)
                    bb_width_pct = (bb_range / indicators['bb_middle']) * 100
                    indicators['bb_width_pct'] = bb_width_pct
                    
                    # Classificação MAIS AGRESSIVA
                    indicators['bb_oversold'] = indicators['bb_position'] < 0.15  # Era 0.20
                    indicators['bb_overbought'] = indicators['bb_position'] > 0.85  # Era 0.80
                    
                    logger.info(f"BB Position: {indicators['bb_position']:.2f}")
            except Exception as e:
                logger.debug(f"Erro no BB: {e}")
            
            # Momentum
            try:
                if len(df) >= 8:  # Reduzido de 10 para 8
                    momentum_period = 8  # Reduzido de 10 para 8
                    momentum = ((current_price - float(df['close'].iloc[-momentum_period])) / 
                               float(df['close'].iloc[-momentum_period])) * 100
                    indicators['momentum'] = momentum
                    indicators['momentum_bullish'] = momentum > 0.3  # Reduzido de 0.5
                    indicators['momentum_bearish'] = momentum < -0.3  # Reduzido de -0.5
                    indicators['momentum_strong'] = abs(momentum) > 1.5  # Reduzido de 2.0
                    
                    logger.info(f"Momentum: {momentum:.2f}%")
            except Exception as e:
                logger.debug(f"Erro no Momentum: {e}")
            
            # Volatilidade
            if len(df) >= 15:  # Reduzido de 20 para 15
                try:
                    returns = df['close'].pct_change().dropna()
                    indicators['volatility'] = float(returns.iloc[-15:].std() * 100)  # Reduzido de 20 para 15
                    indicators['high_volatility'] = indicators['volatility'] > 1.8  # Reduzido de 2.0
                    logger.info(f"Volatilidade: {indicators['volatility']:.2f}%")
                except:
                    pass
            
            # Resumo
            logger.info(f"Indicadores calculados: {len(indicators)} indicadores")
            
            # Aumenta contador de análises
            self.analysis_count += 1
            if self.first_analysis_time is None:
                self.first_analysis_time = datetime.now()
            
            return indicators
            
        except Exception as e:
            logger.error(f"Erro geral ao calcular indicadores: {e}")
            return indicators
    
    def generate_trading_signal(self, df: pd.DataFrame, symbol: str, 
                               indicators: Dict[str, Any] = None,
                               current_positions: Dict = None) -> TradingSignal:
        """Gera sinais com lógica otimizada"""
        
        # Se não tem indicadores, calcula
        if not indicators:
            indicators = self.calculate_technical_indicators(df, symbol)
        
        # Validação inicial
        if not indicators or len(indicators) < 8:  # Reduzido de 10 para 8
            return TradingSignal(
                action='hold', strength=SignalStrength.NEUTRAL, confidence=0.0,
                indicators={}, timestamp=datetime.now(), 
                reason="Indicadores insuficientes"
            )
        
        # Verificar tempo mínimo - REDUZIDO
        if self.first_analysis_time:
            time_since_first = (datetime.now() - self.first_analysis_time).total_seconds()
            initial_wait = self._get_config('strategy.initial_wait_seconds', 30)  # Reduzido
            
            if time_since_first < initial_wait:
                remaining = initial_wait - time_since_first
                logger.info(f"Aguardando período inicial: {remaining:.0f}s restantes")
                return TradingSignal(
                    action='hold', strength=SignalStrength.NEUTRAL, confidence=0.0,
                    indicators=indicators, timestamp=datetime.now(),
                    reason=f"Período de aquecimento ({remaining:.0f}s restantes)"
                )
        
        # Cooldown entre sinais - MAIS FLEXÍVEL
        if self.last_signal_time:
            cooldown = self._get_config('strategy.cooldown_between_trades_seconds', 180)
            time_since_signal = (datetime.now() - self.last_signal_time).total_seconds()
            if time_since_signal < cooldown:
                remaining = cooldown - time_since_signal
                return TradingSignal(
                    action='hold', strength=SignalStrength.NEUTRAL, confidence=0.0,
                    indicators=indicators, timestamp=datetime.now(),
                    reason=f"Cooldown ativo ({remaining:.0f}s restantes)"
                )
        
        # Se já tem posição
        has_position = current_positions and symbol in current_positions
        if has_position:
            return self._generate_exit_signal(indicators, symbol, current_positions)
        
        # ANÁLISE PARA ENTRADA - MAIS AGRESSIVA
        long_score = 0
        short_score = 0
        long_reasons = []
        short_reasons = []
        
        rsi = indicators.get('rsi', 50)
        rsi_avg = indicators.get('rsi_avg_3', 50)  # Mudou de 5 para 3
        
        # === ANÁLISE LONG (mais agressiva) ===
        # RSI - MAIS AGRESSIVO
        if rsi < 20 and rsi_avg < 25:  # Extremo
            long_score += 5
            long_reasons.append(f"RSI extremo oversold ({rsi:.1f})")
        elif rsi < 25 and rsi_avg < 30:  # Muito baixo
            long_score += 4
            long_reasons.append(f"RSI oversold forte ({rsi:.1f})")
        elif rsi < 30 and indicators.get('rsi_rising', False):  # Subindo de baixo
            long_score += 3
            long_reasons.append(f"RSI subindo de oversold ({rsi:.1f})")
        elif rsi < 35:  # Baixo
            long_score += 2
            long_reasons.append(f"RSI baixo ({rsi:.1f})")
        elif rsi < 45:  # Neutro baixo
            long_score += 1
            long_reasons.append(f"RSI neutro-baixo ({rsi:.1f})")
        
        # MACD - MAIS FLEXÍVEL
        macd_hist = indicators.get('macd_histogram', 0)
        if indicators.get('macd_bullish', False):
            if indicators.get('macd_histogram_rising', False):
                if indicators.get('macd_histogram_avg_3', 0) > 0.02:
                    long_score += 4
                    long_reasons.append("MACD forte bullish")
                else:
                    long_score += 3
                    long_reasons.append("MACD bullish subindo")
            else:
                long_score += 2
                long_reasons.append("MACD bullish")
        elif indicators.get('macd_weak_bullish', False) and macd_hist > -0.05:  # Quase virando
            long_score += 1
            long_reasons.append("MACD quase bullish")
        
        # EMA - MAIS FLEXÍVEL
        ema_trend = indicators.get('ema_trend', 'neutral')
        if ema_trend == 'strong_bullish':
            long_score += 4
            long_reasons.append("EMA forte bullish")
        elif ema_trend == 'bullish':
            long_score += 3
            long_reasons.append("EMA bullish")
        elif indicators.get('price_above_ema_short', False):  # Pelo menos acima da EMA curta
            long_score += 1
            long_reasons.append("Preço acima EMA curta")
        
        # Bollinger - MAIS AGRESSIVO
        if indicators.get('bb_oversold', False):
            bb_width = indicators.get('bb_width_pct', 0)
            if bb_width > 2.5:
                long_score += 3
                long_reasons.append("BB oversold + alta volatilidade")
            else:
                long_score += 2
                long_reasons.append("BB oversold")
        elif indicators.get('bb_position', 0.5) < 0.25:  # Próximo ao oversold
            long_score += 1
            long_reasons.append("BB baixo")
        
        # Momentum
        momentum = indicators.get('momentum', 0)
        if indicators.get('momentum_bullish', False) and indicators.get('momentum_strong', False):
            long_score += 3
            long_reasons.append(f"Momentum forte bullish ({momentum:.1f}%)")
        elif indicators.get('momentum_bullish', False):
            long_score += 2
            long_reasons.append("Momentum bullish")
        elif momentum > -0.5:  # Não muito negativo
            long_score += 1
            long_reasons.append("Momentum neutro")
        
        # === ANÁLISE SHORT (mais agressiva) ===
        # RSI
        if rsi > 80 and rsi_avg > 75:
            short_score += 5
            short_reasons.append(f"RSI extremo overbought ({rsi:.1f})")
        elif rsi > 75 and rsi_avg > 70:
            short_score += 4
            short_reasons.append(f"RSI overbought forte ({rsi:.1f})")
        elif rsi > 70 and not indicators.get('rsi_rising', True):
            short_score += 3
            short_reasons.append(f"RSI caindo de overbought ({rsi:.1f})")
        elif rsi > 65:
            short_score += 2
            short_reasons.append(f"RSI alto ({rsi:.1f})")
        elif rsi > 55:
            short_score += 1
            short_reasons.append(f"RSI neutro-alto ({rsi:.1f})")
        
        # MACD
        if indicators.get('macd_bearish', False):
            if not indicators.get('macd_histogram_rising', True):
                if indicators.get('macd_histogram_avg_3', 0) < -0.02:
                    short_score += 4
                    short_reasons.append("MACD forte bearish")
                else:
                    short_score += 3
                    short_reasons.append("MACD bearish descendo")
            else:
                short_score += 2
                short_reasons.append("MACD bearish")
        elif indicators.get('macd_weak_bearish', False) and macd_hist < 0.05:
            short_score += 1
            short_reasons.append("MACD quase bearish")
        
        # EMA
        if ema_trend == 'strong_bearish':
            short_score += 4
            short_reasons.append("EMA forte bearish")
        elif ema_trend == 'bearish':
            short_score += 3
            short_reasons.append("EMA bearish")
        elif not indicators.get('price_above_ema_short', True):
            short_score += 1
            short_reasons.append("Preço abaixo EMA curta")
        
        # Bollinger
        if indicators.get('bb_overbought', False):
            bb_width = indicators.get('bb_width_pct', 0)
            if bb_width > 2.5:
                short_score += 3
                short_reasons.append("BB overbought + alta volatilidade")
            else:
                short_score += 2
                short_reasons.append("BB overbought")
        elif indicators.get('bb_position', 0.5) > 0.75:
            short_score += 1
            short_reasons.append("BB alto")
        
        # Momentum
        if indicators.get('momentum_bearish', False) and indicators.get('momentum_strong', False):
            short_score += 3
            short_reasons.append(f"Momentum forte bearish ({momentum:.1f}%)")
        elif indicators.get('momentum_bearish', False):
            short_score += 2
            short_reasons.append("Momentum bearish")
        elif momentum < 0.5:
            short_score += 1
            short_reasons.append("Momentum neutro")
        
        # === DECISÃO COM PARÂMETROS OTIMIZADOS ===
        logger.info(f"ANÁLISE DE SCORES:")
        logger.info(f"   Long: {long_score} pontos | Short: {short_score} pontos")
        
        # Score mínimo REDUZIDO
        min_score_long = self._get_config('ai_futures.scoring.min_score_long', 4.0)  # Era 6.0
        min_score_short = self._get_config('ai_futures.scoring.min_score_short', 4.0)  # Era 6.0
        min_score_difference = self._get_config('ai_futures.scoring.min_score_difference', 1.0)  # Era 2.0
        
        # Verificar sinais contraditórios (mais flexível)
        check_contradictions = self._get_config('ai_futures.filters.contradictory_signals_check', False)
        
        if long_score >= min_score_long and long_score > short_score + min_score_difference:
            if check_contradictions and self._check_contradictory_signals(indicators, 'long'):
                logger.warning("Trade LONG rejeitado por contradições críticas")
                return TradingSignal(
                    action='hold', strength=SignalStrength.NEUTRAL, confidence=0.0,
                    indicators=indicators, timestamp=datetime.now(),
                    reason="Contradições críticas detectadas"
                )
            
            # SINAL LONG VALIDADO
            confidence = min(0.45 + (long_score * 0.08), 0.95)  # Mais generoso
            
            if long_score >= 12:
                strength = SignalStrength.VERY_STRONG
            elif long_score >= 8:
                strength = SignalStrength.STRONG
            elif long_score >= 5:
                strength = SignalStrength.NEUTRAL
            else:
                strength = SignalStrength.WEAK
            
            reason = " | ".join(long_reasons[:3])
            
            self.signal_count += 1
            self.last_signal_time = datetime.now()
            logger.info(f"SINAL LONG VALIDADO #{self.signal_count}")
            logger.info(f"   Score: {long_score} pontos")
            logger.info(f"   Confiança: {confidence:.1%}")
            logger.info(f"   Força: {strength.name}")
            logger.info(f"   Razões: {reason}")
            
            return TradingSignal(
                action='long',
                strength=strength,
                confidence=confidence,
                indicators=indicators,
                timestamp=datetime.now(),
                reason=reason
            )
            
        elif short_score >= min_score_short and short_score > long_score + min_score_difference:
            if check_contradictions and self._check_contradictory_signals(indicators, 'short'):
                logger.warning("Trade SHORT rejeitado por contradições críticas")
                return TradingSignal(
                    action='hold', strength=SignalStrength.NEUTRAL, confidence=0.0,
                    indicators=indicators, timestamp=datetime.now(),
                    reason="Contradições críticas detectadas"
                )
            
            # SINAL SHORT VALIDADO
            confidence = min(0.45 + (short_score * 0.08), 0.95)
            
            if short_score >= 12:
                strength = SignalStrength.VERY_STRONG
            elif short_score >= 8:
                strength = SignalStrength.STRONG
            elif short_score >= 5:
                strength = SignalStrength.NEUTRAL
            else:
                strength = SignalStrength.WEAK
            
            reason = " | ".join(short_reasons[:3])
            
            self.signal_count += 1
            self.last_signal_time = datetime.now()
            logger.info(f"SINAL SHORT VALIDADO #{self.signal_count}")
            logger.info(f"   Score: {short_score} pontos")
            logger.info(f"   Confiança: {confidence:.1%}")
            logger.info(f"   Força: {strength.name}")
            logger.info(f"   Razões: {reason}")
            
            return TradingSignal(
                action='short',
                strength=strength,
                confidence=confidence,
                indicators=indicators,
                timestamp=datetime.now(),
                reason=reason
            )
        
        # Sem sinal forte o suficiente
        logger.info(f"HOLD - Scores: L:{long_score} S:{short_score} (min:{min_score_long}, diff:{min_score_difference})")
        
        return TradingSignal(
            action='hold',
            strength=SignalStrength.NEUTRAL,
            confidence=0.0,
            indicators=indicators,
            timestamp=datetime.now(),
            reason=f"Aguardando sinal mais forte (L:{long_score} S:{short_score})"
        )
    
    def _generate_exit_signal(self, indicators: Dict[str, Any], symbol: str, 
                            current_positions: Dict) -> TradingSignal:
        """Gera sinais de saída para posições abertas"""
        position = current_positions[symbol]
        rsi = indicators.get('rsi', 50)
        rsi_avg = indicators.get('rsi_avg_3', 50)  # Mudou de 5 para 3
        
        exit_score = 0
        exit_reasons = []
        
        if position.side == PositionSide.LONG:
            # Sinais de saída para LONG - MAIS FLEXÍVEL
            if rsi > 85 and rsi_avg > 80:
                exit_score += 5
                exit_reasons.append(f"RSI extremo alto ({rsi:.1f})")
            elif rsi > 80:
                exit_score += 4
                exit_reasons.append(f"RSI muito alto ({rsi:.1f})")
            elif rsi > 75 and not indicators.get('rsi_rising', True):
                exit_score += 3
                exit_reasons.append(f"RSI alto e caindo ({rsi:.1f})")
            elif rsi > 70:
                exit_score += 2
                exit_reasons.append(f"RSI alto ({rsi:.1f})")
            
            if indicators.get('bb_position', 0.5) > 0.95:
                exit_score += 4
                exit_reasons.append("BB extremo alto")
            elif indicators.get('bb_position', 0.5) > 0.85:
                exit_score += 3
                exit_reasons.append("BB overbought")
            elif indicators.get('bb_position', 0.5) > 0.80:
                exit_score += 1
                exit_reasons.append("BB alto")
            
            if indicators.get('macd_bearish', False) and not indicators.get('macd_histogram_rising', True):
                exit_score += 3
                exit_reasons.append("MACD virou bearish e caindo")
            elif indicators.get('macd_bearish', False):
                exit_score += 2
                exit_reasons.append("MACD virou bearish")
            
            if indicators.get('ema_trend', '') in ['bearish', 'strong_bearish']:
                if indicators.get('ema_trend') == 'strong_bearish':
                    exit_score += 3
                    exit_reasons.append("EMA forte bearish")
                else:
                    exit_score += 2
                    exit_reasons.append("EMA bearish")
            
            if indicators.get('momentum_bearish', False) and indicators.get('momentum_strong', False):
                exit_score += 3
                exit_reasons.append("Momentum forte negativo")
            elif indicators.get('momentum_bearish', False):
                exit_score += 2
                exit_reasons.append("Momentum negativo")
                
        else:  # SHORT
            # Sinais de saída para SHORT - MAIS FLEXÍVEL
            if rsi < 15 and rsi_avg < 20:
                exit_score += 5
                exit_reasons.append(f"RSI extremo baixo ({rsi:.1f})")
            elif rsi < 20:
                exit_score += 4
                exit_reasons.append(f"RSI muito baixo ({rsi:.1f})")
            elif rsi < 25 and indicators.get('rsi_rising', False):
                exit_score += 3
                exit_reasons.append(f"RSI baixo e subindo ({rsi:.1f})")
            elif rsi < 30:
                exit_score += 2
                exit_reasons.append(f"RSI baixo ({rsi:.1f})")
            
            if indicators.get('bb_position', 0.5) < 0.05:
                exit_score += 4
                exit_reasons.append("BB extremo baixo")
            elif indicators.get('bb_position', 0.5) < 0.15:
                exit_score += 3
                exit_reasons.append("BB oversold")
            elif indicators.get('bb_position', 0.5) < 0.20:
                exit_score += 1
                exit_reasons.append("BB baixo")
            
            if indicators.get('macd_bullish', False) and indicators.get('macd_histogram_rising', False):
                exit_score += 3
                exit_reasons.append("MACD virou bullish e subindo")
            elif indicators.get('macd_bullish', False):
                exit_score += 2
                exit_reasons.append("MACD virou bullish")
            
            if indicators.get('ema_trend', '') in ['bullish', 'strong_bullish']:
                if indicators.get('ema_trend') == 'strong_bullish':
                    exit_score += 3
                    exit_reasons.append("EMA forte bullish")
                else:
                    exit_score += 2
                    exit_reasons.append("EMA bullish")
            
            if indicators.get('momentum_bullish', False) and indicators.get('momentum_strong', False):
                exit_score += 3
                exit_reasons.append("Momentum forte positivo")
            elif indicators.get('momentum_bullish', False):
                exit_score += 2
                exit_reasons.append("Momentum positivo")
        
        # Score mínimo para saída REDUZIDO
        min_exit_score = 3  # Era 4
        
        if exit_score >= min_exit_score:
            confidence = min(0.50 + (exit_score * 0.08), 0.92)
            
            if exit_score >= 8:
                strength = SignalStrength.STRONG
            elif exit_score >= 5:
                strength = SignalStrength.NEUTRAL
            else:
                strength = SignalStrength.WEAK
            
            action = 'close_long' if position.side == PositionSide.LONG else 'close_short'
            reason = " | ".join(exit_reasons[:3])
            
            logger.info(f"SINAL DE SAÍDA VALIDADO: {action.upper()}")
            logger.info(f"   Score: {exit_score} pontos")
            logger.info(f"   Confiança: {confidence:.1%}")
            logger.info(f"   Razões: {reason}")
            
            return TradingSignal(
                action=action,
                strength=strength,
                confidence=confidence,
                indicators=indicators,
                timestamp=datetime.now(),
                reason=reason
            )
        
        # Não sair ainda
        logger.debug(f"Mantendo posição {position.side.value} - Score saída: {exit_score} < {min_exit_score}")
        
        return TradingSignal(
            action='hold',
            strength=SignalStrength.NEUTRAL,
            confidence=0.0,
            indicators=indicators,
            timestamp=datetime.now(),
            reason=f"Mantendo posição (score saída: {exit_score})"
        )