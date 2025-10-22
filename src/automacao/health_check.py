import logging
import time
from typing import Dict
from selenium.common.exceptions import WebDriverException, NoSuchWindowException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class HealthCheckDriver:
    def __init__(self, driver):
        self.driver = driver
        self.estatisticas = {
            'verificacoes_realizadas': 0,
            'sessoes_recuperadas': 0,
            'erros_detectados': 0
        }
    
    def verificar_sessao_ativa(self) -> bool:
        """Verificação básica de sessão ativa"""
        try:
            current_url = self.driver.current_url
            title = self.driver.title
            return True
        except (WebDriverException, NoSuchWindowException) as e:
            logger.error(f"Sessão do driver inativa: {e}")
            return False
    
    def verificar_estado_aplicacao_sefaz(self) -> Dict[str, bool]:
        """Verifica vários aspectos do estado da aplicação SEFAZ"""
        resultados = {
            'sessao_ativa': False,
            'pagina_carregada': False,
            'sem_erros_visiveis': False,
            'iframe_acessivel': False,
            'elementos_chave_presentes': False
        }
        
        try:
            resultados['sessao_ativa'] = self.verificar_sessao_ativa()
            if not resultados['sessao_ativa']:
                return resultados
            
            resultados['pagina_carregada'] = self.driver.execute_script("return document.readyState") == "complete"
            
            resultados['sem_erros_visiveis'] = self._verificar_erros_pagina()
            
            resultados['iframe_acessivel'] = self._verificar_iframe_acessivel()
            
            resultados['elementos_chave_presentes'] = self._verificar_elementos_chave()
            
            self.estatisticas['verificacoes_realizadas'] += 1
            return resultados
            
        except Exception as e:
            logger.error(f"Erro na verificação de estado: {e}")
            resultados['sessao_ativa'] = False
            return resultados
    
    def _verificar_erros_pagina(self) -> bool:
        """Verifica se há mensagens de erro na página"""
        try:
            textos_erro = [
                "erro", "error", "inválido", "incorreto", "falha", 
                "timeout", "expirou", "não encontrado", "acesso negado"
            ]
            
            page_source = self.driver.page_source.lower()
            
            for texto in textos_erro:
                if texto in page_source:
                    elementos_erro = self.driver.find_elements(
                        By.XPATH, f"//*[contains(text(), '{texto}')]"
                    )
                    for elemento in elementos_erro:
                        estilo = elemento.value_of_css_property('color')
                        if 'red' in estilo or 'error' in elemento.get_attribute('class').lower():
                            logger.warning(f"Erro detectado na página: {elemento.text[:100]}")
                            return False
            return True
        except:
            return True 
    
    def _verificar_iframe_acessivel(self) -> bool:
        """Verifica se o iframe principal está acessível"""
        try:
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            if iframe.is_displayed():
                self.driver.switch_to.frame(iframe)
                titulo_iframe = self.driver.find_elements(By.TAG_NAME, "title") or self.driver.find_elements(By.TAG_NAME, "h1")
                self.driver.switch_to.default_content()
                return len(titulo_iframe) > 0
            return False
        except:
            return False
    
    def _verificar_elementos_chave(self) -> bool:
        try:
            elementos_chave = [
                (By.ID, "iNetaccess"),
                (By.TAG_NAME, "body"),
                (By.TAG_NAME, "form")
            ]
            
            for seletor in elementos_chave:
                if not self.driver.find_elements(*seletor):
                    return False
            return True
        except:
            return False
    
    def tentar_recuperar_sessao(self, max_tentativas: int = 3) -> bool:
        """Tenta recuperar uma sessão problemática"""
        for tentativa in range(max_tentativas):
            logger.info(f"Tentativa {tentativa + 1} de recuperação de sessão")
            
            try:
                self.driver.refresh()
                time.sleep(3)
                
                if self.verificar_estado_aplicacao_sefaz()['sessao_ativa']:
                    logger.info("Sessão recuperada com refresh")
                    self.estatisticas['sessoes_recuperadas'] += 1
                    return True
            except:
                pass
            
            try:
                self.driver.get("https://www.sefaz.go.gov.br/netaccess/000System/acessoRestrito/")
                time.sleep(5)
                
                if self.verificar_estado_aplicacao_sefaz()['sessao_ativa']:
                    logger.info("Sessão recuperada voltando para URL base")
                    self.estatisticas['sessoes_recuperadas'] += 1
                    return True
            except:
                pass
            
            if tentativa == max_tentativas - 1: 
                try:
                    self.driver.delete_all_cookies()
                    self.driver.refresh()
                    time.sleep(5)
                except:
                    pass
        
        logger.error("Não foi possível recuperar a sessão")
        self.estatisticas['erros_detectados'] += 1
        return False
    
    def executar_com_verificacao(self, operacao, nome_operacao: str, max_tentativas: int = 2):
        """Executa operação com verificações de saúde"""
        for tentativa in range(1, max_tentativas + 1):
            estado = self.verificar_estado_aplicacao_sefaz()
            
            if not estado['sessao_ativa']:
                logger.warning(f"Sessão inativa em {nome_operacao}, tentativa {tentativa}")
                if not self.tentar_recuperar_sessao():
                    if tentativa == max_tentativas:
                        raise WebDriverException(f"Sessão inativa após {max_tentativas} tentativas de recuperação")
                    continue
            
            problemas = []
            if not estado['pagina_carregada']:
                problemas.append("página não carregada")
            if not estado['sem_erros_visiveis']:
                problemas.append("erros visíveis na página")
            if not estado['iframe_acessivel']:
                problemas.append("iframe inacessível")
            if not estado['elementos_chave_presentes']:
                problemas.append("elementos chave ausentes")
            
            if problemas and tentativa > 1:  
                logger.warning(f"Problemas detectados em {nome_operacao}: {', '.join(problemas)}")
                if not self.tentar_recuperar_sessao():
                    if tentativa == max_tentativas:
                        raise WebDriverException(f"Problemas persistentes: {', '.join(problemas)}")
                    continue
            
            try:
                resultado = operacao()
                
                estado_pos = self.verificar_estado_aplicacao_sefaz()
                if not estado_pos['sessao_ativa']:
                    logger.warning(f"Sessão perdida após {nome_operacao}")
                    if tentativa < max_tentativas and self.tentar_recuperar_sessao():
                        continue
                    else:
                        raise WebDriverException("Sessão perdida durante operação")
                
                return resultado
                
            except WebDriverException as e:
                logger.warning(f"Erro de driver em {nome_operacao}: {e}")
                if tentativa == max_tentativas:
                    raise
                
                if not self.tentar_recuperar_sessao():
                    time.sleep(2)  
    
    def obter_estatisticas(self) -> Dict:
        """Retorna estatísticas de health check"""
        return self.estatisticas.copy()
    
    def obter_relatorio_saude(self) -> Dict:
        """Retorna relatório detalhado de saúde"""
        estado = self.verificar_estado_aplicacao_sefaz()
        return {
            'estado_aplicacao': estado,
            'estatisticas': self.estatisticas,
            'timestamp': time.time()
        }