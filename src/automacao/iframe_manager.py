# gerenciador_iframe.py
import logging
from contextlib import contextmanager
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)

class GerenciadorIframe:
    def __init__(self, driver):
        self.driver = driver
        self.iframe_stack = []
    
    @contextmanager
    def contexto_iframe(self, iframe_locator):
        try:
            self.iframe_stack.append(self.driver.current_window_handle)
            
            iframe = self.driver.find_element(*iframe_locator)
            self.driver.switch_to.frame(iframe)
            logger.debug(f"Entrou no iframe: {iframe_locator}")
            
            yield
            
        finally:
            try:
                self.driver.switch_to.default_content()
                logger.debug("Retornou ao contexto padrão")
                
                if self.iframe_stack:
                    window = self.iframe_stack.pop()
                    self.driver.switch_to.window(window)
                    
            except Exception as e:
                logger.warning(f"Erro ao restaurar contexto: {e}")
                self._recuperar_contexto_seguro()
    
    def _recuperar_contexto_seguro(self):
        try:
            self.driver.switch_to.default_content()
            self.iframe_stack.clear()
        except Exception as e:
            logger.error(f"Falha crítica ao recuperar contexto: {e}")