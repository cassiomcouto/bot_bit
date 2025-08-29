import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
from analysis.technical_analysis import TechnicalAnalysis
from analysis.regime_detection import RegimeDetector, MarketRegime

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    def __init__(self, config):
        self.config = config
        self.ta = TechnicalAnalysis(config)
        self.regime_detector = RegimeDetector(config)
        self.last_analysis_time = None
        self.last_trade_time = None
        self.consecutive_losses = 0
        
    def should_analyze(self) -> bool:
        """Verifica se deve fazer nova análise - MAIS FREQUENTE"""
        if self.last_analysis_time is None:
            return True
        
        # Intervalo reduzido para análise mais frequente
        interval = self.config.get('strategy', {}).get('analysis_interval_seconds', 45)  # Era 60
        time_since = (datetime.now() - self.last_analysis_time).total_seconds()
        
        return time_since >= interval
    
    def should_trade_now(self, current_volatility: float = 2.0) -> tuple[bool, str]:
        """Verifica se condições são favoráveis para trading"""
        
        # Verifica cooldown entre trades
        if self.last_trade_time:
            cooldown = self.config.get('strategy', {}).get('cooldown_between_trades_seconds', 180)  # Era 300
            time_since_trade = (datetime.now() - self.last_trade_time).total_seconds()
            
            if time_since_trade < cooldown:
                remaining = cooldown - time_since_trade
                return False, f"Cooldown ativo ({remaining:.0f}s restantes)"
        
        # Evita trading em volatilidade muito baixa
        min_volatility = self.config.get('technical_analysis', {}).get('volatility', {}).get('volatility_threshold', 1.8)
        if current_volatility < min_volatility * 0.7:  # 70% do threshold
            return False, f"Volatilidade muito baixa ({current_volatility:.2f}%)"
        
        # Verifica kill switch
        max_consecutive = self.config.get('risk_management', {}).get('kill_switch', {}).get('consecutive_losses', 6)
        if self.consecutive_losses >= max_consecutive:
            return False, f"Kill switch ativado ({self.consecutive_losses} perdas consecutivas)"
        
        # Evita trading em horários de baixa liquidez (exemplo: 02:00-04:00 UTC)
        current_hour = datetime.utcnow().hour
        if 2 <= current_hour <= 4:
            return False, "Horário de baixa liquidez"
        
        return True, "Condições favoráveis"
    
    def update_trade_result(self, pnl_pct: float):
        """Atualiza resultado do último trade"""
        self.last_trade_time = datetime.now()
        
        if pnl_pct <= 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0  # Reset contador em lucro
    
    def get_current_price(self, symbol: str) -> float:
        """Obtém preço atual"""
        try:
            # Substitua ETH/USDT por ETH-USDT para a API
            api_symbol = symbol.replace('/', '-')
            url = f"https://open-api.bingx.com/openApi/swap/v2/quote/price"
            params = {"symbol": api_symbol}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('code') == 0:
                price = float(data.get('data', {}).get('price', 0))
                logger.debug(f"Preço atual {symbol}: {price}")
                return price
            else:
                logger.warning(f"Erro na API de preço: {data}")
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Erro ao obter preço: {e}")
            return 0.0
    
    def fetch_market_data(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """Busca dados de mercado com cache inteligente"""
        try:
            api_symbol = symbol.replace('/', '-')
            url = f"https://open-api.bingx.com/openApi/swap/v2/quote/klines"
            
            # Usa menos dados para análise mais rápida
            params = {
                "symbol": api_symbol,
                "interval": "5m",
                "limit": min(limit, 150)  # Reduzido de 200 para 150
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("code") != 0:
                logger.error(f"Erro na API klines: {data}")
                return pd.DataFrame()
            
            klines = data.get("data", [])
            if not klines:
                logger.warning("Nenhum dado de klines retornado")
                return pd.DataFrame()
            
            df_data = []
            for kline in klines:
                if isinstance(kline, dict):
                    df_data.append([
                        kline['time'],
                        float(kline['open']),
                        float(kline['high']),
                        float(kline['low']),
                        float(kline['close']),
                        float(kline['volume'])
                    ])
            
            df = pd.DataFrame(df_data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
            
            # Ordena por timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Dados obtidos: {len(df)} velas para {symbol}")
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].dropna()
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados: {e}")
            return pd.DataFrame()
    
    def calculate_market_conditions(self, df: pd.DataFrame) -> Dict:
        """Calcula condições atuais do mercado"""
        if df.empty:
            return {}
        
        try:
            conditions = {}
            
            # Volatilidade atual
            returns = df['close'].pct_change().dropna()
            if len(returns) >= 20:
                current_vol = returns.iloc[-20:].std() * 100  # Últimas 20 velas
                avg_vol = returns.std() * 100
                conditions['current_volatility'] = current_vol
                conditions['avg_volatility'] = avg_vol
                conditions['volatility_ratio'] = current_vol / avg_vol if avg_vol > 0 else 1
            
            # Volume
            if len(df) >= 20:
                current_vol_avg = df['volume'].iloc[-5:].mean()  # Últimas 5 velas
                historical_vol_avg = df['volume'].iloc[-20:].mean()  # Últimas 20 velas
                conditions['volume_ratio'] = current_vol_avg / historical_vol_avg if historical_vol_avg > 0 else 1
            
            # Trend strength simples
            if len(df) >= 20:
                price_20_ago = df['close'].iloc[-20]
                current_price = df['close'].iloc[-1]
                trend_strength = ((current_price - price_20_ago) / price_20_ago) * 100
                conditions['trend_strength'] = trend_strength
                conditions['trend_direction'] = 'up' if trend_strength > 0.5 else 'down' if trend_strength < -0.5 else 'neutral'
            
            # ATR para contexto
            if len(df) >= 14:
                high_low = df['high'] - df['low']
                conditions['atr'] = high_low.rolling(14).mean().iloc[-1]
            
            logger.debug(f"Condições do mercado: {conditions}")
            return conditions
            
        except Exception as e:
            logger.error(f"Erro ao calcular condições: {e}")
            return {}
    
    def analyze_market(self, symbol: str) -> Optional[Dict]:
        """Analisa mercado com otimizações de performance"""
        try:
            self.last_analysis_time = datetime.now()
            
            # Busca dados
            df = self.fetch_market_data(symbol, limit=100)  # Reduzido para 100 velas
            
            if df.empty or len(df) < 30:  # Reduzido de 50 para 30
                logger.warning(f"Dados insuficientes: {len(df)} velas")
                return None
            
            # Calcula condições do mercado
            market_conditions = self.calculate_market_conditions(df)
            
            # Verifica se deve fazer trade
            can_trade, trade_reason = self.should_trade_now(
                market_conditions.get('current_volatility', 2.0)
            )
            
            if not can_trade:
                logger.info(f"Trading bloqueado: {trade_reason}")
                return {
                    'can_trade': False,
                    'reason': trade_reason,
                    'market_conditions': market_conditions,
                    'price': df['close'].iloc[-1]
                }
            
            # Análise de regime (se habilitada e necessária)
            regime_analysis = None
            if self.regime_detector.enabled:
                # Analisa regime com menos frequência (a cada 30 min)
                if self.regime_detector.should_analyze(symbol, 30):
                    regime_analysis = self.regime_detector.analyze_market_regime(symbol)
            
            # Calcula indicadores técnicos
            indicators = self.ta.calculate_technical_indicators(df, symbol)
            
            if not indicators:
                return None
            
            # Adiciona condições do mercado aos indicadores
            indicators.update(market_conditions)
            
            # Gera sinal considerando regime de mercado
            signal = self._generate_regime_aware_signal(
                df, indicators, symbol, regime_analysis
            )
            
            analysis_result = {
                'signal': signal,
                'indicators': indicators,
                'price': indicators.get('current_price', 0),
                'regime': regime_analysis,
                'market_conditions': market_conditions,
                'can_trade': True,
                'data_quality': len(df)  # Para debug
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Erro na análise: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _generate_regime_aware_signal(self, df: pd.DataFrame, indicators: Dict, 
                                    symbol: str, regime_analysis) -> any:
        """Gera sinal adaptado ao regime de mercado detectado"""
        
        # Se não há análise de regime, usa análise técnica padrão
        if not regime_analysis:
            return self.ta.generate_trading_signal(df, symbol, indicators)
        
        # Obtém posições atuais (simulado - em produção viria do position manager)
        current_positions = {}
        
        # Aplica ajustes baseados no regime
        adjusted_config = self._adjust_config_for_regime(regime_analysis)
        
        # Cria analisador técnico temporário com configuração ajustada
        temp_ta = TechnicalAnalysis(adjusted_config)
        
        # Gera sinal com configuração ajustada
        signal = temp_ta.generate_trading_signal(df, symbol, indicators, current_positions)
        
        # Aplica filtros específicos do regime
        filtered_signal = self._apply_regime_filters(signal, regime_analysis, indicators)
        
        if filtered_signal and filtered_signal.action != 'hold':
            logger.info(f"Sinal regime-aware: {filtered_signal.action} (regime: {regime_analysis.primary_regime.value})")
            logger.info(f"  Regime confiança: {regime_analysis.confidence:.2f}")
            logger.info(f"  Trend strength: {regime_analysis.trend_strength:.2f}")
        
        return filtered_signal
    
    def _adjust_config_for_regime(self, regime_analysis) -> Dict:
        """Ajusta configuração baseada no regime detectado"""
        adjusted_config = self.config.copy()
        regime = regime_analysis.primary_regime
        recommendations = regime_analysis.recommendations
        
        # Aplica ajustes de indicadores
        indicator_adjustments = recommendations.get('indicator_adjustments', {})
        
        if 'lower_rsi_oversold' in indicator_adjustments:
            if 'ai_futures' not in adjusted_config:
                adjusted_config['ai_futures'] = {}
            if 'rsi' not in adjusted_config['ai_futures']:
                adjusted_config['ai_futures']['rsi'] = {}
            adjusted_config['ai_futures']['rsi']['oversold_level'] = indicator_adjustments['lower_rsi_oversold']
        
        if 'higher_rsi_overbought' in indicator_adjustments:
            if 'ai_futures' not in adjusted_config:
                adjusted_config['ai_futures'] = {}
            if 'rsi' not in adjusted_config['ai_futures']:
                adjusted_config['ai_futures']['rsi'] = {}
            adjusted_config['ai_futures']['rsi']['overbought_level'] = indicator_adjustments['higher_rsi_overbought']
        
        # Ajusta scores mínimos baseado no regime
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Em trending, reduz score mínimo para pegar mais sinais de momentum
            if 'ai_futures' not in adjusted_config:
                adjusted_config['ai_futures'] = {}
            if 'scoring' not in adjusted_config['ai_futures']:
                adjusted_config['ai_futures']['scoring'] = {}
            
            current_min_long = adjusted_config['ai_futures']['scoring'].get('min_score_long', 4.0)
            current_min_short = adjusted_config['ai_futures']['scoring'].get('min_score_short', 4.0)
            
            adjusted_config['ai_futures']['scoring']['min_score_long'] = max(3.0, current_min_long - 1.0)
            adjusted_config['ai_futures']['scoring']['min_score_short'] = max(3.0, current_min_short - 1.0)
        
        elif regime == MarketRegime.HIGH_VOLATILITY:
            # Em alta volatilidade, aumenta score mínimo para ser mais seletivo
            if 'ai_futures' not in adjusted_config:
                adjusted_config['ai_futures'] = {}
            if 'scoring' not in adjusted_config['ai_futures']:
                adjusted_config['ai_futures']['scoring'] = {}
            
            current_min_long = adjusted_config['ai_futures']['scoring'].get('min_score_long', 4.0)
            current_min_short = adjusted_config['ai_futures']['scoring'].get('min_score_short', 4.0)
            
            adjusted_config['ai_futures']['scoring']['min_score_long'] = min(7.0, current_min_long + 1.5)
            adjusted_config['ai_futures']['scoring']['min_score_short'] = min(7.0, current_min_short + 1.5)
        
        elif regime == MarketRegime.RANGING:
            # Em ranging, favorece mean reversion
            if 'ai_futures' not in adjusted_config:
                adjusted_config['ai_futures'] = {}
            if 'rsi' not in adjusted_config['ai_futures']:
                adjusted_config['ai_futures']['rsi'] = {}
            
            # RSI mais extremo para ranging
            adjusted_config['ai_futures']['rsi']['oversold_level'] = 20
            adjusted_config['ai_futures']['rsi']['overbought_level'] = 80
        
        return adjusted_config
    
    def _apply_regime_filters(self, signal, regime_analysis, indicators):
        """Aplica filtros específicos baseados no regime"""
        if not signal or signal.action == 'hold':
            return signal
        
        regime = regime_analysis.primary_regime
        recommendations = regime_analysis.recommendations
        
        # Filtro para regimes de trending
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            # Em trending up, evita shorts contra a tendência
            if regime == MarketRegime.TRENDING_UP and signal.action == 'short':
                if regime_analysis.trend_strength > 0.6:  # Reduzido de 0.7
                    logger.info(f"Rejeitando SHORT em uptrend (strength: {regime_analysis.trend_strength:.2f})")
                    signal.action = 'hold'
                    signal.reason = "Contra tendência"
            
            # Em trending down, evita longs contra a tendência  
            elif regime == MarketRegime.TRENDING_DOWN and signal.action == 'long':
                if regime_analysis.trend_strength > 0.6:  # Reduzido de 0.7
                    logger.info(f"Rejeitando LONG em downtrend (strength: {regime_analysis.trend_strength:.2f})")
                    signal.action = 'hold'
                    signal.reason = "Contra tendência"
        
        # Filtro para alta volatilidade - MAIS FLEXÍVEL
        elif regime == MarketRegime.HIGH_VOLATILITY:
            # Reduz confiança em alta volatilidade
            original_confidence = signal.confidence
            signal.confidence *= 0.8  # Menos penalização (era 0.7)
            
            # Threshold menor para aceitar sinais
            min_confidence = self.config.get('ai_futures', {}).get('filters', {}).get('min_confidence', 0.55)
            if signal.confidence < min_confidence * 0.9:  # 90% do threshold
                logger.info(f"Rejeitando sinal em alta volatilidade (confiança: {original_confidence:.2f} -> {signal.confidence:.2f})")
                signal.action = 'hold'
                signal.reason = "Baixa confiança em alta volatilidade"
        
        # Filtro para breakouts - MAIS PERMISSIVO
        elif regime in [MarketRegime.BREAKOUT_UP, MarketRegime.BREAKOUT_DOWN]:
            # Em breakouts, favorece direção do breakout mas não rejeita tudo
            if regime == MarketRegime.BREAKOUT_UP and signal.action == 'short':
                if regime_analysis.confidence > 0.8:  # Só rejeita se muito confiante
                    logger.info("Rejeitando SHORT durante breakout up forte")
                    signal.action = 'hold'
                    signal.reason = "Contra direção do breakout"
                else:
                    signal.confidence *= 0.7  # Apenas reduz confiança
                    
            elif regime == MarketRegime.BREAKOUT_DOWN and signal.action == 'long':
                if regime_analysis.confidence > 0.8:  # Só rejeita se muito confiante
                    logger.info("Rejeitando LONG durante breakout down forte") 
                    signal.action = 'hold'
                    signal.reason = "Contra direção do breakout"
                else:
                    signal.confidence *= 0.7  # Apenas reduz confiança
            
            # Aumenta confiança se alinhado com breakout
            elif ((regime == MarketRegime.BREAKOUT_UP and signal.action == 'long') or
                  (regime == MarketRegime.BREAKOUT_DOWN and signal.action == 'short')):
                signal.confidence = min(0.95, signal.confidence * 1.2)  # Menos boost (era 1.3)
                signal.reason += " + breakout confirmation"
        
        # Filtro para ranging/low volatility - MENOS RESTRITIVO
        elif regime in [MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY]:
            # Em ranging, prefere extremos mas não é muito restritivo
            rsi = indicators.get('rsi', 50)
            bb_position = indicators.get('bb_position', 0.5)
            
            # Condições menos restritivas para ranging
            if signal.action == 'long' and not (rsi < 35 or bb_position < 0.25):
                signal.confidence *= 0.8  # Reduz confiança ao invés de rejeitar
                signal.reason += " (ranging - confiança reduzida)"
            
            elif signal.action == 'short' and not (rsi > 65 or bb_position > 0.75):
                signal.confidence *= 0.8  # Reduz confiança ao invés de rejeitar
                signal.reason += " (ranging - confiança reduzida)"
        
        return signal
    
    def get_regime_info(self, symbol: str) -> Dict:
        """Retorna informações do regime atual"""
        current_regime = self.regime_detector.get_current_regime(symbol)
        stats = self.regime_detector.get_regime_stats()
        
        return {
            'current_regime': current_regime.value if current_regime else 'unknown',
            'detector_enabled': self.regime_detector.enabled,
            'stats': stats,
            'consecutive_losses': self.consecutive_losses
        }
    
    def reset_consecutive_losses(self):
        """Reset contador de perdas consecutivas (para testes)"""
        self.consecutive_losses = 0
        logger.info("Contador de perdas consecutivas resetado")