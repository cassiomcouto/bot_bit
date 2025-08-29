# ========== utils/logger.py ==========
"""
Sistema de logging configurável
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = "logs/bot.log") -> logging.Logger:
    """
    Configura sistema de logging
    
    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR)
        log_file: Caminho do arquivo de log
    
    Returns:
        Logger configurado
    """
    # Cria diretório de logs se não existir
    Path(log_file).parent.mkdir(exist_ok=True)
    
    # Formato detalhado
    detailed_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Formato simples para console
    simple_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_format)
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(simple_format)
    
    # Configura root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduz verbosidade de bibliotecas externas
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    return root_logger
