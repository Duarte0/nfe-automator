import logging
import time
from selenium.common.exceptions import WebDriverException, NoSuchWindowException

logger = logging.getLogger(__name__)

class HealthCheckDriver:
    def __init__(self, driver):
        self.driver = driver
    
    def verificar_sessao_ativa(self) -> bool:
        try:
            current_url = self.driver.current_url
            title = self.driver.title
            return True
        except (WebDriverException, NoSuchWindowException) as e:
            logger.error(f"Sessão do driver inativa: {e}")
            return False
    
    def executar_com_verificacao(self, operacao, nome_operacao, max_tentativas=2):
        for tentativa in range(1, max_tentativas + 1):
            if not self.verificar_sessao_ativa():
                logger.error(f"Driver inativo em {nome_operacao}, tentativa {tentativa}")
                if tentativa == max_tentativas:
                    raise WebDriverException(f"Driver inativo após {max_tentativas} tentativas")
                continue
            
            try:
                return operacao()
            except WebDriverException as e:
                logger.warning(f"Erro de driver em {nome_operacao}: {e}")
                if tentativa == max_tentativas:
                    raise