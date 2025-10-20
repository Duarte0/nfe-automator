"""
Processador consolidado de IEs individuais
"""
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from .retry_manager import gerenciador_retry
from .iframe_manager import GerenciadorIframe

logger = logging.getLogger(__name__)

class ProcessadorIE:
    """Consolida toda lógica de processamento de IEs individuais"""
    
    def __init__(self, automator):
        self.automator = automator
        self.driver = automator.driver
        self.config = automator.config
        self.gerenciador_download = automator.gerenciador_download
        self.gerenciador_iframe = GerenciadorIframe(automator.driver)
        
    def processar_ie(self, ie: str) -> bool:
        """Processa uma IE individual de forma consolidada"""
        logger.info(f"Processando IE: {ie}")
        
        # Usar health check se disponível
        if hasattr(self.automator, 'health_check') and self.automator.health_check:
            def operacao_completa():
                return self._executar_fluxo_ie(ie)
            
            return self.automator.health_check.executar_com_verificacao(
                operacao_completa, f"Processar IE {ie}", max_tentativas=2
            )
        else:
            # Fallback para fluxo normal
            return self._executar_fluxo_ie(ie)
        
    def _executar_fluxo_ie(self, ie: str) -> bool:
        """Fluxo principal de processamento de IE"""
        if not self._preencher_formulario(ie):
            logger.error("Falha ao preencher formulário")
            return False
        
        if not self._aguardar_captcha_manual():
            logger.error("Falha no CAPTCHA")
            return False
        
        if not self._executar_consulta(ie):
            logger.error("Falha na consulta")
            return False
        
        if not self._validar_resultados(ie):
            logger.error("Falha na validação")
            return False
        
        total_notas = self.gerenciador_download.contar_notas_tabela()
        if total_notas > 0:
            logger.info(f"Encontradas {total_notas} notas - executando download")
            return self._processar_download(ie)
        else:
            logger.info(f"Nenhuma nota encontrada para IE {ie}")
            return False
    
    def _preencher_formulario(self, ie: str) -> bool:
        def tentar_preencher():
            time.sleep(2)
            
            with self.gerenciador_iframe.contexto_iframe((By.ID, "iNetaccess")):
                campos = {
                    "cmpDataInicial": self.config.data_inicio,
                    "cmpDataFinal": self.config.data_fim, 
                    "cmpNumIeDest": ie
                }
                
                for campo_id, valor in campos.items():
                    elemento = self.driver.find_element(By.ID, campo_id)
                    elemento.clear()
                    elemento.send_keys(valor)
                
                seletor_modelo = Select(self.driver.find_element(By.ID, "cmpModelo"))
                seletor_modelo.select_by_value("-")
                
                try:
                    checkbox = self.driver.find_element(By.ID, "cmpExbNotasCanceladas")
                    if not checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                except:
                    pass
                
                logger.info("Formulário preenchido - aguardando CAPTCHA manual")
                return True
        
        return gerenciador_retry.executar_com_retry(
            tentar_preencher, max_tentativas=2, nome_operacao="Preencher Formulário"
        )
    
    def _aguardar_captcha_manual(self) -> bool:
        """APENAS aguarda resolução manual do CAPTCHA - NÃO faz nada"""
        logger.info("AGUARDANDO RESOLUÇÃO MANUAL DO CAPTCHA")
        
        print("\n" + "="*70)
        print("CAPTCHA REQUERIDO - RESOLUÇÃO MANUAL")
        print("="*70)
        print("INSTRUÇÕES:")
        print("1. RESOLVA o CAPTCHA no navegador AGORA")
        print("2. NÃO clique em Pesquisar ainda")
        print("3. Aguarde o processamento completo do CAPTCHA")
        print("4. A página deve recarregar automaticamente")
        print("5. SÓ DEPOIS pressione ENTER aqui")
        print("="*70)
        print("O programa está AGUARDANDO...")
        print("="*70)
        
        try:
            input("Pressione ENTER APÓS resolver o CAPTCHA no navegador: ")
            time.sleep(3)  # Aguardar processamento
            logger.info("CAPTCHA resolvido - continuando fluxo")
            return True
            
        except Exception as e:
            logger.error(f"Erro no CAPTCHA manual: {e}")
            return False
    
    def _executar_consulta(self, ie: str) -> bool:
        def tentar_consultar():
            with self.gerenciador_iframe.contexto_iframe((By.ID, "iNetaccess")):
                try:
                    campo_ie = self.driver.find_element(By.ID, "cmpNumIeDest")
                    if campo_ie.get_attribute("value") != ie:
                        logger.warning("IE não preenchida - preenchendo novamente")
                        campo_ie.clear()
                        campo_ie.send_keys(ie)
                except:
                    logger.error("Campo IE não encontrado")
                    return False
                
                logger.info("Executando consulta...")
                botao_pesquisar = self.driver.find_element(By.ID, "btnPesquisar")
                botao_pesquisar.click()
                return True
        
        return gerenciador_retry.executar_com_retry(
            tentar_consultar, max_tentativas=2, nome_operacao="Executar Consulta"
        )
    
    def _validar_resultados(self, ie: str) -> bool:
        """Verifica apenas se existe pelo menos uma nota"""
        try:
            total_notas = self.gerenciador_download.contar_notas_tabela()
            return total_notas > 0  # Só importa se tem pelo menos 1
        except Exception:
            return False

    def _processar_download(self, ie: str) -> bool:
        """Processa download - só importa se conseguiu baixar"""
        try:
            from datetime import datetime
            data_referencia = datetime.strptime(self.config.data_inicio, "%d/%m/%Y")
            
            resultado = self.gerenciador_download.executar_fluxo_download_completo(ie, data_referencia)
            
            if resultado.total_baixado > 0:
                self._voltar_pagina_consulta()
                return True
            return False
        except Exception:
            return False
        
    def _voltar_pagina_consulta(self) -> bool:
        """Volta para página de consulta"""
        try:
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            self.driver.switch_to.frame(iframe)
            
            try:
                botao_nova_consulta = self.driver.find_element(
                    By.XPATH, "//button[contains(text(), 'Nova Consulta')]"
                )
                if botao_nova_consulta.is_displayed():
                    botao_nova_consulta.click()
                    time.sleep(2)
                    logger.info("Voltou para página de consulta")
            except:
                logger.info("Já está na página de consulta")
            
            self.driver.switch_to.default_content()
            return True
            
        except Exception as e:
            logger.debug(f"Não foi necessário voltar: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return True