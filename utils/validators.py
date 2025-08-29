
"""
Funções de validação gerais
"""

import os
from typing import List

def check_dependencies() -> bool:
    """Verifica se as dependências estão instaladas"""
    required_modules = [
        'pandas', 'numpy', 'requests', 'yaml', 
        'ta', 'ccxt'  # ccxt opcional para múltiplas exchanges
    ]
    
    missing = []
    
    for module in required_modules:
        try:
            if module == 'ccxt':  # Opcional
                continue
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"❌ Pacotes faltando: {', '.join(missing)}")
        print(f"Instale com: pip install {' '.join(missing)}")
        return False
    
    return True

def check_config_file(config_path: str) -> bool:
    """Verifica se o arquivo de configuração existe"""
    if not os.path.exists(config_path):
        print(f"❌ Arquivo não encontrado: {config_path}")
        
        # Tenta criar config padrão
        if "futures_config.yaml" in config_path:
            print("Criando configuração padrão...")
            create_default_config(config_path)
            return True
        
        return False
    return True

def create_default_config(path: str):
    """Cria arquivo de configuração padrão"""
    default_config = """
# Configuração padrão - AJUSTE ANTES DE USAR!
advanced:
  paper_trading:
    enabled: true  # SEMPRE inicie com paper trading
    initial_balance_usdt: 100.0
    
exchanges:
  bingx:
    api_key: "SUA_API_KEY_AQUI"
    secret_key: "SEU_SECRET_KEY_AQUI"
    testnet: false
    
strategy:
  primary_exchange: "bingx"
  initial_wait_seconds: 300
  analysis_interval_seconds: 60
  
trading:
  primary_pair: "ETH/USDT"
  trading_pairs:
    - symbol: "ETH/USDT"
      futures_symbol: "ETH-USDT"
      leverage: 2
      risk_per_trade_pct: 2.0
      min_position_size: 0.01
      max_position_size: 1.0
      
risk_management:
  stop_loss:
    enabled: true
    percentage: 2.0
  take_profit:
    enabled: true
    percentage: 3.0
  daily_limits:
    max_trades: 5
    max_loss_usdt: 20.0
"""
    
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(default_config)
    print(f"✅ Configuração padrão criada em: {path}")

def validate_api_keys(config: dict) -> bool:
    """Valida se as API keys estão configuradas"""
    try:
        exchange = config['strategy']['primary_exchange']
        api_key = config['exchanges'][exchange]['api_key']
        secret = config['exchanges'][exchange]['secret_key']
        
        if "SUA_API_KEY" in api_key or "SEU_SECRET" in secret:
            print("⚠️ API keys não configuradas!")
            print("Por favor, edite o arquivo de configuração com suas chaves")
            return False
            
        return True
    except KeyError:
        return False