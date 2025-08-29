#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Microstructure Analysis System
Analisa padrões internos do mercado para timing preciso e detecção de liquidez
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import deque
import statistics

class MarketMicrostructureAnalyzer:
    """Analisador de microestrutura do mercado"""
    
    def __init__(self, config):
        self.config = config
        self.tick_data_buffer = deque(maxlen=1000)
        self.order_flow_data = deque(maxlen=500)
        self.liquidity_levels = {}
        self.smart_money_indicators = {}
        
    def analyze_market_microstructure(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Análise completa da microestrutura do mercado"""
        
        microstructure_analysis = {
            'liquidity_analysis': {},
            'order_flow_analysis': {},
            'smart_money_analysis': {},
            'market_structure_health': 0,
            'optimal_execution_strategy': 'market',
            'expected_slippage': 0.0,
            'market_impact_estimate': 0.0
        }
        
        try:
            # 1. Análise de Liquidez
            liquidity_analysis = self._analyze_liquidity_conditions(df, current_price)
            microstructure_analysis['liquidity_analysis'] = liquidity_analysis
            
            # 2. Order Flow Analysis
            order_flow_analysis = self._analyze_order_flow_patterns(df)
            microstructure_analysis['order_flow_analysis'] = order_flow_analysis
            
            # 3. Smart Money Detection
            smart_money_analysis = self._detect_smart_money_activity(df)
            microstructure_analysis['smart_money_analysis'] = smart_money_analysis
            
            # 4. Market Structure Health Score
            health_score = self._calculate_market_health_score(
                liquidity_analysis, order_flow_analysis, smart_money_analysis
            )
            microstructure_analysis['market_structure_health'] = health_score
            
            # 5. Optimal Execution Strategy
            execution_strategy = self._determine_optimal_execution(
                liquidity_analysis, order_flow_analysis, health_score
            )
            microstructure_analysis.update(execution_strategy)
            
            return microstructure_analysis
            
        except Exception as e:
            print(f"Erro na análise de microestrutura: {e}")
            return microstructure_analysis
    
    def _analyze_liquidity_conditions(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Analisa condições de liquidez do mercado"""
        
        analysis = {
            'liquidity_score': 50,  # 0-100
            'spread_estimate': 0.0,
            'depth_estimate': 'medium',
            'liquidity_zones': [],
            'fragmentation_level': 'low',
            'optimal_order_size': 0.0
        }
        
        if len(df) < 20:
            return analysis
        
        try:
            # 1. Spread Analysis (aproximado via high-low)
            recent_spreads = []
            for i in range(-20, 0):
                if abs(i) <= len(df):
                    candle = df.iloc[i]
                    spread_pct = ((candle['high'] - candle['low']) / candle['close']) * 100
                    recent_spreads.append(spread_pct)
            
            avg_spread = np.mean(recent_spreads) if recent_spreads else 0.1
            analysis['spread_estimate'] = avg_spread
            
            # 2. Volume-based Liquidity Analysis
            recent_volume = df['volume'].iloc[-10:].mean()
            historical_volume = df['volume'].mean()
            volume_ratio = recent_volume / historical_volume if historical_volume > 0 else 1.0
            
            # 3. Liquidity Score baseado em volume e spread
            volume_score = min(volume_ratio * 30, 50)  # Max 50 pontos
            spread_score = max(50 - (avg_spread * 10), 0)  # Penaliza spreads largos
            
            analysis['liquidity_score'] = min(volume_score + spread_score, 100)
            
            # 4. Depth Estimate
            if analysis['liquidity_score'] > 75:
                analysis['depth_estimate'] = 'deep'
            elif analysis['liquidity_score'] > 45:
                analysis['depth_estimate'] = 'medium'
            else:
                analysis['depth_estimate'] = 'shallow'
            
            # 5. Liquidity Zones (baseado em volume clusters)
            liquidity_zones = self._identify_liquidity_zones(df, current_price)
            analysis['liquidity_zones'] = liquidity_zones
            
            # 6. Optimal Order Size
            analysis['optimal_order_size'] = self._calculate_optimal_order_size(
                recent_volume, analysis['liquidity_score']
            )
            
            return analysis
            
        except Exception as e:
            print(f"Erro na análise de liquidez: {e}")
            return analysis
    
    def _analyze_order_flow_patterns(self, df: pd.DataFrame) -> Dict:
        """Analisa padrões de order flow"""
        
        analysis = {
            'buy_pressure': 50,  # 0-100
            'sell_pressure': 50,  # 0-100
            'flow_imbalance': 0,  # -100 a +100
            'accumulation_distribution': 0,
            'buying_climax': False,
            'selling_climax': False,
            'flow_trend': 'neutral'
        }
        
        if len(df) < 10:
            return analysis
        
        try:
            # 1. Buy/Sell Pressure Analysis (baseado em close vs range)
            buy_strength_scores = []
            sell_strength_scores = []
            
            for i in range(-10, 0):
                if abs(i) <= len(df):
                    candle = df.iloc[i]
                    candle_range = candle['high'] - candle['low']
                    
                    if candle_range > 0:
                        # Close position na range (0 = low, 1 = high)
                        close_position = (candle['close'] - candle['low']) / candle_range
                        volume_weight = candle['volume']
                        
                        # Buy strength = close alto na range + volume
                        buy_strength = close_position * volume_weight
                        sell_strength = (1 - close_position) * volume_weight
                        
                        buy_strength_scores.append(buy_strength)
                        sell_strength_scores.append(sell_strength)
            
            # 2. Calcula pressões
            total_buy_strength = sum(buy_strength_scores)
            total_sell_strength = sum(sell_strength_scores)
            total_strength = total_buy_strength + total_sell_strength
            
            if total_strength > 0:
                analysis['buy_pressure'] = (total_buy_strength / total_strength) * 100
                analysis['sell_pressure'] = (total_sell_strength / total_strength) * 100
                analysis['flow_imbalance'] = analysis['buy_pressure'] - 50
            
            # 3. Accumulation/Distribution Line
            ad_line = 0
            for i in range(-20, 0):
                if abs(i) <= len(df):
                    candle = df.iloc[i]
                    candle_range = candle['high'] - candle['low']
                    
                    if candle_range > 0:
                        money_flow_multiplier = ((candle['close'] - candle['low']) - 
                                               (candle['high'] - candle['close'])) / candle_range
                        money_flow_volume = money_flow_multiplier * candle['volume']
                        ad_line += money_flow_volume
            
            analysis['accumulation_distribution'] = ad_line
            
            # 4. Climax Detection
            recent_volume = df['volume'].iloc[-3:].mean()
            avg_volume = df['volume'].iloc[-20:].mean()
            volume_spike = recent_volume > avg_volume * 2.0
            
            if volume_spike and analysis['buy_pressure'] > 80:
                analysis['buying_climax'] = True
            elif volume_spike and analysis['sell_pressure'] > 80:
                analysis['selling_climax'] = True
            
            # 5. Flow Trend
            if analysis['flow_imbalance'] > 15:
                analysis['flow_trend'] = 'bullish'
            elif analysis['flow_imbalance'] < -15:
                analysis['flow_trend'] = 'bearish'
            else:
                analysis['flow_trend'] = 'neutral'
            
            return analysis
            
        except Exception as e:
            print(f"Erro na análise de order flow: {e}")
            return analysis
    
    def _detect_smart_money_activity(self, df: pd.DataFrame) -> Dict:
        """Detecta atividade de smart money"""
        
        analysis = {
            'smart_money_direction': 'neutral',
            'institutional_activity_score': 0,  # 0-100
            'dark_pool_indicators': [],
            'large_order_detection': False,
            'unusual_volume_patterns': [],
            'smart_money_confidence': 0.0
        }
        
        if len(df) < 30:
            return analysis
        
        try:
            # 1. Unusual Volume Patterns
            volume_ma_20 = df['volume'].rolling(20).mean()
            volume_std_20 = df['volume'].rolling(20).std()
            
            unusual_volume_events = []
            for i in range(-10, 0):
                if abs(i) <= len(df):
                    idx = len(df) + i
                    current_vol = df['volume'].iloc[i]
                    expected_vol = volume_ma_20.iloc[i]
                    vol_std = volume_std_20.iloc[i]
                    
                    if current_vol > expected_vol + (2 * vol_std):
                        price_move = abs(df['close'].iloc[i] - df['open'].iloc[i])
                        price_move_pct = (price_move / df['open'].iloc[i]) * 100
                        
                        unusual_volume_events.append({
                            'index': idx,
                            'volume_ratio': current_vol / expected_vol,
                            'price_move_pct': price_move_pct,
                            'volume_to_move_ratio': current_vol / max(price_move_pct, 0.1)
                        })
            
            analysis['unusual_volume_patterns'] = unusual_volume_events
            
            # 2. Large Order Detection (volume spikes with small price moves)
            for event in unusual_volume_events:
                if event['volume_to_move_ratio'] > 1000:  # High volume, small move
                    analysis['large_order_detection'] = True
                    analysis['institutional_activity_score'] += 25
                    break
            
            # 3. Dark Pool Indicators
            # Procura por padrões onde preço não reflete o volume
            dark_pool_signals = []
            
            for i in range(-5, 0):
                if abs(i) <= len(df):
                    candle = df.iloc[i]
                    volume = candle['volume']
                    price_range = candle['high'] - candle['low']
                    price_range_pct = (price_range / candle['close']) * 100
                    
                    # Volume alto mas range pequeno = possível dark pool
                    if volume > volume_ma_20.iloc[i] * 1.5 and price_range_pct < 0.5:
                        dark_pool_signals.append({
                            'type': 'low_volatility_high_volume',
                            'confidence': 0.6
                        })
            
            analysis['dark_pool_indicators'] = dark_pool_signals
            if dark_pool_signals:
                analysis['institutional_activity_score'] += 15
            
            # 4. Smart Money Direction
            # Baseado na correlação inversa entre volume e volatilidade
            recent_data = df.iloc[-10:]
            
            # Volume-weighted price moves
            volume_weighted_moves = []
            for _, candle in recent_data.iterrows():
                price_move = candle['close'] - candle['open']
                move_pct = (price_move / candle['open']) * 100
                weighted_move = move_pct * candle['volume']
                volume_weighted_moves.append(weighted_move)
            
            net_flow = sum(volume_weighted_moves)
            if net_flow > 0:
                analysis['smart_money_direction'] = 'bullish'
                analysis['institutional_activity_score'] += 10
            elif net_flow < 0:
                analysis['smart_money_direction'] = 'bearish'
                analysis['institutional_activity_score'] += 10
            
            # 5. Confidence Score
            analysis['smart_money_confidence'] = min(analysis['institutional_activity_score'] / 50, 1.0)
            
            return analysis
            
        except Exception as e:
            print(f"Erro na detecção de smart money: {e}")
            return analysis
    
    def _identify_liquidity_zones(self, df: pd.DataFrame, current_price: float) -> List[Dict]:
        """Identifica zonas de liquidez baseado em volume"""
        
        zones = []
        
        try:
            # Volume Profile simplificado
            price_volume_data = []
            
            for _, candle in df.iloc[-50:].iterrows():  # Últimas 50 velas
                typical_price = (candle['high'] + candle['low'] + candle['close']) / 3
                price_volume_data.append({
                    'price': typical_price,
                    'volume': candle['volume']
                })
            
            # Agrupa por níveis de preço
            price_levels = {}
            price_step = current_price * 0.002  # 0.2% steps
            
            for data_point in price_volume_data:
                level = round(data_point['price'] / price_step) * price_step
                if level not in price_levels:
                    price_levels[level] = 0
                price_levels[level] += data_point['volume']
            
            # Identifica top 5 zonas de liquidez
            sorted_levels = sorted(price_levels.items(), key=lambda x: x[1], reverse=True)
            
            for i, (price_level, volume) in enumerate(sorted_levels[:5]):
                distance_pct = abs(price_level - current_price) / current_price * 100
                
                zones.append({
                    'price_level': price_level,
                    'volume': volume,
                    'distance_pct': distance_pct,
                    'importance': 'high' if i < 2 else 'medium' if i < 4 else 'low',
                    'type': 'resistance' if price_level > current_price else 'support'
                })
            
        except Exception as e:
            print(f"Erro ao identificar zonas de liquidez: {e}")
        
        return zones
    
    def _calculate_market_health_score(self, liquidity_analysis: Dict,
                                     order_flow_analysis: Dict,
                                     smart_money_analysis: Dict) -> int:
        """Calcula score de saúde do mercado (0-100)"""
        
        health_score = 0
        
        # Componente de liquidez (40% do score)
        liquidity_score = liquidity_analysis.get('liquidity_score', 50)
        health_score += (liquidity_score * 0.4)
        
        # Componente de order flow (35% do score)
        flow_imbalance = abs(order_flow_analysis.get('flow_imbalance', 0))
        flow_score = 100 - min(flow_imbalance * 2, 100)  # Penaliza desequilíbrios
        health_score += (flow_score * 0.35)
        
        # Componente smart money (25% do score)
        institutional_score = smart_money_analysis.get('institutional_activity_score', 0)
        # Smart money atividade moderada é saudável
        if 10 <= institutional_score <= 40:
            sm_health_score = 100
        elif institutional_score > 40:
            sm_health_score = max(100 - (institutional_score - 40) * 2, 0)
        else:
            sm_health_score = institutional_score * 10
        
        health_score += (sm_health_score * 0.25)
        
        return min(max(int(health_score), 0), 100)
    
    def _determine_optimal_execution(self, liquidity_analysis: Dict,
                                   order_flow_analysis: Dict,
                                   health_score: int) -> Dict:
        """Determina estratégia ótima de execução"""
        
        execution_strategy = {
            'optimal_execution_strategy': 'market',
            'expected_slippage': 0.05,  # %
            'market_impact_estimate': 0.02,  # %
            'recommended_order_split': 1,
            'execution_urgency': 'normal'
        }
        
        try:
            liquidity_score = liquidity_analysis.get('liquidity_score', 50)
            spread_estimate = liquidity_analysis.get('spread_estimate', 0.1)
            flow_imbalance = abs(order_flow_analysis.get('flow_imbalance', 0))
            
            # Determina estratégia baseado nas condições
            if health_score > 75 and liquidity_score > 70:
                # Mercado saudável com boa liquidez
                execution_strategy.update({
                    'optimal_execution_strategy': 'limit_aggressive',
                    'expected_slippage': spread_estimate * 0.5,
                    'market_impact_estimate': 0.01,
                    'execution_urgency': 'normal'
                })
            elif health_score > 50 and liquidity_score > 50:
                # Condições moderadas
                execution_strategy.update({
                    'optimal_execution_strategy': 'smart_limit',
                    'expected_slippage': spread_estimate * 0.8,
                    'market_impact_estimate': 0.02,
                    'execution_urgency': 'normal'
                })
            elif health_score < 30 or liquidity_score < 30:
                # Condições ruins
                execution_strategy.update({
                    'optimal_execution_strategy': 'twap',
                    'expected_slippage': spread_estimate * 1.5,
                    'market_impact_estimate': 0.05,
                    'recommended_order_split': 3,
                    'execution_urgency': 'patient'
                })
            else:
                # Condições incertas
                execution_strategy.update({
                    'optimal_execution_strategy': 'market',
                    'expected_slippage': spread_estimate,
                    'market_impact_estimate': 0.03,
                    'execution_urgency': 'normal'
                })
            
            # Ajustes para desequilíbrio de fluxo
            if flow_imbalance > 30:
                execution_strategy['execution_urgency'] = 'urgent'
                execution_strategy['expected_slippage'] *= 1.3
            
        except Exception as e:
            print(f"Erro ao determinar execução ótima: {e}")
        
        return execution_strategy
    
    def _calculate_optimal_order_size(self, recent_volume: float, liquidity_score: int) -> float:
        """Calcula tamanho ótimo da ordem baseado na liquidez"""
        
        try:
            # Tamanho base como % do volume médio
            if liquidity_score > 75:
                base_percentage = 0.05  # 5% do volume
            elif liquidity_score > 50:
                base_percentage = 0.03  # 3% do volume
            else:
                base_percentage = 0.02  # 2% do volume
            
            optimal_size = recent_volume * base_percentage
            
            # Limites mínimos e máximos
            min_size = recent_volume * 0.01  # 1% mínimo
            max_size = recent_volume * 0.1   # 10% máximo
            
            return max(min(optimal_size, max_size), min_size)
            
        except Exception as e:
            print(f"Erro ao calcular tamanho ótimo: {e}")
            return recent_volume * 0.02
    
    def get_execution_recommendations(self, microstructure_analysis: Dict,
                                    order_size: float, urgency: str = 'normal') -> Dict:
        """Fornece recomendações específicas de execução"""
        
        recommendations = {
            'strategy': 'market',
            'split_into_parts': 1,
            'time_interval_seconds': 0,
            'price_improvement_target': 0.0,
            'risk_warnings': [],
            'execution_score': 50
        }
        
        try:
            health_score = microstructure_analysis.get('market_structure_health', 50)
            liquidity_analysis = microstructure_analysis.get('liquidity_analysis', {})
            order_flow = microstructure_analysis.get('order_flow_analysis', {})
            
            optimal_strategy = microstructure_analysis.get('optimal_execution_strategy', 'market')
            
            # Configurações por estratégia
            if optimal_strategy == 'limit_aggressive':
                recommendations.update({
                    'strategy': 'limit_aggressive',
                    'price_improvement_target': 0.02,  # Tenta melhorar 0.02%
                    'execution_score': 80
                })
            
            elif optimal_strategy == 'smart_limit':
                recommendations.update({
                    'strategy': 'smart_limit',
                    'price_improvement_target': 0.01,
                    'execution_score': 70
                })
            
            elif optimal_strategy == 'twap':
                # Divide ordem em partes menores
                optimal_size = liquidity_analysis.get('optimal_order_size', order_size)
                if order_size > optimal_size:
                    split_parts = min(int(order_size / optimal_size), 5)
                    recommendations.update({
                        'strategy': 'twap',
                        'split_into_parts': split_parts,
                        'time_interval_seconds': 30,
                        'execution_score': 60
                    })
            
            # Warnings baseados na análise
            if health_score < 40:
                recommendations['risk_warnings'].append("Baixa saúde do mercado - considere atrasar execução")
            
            if liquidity_analysis.get('liquidity_score', 50) < 30:
                recommendations['risk_warnings'].append("Baixa liquidez - esperar alto slippage")
            
            flow_imbalance = abs(order_flow.get('flow_imbalance', 0))
            if flow_imbalance > 40:
                recommendations['risk_warnings'].append("Alto desequilíbrio de order flow")
            
            # Ajustes por urgência
            if urgency == 'urgent':
                recommendations['strategy'] = 'market'
                recommendations['split_into_parts'] = 1
                recommendations['execution_score'] = max(recommendations['execution_score'] - 20, 20)
            elif urgency == 'patient':
                if recommendations['split_into_parts'] == 1:
                    recommendations['split_into_parts'] = 2
                recommendations['time_interval_seconds'] = max(recommendations['time_interval_seconds'], 60)
            
        except Exception as e:
            print(f"Erro nas recomendações de execução: {e}")
        
        return recommendations
    
    def track_execution_performance(self, executed_price: float, expected_price: float,
                                  strategy_used: str, microstructure_state: Dict):
        """Rastreia performance das execuções para aprendizado"""
        
        try:
            slippage_pct = abs(executed_price - expected_price) / expected_price * 100
            expected_slippage = microstructure_state.get('expected_slippage', 0.05)
            
            performance_data = {
                'timestamp': datetime.now(),
                'strategy_used': strategy_used,
                'actual_slippage': slippage_pct,
                'expected_slippage': expected_slippage,
                'slippage_error': slippage_pct - expected_slippage,
                'market_health_score': microstructure_state.get('market_structure_health', 50),
                'liquidity_score': microstructure_state.get('liquidity_analysis', {}).get('liquidity_score', 50)
            }
            
            # Em implementação real, salvar para análise posterior
            # self.execution_history.append(performance_data)
            
        except Exception as e:
            print(f"Erro no rastreamento de performance: {e}")
    
    def get_liquidity_forecast(self, df: pd.DataFrame, forecast_minutes: int = 30) -> Dict:
        """Prevê condições de liquidez para os próximos minutos"""
        
        forecast = {
            'expected_liquidity_trend': 'stable',
            'expected_volatility_change': 0.0,
            'risk_events': [],
            'optimal_trade_windows': []
        }
        
        try:
            if len(df) < 50:
                return forecast
            
            # Análise de padrões de volume por horário
            current_hour = datetime.now().hour
            
            # Volume patterns (simplificado)
            hourly_volume_pattern = {
                # Hours UTC with typical relative volume
                0: 0.6, 1: 0.4, 2: 0.3, 3: 0.3, 4: 0.4,  # Baixa liquidez
                5: 0.6, 6: 0.8, 7: 1.0, 8: 1.3, 9: 1.5,  # Aumentando
                10: 1.4, 11: 1.3, 12: 1.2, 13: 1.3, 14: 1.4,  # Alta
                15: 1.3, 16: 1.2, 17: 1.0, 18: 0.9, 19: 0.8,  # Diminuindo
                20: 0.7, 21: 0.6, 22: 0.5, 23: 0.5  # Baixa
            }
            
            current_volume_factor = hourly_volume_pattern.get(current_hour, 1.0)
            next_hour_factor = hourly_volume_pattern.get((current_hour + 1) % 24, 1.0)
            
            trend_factor = (next_hour_factor - current_volume_factor) / current_volume_factor
            
            if trend_factor > 0.2:
                forecast['expected_liquidity_trend'] = 'improving'
            elif trend_factor < -0.2:
                forecast['expected_liquidity_trend'] = 'deteriorating'
            else:
                forecast['expected_liquidity_trend'] = 'stable'
            
            # Identifica janelas ótimas de trade
            for i in range(forecast_minutes):
                future_hour = (current_hour + (i // 60)) % 24
                volume_factor = hourly_volume_pattern.get(future_hour, 1.0)
                
                if volume_factor > 1.2:  # Alta liquidez
                    window_start = datetime.now() + timedelta(minutes=i)
                    forecast['optimal_trade_windows'].append({
                        'start_time': window_start,
                        'duration_minutes': min(60 - (i % 60), forecast_minutes - i),
                        'expected_liquidity': 'high'
                    })
            
            # Risk events (simplificado)
            # Em produção, integraria com calendário econômico
            risk_hours = [8, 9, 13, 14, 15]  # Horários típicos de volatilidade
            if current_hour in risk_hours:
                forecast['risk_events'].append({
                    'type': 'high_volatility_hour',
                    'impact': 'medium',
                    'recommendation': 'increase_caution'
                })
            
        except Exception as e:
            print(f"Erro na previsão de liquidez: {e}")
        
        return forecast