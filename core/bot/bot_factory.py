#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Factory - Sistema de criação e configuração de bots
Gerencia diferentes tipos de bots de trading
"""

import logging
from typing import Dict, Any, Optional, Type, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from ..managers.base_manager import ConfigurableManager
from .base_bot import BaseBot, BotConfig, BotType, BotStatus

logger = logging.getLogger(__name__)

class BotCreationError(Exception):
    """Erro na criação de bot"""
    pass

@dataclass
class BotTemplate:
    """Template para criação de bot"""
    bot_type: BotType
    name: str
    description: str
    default_config: Dict[str, Any]
    required_components: List[str]
    optional_components: List[str]

class BotRegistry:
    """Registry de tipos de bot disponíveis"""
    
    def __init__(self):
        self._bot_classes: Dict[BotType, Type[BaseBot]] = {}
        self._templates: Dict[str, BotTemplate] = {}
        self._register_default_templates()
    
    def register_bot_class(self, bot_type: BotType, bot_class: Type[BaseBot]):
        """Registra uma classe de bot"""
        self._bot_classes[bot_type] = bot_class
        logger.info(f"Bot class registrada: {bot_type.value} -> {bot_class.__name__}")
    
    def register_template(self, template: BotTemplate):
        """Registra um template de bot"""
        self._templates[template.name] = template
        logger.info(f"Template registrado: {template.name}")
    
    def get_bot_class(self, bot_type: BotType) -> Type[BaseBot]:
        """Obtém classe de bot por tipo"""
        if bot_type not in self._bot_classes:
            raise BotCreationError(f"Tipo de bot não registrado: {bot_type}")
        return self._bot_classes[bot_type]
    
    def get_template(self, template_name: str) -> BotTemplate:
        """Obtém template por nome"""
        if template_name not in self._templates:
            raise BotCreationError(f"Template não encontrado: {template_name}")
        return self._templates[template_name]
    
    def list_available_types(self) -> List[BotType]:
        """Lista tipos de bot disponíveis"""
        return list(self._bot_classes.keys())
    
    def list_templates(self) -> List[str]:
        """Lista templates disponíveis"""
        return list(self._templates.keys())
    
    def _register_default_templates(self):
        """Registra templates padrão"""
        # Template para bot de futuros simples
        futures_template = BotTemplate(
            bot_type=BotType.FUTURES,
            name="simple_futures",
            description="Bot simples para trading de futuros",
            default_config={
                'trading': {
                    'primary_pair': 'BTCUSDT',
                    'max_positions': 1,
                    'base_amount_usdt': 100.0
                },
                'risk_management': {
                    'stop_loss_percent': 2.0,
                    'take_profit_percent': 3.0,
                    'max_drawdown_percent': 10.0
                },
                'strategy': {
                    'analysis_interval_seconds': 60,
                    'primary_exchange': 'bingx'
                }
            },
            required_components=['market_analyzer', 'position_manager', 'risk_manager'],
            optional_components=['csv_logger', 'ai_optimizer']
        )
        
        # Template para bot conservador
        conservative_template = BotTemplate(
            bot_type=BotType.FUTURES,
            name="conservative_futures",
            description="Bot conservador com baixo risco",
            default_config={
                'trading': {
                    'primary_pair': 'BTCUSDT',
                    'max_positions': 1,
                    'base_amount_usdt': 50.0
                },
                'risk_management': {
                    'stop_loss_percent': 1.5,
                    'take_profit_percent': 2.0,
                    'max_drawdown_percent': 5.0,
                    'max_daily_loss_usdt': 20.0
                },
                'strategy': {
                    'analysis_interval_seconds': 120,
                    'primary_exchange': 'bingx',
                    'min_confidence_threshold': 0.8
                }
            },
            required_components=['market_analyzer', 'position_manager', 'risk_manager'],
            optional_components=['csv_logger', 'ai_optimizer']
        )
        
        # Template para bot agressivo
        aggressive_template = BotTemplate(
            bot_type=BotType.FUTURES,
            name="aggressive_futures",
            description="Bot agressivo para traders experientes",
            default_config={
                'trading': {
                    'primary_pair': 'BTCUSDT',
                    'max_positions': 3,
                    'base_amount_usdt': 200.0
                },
                'risk_management': {
                    'stop_loss_percent': 3.0,
                    'take_profit_percent': 5.0,
                    'max_drawdown_percent': 20.0,
                    'max_daily_loss_usdt': 100.0
                },
                'strategy': {
                    'analysis_interval_seconds': 30,
                    'primary_exchange': 'bingx',
                    'min_confidence_threshold': 0.6
                }
            },
            required_components=['market_analyzer', 'position_manager', 'risk_manager'],
            optional_components=['csv_logger', 'ai_optimizer']
        )
        
        self.register_template(futures_template)
        self.register_template(conservative_template)
        self.register_template(aggressive_template)

class BotFactory(ConfigurableManager):
    """Factory principal para criação de bots"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.registry = BotRegistry()
        self._active_bots: Dict[str, BaseBot] = {}
        self._register_default_bots()
    
    def _register_default_bots(self):
        """Registra bots padrão do sistema"""
        try:
            # Importa e registra bot de futuros
            from .futures_bot import FuturesBot
            self.registry.register_bot_class(BotType.FUTURES, FuturesBot)
            
            # Importa outros tipos quando disponíveis
            try:
                from .spot_bot import SpotBot
                self.registry.register_bot_class(BotType.SPOT, SpotBot)
            except ImportError:
                logger.debug("SpotBot não disponível")
            
            try:
                from .grid_bot import GridBot
                self.registry.register_bot_class(BotType.GRID, GridBot)
            except ImportError:
                logger.debug("GridBot não disponível")
                
        except ImportError as e:
            logger.warning(f"Alguns bots não puderam ser registrados: {e}")
    
    def create_bot(self, 
                   bot_type: BotType = None,
                   template_name: str = None,
                   config: Dict[str, Any] = None,
                   bot_id: str = None) -> BaseBot:
        """
        Cria um novo bot
        
        Args:
            bot_type: Tipo do bot a criar
            template_name: Nome do template a usar
            config: Configuração específica
            bot_id: ID único do bot
            
        Returns:
            BaseBot: Instância do bot criado
        """
        try:
            # Determina configuração final
            final_config = {}
            
            if template_name:
                template = self.registry.get_template(template_name)
                final_config.update(template.default_config)
                if not bot_type:
                    bot_type = template.bot_type
            
            if config:
                final_config = self._merge_configs(final_config, config)
            
            if not bot_type:
                bot_type = BotType.FUTURES  # Default
            
            # Cria configuração do bot
            bot_config = BotConfig(
                bot_type=bot_type,
                bot_id=bot_id or self._generate_bot_id(),
                config=final_config,
                template_name=template_name
            )
            
            # Obtém classe do bot e cria instância
            bot_class = self.registry.get_bot_class(bot_type)
            bot_instance = bot_class(bot_config)
            
            # Registra bot ativo
            self._active_bots[bot_config.bot_id] = bot_instance
            
            logger.info(f"Bot criado: {bot_config.bot_id} ({bot_type.value})")
            return bot_instance
            
        except Exception as e:
            logger.error(f"Erro ao criar bot: {e}")
            raise BotCreationError(f"Falha na criação do bot: {e}")
    
    def create_from_template(self, template_name: str, 
                           overrides: Dict[str, Any] = None,
                           bot_id: str = None) -> BaseBot:
        """
        Cria bot a partir de template
        
        Args:
            template_name: Nome do template
            overrides: Sobrescrevem configurações do template
            bot_id: ID único do bot
            
        Returns:
            BaseBot: Bot criado
        """
        return self.create_bot(
            template_name=template_name,
            config=overrides,
            bot_id=bot_id
        )
    
    def create_futures_bot(self, config: Dict[str, Any] = None, 
                          bot_id: str = None) -> BaseBot:
        """Cria bot de futuros (conveniência)"""
        return self.create_bot(
            bot_type=BotType.FUTURES,
            config=config,
            bot_id=bot_id
        )
    
    def create_conservative_bot(self, pair: str = 'BTCUSDT', 
                               balance: float = 100.0,
                               bot_id: str = None) -> BaseBot:
        """Cria bot conservador pré-configurado"""
        config = {
            'trading': {
                'primary_pair': pair,
                'base_amount_usdt': balance
            }
        }
        
        return self.create_from_template(
            template_name="conservative_futures",
            overrides=config,
            bot_id=bot_id
        )
    
    def create_aggressive_bot(self, pair: str = 'BTCUSDT',
                             balance: float = 500.0,
                             bot_id: str = None) -> BaseBot:
        """Cria bot agressivo pré-configurado"""
        config = {
            'trading': {
                'primary_pair': pair,
                'base_amount_usdt': balance
            }
        }
        
        return self.create_from_template(
            template_name="aggressive_futures",
            overrides=config,
            bot_id=bot_id
        )
    
    def get_bot(self, bot_id: str) -> Optional[BaseBot]:
        """Obtém bot ativo por ID"""
        return self._active_bots.get(bot_id)
    
    def list_active_bots(self) -> List[BaseBot]:
        """Lista bots ativos"""
        return list(self._active_bots.values())
    
    def stop_bot(self, bot_id: str) -> bool:
        """Para um bot específico"""
        if bot_id not in self._active_bots:
            logger.warning(f"Bot não encontrado: {bot_id}")
            return False
        
        try:
            bot = self._active_bots[bot_id]
            bot.stop()
            del self._active_bots[bot_id]
            logger.info(f"Bot parado: {bot_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao parar bot {bot_id}: {e}")
            return False
    
    def stop_all_bots(self):
        """Para todos os bots ativos"""
        bot_ids = list(self._active_bots.keys())
        for bot_id in bot_ids:
            self.stop_bot(bot_id)
        
        logger.info(f"Todos os bots parados ({len(bot_ids)} bots)")
    
    def get_bot_status(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de um bot"""
        bot = self.get_bot(bot_id)
        if not bot:
            return None
        
        return {
            'bot_id': bot.config.bot_id,
            'bot_type': bot.config.bot_type.value,
            'status': bot.status.value,
            'uptime': bot.get_uptime(),
            'performance': bot.get_performance_summary()
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtém status do sistema completo"""
        active_bots = len(self._active_bots)
        running_bots = sum(1 for bot in self._active_bots.values() 
                          if bot.status == BotStatus.RUNNING)
        
        return {
            'total_bots': active_bots,
            'running_bots': running_bots,
            'available_types': [bt.value for bt in self.registry.list_available_types()],
            'available_templates': self.registry.list_templates(),
            'bots': {
                bot_id: self.get_bot_status(bot_id) 
                for bot_id in self._active_bots.keys()
            }
        }
    
    def _generate_bot_id(self) -> str:
        """Gera ID único para bot"""
        import uuid
        return f"bot_{uuid.uuid4().hex[:8]}"
    
    def _merge_configs(self, base: Dict[str, Any], 
                      override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge recursivo de configurações"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result

# Instância global da factory
_global_factory = None

def get_bot_factory() -> BotFactory:
    """Obtém instância global da factory"""
    global _global_factory
    if _global_factory is None:
        _global_factory = BotFactory()
    return _global_factory

def create_bot(**kwargs) -> BaseBot:
    """Função de conveniência para criar bot"""
    return get_bot_factory().create_bot(**kwargs)

def create_futures_bot(**kwargs) -> BaseBot:
    """Função de conveniência para criar bot de futuros"""
    return get_bot_factory().create_futures_bot(**kwargs)
