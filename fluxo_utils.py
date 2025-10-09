"""
Utilitários para otimização do fluxo SEFAZ
"""

import time
import logging
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


class DetectorMudancas:
    """Detecta mudanças na interface do SEFAZ."""
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
    
    def aguardar_carregamento(self, timeout=10):
        """Aguarda até que a página esteja carregada."""
        logger.debug("Aguardando carregamento da página...")
        
        try:
            # Aguardar até que o documento esteja pronto
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            logger.debug("Página carregada com sucesso")
            return True
            
        except Exception as e:
            logger.warning(f"Carregamento da página pode estar incompleto: {e}")
            return True  # Continua mesmo com warning
    
    def verificar_mudanca_url(self, url_anterior):
        """Verifica se a URL mudou significativamente."""
        url_atual = self.driver.current_url
        mudanca = url_atual != url_anterior
        
        if mudanca:
            logger.debug(f"Mudança de URL detectada: {url_anterior} -> {url_atual}")
        
        return mudanca, url_atual


class GerenciadorWaitInteligente:
    """Wait conditions mais inteligentes para SEFAZ."""
    
    def __init__(self, driver: WebDriver, timeout=10):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)
    
    def aguardar_elemento_ou_alternativas(self, *seletores):
        """Aguarda por um elemento ou tenta alternativas."""
        for seletor in seletores:
            try:
                logger.debug(f"Tentando seletor: {seletor}")
                elemento = self.wait.until(EC.presence_of_element_located(seletor))
                logger.debug(f"Elemento encontrado com: {seletor}")
                return elemento
            except:
                continue
        
        # Se nenhum seletor funcionar, loga warning mas não falha
        logger.warning("Nenhum seletor principal funcionou, usando fallback...")
        return None
    
    def buscar_elementos_similares(self, texto):
        """Busca elementos com texto similar."""
        try:
            elementos = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{texto}')]")
            if elementos:
                logger.info(f"Encontrados {len(elementos)} elementos com texto: '{texto}'")
                return elementos[0]  # Retorna o primeiro
        except:
            pass
        return None


class VerificadorEstado:
    """Verifica o estado entre etapas do fluxo."""
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
    
    def esta_na_pagina_login(self):
        """Verifica se está na página de login."""
        url = self.driver.current_url.lower()
        return any(texto in url for texto in ["login", "auth", "autenticacao"])
    
    def esta_logado(self):
        """Verifica se o usuário está logado (método simples)."""
        try:
            # Verifica se não está mais na página de login
            if not self.esta_na_pagina_login():
                logger.debug("Possivelmente logado - não está mais na página de login")
                return True
            
            # Verifica elementos de erro de login
            elementos_erro = [
                "//*[contains(text(), 'inválido')]",
                "//*[contains(text(), 'incorreto')]",
                "//*[contains(text(), 'erro')]",
            ]
            
            for elemento in elementos_erro:
                if self.driver.find_elements(By.XPATH, elemento):
                    logger.warning("Elemento de erro de login encontrado")
                    return False
            
            return False
        except:
            return False
    
    def esta_no_acesso_restrito(self):
        """Verifica se está na área de acesso restrito."""
        url = self.driver.current_url.lower()
        return "netaccess" in url
    
    def esta_no_formulario_consulta(self):
        """Verifica se está no formulário de consulta."""
        url = self.driver.current_url.lower()
        return "consulta-notas-recebidas" in url