#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BingX Futures Trading Bot - Sistema Principal
Versão modularizada e otimizada com seleção de bot via configuração
"""

import logging
import sys
import os
import signal
import yaml
from pathlib import Path
from datetime import datetime

# Adiciona o diretório atual ao path
sys.path.append(str(Path(__file__).parent))

# Importações locais
from utils.logger import setup_logging
from utils.validators import check_dependencies, check_config_file

# Constantes
DEFAULT_CONFIG = "config/futures_config.yaml"

class BotManager:
    """Gerenciador do bot com tratamento de sinais"""
    
    def __init__(self):
        self.bot = None
        self.logger = None
        self.config = None
        self.version = "2.0.0"  # versão padrão fallback
        
    def _load_config(self):
        """Carrega configuração para obter informações dinâmicas"""
        config_file = os.getenv('BOT_CONFIG', DEFAULT_CONFIG)
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                # Obtém versão do metadata ou usa fallback
                self.version = self._get_config('metadata.config_version', self.version)
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}")
            self.config = {}
    
    def _get_config(self, path: str, default=None):
        """Obtém valor de configuração aninhada"""
        if not self.config:
            return default
            
        keys = path.split('.')
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def _initialize_bot(self, config_file: str):
        """Inicializa o bot baseado na configuração"""
        # Verifica se deve usar bot integrado ou original
        use_integrated_bot = self._get_config('advanced_settings.use_integrated_bot', False)
        use_ai_optimization = self._get_config('advanced_settings.ai_optimization.enabled', False)
        
        if use_integrated_bot or use_ai_optimization:
            self.logger.info("Carregando bot integrado com sistema IA")
            from core.bot_integrated import BingXFuturesBotIntegrated
            return BingXFuturesBotIntegrated(config_file)
        else:
            self.logger.info("Carregando bot original")
            from core.bot import BingXFuturesBot
            return BingXFuturesBot(config_file)
        
    def signal_handler(self, signum, frame):
        """Tratamento de interrupção (Ctrl+C)"""
        if self.logger:
            self.logger.info("\n🛑 Sinal de interrupção recebido...")
        
        if self.bot:
            self.bot.shutdown()
        
        sys.exit(0)
    
    def display_banner(self):
        """Exibe banner inicial com informações dinâmicas"""
        # Carrega configuração para banner dinâmico
        self._load_config()
        
        # Obtém informações da configuração
        primary_pair = self._get_config('trading.primary_pair', 'ETH/USDT')
        exchange = self._get_config('strategy.primary_exchange', 'BingX')
        mode = self._get_config('strategy.mode', 'futures_precision')
        use_integrated = self._get_config('advanced_settings.use_integrated_bot', False)
        use_ai = self._get_config('advanced_settings.ai_optimization.enabled', False)
        
        # Determina tipo de bot
        if use_integrated or use_ai:
            bot_type = "INTEGRADO (IA)"
        else:
            bot_type = "ORIGINAL"
        
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║           BINGX FUTURES TRADING BOT v{self.version}              ║
║                                                              ║
║  Par Principal: {primary_pair:<20} Exchange: {exchange:<10}     ║
║  Modo: {mode:<25}                           ║
║  Bot Type: {bot_type:<20}                            ║
║  {'Data: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^60}║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def run(self):
        """Executa o bot principal"""
        # Configuração de sinais
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Exibe banner
        self.display_banner()
        
        # Verificações iniciais
        print("🔋 Verificando dependências...")
        if not check_dependencies():
            print("❌ Falha na verificação de dependências")
            return 1
        print("✅ Dependências OK")
        
        # Verifica arquivo de configuração
        config_file = os.getenv('BOT_CONFIG', DEFAULT_CONFIG)
        print(f"🔋 Verificando configuração: {config_file}")
        if not check_config_file(config_file):
            print("❌ Falha na verificação de configuração")
            return 1
        print("✅ Configuração OK")
        
        # Configura logging
        print("Configurando sistema de logs...")
        self.logger = setup_logging()
        self.logger.info(f"Iniciando BingX Futures Bot v{self.version}")
        
        try:
            # Inicializa o bot (original ou integrado baseado na config)
            self.logger.info("🤖 Inicializando bot...")
            self.bot = self._initialize_bot(config_file)
            
            # Verifica modo de operação
            mode = "PAPER TRADING" if self.bot.paper_trading else "TRADING REAL"
            primary_pair = self.bot._get_config('trading.primary_pair', 'ETH/USDT')
            self.logger.info(f"Modo de operação: {mode}")
            self.logger.info(f"Par principal: {primary_pair}")
            
            # Verifica se é bot integrado
            if hasattr(self.bot, 'ai_optimization_enabled'):
                if self.bot.ai_optimization_enabled:
                    self.logger.info("Sistema de otimização IA: ATIVO")
                else:
                    self.logger.info("Sistema de otimização IA: INATIVO")
            
            if not self.bot.paper_trading:
                self.logger.warning("⚠️ ATENÇÃO: Modo de trading REAL ativado!")
                self.logger.warning("⚠️ Operações reais serão executadas!")
                
                # Confirmação de segurança
                print("\n" + "="*50)
                print("⚠️  AVISO: MODO DE TRADING REAL ATIVADO!")
                print("="*50)
                print("Operações REAIS serão executadas com dinheiro REAL.")
                print("Certifique-se de que:")
                print("  1. As configurações estão corretas")
                print("  2. Os limites de risco estão adequados")
                print("  3. Você entende os riscos envolvidos")
                print("="*50)
                
                response = input("\nDeseja continuar? (digite 'SIM' para confirmar): ")
                if response.upper() != 'SIM':
                    self.logger.info("Execução cancelada pelo usuário")
                    return 0
            
            # Executa o bot
            self.logger.info("🚀 Iniciando loop de trading...")
            self.bot.run()
            
        except KeyboardInterrupt:
            self.logger.info("ℹ️ Bot interrompido pelo usuário")
            return 0
            
        except FileNotFoundError as e:
            self.logger.error(f"📁 Arquivo não encontrado: {e}")
            return 1
            
        except ImportError as e:
            self.logger.error(f"📦 Erro de importação: {e}")
            self.logger.error("Verifique se todos os módulos estão instalados")
            return 1
            
        except Exception as e:
            self.logger.error(f"❌ Erro fatal: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 1
            
        finally:
            if self.bot:
                self.bot.print_final_stats()
            self.logger.info("Bot finalizado")
            
        return 0

def main():
    """Função principal"""
    manager = BotManager()
    return manager.run()

if __name__ == "__main__":
    exit(main())