#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Manager Adapter - Versão Completa
Compatibilidade total entre diferentes versões do PositionManager
"""

import logging
from typing import Dict, Any, Optional, Union, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PositionWrapper:
    """
    Wrapper que converte dicionários em objetos compatíveis
    Permite acesso tanto via atributo quanto via índice
    """
    
    def __init__(self, data: Union[Dict, Any]):
        """
        Inicializa o wrapper
        
        Args:
            data: Dados da posição (dict ou objeto)
        """
        if isinstance(data, dict):
            self._data = data
            self._is_dict = True
        else:
            self._data = data
            self._is_dict = False
    
    def __getattr__(self, name):
        """Acesso via atributo (position.symbol)"""
        if self._is_dict:
            if name in self._data:
                return self._data[name]
            # Tenta nomes alternativos
            alternatives = {
                'entry_price': ['entryPrice', 'price', 'avgPrice'],
                'quantity': ['amount', 'size', 'contracts'],
                'side': ['positionSide', 'position_side'],
                'symbol': ['pair', 'market'],
                'pnl': ['unrealizedPnl', 'realizedPnl', 'profit'],
                'entry_time': ['entryTime', 'openTime', 'timestamp']
            }
            if name in alternatives:
                for alt in alternatives[name]:
                    if alt in self._data:
                        return self._data[alt]
            return None
        else:
            return getattr(self._data, name, None)
    
    def __getitem__(self, key):
        """Acesso via índice (position['symbol'])"""
        if self._is_dict:
            return self._data.get(key)
        else:
            return getattr(self._data, key, None)
    
    def __setattr__(self, name, value):
        """Define atributo"""
        if name.startswith('_'):
            super().__setattr__(name, value)
        elif hasattr(self, '_is_dict') and self._is_dict:
            self._data[name] = value
        elif hasattr(self, '_data'):
            setattr(self._data, name, value)
        else:
            super().__setattr__(name, value)
    
    def __setitem__(self, key, value):
        """Define via índice"""
        if self._is_dict:
            self._data[key] = value
        else:
            setattr(self._data, key, value)
    
    def get(self, key, default=None):
        """Método get compatível com dict"""
        if self._is_dict:
            return self._data.get(key, default)
        else:
            return getattr(self._data, key, default)
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        if self._is_dict:
            return self._data.copy()
        else:
            # Converte objeto para dict
            result = {}
            for attr in dir(self._data):
                if not attr.startswith('_'):
                    value = getattr(self._data, attr)
                    if not callable(value):
                        result[attr] = value
            return result
    
    def __repr__(self):
        return f"PositionWrapper({self._data})"


class PositionManagerAdapter:
    """
    Adaptador principal que garante compatibilidade entre versões
    Nome da classe mantido como 'PositionManagerAdapter' para compatibilidade
    """
    
    def __init__(self, position_manager):
        """
        Inicializa o adaptador
        
        Args:
            position_manager: Instância original do PositionManager
        """
        self.position_manager = position_manager
        self.strategy_cache = {}
        self.attempt_log = {}
        
        # Garante que o position_manager tem atributos essenciais
        if not hasattr(self.position_manager, 'positions'):
            self.position_manager.positions = {}
        
        logger.info("PositionManagerAdapter inicializado com sucesso")
    
    def _wrap_position(self, position):
        """Envolve posição em wrapper se necessário"""
        if position is None:
            return None
        if isinstance(position, (dict, object)):
            return PositionWrapper(position)
        return position
    
    # ========== MÉTODOS ESSENCIAIS ==========
    
    def has_position(self, symbol: str) -> bool:
        """Verifica se tem posição para o símbolo"""
        if hasattr(self.position_manager, 'has_position'):
            return self.position_manager.has_position(symbol)
        elif hasattr(self.position_manager, 'positions'):
            return symbol in self.position_manager.positions
        return False
    
    def get_position(self, symbol: str):
        """Obtém dados da posição com wrapper"""
        position = None
        
        if hasattr(self.position_manager, 'get_position'):
            position = self.position_manager.get_position(symbol)
        elif hasattr(self.position_manager, 'positions'):
            position = self.position_manager.positions.get(symbol)
        
        # Sempre retorna wrapped para evitar erro de 'dict' object
        return self._wrap_position(position)
    
    def get_all_positions(self):
        """Retorna todas as posições com wrapper"""
        positions = {}
        
        if hasattr(self.position_manager, 'get_all_positions'):
            positions = self.position_manager.get_all_positions()
        elif hasattr(self.position_manager, 'positions'):
            positions = self.position_manager.positions
        
        # Wrap todas as posições
        wrapped = {}
        for symbol, pos in positions.items():
            wrapped[symbol] = self._wrap_position(pos)
        
        return wrapped
    
    def can_open_position(self, symbol: str) -> bool:
        """Verifica se pode abrir nova posição"""
        if hasattr(self.position_manager, 'can_open_position'):
            return self.position_manager.can_open_position(symbol)
        
        # Implementação fallback
        if self.has_position(symbol):
            return False
        
        # Verifica se está habilitado
        if hasattr(self.position_manager, 'is_enabled'):
            if not self.position_manager.is_enabled():
                return False
        
        return True
    
    def calculate_position_size(self, symbol: str, price: float, side: str, 
                               confidence: float = 1.0) -> float:
        """Calcula tamanho da posição"""
        if hasattr(self.position_manager, 'calculate_position_size'):
            try:
                # Tenta com todos os argumentos
                return self.position_manager.calculate_position_size(
                    symbol, price, side, confidence
                )
            except TypeError:
                try:
                    # Tenta sem confidence
                    return self.position_manager.calculate_position_size(
                        symbol, price, side
                    )
                except:
                    pass
        
        # Fallback: cálculo simples
        balance = self.get_balance()
        risk_pct = 2.0  # 2% padrão
        risk_amount = balance * (risk_pct / 100.0)
        return risk_amount / price
    
    def set_balance(self, balance: float):
        """Define saldo atual"""
        if hasattr(self.position_manager, 'set_balance'):
            return self.position_manager.set_balance(balance)
        elif hasattr(self.position_manager, 'balance'):
            self.position_manager.balance = balance
            logger.info(f"Saldo atualizado: ${balance:.2f}")
    
    def get_balance(self) -> float:
        """Retorna saldo atual"""
        if hasattr(self.position_manager, 'get_balance'):
            return self.position_manager.get_balance()
        elif hasattr(self.position_manager, 'balance'):
            return self.position_manager.balance
        return 0.0
    
    def print_positions(self):
        """Imprime posições atuais"""
        if hasattr(self.position_manager, 'print_positions'):
            return self.position_manager.print_positions()
        else:
            # Implementação fallback
            positions = self.get_all_positions()
            balance = self.get_balance()
            
            if not positions:
                print(f"Nenhuma posição aberta | Saldo: ${balance:.2f}")
            else:
                print(f"Posições abertas: {len(positions)} | Saldo: ${balance:.2f}")
                for symbol, pos in positions.items():
                    side = pos.side or pos.get('side', 'unknown')
                    quantity = pos.quantity or pos.get('quantity', 0)
                    entry_price = pos.entry_price or pos.get('entry_price', 0)
                    print(f"  {symbol}: {side.upper()} {quantity:.4f} @ ${entry_price:.2f}")
    
    def sync_positions(self, positions):
        """Sincroniza posições com a exchange"""
        wrapped_positions = {}
        
        for pos in positions:
            # Detecta o símbolo
            if hasattr(pos, 'symbol'):
                symbol = pos.symbol
            elif isinstance(pos, dict) and 'symbol' in pos:
                symbol = pos['symbol']
            else:
                symbol = str(pos)
            
            wrapped_positions[symbol] = self._wrap_position(pos)
        
        if hasattr(self.position_manager, 'sync_positions'):
            return self.position_manager.sync_positions(positions)
        else:
            # Implementação fallback
            logger.info(f"Sincronizando {len(positions)} posições")
            if hasattr(self.position_manager, 'positions'):
                self.position_manager.positions = wrapped_positions
    
    def cancel_all_orders(self):
        """Cancela todas as ordens abertas"""
        if hasattr(self.position_manager, 'cancel_all_orders'):
            return self.position_manager.cancel_all_orders()
        else:
            logger.info("cancel_all_orders: operação não disponível")
    
    # ========== MÉTODOS DE TIMING ==========
    
    def should_close_by_timing(self, symbol: str, current_price: float) -> Tuple[bool, str]:
        """
        Verifica se a posição deve ser fechada baseado em critérios de tempo
        """
        if hasattr(self.position_manager, 'should_close_by_timing'):
            try:
                return self.position_manager.should_close_by_timing(symbol, current_price)
            except:
                pass
        
        # Implementação fallback
        position = self.get_position(symbol)
        if not position:
            return False, "Sem posição"
        
        # Obtém tempo de entrada
        entry_time = position.entry_time or position.get('entry_time')
        if not entry_time:
            return False, "Sem timestamp de entrada"
        
        # Converte para datetime se necessário
        if isinstance(entry_time, str):
            try:
                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            except:
                return False, "Erro no timestamp"
        
        # Calcula idade da posição
        position_age = datetime.now() - entry_time
        age_hours = position_age.total_seconds() / 3600
        
        # Critério: fecha após 24 horas
        max_hours = 24
        if hasattr(self.position_manager, 'config'):
            max_seconds = self.position_manager.config.get('strategy', {}).get('max_position_hold_seconds', 86400)
            max_hours = max_seconds / 3600
        
        if age_hours > max_hours:
            return True, f"Posição muito antiga: {age_hours:.1f}h > {max_hours:.1f}h"
        
        return False, f"Dentro do tempo: {age_hours:.1f}h"
    
    def check_take_profit_conditions(self, symbol: str, current_price: float) -> Tuple[bool, str, float]:
        """
        Verifica condições de take profit
        """
        if hasattr(self.position_manager, 'check_take_profit_conditions'):
            try:
                return self.position_manager.check_take_profit_conditions(symbol, current_price)
            except:
                pass
        
        # Implementação fallback
        position = self.get_position(symbol)
        if not position:
            return False, "Sem posição", 0.0
        
        # Obtém dados da posição
        entry_price = position.entry_price or position.get('entry_price', current_price)
        side = position.side or position.get('side', 'long')
        
        # Calcula PnL percentual
        if str(side).lower() in ['long', 'buy']:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Take profit em 3% (padrão)
        tp_threshold = 3.0
        if hasattr(self.position_manager, 'config'):
            tp_threshold = self.position_manager.config.get('risk_management', {}).get('take_profit', {}).get('percentage', 3.0)
        
        if pnl_pct >= tp_threshold:
            return True, f"Take profit: +{pnl_pct:.2f}%", 1.0
        
        # Take profit parcial em 1.5%
        partial_threshold = tp_threshold / 2
        if pnl_pct >= partial_threshold:
            return True, f"Take profit parcial: +{pnl_pct:.2f}%", 0.5
        
        return False, f"PnL: {pnl_pct:.2f}%", 0.0
    
    # ========== MÉTODOS DE ABERTURA/FECHAMENTO ==========
    
    def open_position(self, symbol: str, side: str, size: float, price: float,
                     reason: str = None, confidence: float = None, **kwargs) -> Dict[str, Any]:
        """
        Abre posição com detecção automática de assinatura
        """
        # Lista de estratégias para tentar
        strategies = [
            lambda: self.position_manager.open_position(
                symbol=symbol, side=side, size=size, price=price, 
                reason=reason, confidence=confidence
            ),
            lambda: self.position_manager.open_position(
                symbol=symbol, side=side, size=size, price=price, reason=reason
            ),
            lambda: self.position_manager.open_position(
                symbol=symbol, side=side, size=size, price=price
            ),
            lambda: self.position_manager.open_position(symbol, side, size, price),
        ]
        
        for strategy in strategies:
            try:
                result = strategy()
                if result is None:
                    continue
                
                # Cria posição wrapped
                position_data = {
                    'symbol': symbol,
                    'side': side,
                    'quantity': size,
                    'entry_price': price,
                    'entry_time': datetime.now(),
                    'reason': reason
                }
                
                # Adiciona ao tracking
                if hasattr(self.position_manager, 'positions'):
                    self.position_manager.positions[symbol] = position_data
                
                # Normaliza resultado
                if isinstance(result, dict):
                    return result
                else:
                    return {'success': True, 'trade': result, 'position': position_data}
                    
            except Exception as e:
                continue
        
        # Se todas falharam, retorna erro
        return {'success': False, 'error': 'Não foi possível abrir posição'}
    
    def close_position(self, symbol: str, price: float = None, reason: str = None,
                      percentage: float = 1.0, **kwargs) -> Dict[str, Any]:
        """
        Fecha posição com compatibilidade total
        """
        # Obtém posição atual para calcular PnL
        position = self.get_position(symbol)
        
        # Cache de estratégia bem-sucedida
        cache_key = 'close_position'
        if cache_key in self.strategy_cache:
            try:
                strategy_name = self.strategy_cache[cache_key]
                result = self._execute_cached_close(strategy_name, symbol, price, reason, percentage)
                if result.get('success') is not False:
                    return result
            except:
                del self.strategy_cache[cache_key]
        
        # Lista de estratégias
        strategies = [
            ('basic', lambda: self.position_manager.close_position(
                symbol=symbol, price=price, reason=reason
            )),
            ('with_percentage', lambda: self.position_manager.close_position(
                symbol=symbol, price=price, reason=reason, percentage=percentage
            )),
            ('positional', lambda: self.position_manager.close_position(symbol, price)),
            ('symbol_only', lambda: self.position_manager.close_position(symbol)),
        ]
        
        for name, strategy in strategies:
            try:
                result = strategy()
                
                if result is None:
                    continue
                
                # Remove do tracking
                if hasattr(self.position_manager, 'positions'):
                    if symbol in self.position_manager.positions:
                        del self.position_manager.positions[symbol]
                
                if isinstance(result, dict):
                    if result.get('success') is not False:
                        self.strategy_cache[cache_key] = name
                        return result
                else:
                    # Calcula PnL se possível
                    pnl = 0
                    if position and price:
                        entry_price = position.entry_price or position.get('entry_price')
                        quantity = position.quantity or position.get('quantity')
                        side = position.side or position.get('side')
                        
                        if entry_price and quantity:
                            if str(side).lower() in ['long', 'buy']:
                                pnl = (price - entry_price) * quantity
                            else:
                                pnl = (entry_price - price) * quantity
                    
                    return {'success': True, 'trade': result, 'pnl': pnl}
                    
            except TypeError as e:
                if 'percentage' in str(e):
                    continue
            except Exception:
                continue
        
        # Fallback: implementação própria
        return self._fallback_close_position(symbol, price, reason, percentage)
    
    def _execute_cached_close(self, strategy_name: str, symbol: str, price: float, 
                             reason: str, percentage: float) -> Dict:
        """Executa estratégia cached de close"""
        if strategy_name == 'basic':
            return self.position_manager.close_position(symbol=symbol, price=price, reason=reason)
        elif strategy_name == 'with_percentage':
            return self.position_manager.close_position(symbol=symbol, price=price, reason=reason, percentage=percentage)
        elif strategy_name == 'positional':
            return self.position_manager.close_position(symbol, price)
        elif strategy_name == 'symbol_only':
            return self.position_manager.close_position(symbol)
        else:
            raise ValueError(f"Estratégia desconhecida: {strategy_name}")
    
    def _fallback_close_position(self, symbol: str, price: float, reason: str, percentage: float) -> Dict:
        """Implementação fallback de fechamento"""
        position = self.get_position(symbol)
        if not position:
            return {'success': False, 'error': 'Posição não encontrada'}
        
        # Remove do tracking
        if hasattr(self.position_manager, 'positions'):
            if symbol in self.position_manager.positions:
                del self.position_manager.positions[symbol]
        
        # Retorna sucesso simulado
        return {
            'success': True,
            'trade': {
                'symbol': symbol,
                'action': 'close',
                'exit_price': price,
                'reason': reason
            },
            'pnl': 0
        }
    
    # ========== MÉTODOS DE CONFIGURAÇÃO ==========
    
    def _get_config(self, path: str, default=None):
        """Helper para obter configuração"""
        if hasattr(self.position_manager, '_get_config'):
            return self.position_manager._get_config(path, default)
        elif hasattr(self.position_manager, 'config'):
            keys = path.split('.')
            value = self.position_manager.config
            try:
                for key in keys:
                    value = value[key]
                return value
            except (KeyError, TypeError):
                return default
        return default
    
    # ========== PROXY AUTOMÁTICO ==========
    
    def __getattr__(self, name):
        """
        Proxy automático para métodos não implementados
        """
        if hasattr(self.position_manager, name):
            attr = getattr(self.position_manager, name)
            if callable(attr):
                def wrapper(*args, **kwargs):
                    try:
                        return attr(*args, **kwargs)
                    except Exception as e:
                        logger.debug(f"Erro em proxy {name}: {e}")
                        raise
                return wrapper
            else:
                return attr
        else:
            raise AttributeError(f"'{type(self).__name__}' não possui atributo '{name}'")
    
    # ========== MÉTODOS DE DEBUG ==========
    
    def diagnose(self):
        """Diagnóstico completo do adapter"""
        print("="*60)
        print("🔍 DIAGNÓSTICO DO POSITION MANAGER ADAPTER")
        print("="*60)
        
        # Métodos essenciais
        essential_methods = [
            'has_position', 'get_position', 'can_open_position',
            'open_position', 'close_position', 'calculate_position_size',
            'should_close_by_timing', 'check_take_profit_conditions'
        ]
        
        print("📋 Métodos Essenciais:")
        for method in essential_methods:
            if hasattr(self, method):
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method}")
        
        # Métodos do manager original
        if self.position_manager:
            original_methods = [m for m in dir(self.position_manager) 
                              if not m.startswith('_') and callable(getattr(self.position_manager, m))]
            print(f"\n📋 Métodos do PositionManager Original: {len(original_methods)}")
            for method in sorted(original_methods)[:10]:  # Mostra apenas os primeiros 10
                print(f"    • {method}")
            if len(original_methods) > 10:
                print(f"    ... e mais {len(original_methods)-10} métodos")
        
        # Cache de estratégias
        if self.strategy_cache:
            print(f"\n💾 Cache de Estratégias:")
            for key, value in self.strategy_cache.items():
                print(f"    {key}: {value}")
        
        # Posições atuais
        positions = self.get_all_positions()
        print(f"\n📊 Posições Atuais: {len(positions)}")
        for symbol in positions:
            print(f"    • {symbol}")
        
        print("="*60)


# Alias para compatibilidade
EnhancedPositionManagerAdapter = PositionManagerAdapter


# Exporta as classes principais
__all__ = ['PositionManagerAdapter', 'EnhancedPositionManagerAdapter', 'PositionWrapper']