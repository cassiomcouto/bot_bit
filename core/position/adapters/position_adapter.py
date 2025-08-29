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

# Adicione estes métodos ao arquivo core/managers/position_manager.py

def should_close_by_timing(self, symbol: str, current_price: float) -> tuple:
    """
    Verifica se a posição deve ser fechada baseado em critérios de tempo
    
    Args:
        symbol: Símbolo da posição a verificar
        current_price: Preço atual do ativo
        
    Returns:
        tuple: (should_close: bool, reason: str)
    """
    try:
        # Verifica se há posição para o símbolo
        position = self.get_position(symbol)
        if not position:
            return False, f"Nenhuma posição ativa encontrada para {symbol}"
            
        # Verifica se posição está realmente aberta
        status = getattr(position, 'status', position.get('status', 'open'))
        if status in ['closed', 'cancelled', 'filled']:
            return False, f"Posição {symbol} não está ativa (status: {status})"
            
        # === CÁLCULOS DE TEMPO ===
        from datetime import datetime, timedelta
        current_time = datetime.now()
        
        # Obtém tempo de abertura (tenta várias possibilidades)
        open_time = None
        time_fields = ['open_time', 'entry_time', 'timestamp', 'created_at', 'start_time']
        
        for field in time_fields:
            if isinstance(position, dict):
                open_time = position.get(field)
            else:
                open_time = getattr(position, field, None)
            if open_time is not None:
                break
                
        if open_time is None:
            # Se não tem tempo de abertura, assume posição nova (não fecha por tempo)
            logger.warning(f"Posição {symbol} sem timestamp de abertura")
            return False, "Posição sem timestamp de abertura"
            
        # Converte string para datetime se necessário
        if isinstance(open_time, str):
            try:
                # Tenta diferentes formatos
                formats = [
                    '%Y-%m-%d %H:%M:%S.%f',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S'
                ]
                
                parsed = False
                for fmt in formats:
                    try:
                        open_time = datetime.strptime(open_time, fmt)
                        parsed = True
                        break
                    except ValueError:
                        continue
                        
                if not parsed:
                    # Fallback: ISO format
                    open_time = datetime.fromisoformat(open_time.replace('Z', '+00:00').replace('+00:00', ''))
                    
            except Exception as e:
                logger.error(f"Erro ao converter timestamp {open_time}: {e}")
                return False, f"Erro no timestamp: {e}"
                
        # Calcula idade da posição
        position_age = current_time - open_time
        age_hours = position_age.total_seconds() / 3600
        
        # === CÁLCULOS DE PNL ===
        if isinstance(position, dict):
            position_pnl = position.get('pnl', None)
            entry_price = position.get('entry_price', position.get('price', current_price))
            size = position.get('quantity', position.get('size', 0))
            side = position.get('side', 'long')
        else:
            position_pnl = getattr(position, 'pnl', None)
            entry_price = getattr(position, 'entry_price', getattr(position, 'price', current_price))
            size = getattr(position, 'quantity', getattr(position, 'size', 0))
            side = getattr(position, 'side', 'long')
        
        # Se PnL não está disponível, calcula aproximadamente
        if position_pnl is None or position_pnl == 0:
            try:
                if str(side).lower() in ['long', 'buy']:
                    position_pnl = (current_price - entry_price) * size
                else:  # short/sell
                    position_pnl = (entry_price - current_price) * size
            except (TypeError, ValueError):
                position_pnl = 0
                
        # === CRITÉRIOS DE FECHAMENTO ===
        
        # 1. POSIÇÃO MUITO ANTIGA (Máximo configurável)
        max_position_hours = self._get_config('strategy.max_position_hold_seconds', 7200) / 3600  # Converte para horas
        if age_hours > max_position_hours:
            reason = f"Posição muito antiga: {age_hours:.1f}h (máx: {max_position_hours:.1f}h)"
            logger.info(f"[TIMING] {symbol}: {reason}")
            return True, reason
            
        # 2. PREJUÍZO PROLONGADO (4+ horas no vermelho)
        max_loss_hours = self._get_config('risk_management.max_loss_hold_hours', 4)
        if position_pnl < 0 and age_hours > max_loss_hours:
            try:
                loss_value = abs(position_pnl)
                position_value = entry_price * size if size > 0 else 100  # fallback
                loss_percentage = (loss_value / position_value) * 100
                
                # Se prejuízo significativo (>2%) e posição velha
                if loss_percentage > 2.0:
                    reason = f"Prejuízo prolongado: -{loss_percentage:.1f}% há {age_hours:.1f}h"
                    logger.info(f"[TIMING] {symbol}: {reason}")
                    return True, reason
                    
            except (TypeError, ValueError, ZeroDivisionError):
                # Se não conseguiu calcular %, usa valor absoluto
                if abs(position_pnl) > 10:  # Prejuízo > $10
                    reason = f"Prejuízo prolongado: ${position_pnl:.2f} há {age_hours:.1f}h"
                    logger.info(f"[TIMING] {symbol}: {reason}")
                    return True, reason
                    
        # 3. LUCRO PEQUENO PROLONGADO (12+ horas com lucro baixo)
        max_profit_hours = self._get_config('risk_management.max_small_profit_hours', 12)
        if position_pnl > 0 and age_hours > max_profit_hours:
            try:
                profit_value = position_pnl
                position_value = entry_price * size if size > 0 else 100
                profit_percentage = (profit_value / position_value) * 100
                
                # Se lucro muito pequeno (<0.5%) e posição muito velha
                if profit_percentage < 0.5:
                    reason = f"Lucro pequeno prolongado: +{profit_percentage:.1f}% há {age_hours:.1f}h"
                    logger.info(f"[TIMING] {symbol}: {reason}")
                    return True, reason
                    
            except (TypeError, ValueError, ZeroDivisionError):
                # Fallback por valor absoluto
                if position_pnl < 3:  # Lucro < $3
                    reason = f"Lucro pequeno prolongado: +${position_pnl:.2f} há {age_hours:.1f}h"
                    logger.info(f"[TIMING] {symbol}: {reason}")
                    return True, reason
        
        # 4. FINAL DE SEMANA (opcional - descomente se necessário)
        weekend_close = self._get_config('strategy.close_on_weekend', False)
        if weekend_close and current_time.weekday() >= 5:  # Sábado=5, Domingo=6
            reason = f"Final de semana (dia {current_time.weekday()})"
            return True, reason
        
        # Nenhum critério atendido
        reason = f"OK: {age_hours:.1f}h, PnL: ${position_pnl:.2f}"
        logger.debug(f"[TIMING] {symbol}: {reason}")
        return False, reason
        
    except Exception as e:
        error_msg = f"Erro em should_close_by_timing para {symbol}: {e}"
        logger.error(error_msg)
        return False, error_msg

    def check_take_profit_conditions(self, symbol: str, current_price: float) -> tuple:
        """
        Verifica condições de take profit (parcial ou total)
        
        Args:
            symbol: Símbolo da posição
            current_price: Preço atual
            
        Returns:
            tuple: (should_take: bool, reason: str, percentage: float)
                percentage = 1.0 para take profit total, < 1.0 para parcial
        """
        try:
            position = self.get_position(symbol)
            if not position:
                return False, "Sem posição", 0.0
            
            # Obtém dados da posição
            if isinstance(position, dict):
                entry_price = position.get('entry_price', position.get('price', current_price))
                side = position.get('side', 'long')
                partial_taken = position.get('partial_taken', False)
            else:
                entry_price = getattr(position, 'entry_price', getattr(position, 'price', current_price))
                side = getattr(position, 'side', 'long')
                partial_taken = getattr(position, 'partial_taken', False)
            
            # Calcula PnL percentual atual
            if str(side).lower() in ['long', 'buy']:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            # Configurações de take profit
            full_tp_pct = self._get_config('risk_management.take_profit.percentage', 3.0)
            partial_tp_pct = self._get_config('risk_management.take_profit.partial_percentage', 1.5)
            partial_amount = self._get_config('risk_management.take_profit.partial_amount_pct', 0.5)
            
            # Take profit total
            if pnl_pct >= full_tp_pct:
                return True, f"Take profit total: +{pnl_pct:.2f}%", 1.0
            
            # Take profit parcial (se ainda não foi feito)
            if not partial_taken and pnl_pct >= partial_tp_pct:
                return True, f"Take profit parcial: +{pnl_pct:.2f}%", partial_amount
            
            return False, f"PnL insuficiente: {pnl_pct:.2f}%", 0.0
            
        except Exception as e:
            error_msg = f"Erro ao verificar take profit para {symbol}: {e}"
            logger.error(error_msg)
            return False, error_msg, 0.0

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


    def has_position(self, symbol: str) -> bool:
        """Proxy para has_position"""
        return self.position_manager.has_position(symbol)
    
    def get_position(self, symbol: str):
        """Proxy para get_position"""
        return self.position_manager.get_position(symbol)
    
    def can_open_position(self, symbol: str) -> bool:
        """Proxy para can_open_position"""
        return self.position_manager.can_open_position(symbol)
    
    def calculate_position_size(self, symbol: str, price: float, side: str, confidence: float = 1.0) -> float:
        """Proxy para calculate_position_size"""
        return self.position_manager.calculate_position_size(symbol, price, side, confidence)
    
    def set_balance(self, balance: float):
        """Proxy para set_balance"""
        return self.position_manager.set_balance(balance)
    
    def get_balance(self) -> float:
        """Proxy para get_balance"""  
        return self.position_manager.get_balance()
    
    def print_positions(self):
        """Proxy para print_positions"""
        return self.position_manager.print_positions()
    
    def sync_positions(self, positions):
        """Proxy para sync_positions"""
        return self.position_manager.sync_positions(positions)
    
    def cancel_all_orders(self):
        """Proxy para cancel_all_orders"""
        return self.position_manager.cancel_all_orders()
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