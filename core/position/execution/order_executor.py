# core/position/execution/order_executor.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Order Executor - Responsável pela execução de ordens
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ..sizing import PositionSizerFactory

logger = logging.getLogger(__name__)

class OrderExecutionResult:
    """Resultado da execução de uma ordem"""
    
    def __init__(self, success: bool, trade_data: Dict = None, error: str = None):
        self.success = success
        self.trade_data = trade_data or {}
        self.error = error
        self.timestamp = datetime.now()

class OrderExecutor:
    """Executa ordens de abertura e fechamento de posições"""
    
    def __init__(self, config: Dict[str, Any], api=None, paper_trading: bool = True):
        self.config = config
        self.api = api
        self.paper_trading = paper_trading
        
        # Position sizer
        sizer_type = config.get('position_sizing', {}).get('method', 'traditional')
        self.position_sizer = PositionSizerFactory.create(sizer_type, config)
        
        logger.info(f"OrderExecutor inicializado - Paper: {paper_trading}, Sizer: {sizer_type}")
    
    def execute_entry_order(self, symbol: str, side: str, price: float, 
                           balance: float, signal_confidence: float = 1.0,
                           reason: str = None, **kwargs) -> OrderExecutionResult:
        """Executa ordem de entrada"""
        try:
            # Calcula tamanho da posição
            sizing_result = self.position_sizer.calculate_size(
                symbol=symbol,
                price=price,
                balance=balance,
                signal_confidence=signal_confidence,
                **kwargs
            )
            
            size = sizing_result.size
            
            # Validações básicas
            if size <= 0:
                return OrderExecutionResult(False, error="Tamanho de posição inválido")
            
            # Aplica limites específicos do par
            pair_config = self._get_pair_config(symbol)
            min_size = pair_config.get('min_position_size', 0.01)
            max_size = pair_config.get('max_position_size', 1.0)
            step_size = pair_config.get('step_size', 0.001)
            
            size = self.position_sizer.validate_size(size, min_size, max_size, step_size)
            
            # Executa ordem
            if self.paper_trading:
                result = self._execute_paper_entry(symbol, side, size, price, reason, sizing_result)
            else:
                result = self._execute_real_entry(symbol, side, size, price, reason, pair_config)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao executar entrada: {e}")
            return OrderExecutionResult(False, error=str(e))
    
    def execute_exit_order(self, symbol: str, position_data: Dict, 
                          exit_price: float, reason: str, 
                          percentage: float = 1.0) -> OrderExecutionResult:
        """Executa ordem de saída"""
        try:
            if self.paper_trading:
                result = self._execute_paper_exit(symbol, position_data, exit_price, reason, percentage)
            else:
                result = self._execute_real_exit(symbol, position_data, exit_price, reason, percentage)
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao executar saída: {e}")
            return OrderExecutionResult(False, error=str(e))
    
    def _execute_paper_entry(self, symbol: str, side: str, size: float, 
                           price: float, reason: str, sizing_result) -> OrderExecutionResult:
        """Executa entrada em paper trading"""
        
        leverage = self._get_pair_config(symbol).get('leverage', 2)
        margin_used = (size * price) / leverage
        
        trade_data = {
            'symbol': symbol,
            'side': side,
            'action': 'open',
            'quantity': size,
            'entry_price': price,
            'exit_price': None,
            'pnl': 0.0,
            'margin_used': margin_used,
            'leverage': leverage,
            'entry_time': datetime.now(),
            'exit_time': None,
            'reason': reason,
            'real_trade': False,
            'sizing_details': sizing_result.details
        }
        
        logger.info(f"[PAPER] Posição aberta: {side.upper()} {size:.4f} {symbol} @ ${price:.4f}")
        
        return OrderExecutionResult(True, trade_data)
    
    def _execute_real_entry(self, symbol: str, side: str, size: float, 
                          price: float, reason: str, pair_config: Dict) -> OrderExecutionResult:
        """Executa entrada em trading real"""
        if not self.api:
            return OrderExecutionResult(False, error="API não disponível")
        
        try:
            futures_symbol = pair_config.get('futures_symbol', symbol.replace('/', '-'))
            leverage = pair_config.get('leverage', 2)
            
            # Define leverage
            try:
                self.api.set_leverage(futures_symbol, leverage, side=side.upper())
            except Exception as e:
                logger.warning(f"Erro ao definir leverage: {e}")
            
            # Executa ordem
            order_side = "BUY" if side == 'long' else "SELL"
            position_side = "LONG" if side == 'long' else "SHORT"
            
            result = self.api.place_order(
                symbol=futures_symbol,
                side=order_side,
                position_side=position_side,
                quantity=size,
                order_type="MARKET"
            )
            
            order_id = result.get('order', {}).get('orderId', 'unknown')
            
            trade_data = {
                'symbol': symbol,
                'side': side,
                'action': 'open',
                'quantity': size,
                'entry_price': price,
                'pnl': 0.0,
                'leverage': leverage,
                'entry_time': datetime.now(),
                'reason': reason,
                'real_trade': True,
                'order_id': order_id
            }
            
            logger.info(f"[REAL] Ordem executada: {order_id}")
            
            return OrderExecutionResult(True, trade_data)
            
        except Exception as e:
            logger.error(f"Erro na execução real: {e}")
            return OrderExecutionResult(False, error=str(e))
    
    def _execute_paper_exit(self, symbol: str, position_data: Dict, 
                          exit_price: float, reason: str, percentage: float) -> OrderExecutionResult:
        """Executa saída em paper trading"""
        
        entry_price = position_data.get('entry_price', 0)
        size = position_data.get('quantity', 0) * percentage
        side = position_data.get('side', 'long')
        
        # Calcula PnL
        if side.lower() == 'long':
            pnl = (exit_price - entry_price) * size
        else:
            pnl = (entry_price - exit_price) * size
        
        # Deduz fees
        fees = self.config.get('exchanges', {}).get('bingx', {}).get('fees', {}).get('taker', 0.0004)
        fee_cost = size * exit_price * fees
        pnl_net = pnl - fee_cost
        
        trade_data = {
            'symbol': symbol,
            'side': f'close_{side}' if percentage == 1.0 else f'partial_close_{side}',
            'action': 'close',
            'quantity': size,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl_net,
            'exit_time': datetime.now(),
            'reason': reason,
            'percentage': percentage,
            'real_trade': False
        }
        
        action_text = "fechada" if percentage == 1.0 else f"parcialmente fechada ({percentage*100:.0f}%)"
        logger.info(f"[PAPER] Posição {action_text}: PnL ${pnl_net:.2f}")
        
        return OrderExecutionResult(True, trade_data)
    
    def _execute_real_exit(self, symbol: str, position_data: Dict, 
                         exit_price: float, reason: str, percentage: float) -> OrderExecutionResult:
        """Executa saída em trading real"""
        if not self.api:
            return OrderExecutionResult(False, error="API não disponível")
        
        try:
            pair_config = self._get_pair_config(symbol)
            futures_symbol = pair_config.get('futures_symbol', symbol.replace('/', '-'))
            
            side = position_data.get('side', 'long')
            original_size = position_data.get('quantity', 0)
            exit_size = original_size * percentage
            
            # Ordem de fechamento
            order_side = "SELL" if side == 'long' else "BUY"
            position_side = side.upper()
            
            result = self.api.place_order(
                symbol=futures_symbol,
                side=order_side,
                position_side=position_side,
                quantity=exit_size,
                order_type="MARKET"
            )
            
            # Calcula PnL aproximado
            entry_price = position_data.get('entry_price', 0)
            if side.lower() == 'long':
                pnl = (exit_price - entry_price) * exit_size
            else:
                pnl = (entry_price - exit_price) * exit_size
            
            trade_data = {
                'symbol': symbol,
                'side': f'close_{side}' if percentage == 1.0 else f'partial_close_{side}',
                'action': 'close',
                'quantity': exit_size,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'pnl': pnl,
                'exit_time': datetime.now(),
                'reason': reason,
                'percentage': percentage,
                'real_trade': True,
                'order_id': result.get('order', {}).get('orderId', 'unknown')
            }
            
            return OrderExecutionResult(True, trade_data)
            
        except Exception as e:
            logger.error(f"Erro na saída real: {e}")
            return OrderExecutionResult(False, error=str(e))
    
    def _get_pair_config(self, symbol: str) -> Dict:
        """Obtém configuração específica do par"""
        trading_pairs = self.config.get('trading', {}).get('trading_pairs', [])
        for pair in trading_pairs:
            if pair.get('symbol') == symbol:
                return pair
        return trading_pairs[0] if trading_pairs else {}


