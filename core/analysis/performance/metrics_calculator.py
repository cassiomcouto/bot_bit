#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Cálculo de Métricas de Performance
Calcula métricas avançadas de performance para análise de trading
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Estrutura para armazenar métricas de performance"""
    
    # Métricas básicas
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Métricas de PnL
    total_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    
    # Métricas de risco-retorno
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Métricas avançadas
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    # Métricas de consistência
    win_streak: int = 0
    loss_streak: int = 0
    avg_trade_duration: float = 0.0
    recovery_factor: float = 0.0
    
    # Métricas por direção
    long_metrics: Optional[Dict] = None
    short_metrics: Optional[Dict] = None
    
    # Métricas temporais
    monthly_returns: Optional[Dict] = None
    daily_performance: Optional[Dict] = None
    
    # Metadados
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    analysis_timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return asdict(self)

class BaseMetricsCalculator(ABC):
    """Classe base para calculadores de métricas"""
    
    @abstractmethod
    def calculate(self, trades_data: pd.DataFrame) -> PerformanceMetrics:
        """Calcula métricas de performance"""
        pass

class ComprehensiveMetricsCalculator(BaseMetricsCalculator):
    """Calculador abrangente de métricas de performance"""
    
    def __init__(self, risk_free_rate: float = 0.02):
        """
        Args:
            risk_free_rate: Taxa livre de risco para cálculo do Sharpe ratio
        """
        self.risk_free_rate = risk_free_rate
        
    def calculate(self, trades_data: pd.DataFrame) -> PerformanceMetrics:
        """
        Calcula métricas abrangentes de performance
        
        Args:
            trades_data: DataFrame com dados dos trades
            
        Returns:
            PerformanceMetrics: Objeto com todas as métricas calculadas
        """
        if trades_data.empty:
            logger.warning("DataFrame de trades está vazio")
            return PerformanceMetrics()
        
        try:
            metrics = PerformanceMetrics()
            
            # Prepara dados
            df = self._prepare_data(trades_data)
            
            # Calcula métricas básicas
            self._calculate_basic_metrics(df, metrics)
            
            # Calcula métricas de PnL
            self._calculate_pnl_metrics(df, metrics)
            
            # Calcula métricas de risco-retorno
            self._calculate_risk_return_metrics(df, metrics)
            
            # Calcula métricas avançadas
            self._calculate_advanced_metrics(df, metrics)
            
            # Calcula métricas de consistência
            self._calculate_consistency_metrics(df, metrics)
            
            # Calcula métricas por direção
            self._calculate_directional_metrics(df, metrics)
            
            # Calcula métricas temporais
            self._calculate_temporal_metrics(df, metrics)
            
            # Define metadados
            self._set_metadata(df, metrics)
            
            logger.info(f"Métricas calculadas para {len(df)} trades")
            return metrics
            
        except Exception as e:
            logger.error(f"Erro ao calcular métricas: {e}")
            return PerformanceMetrics()
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara e valida os dados dos trades"""
        df = df.copy()
        
        # Colunas essenciais
        required_cols = ['pnl']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0
        
        # Converte timestamp se presente
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Remove trades com PnL inválido
        df = df.dropna(subset=['pnl'])
        
        # Adiciona colunas calculadas
        df['is_winner'] = df['pnl'] > 0
        df['is_loser'] = df['pnl'] < 0
        
        # Calcula retornos cumulativos
        df['cumulative_pnl'] = df['pnl'].cumsum()
        
        return df
    
    def _calculate_basic_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calcula métricas básicas"""
        metrics.total_trades = len(df)
        metrics.winning_trades = len(df[df['is_winner']])
        metrics.losing_trades = len(df[df['is_loser']])
        
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
    
    def _calculate_pnl_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calcula métricas de PnL"""
        pnl_series = df['pnl']
        
        metrics.total_pnl = float(pnl_series.sum())
        metrics.gross_profit = float(pnl_series[pnl_series > 0].sum())
        metrics.gross_loss = float(abs(pnl_series[pnl_series < 0].sum()))
        metrics.net_profit = metrics.total_pnl
    
    def _calculate_risk_return_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calcula métricas de risco-retorno"""
        winners = df[df['is_winner']]['pnl']
        losers = df[df['is_loser']]['pnl']
        
        # Médias
        metrics.average_win = float(winners.mean()) if len(winners) > 0 else 0.0
        metrics.average_loss = float(losers.mean()) if len(losers) > 0 else 0.0
        
        # Extremos
        metrics.largest_win = float(df['pnl'].max()) if len(df) > 0 else 0.0
        metrics.largest_loss = float(df['pnl'].min()) if len(df) > 0 else 0.0
        
        # Profit Factor
        if metrics.gross_loss > 0:
            metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
        else:
            metrics.profit_factor = float('inf') if metrics.gross_profit > 0 else 0.0
        
        # Expectancy
        if metrics.total_trades > 0:
            win_prob = metrics.winning_trades / metrics.total_trades
            lose_prob = metrics.losing_trades / metrics.total_trades
            metrics.expectancy = (win_prob * metrics.average_win) + (lose_prob * metrics.average_loss)
    
    def _calculate_advanced_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calcula métricas avançadas (Sharpe, Sortino, etc.)"""
        if len(df) < 2:
            return
        
        returns = df['pnl']
        cumulative = df['cumulative_pnl']
        
        # Sharpe Ratio
        if returns.std() != 0:
            daily_risk_free = self.risk_free_rate / 252  # Assumindo trading diário
            excess_returns = returns.mean() - daily_risk_free
            metrics.sharpe_ratio = float(excess_returns / returns.std())
        
        # Sortino Ratio
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0 and negative_returns.std() != 0:
            daily_risk_free = self.risk_free_rate / 252
            excess_returns = returns.mean() - daily_risk_free
            metrics.sortino_ratio = float(excess_returns / negative_returns.std())
        
        # Drawdown
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        metrics.max_drawdown = float(abs(drawdown.min()))
        
        # Duração do drawdown
        metrics.max_drawdown_duration = self._calculate_max_drawdown_duration(drawdown)
        
        # Calmar Ratio
        if metrics.max_drawdown > 0:
            annual_return = (metrics.total_pnl / len(df)) * 252  # Anualizado
            metrics.calmar_ratio = float(annual_return / metrics.max_drawdown)
    
    def _calculate_max_drawdown_duration(self, drawdown: pd.Series) -> int:
        """Calcula a duração máxima do drawdown"""
        is_drawdown = drawdown < 0
        groups = (is_drawdown != is_drawdown.shift()).cumsum()
        drawdown_periods = is_drawdown.groupby(groups).sum()
        return int(drawdown_periods.max()) if len(drawdown_periods) > 0 else 0
    
    def _calculate_consistency_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calcula métricas de consistência"""
        if len(df) == 0:
            return
        
        # Sequências de vitórias/derrotas
        streaks = self._calculate_streaks(df['is_winner'])
        metrics.win_streak = streaks['max_win_streak']
        metrics.loss_streak = streaks['max_loss_streak']
        
        # Duração média dos trades
        if 'duration_seconds' in df.columns:
            metrics.avg_trade_duration = float(df['duration_seconds'].mean())
        elif 'entry_time' in df.columns and 'exit_time' in df.columns:
            durations = pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])
            metrics.avg_trade_duration = float(durations.dt.total_seconds().mean())
        
        # Recovery Factor
        if metrics.max_drawdown > 0:
            metrics.recovery_factor = metrics.net_profit / metrics.max_drawdown
    
    def _calculate_streaks(self, wins: pd.Series) -> Dict[str, int]:
        """Calcula sequências máximas de vitórias e derrotas"""
        if len(wins) == 0:
            return {'max_win_streak': 0, 'max_loss_streak': 0}
        
        # Identifica mudanças de estado
        groups = (wins != wins.shift()).cumsum()
        streak_data = wins.groupby(groups).agg(['first', 'count'])
        
        # Separa vitórias e derrotas
        win_streaks = streak_data[streak_data['first'] == True]['count']
        loss_streaks = streak_data[streak_data['first'] == False]['count']
        
        return {
            'max_win_streak': int(win_streaks.max()) if len(win_streaks) > 0 else 0,
            'max_loss_streak': int(loss_streaks.max()) if len(loss_streaks) > 0 else 0
        }
    
    def _calculate_directional_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calcula métricas por direção (long/short)"""
        if 'side' not in df.columns:
            return
        
        # Identifica longs e shorts
        long_trades = df[df['side'].str.contains('long|buy', case=False, na=False)]
        short_trades = df[df['side'].str.contains('short|sell', case=False, na=False)]
        
        # Calcula métricas para longs
        if len(long_trades) > 0:
            long_calc = ComprehensiveMetricsCalculator(self.risk_free_rate)
            long_metrics_obj = long_calc.calculate(long_trades)
            metrics.long_metrics = long_metrics_obj.to_dict()
        
        # Calcula métricas para shorts
        if len(short_trades) > 0:
            short_calc = ComprehensiveMetricsCalculator(self.risk_free_rate)
            short_metrics_obj = short_calc.calculate(short_trades)
            metrics.short_metrics = short_metrics_obj.to_dict()
    
    def _calculate_temporal_metrics(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Calcula métricas temporais"""
        if 'timestamp' not in df.columns or df['timestamp'].isna().all():
            return
        
        df_with_time = df.dropna(subset=['timestamp']).copy()
        if len(df_with_time) == 0:
            return
        
        # Performance mensal
        df_with_time['month'] = df_with_time['timestamp'].dt.to_period('M')
        monthly_pnl = df_with_time.groupby('month')['pnl'].agg({
            'total_pnl': 'sum',
            'trades': 'count',
            'win_rate': lambda x: (x > 0).mean() * 100,
            'avg_pnl': 'mean'
        })
        
        metrics.monthly_returns = {
            str(month): {
                'total_pnl': float(data['total_pnl']),
                'trades': int(data['trades']),
                'win_rate': float(data['win_rate']),
                'avg_pnl': float(data['avg_pnl'])
            }
            for month, data in monthly_pnl.iterrows()
        }
        
        # Performance diária
        df_with_time['date'] = df_with_time['timestamp'].dt.date
        daily_pnl = df_with_time.groupby('date')['pnl'].agg({
            'total_pnl': 'sum',
            'trades': 'count'
        })
        
        # Estatísticas dos dias
        daily_stats = {
            'profitable_days': int((daily_pnl['total_pnl'] > 0).sum()),
            'losing_days': int((daily_pnl['total_pnl'] < 0).sum()),
            'breakeven_days': int((daily_pnl['total_pnl'] == 0).sum()),
            'best_day': float(daily_pnl['total_pnl'].max()) if len(daily_pnl) > 0 else 0.0,
            'worst_day': float(daily_pnl['total_pnl'].min()) if len(daily_pnl) > 0 else 0.0,
            'avg_daily_pnl': float(daily_pnl['total_pnl'].mean()) if len(daily_pnl) > 0 else 0.0
        }
        
        metrics.daily_performance = daily_stats
    
    def _set_metadata(self, df: pd.DataFrame, metrics: PerformanceMetrics):
        """Define metadados da análise"""
        if 'timestamp' in df.columns and not df['timestamp'].isna().all():
            timestamps = df['timestamp'].dropna()
            if len(timestamps) > 0:
                metrics.period_start = timestamps.min().isoformat()
                metrics.period_end = timestamps.max().isoformat()
        
        metrics.analysis_timestamp = datetime.now().isoformat()

class QuickMetricsCalculator(BaseMetricsCalculator):
    """Calculador rápido de métricas essenciais"""
    
    def calculate(self, trades_data: pd.DataFrame) -> PerformanceMetrics:
        """Calcula apenas métricas essenciais para análise rápida"""
        if trades_data.empty:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        df = trades_data.copy()
        
        # Métricas básicas
        metrics.total_trades = len(df)
        metrics.winning_trades = len(df[df['pnl'] > 0])
        metrics.losing_trades = len(df[df['pnl'] < 0])
        
        if metrics.total_trades > 0:
            metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
        
        # PnL
        metrics.total_pnl = float(df['pnl'].sum())
        metrics.average_win = float(df[df['pnl'] > 0]['pnl'].mean()) if metrics.winning_trades > 0 else 0.0
        metrics.average_loss = float(df[df['pnl'] < 0]['pnl'].mean()) if metrics.losing_trades > 0 else 0.0
        
        # Profit Factor
        gross_profit = df[df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
        
        if gross_loss > 0:
            metrics.profit_factor = gross_profit / gross_loss
        
        metrics.analysis_timestamp = datetime.now().isoformat()
        
        return metrics

class MetricsCalculatorFactory:
    """Factory para criar calculadores de métricas"""
    
    @staticmethod
    def create_calculator(calculator_type: str = "comprehensive", **kwargs) -> BaseMetricsCalculator:
        """
        Cria um calculador de métricas
        
        Args:
            calculator_type: Tipo do calculador ('comprehensive', 'quick')
            **kwargs: Argumentos específicos do calculador
            
        Returns:
            BaseMetricsCalculator: Instância do calculador
        """
        calculators = {
            'comprehensive': ComprehensiveMetricsCalculator,
            'quick': QuickMetricsCalculator
        }
        
        if calculator_type not in calculators:
            raise ValueError(f"Tipo de calculador desconhecido: {calculator_type}")
        
        return calculators[calculator_type](**kwargs)

def calculate_portfolio_metrics(trades_data: pd.DataFrame, 
                              calculator_type: str = "comprehensive",
                              **kwargs) -> PerformanceMetrics:
    """
    Função de conveniência para calcular métricas de performance
    
    Args:
        trades_data: DataFrame com dados dos trades
        calculator_type: Tipo do calculador a usar
        **kwargs: Argumentos adicionais para o calculador
        
    Returns:
        PerformanceMetrics: Métricas calculadas
    """
    calculator = MetricsCalculatorFactory.create_calculator(calculator_type, **kwargs)
    return calculator.calculate(trades_data)

def compare_periods(current_trades: pd.DataFrame, 
                   previous_trades: pd.DataFrame,
                   calculator_type: str = "comprehensive") -> Dict[str, Any]:
    """
    Compara métricas entre dois períodos
    
    Args:
        current_trades: Trades do período atual
        previous_trades: Trades do período anterior
        calculator_type: Tipo do calculador
        
    Returns:
        Dict com comparação das métricas
    """
    calculator = MetricsCalculatorFactory.create_calculator(calculator_type)
    
    current_metrics = calculator.calculate(current_trades)
    previous_metrics = calculator.calculate(previous_trades)
    
    comparison = {
        'current_period': current_metrics.to_dict(),
        'previous_period': previous_metrics.to_dict(),
        'improvements': {},
        'deteriorations': {}
    }
    
    # Métricas chave para comparação
    key_metrics = [
        'win_rate', 'total_pnl', 'profit_factor', 'sharpe_ratio', 
        'max_drawdown', 'expectancy', 'average_win', 'average_loss'
    ]
    
    for metric in key_metrics:
        current_val = getattr(current_metrics, metric)
        previous_val = getattr(previous_metrics, metric)
        
        if previous_val != 0:
            change_pct = ((current_val - previous_val) / abs(previous_val)) * 100
            
            if change_pct > 0:
                comparison['improvements'][metric] = {
                    'current': current_val,
                    'previous': previous_val,
                    'change_pct': change_pct
                }
            elif change_pct < 0:
                comparison['deteriorations'][metric] = {
                    'current': current_val,
                    'previous': previous_val,
                    'change_pct': change_pct
                }
    
    return comparison