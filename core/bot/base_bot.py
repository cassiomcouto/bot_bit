#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Bot - Classe base para todos os bots de trading
Define interface comum e funcionalidades compartilhadas
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from ..managers.base_manager import StatefulManager

logger = logging.getLogger(__name__)

class BotType(Enum):
    """Tipos de bot disponíveis"""
    FUTURES = "futures"
    SPOT = "spot" 
    GRID = "grid"
    ARBITRAGE = "arbitrage"
    DCA = "dca"

class BotStatus(Enum):
    """Status do bot"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class BotConfig:
    """Configuração do bot"""
    bot_type: BotType
    bot_id: str
    config: Dict[str, Any]
    template_name: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class BotMetrics:
    """Métricas do bot"""
    uptime: timedelta = timedelta()
    cycles_executed: int = 0
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_pnl: float = 0.0
    last_trade_time: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

class BaseBot(StatefulManager, ABC):
    """Classe base para todos os bots de trading"""
    
    def __init__(self, config: BotConfig):
        """
        Inicializa bot base
        
        Args:
            config: Configuração do bot
        """
        super().__init__(config.config)
        self.config = config
        self.status = BotStatus.INITIALIZING
        self.metrics = BotMetrics()
        
        # Threading
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Timing
        self.start_time: Optional[datetime] = None
        self.last_cycle_time: Optional[datetime] = None
        
        # Components (serão inicializados pelos bots específicos)
        self.components: Dict[str, Any] = {}
        
        # Event hooks
        self._event_handlers: Dict[str, List] = {
            'on_start': [],
            'on_stop': [],
            'on_trade': [],
            'on_error': [],
            'on_cycle': []
        }
        
        logger.info(f"Bot inicializado: {self.config.bot_id} ({self.config.bot_type.value})")
    
    @abstractmethod
    def _initialize_components(self):
        """Inicializa componentes específicos do bot"""
        pass
    
    @abstractmethod
    def _execute_trading_cycle(self):
        """Executa um ciclo de trading"""
        pass
    
    @abstractmethod
    def _cleanup_resources(self):
        """Limpa recursos específicos do bot"""
        pass
    
    def start(self):
        """Inicia o bot"""
        with self._lock:
            if self._running:
                logger.warning(f"Bot {self.config.bot_id} já está executando")
                return
            
            try:
                logger.info(f"Iniciando bot {self.config.bot_id}...")
                
                # Inicializa componentes
                self._initialize_components()
                
                # Configura estado
                self._running = True
                self.status = BotStatus.RUNNING
                self.start_time = datetime.now()
                
                # Inicia thread principal
                self._thread = threading.Thread(target=self._main_loop, daemon=True)
                self._thread.start()
                
                # Dispara evento de início
                self._fire_event('on_start', self)
                
                logger.info(f"Bot {self.config.bot_id} iniciado com sucesso")
                
            except Exception as e:
                logger.error(f"Erro ao iniciar bot {self.config.bot_id}: {e}")
                self.status = BotStatus.ERROR
                self.metrics.last_error = str(e)
                self.metrics.last_error_time = datetime.now()
                raise
    
    def stop(self):
        """Para o bot"""
        with self._lock:
            if not self._running:
                logger.info(f"Bot {self.config.bot_id} já está parado")
                return
            
            logger.info(f"Parando bot {self.config.bot_id}...")
            self.status = BotStatus.STOPPING
            self._running = False
            
            # Aguarda thread principal terminar
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=30.0)
                
                if self._thread.is_alive():
                    logger.warning(f"Thread do bot {self.config.bot_id} não terminou graciosamente")
            
            # Limpa recursos
            try:
                self._cleanup_resources()
            except Exception as e:
                logger.error(f"Erro na limpeza de recursos: {e}")
            
            # Atualiza status final
            self.status = BotStatus.STOPPED
            
            # Dispara evento de parada
            self._fire_event('on_stop', self)
            
            logger.info(f"Bot {self.config.bot_id} parado")
    
    def pause(self):
        """Pausa o bot (mantém thread ativa mas não executa ciclos)"""
        with self._lock:
            if self.status == BotStatus.RUNNING:
                self.status = BotStatus.PAUSED
                logger.info(f"Bot {self.config.bot_id} pausado")
    
    def resume(self):
        """Resume o bot pausado"""
        with self._lock:
            if self.status == BotStatus.PAUSED:
                self.status = BotStatus.RUNNING
                logger.info(f"Bot {self.config.bot_id} resumido")
    
    def is_running(self) -> bool:
        """Verifica se bot está executando"""
        return self._running and self.status == BotStatus.RUNNING
    
    def is_active(self) -> bool:
        """Verifica se bot está ativo (não parado)"""
        return self.status not in [BotStatus.STOPPED, BotStatus.ERROR]
    
    def get_uptime(self) -> timedelta:
        """Calcula tempo de execução"""
        if self.start_time:
            return datetime.now() - self.start_time
        return timedelta()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtém resumo de performance"""
        uptime = self.get_uptime()
        win_rate = 0.0
        
        if self.metrics.total_trades > 0:
            win_rate = (self.metrics.successful_trades / self.metrics.total_trades) * 100
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'uptime_str': str(uptime),
            'cycles_executed': self.metrics.cycles_executed,
            'total_trades': self.metrics.total_trades,
            'win_rate': win_rate,
            'total_pnl': self.metrics.total_pnl,
            'avg_pnl_per_trade': self.metrics.total_pnl / max(1, self.metrics.total_trades),
            'last_trade': self.metrics.last_trade_time.isoformat() if self.metrics.last_trade_time else None,
            'status': self.status.value
        }
    
    def add_event_handler(self, event: str, handler):
        """Adiciona handler de evento"""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)
    
    def remove_event_handler(self, event: str, handler):
        """Remove handler de evento"""
        if event in self._event_handlers and handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)
    
    def _fire_event(self, event: str, *args, **kwargs):
        """Dispara evento para handlers"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Erro no handler de evento {event}: {e}")
    
    def _main_loop(self):
        """Loop principal do bot"""
        logger.info(f"Loop principal iniciado para bot {self.config.bot_id}")
        
        cycle_interval = self.get_config('strategy.analysis_interval_seconds', 60)
        
        try:
            while self._running:
                cycle_start = datetime.now()
                
                try:
                    # Só executa se estiver rodando (não pausado)
                    if self.status == BotStatus.RUNNING:
                        self._execute_trading_cycle()
                        self.metrics.cycles_executed += 1
                        self._fire_event('on_cycle', self)
                    
                    self.last_cycle_time = cycle_start
                    
                except Exception as e:
                    logger.error(f"Erro no ciclo de trading do bot {self.config.bot_id}: {e}")
                    self.metrics.last_error = str(e)
                    self.metrics.last_error_time = datetime.now()
                    self._fire_event('on_error', self, e)
                    
                    # Em caso de erro crítico, para o bot
                    if self._is_critical_error(e):
                        logger.error(f"Erro crítico detectado, parando bot {self.config.bot_id}")
                        self.status = BotStatus.ERROR
                        break
                
                # Aguarda próximo ciclo
                self._wait_next_cycle(cycle_start, cycle_interval)
                
        except Exception as e:
            logger.error(f"Erro fatal no loop do bot {self.config.bot_id}: {e}")
            self.status = BotStatus.ERROR
        finally:
            logger.info(f"Loop principal finalizado para bot {self.config.bot_id}")
    
    def _wait_next_cycle(self, cycle_start: datetime, interval: int):
        """Aguarda próximo ciclo respeitando intervalo"""
        elapsed = (datetime.now() - cycle_start).total_seconds()
        sleep_time = max(0, interval - elapsed)
        
        # Dorme em pequenos incrementos para responder rapidamente ao stop
        while sleep_time > 0 and self._running:
            chunk = min(1.0, sleep_time)  # Máximo 1 segundo por vez
            time.sleep(chunk)
            sleep_time -= chunk
    
    def _is_critical_error(self, error: Exception) -> bool:
        """Determina se um erro é crítico"""
        # Sobrescreva em bots específicos para definir erros críticos
        critical_errors = (
            ConnectionError,
            MemoryError,
        )
        return isinstance(error, critical_errors)
    
    def update_trade_metrics(self, trade_result: Dict[str, Any]):
        """Atualiza métricas de trade"""
        with self._lock:
            self.metrics.total_trades += 1
            self.metrics.last_trade_time = datetime.now()
            
            pnl = trade_result.get('pnl', 0.0)
            self.metrics.total_pnl += pnl
            
            if pnl > 0:
                self.metrics.successful_trades += 1
            else:
                self.metrics.failed_trades += 1
            
            # Dispara evento de trade
            self._fire_event('on_trade', self, trade_result)
    
    def get_status_dict(self) -> Dict[str, Any]:
        """Obtém dicionário completo de status"""
        return {
            'bot_id': self.config.bot_id,
            'bot_type': self.config.bot_type.value,
            'status': self.status.value,
            'template': self.config.template_name,
            'created_at': self.config.created_at.isoformat(),
            'started_at': self.start_time.isoformat() if self.start_time else None,
            'uptime': self.get_uptime().total_seconds(),
            'performance': self.get_performance_summary(),
            'last_cycle': self.last_cycle_time.isoformat() if self.last_cycle_time else None,
            'components': list(self.components.keys()),
            'config_summary': self._get_config_summary()
        }
    
    def _get_config_summary(self) -> Dict[str, Any]:
        """Obtém resumo da configuração"""
        return {
            'primary_pair': self.get_config('trading.primary_pair'),
            'max_positions': self.get_config('trading.max_positions'),
            'stop_loss': self.get_config('risk_management.stop_loss_percent'),
            'take_profit': self.get_config('risk_management.take_profit_percent'),
            'analysis_interval': self.get_config('strategy.analysis_interval_seconds')
        }
    
    def __str__(self) -> str:
        """Representação string do bot"""
        uptime = self.get_uptime()
        return (f"Bot(id={self.config.bot_id}, type={self.config.bot_type.value}, "
                f"status={self.status.value}, uptime={uptime})")
    
    def __repr__(self) -> str:
        return self.__str__()