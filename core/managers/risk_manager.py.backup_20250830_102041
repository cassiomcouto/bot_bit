#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerenciador de Risco - Implementação Completa
Inclui: Stop Loss, Take Profit, Limites Diários, Kill Switch
"""

import logging
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime, timedelta
from models.data_classes import FuturesPosition, PositionSide

logger = logging.getLogger(__name__)

class RiskManager:
    """Gerenciador de risco com implementação completa"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.statistics = {
            'daily_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'best_trade': 0.0,
            'worst_trade': 0.0,
            'consecutive_losses': 0,
            'max_consecutive_losses': 0,
            'daily_loss': 0.0,
            'current_drawdown': 0.0,
            'max_drawdown': 0.0
        }
        
        # Estado do dia
        self.last_reset_date = datetime.now().date()
        self.daily_trade_count = 0
        self.daily_pnl = 0.0
        self.kill_switch_triggered = False
        
        # Configurações de Stop Loss
        self.stop_loss_enabled = self._get_config('risk_management.stop_loss.enabled', True)
        self.stop_loss_pct = self._get_config('risk_management.stop_loss.percentage', 2.0)
        self.trailing_enabled = self._get_config('risk_management.stop_loss.trailing_enabled', True)
        self.trailing_pct = self._get_config('risk_management.stop_loss.trailing_percentage', 0.5)
        
        # Configurações de Take Profit
        self.take_profit_enabled = self._get_config('risk_management.take_profit.enabled', True)
        self.take_profit_pct = self._get_config('risk_management.take_profit.percentage', 3.0)
        
        # Limites diários
        self.max_daily_trades = self._get_config('risk_management.daily_limits.max_trades', 30)
        self.max_daily_loss = self._get_config('risk_management.daily_limits.max_loss_usdt', 30.0)
        self.max_daily_loss_pct = self._get_config('risk_management.daily_limits.max_loss_percentage', 5.0)
        self.max_drawdown_pct = self._get_config('risk_management.daily_limits.max_drawdown_percentage', 10.0)
        
        # Kill Switch
        self.kill_switch_enabled = self._get_config('risk_management.kill_switch.enabled', True)
        self.kill_switch_loss_pct = self._get_config('risk_management.kill_switch.total_loss_percentage', 10.0)
        self.kill_switch_consecutive = self._get_config('risk_management.kill_switch.consecutive_losses', 3)
        
        # Tracking para trailing stops
        self.trailing_stops = {}  # symbol -> best_price
        
        logger.info(f"Risk Manager inicializado:")
        logger.info(f"  Stop Loss: {self.stop_loss_pct}% (Trailing: {self.trailing_enabled})")
        logger.info(f"  Take Profit: {self.take_profit_pct}%")
        logger.info(f"  Limites diários: {self.max_daily_trades} trades, ${self.max_daily_loss} loss")
    
    def _get_config(self, path: str, default=None):
        """Obtém valor de configuração aninhada"""
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def _reset_daily_stats_if_needed(self):
        """Reseta estatísticas diárias se mudou o dia"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            logger.info(f"Resetando estatísticas diárias - Novo dia: {today}")
            self.daily_trade_count = 0
            self.daily_pnl = 0.0
            self.statistics['daily_trades'] = 0
            self.statistics['daily_loss'] = 0.0
            self.last_reset_date = today
    
    def can_open_position(self) -> bool:
        """Verifica se pode abrir nova posição baseado nos limites de risco"""
        self._reset_daily_stats_if_needed()
        
        # Verifica kill switch
        if self.kill_switch_triggered:
            logger.warning("Kill switch ativado - Não é possível abrir posições")
            return False
        
        # Verifica limite de trades diários
        if self.daily_trade_count >= self.max_daily_trades:
            logger.warning(f"Limite diário de trades atingido: {self.daily_trade_count}/{self.max_daily_trades}")
            return False
        
        # Verifica perda diária em USDT
        if abs(self.daily_pnl) >= self.max_daily_loss and self.daily_pnl < 0:
            logger.warning(f"Limite diário de perda atingido: ${self.daily_pnl:.2f} >= ${self.max_daily_loss}")
            return False
        
        # Verifica consecutive losses
        if self.statistics['consecutive_losses'] >= self.kill_switch_consecutive:
            logger.warning(f"Muitas perdas consecutivas: {self.statistics['consecutive_losses']}")
            self._trigger_kill_switch("consecutive_losses")
            return False
        
        return True
    
    def check_exit_conditions(self, position: FuturesPosition, current_price: float) -> Optional[str]:
        """
        Verifica condições de saída obrigatória (Stop Loss, Take Profit, etc)
        Retorna razão para fechar ou None
        """
        if not position:
            return None
        
        symbol = position.symbol
        entry_price = position.entry_price
        
        # Calcula PnL percentual atual
        if position.side == PositionSide.LONG:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        # === STOP LOSS ===
        if self.stop_loss_enabled and pnl_pct <= -self.stop_loss_pct:
            logger.warning(f"Stop Loss atingido: {pnl_pct:.2f}% <= -{self.stop_loss_pct}%")
            return f"Stop Loss ({pnl_pct:.1f}%)"
        
        # === TRAILING STOP ===
        if self.trailing_enabled and symbol in self.trailing_stops:
            best_price = self.trailing_stops[symbol]
            
            if position.side == PositionSide.LONG:
                # Para LONG: trailing stop quando preço cai X% do melhor preço
                trailing_pnl = ((current_price - best_price) / best_price) * 100
                if trailing_pnl <= -self.trailing_pct:
                    logger.warning(f"Trailing Stop atingido: {trailing_pnl:.2f}% <= -{self.trailing_pct}%")
                    return f"Trailing Stop ({trailing_pnl:.1f}%)"
            else:
                # Para SHORT: trailing stop quando preço sobe X% do melhor preço
                trailing_pnl = ((best_price - current_price) / best_price) * 100
                if trailing_pnl <= -self.trailing_pct:
                    logger.warning(f"Trailing Stop atingido: {trailing_pnl:.2f}% <= -{self.trailing_pct}%")
                    return f"Trailing Stop ({trailing_pnl:.1f}%)"
        
        # === TAKE PROFIT ===
        if self.take_profit_enabled and pnl_pct >= self.take_profit_pct:
            logger.info(f"Take Profit atingido: {pnl_pct:.2f}% >= {self.take_profit_pct}%")
            return f"Take Profit ({pnl_pct:.1f}%)"
        
        # Atualiza trailing stop
        self._update_trailing_stop(symbol, current_price, position.side)
        
        return None
    
    def _update_trailing_stop(self, symbol: str, current_price: float, side: PositionSide):
        """Atualiza o trailing stop para a posição"""
        if not self.trailing_enabled:
            return
        
        if symbol not in self.trailing_stops:
            self.trailing_stops[symbol] = current_price
            logger.debug(f"Iniciando trailing stop para {symbol}: ${current_price:.2f}")
            return
        
        best_price = self.trailing_stops[symbol]
        
        if side == PositionSide.LONG:
            # Para LONG: atualiza se preço atual é maior que o melhor registrado
            if current_price > best_price:
                self.trailing_stops[symbol] = current_price
                logger.debug(f"Trailing stop atualizado (LONG) {symbol}: ${best_price:.2f} -> ${current_price:.2f}")
        else:
            # Para SHORT: atualiza se preço atual é menor que o melhor registrado
            if current_price < best_price:
                self.trailing_stops[symbol] = current_price
                logger.debug(f"Trailing stop atualizado (SHORT) {symbol}: ${best_price:.2f} -> ${current_price:.2f}")
    
    def validate_signal(self, signal, indicators: Dict[str, Any]) -> bool:
        """Valida sinal de entrada com filtros de risco"""
        # Verifica se pode abrir posição
        if not self.can_open_position():
            return False
        
        # Validação de confiança mínima
        min_confidence = self._get_config('ai_futures.filters.min_confidence', 0.65)
        if signal.confidence < min_confidence:
            logger.info(f"Sinal rejeitado: confiança baixa ({signal.confidence:.2f} < {min_confidence})")
            return False
        
        # Validação de volatilidade
        volatility = indicators.get('volatility', 0)
        if volatility > 5.0:  # Volatilidade muito alta
            logger.warning(f"Sinal rejeitado: volatilidade muito alta ({volatility:.1f}%)")
            return False
        
        # Validação de RSI extremo
        rsi = indicators.get('rsi', 50)
        if signal.action == 'long' and rsi > 80:
            logger.warning(f"Sinal LONG rejeitado: RSI muito alto ({rsi:.1f})")
            return False
        elif signal.action == 'short' and rsi < 20:
            logger.warning(f"Sinal SHORT rejeitado: RSI muito baixo ({rsi:.1f})")
            return False
        
        return True
    
    def update_statistics(self, trade: Dict[str, Any]):
        """Atualiza estatísticas com novo trade"""
        self._reset_daily_stats_if_needed()
        
        pnl = trade.get('pnl', 0)
        
        # Atualiza contadores
        self.daily_trade_count += 1
        self.daily_pnl += pnl
        self.statistics['daily_trades'] = self.daily_trade_count
        self.statistics['daily_loss'] = min(0, self.daily_pnl)
        self.statistics['total_trades'] += 1
        self.statistics['total_pnl'] += pnl
        
        # Melhor e pior trade
        if pnl > self.statistics['best_trade']:
            self.statistics['best_trade'] = pnl
        if pnl < self.statistics['worst_trade']:
            self.statistics['worst_trade'] = pnl
        
        # Win/Loss tracking
        if pnl > 0:
            self.statistics['wins'] += 1
            self.statistics['consecutive_losses'] = 0
        else:
            self.statistics['losses'] += 1
            self.statistics['consecutive_losses'] += 1
            
            # Atualiza max consecutive losses
            if self.statistics['consecutive_losses'] > self.statistics['max_consecutive_losses']:
                self.statistics['max_consecutive_losses'] = self.statistics['consecutive_losses']
        
        # Calcula win rate
        total = self.statistics['wins'] + self.statistics['losses']
        if total > 0:
            self.statistics['win_rate'] = (self.statistics['wins'] / total) * 100
        
        # Atualiza drawdown
        if pnl < 0:
            self.statistics['current_drawdown'] += abs(pnl)
            if self.statistics['current_drawdown'] > self.statistics['max_drawdown']:
                self.statistics['max_drawdown'] = self.statistics['current_drawdown']
        else:
            self.statistics['current_drawdown'] = max(0, self.statistics['current_drawdown'] - pnl)
        
        # Remove trailing stop se posição foi fechada
        symbol = trade.get('symbol')
        if symbol and symbol in self.trailing_stops and 'close' in trade.get('side', ''):
            del self.trailing_stops[symbol]
            logger.debug(f"Trailing stop removido para {symbol}")
        
        # Verifica kill switch
        self._check_kill_switch_conditions()
        
        logger.info(f"Estatísticas atualizadas: Trades hoje: {self.daily_trade_count}, PnL diário: ${self.daily_pnl:.2f}")
    
    def _check_kill_switch_conditions(self):
        """Verifica se deve ativar kill switch"""
        if not self.kill_switch_enabled or self.kill_switch_triggered:
            return
        
        # Verifica perda total percentual
        initial_balance = self._get_config('advanced.paper_trading.initial_balance_usdt', 100.0)
        total_loss_pct = abs(self.statistics['total_pnl']) / initial_balance * 100
        
        if self.statistics['total_pnl'] < 0 and total_loss_pct >= self.kill_switch_loss_pct:
            self._trigger_kill_switch(f"total_loss_{total_loss_pct:.1f}%")
            return
        
        # Verifica perdas consecutivas
        if self.statistics['consecutive_losses'] >= self.kill_switch_consecutive:
            self._trigger_kill_switch(f"consecutive_losses_{self.statistics['consecutive_losses']}")
            return
        
        # Verifica drawdown máximo
        drawdown_pct = (self.statistics['current_drawdown'] / initial_balance) * 100
        if drawdown_pct >= self.max_drawdown_pct:
            self._trigger_kill_switch(f"max_drawdown_{drawdown_pct:.1f}%")
    
    def _trigger_kill_switch(self, reason: str):
        """Ativa kill switch"""
        self.kill_switch_triggered = True
        logger.error(f"🚨 KILL SWITCH ATIVADO: {reason}")
        logger.error("🛑 Trading suspenso por motivos de segurança!")
    
    def is_kill_switch_active(self) -> bool:
        """Verifica se kill switch está ativo"""
        return self.kill_switch_triggered
    
    def reset_kill_switch(self):
        """Reseta kill switch (apenas para uso manual)"""
        self.kill_switch_triggered = False
        logger.warning("Kill switch resetado manualmente")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas atuais"""
        self._reset_daily_stats_if_needed()
        return self.statistics.copy()
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Retorna resumo de risco atual"""
        return {
            'kill_switch_active': self.kill_switch_triggered,
            'daily_trades': f"{self.daily_trade_count}/{self.max_daily_trades}",
            'daily_pnl': self.daily_pnl,
            'consecutive_losses': self.statistics['consecutive_losses'],
            'current_drawdown_pct': (self.statistics['current_drawdown'] / 
                                   self._get_config('advanced.paper_trading.initial_balance_usdt', 100.0)) * 100,
            'can_trade': self.can_open_position()
        }