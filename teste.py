#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste para o método should_close_by_timing
"""

def test_timing_method():
    """Testa se o método funciona corretamente"""
    
    # Mock de uma posição para teste
    class MockPosition:
        def __init__(self):
            from datetime import datetime, timedelta
            self.symbol = "SOL/USDT"
            self.side = "long"
            self.size = 0.01
            self.entry_price = 217.0
            self.pnl = -5.0  # Prejuízo de $5
            self.open_time = datetime.now() - timedelta(hours=5)  # Aberta há 5 horas
            self.status = "open"
    
    # Mock do PositionManager
    class MockPositionManager:
        def __init__(self):
            self.positions = {
                "SOL/USDT": MockPosition()
            }
        
        # Coloque aqui o método should_close_by_timing que você implementou
        def should_close_by_timing(self, symbol: str, current_price: float):
            # Use o código do artifact aqui
            pass
    
    # Teste
    try:
        pm = MockPositionManager()
        
        # Simula a chamada do bot_integrated.py
        should_close_timing, timing_reason = pm.should_close_by_timing("SOL/USDT", 215.0)
        
        print("✅ Teste bem-sucedido!")
        print(f"Should close: {should_close_timing}")
        print(f"Reason: {timing_reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Teste falhou: {e}")
        return False

if __name__ == "__main__":
    test_timing_method()