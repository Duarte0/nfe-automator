"""
Ponto de entrada principal da automação SEFAZ NFe
"""
import sys
import os
import logging
import traceback
from datetime import datetime

# Configuração de imports
from config_manager import gerenciador_config
from sefaz_automator import AutomatorSEFAZ


def configurar_logging():
    """
    Configura sistema de logging robusto.
    
    Cria arquivos de log com timestamp e configura formato profissional.
    """
    try:
        # Criar pasta de logs se não existir
        pasta_logs = "logs"
        os.makedirs(pasta_logs, exist_ok=True)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo_log = f"nfe_automation_{timestamp}.log"
        caminho_log = os.path.join(pasta_logs, nome_arquivo_log)
        
        # 🔧 CONFIGURAÇÃO DE LOGGING LIMPO
        log_levels = {
            '__main__': logging.INFO,
            'sefaz_automator': logging.INFO,
            'config_manager': logging.INFO,
            'driver_manager': logging.INFO,
            'selenium': logging.WARNING,           # Apenas warnings e erros
            'selenium.webdriver.remote.remote_connection': logging.WARNING,
            'urllib3': logging.WARNING,            # Apenas warnings
            'urllib3.connectionpool': logging.WARNING,
            'WDM': logging.INFO,                   # Info apenas
            'webdriver_manager': logging.INFO,
        }
        
        # Configurar nível para cada logger
        for logger_name, level in log_levels.items():
            logging.getLogger(logger_name).setLevel(level)
        
        # Configuração específica do Selenium Remote Connection
        try:
            from selenium.webdriver.remote.remote_connection import LOGGER
            LOGGER.setLevel(logging.WARNING)
        except ImportError:
            pass
        
        # Handler principal para aplicação
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s'
        )
        
        # Arquivo de log principal
        file_handler = logging.FileHandler(caminho_log, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # Console handler (apenas para aplicação)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # Aplicar handlers apenas aos loggers da aplicação
        app_loggers = ['__main__', 'sefaz_automator', 'config_manager', 'driver_manager']
        for logger_name in app_loggers:
            logger = logging.getLogger(logger_name)
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            logger.propagate = False  # Evitar duplicação
        
        logger_principal = logging.getLogger(__name__)
        logger_principal.info(f"📝 LOG INICIADO: {caminho_log}")
        logger_principal.info("🧹 LOGGING LIMPO CONFIGURADO")
        logger_principal.info("🔧 Selenium: apenas WARNING+ | Chrome: logs silenciados")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NA CONFIGURAÇÃO DE LOGGING: {e}")
        return False


def mostrar_banner():
    """Exibe banner profissional."""
    print("\n" + "="*70)
    print("🚀 AUTOMAÇÃO SEFAZ NFe - DOWNLOAD DE XMLs")
    print("="*70)
    print(f"📅 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("🔧 Sistema otimizado com gerenciamento de abas")
    print("="*70)


def verificar_ambiente():
    """
    Verifica se o ambiente está configurado corretamente.
    
    Returns:
        bool: True se o ambiente está OK, False caso contrário
    """
    logger = logging.getLogger(__name__)
    
    # Verificar se arquivos necessários existem
    arquivos_necessarios = [
        "config.py",
        "sefaz_automator.py",
        "config_manager.py",
        "driver_manager.py", 
        "constants.py"
    ]
    
    for arquivo in arquivos_necessarios:
        if not os.path.exists(arquivo):
            logger.warning(f"⚠️ Arquivo não encontrado: {arquivo}")
            return False
    
    # Verificar pasta drivers
    if not os.path.exists("drivers"):
        logger.warning("⚠️ Pasta 'drivers' não encontrada")
        logger.info("💡 O WebDriver Manager pode baixar automaticamente")
    
    return True


def executar_automacao():
    """
    Executa o fluxo principal de automação.
    
    Returns:
        bool: True se bem sucedido, False caso contrário
    """
    logger = logging.getLogger(__name__)
    automator = None
    
    try:
        # 1. Carregar configurações
        logger.info("📋 Etapa 1/4: Carregando configurações...")
        config = gerenciador_config.carregar_config()
        if not config:
            logger.error("❌ Falha crítica: Não foi possível carregar as configurações")
            return False
        
        # 2. Inicializar automator
        logger.info("🔧 Etapa 2/4: Inicializando automator...")
        automator = AutomatorSEFAZ()
        
        if not automator.inicializar(config):
            logger.error("❌ Falha crítica: Não foi possível inicializar o automator")
            return False
        
        # 3. Executar fluxo principal
        logger.info("🔄 Etapa 3/4: Executando fluxo de automação...")
        sucesso = automator.executar_fluxo()
        
        # 4. Resultado final
        if sucesso:
            logger.info("🎉 Etapa 4/4: Processo concluído com SUCESSO!")
            return True
        else:
            logger.error("❌ Etapa 4/4: Processo interrompido devido a erros")
            return False
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Processo interrompido pelo usuário")
        logger.warning("Processo interrompido pelo usuário via Ctrl+C")
        return False
        
    except Exception as e:
        logger.error(f"💥 Erro não tratado: {e}")
        logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        return False
        
    finally:
        # Cleanup garantido e seguro
        executar_cleanup(automator)


def executar_cleanup(automator):
    """
    Executa limpeza de recursos de forma segura.
    
    Args:
        automator: Instância do AutomatorSEFAZ ou None
    """
    logger = logging.getLogger(__name__)
    
    try:
        if automator is not None:
            logger.info("🧹 Executando limpeza de recursos...")
            automator.limpar_recursos()
            logger.info("✅ Limpeza concluída")
        else:
            logger.debug("ℹ️  Nenhum recurso para limpar")
            
    except Exception as e:
        logger.error(f"⚠️ Erro durante limpeza: {e}")


def mostrar_resultado(sucesso):
    """
    Exibe resultado final baseado no sucesso da execução.
    
    Args:
        sucesso: Booleano indicando sucesso ou falha
    """
    print("\n" + "="*70)
    
    if sucesso:
        print("🎉 SUCESSO: Processo concluído!")
        print("📊 Verifique os resultados no navegador")
        print("💾 XMLs disponíveis para download")
    else:
        print("❌ ERRO: Processo interrompido")
        print("📋 Consulte o arquivo de log para detalhes")
        print("🔧 Verifique: config.py, conexão, credenciais")
    
    print("⏰ Fim:", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    print("="*70)


def main():
    """
    Função principal da aplicação.
    
    Coordena toda a execução com tratamento robusto de erros.
    
    Returns:
        int: Código de saída para o sistema operacional
    """
    # Configurar logging primeiro
    if not configurar_logging():
        print("❌ Não foi possível inicializar o sistema de logging")
        return 1
    
    logger = logging.getLogger(__name__)
    
    try:
        # Banner inicial
        mostrar_banner()
        logger.info("Iniciando aplicação de automação SEFAZ NFe")
        
        # Verificar ambiente
        logger.info("🔍 Verificando ambiente...")
        if not verificar_ambiente():
            logger.warning("⚠️ Alguns arquivos podem estar faltando, mas continuando...")
        
        # Executar automação principal
        sucesso = executar_automacao()
        
        # Mostrar resultado final
        mostrar_resultado(sucesso)
        
        return 0 if sucesso else 1
        
    except Exception as e:
        # Erro crítico durante inicialização
        print(f"\n💥 ERRO CRÍTICO: {e}")
        logger.critical(f"Erro durante inicialização: {e}")
        logger.critical(f"Stack trace: {traceback.format_exc()}")
        return 1
        
    finally:
        # Aguardar input do usuário antes de fechar
        try:
            input("\nPressione ENTER para sair...")
        except:
            pass  # Ignora erro se não houver input disponível


if __name__ == "__main__":
    """
    Ponto de entrada do script.
    
    Garante que a aplicação sempre retorne um código de saída apropriado.
    """
    try:
        codigo_saida = main()
        sys.exit(codigo_saida)
    except KeyboardInterrupt:
        print("\n\n⏹️  Aplicação interrompida")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERRO INESPERADO: {e}")
        sys.exit(1)