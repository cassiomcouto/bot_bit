#!/usr/bin/env python3
"""
Script de Validação do Sistema de Trading
Identifica por que os trades não estão acontecendo
"""

import yaml
import logging
import os
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_config_restrictions(config_path):
    """Verifica configurações que podem estar impedindo trades"""
    print("VERIFICANDO CONFIGURACOES RESTRITIVAS...")
    print("-" * 50)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        issues = []
        warnings = []
        
        # Verifica AI futures config
        ai_config = config.get('ai_futures', {})
        if not ai_config.get('enabled', False):
            issues.append("ai_futures está DESABILITADO")
        
        # Scores mínimos
        scoring = ai_config.get('scoring', {})
        min_score_long = scoring.get('min_score_long', 0)
        min_score_short = scoring.get('min_score_short', 0)
        
        print(f"min_score_long: {min_score_long}")
        print(f"min_score_short: {min_score_short}")
        
        if min_score_long > 4.0:
            warnings.append(f"min_score_long MUITO ALTO: {min_score_long} (recomendado: 3.0-3.5)")
        if min_score_short > 4.0:
            warnings.append(f"min_score_short MUITO ALTO: {min_score_short} (recomendado: 3.0-3.5)")
        
        # Confiança mínima
        filters = ai_config.get('filters', {})
        min_confidence = filters.get('min_confidence', 0)
        print(f"min_confidence: {min_confidence}")
        
        if min_confidence > 0.6:
            warnings.append(f"min_confidence MUITO ALTO: {min_confidence} (recomendado: 0.50-0.55)")
        
        # Kill switch
        risk_config = config.get('risk_management', {})
        kill_switch = risk_config.get('kill_switch', {})
        consecutive_losses = kill_switch.get('consecutive_losses', 10)
        print(f"consecutive_losses: {consecutive_losses}")
        
        if consecutive_losses < 4:
            warnings.append(f"consecutive_losses MUITO BAIXO: {consecutive_losses} (recomendado: 5-6)")
        
        # Cooldown
        strategy_config = config.get('strategy', {})
        cooldown = strategy_config.get('cooldown_between_trades_seconds', 0)
        print(f"cooldown_between_trades: {cooldown}s")
        
        if cooldown > 180:
            warnings.append(f"cooldown MUITO LONGO: {cooldown}s (recomendado: 90-120s)")
        
        # RSI
        rsi_config = ai_config.get('rsi', {})
        oversold = rsi_config.get('oversold_level', 30)
        overbought = rsi_config.get('overbought_level', 70)
        print(f"RSI oversold/overbought: {oversold}/{overbought}")
        
        if oversold > 20 or overbought < 80:
            warnings.append(f"RSI CONSERVADOR: {oversold}/{overbought} (recomendado: 15/85 para mais trades)")
        
        # Volatilidade
        vol_config = config.get('technical_analysis', {}).get('volatility', {})
        vol_threshold = vol_config.get('volatility_threshold', 1.0)
        print(f"volatility_threshold: {vol_threshold}")
        
        if vol_threshold > 0.3:
            warnings.append(f"volatility_threshold MUITO ALTO: {vol_threshold} (recomendado: 0.15-0.25)")
        
        # Resultados
        print("\nRESULTADOS:")
        if issues:
            print("PROBLEMAS CRITICOS:")
            for issue in issues:
                print(f"  - {issue}")
        
        if warnings:
            print("CONFIGURACOES RESTRITIVAS:")
            for warning in warnings:
                print(f"  - {warning}")
        
        if not issues and not warnings:
            print("Configuracoes parecem adequadas para trading ativo")
        
        return len(issues) == 0
        
    except Exception as e:
        print(f"Erro ao verificar config: {e}")
        return False

def test_market_data():
    """Testa obtenção de dados de mercado"""
    print("\nTESTANDO DADOS DE MERCADO...")
    print("-" * 50)
    
    try:
        from analysis.market_analyzer import MarketAnalyzer
        
        # Config mínima para teste
        test_config = {'strategy': {}, 'technical_analysis': {'volatility': {}}}
        analyzer = MarketAnalyzer(test_config)
        
        # Testa preço atual
        symbol = 'XRP/USDT'
        price = analyzer.get_current_price(symbol)
        print(f"Preco atual {symbol}: {price}")
        
        if price <= 0:
            print("ERRO: Nao conseguiu obter preco atual")
            return False
        
        # Testa dados históricos
        df = analyzer.fetch_market_data(symbol, limit=50)
        print(f"Dados historicos: {len(df)} velas")
        
        if df.empty:
            print("ERRO: Nao conseguiu obter dados historicos")
            return False
        
        if len(df) < 30:
            print(f"AVISO: Poucos dados ({len(df)} velas) - pode afetar sinais")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao testar dados: {e}")
        return False

