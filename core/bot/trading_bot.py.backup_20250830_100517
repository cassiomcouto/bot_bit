# Diagnóstico inicial dos componentes
        self._diagnose_components()
        
        logger.info(f"Bot inicializado - Modo: {'PAPER' if self.paper_trading else 'REAL'}")#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Bot Module - Classe principal do bot de trading
"""

import logging
import time
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any

# Importações locais
from models.data_classes import FuturesPosition, FuturesTrade, PositionSide
from api.bingx_api import BingXFuturesAPI
from analysis.market_analyzer import MarketAnalyzer
from core.managers.position_manager import PositionManager
from core.managers.risk_manager import RiskManager
from utils.csv_logger import CSVLogger

logger = logging.getLogger(__name__)

class BingXFuturesBot:
    """Bot principal de trading para futuros BingX"""
    
    def __init__(self, config_path: str = "config/futures_config.yaml"):
        """
        Inicializa o bot de trading
        
        Args:
            config_path: Caminho para arquivo de configuração
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.running = False
        self.bot_start_time = datetime.now()
        
        # Estado do bot
        self.paper_trading = self._get_config('advanced.paper_trading.enabled', True)
        
        # Cache de preços para acompanhamento
        self.price_cache = {}
        
        # Inicializa componentes
        self._initialize_components()
        
        # Sincronização inicial
        if not self.paper_trading:
            self._sync_with_exchange()
        
        logger.info(f"Bot inicializado - Modo: {'PAPER' if self.paper_trading else 'REAL'}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configuração do arquivo YAML"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self._validate_config(config)
                return config
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            raise
    
    def _validate_config(self, config: Dict[str, Any]):
        """Valida configuração obrigatória"""
        required = ['trading', 'risk_management', 'exchanges', 'strategy']
        missing = [s for s in required if s not in config]
        if missing:
            raise ValueError(f"Seções obrigatórias ausentes: {missing}")
    
    def _get_config(self, path: str, default=None):
        """Obtém valor de configuração aninhada"""
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def _initialize_components(self):
        """Inicializa todos os componentes do bot"""
        # Exchange API
        if not self.paper_trading:
            exchange_name = self._get_config('strategy.primary_exchange')
            exchange_config = self._get_config(f'exchanges.{exchange_name}')
            
            self.api = BingXFuturesAPI(
                api_key=exchange_config['api_key'],
                secret_key=exchange_config['secret_key'],
                testnet=exchange_config.get('testnet', False)
            )
        else:
            self.api = None
        
        # Componentes de trading
        self.market_analyzer = MarketAnalyzer(self.config)
        self.position_manager = PositionManager(self.config, self.api, self.paper_trading)
        self.risk_manager = RiskManager(self.config)
        
        # Logger CSV com campos adicionais
        self.csv_logger = CSVLogger("logs/trades.csv")
        
        # Estado inicial
        if self.paper_trading:
            initial_balance = self._get_config('advanced.paper_trading.initial_balance_usdt', 100.0)
            self.position_manager.set_balance(initial_balance)
    
    def _sync_with_exchange(self):
        """Sincroniza estado com a exchange"""
        if self.paper_trading or not self.api:
            return
        
        try:
            logger.info("Sincronizando com exchange...")
            
            # Health check
            if not self.api.health_check():
                logger.warning("Health check falhou, continuando...")
            
            # Sincroniza saldo
            try:
                account_info = self.api.get_account_info()
                if account_info and 'balance' in account_info:
                    balance = self._extract_balance(account_info['balance'])
                    self.position_manager.set_balance(balance)
                    logger.info(f"Saldo: ${balance:.2f}")
            except Exception as e:
                logger.warning(f"Erro ao obter saldo: {e}")
            
            # Sincroniza posições
            try:
                positions = self.api.get_positions()
                self.position_manager.sync_positions(positions)
                logger.info(f"Posições sincronizadas: {len(positions)}")
            except Exception as e:
                logger.warning(f"Erro ao obter posições: {e}")
            
            logger.info("Sincronização concluída")
            
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
    
    def _extract_balance(self, balance_obj) -> float:
        """Extrai saldo do objeto de resposta"""
        if isinstance(balance_obj, dict):
            for field in ['equity', 'availableMargin', 'balance']:
                if field in balance_obj:
                    try:
                        return float(balance_obj[field])
                    except (ValueError, TypeError):
                        continue
        return 0.0
    
    def _calculate_exit_targets(self, entry_price: float, side: str) -> Dict[str, float]:
        """Calcula valores de take profit e stop loss"""
        tp_percent = self._get_config('risk_management.take_profit_percent', 2.0)
        sl_percent = self._get_config('risk_management.stop_loss_percent', 1.0)
        
        if side.lower() == 'long':
            take_profit = entry_price * (1 + tp_percent / 100)
            stop_loss = entry_price * (1 - sl_percent / 100)
        else:  # short
            take_profit = entry_price * (1 - tp_percent / 100)
            stop_loss = entry_price * (1 + sl_percent / 100)
        
        return {
            'take_profit': take_profit,
            'stop_loss': stop_loss
        }
    
    def _update_price_cache(self, symbol: str, price: float):
        """Atualiza cache de preços"""
        self.price_cache[symbol] = {
            'price': price,
            'timestamp': datetime.now()
        }
    
    def run_trading_cycle(self):
        """Executa um ciclo de trading"""
        try:
            # Verifica período de aquecimento
            if not self._check_warmup_period():
                return
            
            # Verifica se deve analisar mercado
            if not self.market_analyzer.should_analyze():
                return
            
            primary_pair = self._get_config('trading.primary_pair')
            
            # Atualiza cache de preço
            current_price = self.market_analyzer.get_current_price(primary_pair)
            if current_price:
                self._update_price_cache(primary_pair, current_price)
            
            # Gerencia posições existentes
            if self.position_manager.has_position(primary_pair):
                self._manage_existing_position(primary_pair)
            else:
                self._check_entry_opportunity(primary_pair)
            
        except Exception as e:
            logger.error(f"Erro no ciclo de trading: {e}")
    
    def _check_warmup_period(self) -> bool:
        """Verifica período de aquecimento inicial"""
        time_since_start = (datetime.now() - self.bot_start_time).total_seconds()
        warmup_period = self._get_config('strategy.initial_wait_seconds', 300)
        
        if time_since_start < warmup_period:
            remaining = warmup_period - time_since_start
            if int(remaining) % 30 == 0:
                logger.info(f"Período de aquecimento: {remaining:.0f}s restantes")
            return False
        return True
    
    def _manage_existing_position(self, symbol: str):
        """Gerencia posição existente"""
        position = self.position_manager.get_position(symbol)
        current_price = self.market_analyzer.get_current_price(symbol)
        
        if not current_price:
            logger.warning(f"Não foi possível obter preço atual para {symbol}")
            return
        
        # Atualiza cache de preço
        self._update_price_cache(symbol, current_price)
        
        # Log periódico do status da posição
        self._log_position_status(position, current_price)
        
        # Verifica condições de saída com preço atual
        try:
            # Tenta chamar com current_price (versão integrada)
            exit_signal = self.risk_manager.check_exit_conditions(position, current_price)
        except TypeError:
            # Fallback para versão original sem current_price
            exit_signal = self.risk_manager.check_exit_conditions(position)
        
        if exit_signal:
            logger.info(f"Sinal de saída: {exit_signal}")
            self._execute_exit(symbol, position, exit_signal, current_price)
        else:
            # Analisa possível saída por indicadores
            analysis = self.market_analyzer.analyze_market(symbol)
            if analysis and analysis.get('signal'):
                signal = analysis['signal']
                if signal.action.startswith('close_'):
                    self._execute_exit(symbol, position, signal.reason, current_price)
    
    def _log_position_status(self, position, current_price: float):
        """Log periódico do status da posição"""
        # Log a cada 5 minutos
        if hasattr(position, 'last_status_log'):
            time_since_log = (datetime.now() - position.last_status_log).total_seconds()
            if time_since_log < 300:  # 5 minutos
                return
        
        # Calcula PnL atual
        unrealized_pnl = self.position_manager.calculate_unrealized_pnl(position, current_price)
        
        # Calcula targets se ainda não existirem
        targets = self._calculate_exit_targets(position.entry_price, position.side.value)
        
        logger.info(f"Status da posição {position.symbol}: "
                   f"Preço atual: ${current_price:.4f} | "
                   f"PnL: ${unrealized_pnl:.2f} | "
                   f"TP: ${targets['take_profit']:.4f} | "
                   f"SL: ${targets['stop_loss']:.4f}")
        
        # Marca timestamp do último log
        position.last_status_log = datetime.now()
    
    def _check_entry_opportunity(self, symbol: str):
        """Verifica oportunidade de entrada"""
        # Validações pré-entrada
        if not self.risk_manager.can_open_position():
            logger.debug("Não pode abrir nova posição (limites)")
            return
        
        if not self.position_manager.can_open_position(symbol):
            logger.debug("Não pode abrir posição (cooldown ou limite)")
            return
        
        # Análise de mercado
        analysis = self.market_analyzer.analyze_market(symbol)
        
        if not analysis or not analysis.get('signal'):
            return
        
        signal = analysis['signal']
        
        # Valida sinal
        if signal.action in ['long', 'short']:
            if self.risk_manager.validate_signal(signal, analysis['indicators']):
                logger.info(f"Sinal validado: {signal.action.upper()}")
                self._execute_entry(symbol, signal, analysis['price'])
            else:
                logger.info(f"Sinal rejeitado pelos filtros de risco")
    
    def _execute_entry(self, symbol: str, signal, price: float):
        """Executa entrada em posição"""
        try:
            # Calcula valores de saída esperados
            exit_targets = self._calculate_exit_targets(price, signal.action)
            
            # Calcula tamanho da posição
            size = self.position_manager.calculate_position_size(
                symbol, price, signal.action
            )
            
            # Executa ordem usando método seguro
            result = self._safe_open_position(
                symbol=symbol,
                side=signal.action,
                size=size,
                price=price,
                reason=signal.reason,
                confidence=signal.confidence
            )
            
            if result and result.get('success', False):
                trade = result.get('trade')
                
                # Log detalhado da entrada
                logger.info(f"Posição aberta com sucesso!")
                logger.info(f"Símbolo: {symbol} | Lado: {signal.action.upper()}")
                logger.info(f"Preço de entrada: ${price:.4f}")
                logger.info(f"Tamanho: {size}")
                logger.info(f"Take Profit previsto: ${exit_targets['take_profit']:.4f}")
                logger.info(f"Stop Loss previsto: ${exit_targets['stop_loss']:.4f}")
                
                # Adiciona informações extras ao trade para o CSV
                trade_data = {
                    'trade': trade if trade else {
                        'symbol': symbol,
                        'side': signal.action,
                        'action': 'open',
                        'quantity': size,
                        'entry_price': price,
                        'pnl': 0.0,
                        'entry_time': datetime.now(),
                        'reason': signal.reason
                    },
                    'predicted_tp': exit_targets['take_profit'],
                    'predicted_sl': exit_targets['stop_loss'],
                    'current_price_at_entry': price,
                    'signal_confidence': signal.confidence,
                    'signal_reason': signal.reason
                }
                
                # Log no CSV com dados estendidos
                self.csv_logger.log_trade_extended(trade_data)
                
            else:
                error_msg = result.get('error', 'Erro desconhecido') if result else 'Nenhum resultado'
                logger.warning(f"Falha ao abrir posição: {error_msg}")
                
        except Exception as e:
            logger.error(f"Erro ao executar entrada: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _execute_exit(self, symbol: str, position, reason: str, current_price: float = None):
        """Executa saída de posição com tratamento robusto de argumentos"""
        try:
            if current_price is None:
                current_price = self.market_analyzer.get_current_price(symbol)
                
            if not current_price:
                logger.error(f"Não foi possível obter preço para fechar posição {symbol}")
                return
            
            # Calcula targets originais para comparação
            original_targets = self._calculate_exit_targets(position.entry_price, position.side.value)
            
            # SOLUÇÃO ROBUSTA: Tenta múltiplas assinaturas do close_position
            result = self._safe_close_position(symbol, current_price, reason)
            
            if result and result.get('success', False):
                trade = result.get('trade')
                pnl = result.get('pnl', 0)
                
                # Log detalhado da saída
                logger.info(f"Posição fechada: PnL ${pnl:.2f}")
                logger.info(f"Preço de entrada: ${position.entry_price:.4f}")
                logger.info(f"Preço de saída: ${current_price:.4f}")
                logger.info(f"TP previsto era: ${original_targets['take_profit']:.4f}")
                logger.info(f"SL previsto era: ${original_targets['stop_loss']:.4f}")
                logger.info(f"Motivo: {reason}")
                
                # Se temos dados do trade, registra no CSV
                if trade:
                    # Adiciona informações extras ao trade para o CSV
                    trade_data = {
                        'trade': trade,
                        'predicted_tp': original_targets['take_profit'],
                        'predicted_sl': original_targets['stop_loss'],
                        'actual_exit_price': current_price,
                        'exit_reason': reason,
                        'target_hit': self._check_target_hit(
                            position.entry_price, 
                            current_price, 
                            original_targets, 
                            position.side.value
                        )
                    }
                    
                    # Log no CSV com dados estendidos
                    self.csv_logger.log_trade_extended(trade_data)
                    
                    # Atualiza estatísticas
                    self.risk_manager.update_statistics(trade)
                else:
                    # Log básico se não temos objeto trade
                    trade_dict = {
                        'symbol': symbol,
                        'side': position.side.value,
                        'action': 'close',
                        'quantity': getattr(position, 'quantity', 0),
                        'entry_price': position.entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                        'entry_time': getattr(position, 'entry_time', None),
                        'exit_time': datetime.now(),
                        'reason': reason
                    }
                    
                    trade_data = {
                        'trade': trade_dict,
                        'predicted_tp': original_targets['take_profit'],
                        'predicted_sl': original_targets['stop_loss'],
                        'actual_exit_price': current_price,
                        'exit_reason': reason,
                        'target_hit': self._check_target_hit(
                            position.entry_price, 
                            current_price, 
                            original_targets, 
                            position.side.value
                        )
                    }
                    
                    self.csv_logger.log_trade_extended(trade_data)
                
            else:
                error_msg = result.get('error', 'Erro desconhecido') if result else 'Nenhum resultado'
                logger.warning(f"Falha ao fechar posição: {error_msg}")
                
                # Força limpeza da posição no tracking
                try:
                    if hasattr(self.position_manager, 'positions'):
                        self.position_manager.positions.pop(symbol, None)
                    logger.info(f"Posição {symbol} removida do tracking após falha")
                except Exception as cleanup_error:
                    logger.warning(f"Erro na limpeza: {cleanup_error}")
                
        except Exception as e:
            logger.error(f"Erro ao executar saída: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
            # Em caso de erro crítico, força limpeza
            try:
                if hasattr(self.position_manager, 'positions'):
                    self.position_manager.positions.pop(symbol, None)
                logger.warning(f"Posição {symbol} removida forçadamente após erro crítico")
            except:
                pass
    
    def _safe_close_position(self, symbol: str, price: float, reason: str):
        """
        Tenta fechar posição usando múltiplas assinaturas de forma segura
        Esta função resolve o erro 'percentage' definitivamente
        """
        
        # Lista de estratégias ordenadas por probabilidade de sucesso
        strategies = [
            # Estratégia 1: Apenas argumentos básicos (mais comum)
            lambda: self.position_manager.close_position(symbol=symbol, price=price, reason=reason),
            
            # Estratégia 2: Apenas symbol e price
            lambda: self.position_manager.close_position(symbol=symbol, price=price),
            
            # Estratégia 3: Argumentos posicionais
            lambda: self.position_manager.close_position(symbol, price, reason),
            
            # Estratégia 4: Argumentos posicionais básicos
            lambda: self.position_manager.close_position(symbol, price),
            
            # Estratégia 5: Apenas symbol
            lambda: self.position_manager.close_position(symbol),
            
            # Estratégia 6: Com percentage (para versões que exigem)
            lambda: self.position_manager.close_position(symbol=symbol, price=price, reason=reason, percentage=100.0),
            
            # Estratégia 7: Chamada mínima com percentage
            lambda: self.position_manager.close_position(symbol=symbol, percentage=100.0),
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logger.debug(f"Tentando estratégia {i} para close_position")
                result = strategy()
                
                # Normaliza resultado
                if result is None:
                    continue
                
                if isinstance(result, dict):
                    if result.get('success') is not False:
                        logger.debug(f"✅ Estratégia {i} bem-sucedida")
                        return result
                else:
                    # Se não é dict, assume sucesso
                    logger.debug(f"✅ Estratégia {i} bem-sucedida (resultado não-dict)")
                    return {
                        'success': True,
                        'trade': result if hasattr(result, 'symbol') else None,
                        'pnl': getattr(result, 'pnl', 0) if hasattr(result, 'pnl') else 0,
                        'result': result
                    }
                    
            except TypeError as te:
                if 'percentage' in str(te):
                    logger.debug(f"Estratégia {i} falhou: erro 'percentage' - {te}")
                else:
                    logger.debug(f"Estratégia {i} falhou: TypeError - {te}")
                continue
                
            except Exception as e:
                logger.debug(f"Estratégia {i} falhou: {type(e).__name__} - {e}")
                continue
        
        # Se todas as estratégias falharam
        logger.error("Todas as estratégias de close_position falharam")
        return {
            'success': False,
            'error': 'Todas as estratégias de fechamento falharam',
            'trade': None,
            'pnl': 0
        }
    
    def _safe_open_position(self, symbol: str, side: str, size: float, price: float, reason: str = None, confidence: float = None):
        """
        Abre posição de forma segura com múltiplas assinaturas
        """
        
        open_strategies = [
            # Estratégia 1: Argumentos completos
            lambda: self.position_manager.open_position(
                symbol=symbol, side=side, size=size, price=price, reason=reason, confidence=confidence
            ),
            
            # Estratégia 2: Sem confidence
            lambda: self.position_manager.open_position(
                symbol=symbol, side=side, size=size, price=price, reason=reason
            ),
            
            # Estratégia 3: Apenas argumentos básicos
            lambda: self.position_manager.open_position(
                symbol=symbol, side=side, size=size, price=price
            ),
            
            # Estratégia 4: Argumentos posicionais
            lambda: self.position_manager.open_position(symbol, side, size, price),
        ]
        
        for i, strategy in enumerate(open_strategies, 1):
            try:
                logger.debug(f"Tentando estratégia open {i}")
                result = strategy()
                
                if result is None:
                    continue
                
                if isinstance(result, dict):
                    if result.get('success') is not False:
                        logger.debug(f"✅ Estratégia open {i} bem-sucedida")
                        return result
                else:
                    logger.debug(f"✅ Estratégia open {i} bem-sucedida (resultado não-dict)")
                    return {
                        'success': True,
                        'trade': result,
                        'result': result
                    }
                    
            except Exception as e:
                logger.debug(f"Estratégia open {i} falhou: {e}")
                continue
        
        logger.error("Todas as estratégias de open_position falharam")
        return {
            'success': False,
            'error': 'Todas as estratégias de abertura falharam'
        }
    
    def _check_target_hit(self, entry_price: float, exit_price: float, 
                         targets: Dict[str, float], side: str) -> str:
        """Verifica qual target foi atingido"""
        tp_price = targets['take_profit']
        sl_price = targets['stop_loss']
        
        if side.lower() == 'long':
            if exit_price >= tp_price:
                return 'TAKE_PROFIT'
            elif exit_price <= sl_price:
                return 'STOP_LOSS'
        else:  # short
            if exit_price <= tp_price:
                return 'TAKE_PROFIT'
            elif exit_price >= sl_price:
                return 'STOP_LOSS'
        
        return 'MANUAL'
    
    def run(self):
        """Loop principal do bot"""
        self.running = True
        logger.info("Bot iniciado")
        
        cycle_count = 0
        analysis_interval = self._get_config('strategy.analysis_interval_seconds', 60)
        
        try:
            while self.running:
                # Sincronização periódica
                if not self.paper_trading and cycle_count % 20 == 0:
                    self._sync_with_exchange()
                
                # Executa ciclo de trading
                self.run_trading_cycle()
                
                # Status periódico
                cycle_count += 1
                if cycle_count % 10 == 0:
                    self.print_status()
                
                # Aguarda próximo ciclo
                time.sleep(analysis_interval)
                
        except KeyboardInterrupt:
            logger.info("Bot interrompido pelo usuário")
        except Exception as e:
            logger.error(f"Erro fatal: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.shutdown()
    
    def print_status(self):
        """Imprime status atual do bot"""
        print("\n" + "="*60)
        print(f"BINGX BOT - {'PAPER' if self.paper_trading else 'REAL'}")
        print(f"Tempo de execução: {(datetime.now() - self.bot_start_time)}")
        print("="*60)
        
        # Status das posições com preços atuais
        self.position_manager.print_positions()
        
        # Preços atuais em cache
        if self.price_cache:
            print("\nPreços atuais:")
            for symbol, data in self.price_cache.items():
                age = (datetime.now() - data['timestamp']).total_seconds()
                print(f"{symbol}: ${data['price']:.4f} (há {age:.0f}s)")
        
        # Estatísticas
        stats = self.risk_manager.get_statistics()
        print(f"\nTrades hoje: {stats['daily_trades']}")
        print(f"PnL total: ${stats['total_pnl']:.2f}")
        print(f"Win rate: {stats['win_rate']:.1f}%")
        print("="*60)
    
    def print_final_stats(self):
        """Imprime estatísticas finais"""
        logger.info("\nEstatísticas Finais:")
        stats = self.risk_manager.get_statistics()
        
        logger.info(f"Total de trades: {stats['total_trades']}")
        logger.info(f"PnL Total: ${stats['total_pnl']:.2f}")
        logger.info(f"Win Rate: {stats['win_rate']:.1f}%")
        logger.info(f"Maior ganho: ${stats['best_trade']:.2f}")
        logger.info(f"Maior perda: ${stats['worst_trade']:.2f}")
    
    def shutdown(self):
        """Desliga o bot de forma segura"""
        self.running = False
        logger.info("Desligando bot...")
        
        # Cancela ordens pendentes se houver
        if not self.paper_trading and self.api:
            try:
                self.position_manager.cancel_all_orders()
            except Exception as e:
                logger.warning(f"Erro ao cancelar ordens: {e}")
        
        # Salva estado final
        self.print_final_stats()
        logger.info("Bot finalizado com sucesso")
    
    def _diagnose_components(self):
        """Executa diagnóstico dos componentes do bot"""
        try:
            logger.info("=== DIAGNÓSTICO DOS COMPONENTES ===")
            
            # Diagnóstico do PositionManager
            logger.info("PositionManager:")
            if hasattr(self.position_manager, 'get_method_signatures'):
                signatures = self.position_manager.get_method_signatures()
                for method, info in signatures.items():
                    params_str = ", ".join(info.get('params', []))
                    logger.info(f"  {method}({params_str})")
            
            # Diagnóstico do RiskManager
            logger.info("RiskManager disponível: " + str(hasattr(self, 'risk_manager')))
            
            # Diagnóstico do MarketAnalyzer
            logger.info("MarketAnalyzer disponível: " + str(hasattr(self, 'market_analyzer')))
            
            # Diagnóstico do CSVLogger
            logger.info("CSVLogger disponível: " + str(hasattr(self, 'csv_logger')))
            
            logger.info("=== FIM DO DIAGNÓSTICO ===")
            
        except Exception as e:
            logger.warning(f"Erro no diagnóstico: {e}")