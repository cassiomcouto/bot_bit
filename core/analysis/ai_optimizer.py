#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Análise IA para Otimização de Configuração
Analisa logs de performance e sugere ajustes automáticos
"""

import os
import json
import yaml
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import threading
import time

logger = logging.getLogger(__name__)

class AIConfigOptimizer:
    """Sistema de análise IA para otimização automática da configuração"""
    
    def __init__(self, config_path: str = "config/futures_config.yaml", 
                 logs_path: str = "logs/", snapshots_path: str = "config/snapshots/"):
        self.config_path = config_path
        self.logs_path = logs_path
        self.snapshots_path = snapshots_path
        self.running = False
        self.analysis_thread = None
        
        # Cria diretório de snapshots se não existir
        os.makedirs(self.snapshots_path, exist_ok=True)
        
        # Configurações de análise
        self.analysis_interval_hours = 1
        self.min_trades_for_analysis = 5
        self.performance_window_hours = 24
        
        logger.info(f"AI Config Optimizer inicializado")
        logger.info(f"Snapshots serão salvos em: {self.snapshots_path}")
    
    def start_monitoring(self):
        """Inicia monitoramento contínuo"""
        if self.running:
            logger.warning("Monitoramento já está ativo")
            return
        
        self.running = True
        self.analysis_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.analysis_thread.start()
        logger.info("Monitoramento IA iniciado - Análise a cada hora")
    
    def stop_monitoring(self):
        """Para monitoramento"""
        self.running = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)
        logger.info("Monitoramento IA parado")
    
    def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        while self.running:
            try:
                # Aguarda uma hora
                for _ in range(3600):  # 3600 segundos = 1 hora
                    if not self.running:
                        return
                    time.sleep(1)
                
                # Executa análise
                self.analyze_and_optimize()
                
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(300)  # Aguarda 5 minutos em caso de erro
    
    def analyze_and_optimize(self):
        """Executa análise completa e gera snapshot otimizado"""
        try:
            logger.info("Iniciando análise IA para otimização...")
            
            # Coleta dados de performance
            performance_data = self._collect_performance_data()
            
            if not performance_data or len(performance_data.get('trades', [])) < self.min_trades_for_analysis:
                logger.info(f"Dados insuficientes para análise (mínimo: {self.min_trades_for_analysis} trades)")
                return
            
            # Carrega configuração atual
            current_config = self._load_current_config()
            
            # Executa análise IA
            analysis_results = self._perform_ai_analysis(performance_data, current_config)
            
            # Gera configuração otimizada
            optimized_config = self._generate_optimized_config(current_config, analysis_results)
            
            # Salva snapshot
            self._save_config_snapshot(optimized_config, analysis_results)
            
            logger.info("Análise IA concluída - Snapshot salvo")
            
        except Exception as e:
            logger.error(f"Erro na análise IA: {e}")
    
    def _collect_performance_data(self) -> Dict[str, Any]:
        """Coleta dados de performance dos logs"""
        performance_data = {
            'trades': [],
            'statistics': {},
            'market_conditions': {},
            'time_range': {}
        }
        
        try:
            # Lê arquivo de trades CSV
            trades_file = os.path.join(self.logs_path, "trades.csv")
            if not os.path.exists(trades_file):
                logger.warning(f"Arquivo de trades não encontrado: {trades_file}")
                return performance_data
            
            # Carrega trades das últimas 24h
            cutoff_time = datetime.now() - timedelta(hours=self.performance_window_hours)
            
            df = pd.read_csv(trades_file)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                recent_trades = df[df['timestamp'] >= cutoff_time]
                
                # Converte para lista de dicionários
                performance_data['trades'] = recent_trades.to_dict('records')
                
                # Calcula estatísticas
                performance_data['statistics'] = self._calculate_statistics(recent_trades)
                
                # Define período de análise
                performance_data['time_range'] = {
                    'start': cutoff_time.isoformat(),
                    'end': datetime.now().isoformat(),
                    'hours': self.performance_window_hours
                }
            
            logger.info(f"Coletados {len(performance_data['trades'])} trades para análise")
            
        except Exception as e:
            logger.error(f"Erro ao coletar dados de performance: {e}")
        
        return performance_data
    
    def _calculate_statistics(self, trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Calcula estatísticas detalhadas dos trades"""
        if trades_df.empty:
            return {}
        
        stats = {}
        
        # Estatísticas básicas
        stats['total_trades'] = len(trades_df)
        stats['profitable_trades'] = len(trades_df[trades_df.get('pnl', 0) > 0])
        stats['losing_trades'] = len(trades_df[trades_df.get('pnl', 0) < 0])
        
        # Win rate
        stats['win_rate'] = (stats['profitable_trades'] / stats['total_trades']) * 100 if stats['total_trades'] > 0 else 0
        
        # PnL
        pnl_series = trades_df.get('pnl', pd.Series([0]))
        stats['total_pnl'] = float(pnl_series.sum())
        stats['average_win'] = float(pnl_series[pnl_series > 0].mean()) if len(pnl_series[pnl_series > 0]) > 0 else 0
        stats['average_loss'] = float(pnl_series[pnl_series < 0].mean()) if len(pnl_series[pnl_series < 0]) > 0 else 0
        stats['largest_win'] = float(pnl_series.max())
        stats['largest_loss'] = float(pnl_series.min())
        
        # Risk-reward ratio
        if stats['average_loss'] != 0:
            stats['risk_reward_ratio'] = abs(stats['average_win'] / stats['average_loss'])
        else:
            stats['risk_reward_ratio'] = 0
        
        # Análise por direção
        long_trades = trades_df[trades_df.get('side', '').str.contains('long', case=False, na=False)]
        short_trades = trades_df[trades_df.get('side', '').str.contains('short', case=False, na=False)]
        
        stats['long_performance'] = {
            'count': len(long_trades),
            'win_rate': (len(long_trades[long_trades.get('pnl', 0) > 0]) / len(long_trades)) * 100 if len(long_trades) > 0 else 0,
            'total_pnl': float(long_trades.get('pnl', pd.Series([0])).sum())
        }
        
        stats['short_performance'] = {
            'count': len(short_trades),
            'win_rate': (len(short_trades[short_trades.get('pnl', 0) > 0]) / len(short_trades)) * 100 if len(short_trades) > 0 else 0,
            'total_pnl': float(short_trades.get('pnl', pd.Series([0])).sum())
        }
        
        # Análise temporal
        if 'timestamp' in trades_df.columns:
            trades_df['hour'] = trades_df['timestamp'].dt.hour
            hourly_performance = trades_df.groupby('hour')['pnl'].agg(['count', 'sum', 'mean']).to_dict('index')
            stats['hourly_performance'] = hourly_performance
        
        return stats
    
    def _load_current_config(self) -> Dict[str, Any]:
        """Carrega configuração atual"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            return {}
    
    def _perform_ai_analysis(self, performance_data: Dict[str, Any], 
                           current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Executa análise IA dos dados de performance"""
        analysis = {
            'performance_score': 0.0,
            'issues_detected': [],
            'recommendations': [],
            'config_changes': {},
            'confidence_level': 0.0
        }
        
        stats = performance_data.get('statistics', {})
        trades = performance_data.get('trades', [])
        
        # Análise de performance geral
        win_rate = stats.get('win_rate', 0)
        total_pnl = stats.get('total_pnl', 0)
        risk_reward = stats.get('risk_reward_ratio', 0)
        
        # Score de performance (0-100)
        performance_score = 0
        
        # Componente win rate (0-40 pontos)
        if win_rate >= 60:
            performance_score += 40
        elif win_rate >= 50:
            performance_score += 30
        elif win_rate >= 40:
            performance_score += 20
        else:
            performance_score += 10
        
        # Componente PnL (0-30 pontos)
        if total_pnl > 0:
            performance_score += min(30, total_pnl * 2)  # 2 pontos por dólar de lucro
        
        # Componente risk-reward (0-30 pontos)
        if risk_reward >= 2.0:
            performance_score += 30
        elif risk_reward >= 1.5:
            performance_score += 20
        elif risk_reward >= 1.0:
            performance_score += 10
        
        analysis['performance_score'] = min(100, performance_score)
        
        # Detecção de problemas e recomendações
        self._analyze_win_rate(analysis, stats, current_config)
        self._analyze_risk_management(analysis, stats, current_config)
        self._analyze_position_sizing(analysis, trades, current_config)
        self._analyze_timing_settings(analysis, trades, current_config)
        self._analyze_technical_indicators(analysis, stats, current_config)
        
        # Nível de confiança baseado no número de trades
        total_trades = stats.get('total_trades', 0)
        if total_trades >= 50:
            analysis['confidence_level'] = 0.9
        elif total_trades >= 25:
            analysis['confidence_level'] = 0.7
        elif total_trades >= 10:
            analysis['confidence_level'] = 0.5
        else:
            analysis['confidence_level'] = 0.3
        
        return analysis
    
    def _analyze_win_rate(self, analysis: Dict, stats: Dict, config: Dict):
        """Analisa win rate e sugere ajustes"""
        win_rate = stats.get('win_rate', 0)
        
        if win_rate < 40:
            analysis['issues_detected'].append(f"Win rate baixo: {win_rate:.1f}%")
            analysis['recommendations'].append("Aumentar critérios de entrada - scores mínimos mais altos")
            
            # Sugere ajustes mais conservadores
            analysis['config_changes']['ai_futures.scoring.min_score_long'] = 8.0
            analysis['config_changes']['ai_futures.scoring.min_score_short'] = 8.0
            analysis['config_changes']['ai_futures.filters.min_confidence'] = 0.75
            
        elif win_rate > 80:
            analysis['issues_detected'].append(f"Win rate muito alto: {win_rate:.1f}% - poucos trades")
            analysis['recommendations'].append("Relaxar critérios de entrada para mais oportunidades")
            
            # Sugere critérios menos restritivos
            analysis['config_changes']['ai_futures.scoring.min_score_long'] = 5.0
            analysis['config_changes']['ai_futures.scoring.min_score_short'] = 5.0
            analysis['config_changes']['ai_futures.filters.min_confidence'] = 0.60
    
    def _analyze_risk_management(self, analysis: Dict, stats: Dict, config: Dict):
        """Analisa gestão de risco"""
        avg_loss = abs(stats.get('average_loss', 0))
        avg_win = stats.get('average_win', 0)
        risk_reward = stats.get('risk_reward_ratio', 0)
        
        # Stop loss muito apertado?
        if avg_loss < 1.0:  # Perdas muito pequenas
            analysis['issues_detected'].append("Stop loss possivelmente muito apertado")
            analysis['recommendations'].append("Considerar aumentar stop loss para 2.5-3.0%")
            analysis['config_changes']['risk_management.stop_loss.percentage'] = 2.5
        
        # Risk-reward inadequado?
        if risk_reward < 1.0:
            analysis['issues_detected'].append(f"Risk-reward desfavorável: {risk_reward:.2f}")
            analysis['recommendations'].append("Ajustar take profit ou stop loss")
            
            if avg_win < avg_loss:
                # Aumentar take profit
                current_tp = config.get('risk_management', {}).get('take_profit', {}).get('percentage', 3.0)
                analysis['config_changes']['risk_management.take_profit.percentage'] = current_tp + 1.0
    
    def _analyze_position_sizing(self, analysis: Dict, trades: List, config: Dict):
        """Analisa tamanho de posições"""
        if not trades:
            return
        
        # Analisa se está arriscando muito por trade
        total_trades = len(trades)
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        
        if len(losing_trades) > 0:
            avg_loss_pct = sum(abs(t.get('pnl', 0)) for t in losing_trades) / len(losing_trades)
            
            # Se perdas médias > 3% do saldo, reduzir risk per trade
            if avg_loss_pct > 3.0:
                analysis['issues_detected'].append(f"Risco por trade alto: ${avg_loss_pct:.2f}")
                analysis['recommendations'].append("Reduzir risk_per_trade_pct")
                
                current_risk = config.get('trading', {}).get('trading_pairs', [{}])[0].get('risk_per_trade_pct', 2.0)
                analysis['config_changes']['trading.trading_pairs.0.risk_per_trade_pct'] = max(1.0, current_risk - 0.5)
    
    def _analyze_timing_settings(self, analysis: Dict, trades: List, config: Dict):
        """Analisa configurações de timing"""
        if not trades:
            return
        
        # Verifica se trades estão sendo fechados por timeout muito frequentemente
        timeout_closes = [t for t in trades if 'timeout' in str(t.get('reason', '')).lower() or 'tempo' in str(t.get('reason', '')).lower()]
        
        if len(timeout_closes) / len(trades) > 0.3:  # Mais de 30% por timeout
            analysis['issues_detected'].append("Muitos fechamentos por timeout")
            analysis['recommendations'].append("Aumentar max_position_hold_seconds")
            
            current_max_hold = config.get('strategy', {}).get('max_position_hold_seconds', 7200)
            analysis['config_changes']['strategy.max_position_hold_seconds'] = min(14400, current_max_hold + 1800)  # +30min
    
    def _analyze_technical_indicators(self, analysis: Dict, stats: Dict, config: Dict):
        """Analisa eficácia dos indicadores técnicos"""
        long_perf = stats.get('long_performance', {})
        short_perf = stats.get('short_performance', {})
        
        # Se uma direção está performando muito melhor, ajustar
        long_wr = long_perf.get('win_rate', 50)
        short_wr = short_perf.get('win_rate', 50)
        
        if abs(long_wr - short_wr) > 20:  # Diferença > 20%
            if long_wr > short_wr:
                analysis['recommendations'].append("LONGs performam melhor - considerar desabilitar SHORTs temporariamente")
                analysis['config_changes']['ai_futures.signals.allow_short'] = False
            else:
                analysis['recommendations'].append("SHORTs performam melhor - considerar desabilitar LONGs temporariamente")
                analysis['config_changes']['ai_futures.signals.allow_long'] = False
    
    def _generate_optimized_config(self, current_config: Dict, analysis: Dict) -> Dict:
        """Gera configuração otimizada baseada na análise"""
        optimized_config = current_config.copy()
        
        # Aplica mudanças sugeridas
        for key_path, value in analysis.get('config_changes', {}).items():
            self._set_nested_config(optimized_config, key_path, value)
        
        # Adiciona metadados da otimização
        if 'metadata' not in optimized_config:
            optimized_config['metadata'] = {}
        
        optimized_config['metadata']['optimization'] = {
            'timestamp': datetime.now().isoformat(),
            'performance_score': analysis['performance_score'],
            'confidence_level': analysis['confidence_level'],
            'changes_applied': len(analysis.get('config_changes', {})),
            'issues_detected': len(analysis.get('issues_detected', [])),
            'ai_version': '1.0'
        }
        
        return optimized_config
    
    def _set_nested_config(self, config: Dict, key_path: str, value: Any):
        """Define valor em configuração aninhada"""
        keys = key_path.split('.')
        current = config
        
        # Navega até o penúltimo nível
        for key in keys[:-1]:
            if key.isdigit():  # Se é um índice de array
                key = int(key)
                if not isinstance(current, list) or len(current) <= key:
                    return  # Não pode definir
                current = current[key]
            else:
                if key not in current:
                    current[key] = {}
                current = current[key]
        
        # Define o valor final
        final_key = keys[-1]
        if final_key.isdigit():
            final_key = int(final_key)
        
        current[final_key] = value
    
    def _save_config_snapshot(self, optimized_config: Dict, analysis: Dict):
        """Salva snapshot da configuração otimizada"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"config_snapshot_{timestamp}.yaml"
        filepath = os.path.join(self.snapshots_path, filename)
        
        # Salva configuração
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(optimized_config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        # Salva análise separadamente
        analysis_filename = f"analysis_{timestamp}.json"
        analysis_filepath = os.path.join(self.snapshots_path, analysis_filename)
        
        with open(analysis_filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.info(f"Snapshot salvo: {filename}")
        logger.info(f"Análise salva: {analysis_filename}")
        
        # Log das principais mudanças
        changes = analysis.get('config_changes', {})
        if changes:
            logger.info("Principais otimizações sugeridas:")
            for key, value in changes.items():
                logger.info(f"  {key}: {value}")
    
    def get_latest_snapshot(self) -> Tuple[str, Dict]:
        """Retorna o snapshot mais recente"""
        try:
            snapshots = [f for f in os.listdir(self.snapshots_path) if f.startswith('config_snapshot_') and f.endswith('.yaml')]
            if not snapshots:
                return None, {}
            
            latest = sorted(snapshots)[-1]
            filepath = os.path.join(self.snapshots_path, latest)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            return latest, config
            
        except Exception as e:
            logger.error(f"Erro ao obter snapshot mais recente: {e}")
            return None, {}
    
    def apply_latest_snapshot(self) -> bool:
        """Aplica o snapshot mais recente à configuração principal"""
        try:
            snapshot_name, snapshot_config = self.get_latest_snapshot()
            if not snapshot_config:
                logger.warning("Nenhum snapshot encontrado")
                return False
            
            # Backup da configuração atual
            backup_path = f"{self.config_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(self.config_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            # Aplica snapshot
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(snapshot_config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logger.info(f"Snapshot {snapshot_name} aplicado com sucesso")
            logger.info(f"Backup salvo em: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao aplicar snapshot: {e}")
            return False