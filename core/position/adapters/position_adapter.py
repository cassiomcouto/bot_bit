#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Manager Adapter - Versão Ultra-Robusta
Resolve definitivamente o erro: "got an unexpected keyword argument 'percentage'"
"""

import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class PositionManagerAdapter:
    """
    Adaptador ultra-robusto que funciona com QUALQUER versão do PositionManager
    
    Características:
    - Detecção automática de assinatura por tentativas inteligentes
    - Cache de estratégias que funcionaram
    - Sistema de fallback com 6+ estratégias diferentes
    - Normalização automática de resultados
    - Zero dependência de inspect ou bibliotecas externas
    - Logs detalhados para diagnóstico
    """
    
    def __init__(self, position_manager):
        """
        Inicializa o adaptador
        
        Args:
            position_manager: Qualquer instância de PositionManager
        """
        self.position_manager = position_manager
        self.strategy_cache = {}  # Cache das estratégias que funcionaram
        self.attempt_log = {}     # Log de tentativas para análise
        
        logger.info("PositionManagerAdapter ultra-robusto inicializado")
        logger.debug(f"PositionManager tipo: {type(position_manager)}")


    # Adicione este método ao PositionManagerAdapter

    def should_close_by_timing(self, symbol: str, current_price: float) -> tuple[bool, str]:
        """
        Proxy para should_close_by_timing com fallback robusto
        
        Args:
            symbol: Símbolo da posição
            current_price: Preço atual
            
        Returns:
            tuple[bool, str]: (should_close, reason)
        """
        try:
            # Se o PositionManager tem o método, usa ele
            if hasattr(self.position_manager, 'should_close_by_timing'):
                return self.position_manager.should_close_by_timing(symbol, current_price)
            
            # Fallback: implementação básica no adapter
            logger.debug(f"PositionManager não tem should_close_by_timing, usando fallback para {symbol}")
            
            # Implementação básica como fallback
            return self._fallback_timing_check(symbol, current_price)
            
        except Exception as e:
            logger.error(f"Erro em should_close_by_timing (adapter) para {symbol}: {e}")
            return False, f"Erro no adapter: {e}"

    def _fallback_timing_check(self, symbol: str, current_price: float) -> tuple[bool, str]:
        """
        Implementação de fallback para verificação de timing
        """
        try:
            # Tenta acessar posições de diferentes formas
            position = None
            
            # Método 1: positions dict
            if hasattr(self.position_manager, 'positions'):
                positions = getattr(self.position_manager, 'positions', {})
                if isinstance(positions, dict) and symbol in positions:
                    position = positions[symbol]
            
            # Método 2: current_position
            if position is None and hasattr(self.position_manager, 'current_position'):
                current_pos = getattr(self.position_manager, 'current_position')
                if current_pos and getattr(current_pos, 'symbol', None) == symbol:
                    position = current_pos
            
            # Método 3: get_position method
            if position is None and hasattr(self.position_manager, 'get_position'):
                try:
                    position = self.position_manager.get_position(symbol)
                except:
                    pass
                    
            if position is None:
                return False, "Nenhuma posição encontrada (fallback)"
                
            # Verificação básica de timing
            from datetime import datetime, timedelta
            current_time = datetime.now()
            
            # Obtém tempo de abertura
            open_time = getattr(position, 'open_time', None)
            if open_time is None:
                open_time = getattr(position, 'timestamp', current_time)
                
            if isinstance(open_time, str):
                try:
                    open_time = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
                except:
                    open_time = current_time
                    
            position_age = current_time - open_time
            
            # Critério simples: fecha após 24 horas
            if position_age > timedelta(hours=24):
                return True, f"Fallback: posição muito antiga ({position_age.total_seconds()/3600:.1f}h)"
                
            return False, "Fallback: critérios de timing não atendidos"
            
        except Exception as e:
            logger.error(f"Erro no fallback timing para {symbol}: {e}")
            return False, f"Erro no fallback: {e}"

    def close_position(self, symbol: str, price: float = None, reason: str = None, 
                      percentage: float = 100.0, **extra_kwargs) -> Dict[str, Any]:
        """
        Fecha posição com detecção automática da assinatura correta
        
        Args:
            symbol: Símbolo da posição a fechar
            price: Preço de fechamento (opcional)
            reason: Motivo do fechamento (opcional) 
            percentage: Percentual a fechar - padrão 100% (opcional)
            **extra_kwargs: Argumentos adicionais
            
        Returns:
            Dict com resultado normalizado: {'success': bool, 'trade': obj, 'pnl': float, ...}
        """
        
        if not hasattr(self.position_manager, 'close_position'):
            return self._error_result("PositionManager não possui método close_position")
        
        # Se já conhecemos a estratégia que funciona, usa ela
        if 'close_position' in self.strategy_cache:
            try:
                result = self._execute_cached_strategy('close_position', symbol, price, reason, percentage, **extra_kwargs)
                if result.get('success') is not False:
                    return result
                else:
                    # Cache invalidado, remove e tenta novamente
                    logger.warning("Estratégia cached falhou, removendo do cache")
                    del self.strategy_cache['close_position']
            except Exception as e:
                logger.debug(f"Estratégia cached falhou: {e}")
                del self.strategy_cache['close_position']
        
        # Lista de estratégias ordenadas por probabilidade de sucesso
        strategies = [
            ('kwargs_basic', self._close_kwargs_basic),
            ('kwargs_with_reason', self._close_kwargs_with_reason),
            ('kwargs_with_percentage', self._close_kwargs_with_percentage),
            ('kwargs_all', self._close_kwargs_all),
            ('positional_2', self._close_positional_2),
            ('positional_3', self._close_positional_3),
            ('positional_1', self._close_positional_1),
            ('mixed_args', self._close_mixed_args),
        ]
        
        # Tenta cada estratégia sequencialmente
        for strategy_name, strategy_func in strategies:
            try:
                logger.debug(f"Tentando estratégia: {strategy_name}")
                
                result = strategy_func(symbol, price, reason, percentage, **extra_kwargs)
                result_normalized = self._normalize_result(result)
                
                # Se teve sucesso (ou pelo menos não falhou explicitamente)
                if result_normalized.get('success') is not False:
                    logger.info(f"✅ Estratégia bem-sucedida: {strategy_name}")
                    
                    # Salva no cache para próximas chamadas
                    self.strategy_cache['close_position'] = strategy_name
                    self._log_attempt('close_position', strategy_name, 'SUCCESS')
                    
                    return result_normalized
                
            except Exception as e:
                logger.debug(f"Estratégia {strategy_name} falhou: {type(e).__name__}: {e}")
                self._log_attempt('close_position', strategy_name, f'ERROR: {e}')
                continue
        
        # Se chegou aqui, todas as estratégias falharam
        error_msg = "Todas as estratégias de fechamento falharam"
        logger.error(error_msg)
        self._log_attempt('close_position', 'ALL', 'FAILED')
        
        return self._error_result(error_msg)
    
    # === ESTRATÉGIAS DE CLOSE_POSITION ===
    
    def _close_kwargs_basic(self, symbol, price, reason, percentage, **extra_kwargs):
        """Estratégia: kwargs básicos (symbol, price)"""
        kwargs = {'symbol': symbol}
        if price is not None:
            kwargs['price'] = price
        return self.position_manager.close_position(**kwargs)
    
    def _close_kwargs_with_reason(self, symbol, price, reason, percentage, **extra_kwargs):
        """Estratégia: kwargs com reason (symbol, price, reason)"""
        kwargs = {'symbol': symbol}
        if price is not None:
            kwargs['price'] = price
        if reason is not None:
            kwargs['reason'] = reason
        return self.position_manager.close_position(**kwargs)
    
    def _close_kwargs_with_percentage(self, symbol, price, reason, percentage, **extra_kwargs):
        """Estratégia: kwargs com percentage"""
        kwargs = {'symbol': symbol, 'percentage': percentage}
        if price is not None:
            kwargs['price'] = price
        if reason is not None:
            kwargs['reason'] = reason
        return self.position_manager.close_position(**kwargs)
    
    def _close_kwargs_all(self, symbol, price, reason, percentage, **extra_kwargs):
        """Estratégia: todos os kwargs possíveis"""
        kwargs = {
            'symbol': symbol,
            'price': price,
            'reason': reason,
            'percentage': percentage,
            **extra_kwargs
        }
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return self.position_manager.close_position(**kwargs)
    
    def _close_positional_1(self, symbol, price, reason, percentage, **extra_kwargs):
        """Estratégia: apenas symbol como argumento posicional"""
        return self.position_manager.close_position(symbol)
    
    def _close_positional_2(self, symbol, price, reason, percentage, **extra_kwargs):
        """Estratégia: symbol e price como argumentos posicionais"""
        return self.position_manager.close_position(symbol, price or 0)
    
    def _close_positional_3(self, symbol, price, reason, percentage, **extra_kwargs):
        """Estratégia: symbol, price, reason como argumentos posicionais"""
        return self.position_manager.close_position(symbol, price or 0, reason or "close")
    
    def _close_mixed_args(self, symbol, price, reason, percentage, **extra_kwargs):
        """Estratégia: argumentos mistos (posicional + kwargs)"""
        return self.position_manager.close_position(symbol, price=price, reason=reason)
    
    # === OPEN POSITION ===
    
    def open_position(self, symbol: str, side: str, size: float, price: float,
                     reason: str = None, confidence: float = None, **extra_kwargs) -> Dict[str, Any]:
        """
        Abre posição com detecção automática da assinatura
        
        Args:
            symbol: Símbolo a negociar
            side: Lado da posição ('long' ou 'short')
            size: Tamanho da posição
            price: Preço de entrada
            reason: Motivo da abertura
            confidence: Confiança do sinal (0-100)
            **extra_kwargs: Argumentos extras
            
        Returns:
            Resultado normalizado
        """
        
        if not hasattr(self.position_manager, 'open_position'):
            return self._error_result("PositionManager não possui método open_position")
        
        # Cache strategy
        if 'open_position' in self.strategy_cache:
            try:
                result = self._execute_cached_open_strategy(symbol, side, size, price, reason, confidence, **extra_kwargs)
                if result.get('success') is not False:
                    return result
                else:
                    del self.strategy_cache['open_position']
            except Exception as e:
                logger.debug(f"Estratégia open cached falhou: {e}")
                del self.strategy_cache['open_position']
        
        # Estratégias de abertura
        open_strategies = [
            ('open_kwargs_basic', self._open_kwargs_basic),
            ('open_kwargs_with_extras', self._open_kwargs_with_extras),
            ('open_kwargs_all', self._open_kwargs_all),
            ('open_positional', self._open_positional),
        ]
        
        for strategy_name, strategy_func in open_strategies:
            try:
                logger.debug(f"Tentando estratégia open: {strategy_name}")
                
                result = strategy_func(symbol, side, size, price, reason, confidence, **extra_kwargs)
                result_normalized = self._normalize_result(result)
                
                if result_normalized.get('success') is not False:
                    logger.info(f"✅ Estratégia open bem-sucedida: {strategy_name}")
                    self.strategy_cache['open_position'] = strategy_name
                    return result_normalized
                    
            except Exception as e:
                logger.debug(f"Estratégia open {strategy_name} falhou: {e}")
                continue
        
        return self._error_result("Todas as estratégias de abertura falharam")
    
    # === ESTRATÉGIAS DE OPEN_POSITION ===
    
    def _open_kwargs_basic(self, symbol, side, size, price, reason, confidence, **extra_kwargs):
        """Open: argumentos básicos obrigatórios"""
        return self.position_manager.open_position(
            symbol=symbol,
            side=side, 
            size=size,
            price=price
        )
    
    def _open_kwargs_with_extras(self, symbol, side, size, price, reason, confidence, **extra_kwargs):
        """Open: básicos + reason"""
        kwargs = {'symbol': symbol, 'side': side, 'size': size, 'price': price}
        if reason is not None:
            kwargs['reason'] = reason
        return self.position_manager.open_position(**kwargs)
    
    def _open_kwargs_all(self, symbol, side, size, price, reason, confidence, **extra_kwargs):
        """Open: todos os argumentos"""
        kwargs = {
            'symbol': symbol,
            'side': side,
            'size': size, 
            'price': price,
            'reason': reason,
            'confidence': confidence,
            **extra_kwargs
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return self.position_manager.open_position(**kwargs)
    
    def _open_positional(self, symbol, side, size, price, reason, confidence, **extra_kwargs):
        """Open: argumentos posicionais"""
        return self.position_manager.open_position(symbol, side, size, price)
    
    # === MÉTODOS DE CACHE ===
    
    def _execute_cached_strategy(self, method, symbol, price, reason, percentage, **extra_kwargs):
        """Executa estratégia conhecida do cache"""
        strategy_name = self.strategy_cache[method]
        
        if strategy_name == 'kwargs_basic':
            return self._close_kwargs_basic(symbol, price, reason, percentage, **extra_kwargs)
        elif strategy_name == 'kwargs_with_reason':
            return self._close_kwargs_with_reason(symbol, price, reason, percentage, **extra_kwargs)
        elif strategy_name == 'kwargs_with_percentage':
            return self._close_kwargs_with_percentage(symbol, price, reason, percentage, **extra_kwargs)
        elif strategy_name == 'kwargs_all':
            return self._close_kwargs_all(symbol, price, reason, percentage, **extra_kwargs)
        elif strategy_name == 'positional_2':
            return self._close_positional_2(symbol, price, reason, percentage, **extra_kwargs)
        elif strategy_name == 'positional_3':
            return self._close_positional_3(symbol, price, reason, percentage, **extra_kwargs)
        elif strategy_name == 'positional_1':
            return self._close_positional_1(symbol, price, reason, percentage, **extra_kwargs)
        elif strategy_name == 'mixed_args':
            return self._close_mixed_args(symbol, price, reason, percentage, **extra_kwargs)
        else:
            raise ValueError(f"Estratégia cached desconhecida: {strategy_name}")
    
    def _execute_cached_open_strategy(self, symbol, side, size, price, reason, confidence, **extra_kwargs):
        """Executa estratégia open conhecida do cache"""
        strategy_name = self.strategy_cache['open_position']
        
        if strategy_name == 'open_kwargs_basic':
            return self._open_kwargs_basic(symbol, side, size, price, reason, confidence, **extra_kwargs)
        elif strategy_name == 'open_kwargs_with_extras':
            return self._open_kwargs_with_extras(symbol, side, size, price, reason, confidence, **extra_kwargs)
        elif strategy_name == 'open_kwargs_all':
            return self._open_kwargs_all(symbol, side, size, price, reason, confidence, **extra_kwargs)
        elif strategy_name == 'open_positional':
            return self._open_positional(symbol, side, size, price, reason, confidence, **extra_kwargs)
        else:
            raise ValueError(f"Estratégia open cached desconhecida: {strategy_name}")
    
    # === MÉTODOS UTILITÁRIOS ===
    
    def _normalize_result(self, result) -> Dict[str, Any]:
        """
        Normaliza resultado para formato padrão independente do que o PositionManager retorna
        
        Returns:
            {'success': bool, 'trade': obj/dict, 'pnl': float, 'error': str}
        """
        
        if result is None:
            return {'success': False, 'error': 'Resultado None'}
        
        # Se já é dict com success, usa como está
        if isinstance(result, dict):
            if 'success' in result:
                return result
            else:
                # Dict sem success - assume sucesso se não tem error
                return {
                    'success': 'error' not in result,
                    'trade': result.get('trade'),
                    'pnl': result.get('pnl', 0),
                    **result
                }
        
        # Se é objeto, tenta extrair informações
        if hasattr(result, '__dict__'):
            return {
                'success': True,
                'trade': result,
                'pnl': getattr(result, 'pnl', 0),
                'result': result
            }
        
        # Qualquer outro tipo - assume sucesso
        return {
            'success': True,
            'result': result,
            'trade': None,
            'pnl': 0
        }
    
    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Cria resultado de erro padronizado"""
        return {
            'success': False,
            'error': error_msg,
            'trade': None,
            'pnl': 0,
            'timestamp': datetime.now()
        }
    
    def _log_attempt(self, method: str, strategy: str, result: str):
        """Registra tentativa para análise posterior"""
        if method not in self.attempt_log:
            self.attempt_log[method] = []
        
        self.attempt_log[method].append({
            'strategy': strategy,
            'result': result,
            'timestamp': datetime.now()
        })
    
    # === MÉTODOS DE DIAGNÓSTICO ===
    
    def diagnose(self):
        """Executa diagnóstico completo do PositionManager"""
        print("="*60)
        print("🔍 DIAGNÓSTICO POSITION MANAGER ADAPTER")
        print("="*60)
        
        # Informações básicas
        print(f"📋 Classe do PositionManager: {type(self.position_manager)}")
        print(f"📋 Adaptador versão: Ultra-Robusta v2.0")
        
        # Métodos disponíveis
        available_methods = [method for method in dir(self.position_manager)
                           if callable(getattr(self.position_manager, method))
                           and not method.startswith('_')]
        
        print(f"📋 Métodos disponíveis ({len(available_methods)}):")
        for method in sorted(available_methods):
            print(f"    ✓ {method}")
        
        # Cache de estratégias
        if self.strategy_cache:
            print(f"\n💾 Estratégias em cache:")
            for method, strategy in self.strategy_cache.items():
                print(f"    {method}: {strategy}")
        else:
            print(f"\n💾 Cache de estratégias: vazio")
        
        # Log de tentativas
        if self.attempt_log:
            print(f"\n📊 Histórico de tentativas:")
            for method, attempts in self.attempt_log.items():
                successful = [a for a in attempts if 'SUCCESS' in a['result']]
                failed = [a for a in attempts if 'ERROR' in a['result']]
                print(f"    {method}: {len(successful)} sucessos, {len(failed)} falhas")
        
        # Teste de conectividade
        print(f"\n🔌 Teste de conectividade:")
        
        critical_methods = ['close_position', 'open_position']
        for method in critical_methods:
            if hasattr(self.position_manager, method):
                print(f"    ✅ {method}: Disponível")
            else:
                print(f"    ❌ {method}: NÃO ENCONTRADO")
        
        print("="*60)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do adaptador"""
        return {
            'strategy_cache': self.strategy_cache.copy(),
            'attempt_log': self.attempt_log.copy(),
            'position_manager_type': str(type(self.position_manager)),
            'available_methods': [method for method in dir(self.position_manager)
                                if callable(getattr(self.position_manager, method))
                                and not method.startswith('_')]
        }
    
    def reset_cache(self):
        """Limpa cache e logs (útil para debug)"""
        self.strategy_cache.clear()
        self.attempt_log.clear()
        logger.info("Cache e logs limpos")
    
    # === PROXY METHODS ===
    
    def __getattr__(self, name):
        """
        Proxy automático para outros métodos do PositionManager
        Permite usar o adaptador como drop-in replacement
        """
        if hasattr(self.position_manager, name):
            attr = getattr(self.position_manager, name)
            if callable(attr):
                # Para métodos, adiciona logging
                def wrapper(*args, **kwargs):
                    logger.debug(f"Proxy call: {name}({args}, {kwargs})")
                    return attr(*args, **kwargs)
                return wrapper
            else:
                return attr
        else:
            raise AttributeError(f"'{type(self).__name__}' e '{type(self.position_manager).__name__}' não possuem atributo '{name}'")


# === FUNÇÃO DE TESTE INTEGRADA ===

def test_adapter():
    """Função de teste integrada para validação rápida"""
    
    print("🧪 TESTE INTEGRADO DO POSITION MANAGER ADAPTER")
    print("="*50)
    
    # Mock simples para teste
    class TestPositionManager:
        def __init__(self, version="standard"):
            self.version = version
            
        def close_position(self, *args, **kwargs):
            print(f"[TEST PM] close_position chamado: args={args}, kwargs={kwargs}")
            
            if self.version == "with_percentage":
                if 'percentage' not in kwargs:
                    raise TypeError("missing percentage")
                    
            return {
                'success': True,
                'trade': {'symbol': 'TEST', 'pnl': 100.0},
                'pnl': 100.0
            }
    
    # Teste com diferentes versões
    for version in ["standard", "with_percentage"]:
        print(f"\n--- Testando versão: {version} ---")
        
        try:
            pm = TestPositionManager(version)
            adapter = PositionManagerAdapter(pm)
            
            result = adapter.close_position("TEST", price=100.0, reason="test")
            
            if result.get('success'):
                print(f"✅ Sucesso: PnL = ${result.get('pnl', 0)}")
            else:
                print(f"❌ Falhou: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    print("\n🎯 Teste concluído")


if __name__ == "__main__":
    test_adapter()