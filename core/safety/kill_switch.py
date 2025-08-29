# core/safety/kill_switch.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kill Switch - Sistema de parada de emergência
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class KillSwitchTrigger(Enum):
    """Tipos de triggers para kill switch"""
    TOTAL_LOSS = "total_loss"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    MAX_DRAWDOWN = "max_drawdown"
    MANUAL = "manual"
    SYSTEM_ERROR = "system_error"

class KillSwitch:
    """Sistema de kill switch para parada de emergência"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active = False
        self.trigger_reason = None
        self.trigger_time = None
        self.trigger_data = {}
        
        # Configurações
        self.enabled = config.get('risk_management', {}).get('kill_switch', {}).get('enabled', True)
        self.max_loss_pct = config.get('risk_management', {}).get('kill_switch', {}).get('total_loss_percentage', 10.0)
        self.max_consecutive = config.get('risk_management', {}).get('kill_switch', {}).get('consecutive_losses', 5)
        self.max_drawdown_pct = config.get('risk_management', {}).get('kill_switch', {}).get('max_drawdown_percentage', 15.0)
        
        logger.info(f"KillSwitch inicializado - Enabled: {self.enabled}")
    
    def check_conditions(self, statistics: Dict[str, Any]) -> bool:
        """
        Verifica condições de trigger do kill switch
        
        Args:
            statistics: Estatísticas atuais de trading
            
        Returns:
            True se deve ativar kill switch
        """
        if not self.enabled or self.active:
            return False
        
        # Verifica perda total percentual
        total_pnl = statistics.get('total_pnl', 0)
        initial_balance = self.config.get('advanced', {}).get('paper_trading', {}).get('initial_balance_usdt', 100.0)
        
        if total_pnl < 0:
            loss_pct = abs(total_pnl) / initial_balance * 100
            if loss_pct >= self.max_loss_pct:
                self._trigger(
                    KillSwitchTrigger.TOTAL_LOSS,
                    f"Perda total: {loss_pct:.1f}% >= {self.max_loss_pct}%",
                    {'loss_percentage': loss_pct, 'total_pnl': total_pnl}
                )
                return True
        
        # Verifica perdas consecutivas
        consecutive_losses = statistics.get('consecutive_losses', 0)
        if consecutive_losses >= self.max_consecutive:
            self._trigger(
                KillSwitchTrigger.CONSECUTIVE_LOSSES,
                f"Perdas consecutivas: {consecutive_losses} >= {self.max_consecutive}",
                {'consecutive_losses': consecutive_losses}
            )
            return True
        
        # Verifica drawdown máximo
        current_drawdown = statistics.get('current_drawdown', 0)
        drawdown_pct = (current_drawdown / initial_balance) * 100
        if drawdown_pct >= self.max_drawdown_pct:
            self._trigger(
                KillSwitchTrigger.MAX_DRAWDOWN,
                f"Drawdown máximo: {drawdown_pct:.1f}% >= {self.max_drawdown_pct}%",
                {'drawdown_percentage': drawdown_pct, 'drawdown_amount': current_drawdown}
            )
            return True
        
        return False
    
    def trigger_manual(self, reason: str = "Manual trigger"):
        """Ativa kill switch manualmente"""
        self._trigger(KillSwitchTrigger.MANUAL, reason, {'manual': True})
    
    def trigger_system_error(self, error_details: str):
        """Ativa kill switch por erro do sistema"""
        self._trigger(
            KillSwitchTrigger.SYSTEM_ERROR,
            f"Erro do sistema: {error_details}",
            {'error': error_details}
        )
    
    def _trigger(self, trigger_type: KillSwitchTrigger, reason: str, data: Dict):
        """Ativa o kill switch"""
        self.active = True
        self.trigger_reason = reason
        self.trigger_time = datetime.now()
        self.trigger_data = data
        
        logger.critical(f"🚨 KILL SWITCH ATIVADO: {trigger_type.value}")
        logger.critical(f"🛑 MOTIVO: {reason}")
        logger.critical("🛑 TRADING SUSPENSO POR MOTIVOS DE SEGURANÇA!")
    
    def reset(self, authorization_code: str = None):
        """Reseta kill switch (requer autorização)"""
        # Simples verificação - em produção seria mais robusta
        if authorization_code != "RESET_AUTHORIZED":
            logger.warning("Tentativa de reset sem autorização")
            return False
        
        self.active = False
        self.trigger_reason = None
        self.trigger_time = None
        self.trigger_data = {}
        
        logger.warning("Kill switch resetado - Trading pode ser retomado")
        return True
    
    def is_active(self) -> bool:
        """Verifica se kill switch está ativo"""
        return self.active
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do kill switch"""
        return {
            'active': self.active,
            'enabled': self.enabled,
            'trigger_reason': self.trigger_reason,
            'trigger_time': self.trigger_time.isoformat() if self.trigger_time else None,
            'trigger_data': self.trigger_data,
            'thresholds': {
                'max_loss_pct': self.max_loss_pct,
                'max_consecutive_losses': self.max_consecutive,
                'max_drawdown_pct': self.max_drawdown_pct
            }
        }


