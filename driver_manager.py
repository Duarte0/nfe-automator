"""
Gerenciador de WebDriver simplificado e robusto.
"""
import os
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)


class GerenciadorDriver:
    """Gerencia criação e configuração do WebDriver."""
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self._configurar_logging_limpo()
    
    def _configurar_logging_limpo(self):
        """Configura logging limpo para Selenium."""
        log_levels = {
            'selenium': logging.WARNING,
            'selenium.webdriver.remote.remote_connection': logging.WARNING,
            'urllib3': logging.WARNING,
            'urllib3.connectionpool': logging.WARNING,
            'WDM': logging.INFO,
            'webdriver_manager': logging.INFO,
        }
        
        for logger_name, level in log_levels.items():
            logging.getLogger(logger_name).setLevel(level)
        
        # Configuração específica do Selenium
        try:
            from selenium.webdriver.remote.remote_connection import LOGGER
            LOGGER.setLevel(logging.WARNING)
        except ImportError:
            pass
    
    def configurar_driver(self) -> Optional[webdriver.Chrome]:
        """Configura WebDriver com fallback."""
        estrategias = [
            self._configurar_driver_manual,
            self._configurar_webdriver_manager,
            self._configurar_driver_sistema,
        ]
        
        for estrategia in estrategias:
            driver = estrategia()
            if driver:
                self.driver = driver
                self._aplicar_config_stealth()
                return driver
        
        self._mostrar_erro_driver()
        return None
    
    def _configurar_driver_manual(self) -> Optional[webdriver.Chrome]:
        """Configura usando driver manual."""
        try:
            logger.info("🔧 Tentando configuração manual...")
            
            # Caminhos possíveis para o ChromeDriver
            caminhos_driver = [
                "./drivers/chromedriver.exe",
                "./chromedriver.exe",
                "chromedriver.exe",
                os.path.join(os.getcwd(), "drivers", "chromedriver.exe"),
            ]
            
            caminho_driver = None
            for caminho in caminhos_driver:
                if os.path.exists(caminho):
                    caminho_driver = caminho
                    logger.info(f"📁 ChromeDriver encontrado: {caminho}")
                    break
            
            if not caminho_driver:
                logger.warning("📁 Nenhum ChromeDriver manual encontrado")
                return None
            
            service = Service(caminho_driver)
            options = self._obter_opcoes_chrome()
            driver = webdriver.Chrome(service=service, options=options)
            
            logger.info("✅ Driver manual configurado com sucesso")
            return driver
            
        except Exception as e:
            logger.warning(f"⚠️ Driver manual falhou: {e}")
            return None
    
    def _configurar_webdriver_manager(self) -> Optional[webdriver.Chrome]:
        """Configura usando WebDriver Manager."""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            
            logger.info("🔧 Tentando configuração automática com WebDriver Manager...")
            
            service = Service(
                ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install()
            )
            
            options = self._obter_opcoes_chrome()
            driver = webdriver.Chrome(service=service, options=options)
            
            logger.info("✅ Driver configurado via WebDriver Manager")
            return driver
            
        except Exception as e:
            logger.warning(f"⚠️ WebDriver Manager falhou: {e}")
            return None
    
    def _configurar_driver_sistema(self) -> Optional[webdriver.Chrome]:
        """Configura usando driver do PATH."""
        try:
            logger.info("🔧 Tentando driver do PATH do sistema...")
            options = self._obter_opcoes_chrome()
            driver = webdriver.Chrome(options=options)
            logger.info("✅ Driver do sistema configurado")
            return driver
        except Exception as e:
            logger.warning(f"⚠️ Driver do sistema falhou: {e}")
            return None
    
    def _obter_opcoes_chrome(self):
        """Retorna opções configuradas do Chrome."""
        options = Options()
        
        # 🔧 CONFIGURAÇÃO DE LOGGING LIMPO
        options.add_argument('--log-level=3')
        options.add_argument('--disable-logging')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        # Performance e stealth
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1200,800")
        
        # Remover automação detectável
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        return options
    
    def _aplicar_config_stealth(self):
        """Aplica configurações para evitar detecção."""
        if self.driver:
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception as e:
                logger.debug(f"⚠️ Configuração stealth falhou: {e}")
    
    def _mostrar_erro_driver(self):
        """Exibe mensagem de erro amigável."""
        erro_msg = """
❌ ERRO DE CONFIGURAÇÃO DO NAVEGADOR
====================================
Não foi possível configurar o WebDriver.

🔧 SOLUÇÕES:
1. Baixe o ChromeDriver em: https://chromedriver.chromium.org/
2. Coloque na pasta 'drivers/chromedriver.exe'
3. Ou execute: pip install webdriver-manager
4. Verifique se o Google Chrome está instalado
====================================
"""
        print(erro_msg)
    
    def fechar(self):
        logger.info("🔍 MANTENDO NAVEGADOR ABERTO PARA INSPEÇÃO")
        logger.info("💡 O navegador permanecerá aberto para verificação")
        logger.info("📋 Verifique os resultados manualmente")
        
        # ⚠️ NÃO executa driver.quit() - mantém aberto
        # self.driver.quit()  # COMENTADO
        
        # Apenas limpa a referência, mas mantém navegador aberto
        self.driver = None