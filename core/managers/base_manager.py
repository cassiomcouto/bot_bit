#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Manager - Classe base para todos os gerenciadores
Fornece funcionalidades comuns e padrões de arquitetura
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseManager(ABC):
    """Classe base para todos os gerenciadores do sistema"""
    
    def __init__(self, config: Dict[str, Any], name: str = None):
        """
        Inicializa o gerenciador base
        
        Args:
            config: Configuração do sistema
            name: Nome do gerenciador (usado para logs)
        """
        self.config = config
        self.name = name or self.__class__.__name__
        self.initialized = False
        self.start_time = datetime.now()
        
        # Estado do gerenciador
        self._enabled = True
        self._statistics = {}
        self._last_update = None
        
        # Inicialização específica do gerenciador
        self._initialize()
        self.initialized = True
        
        logger.info(f"{self.name} inicializado")
    
    @abstractmethod
    def _initialize(self):
        """Inicialização específica do gerenciador - deve ser implementada"""
        pass
    
    def _get_config(self, path: str, default=None):
        """
        Obtém valor de configuração aninhada
        
        Args:
            path: Caminho para a configuração (ex: 'trading.risk_per_trade')
            default: Valor padrão se não encontrar
            
        Returns:
            Valor da configuração ou default
        """
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def is_enabled(self) -> bool:
        """Verifica se o gerenciador está habilitado"""
        return self._enabled and self.initialized
    
    def enable(self):
        """Habilita o gerenciador"""
        self._enabled = True
        logger.info(f"{self.name} habilitado")
    
    def disable(self):
        """Desabilita o gerenciador"""
        self._enabled = False
        logger.warning(f"{self.name} desabilitado")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do gerenciador"""
        base_stats = {
            'name': self.name,
            'enabled': self._enabled,
            'initialized': self.initialized,
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'last_update': self._last_update.isoformat() if self._last_update else None
        }
        
        # Adiciona estatísticas específicas
        base_stats.update(self._statistics)
        return base_stats
    
    def update_statistics(self, stats: Dict[str, Any]):
        """Atualiza estatísticas do gerenciador"""
        self._statistics.update(stats)
        self._last_update = datetime.now()
    
    def reset_statistics(self):
        """Reseta estatísticas do gerenciador"""
        self._statistics.clear()
        self._last_update = None
        logger.info(f"Estatísticas do {self.name} resetadas")
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Valida configuração do gerenciador
        
        Returns:
            Dict com resultado da validação
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'required_keys': self._get_required_config_keys(),
            'optional_keys': self._get_optional_config_keys()
        }
        
        # Verifica chaves obrigatórias
        for key in validation_result['required_keys']:
            if self._get_config(key) is None:
                validation_result['errors'].append(f"Configuração obrigatória ausente: {key}")
                validation_result['valid'] = False
        
        # Validações específicas do gerenciador
        self._validate_specific_config(validation_result)
        
        return validation_result
    
    def _get_required_config_keys(self) -> list:
        """Retorna chaves de configuração obrigatórias - pode ser sobrescrita"""
        return []
    
    def _get_optional_config_keys(self) -> list:
        """Retorna chaves de configuração opcionais - pode ser sobrescrita"""
        return []
    
    def _validate_specific_config(self, validation_result: Dict[str, Any]):
        """Validação específica do gerenciador - pode ser sobrescrita"""
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """
        Executa verificação de saúde do gerenciador
        
        Returns:
            Dict com status de saúde
        """
        health_status = {
            'healthy': True,
            'issues': [],
            'last_check': datetime.now().isoformat(),
            'manager': self.name
        }
        
        # Verificações básicas
        if not self.initialized:
            health_status['healthy'] = False
            health_status['issues'].append("Gerenciador não inicializado")
        
        if not self._enabled:
            health_status['issues'].append("Gerenciador desabilitado")
        
        # Verificações específicas do gerenciador
        self._perform_specific_health_checks(health_status)
        
        return health_status
    
    def _perform_specific_health_checks(self, health_status: Dict[str, Any]):
        """Verificações específicas de saúde - pode ser sobrescrita"""
        pass
    
    def reload_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Recarrega configuração do gerenciador
        
        Args:
            new_config: Nova configuração
            
        Returns:
            True se recarregou com sucesso
        """
        try:
            old_config = self.config.copy()
            self.config = new_config
            
            # Reinicializa se necessário
            if self._should_reinitialize(old_config, new_config):
                logger.info(f"Reinicializando {self.name} devido a mudanças na configuração")
                self.initialized = False
                self._initialize()
                self.initialized = True
            
            logger.info(f"Configuração do {self.name} recarregada")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao recarregar configuração do {self.name}: {e}")
            self.config = old_config  # Restaura configuração anterior
            return False
    
    def _should_reinitialize(self, old_config: Dict, new_config: Dict) -> bool:
        """
        Determina se deve reinicializar após mudança de configuração
        Pode ser sobrescrita para lógica específica
        """
        return False
    
    def shutdown(self):
        """Finaliza o gerenciador de forma limpa"""
        try:
            self._perform_cleanup()
            self._enabled = False
            logger.info(f"{self.name} finalizado")
        except Exception as e:
            logger.error(f"Erro ao finalizar {self.name}: {e}")
    
    def _perform_cleanup(self):
        """Limpeza específica do gerenciador - pode ser sobrescrita"""
        pass
    
    def __repr__(self) -> str:
        """Representação string do gerenciador"""
        return f"{self.name}(enabled={self._enabled}, initialized={self.initialized})"


class ConfigurableManager(BaseManager):
    """Manager base com suporte avançado a configuração"""
    
    def __init__(self, config: Dict[str, Any], config_section: str, name: str = None):
        """
        Args:
            config: Configuração completa do sistema
            config_section: Seção específica da configuração para este manager
            name: Nome do manager
        """
        self.config_section = config_section
        super().__init__(config, name)
    
    def _get_section_config(self, key: str = None, default=None):
        """Obtém configuração da seção específica do manager"""
        if key:
            return self._get_config(f"{self.config_section}.{key}", default)
        else:
            return self._get_config(self.config_section, {})


class StatefulManager(BaseManager):
    """Manager base com suporte a estado persistente"""
    
    def __init__(self, config: Dict[str, Any], name: str = None):
        self._state = {}
        super().__init__(config, name)
    
    def get_state(self) -> Dict[str, Any]:
        """Retorna estado atual do manager"""
        return self._state.copy()
    
    def update_state(self, updates: Dict[str, Any]):
        """Atualiza estado do manager"""
        self._state.update(updates)
        self._last_update = datetime.now()
    
    def reset_state(self):
        """Reseta estado do manager"""
        self._state.clear()
        logger.info(f"Estado do {self.name} resetado")
    
    def save_state_snapshot(self) -> Dict[str, Any]:
        """Cria snapshot do estado atual"""
        return {
            'timestamp': datetime.now().isoformat(),
            'manager': self.name,
            'state': self._state.copy(),
            'statistics': self._statistics.copy()
        }