"""
Ponto de entrada principal - Versão Simplificada
"""

import sys
import os
import logging
from datetime import datetime

from config_manager import gerenciador_config
from sefaz_automator import AutomatorSEFAZ


def configurar_logging():
    """Configura logging simples e direto."""
    try:
        # Criar pasta de logs se não existir
        os.makedirs("logs", exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_log = f"logs/nfe_automation_{timestamp}.log"
        
        # Configuração básica
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            handlers=[
                logging.FileHandler(caminho_log, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Reduzir logs de bibliotecas externas
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Log iniciado: {caminho_log}")
        return True
        
    except Exception as e:
        print(f"Erro configuracao logging: {e}")
        return False


def main():
    """Função principal simplificada."""
    
    # Configurar logging primeiro
    if not configurar_logging():
        return 1
    
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*50)
    print("AUTOMACAO SEFAZ NFe - INICIANDO")
    print("="*50)
    print(f"Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*50)
    
    automator = None
    
    try:
        # 1. Carregar configurações
        logger.info("Carregando configuracoes...")
        config = gerenciador_config.carregar_config()
        if not config:
            logger.error("Falha: Configuracoes nao carregadas")
            return 1
        
        # 2. Validar credenciais
        logger.info("Validando credenciais...")
        erros = config.validar_formatos()
        if erros:
            logger.error("Erros nas credenciais:")
            for erro in erros:
                logger.error(f" - {erro}")
            return 1
        logger.info("Credenciais validadas")
        
        # 3. Inicializar automator
        logger.info("Inicializando automator...")
        automator = AutomatorSEFAZ()
        if not automator.inicializar(config):
            logger.error("Falha: Automator nao inicializado")
            return 1
        
        # 4. Executar fluxo
        logger.info("Executando fluxo...")
        sucesso = automator.executar_fluxo()
        
        # 5. Resultado final
        print("\n" + "="*50)
        if sucesso:
            print("SUCESSO: Processo concluido")
            print("Verifique os resultados no navegador")
        else:
            print("ERRO: Processo interrompido")
            print("Consulte o arquivo de log para detalhes")
        print(f"Fim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*50)
        
        return 0 if sucesso else 1
        
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuario")
        return 1
        
    except Exception as e:
        logger.error(f"Erro nao tratado: {e}")
        return 1
        
    finally:
        # Cleanup seguro
        if automator:
            automator.limpar_recursos()
        
        # Aguardar input antes de fechar
        try:
            input("\nPressione ENTER para sair...")
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())