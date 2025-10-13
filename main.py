"""
Ponto de entrada principal - Versão Otimizada
"""

import sys
import os
import logging
from datetime import datetime

from src.config import gerenciador_config
from src.automacao import AutomatorSEFAZ

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def configurar_logging():
    try:
        os.makedirs("logs", exist_ok=True)
        
        caminho_log = "logs/nfe_automation.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-8s | %(message)s',
            handlers=[
                logging.FileHandler(caminho_log, mode='w', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        return True
        
    except Exception as e:
        print(f"Erro configuracao logging: {e}")
        return False
    
def limpar_logs_antigos(max_logs=5):
    try:
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            return
            
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)))
        
        if len(log_files) > max_logs:
            for old_log in log_files[:-max_logs]:
                os.remove(os.path.join(logs_dir, old_log))
                print(f"Removido log antigo: {old_log}")
                
    except Exception as e:
        print(f"Erro ao limpar logs antigos: {e}")

def main():
    
    limpar_logs_antigos(max_logs=3)
    
    if not configurar_logging():
        return 1
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*50)
    print("AUTOMACAO SEFAZ NFe - INICIANDO")
    print("="*50)
    
    automator = None
    
    try:
        logger.info("Carregando configuracoes...")
        config = gerenciador_config.carregar_config()
        if not config:
            logger.error("Falha: Configuracoes nao carregadas")
            return 1
        
        logger.info("Validando credenciais...")
        erros = config.validar_formatos()
        if erros:
            logger.error("Erros nas credenciais:")
            for erro in erros:
                logger.error(f" - {erro}")
            return 1
        
        logger.info("Inicializando automator...")
        automator = AutomatorSEFAZ()
        if not automator.inicializar(config):
            logger.error("Falha: Automator nao inicializado")
            return 1
        
        logger.info("Executando fluxo...")
        sucesso = automator.executar_fluxo()
        
        print("\n" + "="*50)
        if sucesso:
            print("SUCESSO: Processo concluido")
        else:
            print("ERRO: Processo interrompido")
        print("="*50)
        
        return 0 if sucesso else 1
        
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuario")
        return 1
        
    except Exception as e:
        logger.error(f"Erro nao tratado: {e}")
        return 1
        
    finally:
        if automator:
            automator.limpar_recursos()
        
        try:
            input("\nPressione ENTER para sair...")
        except:
            pass

if __name__ == "__main__":
    sys.exit(main())