# core/safety/circuit_breakers.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Circuit Breakers - Sistemas de proteção automática
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker individual"""
    
    def __init__(self, name: str, threshold: int, window_minutes: int):
        self.name = name
        self.threshold = threshold
        self.window = timedelta(minutes=window_minutes)
        self.events = []
        self.tripped = False
        self.trip_time = None
    
    def record_event(self):
        """Registra um evento"""
        now = datetime.now()
        self.events.append(now)
        
        # Remove eventos fora da janela
        cutoff = now - self.window
        self.events = [event for event in self.events if event > cutoff]
        
        # Verifica se deve disparar
        if len(self.events) >= self.threshold and not self.tripped:
            self.trip()
    
    def trip(self):
        """Dispara o circuit breaker"""
        self.tripped = True
        self.trip_time = datetime.now()
        logger.warning(f"Circuit Breaker '{self.name}' disparado: {len(self.events)} eventos em {self.window}")
    
    def reset(self):
        """Reseta o circuit breaker"""
        self.tripped = False
        self.trip_time = None
        self.events.clear()
        logger.info(f"Circuit Breaker '{self.name}' resetado")
    
    def is_tripped(self) -> bool:
        """Verifica se está disparado"""
        return self.tripped

class CircuitBreakerManager:
    """Gerenciador de circuit breakers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.breakers = {}
        
        # Inicializa circuit breakers padrão
        self._initialize_default_breakers()
        
        logger.info(f"CircuitBreakerManager inicializado com {len(self.breakers)} breakers")
    
    def _initialize_default_breakers(self):
        """Inicializa circuit breakers padrão"""
        breaker_configs = self.config.get('safety', {}).get('circuit_breakers', {})
        
        # API Errors
        api_config = breaker_configs.get('api_errors', {'threshold': 5, 'window_minutes': 10})
        self.breakers['api_errors'] = CircuitBreaker(
            'API Errors',
            api_config['threshold'],
            api_config['window_minutes']
        )
        
        # Order Failures
        order_config = breaker_configs.get('order_failures', {'threshold': 3, 'window_minutes': 5})
        self.breakers['order_failures'] = CircuitBreaker(
            'Order Failures',
            order_config['threshold'],
            order_config['window_minutes']
        )
        
        # Quick Losses
        loss_config = breaker_configs.get('quick_losses', {'threshold': 3, 'window_minutes': 15})
        self.breakers['quick_losses'] = CircuitBreaker(
            'Quick Losses',
            loss_config['threshold'],
            loss_config['window_minutes']
        )
    
    def record_api_error(self):
        """Registra erro de API"""
        self.breakers['api_errors'].record_event()
    
    def record_order_failure(self):
        """Registra falha de ordem"""
        self.breakers['order_failures'].record_event()
    
    def record_quick_loss(self):
        """Registra perda rápida"""
        self.breakers['quick_losses'].record_event()
    
    def is_any_tripped(self) -> bool:
        """Verifica se algum circuit breaker está disparado"""
        return any(breaker.is_tripped() for breaker in self.breakers.values())
    
    def get_tripped_breakers(self) -> List[str]:
        """Retorna lista de breakers disparados"""
        return [name for name, breaker in self.breakers.items() if breaker.is_tripped()]
    
    def reset_all(self):
        """Reseta todos os circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status de todos os breakers"""
        return {
            name: {
                'tripped': breaker.is_tripped(),
                'events_count': len(breaker.events),
                'threshold': breaker.threshold,
                'trip_time': breaker.trip_time.isoformat() if breaker.trip_time else None
            }
            for name, breaker in self.breakers.items()
        }


