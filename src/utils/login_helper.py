"""
Configuração centralizada de logging
"""
import logging
import sys
import os
from typing import Optional

class LoggingConfig:
    @staticmethod
    def setup(log_level: int = logging.WARNING, log_file: Optional[str] = None, verbose: bool = False) -> bool:
        """
        Configura logging com níveis ajustados
        verbose=True: mostra todos os logs (INFO, DEBUG)
        verbose=False: mostra apenas WARNING e ERROR (padrão)
        """
        try:
            # Se verbose for True, usa o nível fornecido, senão força WARNING
            nivel_efetivo = log_level if verbose else logging.WARNING
            
            handlers = [logging.StreamHandler(sys.stdout)]
            
            if log_file:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                handlers.append(logging.FileHandler(log_file, mode='w', encoding='utf-8'))
            
            logging.basicConfig(
                level=nivel_efetivo,
                format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
                datefmt='%H:%M:%S',
                handlers=handlers
            )
            
            # Silenciar logs de bibliotecas externas
            logging.getLogger('selenium').setLevel(logging.WARNING)
            logging.getLogger('urllib3').setLevel(logging.WARNING)
            logging.getLogger('webdriver_manager').setLevel(logging.WARNING)
            
            # Loggers específicos do nosso sistema - controlar nível base
            loggers_sistema = [
                'src.automacao.processador_ie',
                'src.automacao.download_manager', 
                'src.automacao.fluxo_utils',
                'src.automacao.driver_manager',
                'src.automacao.iframe_manager'
            ]
            
            for logger_name in loggers_sistema:
                logging.getLogger(logger_name).setLevel(nivel_efetivo)
            
            return True
            
        except Exception as e:
            print(f"Erro configuração logging: {e}")
            return False

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)