def test_signal_generation():
    """Testa geração de sinais"""
    print("\nTESTANDO GERACAO DE SINAIS...")
    print("-" * 50)
    
    try:
        # Carrega config real
        config_files = ['futures_config.yaml', 'config/futures_config.yaml']
        config = None
        
        for path in config_files:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                break
        
        if not config:
            print("ERRO: Config nao encontrada para teste")
            return False
        
        from analysis.market_analyzer import MarketAnalyzer
        analyzer = MarketAnalyzer(config)
        
        symbol = 'XRP/USDT'
        signals_found = 0
        
        print("Testando geracao de sinais (5 tentativas)...")
        
        for i in range(5):
            analysis = analyzer.analyze_market(symbol)
            
            if analysis:
                can_trade = analysis.get('can_trade', False)
                signal = analysis.get('signal')
                
                print(f"Tentativa {i+1}: can_trade={can_trade}")
                
                if signal and hasattr(signal, 'action'):
                    if signal.action in ['long', 'short']:
                        signals_found += 1
                        print(f"  -> SINAL: {signal.action} (confianca: {signal.confidence:.2f})")
                    else:
                        print(f"  -> Hold: {signal.reason}")
                else:
                    print("  -> Sem sinal")
                
                if not can_trade:
                    print(f"  -> Bloqueado: {analysis.get('reason', 'Sem razao')}")
            else:
                print(f"Tentativa {i+1}: Analise falhou")
        
        print(f"\nSinais encontrados: {signals_found}/5")
        
        if signals_found == 0:
            print("PROBLEMA: Nenhum sinal gerado - config muito restritiva")
            return False
        elif signals_found < 2:
            print("AVISO: Poucos sinais - considere relaxar parametros")
        else:
            print("OK: Geracao de sinais funcionando")
        
        return True
        
    except Exception as e:
        print(f"ERRO ao testar sinais: {e}")
        return False

def test_position_sizing():
    """Testa cálculo de posições"""
    print("\nTESTANDO POSITION SIZING...")
    print("-" * 50)
    
    try:
        from core.position.adapters.position_adapter import PositionManagerAdapter
        
        # Mock position manager
        class MockPM:
            def __init__(self):
                self.balance = 1000.0
                self.positions = {}
            def get_balance(self):
                return self.balance
        
        mock_pm = MockPM()
        adapter = PositionManagerAdapter(mock_pm)
        
        # Testa diferentes cryptos
        test_cases = [
            ('XRP/USDT', 2.8119),
            ('ETH/USDT', 4300.0),
            ('BTC/USDT', 65000.0)
        ]
        
        for symbol, price in test_cases:
            size = adapter.calculate_position_size(symbol, price, 'long', 0.8)
            crypto_info = adapter.get_crypto_info(symbol)
            
            print(f"{symbol}: {size} units @ ${price}")
            print(f"  Tipo: {crypto_info['detected_type']}")
            print(f"  Minimo: {crypto_info['min_quantity']}")
            
            if size <= 0:
                print(f"  ERRO: Tamanho invalido")
                return False
            elif size < crypto_info['min_quantity']:
                print(f"  ERRO: Abaixo do minimo")
                return False
        
        print("Position sizing funcionando corretamente")
        return True
        
    except Exception as e:
        print(f"ERRO ao testar position sizing: {e}")
        return False

def generate_optimized_config():
    """Gera configuração otimizada para mais trades"""
    print("\nCONFIGURACOES RECOMENDADAS PARA MAIS TRADES:")
    print("-" * 50)
    print("""
# Cole estas configuracoes no seu futures_config.yaml:

ai_futures:
  enabled: true
  scoring:
    min_score_long: 3.0      # Reduzido de 3.8
    min_score_short: 3.0     # Reduzido de 3.8
  filters:
    min_confidence: 0.50     # Reduzido de 0.48
  rsi:
    oversold_level: 15       # Mais agressivo (era 18)
    overbought_level: 85     # Mais agressivo (era 82)

strategy:
  cooldown_between_trades_seconds: 90    # Reduzido se estava maior
  analysis_interval_seconds: 30          # Analise mais frequente

risk_management:
  kill_switch:
    consecutive_losses: 5                 # Menos restritivo

technical_analysis:
  volatility:
    volatility_threshold: 0.20            # Reduzido de 0.25
""")

def main():
    """Funcao principal"""
    print("VALIDACAO RAPIDA DO SISTEMA DE TRADING")
    print("=" * 60)
    
    # Encontra config
    config_files = ['futures_config.yaml', 'config/futures_config.yaml', '../futures_config.yaml']
    config_path = None
    
    for path in config_files:
        if os.path.exists(path):
            config_path = path
            break
    
    if not config_path:
        print("ERRO: Arquivo futures_config.yaml nao encontrado!")
        print("Procurado em:", config_files)
        return
    
    print(f"Usando config: {config_path}\n")
    
    # Executa testes
    tests = [
        ("Configuracoes", lambda: check_config_restrictions(config_path)),
        ("Dados de Mercado", test_market_data),
        ("Geracao de Sinais", test_signal_generation),
        ("Position Sizing", test_position_sizing)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"✓ {test_name}: OK\n")
                passed += 1
            else:
                print(f"✗ {test_name}: PROBLEMA\n")
        except Exception as e:
            print(f"✗ {test_name}: ERRO - {e}\n")
    
    # Resumo
    print("RESUMO FINAL:")
    print(f"Testes aprovados: {passed}/{total}")
    
    if passed == total:
        print("Sistema funcionando - se poucos trades, considere ajustar parametros")
    elif passed < total/2:
        print("PROBLEMAS CRITICOS detectados")
    else:
        print("Sistema parcialmente funcional - precisa ajustes")
    
    # Sempre mostra configurações recomendadas
    generate_optimized_config()

if __name__ == "__main__":
    main()