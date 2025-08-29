#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Avançado de Entrada - Volume Profile + Order Flow
Melhora significativamente a precisão dos pontos de entrada
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class AdvancedEntrySystem:
    """Sistema avançado para otimizar pontos de entrada"""
    
    def __init__(self, config):
        self.config = config
        self.volume_levels = {}
        self.order_flow_data = {}
        
    def analyze_entry_quality(self, symbol: str, df: pd.DataFrame, 
                             signal_action: str, current_price: float) -> Dict:
        """Analisa qualidade do ponto de entrada"""
        
        entry_analysis = {
            'quality_score': 0,
            'risk_reward_ratio': 0,
            'volume_confirmation': False,
            'support_resistance_proximity': 0,
            'order_flow_bias': 'neutral',
            'optimal_entry_price': current_price,
            'entry_timing': 'immediate'
        }
        
        try:
            # 1. Análise de Volume Profile
            volume_analysis = self._analyze_volume_profile(df, current_price)
            entry_analysis['volume_confirmation'] = volume_analysis['strong_level']
            entry_analysis['quality_score'] += volume_analysis['score']
            
            # 2. Proximidade de Suporte/Resistência
            sr_analysis = self._analyze_support_resistance_proximity(df, current_price, signal_action)
            entry_analysis['support_resistance_proximity'] = sr_analysis['proximity_score']
            entry_analysis['quality_score'] += sr_analysis['score']
            
            # 3. Order Flow Analysis
            flow_analysis = self._analyze_order_flow(df, signal_action)
            entry_analysis['order_flow_bias'] = flow_analysis['bias']
            entry_analysis['quality_score'] += flow_analysis['score']
            
            # 4. Risk-Reward Calculation
            rr_analysis = self._calculate_risk_reward(df, current_price, signal_action)
            entry_analysis['risk_reward_ratio'] = rr_analysis['ratio']
            entry_analysis['quality_score'] += rr_analysis['score']
            
            # 5. Entry Timing Optimization
            timing_analysis = self._optimize_entry_timing(df, signal_action, current_price)
            entry_analysis['entry_timing'] = timing_analysis['timing']
            entry_analysis['optimal_entry_price'] = timing_analysis['optimal_price']
            entry_analysis['quality_score'] += timing_analysis['score']
            
            # Normaliza score final (0-100)
            entry_analysis['quality_score'] = min(max(entry_analysis['quality_score'], 0), 100)
            
            return entry_analysis
            
        except Exception as e:
            print(f"Erro na análise de entrada: {e}")
            return entry_analysis
    
    def _analyze_volume_profile(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Analisa volume profile para identificar níveis importantes"""
        
        if len(df) < 50:
            return {'strong_level': False, 'score': 0}
        
        # Calcula VWAP
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['volume_price'] = df['typical_price'] * df['volume']
        
        # VWAP rolling 50 períodos
        vwap_50 = df['volume_price'].rolling(50).sum() / df['volume'].rolling(50).sum()
        current_vwap = vwap_50.iloc[-1]
        
        # Calcula desvio padrão do VWAP
        price_variance = ((df['typical_price'] - vwap_50) ** 2 * df['volume']).rolling(50).sum()
        vwap_std = np.sqrt(price_variance.iloc[-1] / df['volume'].rolling(50).sum().iloc[-1])
        
        # Identifica zonas de alto volume
        volume_threshold = df['volume'].quantile(0.8)
        high_volume_zones = df[df['volume'] > volume_threshold]
        
        score = 0
        strong_level = False
        
        # Score baseado na proximidade do VWAP
        vwap_distance = abs(current_price - current_vwap) / current_vwap
        if vwap_distance < 0.002:  # Muito próximo do VWAP
            score += 15
            strong_level = True
        elif vwap_distance < 0.005:  # Próximo do VWAP
            score += 10
        
        # Score baseado em zonas de alto volume
        for _, zone in high_volume_zones.iloc[-20:].iterrows():  # Últimas 20 zonas
            zone_distance = abs(current_price - zone['typical_price']) / current_price
            if zone_distance < 0.003:  # Muito próximo de zona de volume
                score += 12
                strong_level = True
                break
            elif zone_distance < 0.007:  # Próximo de zona de volume
                score += 6
        
        # Score baseado na banda VWAP
        if current_vwap - vwap_std <= current_price <= current_vwap + vwap_std:
            score += 8
        
        return {
            'strong_level': strong_level,
            'score': min(score, 25),  # Max 25 pontos
            'vwap': current_vwap,
            'vwap_distance_pct': vwap_distance * 100
        }
    
    def _analyze_support_resistance_proximity(self, df: pd.DataFrame, 
                                            current_price: float, signal_action: str) -> Dict:
        """Analisa proximidade de suporte/resistência"""
        
        if len(df) < 30:
            return {'proximity_score': 0, 'score': 0}
        
        # Identifica pivots
        window = 5
        df['pivot_high'] = df['high'].rolling(window*2+1, center=True).max() == df['high']
        df['pivot_low'] = df['low'].rolling(window*2+1, center=True).min() == df['low']
        
        # Extrai níveis de suporte e resistência
        resistance_levels = df[df['pivot_high']]['high'].iloc[-10:].tolist()
        support_levels = df[df['pivot_low']]['low'].iloc[-10:].tolist()
        
        score = 0
        proximity_score = 0
        
        if signal_action == 'long':
            # Para LONG, queremos estar próximo de suporte
            for support in support_levels:
                distance = abs(current_price - support) / current_price
                if distance < 0.005:  # Muito próximo (0.5%)
                    score += 20
                    proximity_score = 90
                    break
                elif distance < 0.01:  # Próximo (1%)
                    score += 12
                    proximity_score = max(proximity_score, 70)
                elif distance < 0.02:  # Relativamente próximo (2%)
                    score += 6
                    proximity_score = max(proximity_score, 50)
        
        elif signal_action == 'short':
            # Para SHORT, queremos estar próximo de resistência
            for resistance in resistance_levels:
                distance = abs(current_price - resistance) / current_price
                if distance < 0.005:  # Muito próximo (0.5%)
                    score += 20
                    proximity_score = 90
                    break
                elif distance < 0.01:  # Próximo (1%)
                    score += 12
                    proximity_score = max(proximity_score, 70)
                elif distance < 0.02:  # Relativamente próximo (2%)
                    score += 6
                    proximity_score = max(proximity_score, 50)
        
        return {
            'proximity_score': proximity_score,
            'score': min(score, 20),  # Max 20 pontos
            'nearest_support': min(support_levels) if support_levels else 0,
            'nearest_resistance': max(resistance_levels) if resistance_levels else 0
        }
    
    def _analyze_order_flow(self, df: pd.DataFrame, signal_action: str) -> Dict:
        """Analisa order flow para confirmar direção"""
        
        if len(df) < 10:
            return {'bias': 'neutral', 'score': 0}
        
        # Análise simples de order flow baseada em closes vs ranges
        recent_bars = df.iloc[-10:]
        
        bullish_bars = 0
        bearish_bars = 0
        
        for _, bar in recent_bars.iterrows():
            bar_range = bar['high'] - bar['low']
            if bar_range > 0:
                close_position = (bar['close'] - bar['low']) / bar_range
                
                # Close no terço superior = bullish
                if close_position > 0.66:
                    bullish_bars += 1
                # Close no terço inferior = bearish
                elif close_position < 0.33:
                    bearish_bars += 1
        
        # Determina bias
        if bullish_bars > bearish_bars + 2:
            bias = 'bullish'
        elif bearish_bars > bullish_bars + 2:
            bias = 'bearish'
        else:
            bias = 'neutral'
        
        # Score baseado no alinhamento com o sinal
        score = 0
        if (signal_action == 'long' and bias == 'bullish') or \
           (signal_action == 'short' and bias == 'bearish'):
            score = 15  # Alinhado
        elif bias == 'neutral':
            score = 5   # Neutro
        else:
            score = -10  # Contra o bias (penalidade)
        
        return {
            'bias': bias,
            'score': max(min(score, 15), -10),  # Entre -10 e 15 pontos
            'bullish_bars': bullish_bars,
            'bearish_bars': bearish_bars
        }
    
    def _calculate_risk_reward(self, df: pd.DataFrame, current_price: float, 
                             signal_action: str) -> Dict:
        """Calcula risk-reward ratio do trade"""
        
        if len(df) < 20:
            return {'ratio': 1.0, 'score': 0}
        
        # Estima stop loss baseado em ATR
        atr_14 = self._calculate_atr(df, 14)
        
        # Estima target baseado em resistência/suporte próximo
        if signal_action == 'long':
            # Stop loss abaixo do low recente
            recent_low = df['low'].iloc[-10:].min()
            estimated_stop = min(recent_low * 0.998, current_price - (atr_14 * 1.5))
            
            # Target na resistência próxima
            resistance_levels = df['high'].rolling(10).max().iloc[-20:]
            potential_target = resistance_levels[resistance_levels > current_price * 1.01].min()
            if pd.isna(potential_target):
                potential_target = current_price * 1.025  # 2.5% default
            
        else:  # short
            # Stop loss acima do high recente
            recent_high = df['high'].iloc[-10:].max()
            estimated_stop = max(recent_high * 1.002, current_price + (atr_14 * 1.5))
            
            # Target no suporte próximo
            support_levels = df['low'].rolling(10).min().iloc[-20:]
            potential_target = support_levels[support_levels < current_price * 0.99].max()
            if pd.isna(potential_target):
                potential_target = current_price * 0.975  # 2.5% default
        
        # Calcula risk-reward
        risk = abs(current_price - estimated_stop) / current_price * 100
        reward = abs(potential_target - current_price) / current_price * 100
        
        if risk > 0:
            rr_ratio = reward / risk
        else:
            rr_ratio = 1.0
        
        # Score baseado no R:R
        score = 0
        if rr_ratio >= 3.0:
            score = 25  # Excelente R:R
        elif rr_ratio >= 2.0:
            score = 20  # Bom R:R
        elif rr_ratio >= 1.5:
            score = 15  # Aceitável R:R
        elif rr_ratio >= 1.0:
            score = 5   # R:R neutro
        else:
            score = -15  # R:R ruim (penalidade)
        
        return {
            'ratio': round(rr_ratio, 2),
            'score': max(min(score, 25), -15),  # Entre -15 e 25 pontos
            'estimated_stop': estimated_stop,
            'potential_target': potential_target,
            'risk_pct': round(risk, 2),
            'reward_pct': round(reward, 2)
        }
    
    def _optimize_entry_timing(self, df: pd.DataFrame, signal_action: str, 
                             current_price: float) -> Dict:
        """Otimiza timing de entrada"""
        
        if len(df) < 5:
            return {'timing': 'immediate', 'optimal_price': current_price, 'score': 0}
        
        # Analisa momentum de curto prazo
        recent_closes = df['close'].iloc[-5:].values
        recent_volumes = df['volume'].iloc[-5:].values
        
        # Verifica se está em pullback saudável
        momentum_score = 0
        timing = 'immediate'
        optimal_price = current_price
        
        # Para LONG
        if signal_action == 'long':
            # Verifica se preço está puxando back após movimento up
            if len(recent_closes) >= 3:
                if (recent_closes[-3] < recent_closes[-2] > recent_closes[-1] and
                    recent_closes[-1] > recent_closes[-3]):  # Pullback saudável
                    momentum_score += 10
                    timing = 'on_pullback'
                    # Entrada um pouco abaixo do preço atual
                    optimal_price = current_price * 0.999
        
        # Para SHORT  
        elif signal_action == 'short':
            # Verifica se preço está fazendo retrace após movimento down
            if len(recent_closes) >= 3:
                if (recent_closes[-3] > recent_closes[-2] < recent_closes[-1] and
                    recent_closes[-1] < recent_closes[-3]):  # Retrace saudável
                    momentum_score += 10
                    timing = 'on_retrace'
                    # Entrada um pouco acima do preço atual
                    optimal_price = current_price * 1.001
        
        # Verifica volume confirming
        avg_volume = np.mean(recent_volumes[:-1])
        current_volume = recent_volumes[-1]
        
        if current_volume > avg_volume * 1.2:  # Volume forte
            momentum_score += 8
        elif current_volume < avg_volume * 0.7:  # Volume fraco
            momentum_score -= 5
            timing = 'wait_for_volume'
        
        return {
            'timing': timing,
            'optimal_price': round(optimal_price, 2),
            'score': max(min(momentum_score, 15), -5),  # Entre -5 e 15 pontos
            'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> float:
        """Calcula Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        return true_range.rolling(period).mean().iloc[-1]
    
    def should_enter_now(self, entry_analysis: Dict, min_quality_score: float = 60) -> Tuple[bool, str]:
        """Determina se deve entrar agora baseado na análise"""
        
        quality_score = entry_analysis['quality_score']
        timing = entry_analysis['entry_timing']
        rr_ratio = entry_analysis['risk_reward_ratio']
        
        # Critérios para entrada
        if quality_score < min_quality_score:
            return False, f"Qualidade insuficiente ({quality_score:.1f} < {min_quality_score})"
        
        if rr_ratio < 1.5:
            return False, f"Risk-Reward ruim ({rr_ratio:.1f}:1)"
        
        if timing == 'wait_for_volume':
            return False, "Aguardando confirmação de volume"
        
        return True, f"Entrada aprovada (Quality: {quality_score:.1f}, R:R: {rr_ratio:.1f}:1)"
    
    def get_optimal_entry_size(self, entry_analysis: Dict, base_size: float) -> float:
        """Calcula tamanho ótimo da posição baseado na qualidade"""
        
        quality_score = entry_analysis['quality_score']
        rr_ratio = entry_analysis['risk_reward_ratio']
        
        # Multiplicador baseado na qualidade (0.5x a 1.5x)
        quality_multiplier = 0.5 + (quality_score / 100)
        
        # Multiplicador baseado no R:R (0.8x a 1.3x)
        rr_multiplier = min(0.8 + (rr_ratio - 1) * 0.2, 1.3)
        
        # Tamanho final
        optimal_size = base_size * quality_multiplier * rr_multiplier
        
        # Limites de segurança
        return max(min(optimal_size, base_size * 1.8), base_size * 0.6)