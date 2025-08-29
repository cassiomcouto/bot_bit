#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Futures Bot - Bot especializado em trading de futuros
Integra com o sistema existente BingXFuturesBot
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .base_bot import BaseBot, BotType

# Importação segura do metrics calculator
calculate_portfolio_metrics = None
try:
    from ..analysis.performance.metrics_calculator import calculate_portfolio_metrics
    logger = logging.getLogger(__name__)
    logger.debug("MetricsCalculator importado com sucesso")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.debug(f"MetricsCalculator não disponível: {e}")

class FuturesBot(BaseBot):
    """Bot especializado para trading de futuros"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # Referência ao bot original (será inicializada)
        self.trading_bot: Optional[Any] = None
        
        # Cache de performance
        self._last_performance_update = None
        self._performance_cache = None
    
    def _initialize_components(self):
        """Inicializa componentes específicos do futures bot"""
        try:
            # Importa e inicializa o bot original
            from ...trading_bot import BingXFuturesBot
            
            # Converte configuração para o formato esperado
            config_path = self._create_temp_config()
            
            # Inicializa bot de trading
            self.trading_bot = BingXFuturesBot(config_path)
            
            # Registra componentes
            self.components['trading_bot'] = self.trading_bot
            self.components['api'] = getattr(self.trading_bot, 'api', None)
            self.components['market_analyzer'] = getattr(self.trading_bot, 'market_analyzer', None)
            self.components['position_manager'] = getattr(self.trading_bot, 'position_manager', None)
            self.components['risk_manager'] = getattr(self.trading_bot, 'risk_manager', None)
            self.components['csv_logger'] = getattr(self.trading_bot, 'csv_logger', None)
            
            # Adiciona hooks de eventos
            self._setup_event_hooks()
            
            logger.info(f"Componentes inicializados para bot {self.config.bot_id}")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar componentes: {e}")
            raise
    
    def _execute_trading_cycle(self):
        """Executa um ciclo de trading"""
        if not self.trading_bot:
            logger.error("Trading bot não inicializado")
            return
        
        try:
            # Executa ciclo do bot original
            self.trading_bot.run_trading_cycle()
            
            # Atualiza métricas se necessário
            self._update_performance_metrics()
            
        except Exception as e:
            logger.error(f"Erro no ciclo de trading: {e}")
            raise
    
    def _cleanup_resources(self):
        """Limpa recursos específicos"""
        try:
            if self.trading_bot:
                # Para o bot original se estiver rodando
                if hasattr(self.trading_bot, 'running') and self.trading_bot.running:
                    self.trading_bot.shutdown()
                
                # Limpa referência
                self.trading_bot = None
            
            # Limpa componentes
            self.components.clear()
            
            logger.info(f"Recursos limpos para bot {self.config.bot_id}")
            
        except Exception as e:
            logger.error(f"Erro na limpeza de recursos: {e}")
    
    def _create_temp_config(self) -> str:
        """Cria arquivo temporário de configuração"""
        import tempfile
        import yaml
        import os
        
        # Converte configuração interna para formato YAML
        yaml_config = self._convert_config_to_yaml()
        
        # Cria arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_config, f, default_flow_style=False, allow_unicode=True)
            temp_path = f.name
        
        # Registra para limpeza posterior
        if not hasattr(self, '_temp_files'):
            self._temp_files = []
        self._temp_files.append(temp_path)
        
        return temp_path
    
    def _convert_config_to_yaml(self) -> Dict[str, Any]:
        """Converte configuração interna para formato YAML esperado"""
        # Configuração padrão baseada no formato esperado pelo BingXFuturesBot
        default_config = {
            'trading': {
                'primary_pair': 'BTCUSDT',
                'max_positions': 1,
                'base_amount_usdt': 100.0
            },
            'risk_management': {
                'stop_loss_percent': 2.0,
                'take_profit_percent': 3.0,
                'max_drawdown_percent': 10.0,
                'max_daily_trades': 10,
                'cooldown_minutes': 30
            },
            'strategy': {
                'analysis_interval_seconds': 60,
                'primary_exchange': 'bingx',
                'initial_wait_seconds': 300
            },
            'exchanges': {
                'bingx': {
                    'api_key': 'your_api_key',
                    'secret_key': 'your_secret_key',
                    'testnet': True
                }
            },
            'advanced': {
                'paper_trading': {
                    'enabled': True,
                    'initial_balance_usdt': 1000.0
                }
            },
            'ai_futures': {
                'enabled': True,
                'scoring': {
                    'min_score_long': 6.0,
                    'min_score_short': 6.0
                },
                'filters': {
                    'min_confidence': 0.7
                },
                'signals': {
                    'allow_long': True,
                    'allow_short': True
                }
            }
        }
        
        # Merge com configuração atual
        return self._deep_merge(default_config, self.config.config)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge profundo de dicionários"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _setup_event_hooks(self):
        """Configura hooks de eventos para integração"""
        try:
            # Hook para trades - intercepta logs do CSV
            if hasattr(self.trading_bot, 'csv_logger'):
                original_log = self.trading_bot.csv_logger.log_trade_extended
                
                def hooked_log(trade_data):
                    # Chama método original
                    result = original_log(trade_data)
                    
                    # Atualiza nossas métricas
                    self._process_trade_event(trade_data)
                    
                    return result
                
                # Substitui método
                self.trading_bot.csv_logger.log_trade_extended = hooked_log
            
        except Exception as e:
            logger.warning(f"Erro ao configurar hooks: {e}")
    
    def _process_trade_event(self, trade_data: Dict[str, Any]):
        """Processa evento de trade"""
        try:
            trade = trade_data.get('trade', {})
            
            if isinstance(trade, dict):
                # Atualiza métricas do bot
                self.update_trade_metrics(trade)
                
                # Invalida cache de performance
                self._performance_cache = None
                self._last_performance_update = None
                
        except Exception as e:
            logger.error(f"Erro ao processar evento de trade: {e}")
    
    def _update_performance_metrics(self):
        """Atualiza métricas de performance periodicamente"""
        now = datetime.now()
        
        # Atualiza a cada 5 minutos
        if (self._last_performance_update and 
            (now - self._last_performance_update).total_seconds() < 300):
            return
        
        try:
            # Carrega dados de trades do CSV
            import pandas as pd
            import os
            
            csv_path = "logs/trades.csv"
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                
                if not df.empty and calculate_portfolio_metrics:
                    # Calcula métricas usando o sistema avançado
                    self._performance_cache = calculate_portfolio_metrics(df)
                    self._last_performance_update = now
                    
                    # Atualiza métricas básicas do bot
                    if hasattr(self._performance_cache, 'total_pnl'):
                        self.metrics.total_pnl = self._performance_cache.total_pnl
                else:
                    logger.debug("Métricas avançadas não disponíveis ou dados vazios")
                    
        except Exception as e:
            logger.debug(f"Erro ao atualizar métricas de performance: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtém resumo de performance estendido"""
        # Obtém resumo base
        summary = super().get_performance_summary()
        
        # Adiciona métricas avançadas se disponíveis
        if self._performance_cache and calculate_portfolio_metrics:
            try:
                advanced_metrics = {
                    'win_rate_detailed': self._performance_cache.win_rate,
                    'profit_factor': self._performance_cache.profit_factor,
                    'sharpe_ratio': self._performance_cache.sharpe_ratio,
                    'max_drawdown': self._performance_cache.max_drawdown,
                    'expectancy': self._performance_cache.expectancy,
                    'average_win': self._performance_cache.average_win,
                    'average_loss': self._performance_cache.average_loss,
                    'largest_win': self._performance_cache.largest_win,
                    'largest_loss': self._performance_cache.largest_loss
                }
                
                summary.update(advanced_metrics)
            except AttributeError as e:
                logger.debug(f"Erro ao acessar métricas avançadas: {e}")
        
        # Adiciona status dos componentes
        if self.trading_bot:
            summary['paper_trading'] = getattr(self.trading_bot, 'paper_trading', True)
            summary['current_balance'] = self._get_current_balance()
            summary['active_positions'] = self._get_active_positions_count()
        
        return summary
    
    def _get_current_balance(self) -> float:
        """Obtém saldo atual"""
        try:
            if (self.trading_bot and 
                hasattr(self.trading_bot, 'position_manager') and
                hasattr(self.trading_bot.position_manager, 'current_balance')):
                return float(self.trading_bot.position_manager.current_balance)
        except:
            pass
        return 0.0
    
    def _get_active_positions_count(self) -> int:
        """Obtém número de posições ativas"""
        try:
            if (self.trading_bot and 
                hasattr(self.trading_bot, 'position_manager') and
                hasattr(self.trading_bot.position_manager, 'positions')):
                return len(self.trading_bot.position_manager.positions)
        except:
            pass
        return 0
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Obtém status detalhado específico do futures bot"""
        status = self.get_status_dict()
        
        # Adiciona informações específicas de futuros
        if self.trading_bot:
            futures_info = {
                'primary_pair': getattr(self.trading_bot, 'price_cache', {}).keys(),
                'paper_trading_mode': getattr(self.trading_bot, 'paper_trading', True),
                'bot_start_time': getattr(self.trading_bot, 'bot_start_time', None),
                'last_cycle_time': getattr(self.trading_bot, 'last_cycle_time', None),
                'current_prices': getattr(self.trading_bot, 'price_cache', {}),
                'component_status': {
                    name: component is not None 
                    for name, component in self.components.items()
                }
            }
            
            # Formata timestamps
            if futures_info['bot_start_time']:
                futures_info['bot_start_time'] = futures_info['bot_start_time'].isoformat()
            
            if futures_info['last_cycle_time']:
                futures_info['last_cycle_time'] = futures_info['last_cycle_time'].isoformat()
            
            status['futures_specific'] = futures_info
        
        return status
    
    def force_sync(self):
        """Força sincronização com exchange (se não for paper trading)"""
        try:
            if (self.trading_bot and 
                not getattr(self.trading_bot, 'paper_trading', True) and
                hasattr(self.trading_bot, '_sync_with_exchange')):
                self.trading_bot._sync_with_exchange()
                logger.info(f"Sincronização forçada para bot {self.config.bot_id}")
        except Exception as e:
            logger.error(f"Erro na sincronização forçada: {e}")
    
    def get_positions(self) -> Dict[str, Any]:
        """Obtém posições atuais"""
        try:
            if (self.trading_bot and 
                hasattr(self.trading_bot, 'position_manager')):
                
                positions = getattr(self.trading_bot.position_manager, 'positions', {})
                
                # Serializa posições para dict
                serialized_positions = {}
                for symbol, position in positions.items():
                    try:
                        serialized_positions[symbol] = {
                            'symbol': getattr(position, 'symbol', symbol),
                            'side': getattr(position, 'side', '').value if hasattr(getattr(position, 'side', ''), 'value') else str(getattr(position, 'side', '')),
                            'quantity': getattr(position, 'quantity', 0),
                            'entry_price': getattr(position, 'entry_price', 0),
                            'entry_time': getattr(position, 'entry_time', ''),
                            'unrealized_pnl': getattr(position, 'unrealized_pnl', 0)
                        }
                        
                        # Formatar timestamp se necessário
                        entry_time = serialized_positions[symbol]['entry_time']
                        if hasattr(entry_time, 'isoformat'):
                            serialized_positions[symbol]['entry_time'] = entry_time.isoformat()
                            
                    except Exception as e:
                        logger.debug(f"Erro ao serializar posição {symbol}: {e}")
                        serialized_positions[symbol] = {'error': str(e)}
                
                return serialized_positions
                
        except Exception as e:
            logger.error(f"Erro ao obter posições: {e}")
        
        return {}
    
    def __del__(self):
        """Destructor - limpa arquivos temporários"""
        if hasattr(self, '_temp_files'):
            import os
            for temp_file in self._temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except:
                    pass