# core/config/config_manager.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config Manager - Gestão centralizada de configuração
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class ConfigManager:
    """Gerenciador centralizado de configuração"""
    
    def __init__(self, config_path: str = "config/futures_config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.last_modified = None
        self.validators = []
        self.change_callbacks = []
        
        self.load_config()
        logger.info(f"ConfigManager inicializado: {config_path}")
    
    def load_config(self) -> bool:
        """Carrega configuração do arquivo"""
        try:
            if not os.path.exists(self.config_path):
                logger.error(f"Arquivo de configuração não encontrado: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            self.last_modified = datetime.fromtimestamp(os.path.getmtime(self.config_path))
            
            # Executa validação
            validation_result = self.validate()
            if not validation_result['valid']:
                logger.error(f"Configuração inválida: {validation_result['errors']}")
                return False
            
            logger.info("Configuração carregada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            return False
    
    def save_config(self, backup: bool = True) -> bool:
        """Salva configuração no arquivo"""
        try:
            # Faz backup se solicitado
            if backup:
                backup_path = f"{self.config_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r') as src, open(backup_path, 'w') as dst:
                        dst.write(src.read())
            
            # Salva nova configuração
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self.last_modified = datetime.now()
            logger.info("Configuração salva com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {e}")
            return False
    
    def get(self, path: str, default=None):
        """Obtém valor de configuração aninhada"""
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, path: str, value: Any) -> bool:
        """Define valor de configuração aninhada"""
        try:
            keys = path.split('.')
            current = self.config
            
            # Navega até o penúltimo nível
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Define valor final
            current[keys[-1]] = value
            
            # Notifica callbacks
            self._notify_change(path, value)
            
            return True
        except Exception as e:
            logger.error(f"Erro ao definir configuração {path}: {e}")
            return False
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """Atualiza múltiplas configurações"""
        try:
            for path, value in updates.items():
                self.set(path, value)
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar configurações: {e}")
            return False
    
    def add_validator(self, validator: Callable[[Dict], Dict]):
        """Adiciona validador de configuração"""
        self.validators.append(validator)
    
    def validate(self) -> Dict[str, Any]:
        """Valida configuração atual"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Validações básicas
        required_sections = ['trading', 'risk_management', 'exchanges', 'strategy']
        for section in required_sections:
            if section not in self.config:
                result['errors'].append(f"Seção obrigatória ausente: {section}")
                result['valid'] = False
        
        # Executa validadores customizados
        for validator in self.validators:
            try:
                validator_result = validator(self.config)
                if not validator_result.get('valid', True):
                    result['valid'] = False
                    result['errors'].extend(validator_result.get('errors', []))
                result['warnings'].extend(validator_result.get('warnings', []))
            except Exception as e:
                result['warnings'].append(f"Erro em validador: {e}")
        
        return result
    
    def add_change_callback(self, callback: Callable[[str, Any], None]):
        """Adiciona callback para mudanças de configuração"""
        self.change_callbacks.append(callback)
    
    def _notify_change(self, path: str, value: Any):
        """Notifica callbacks sobre mudança"""
        for callback in self.change_callbacks:
            try:
                callback(path, value)
            except Exception as e:
                logger.error(f"Erro em callback de configuração: {e}")
    
    def is_modified(self) -> bool:
        """Verifica se arquivo foi modificado externamente"""
        if not os.path.exists(self.config_path):
            return False
        
        file_modified = datetime.fromtimestamp(os.path.getmtime(self.config_path))
        return file_modified > self.last_modified
    
    def reload_if_changed(self) -> bool:
        """Recarrega se arquivo foi modificado externamente"""
        if self.is_modified():
            logger.info("Arquivo de configuração modificado - recarregando")
            return self.load_config()
        return True


# core/config/hot_reload.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hot Reload - Recarga dinâmica de configuração
"""

import threading
import time
import logging
from typing import Dict, Any, Callable, List
from .config_manager import ConfigManager

logger = logging.getLogger(__name__)

class HotReloadManager:
    """Gerenciador de hot reload de configuração"""
    
    def __init__(self, config_manager: ConfigManager, check_interval: int = 5):
        self.config_manager = config_manager
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.reload_callbacks = []
        
    def start(self):
        """Inicia monitoramento de hot reload"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Hot reload iniciado")
    
    def stop(self):
        """Para monitoramento"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Hot reload parado")
    
    def add_reload_callback(self, callback: Callable[[Dict], None]):
        """Adiciona callback para quando configuração for recarregada"""
        self.reload_callbacks.append(callback)
    
    def _monitor_loop(self):
        """Loop de monitoramento"""
        while self.running:
            try:
                if self.config_manager.is_modified():
                    old_config = self.config_manager.config.copy()
                    
                    if self.config_manager.reload_if_changed():
                        logger.info("Configuração recarregada automaticamente")
                        
                        # Notifica callbacks
                        for callback in self.reload_callbacks:
                            try:
                                callback(self.config_manager.config)
                            except Exception as e:
                                logger.error(f"Erro em callback de reload: {e}")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Erro no hot reload: {e}")
                time.sleep(self.check_interval)


# core/bot/bot_factory.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Factory - Criação de diferentes tipos de bots
"""

import logging
from typing import Dict, Any, Optional
from .base_bot import BaseBot
from .trading_bot import TradingBot
from .integrated_bot import IntegratedBot

logger = logging.getLogger(__name__)

class BotFactory:
    """Factory para criação de diferentes tipos de bots"""
    
    _bot_types = {
        'basic': TradingBot,
        'trading': TradingBot,
        'integrated': IntegratedBot,
        'ai': IntegratedBot
    }
    
    @classmethod
    def create_bot(cls, bot_type: str, config: Dict[str, Any], **kwargs) -> BaseBot:
        """
        Cria bot do tipo especificado
        
        Args:
            bot_type: Tipo do bot ('basic', 'trading', 'integrated', 'ai')
            config: Configuração do bot
            **kwargs: Argumentos adicionais
            
        Returns:
            Instância do bot
        """
        if bot_type not in cls._bot_types:
            raise ValueError(f"Tipo de bot '{bot_type}' não suportado. Opções: {list(cls._bot_types.keys())}")
        
        bot_class = cls._bot_types[bot_type]
        
        try:
            # Configurações específicas por tipo
            if bot_type in ['integrated', 'ai']:
                # Bot integrado com IA
                ai_config = config.get('advanced_settings', {}).get('ai_optimization', {})
                if not ai_config.get('enabled', True):
                    logger.warning("Bot integrado criado mas IA desabilitada na configuração")
            
            bot = bot_class(config=config, **kwargs)
            logger.info(f"Bot '{bot_type}' criado com sucesso")
            return bot
            
        except Exception as e:
            logger.error(f"Erro ao criar bot '{bot_type}': {e}")
            raise
    
    @classmethod
    def get_available_types(cls) -> list:
        """Retorna tipos de bots disponíveis"""
        return list(cls._bot_types.keys())
    
    @classmethod
    def register_bot_type(cls, name: str, bot_class: type):
        """Registra novo tipo de bot"""
        cls._bot_types[name] = bot_class
        logger.info(f"Tipo de bot '{name}' registrado")


# core/safety/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safety Module - Sistemas de segurança e proteção
"""

from .kill_switch import KillSwitch, KillSwitchTrigger
from .circuit_breakers import CircuitBreaker, CircuitBreakerManager

__all__ = [
    'KillSwitch',
    'KillSwitchTrigger', 
    'CircuitBreaker',
    'CircuitBreakerManager'
]

# core/config/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Config Module - Gestão de configuração
"""

from .config_manager import ConfigManager
from .hot_reload import HotReloadManager

__all__ = [
    'ConfigManager',
    'HotReloadManager'
]

# core/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core Module - Sistema principal do bot de trading
Estrutura modular reorganizada para melhor manutenção
"""

# Managers
from .managers.base_manager import BaseManager, ConfigurableManager, StatefulManager
from .managers.position_manager import PositionManager

# Position Components
from .position.sizing import (
    BasePositionSizer, PositionSizingResult, PositionSizerFactory,
    TraditionalPositionSizer, VolatilityPositionSizer, KellyPositionSizer
)
from .position.execution import (
    OrderExecutor, OrderExecutionResult, PositionTracker, 
    ExitManager, ExitCondition
)

# Safety Systems
from .safety import KillSwitch, KillSwitchTrigger, CircuitBreakerManager

# Configuration
from .config import ConfigManager, HotReloadManager

# Bot Factory
from .bot.bot_factory import BotFactory

__version__ = "2.0.0"

__all__ = [
    # Core Managers
    'BaseManager',
    'ConfigurableManager', 
    'StatefulManager',
    'PositionManager',
    
    # Position Sizing
    'BasePositionSizer',
    'PositionSizingResult',
    'PositionSizerFactory',
    'TraditionalPositionSizer',
    'VolatilityPositionSizer',
    'KellyPositionSizer',
    
    # Position Execution
    'OrderExecutor',
    'OrderExecutionResult',
    'PositionTracker',
    'ExitManager',
    'ExitCondition',
    
    # Safety
    'KillSwitch',
    'KillSwitchTrigger',
    'CircuitBreakerManager',
    
    # Configuration
    'ConfigManager',
    'HotReloadManager',
    
    # Bot Creation
    'BotFactory'
]