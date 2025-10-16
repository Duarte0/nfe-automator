"""
Configuração centralizada de logging
"""
import logging
import sys
import os
from typing import Optional

class LoggingConfig:
    @staticmethod
    def setup(log_level: int = logging.INFO, log_file: Optional[str] = None) -> bool:
        try:
            handlers = [logging.StreamHandler(sys.stdout)]
            
            if log_file:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                handlers.append(logging.FileHandler(log_file, mode='w', encoding='utf-8'))
            
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
                datefmt='%H:%M:%S',
                handlers=handlers
            )
            
            logging.getLogger('selenium').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('webdriver_manager').setLevel(logging.INFO)
            
            return True
            
        except Exception as e:
            print(f"Erro configuração logging: {e}")
            return False

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)