#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Grid Bot - Bot de trading com estratégia de grid
Implementação de exemplo para mostrar extensibilidade do sistema
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_bot import BaseBot
from ..analysis.performance.metrics_calculator import calculate_portfolio_metrics

logger = logging.getLogger(__name__)

class GridBot(BaseBot):
    """Bot que implementa estratégia de grid trading"""
    
    def __init__(self, config):
        super().__init__(config)
        
        # Grid parameters
        self.grid_levels: List[float] = []
        self.buy_orders: Dict[str, Any] = {}
        self.sell_orders: Dict[str, Any] = {}
        self.center_price: Optional[float] = None
        self.grid_spacing: float = 0.01  # 1% default
        self.grid_size: int = 10  # 10 levels default
        
        # Estado do grid
        self.grid_initialized = False
    
    def _initialize_components(self):
        """Inicializa componentes específicos do grid bot"""
        try:
            # Carrega parâmetros do grid da configuração
            self.grid_spacing = self.get_config('grid.spacing_percent', 1.0) / 100.0
            self.grid_size = self.get_config('grid.levels', 10)
            
            # Mock de componentes para exemplo
            # Em implementação real, conectaria com exchange
            self.components['exchange_api'] = None  # Seria BingXAPI ou similar
            self.components['price_monitor'] = self._create_price_monitor()
            self.components['order_manager'] = self._create_order_manager()
            
            logger.info(f"Grid bot inicializado: {self.grid_size} níveis, {self.grid_spacing*100:.1f}% spacing")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar grid bot: {e}")
            raise
    
    def _execute_trading_cycle(self):
        """Executa ciclo de trading do grid"""
        try:
            symbol = self.get_config('trading.primary_pair', 'BTCUSDT')
            current_price = self._get_current_price(symbol)
            
            if not current_price:
                logger.warning(f"Não foi possível obter preço para {symbol}")
                return
            
            # Inicializa grid se necessário
            if not self.grid_initialized:
                self._initialize_grid(current_price)
            
            # Monitora e executa ordens do grid
            self._process_grid_orders(current_price)
            
            # Rebalanceia grid se necessário
            self._rebalance_grid_if_needed(current_price)
            
        except Exception as e:
            logger.error(f"Erro no ciclo do grid: {e}")
            raise
    
    def _cleanup_resources(self):
        """Limpa recursos do grid bot"""
        try:
            # Cancela todas as ordens pendentes
            self._cancel_all_grid_orders()
            
            # Limpa estado
            self.buy_orders.clear()
            self.sell_orders.clear()
            self.grid_levels.clear()
            self.grid_initialized = False
            
            logger.info("Recursos do grid bot limpos")
            
        except Exception as e:
            logger.error(f"Erro na limpeza do grid: {e}")
    
    def _initialize_grid(self, center_price: float):
        """Inicializa o grid de ordens"""
        self.center_price = center_price
        self.grid_levels.clear()
        
        # Calcula níveis do grid
        for i in range(-self.grid_size // 2, self.grid_size // 2 + 1):
            level_price = center_price * (1 + i * self.grid_spacing)
            self.grid_levels.append(level_price)
        
        # Coloca ordens iniciais
        self._place_initial_grid_orders()
        
        self.grid_initialized = True
        logger.info(f"Grid inicializado com {len(self.grid_levels)} níveis ao redor de ${center_price:.4f}")
    
    def _place_initial_grid_orders(self):
        """Coloca ordens iniciais do grid"""
        order_size = self.get_config('trading.grid_order_size_usdt', 50.0)
        
        for price in self.grid_levels:
            if price < self.center_price:
                # Ordens de compra abaixo do preço atual
                order_id = self._place_buy_order(price, order_size / price)
                if order_id:
                    self.buy_orders[order_id] = {
                        'price': price,
                        'quantity': order_size / price,
                        'level': price
                    }
            elif price > self.center_price:
                # Ordens de venda acima do preço atual
                order_id = self._place_sell_order(price, order_size / price)
                if order_id:
                    self.sell_orders[order_id] = {
                        'price': price,
                        'quantity': order_size / price,
                        'level': price
                    }
    
    def _process_grid_orders(self, current_price: float):
        """Processa execuções das ordens do grid"""
        # Verifica ordens executadas (mock)
        executed_buy_orders = self._check_executed_orders(self.buy_orders, current_price)
        executed_sell_orders = self._check_executed_orders(self.sell_orders, current_price)
        
        # Processa compras executadas
        for order_id in executed_buy_orders:
            order = self.buy_orders.pop(order_id)
            self._handle_buy_execution(order, current_price)
        
        # Processa vendas executadas
        for order_id in executed_sell_orders:
            order = self.sell_orders.pop(order_id)
            self._handle_sell_execution(order, current_price)
    
    def _handle_buy_execution(self, order: Dict[str, Any], current_price: float):
        """Manuseia execução de ordem de compra"""
        # Registra trade
        trade_data = {
            'symbol': self.get_config('trading.primary_pair', 'BTCUSDT'),
            'side': 'buy',
            'quantity': order['quantity'],
            'price': order['price'],
            'pnl': 0,  # Será calculado na venda
            'entry_time': datetime.now(),
            'strategy': 'grid_buy'
        }
        
        self.update_trade_metrics(trade_data)
        
        # Coloca ordem de venda correspondente no próximo nível
        next_sell_price = order['price'] * (1 + self.grid_spacing)
        sell_order_id = self._place_sell_order(next_sell_price, order['quantity'])
        
        if sell_order_id:
            self.sell_orders[sell_order_id] = {
                'price': next_sell_price,
                'quantity': order['quantity'],
                'level': next_sell_price,
                'paired_with': order
            }
        
        logger.info(f"Grid: Compra executada a ${order['price']:.4f}, venda colocada a ${next_sell_price:.4f}")
    
    def _handle_sell_execution(self, order: Dict[str, Any], current_price: float):
        """Manuseia execução de ordem de venda"""
        # Calcula PnL se ordem estava pareada
        pnl = 0
        if 'paired_with' in order:
            buy_price = order['paired_with']['price']
            sell_price = order['price']
            quantity = order['quantity']
            pnl = (sell_price - buy_price) * quantity
        
        # Registra trade
        trade_data = {
            'symbol': self.get_config('trading.primary_pair', 'BTCUSDT'),
            'side': 'sell',
            'quantity': order['quantity'],
            'price': order['price'],
            'pnl': pnl,
            'exit_time': datetime.now(),
            'strategy': 'grid_sell'
        }
        
        self.update_trade_metrics(trade_data)
        
        # Coloca ordem de compra correspondente no nível anterior
        next_buy_price = order['price'] * (1 - self.grid_spacing)
        buy_order_id = self._place_buy_order(next_buy_price, order['quantity'])
        
        if buy_order_id:
            self.buy_orders[buy_order_id] = {
                'price': next_buy_price,
                'quantity': order['quantity'],
                'level': next_buy_price
            }
        
        logger.info(f"Grid: Venda executada a ${order['price']:.4f}, compra colocada a ${next_buy_price:.4f}, PnL: ${pnl:.2f}")
    
    def _rebalance_grid_if_needed(self, current_price: float):
        """Rebalanceia grid se preço saiu muito do centro"""
        if not self.center_price:
            return
        
        price_deviation = abs(current_price - self.center_price) / self.center_price
        max_deviation = self.get_config('grid.max_deviation_percent', 10.0) / 100.0
        
        if price_deviation > max_deviation:
            logger.info(f"Rebalanceando grid: desvio de {price_deviation*100:.1f}%")
            self._cancel_all_grid_orders()
            self._initialize_grid(current_price)
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Obtém preço atual (mock implementation)"""
        # Em implementação real, consultaria API da exchange
        # Para este exemplo, simula variação de preço
        import random
        
        if not hasattr(self, '_mock_price'):
            self._mock_price = 50000.0  # Preço inicial simulado
        
        # Simula variação de ±0.1%
        variation = random.uniform(-0.001, 0.001)
        self._mock_price *= (1 + variation)
        
        return self._mock_price
    
    def _place_buy_order(self, price: float, quantity: float) -> Optional[str]:
        """Coloca ordem de compra (mock)"""
        # Em implementação real, usaria API da exchange
        order_id = f"buy_{datetime.now().timestamp()}"
        logger.debug(f"Mock: Ordem de compra colocada - {quantity:.6f} @ ${price:.4f}")
        return order_id
    
    def _place_sell_order(self, price: float, quantity: float) -> Optional[str]:
        """Coloca ordem de venda (mock)"""
        # Em implementação real, usaria API da exchange
        order_id = f"sell_{datetime.now().timestamp()}"
        logger.debug(f"Mock: Ordem de venda colocada - {quantity:.6f} @ ${price:.4f}")
        return order_id
    
    def _check_executed_orders(self, orders: Dict[str, Any], current_price: float) -> List[str]:
        """Verifica quais ordens foram executadas (mock)"""
        executed = []
        
        for order_id, order in orders.items():
            # Mock: simula execução baseada em preço atual
            if ('buy' in order_id and current_price <= order['price'] * 1.0001) or \
               ('sell' in order_id and current_price >= order['price'] * 0.9999):
                executed.append(order_id)
        
        return executed
    
    def _cancel_all_grid_orders(self):
        """Cancela todas as ordens do grid"""
        # Em implementação real, cancelaria via API
        cancelled_count = len(self.buy_orders) + len(self.sell_orders)
        self.buy_orders.clear()
        self.sell_orders.clear()
        
        if cancelled_count > 0:
            logger.info(f"Mock: {cancelled_count} ordens canceladas")
    
    def _create_price_monitor(self):
        """Cria monitor de preços (mock)"""
        return {'status': 'active', 'type': 'mock_price_monitor'}
    
    def _create_order_manager(self):
        """Cria gerenciador de ordens (mock)"""
        return {'status': 'active', 'type': 'mock_order_manager'}
    
    def get_grid_status(self) -> Dict[str, Any]:
        """Obtém status detalhado do grid"""
        return {
            'grid_initialized': self.grid_initialized,
            'center_price': self.center_price,
            'grid_levels': len(self.grid_levels),
            'active_buy_orders': len(self.buy_orders),
            'active_sell_orders': len(self.sell_orders),
            'grid_spacing_percent': self.grid_spacing * 100,
            'current_spread': {
                'lowest_buy': min((order['price'] for order in self.buy_orders.values()), default=0),
                'highest_sell': max((order['price'] for order in self.sell_orders.values()), default=0)
            }
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtém resumo de performance específico do grid"""
        summary = super().get_performance_summary()
        
        # Adiciona métricas específicas do grid
        grid_metrics = {
            'grid_efficiency': self._calculate_grid_efficiency(),
            'average_profit_per_cycle': self._calculate_avg_profit_per_cycle(),
            'grid_coverage': self._calculate_grid_coverage(),
            'rebalance_count': getattr(self, '_rebalance_count', 0)
        }
        
        summary.update(grid_metrics)
        return summary
    
    def _calculate_grid_efficiency(self) -> float:
        """Calcula eficiência do grid (% de ordens executadas)"""
        total_possible_orders = self.grid_size * 2  # Buy + sell orders
        current_active = len(self.buy_orders) + len(self.sell_orders)
        
        if total_possible_orders == 0:
            return 0.0
        
        return ((total_possible_orders - current_active) / total_possible_orders) * 100
    
    def _calculate_avg_profit_per_cycle(self) -> float:
        """Calcula lucro médio por ciclo completo do grid"""
        if self.metrics.total_trades == 0:
            return 0.0
        
        # Assume que cada 2 trades (buy + sell) = 1 ciclo
        cycles = max(1, self.metrics.total_trades // 2)
        return self.metrics.total_pnl / cycles
    
    def _calculate_grid_coverage(self) -> float:
        """Calcula % de cobertura do grid em relação ao preço atual"""
        if not self.grid_levels or not self.center_price:
            return 0.0
        
        current_price = self._get_current_price(self.get_config('trading.primary_pair', 'BTCUSDT'))
        if not current_price:
            return 0.0
        
        min_level = min(self.grid_levels)
        max_level = max(self.grid_levels)
        
        if min_level <= current_price <= max_level:
            return 100.0
        else:
            return 0.0  # Price is outside grid range