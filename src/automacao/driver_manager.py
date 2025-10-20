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
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self._configurar_logging_limpo()
    
    def _configurar_logging_limpo(self):
        log_levels = {
            'selenium': logging.WARNING,
            'selenium.webdriver.remote.remote_connection': logging.WARNING,
            'urllib3': logging.WARNING,
            'urllib3.connectionpool': logging.WARNING,
            'WDM': logging.WARNING,  # Reduzir ainda mais logs do WDM
            'webdriver_manager': logging.WARNING,
        }
        
        for logger_name, level in log_levels.items():
            logging.getLogger(logger_name).setLevel(level)
        
        try:
            from selenium.webdriver.remote.remote_connection import LOGGER
            LOGGER.setLevel(logging.WARNING)
        except ImportError:
            pass
    
    def configurar_driver(self) -> Optional[webdriver.Chrome]:
        logger.info("Configurando WebDriver...")
        
        # Prioridade: WebDriver Manager (sempre atualizado)
        estrategias = [
            self._configurar_webdriver_manager,
            self._configurar_driver_sistema,
        ]
        
        for estrategia in estrategias:
            driver = estrategia()
            if driver:
                self.driver = driver
                self._aplicar_config_stealth()
                logger.info("WebDriver configurado com sucesso")
                return driver
        
        self._mostrar_erro_driver()
        return None
    
    def _configurar_webdriver_manager(self) -> Optional[webdriver.Chrome]:
        """Configura via WebDriver Manager - SEMPRE ATUALIZADO"""
        try:
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.core.os_manager import ChromeType
            
            # Configuração silenciosa
            service = Service(
                ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install()
            )
            
            options = self._obter_opcoes_chrome()
            driver = webdriver.Chrome(service=service, options=options)
            
            return driver
            
        except Exception as e:
            logger.debug(f"WebDriver Manager: {e}")
            return None
    
    def _configurar_driver_sistema(self) -> Optional[webdriver.Chrome]:
        """Fallback: Driver do PATH do sistema"""
        try:
            options = self._obter_opcoes_chrome()
            driver = webdriver.Chrome(options=options)
            return driver
        except Exception as e:
            logger.debug(f"Driver sistema: {e}")
            return None
    
    def _obter_opcoes_chrome(self):
        options = Options()
        
        # Otimizações de performance e stealth
        options.add_argument('--log-level=3')
        options.add_argument('--disable-logging')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1200,800")
        
        # Remover automação detectável
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        return options
    
    def _aplicar_config_stealth(self):
        if self.driver:
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
    
    def _mostrar_erro_driver(self):
        erro_msg = """
     ERRO DE CONFIGURACAO DO NAVEGADOR
====================================
Não foi possível configurar o WebDriver.

SOLUÇÕES:
1. Execute: pip install webdriver-manager
2. Verifique se o Google Chrome está instalado
3. Ou baixe ChromeDriver manualmente em:
   https://chromedriver.chromium.org/
   e coloque no PATH do sistema
====================================
"""
        print(erro_msg)
    
    def fechar(self):
        logger.info("Navegador mantido aberto para inspeção")
        self.driver = None