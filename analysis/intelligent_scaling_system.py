#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Position Scaling Inteligente
Maximiza lucros através de scaling in/out baseado em condições de mercado
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from enum import Enum

class ScalingAction(Enum):
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    HOLD = "hold"
    CLOSE_ALL = "close_all"

class IntelligentPositionScaling:
    """Sistema inteligente para scaling de posições"""
    
    def __init__(self, config):
        self.config = config
        self.scaling_history = {}
        self.position_zones = {}
        
    def analyze_scaling_opportunity(self, position: Dict, current_price: float,
                                  market_conditions: Dict, indicators: Dict) -> Dict:
        """Analisa oportunidades de scaling in/out"""
        
        scaling_analysis = {
            'action': ScalingAction.HOLD,
            'percentage': 0.0,
            'confidence': 0.0,
            'reason': '',
            'optimal_price': current_price,
            'risk_assessment': 'medium'
        }
        
        try:
            entry_price = position['entry_price']
            side = position['side']
            current_pnl = self._calculate_pnl_pct(position, current_price)
            position_age_minutes = self._get_position_age_minutes(position)
            
            # Analisa scale out (take profits parciais)
            scale_out_analysis = self._analyze_scale_out_opportunities(
                position, current_price, current_pnl, market_conditions, indicators
            )
            
            # Analisa scale in (adicionar à posição)
            scale_in_analysis = self._analyze_scale_in_opportunities(
                position, current_price, current_pnl, market_conditions, indicators
            )
            
            # Decide qual ação tomar baseado na análise
            if scale_out_analysis['score'] > scale_in_analysis['score']:
                scaling_analysis.update({
                    'action': ScalingAction.SCALE_OUT,
                    'percentage': scale_out_analysis['percentage'],
                    'confidence': scale_out_analysis['confidence'],
                    'reason': scale_out_analysis['reason'],
                    'risk_assessment': 'low'
                })
            elif scale_in_analysis['score'] > 15:  # Threshold para scale in
                scaling_analysis.update({
                    'action': ScalingAction.SCALE_IN,
                    'percentage': scale_in_analysis['percentage'],
                    'confidence': scale_in_analysis['confidence'],
                    'reason': scale_in_analysis['reason'],
                    'optimal_price': scale_in_analysis['optimal_price'],
                    'risk_assessment': scale_in_analysis['risk_level']
                })
            
            return scaling_analysis
            
        except Exception as e:
            print(f"Erro na análise de scaling: {e}")
            return scaling_analysis
    
    def _analyze_scale_out_opportunities(self, position: Dict, current_price: float,
                                       current_pnl: float, market_conditions: Dict,
                                       indicators: Dict) -> Dict:
        """Analisa oportunidades para scale out"""
        
        analysis = {'score': 0, 'percentage': 0, 'confidence': 0, 'reason': ''}
        
        side = position['side']
        
        # 1. Scale out baseado em P&L
        if current_pnl >= 0.8:  # A partir de 0.8% de lucro
            pnl_score = min(current_pnl * 8, 25)  # Max 25 pontos
            analysis['score'] += pnl_score
            
            # Determine percentage baseado no P&L
            if current_pnl >= 3.0:
                analysis['percentage'] = 0.8  # 80% da posição
                analysis['reason'] = f"Scale out 80% - grande lucro ({current_pnl:.1f}%)"
            elif current_pnl >= 2.0:
                analysis['percentage'] = 0.6  # 60% da posição
                analysis['reason'] = f"Scale out 60% - bom lucro ({current_pnl:.1f}%)"
            elif current_pnl >= 1.5:
                analysis['percentage'] = 0.4  # 40% da posição
                analysis['reason'] = f"Scale out 40% - lucro moderado ({current_pnl:.1f}%)"
            else:
                analysis['percentage'] = 0.25  # 25% da posição
                analysis['reason'] = f"Scale out 25% - lucro inicial ({current_pnl:.1f}%)"
        
        # 2. Scale out baseado em indicadores técnicos
        rsi = indicators.get('rsi', 50)
        bb_position = indicators.get('bb_position', 0.5)
        
        if side.lower() == 'long':
            # Para LONG, scale out se indicadores ficam overbought
            if rsi > 75 or bb_position > 0.85:
                analysis['score'] += 15
                analysis['reason'] += " + indicadores overbought"
            elif rsi > 70 or bb_position > 0.80:
                analysis['score'] += 10
                analysis['reason'] += " + indicadores altos"
        
        else:  # SHORT
            # Para SHORT, scale out se indicadores ficam oversold
            if rsi < 25 or bb_position < 0.15:
                analysis['score'] += 15
                analysis['reason'] += " + indicadores oversold"
            elif rsi < 30 or bb_position < 0.20:
                analysis['score'] += 10
                analysis['reason'] += " + indicadores baixos"
        
        # 3. Scale out baseado em volatilidade
        volatility = market_conditions.get('current_volatility', 2.0)
        if volatility > 4.0 and current_pnl > 1.0:
            analysis['score'] += 12
            analysis['reason'] += " + alta volatilidade"
            # Aumenta percentage em alta volatilidade
            analysis['percentage'] = min(analysis['percentage'] * 1.3, 0.9)
        
        # 4. Scale out baseado no regime de mercado
        regime = market_conditions.get('regime', 'normal')
        if regime == 'ranging' and current_pnl > 0.8:
            analysis['score'] += 10
            analysis['reason'] += " + mercado lateral"
        
        # 5. Resistência próxima (para long) ou suporte próximo (para short)
        if self._near_important_level(current_price, side, indicators):
            analysis['score'] += 8
            analysis['reason'] += " + próximo de nível importante"
        
        # Calcula confiança
        analysis['confidence'] = min(analysis['score'] / 40, 0.95)
        
        return analysis
    
    def _analyze_scale_in_opportunities(self, position: Dict, current_price: float,
                                      current_pnl: float, market_conditions: Dict,
                                      indicators: Dict) -> Dict:
        """Analisa oportunidades para scale in (adicionar à posição)"""
        
        analysis = {
            'score': 0, 'percentage': 0, 'confidence': 0, 'reason': '',
            'optimal_price': current_price, 'risk_level': 'medium'
        }
        
        side = position['side']
        entry_price = position['entry_price']
        
        # Só considera scale in se:
        # 1. Posição não está em prejuízo significativo
        # 2. Não passou muito tempo
        # 3. Condições técnicas favoráveis
        
        if current_pnl < -1.5:  # Não scale in se prejuízo > 1.5%
            return analysis
        
        position_age = self._get_position_age_minutes(position)
        if position_age > 120:  # Não scale in após 2 horas
            return analysis
        
        # 1. Scale in em pullback saudável
        if self._is_healthy_pullback(position, current_price, indicators):
            analysis['score'] += 20
            analysis['reason'] = "Pullback saudável"
            analysis['percentage'] = 0.3  # 30% adicional
            analysis['risk_level'] = 'low'
            
            # Preço ótimo um pouco melhor que o atual
            if side.lower() == 'long':
                analysis['optimal_price'] = current_price * 0.998  # 0.2% abaixo
            else:
                analysis['optimal_price'] = current_price * 1.002  # 0.2% acima
        
        # 2. Breakout confirmation
        elif self._is_breakout_confirmation(current_price, side, indicators, market_conditions):
            analysis['score'] += 25
            analysis['reason'] = "Confirmação de breakout"
            analysis['percentage'] = 0.4  # 40% adicional
            analysis['risk_level'] = 'medium'
        
        # 3. Suporte/resistência defendido
        elif self._is_level_defended(current_price, side, indicators):
            analysis['score'] += 18
            analysis['reason'] = "Nível importantes defendido"
            analysis['percentage'] = 0.35  # 35% adicional
            analysis['risk_level'] = 'low'
        
        # 4. Volume confirmation
        volume_ratio = market_conditions.get('volume_ratio', 1.0)
        if volume_ratio > 1.3:  # Volume 30% acima da média
            analysis['score'] += 8
            analysis['reason'] += " + volume forte"
        
        # 5. Trending market favor
        trend_strength = market_conditions.get('trend_strength', 0)
        if ((side.lower() == 'long' and trend_strength > 1.0) or
            (side.lower() == 'short' and trend_strength < -1.0)):
            analysis['score'] += 12
            analysis['reason'] += " + trend favorável"
        
        # Penalizações
        # Penaliza scale in se já fez muitos
        scale_count = position.get('scale_in_count', 0)
        if scale_count >= 2:
            analysis['score'] -= 15  # Penalidade por muito scaling
            analysis['risk_level'] = 'high'
        elif scale_count >= 1:
            analysis['score'] -= 8
        
        # Calcula confiança
        analysis['confidence'] = min(analysis['score'] / 30, 0.90)
        
        return analysis
    
    def _is_healthy_pullback(self, position: Dict, current_price: float, 
                           indicators: Dict) -> bool:
        """Verifica se é um pullback saudável para scale in"""
        
        side = position['side']
        entry_price = position['entry_price']
        
        # Pullback deve ser pequeno (1-3%)
        pullback_pct = abs((current_price - entry_price) / entry_price * 100)
        if pullback_pct > 3.0 or pullback_pct < 0.3:
            return False
        
        # RSI deve estar em nível bom para adicionar
        rsi = indicators.get('rsi', 50)
        
        if side.lower() == 'long':
            # Para LONG, RSI deve estar oversold mas não extremo
            if not (25 < rsi < 45):
                return False
        else:
            # Para SHORT, RSI deve estar overbought mas não extremo
            if not (55 < rsi < 75):
                return False
        
        # MACD deve mostrar divergência ou correção
        macd_hist = indicators.get('macd_histogram', 0)
        macd_rising = indicators.get('macd_histogram_rising', False)
        
        if side.lower() == 'long':
            # Para LONG, MACD deve estar se recuperando
            return macd_hist > -0.05 or macd_rising
        else:
            # Para SHORT, MACD deve estar descendo ou se recuperando para baixo
            return macd_hist < 0.05 or not macd_rising
    
    def _is_breakout_confirmation(self, current_price: float, side: str,
                                indicators: Dict, market_conditions: Dict) -> bool:
        """Verifica se é confirmação de breakout"""
        
        # Volume deve estar forte
        volume_ratio = market_conditions.get('volume_ratio', 1.0)
        if volume_ratio < 1.2:
            return False
        
        # Bollinger Bands position
        bb_position = indicators.get('bb_position', 0.5)
        
        if side.lower() == 'long':
            # Para LONG, deve estar acima da banda média e subindo
            return bb_position > 0.6 and indicators.get('momentum_bullish', False)
        else:
            # Para SHORT, deve estar abaixo da banda média e descendo
            return bb_position < 0.4 and indicators.get('momentum_bearish', False)
    
    def _is_level_defended(self, current_price: float, side: str, indicators: Dict) -> bool:
        """Verifica se nível importante foi defendido"""
        
        # Análise simplificada baseada em Bollinger Bands
        bb_position = indicators.get('bb_position', 0.5)
        rsi = indicators.get('rsi', 50)
        
        if side.lower() == 'long':
            # Para LONG, suporte defendido = BB baixo + RSI oversold se recuperando
            return (bb_position < 0.25 and rsi > 25 and 
                   indicators.get('rsi_rising', False))
        else:
            # Para SHORT, resistência defendida = BB alto + RSI overbought caindo
            return (bb_position > 0.75 and rsi < 75 and 
                   not indicators.get('rsi_rising', True))
    
    def _near_important_level(self, current_price: float, side: str, indicators: Dict) -> bool:
        """Verifica se está próximo de nível importante"""
        
        bb_position = indicators.get('bb_position', 0.5)
        
        if side.lower() == 'long':
            # Para LONG, próximo de resistência (BB upper)
            return bb_position > 0.85
        else:
            # Para SHORT, próximo de suporte (BB lower)
            return bb_position < 0.15
    
    def execute_scaling_decision(self, position: Dict, scaling_analysis: Dict,
                               current_balance: float) -> Dict:
        """Executa a decisão de scaling"""
        
        result = {
            'executed': False,
            'action': 'none',
            'amount': 0.0,
            'new_position_size': position.get('size', 0),
            'reason': '',
            'risk_check': 'passed'
        }
        
        try:
            action = scaling_analysis['action']
            percentage = scaling_analysis['percentage']
            confidence = scaling_analysis['confidence']
            
            # Verificações de segurança
            if confidence < 0.6:
                result['risk_check'] = 'low_confidence'
                result['reason'] = f"Confiança muito baixa: {confidence:.2f}"
                return result
            
            if action == ScalingAction.SCALE_OUT:
                current_size = position.get('size', 0)
                scale_out_amount = current_size * percentage
                
                # Verifica se já não fez muito scale out
                total_scaled_out = position.get('total_scaled_out', 0)
                if total_scaled_out + scale_out_amount > current_size * 0.9:  # Max 90%
                    result['risk_check'] = 'max_scale_out_reached'
                    result['reason'] = "Limite de scale out atingido"
                    return result
                
                result.update({
                    'executed': True,
                    'action': 'scale_out',
                    'amount': scale_out_amount,
                    'new_position_size': current_size - scale_out_amount,
                    'reason': scaling_analysis['reason']
                })
                
                # Atualiza posição
                position['size'] = result['new_position_size']
                position['total_scaled_out'] = total_scaled_out + scale_out_amount
                position['last_scale_out'] = datetime.now()
            
            elif action == ScalingAction.SCALE_IN:
                current_size = position.get('size', 0)
                base_size = position.get('original_size', current_size)
                
                # Calcula quanto adicionar
                scale_in_amount = base_size * percentage
                
                # Verificações de risco para scale in
                max_position_multiplier = self.config.get('risk_management', {}).get('max_position_multiplier', 2.0)
                if current_size + scale_in_amount > base_size * max_position_multiplier:
                    result['risk_check'] = 'max_position_size'
                    result['reason'] = f"Tamanho máximo da posição atingido"
                    return result
                
                # Verifica se tem saldo suficiente
                required_balance = scale_in_amount * scaling_analysis['optimal_price']
                if required_balance > current_balance * 0.3:  # Max 30% do saldo
                    result['risk_check'] = 'insufficient_balance'
                    result['reason'] = "Saldo insuficiente para scale in"
                    return result
                
                result.update({
                    'executed': True,
                    'action': 'scale_in',
                    'amount': scale_in_amount,
                    'new_position_size': current_size + scale_in_amount,
                    'reason': scaling_analysis['reason'],
                    'entry_price': scaling_analysis['optimal_price']
                })
                
                # Atualiza posição
                old_weighted_price = position['entry_price'] * current_size
                new_weighted_price = scaling_analysis['optimal_price'] * scale_in_amount
                
                position['entry_price'] = (old_weighted_price + new_weighted_price) / (current_size + scale_in_amount)
                position['size'] = result['new_position_size']
                position['scale_in_count'] = position.get('scale_in_count', 0) + 1
                position['last_scale_in'] = datetime.now()
            
            return result
            
        except Exception as e:
            result.update({
                'executed': False,
                'risk_check': 'execution_error',
                'reason': f"Erro na execução: {e}"
            })
            return result
    
    def calculate_optimal_scaling_levels(self, entry_price: float, side: str,
                                       atr: float) -> Dict:
        """Calcula níveis ótimos para scaling in/out"""
        
        levels = {
            'scale_in_levels': [],
            'scale_out_levels': [],
            'max_scale_in_distance': 0,
            'target_levels': []
        }
        
        if side.lower() == 'long':
            # Scale in levels (abaixo do preço de entrada)
            levels['scale_in_levels'] = [
                entry_price * 0.995,  # 0.5% abaixo
                entry_price * 0.985,  # 1.5% abaixo
                entry_price * 0.970   # 3.0% abaixo (máximo)
            ]
            
            # Scale out levels (acima do preço de entrada)
            levels['scale_out_levels'] = [
                entry_price * 1.012,  # 1.2% acima - 25%
                entry_price * 1.020,  # 2.0% acima - 40%
                entry_price * 1.030,  # 3.0% acima - 60%
                entry_price * 1.045   # 4.5% acima - 80%
            ]
            
            # Target final
            levels['target_levels'] = [
                entry_price * 1.035,  # Target conservador
                entry_price * 1.050,  # Target moderado
                entry_price * 1.075   # Target otimista
            ]
            
        else:  # SHORT
            # Scale in levels (acima do preço de entrada)
            levels['scale_in_levels'] = [
                entry_price * 1.005,  # 0.5% acima
                entry_price * 1.015,  # 1.5% acima
                entry_price * 1.030   # 3.0% acima (máximo)
            ]
            
            # Scale out levels (abaixo do preço de entrada)
            levels['scale_out_levels'] = [
                entry_price * 0.988,  # 1.2% abaixo - 25%
                entry_price * 0.980,  # 2.0% abaixo - 40%
                entry_price * 0.970,  # 3.0% abaixo - 60%
                entry_price * 0.955   # 4.5% abaixo - 80%
            ]
            
            # Target final
            levels['target_levels'] = [
                entry_price * 0.965,  # Target conservador
                entry_price * 0.950,  # Target moderado
                entry_price * 0.925   # Target otimista
            ]
        
        levels['max_scale_in_distance'] = 3.0  # 3% máximo para scale in
        
        return levels
    
    def get_scaling_statistics(self, position: Dict) -> Dict:
        """Retorna estatísticas de scaling da posição"""
        
        return {
            'scale_in_count': position.get('scale_in_count', 0),
            'total_scaled_out': position.get('total_scaled_out', 0),
            'original_size': position.get('original_size', position.get('size', 0)),
            'current_size': position.get('size', 0),
            'average_entry_price': position.get('entry_price', 0),
            'last_scale_in': position.get('last_scale_in'),
            'last_scale_out': position.get('last_scale_out'),
            'scaling_pnl_contribution': self._calculate_scaling_pnl(position)
        }
    
    def _calculate_scaling_pnl(self, position: Dict) -> float:
        """Calcula contribuição do scaling para o P&L"""
        # Implementação simplificada
        scale_in_count = position.get('scale_in_count', 0)
        total_scaled_out = position.get('total_scaled_out', 0)
        
        # Estimativa de contribuição (em produção seria mais preciso)
        scaling_contribution = (total_scaled_out * 0.015) - (scale_in_count * 0.005)
        return scaling_contribution
    
    def _calculate_pnl_pct(self, position: Dict, current_price: float) -> float:
        """Calcula P&L em porcentagem"""
        entry_price = position['entry_price']
        side = position['side']
        
        if side.lower() == 'long':
            return ((current_price - entry_price) / entry_price) * 100
        else:
            return ((entry_price - current_price) / entry_price) * 100
    
    def _get_position_age_minutes(self, position: Dict) -> float:
        """Calcula idade da posição em minutos"""
        entry_time = position.get('entry_time', datetime.now())
        if isinstance(entry_time, str):
            entry_time = datetime.fromisoformat(entry_time)
        
        return (datetime.now() - entry_time).total_seconds() / 60