# core/position/execution/position_tracker.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Tracker - Rastreia e gerencia posições ativas
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PositionTracker:
    """Rastreia posições ativas e seu estado"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.positions = {}  # symbol -> position_data
        self.position_history = []
        self.max_concurrent = config.get('strategy', {}).get('max_concurrent_positions', 1)
        
        logger.info(f"PositionTracker inicializado - Max posições: {self.max_concurrent}")
    
    def add_position(self, symbol: str, position_data: Dict) -> bool:
        """Adiciona nova posição ao tracking"""
        if len(self.positions) >= self.max_concurrent:
            logger.warning(f"Limite de posições atingido: {len(self.positions)}/{self.max_concurrent}")
            return False
        
        if symbol in self.positions:
            logger.warning(f"Posição já existe para {symbol}")
            return False
        
        # Adiciona timestamp de tracking
        position_data['tracked_since'] = datetime.now()
        position_data['last_update'] = datetime.now()
        
        self.positions[symbol] = position_data
        logger.info(f"Posição adicionada ao tracking: {symbol}")
        return True
    
    def update_position(self, symbol: str, updates: Dict) -> bool:
        """Atualiza dados da posição"""
        if symbol not in self.positions:
            logger.warning(f"Posição não encontrada para update: {symbol}")
            return False
        
        self.positions[symbol].update(updates)
        self.positions[symbol]['last_update'] = datetime.now()
        return True
    
    def remove_position(self, symbol: str, reason: str = "closed") -> Optional[Dict]:
        """Remove posição do tracking"""
        if symbol not in self.positions:
            return None
        
        position_data = self.positions.pop(symbol)
        position_data['removed_at'] = datetime.now()
        position_data['removal_reason'] = reason
        
        # Adiciona ao histórico
        self.position_history.append(position_data)
        
        # Mantém histórico limitado
        if len(self.position_history) > 100:
            self.position_history = self.position_history[-100:]
        
        logger.info(f"Posição removida do tracking: {symbol} ({reason})")
        return position_data
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Obtém dados da posição"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Verifica se tem posição para o símbolo"""
        return symbol in self.positions
    
    def get_all_positions(self) -> Dict[str, Dict]:
        """Retorna todas as posições ativas"""
        return self.positions.copy()
    
    def get_position_count(self) -> int:
        """Retorna número de posições ativas"""
        return len(self.positions)
    
    def can_open_new_position(self) -> bool:
        """Verifica se pode abrir nova posição"""
        return len(self.positions) < self.max_concurrent
    
    def get_positions_by_side(self, side: str) -> List[str]:
        """Retorna símbolos das posições do lado especificado"""
        return [symbol for symbol, pos in self.positions.items() 
                if pos.get('side', '').lower() == side.lower()]
    
    def calculate_unrealized_pnl(self, symbol: str, current_price: float) -> float:
        """Calcula PnL não realizado da posição"""
        position = self.get_position(symbol)
        if not position:
            return 0.0
        
        entry_price = position.get('entry_price', 0)
        quantity = position.get('quantity', 0)
        side = position.get('side', 'long')
        
        if side.lower() == 'long':
            return (current_price - entry_price) * quantity
        else:
            return (entry_price - current_price) * quantity
    
    def get_positions_summary(self) -> Dict:
        """Retorna resumo das posições"""
        total_positions = len(self.positions)
        long_positions = len(self.get_positions_by_side('long'))
        short_positions = len(self.get_positions_by_side('short'))
        
        return {
            'total': total_positions,
            'long': long_positions,
            'short': short_positions,
            'available_slots': self.max_concurrent - total_positions,
            'symbols': list(self.positions.keys())
        }
    
    def get_oldest_position(self) -> Optional[tuple]:
        """Retorna a posição mais antiga (símbolo, dados)"""
        if not self.positions:
            return None
        
        oldest_symbol = min(
            self.positions.keys(),
            key=lambda s: self.positions[s].get('entry_time', datetime.now())
        )
        
        return oldest_symbol, self.positions[oldest_symbol]
    
    def get_positions_older_than(self, minutes: int) -> List[tuple]:
        """Retorna posições mais antigas que X minutos"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        old_positions = []
        
        for symbol, position in self.positions.items():
            entry_time = position.get('entry_time')
            if entry_time and entry_time < cutoff:
                old_positions.append((symbol, position))
        
        return old_positions
    
    def cleanup_history(self, max_entries: int = 50):
        """Limpa histórico de posições"""
        if len(self.position_history) > max_entries:
            self.position_history = self.position_history[-max_entries:]
            logger.info(f"Histórico de posições limitado a {max_entries} entradas")


# core/position/execution/exit_manager.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exit Manager - Gerencia condições de saída (TP, SL, timing)
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ExitCondition:
    """Representa uma condição de saída"""
    
    def __init__(self, condition_type: str, reason: str, priority: int = 1):
        self.type = condition_type  # 'stop_loss', 'take_profit', 'timing', 'technical'
        self.reason = reason
        self.priority = priority  # 1 = alta prioridade
        self.timestamp = datetime.now()

class ExitManager:
    """Gerencia todas as condições de saída de posições"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.active_conditions = {}  # symbol -> list of conditions
        
        # Configurações de saída
        self.stop_loss_pct = config.get('risk_management', {}).get('stop_loss', {}).get('percentage', 2.0)
        self.take_profit_pct = config.get('risk_management', {}).get('take_profit', {}).get('percentage', 3.0)
        self.max_hold_seconds = config.get('strategy', {}).get('max_position_hold_seconds', 7200)
        self.min_hold_seconds = config.get('strategy', {}).get('min_position_hold_seconds', 300)
        
        logger.info(f"ExitManager inicializado - SL: {self.stop_loss_pct}%, TP: {self.take_profit_pct}%")
    
    def check_exit_conditions(self, symbol: str, position: Dict, 
                            current_price: float) -> Optional[ExitCondition]:
        """Verifica todas as condições de saída para uma posição"""
        
        # Stop Loss (prioridade 1)
        sl_condition = self._check_stop_loss(position, current_price)
        if sl_condition:
            return sl_condition
        
        # Take Profit (prioridade 1)
        tp_condition = self._check_take_profit(position, current_price)
        if tp_condition:
            return tp_condition
        
        # Timing - tempo máximo (prioridade 2)
        timing_condition = self._check_max_timing(position)
        if timing_condition:
            return timing_condition
        
        # Quick profit (prioridade 3)
        quick_condition = self._check_quick_profit(position, current_price)
        if quick_condition:
            return quick_condition
        
        return None
    
    def _check_stop_loss(self, position: Dict, current_price: float) -> Optional[ExitCondition]:
        """Verifica condição de stop loss"""
        entry_price = position.get('entry_price', 0)
        side = position.get('side', 'long')
        
        if not entry_price:
            return None
        
        # Calcula PnL percentual
        if side.lower() == 'long':
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        if pnl_pct <= -self.stop_loss_pct:
            return ExitCondition(
                'stop_loss',
                f"Stop Loss: {pnl_pct:.2f}% <= -{self.stop_loss_pct}%",
                priority=1
            )
        
        return None
    
    def _check_take_profit(self, position: Dict, current_price: float) -> Optional[ExitCondition]:
        """Verifica condição de take profit"""
        entry_price = position.get('entry_price', 0)
        side = position.get('side', 'long')
        
        if not entry_price:
            return None
        
        # Calcula PnL percentual
        if side.lower() == 'long':
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        if pnl_pct >= self.take_profit_pct:
            return ExitCondition(
                'take_profit',
                f"Take Profit: {pnl_pct:.2f}% >= {self.take_profit_pct}%",
                priority=1
            )
        
        return None
    
    def _check_max_timing(self, position: Dict) -> Optional[ExitCondition]:
        """Verifica tempo máximo em posição"""
        entry_time = position.get('entry_time')
        if not entry_time:
            return None
        
        time_in_position = (datetime.now() - entry_time).total_seconds()
        
        if time_in_position >= self.max_hold_seconds:
            minutes = time_in_position / 60
            return ExitCondition(
                'max_timing',
                f"Tempo máximo atingido: {minutes:.1f}min",
                priority=2
            )
        
        return None
    
    def _check_quick_profit(self, position: Dict, current_price: float) -> Optional[ExitCondition]:
        """Verifica saída rápida por lucro"""
        entry_time = position.get('entry_time')
        entry_price = position.get('entry_price', 0)
        side = position.get('side', 'long')
        
        if not entry_time or not entry_price:
            return None
        
        time_in_position = (datetime.now() - entry_time).total_seconds()
        
        # Só considera quick profit após tempo mínimo
        if time_in_position < self.min_hold_seconds:
            return None
        
        # Calcula PnL
        if side.lower() == 'long':
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Quick profit threshold configurável
        quick_profit_threshold = self.config.get('strategy', {}).get('quick_profit_exit_threshold', 1.0)
        quick_profit_time_limit = self.config.get('strategy', {}).get('quick_profit_time_limit_minutes', 10) * 60
        
        if pnl_pct >= quick_profit_threshold and time_in_position <= quick_profit_time_limit:
            minutes = time_in_position / 60
            return ExitCondition(
                'quick_profit',
                f"Quick profit: +{pnl_pct:.2f}% em {minutes:.1f}min",
                priority=3
            )
        
        return None
    
    def should_partial_exit(self, symbol: str, position: Dict, 
                          current_price: float) -> Tuple[bool, float, str]:
        """Verifica se deve fazer saída parcial"""
        entry_price = position.get('entry_price', 0)
        side = position.get('side', 'long')
        
        if not entry_price:
            return False, 0.0, "Sem preço de entrada"
        
        # Calcula PnL
        if side.lower() == 'long':
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Configurações de saída parcial
        partial_threshold = self.config.get('risk_management', {}).get('take_profit', {}).get('partial_percentage', 1.5)
        partial_amount = self.config.get('risk_management', {}).get('take_profit', {}).get('partial_amount_pct', 0.5)
        
        # Verifica se já fez parcial
        if position.get('partial_taken', False):
            return False, 0.0, "Já executou take profit parcial"
        
        if pnl_pct >= partial_threshold:
            return True, partial_amount, f"Take profit parcial: +{pnl_pct:.2f}%"
        
        return False, 0.0, f"PnL insuficiente: {pnl_pct:.2f}% < {partial_threshold}%"
    
    def get_exit_targets(self, entry_price: float, side: str) -> Dict[str, float]:
        """Calcula preços-alvo de saída"""
        if side.lower() == 'long':
            take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
            stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)
        else:
            take_profit_price = entry_price * (1 - self.take_profit_pct / 100)
            stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)
        
        return {
            'take_profit': take_profit_price,
            'stop_loss': stop_loss_price
        }


# core/position/execution/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Position Execution Module - Execução e tracking de posições
"""

from .order_executor import OrderExecutor, OrderExecutionResult
from .position_tracker import PositionTracker
from .exit_manager import ExitManager, ExitCondition

__all__ = [
    'OrderExecutor',
    'OrderExecutionResult',
    'PositionTracker',
    'ExitManager',
    'ExitCondition'
]