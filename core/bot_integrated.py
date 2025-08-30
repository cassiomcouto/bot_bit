#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Integrado com Sistema de Otimização IA
Versão completa com todos os sistemas implementados
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
from core.analysis.ai_optimizer import AIConfigOptimizer
from utils.csv_logger import CSVLogger

logger = logging.getLogger(__name__)

class BingXFuturesBotIntegrated:
    """Bot principal com sistema IA de otimização integrado"""
    
    def __init__(self, config_path: str = "config/futures_config.yaml"):
        """
        Inicializa o bot de trading com otimização IA
        
        Args:
            config_path: Caminho para arquivo de configuração
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.running = False
        self.bot_start_time = datetime.now()
        
        # Estado do bot
        # Configuração de paper trading - FORÇADO PARA REAL
        paper_config = self._get_config('advanced.paper_trading', {})
        config_paper_trading = paper_config.get('enabled', False)  # Default False
        
        # FORÇA TRADING REAL se config diz False
        if not config_paper_trading:
            self.paper_trading = False
            print("🔴 TRADING REAL ATIVO - Ordens serão executadas na BingX!")
        else:
            self.paper_trading = True
            print("🟡 Paper trading ativo - Apenas simulação")
        
        # Log importante sobre modo de trading
        if self.paper_trading:
            logger.warning("🟡 MODO PAPER TRADING ATIVO - Nenhum trade real será executado")
        else:
            logger.critical("🔴 MODO TRADING REAL ATIVO - Trades reais serão executados!")
        
        # Inicializa componentes principais
        self._initialize_components()
        
        # Inicializa sistema IA (se habilitado)
        self.ai_optimization_enabled = self._get_config('advanced_settings.ai_optimization.enabled', True)
        if self.ai_optimization_enabled:
            self.ai_optimizer = AIConfigOptimizer(
                config_path=self.config_path,
                logs_path="logs/",
                snapshots_path="config/snapshots/"
            )
            self.ai_optimizer.start_monitoring()
            logger.info("Sistema de otimização IA ativado")
        else:
            self.ai_optimizer = None
            logger.info("Sistema de otimização IA desabilitado")
        
        # Sincronização inicial
        if not self.paper_trading:
            self._sync_with_exchange()
        
        logger.info(f"Bot integrado inicializado - Modo: {'PAPER' if self.paper_trading else 'REAL'}")
    
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
    
# Em core/bot_integrated.py
# Substitua a seção _initialize_components() por esta versão:

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
        
        # *** CORREÇÃO: Usar PositionManagerAdapter ***
        from core.position.adapters.position_adapter import PositionManagerAdapter
        
        # Cria PositionManager original
        original_position_manager = PositionManager(self.config, self.api, self.paper_trading)
        
        # Envolve com adaptador que resolve os problemas de compatibilidade
        self.position_manager = PositionManagerAdapter(original_position_manager)
        
        # Risk Manager
        self.risk_manager = RiskManager(self.config)
        
        # Logger CSV
        self.csv_logger = CSVLogger("logs/trades.csv")
        
        # Estado inicial
        if self.paper_trading:
            initial_balance = self._get_config('advanced.paper_trading.initial_balance_usdt', 100.0)
            # Usa o adaptador para definir o saldo
            self.position_manager.position_manager.set_balance(initial_balance)

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
    
    def reload_config_if_updated(self):
        """Recarrega configuração se foi atualizada pelo sistema IA"""
        if not self.ai_optimizer:
            return False
        
        try:
            # Verifica se existe snapshot mais recente que a configuração atual
            snapshot_name, snapshot_config = self.ai_optimizer.get_latest_snapshot()
            
            if snapshot_config and 'metadata' in snapshot_config:
                snapshot_time = snapshot_config['metadata']['optimization']['timestamp']
                
                # Se snapshot é mais recente que o início do bot, considera aplicar
                if snapshot_time > self.bot_start_time.isoformat():
                    logger.info(f"Nova configuração otimizada disponível: {snapshot_name}")
                    
                    # Verifica confidence level antes de aplicar
                    confidence = snapshot_config['metadata']['optimization']['confidence_level']
                    min_confidence = self._get_config('advanced_settings.ai_optimization.min_confidence_to_apply', 0.7)
                    
                    if confidence >= min_confidence:
                        logger.info(f"Aplicando configuração otimizada (confiança: {confidence:.2f})")
                        
                        # Recarrega configuração
                        self.config = self._load_config()
                        
                        # Reinicializa componentes que dependem da configuração
                        self.market_analyzer = MarketAnalyzer(self.config)
                        self.position_manager.config = self.config
                        self.risk_manager.config = self.config
                        
                        return True
                    else:
                        logger.info(f"Confiança insuficiente para aplicar: {confidence:.2f} < {min_confidence}")
            
        except Exception as e:
            logger.error(f"Erro ao verificar configuração atualizada: {e}")
        
        return False
    
    def run_trading_cycle(self):
        """Executa um ciclo de trading com verificação de configuração"""
        try:
            # Verifica período de aquecimento
            if not self._check_warmup_period():
                return
            
            # Verifica kill switch
            if self.risk_manager.is_kill_switch_active():
                logger.error("Trading suspenso - Kill switch ativo")
                return
            
            # Verifica se deve analisar mercado
            if not self.market_analyzer.should_analyze():
                return
            
            primary_pair = self._get_config('trading.primary_pair')
            
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
        warmup_period = self._get_config('strategy.initial_wait_seconds', 60)
        
        if time_since_start < warmup_period:
            remaining = warmup_period - time_since_start
            if int(remaining) % 30 == 0:
                logger.info(f"Período de aquecimento: {remaining:.0f}s restantes")
            return False
        return True
    
    def _manage_existing_position(self, symbol: str):
        """Gerencia posição existente com controles de risco integrados"""
        position = self.position_manager.get_position(symbol)
        current_price = self.market_analyzer.get_current_price(symbol)
        
        if not current_price:
            logger.warning(f"Não foi possível obter preço para {symbol}")
            return
        
        # Verificações de timing
        should_close_timing, timing_reason = self.position_manager.should_close_by_timing(symbol, current_price)
        if should_close_timing:
            logger.info(f"Fechando por timing: {timing_reason}")
            self._execute_exit(symbol, position, timing_reason, current_price)
            return
        
        # Verificações de risco (Stop Loss, Take Profit)
        exit_reason = self.risk_manager.check_exit_conditions(position, current_price)
        if exit_reason:
            logger.info(f"Fechando por risco: {exit_reason}")
            self._execute_exit(symbol, position, exit_reason, current_price)
            return
        
        # Take profit parcial
        should_take, tp_reason, tp_percentage = self.position_manager.check_take_profit_conditions(symbol, current_price)
        if should_take and tp_percentage < 1.0:
            logger.info(f"Executando take profit parcial: {tp_reason}")
            self._execute_partial_exit(symbol, position, tp_reason, current_price, tp_percentage)
            return
        elif should_take:
            logger.info(f"Executando take profit total: {tp_reason}")
            self._execute_exit(symbol, position, tp_reason, current_price)
            return
        
        # Análise técnica para saída
        current_positions = {symbol: position}
        analysis = self.market_analyzer.analyze_market(symbol)
        if analysis and analysis.get('signal'):
            signal = analysis['signal']
            if signal.action.startswith('close_'):
                confidence_threshold = 0.70
                if signal.confidence >= confidence_threshold:
                    logger.info(f"Sinal técnico de saída: {signal.reason}")
                    self._execute_exit(symbol, position, f"Sinal técnico: {signal.reason}", current_price)
    
    def _check_entry_opportunity(self, symbol: str):
        """Verifica oportunidade de entrada com validações rigorosas"""
        # Validações pré-entrada (Risk Manager)
        if not self.risk_manager.can_open_position():
            logger.debug("Não pode abrir nova posição (limites de risco)")
            return
        
        # Validações do Position Manager
        if not self.position_manager.can_open_position(symbol):
            logger.debug("Não pode abrir posição (cooldown ou limite)")
            return
        
        # Análise de mercado
        analysis = self.market_analyzer.analyze_market(symbol)
        
        if not analysis or not analysis.get('signal'):
            return
        
        signal = analysis['signal']
        
        # Valida sinal com Risk Manager
        if signal.action in ['long', 'short']:
            if self.risk_manager.validate_signal(signal, analysis['indicators']):
                logger.info(f"Sinal validado: {signal.action.upper()}")
                self._execute_entry(symbol, signal, analysis['price'])
            else:
                logger.info(f"Sinal rejeitado pelos filtros de risco")
    
    def _execute_entry(self, symbol: str, signal, price: float):
        """Executa entrada em posição"""
        try:
            # Calcula tamanho da posição
            size = self.position_manager.calculate_position_size(
                symbol, price, signal.action
            )
            
            # Executa ordem
            result = self.position_manager.open_position(
                symbol=symbol,
                side=signal.action,
                size=size,
                price=price,
                reason=signal.reason,
                confidence=signal.confidence
            )
            
            if result['success']:
                logger.info(f"Posição aberta com sucesso!")
                # Log no CSV
                self.csv_logger.log_trade(result['trade'])
            else:
                logger.warning(f"Falha ao abrir posição: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Erro ao executar entrada: {e}")
    
    def _execute_exit(self, symbol: str, position, reason: str, current_price: float):
        """Executa saída completa de posição"""
        try:
            result = self.position_manager.close_position(
                symbol=symbol,
                price=current_price,
                reason=reason,
                percentage=1.0
            )
            
            if result['success']:
                logger.info(f"Posição fechada: PnL ${result['pnl']:.2f}")
                # Log no CSV
                self.csv_logger.log_trade(result['trade'])
                # Atualiza estatísticas
                self.risk_manager.update_statistics(result['trade'])
            else:
                logger.warning(f"Falha ao fechar posição: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Erro ao executar saída: {e}")
    
    def _execute_partial_exit(self, symbol: str, position, reason: str, 
                            current_price: float, percentage: float):
        """Executa saída parcial de posição"""
        try:
            result = self.position_manager.close_position(
                symbol=symbol,
                price=current_price,
                reason=reason,
                percentage=percentage
            )
            
            if result['success']:
                logger.info(f"Fechamento parcial ({percentage*100:.0f}%): PnL ${result['pnl']:.2f}")
                # Log no CSV
                self.csv_logger.log_trade(result['trade'])
                # Atualiza estatísticas
                self.risk_manager.update_statistics(result['trade'])
            else:
                logger.warning(f"Falha no fechamento parcial: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"Erro ao executar saída parcial: {e}")
    
    def run(self):
        """Loop principal do bot com sistema IA integrado"""
        self.running = True
        logger.info("Bot integrado iniciado")
        
        cycle_count = 0
        analysis_interval = self._get_config('strategy.analysis_interval_seconds', 60)
        config_check_interval = 20  # Verifica configuração a cada 20 ciclos
        
        try:
            while self.running:
                # Sincronização periódica
                if not self.paper_trading and cycle_count % 20 == 0:
                    self._sync_with_exchange()
                
                # Verifica configuração atualizada pelo sistema IA
                if self.ai_optimization_enabled and cycle_count % config_check_interval == 0:
                    if self.reload_config_if_updated():
                        logger.info("Configuração recarregada - Continuando com novos parâmetros")
                
                # Executa ciclo de trading
                self.run_trading_cycle()
                
                # Status periódico
                cycle_count += 1
                if cycle_count % 10 == 0:
                    self.print_status()
                
                # Verifica kill switch
                if self.risk_manager.is_kill_switch_active():
                    logger.error("Bot pausado - Kill switch ativo!")
                    break
                
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
        """Imprime status atual do bot com informações IA"""
        print("\n" + "="*60)
        print(f"BINGX BOT INTEGRADO - {'PAPER' if self.paper_trading else 'REAL'}")
        print(f"Tempo de execução: {(datetime.now() - self.bot_start_time)}")
        
        if self.ai_optimization_enabled:
            print("Sistema IA: ATIVO")
        
        print("="*60)
        
        # Status das posições
        self.position_manager.print_positions()
        
        # Estatísticas de risco
        risk_summary = self.risk_manager.get_risk_summary()
        stats = self.risk_manager.get_statistics()
        
        print(f"\nRISCO & ESTATÍSTICAS:")
        print(f"Trades hoje: {risk_summary['daily_trades']}")
        print(f"PnL diário: ${risk_summary['daily_pnl']:+.2f}")
        print(f"PnL total: ${stats['total_pnl']:+.2f}")
        print(f"Win rate: {stats['win_rate']:.1f}%")
        print(f"Perdas consecutivas: {risk_summary['consecutive_losses']}")
        print(f"Drawdown atual: {risk_summary['current_drawdown_pct']:.1f}%")
        
        if risk_summary['kill_switch_active']:
            print("KILL SWITCH ATIVO!")
        elif not risk_summary['can_trade']:
            print("Trading pausado por limites")
        else:
            print("Operacional")
        
        # Status do sistema IA
        if self.ai_optimization_enabled and self.ai_optimizer:
            try:
                snapshot_name, _ = self.ai_optimizer.get_latest_snapshot()
                if snapshot_name:
                    print(f"Último snapshot IA: {snapshot_name}")
            except:
                pass
            
        print("="*60)
    
    def print_final_stats(self):
        """Imprime estatísticas finais com informações IA"""
        logger.info("\nESTATÍSTICAS FINAIS:")
        stats = self.risk_manager.get_statistics()
        
        logger.info(f"Total de trades: {stats['total_trades']}")
        logger.info(f"PnL Total: ${stats['total_pnl']:+.2f}")
        logger.info(f"Win Rate: {stats['win_rate']:.1f}%")
        logger.info(f"Maior ganho: ${stats['best_trade']:+.2f}")
        logger.info(f"Maior perda: ${stats['worst_trade']:+.2f}")
        logger.info(f"Max perdas consecutivas: {stats['max_consecutive_losses']}")
        logger.info(f"Max drawdown: ${stats['max_drawdown']:+.2f}")
        
        if self.risk_manager.is_kill_switch_active():
            logger.warning("Bot finalizado com kill switch ativo")
        
        if self.ai_optimization_enabled:
            logger.info("Sistema de otimização IA estava ativo durante a execução")
    
    def shutdown(self):
        """Desliga o bot de forma segura"""
        self.running = False
        logger.info("Desligando bot integrado...")
        
        # Para sistema IA
        if self.ai_optimizer:
            self.ai_optimizer.stop_monitoring()
            logger.info("Sistema IA parado")
        
        # Cancela ordens pendentes
        if not self.paper_trading and self.api:
            try:
                self.position_manager.cancel_all_orders()
            except Exception as e:
                logger.warning(f"Erro ao cancelar ordens: {e}")
        
        # Salva estado final
        self.print_final_stats()
        logger.info("Bot integrado finalizado com sucesso")