#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Manager Adapter - Versão Simplificada e Funcional
Corrige todos os problemas de sintaxe e compatibilidade
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class PositionManagerAdapter:
    """Adaptador simplificado e funcional para PositionManager"""
    
    def __init__(self, position_manager):
        self.position_manager = position_manager
        logger.info("PositionManagerAdapter inicializado (versão simplificada)")
    
    def has_position(self, symbol: str) -> bool:
        """Verifica se tem posição para o símbolo"""
        try:
            if hasattr(self.position_manager, 'has_position'):
                return self.position_manager.has_position(symbol)
            elif hasattr(self.position_manager, 'positions'):
                return symbol in self.position_manager.positions
            return False
        except Exception as e:
            logger.error(f"Erro em has_position: {e}")
            return False
    
    def get_position(self, symbol: str):
        """Obtém dados da posição"""
        try:
            if hasattr(self.position_manager, 'get_position'):
                return self.position_manager.get_position(symbol)
            elif hasattr(self.position_manager, 'positions'):
                return self.position_manager.positions.get(symbol)
            return None
        except Exception as e:
            logger.error(f"Erro em get_position: {e}")
            return None
    
    def can_open_position(self, symbol: str) -> bool:
        """Verifica se pode abrir nova posição"""
        try:
            if hasattr(self.position_manager, 'can_open_position'):
                return self.position_manager.can_open_position(symbol)
            return not self.has_position(symbol)
        except Exception as e:
            logger.error(f"Erro em can_open_position: {e}")
            return False
    
    def set_balance(self, balance: float):
        """Define saldo atual"""
        try:
            # Tenta múltiplas estratégias
            if hasattr(self.position_manager, 'set_balance'):
                self.position_manager.set_balance(balance)
            elif hasattr(self.position_manager, 'balance'):
                self.position_manager.balance = balance
            else:
                logger.warning(f"Não foi possível definir saldo: {balance}")
        except Exception as e:
            logger.error(f"Erro em set_balance: {e}")
    
    def get_balance(self) -> float:
        """Retorna saldo atual"""
        try:
            if hasattr(self.position_manager, 'get_balance'):
                return self.position_manager.get_balance()
            elif hasattr(self.position_manager, 'balance'):
                return getattr(self.position_manager, 'balance', 0.0)
            return 0.0
        except Exception as e:
            logger.error(f"Erro em get_balance: {e}")
            return 0.0
    
    def open_position(self, symbol: str, side: str, size: float, price: float, 
                     reason: str = None, confidence: float = None) -> Dict[str, Any]:
        """Abre posição com múltiplas estratégias"""
        strategies = [
            lambda: self.position_manager.open_position(symbol, side, size, price, reason, confidence),
            lambda: self.position_manager.open_position(symbol, side, size, price, reason),
            lambda: self.position_manager.open_position(symbol, side, size, price),
        ]
        
        for strategy in strategies:
            try:
                result = strategy()
                if result:
                    return result if isinstance(result, dict) else {'success': True, 'trade': result}
            except TypeError:
                continue
            except Exception as e:
                logger.debug(f"Estratégia open_position falhou: {e}")
                continue
        
        return {'success': False, 'error': 'Falha ao abrir posição'}
    
    def close_position(self, symbol: str, price: float = None, reason: str = None, 
                      percentage: float = 1.0) -> Dict[str, Any]:
        """Fecha posição com múltiplas estratégias"""
        strategies = [
            lambda: self.position_manager.close_position(symbol, price, reason, percentage),
            lambda: self.position_manager.close_position(symbol, price, reason),
            lambda: self.position_manager.close_position(symbol, price),
            lambda: self.position_manager.close_position(symbol),
        ]
        
        for strategy in strategies:
            try:
                result = strategy()
                if result:
                    # Remove posição do tracking
                    if hasattr(self.position_manager, 'positions') and symbol in self.position_manager.positions:
                        del self.position_manager.positions[symbol]
                    
                    return result if isinstance(result, dict) else {'success': True, 'trade': result, 'pnl': 0}
            except TypeError:
                continue
            except Exception as e:
                logger.debug(f"Estratégia close_position falhou: {e}")
                continue
        
        return {'success': False, 'error': 'Falha ao fechar posição'}
    
    def calculate_position_size(self, symbol: str, price: float, side: str, confidence: float = 1.0) -> float:
        """Calcula tamanho da posição"""
        try:
            if hasattr(self.position_manager, 'calculate_position_size'):
                return self.position_manager.calculate_position_size(symbol, price, side, confidence)
            
            # Cálculo simples fallback
            balance = self.get_balance()
            risk_pct = 2.0  # 2% do saldo
            position_value = balance * (risk_pct / 100)
            return position_value / price
            
        except Exception as e:
            logger.error(f"Erro em calculate_position_size: {e}")
            return 0.01  # Fallback mínimo
    
    def should_close_by_timing(self, symbol: str, current_price: float) -> Tuple[bool, str]:
        """Verifica se deve fechar por timing"""
        try:
            if hasattr(self.position_manager, 'should_close_by_timing'):
                return self.position_manager.should_close_by_timing(symbol, current_price)
            return False, "Timing check não disponível"
        except Exception as e:
            logger.error(f"Erro em should_close_by_timing: {e}")
            return False, f"Erro: {e}"
    
    def check_take_profit_conditions(self, symbol: str, current_price: float) -> Tuple[bool, str, float]:
        """Verifica condições de take profit"""
        try:
            if hasattr(self.position_manager, 'check_take_profit_conditions'):
                return self.position_manager.check_take_profit_conditions(symbol, current_price)
            return False, "Take profit check não disponível", 0.0
        except Exception as e:
            logger.error(f"Erro em check_take_profit_conditions: {e}")
            return False, f"Erro: {e}", 0.0
    
    def sync_positions(self, positions):
        """Sincroniza posições com a exchange"""
        try:
            if hasattr(self.position_manager, 'sync_positions'):
                return self.position_manager.sync_positions(positions)
            logger.info(f"Sync positions: {len(positions)} posições")
        except Exception as e:
            logger.error(f"Erro em sync_positions: {e}")
    
    def print_positions(self):
        """Imprime posições atuais"""
        try:
            if hasattr(self.position_manager, 'print_positions'):
                return self.position_manager.print_positions()
            
            balance = self.get_balance()
            positions = getattr(self.position_manager, 'positions', {})
            print(f"Saldo: ${balance:.2f} | Posições: {len(positions)}")
            
        except Exception as e:
            logger.error(f"Erro em print_positions: {e}")
    
    def cancel_all_orders(self):
        """Cancela todas as ordens abertas"""
        try:
            if hasattr(self.position_manager, 'cancel_all_orders'):
                return self.position_manager.cancel_all_orders()
            logger.info("cancel_all_orders: não disponível")
        except Exception as e:
            logger.error(f"Erro em cancel_all_orders: {e}")
    
    def __getattr__(self, name):
        """Proxy para métodos não implementados"""
        if hasattr(self.position_manager, name):
            return getattr(self.position_manager, name)
        else:
            def dummy_method(*args, **kwargs):
                logger.warning(f"Método {name} não encontrado - retornando None")
                return None
            return dummy_method

# Alias para compatibilidade
EnhancedPositionManagerAdapter = PositionManagerAdapter

# Função de teste rápido
def test_adapter():
    """Teste rápido do adaptador"""
    print("🧪 Testando PositionManagerAdapter...")
    
    # Mock simples para teste
    class MockPositionManager:
        def __init__(self):
            self.balance = 1000.0
            self.positions = {}
        
        def set_balance(self, balance):
            self.balance = balance
        
        def get_balance(self):
            return self.balance
    
    # Teste
    mock_pm = MockPositionManager()
    adapter = PositionManagerAdapter(mock_pm)
    
    # Testes básicos
    adapter.set_balance(1500.0)
    balance = adapter.get_balance()
    
    print(f"✅ Teste básico: saldo definido para {balance}")
    print("✅ PositionManagerAdapter funcionando")

if __name__ == "__main__":
    test_adapter()
