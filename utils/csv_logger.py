#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV Logger com Debug - Sistema de logging robusto para trades
"""

import csv
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class CSVLogger:
    """Logger CSV robusto que aceita objetos ou dicionários"""
    
    def __init__(self, filepath: str):
        """
        Inicializa o logger CSV
        
        Args:
            filepath: Caminho para o arquivo CSV
        """
        self.filepath = filepath
        self._ensure_directory()
        self._initialize_csv()
    
    def _ensure_directory(self):
        """Garante que o diretório existe"""
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
    
    def _initialize_csv(self):
        """Inicializa o arquivo CSV com cabeçalhos se não existir"""
        if not os.path.exists(self.filepath):
            self._create_csv_with_headers()
    
    def _create_csv_with_headers(self):
        """Cria arquivo CSV com cabeçalhos completos"""
        headers = [
            'timestamp', 'symbol', 'side', 'action', 'quantity',
            'entry_price', 'exit_price', 'predicted_take_profit', 'predicted_stop_loss',
            'current_price_at_entry', 'actual_exit_price', 'pnl', 'pnl_percent',
            'price_change_percent', 'signal_confidence', 'signal_reason',
            'exit_reason', 'target_hit', 'entry_time', 'exit_time',
            'time_in_position_minutes', 'trade_id', 'reason'
        ]
        
        try:
            with open(self.filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
            logger.info(f"Arquivo CSV criado: {self.filepath}")
        except Exception as e:
            logger.error(f"Erro ao criar arquivo CSV: {e}")
    
    def _debug_trade_structure(self, trade, trade_data: Dict[str, Any]):
        """Debug da estrutura de dados recebida"""
        logger.debug("=== DEBUG TRADE STRUCTURE ===")
        logger.debug(f"Trade type: {type(trade)}")
        
        if isinstance(trade, dict):
            logger.debug(f"Trade dict keys: {list(trade.keys())}")
            logger.debug(f"Trade dict content: {trade}")
        else:
            # É um objeto
            attrs = [attr for attr in dir(trade) if not attr.startswith('_')]
            logger.debug(f"Trade object attrs: {attrs}")
            
            # Tenta acessar atributos comuns
            for attr in ['symbol', 'side', 'action', 'quantity', 'entry_price', 'pnl']:
                try:
                    value = getattr(trade, attr, 'NOT_FOUND')
                    logger.debug(f"trade.{attr} = {value} (type: {type(value)})")
                except Exception as e:
                    logger.debug(f"Erro ao acessar trade.{attr}: {e}")
        
        logger.debug(f"Trade_data keys: {list(trade_data.keys())}")
        logger.debug("=== END DEBUG ===")
    
    def log_trade(self, trade):
        """Log básico - compatível com qualquer formato"""
        try:
            # Debug da estrutura (só em desenvolvimento)
            if logger.isEnabledFor(logging.DEBUG):
                trade_data_debug = {'trade': trade}
                self._debug_trade_structure(trade, trade_data_debug)
            
            trade_data = {
                'trade': trade,
                'predicted_tp': 0.0,
                'predicted_sl': 0.0,
                'current_price_at_entry': self._safe_get_value(trade, 'entry_price', 0.0),
                'signal_confidence': 0.0,
                'signal_reason': 'N/A'
            }
            
            self.log_trade_extended(trade_data)
            
        except Exception as e:
            logger.error(f"Erro no log_trade: {e}")
            # Log de emergência com dados básicos
            self._emergency_log(trade, e)
    
    def log_trade_extended(self, trade_data: Dict[str, Any]):
        """Log detalhado com informações extras"""
        try:
            trade = trade_data['trade']
            
            # Debug se necessário
            if logger.isEnabledFor(logging.DEBUG):
                self._debug_trade_structure(trade, trade_data)
            
            # Prepara dados para CSV
            csv_row = self._prepare_csv_row_safe(trade, trade_data)
            
            # Escreve no arquivo
            headers = [
                'timestamp', 'symbol', 'side', 'action', 'quantity',
                'entry_price', 'exit_price', 'predicted_take_profit', 'predicted_stop_loss',
                'current_price_at_entry', 'actual_exit_price', 'pnl', 'pnl_percent',
                'price_change_percent', 'signal_confidence', 'signal_reason',
                'exit_reason', 'target_hit', 'entry_time', 'exit_time',
                'time_in_position_minutes', 'trade_id', 'reason'
            ]
            
            with open(self.filepath, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writerow(csv_row)
            
            symbol = self._safe_get_value(trade, 'symbol', 'UNKNOWN')
            action = self._safe_get_value(trade, 'action', 'unknown')
            logger.debug(f"Trade logado no CSV: {symbol} - {action}")
            
        except Exception as e:
            logger.error(f"Erro ao logar trade no CSV: {e}")
            # Log de emergência
            self._emergency_log(trade_data.get('trade'), e)
    
    def _safe_get_value(self, obj, key: str, default=None):
        """Obtém valor de forma segura de objeto ou dicionário"""
        try:
            if isinstance(obj, dict):
                return obj.get(key, default)
            else:
                return getattr(obj, key, default)
        except Exception:
            return default
    
    def _safe_format(self, value, default='', format_func=str):
        """Formata valor de forma segura"""
        try:
            return format_func(value) if value is not None else default
        except:
            return default
    
    def _safe_float(self, value, decimals=4):
        """Converte para float com decimais específicos"""
        try:
            return f"{float(value):.{decimals}f}" if value is not None else "0.0"
        except:
            return "0.0"
    
    def _safe_datetime(self, dt):
        """Formata datetime de forma segura"""
        try:
            if isinstance(dt, datetime):
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(dt, str):
                return dt
            else:
                return ''
        except:
            return ''
    
    def _get_side_value(self, trade):
        """Obtém valor do side (pode ser enum, string, etc.)"""
        side = self._safe_get_value(trade, 'side')
        
        try:
            # Se tem atributo value (enum)
            if hasattr(side, 'value'):
                return str(side.value)
            # Se é string
            elif isinstance(side, str):
                return side
            # Converte para string
            else:
                return str(side) if side else 'unknown'
        except:
            return 'unknown'
    
    def _prepare_csv_row_safe(self, trade, trade_data: Dict[str, Any]) -> Dict[str, str]:
        """Prepara linha CSV de forma ultra-segura"""
        
        try:
            # Calcula métricas básicas
            entry_price = self._safe_get_value(trade, 'entry_price', 0)
            exit_price = self._safe_get_value(trade, 'exit_price', 0)
            quantity = self._safe_get_value(trade, 'quantity', 0)
            pnl = self._safe_get_value(trade, 'pnl', 0)
            
            # Variação percentual
            price_change_percent = 0.0
            if entry_price and exit_price and entry_price > 0:
                price_change_percent = ((exit_price - entry_price) / entry_price) * 100
            
            # PnL percentual
            pnl_percent = 0.0
            if pnl and entry_price and quantity and (entry_price * quantity) > 0:
                pnl_percent = (pnl / (entry_price * quantity)) * 100
            
            # Tempo em posição
            time_in_position = 0
            entry_time = self._safe_get_value(trade, 'entry_time')
            exit_time = self._safe_get_value(trade, 'exit_time')
            if entry_time and exit_time:
                try:
                    if isinstance(entry_time, datetime) and isinstance(exit_time, datetime):
                        time_diff = exit_time - entry_time
                        time_in_position = round(time_diff.total_seconds() / 60, 2)
                except:
                    pass
            
            # Monta linha
            row = {
                'timestamp': self._safe_datetime(datetime.now()),
                'symbol': self._safe_format(self._safe_get_value(trade, 'symbol', 'UNKNOWN')),
                'side': self._safe_format(self._get_side_value(trade)),
                'action': self._safe_format(self._safe_get_value(trade, 'action', 'unknown')),
                'quantity': self._safe_float(quantity),
                'entry_price': self._safe_float(entry_price),
                'exit_price': self._safe_float(exit_price),
                'predicted_take_profit': self._safe_float(trade_data.get('predicted_tp', 0)),
                'predicted_stop_loss': self._safe_float(trade_data.get('predicted_sl', 0)),
                'current_price_at_entry': self._safe_float(trade_data.get('current_price_at_entry', entry_price)),
                'actual_exit_price': self._safe_float(trade_data.get('actual_exit_price', exit_price)),
                'pnl': self._safe_float(pnl, 2),
                'pnl_percent': self._safe_float(pnl_percent, 2),
                'price_change_percent': self._safe_float(price_change_percent, 2),
                'signal_confidence': self._safe_float(trade_data.get('signal_confidence', 0), 2),
                'signal_reason': self._safe_format(trade_data.get('signal_reason', 'N/A')),
                'exit_reason': self._safe_format(trade_data.get('exit_reason', 'N/A')),
                'target_hit': self._safe_format(trade_data.get('target_hit', 'UNKNOWN')),
                'entry_time': self._safe_datetime(entry_time),
                'exit_time': self._safe_datetime(exit_time),
                'time_in_position_minutes': self._safe_float(time_in_position, 1),
                'trade_id': self._safe_format(self._safe_get_value(trade, 'id', '')),
                'reason': self._safe_format(self._safe_get_value(trade, 'reason', ''))
            }
            
            return row
            
        except Exception as e:
            logger.error(f"Erro ao preparar CSV row: {e}")
            # Row de emergência com dados mínimos
            return self._emergency_csv_row(trade, trade_data)
    
    def _emergency_csv_row(self, trade, trade_data: Dict[str, Any]) -> Dict[str, str]:
        """Cria row de emergência com dados mínimos"""
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': str(trade).get('symbol', 'ERROR') if isinstance(trade, dict) else 'ERROR',
            'side': 'unknown',
            'action': 'unknown',
            'quantity': '0.0',
            'entry_price': '0.0',
            'exit_price': '0.0',
            'predicted_take_profit': '0.0',
            'predicted_stop_loss': '0.0',
            'current_price_at_entry': '0.0',
            'actual_exit_price': '0.0',
            'pnl': '0.0',
            'pnl_percent': '0.0',
            'price_change_percent': '0.0',
            'signal_confidence': '0.0',
            'signal_reason': 'ERROR',
            'exit_reason': 'N/A',
            'target_hit': 'ERROR',
            'entry_time': '',
            'exit_time': '',
            'time_in_position_minutes': '0.0',
            'trade_id': 'ERROR',
            'reason': 'LOG_ERROR'
        }
    
    def _emergency_log(self, trade, error):
        """Log de emergência quando há erro"""
        try:
            emergency_file = self.filepath.replace('.csv', '_emergency.log')
            with open(emergency_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{datetime.now()}: ERRO no log CSV\n")
                f.write(f"Erro: {error}\n")
                f.write(f"Trade type: {type(trade)}\n")
                f.write(f"Trade data: {str(trade)[:500]}\n")
                f.write("-" * 50 + "\n")
            logger.warning(f"Log de emergência criado: {emergency_file}")
        except Exception as e2:
            logger.error(f"Falha até no log de emergência: {e2}")
    
    def get_trade_summary(self, days: int = 7) -> Dict[str, Any]:
        """Retorna resumo dos trades"""
        if not os.path.exists(self.filepath):
            return {}
        
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            trades = []
            with open(self.filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    try:
                        trade_date = datetime.strptime(row.get('timestamp', ''), '%Y-%m-%d %H:%M:%S')
                        if trade_date >= cutoff_date:
                            trades.append(row)
                    except:
                        continue
            
            if not trades:
                return {'total_trades': 0, 'message': 'Nenhum trade no período'}
            
            total_trades = len(trades)
            winning_trades = len([t for t in trades if float(t.get('pnl', 0)) > 0])
            total_pnl = sum(float(t.get('pnl', 0)) for t in trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                'period_days': days,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate': round(win_rate, 1),
                'total_pnl': round(total_pnl, 2),
                'average_pnl': round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
                'best_trade': round(max((float(t.get('pnl', 0)) for t in trades), default=0), 2),
                'worst_trade': round(min((float(t.get('pnl', 0)) for t in trades), default=0), 2)
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            return {'error': str(e)}

# Função utilitária para testar o logger
def test_csv_logger():
    """Função para testar o CSVLogger com diferentes formatos de dados"""
    
    logger.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    csv_logger = CSVLogger("test_trades.csv")
    
    # Teste 1: Dicionário simples
    print("=== TESTE 1: Dicionário simples ===")
    trade_dict = {
        'symbol': 'BTCUSDT',
        'side': 'long',
        'action': 'open',
        'quantity': 0.1,
        'entry_price': 45000.0,
        'pnl': 0.0
    }
    
    csv_logger.log_trade(trade_dict)
    print("Teste 1 concluído\n")
    
    # Teste 2: Dicionário com dados estendidos
    print("=== TESTE 2: Dicionário com dados estendidos ===")
    trade_data_extended = {
        'trade': trade_dict,
        'predicted_tp': 46000.0,
        'predicted_sl': 44000.0,
        'current_price_at_entry': 45000.0,
        'signal_confidence': 85.5,
        'signal_reason': 'RSI_OVERSOLD'
    }
    
    csv_logger.log_trade_extended(trade_data_extended)
    print("Teste 2 concluído\n")
    
    # Teste 3: Objeto simulado
    print("=== TESTE 3: Objeto simulado ===")
    class MockTrade:
        def __init__(self):
            self.symbol = 'ETHUSDT'
            self.side = MockSide()
            self.action = 'close'
            self.quantity = 0.5
            self.entry_price = 3000.0
            self.exit_price = 3100.0
            self.pnl = 50.0
            self.entry_time = datetime.now()
            self.exit_time = datetime.now()
    
    class MockSide:
        def __init__(self):
            self.value = 'long'
    
    mock_trade = MockTrade()
    csv_logger.log_trade(mock_trade)
    print("Teste 3 concluído\n")
    
    # Teste 4: Dados problemáticos
    print("=== TESTE 4: Dados problemáticos ===")
    problematic_trade = {
        'symbol': None,
        'side': 12345,  # Tipo inválido
        'action': '',
        'quantity': 'invalid',  # String em campo numérico
        'entry_price': None,
    }
    
    csv_logger.log_trade(problematic_trade)
    print("Teste 4 concluído\n")
    
    print("=== TODOS OS TESTES CONCLUÍDOS ===")
    print("Verifique o arquivo test_trades.csv")

if __name__ == "__main__":
    test_csv_logger()