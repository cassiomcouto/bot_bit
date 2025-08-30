import logging
import requests
import pandas as pd
import time
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
        interval = self.config.get('strategy', {}).get('analysis_interval_seconds', 45)
        time_since = (datetime.now() - self.last_analysis_time).total_seconds()
        
        return time_since >= interval
    
    def should_trade_now(self, current_volatility: float = 2.0) -> tuple[bool, str]:
        """Verifica se condições são favoráveis para trading"""
        
        # Verifica cooldown entre trades
        if self.last_trade_time:
            cooldown = self.config.get('strategy', {}).get('cooldown_between_trades_seconds', 180)
            time_since_trade = (datetime.now() - self.last_trade_time).total_seconds()
            
            if time_since_trade < cooldown:
                remaining = cooldown - time_since_trade
                return False, f"Cooldown ativo ({remaining:.0f}s restantes)"
        
        # Evita trading em volatilidade muito baixa
        min_volatility = self.config.get('technical_analysis', {}).get('volatility', {}).get('volatility_threshold', 1.8)
        if current_volatility < min_volatility * 0.7:
            return False, f"Volatilidade muito baixa ({current_volatility:.2f}%)"
        
        # Verifica kill switch
        max_consecutive = self.config.get('risk_management', {}).get('kill_switch', {}).get('consecutive_losses', 6)
        if self.consecutive_losses >= max_consecutive:
            return False, f"Kill switch ativado ({self.consecutive_losses} perdas consecutivas)"
        
        # Evita trading em horários de baixa liquidez
        current_hour = datetime.utcnow().hour
        if 2 <= current_hour <= 4:
            return False, "Horário de baixa liquidez"
        
        return True, "Condições favoráveis"
    
    def update_trade_result(self, pnl_pct: float):
        """Atualiza resultado do último trade - CORRIGIDO"""
        self.last_trade_time = datetime.now()
        
        if pnl_pct < -0.5:
            self.consecutive_losses += 1
            logger.info(f"Perda registrada: {pnl_pct:.2f}% (consecutivas: {self.consecutive_losses})")
        elif pnl_pct > 0.5:
            self.consecutive_losses = 0
            logger.info(f"Lucro registrado: {pnl_pct:.2f}% (contador resetado)")
    
    def get_current_price(self, symbol: str) -> float:
        """Obtém preço atual"""
        try:
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
        """Busca dados de mercado - VERSÃO MELHORADA"""
        try:
            api_symbol = symbol.replace('/', '-')
            url = f"https://open-api.bingx.com/openApi/swap/v2/quote/klines"
            
            safe_limit = max(50, min(limit, 150))
            params = {
                "symbol": api_symbol,
                "interval": "5m",
                "limit": safe_limit
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("code") != 0:
                logger.error(f"Erro na API klines: {data}")
                return self._create_empty_dataframe()
            
            klines = data.get("data", [])
            if not klines:
                logger.warning("Nenhum dado de klines retornado")
                return self._create_empty_dataframe()
            
            if len(klines) < 10:
                logger.warning(f"Dados insuficientes retornados: {len(klines)} velas")
            
            df_data = []
            for kline in klines:
                if isinstance(kline, dict):
                    try:
                        df_data.append([
                            kline['time'],
                            float(kline['open']),
                            float(kline['high']),
                            float(kline['low']),
                            float(kline['close']),
                            float(kline['volume'])
                        ])
                    except (KeyError, ValueError) as e:
                        logger.warning(f"Erro ao processar kline: {e}")
                        continue
            
            if not df_data:
                logger.error("Nenhum dado válido após processamento")
                return self._create_empty_dataframe()
            
            df = pd.DataFrame(df_data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
            
            df = df.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
            
            final_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].dropna()
            
            if final_df.empty:
                logger.error("DataFrame final vazio após limpeza")
                return self._create_empty_dataframe()
            
            logger.info(f"Dados obtidos para {symbol}: {len(final_df)} velas válidas")
            return final_df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao buscar dados: {e}")
            return self._create_empty_dataframe()
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar dados: {e}")
            return self._create_empty_dataframe()
    
    def _create_empty_dataframe(self) -> pd.DataFrame:
        """Cria DataFrame vazio com estrutura correta"""
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    def calculate_market_conditions(self, df: pd.DataFrame) -> Dict:
        """Calcula condições atuais do mercado - VERSÃO CORRIGIDA"""
        if df.empty:
            logger.warning("DataFrame vazio para análise de condições")
            return self._get_default_market_conditions()
        
        try:
            conditions = {}
            df_len = len(df)
            logger.debug(f"Calculando condições com {df_len} velas")
            
            # VOLATILIDADE - COM VERIFICAÇÃO SEGURA
            returns = df['close'].pct_change().dropna()
            returns_len = len(returns)
            
            if returns_len >= 20:
                current_vol = returns.iloc[-20:].std() * 100
                avg_vol = returns.std() * 100
            elif returns_len >= 10:
                current_vol = returns.iloc[-returns_len:].std() * 100
                avg_vol = returns.std() * 100
                logger.warning(f"Dados limitados para volatilidade: {returns_len} returns")
            elif returns_len >= 5:
                current_vol = returns.std() * 100
                avg_vol = current_vol
                logger.warning(f"Dados muito limitados para volatilidade: {returns_len} returns")
            else:
                current_vol = 2.0
                avg_vol = 2.0
                logger.warning(f"Dados insuficientes para volatilidade: {returns_len} returns")
            
            conditions['current_volatility'] = current_vol
            conditions['avg_volatility'] = avg_vol
            conditions['volatility_ratio'] = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            # VOLUME - COM VERIFICAÇÃO SEGURA
            if df_len >= 20:
                current_vol_avg = df['volume'].iloc[-5:].mean()
                historical_vol_avg = df['volume'].iloc[-20:].mean()
            elif df_len >= 10:
                current_vol_avg = df['volume'].iloc[-min(3, df_len):].mean()
                historical_vol_avg = df['volume'].iloc[-min(10, df_len):].mean()
            elif df_len >= 5:
                current_vol_avg = df['volume'].iloc[-min(2, df_len):].mean()
                historical_vol_avg = df['volume'].mean()
            else:
                current_vol_avg = df['volume'].mean()
                historical_vol_avg = current_vol_avg
                
            conditions['volume_ratio'] = current_vol_avg / historical_vol_avg if historical_vol_avg > 0 else 1.0
            
            # TREND STRENGTH - COM VERIFICAÇÃO SEGURA
            if df_len >= 20:
                price_ago = df['close'].iloc[-20]
                current_price = df['close'].iloc[-1]
                trend_strength = ((current_price - price_ago) / price_ago) * 100
            elif df_len >= 10:
                price_ago = df['close'].iloc[-min(10, df_len)]
                current_price = df['close'].iloc[-1]
                trend_strength = ((current_price - price_ago) / price_ago) * 100
            elif df_len >= 5:
                price_ago = df['close'].iloc[-min(5, df_len)]
                current_price = df['close'].iloc[-1]
                trend_strength = ((current_price - price_ago) / price_ago) * 100
            else:
                trend_strength = 0.0
                
            conditions['trend_strength'] = trend_strength
            conditions['trend_direction'] = 'up' if trend_strength > 0.5 else 'down' if trend_strength < -0.5 else 'neutral'
            
            # ATR - COM VERIFICAÇÃO SEGURA
            if df_len >= 14:
                high_low = df['high'] - df['low']
                atr_window = min(14, df_len)
                conditions['atr'] = high_low.rolling(atr_window).mean().iloc[-1]
            else:
                conditions['atr'] = (df['high'] - df['low']).mean()
            
            conditions['_debug_info'] = {
                'df_length': df_len,
                'returns_length': returns_len,
                'data_quality': self._assess_data_quality(df_len)
            }
            
            logger.debug(f"Condições calculadas: vol={current_vol:.2f}%, trend={trend_strength:.2f}%")
            return conditions
            
        except Exception as e:
            logger.error(f"Erro ao calcular condições: {e}")
            return self._get_fallback_market_conditions(df)
    
    def _get_default_market_conditions(self) -> Dict:
        """Retorna condições padrão quando não há dados"""
        return {
            'current_volatility': 2.0,
            'avg_volatility': 2.0,
            'volatility_ratio': 1.0,
            'volume_ratio': 1.0,
            'trend_strength': 0.0,
            'trend_direction': 'neutral',
            'atr': 10.0,
            '_debug_info': {
                'df_length': 0,
                'returns_length': 0,
                'data_quality': 'no_data'
            }
        }
    
    def _get_fallback_market_conditions(self, df: pd.DataFrame) -> Dict:
        """Condições de fallback quando há erro no cálculo"""
        if df.empty:
            return self._get_default_market_conditions()
        
        try:
            current_price = df['close'].iloc[-1]
            prev_price = df['close'].iloc[0] if len(df) > 1 else current_price
            
            price_change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
            
            return {
                'current_volatility': abs(price_change_pct) + 1.0,
                'avg_volatility': 2.0,
                'volatility_ratio': 1.0,
                'volume_ratio': 1.0,
                'trend_strength': price_change_pct,
                'trend_direction': 'up' if price_change_pct > 0.5 else 'down' if price_change_pct < -0.5 else 'neutral',
                'atr': abs(df['high'].max() - df['low'].min()),
                '_debug_info': {
                    'df_length': len(df),
                    'returns_length': 0,
                    'data_quality': 'fallback_calculation'
                }
            }
        except Exception as e:
            logger.error(f"Erro mesmo no fallback: {e}")
            return self._get_default_market_conditions()
    
    def _assess_data_quality(self, df_length: int) -> str:
        """Avalia a qualidade dos dados disponíveis"""
        if df_length >= 100:
            return 'excellent'
        elif df_length >= 50:
            return 'good'
        elif df_length >= 20:
            return 'adequate'
        elif df_length >= 10:
            return 'limited'
        elif df_length >= 5:
            return 'poor'
        else:
            return 'insufficient'
    
    def analyze_market(self, symbol: str) -> Optional[Dict]:
        """Analisa mercado - VERSÃO ROBUSTA"""
        try:
            self.last_analysis_time = datetime.now()
            
            df = None
            max_retries = 3
            
            for attempt in range(max_retries):
                df = self.fetch_market_data(symbol, limit=100)
                
                if not df.empty and len(df) >= 10:
                    break
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"Tentativa {attempt + 1}/{max_retries} falhou para {symbol}")
                        time.sleep(2)
                    else:
                        logger.error(f"Falha em todas as {max_retries} tentativas para {symbol}")
            
            if df is None or df.empty:
                logger.error(f"Impossível obter dados para {symbol}")
                return self._get_emergency_analysis_result(symbol)
            
            if len(df) < 5:
                logger.warning(f"Dados muito limitados para {symbol}: {len(df)} velas")
                return self._get_limited_analysis_result(symbol, df)
            
            market_conditions = self.calculate_market_conditions(df)
            
            can_trade, trade_reason = self.should_trade_now(
                market_conditions.get('current_volatility', 2.0)
            )
            
            if not can_trade:
                logger.info(f"Trading bloqueado para {symbol}: {trade_reason}")
                return {
                    'can_trade': False,
                    'reason': trade_reason,
                    'market_conditions': market_conditions,
                    'price': df['close'].iloc[-1] if len(df) > 0 else 0,
                    'data_quality': market_conditions.get('_debug_info', {}).get('data_quality', 'unknown')
                }
            
            regime_analysis = None
            if self.regime_detector.enabled:
                try:
                    if self.regime_detector.should_analyze(symbol, 30):
                        regime_analysis = self.regime_detector.analyze_market_regime(symbol)
                except Exception as e:
                    logger.warning(f"Erro na análise de regime para {symbol}: {e}")
                    regime_analysis = None
            
            indicators = None
            try:
                indicators = self.ta.calculate_technical_indicators(df, symbol)
            except Exception as e:
                logger.error(f"Erro ao calcular indicadores técnicos para {symbol}: {e}")
                return self._get_emergency_analysis_result(symbol)
            
            if not indicators:
                logger.warning(f"Nenhum indicador calculado para {symbol}")
                return self._get_emergency_analysis_result(symbol)
            
            indicators.update(market_conditions)
            
            signal = None
            try:
                signal = self._generate_regime_aware_signal(
                    df, indicators, symbol, regime_analysis
                )
            except Exception as e:
                logger.error(f"Erro ao gerar sinal para {symbol}: {e}")
                signal = None
            
            analysis_result = {
                'signal': signal,
                'indicators': indicators,
                'price': indicators.get('current_price', 0),
                'regime': regime_analysis,
                'market_conditions': market_conditions,
                'can_trade': True,
                'data_quality': market_conditions.get('_debug_info', {}).get('data_quality', 'unknown'),
                'data_length': len(df)
            }
            
            logger.debug(f"Análise completa para {symbol}: {analysis_result['data_quality']} quality")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Erro crítico na análise de {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_emergency_analysis_result(symbol)
    
    def _get_emergency_analysis_result(self, symbol: str) -> Dict:
        """Resultado de emergência quando tudo falha"""
        try:
            current_price = self.get_current_price(symbol)
        except:
            current_price = 0.0
        
        return {
            'can_trade': False,
            'reason': 'Erro crítico na análise - dados insuficientes',
            'price': current_price,
            'signal': None,
            'indicators': {},
            'market_conditions': self._get_default_market_conditions(),
            'regime': None,
            'data_quality': 'emergency',
            'data_length': 0
        }
    
    def _get_limited_analysis_result(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Análise limitada com poucos dados"""
        try:
            current_price = df['close'].iloc[-1] if len(df) > 0 else 0
            basic_conditions = self._get_fallback_market_conditions(df)
            
            return {
                'can_trade': False,
                'reason': f'Dados insuficientes: apenas {len(df)} velas disponíveis',
                'price': current_price,
                'signal': None,
                'indicators': {'current_price': current_price},
                'market_conditions': basic_conditions,
                'regime': None,
                'data_quality': 'insufficient',
                'data_length': len(df)
            }
        except Exception as e:
            logger.error(f"Erro mesmo na análise limitada: {e}")
            return self._get_emergency_analysis_result(symbol)
    
    def _generate_regime_aware_signal(self, df: pd.DataFrame, indicators: Dict, 
                                    symbol: str, regime_analysis) -> any:
        """Gera sinal adaptado ao regime de mercado detectado"""
        
        if not regime_analysis:
            return self.ta.generate_trading_signal(df, symbol, indicators)
        
        current_positions = {}
        adjusted_config = self._adjust_config_for_regime(regime_analysis)
        temp_ta = TechnicalAnalysis(adjusted_config)
        signal = temp_ta.generate_trading_signal(df, symbol, indicators, current_positions)
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
        
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if 'ai_futures' not in adjusted_config:
                adjusted_config['ai_futures'] = {}
            if 'scoring' not in adjusted_config['ai_futures']:
                adjusted_config['ai_futures']['scoring'] = {}
            
            current_min_long = adjusted_config['ai_futures']['scoring'].get('min_score_long', 4.0)
            current_min_short = adjusted_config['ai_futures']['scoring'].get('min_score_short', 4.0)
            
            adjusted_config['ai_futures']['scoring']['min_score_long'] = max(3.0, current_min_long - 1.0)
            adjusted_config['ai_futures']['scoring']['min_score_short'] = max(3.0, current_min_short - 1.0)
        
        elif regime == MarketRegime.HIGH_VOLATILITY:
            if 'ai_futures' not in adjusted_config:
                adjusted_config['ai_futures'] = {}
            if 'scoring' not in adjusted_config['ai_futures']:
                adjusted_config['ai_futures']['scoring'] = {}
            
            current_min_long = adjusted_config['ai_futures']['scoring'].get('min_score_long', 4.0)
            current_min_short = adjusted_config['ai_futures']['scoring'].get('min_score_short', 4.0)
            
            adjusted_config['ai_futures']['scoring']['min_score_long'] = min(7.0, current_min_long + 1.5)
            adjusted_config['ai_futures']['scoring']['min_score_short'] = min(7.0, current_min_short + 1.5)
        
        elif regime == MarketRegime.RANGING:
            if 'ai_futures' not in adjusted_config:
                adjusted_config['ai_futures'] = {}
            if 'rsi' not in adjusted_config['ai_futures']:
                adjusted_config['ai_futures']['rsi'] = {}
            
            adjusted_config['ai_futures']['rsi']['oversold_level'] = 20
            adjusted_config['ai_futures']['rsi']['overbought_level'] = 80
        
        return adjusted_config
    
    def _apply_regime_filters(self, signal, regime_analysis, indicators):
        """Aplica filtros específicos baseados no regime"""
        if not signal or signal.action == 'hold':
            return signal
        
        regime = regime_analysis.primary_regime
        recommendations = regime_analysis.recommendations
        
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if regime == MarketRegime.TRENDING_UP and signal.action == 'short':
                if regime_analysis.trend_strength > 0.6:
                    logger.info(f"Rejeitando SHORT em uptrend (strength: {regime_analysis.trend_strength:.2f})")
                    signal.action = 'hold'
                    signal.reason = "Contra tendência"
            
            elif regime == MarketRegime.TRENDING_DOWN and signal.action == 'long':
                if regime_analysis.trend_strength > 0.6:
                    logger.info(f"Rejeitando LONG em downtrend (strength: {regime_analysis.trend_strength:.2f})")
                    signal.action = 'hold'
                    signal.reason = "Contra tendência"
        
        elif regime == MarketRegime.HIGH_VOLATILITY:
            original_confidence = signal.confidence
            signal.confidence *= 0.8
            
            min_confidence = self.config.get('ai_futures', {}).get('filters', {}).get('min_confidence', 0.55)
            if signal.confidence < min_confidence * 0.9:
                logger.info(f"Rejeitando sinal em alta volatilidade (confiança: {original_confidence:.2f} -> {signal.confidence:.2f})")
                signal.action = 'hold'
                signal.reason = "Baixa confiança em alta volatilidade"
        
        elif regime in [MarketRegime.BREAKOUT_UP, MarketRegime.BREAKOUT_DOWN]:
            if regime == MarketRegime.BREAKOUT_UP and signal.action == 'short':
                if regime_analysis.confidence > 0.8:
                    logger.info("Rejeitando SHORT durante breakout up forte")
                    signal.action = 'hold'
                    signal.reason = "Contra direção do breakout"
                else:
                    signal.confidence *= 0.7
                    
            elif regime == MarketRegime.BREAKOUT_DOWN and signal.action == 'long':
                if regime_analysis.confidence > 0.8:
                    logger.info("Rejeitando LONG durante breakout down forte") 
                    signal.action = 'hold'
                    signal.reason = "Contra direção do breakout"
                else:
                    signal.confidence *= 0.7
            
            elif ((regime == MarketRegime.BREAKOUT_UP and signal.action == 'long') or
                  (regime == MarketRegime.BREAKOUT_DOWN and signal.action == 'short')):
                signal.confidence = min(0.95, signal.confidence * 1.2)
                signal.reason += " + breakout confirmation"
        
        elif regime in [MarketRegime.RANGING, MarketRegime.LOW_VOLATILITY]:
            rsi = indicators.get('rsi', 50)
            bb_position = indicators.get('bb_position', 0.5)
            
            if signal.action == 'long' and not (rsi < 35 or bb_position < 0.25):
                signal.confidence *= 0.8
                signal.reason += " (ranging - confiança reduzida)"
            
            elif signal.action == 'short' and not (rsi > 65 or bb_position > 0.75):
                signal.confidence *= 0.8
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
        """Reset contador de perdas consecutivas"""
        self.consecutive_losses = 0
        logger.info("Contador de perdas consecutivas resetado")