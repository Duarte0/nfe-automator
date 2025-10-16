"""
Processador consolidado de IEs individuais
"""
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from .retry_manager import gerenciador_retry

logger = logging.getLogger(__name__)

class ProcessadorIE:
    """Consolida toda lógica de processamento de IEs individuais"""
    
    def __init__(self, automator):
        self.automator = automator
        self.driver = automator.driver
        self.config = automator.config
        self.gerenciador_download = automator.gerenciador_download
        
    def processar_ie(self, ie: str) -> bool:
        """Processa uma IE individual de forma consolidada"""
        logger.info(f"Processando IE: {ie}")
        
        # ETAPA 1: Apenas preencher formulário
        if not self._preencher_formulario(ie):
            logger.error("Falha ao preencher formulário")
            return False
        
        # ETAPA 2: Aguardar CAPTCHA manual SEM fazer nada
        if not self._aguardar_captcha_manual():
            logger.error("Falha no CAPTCHA")
            return False
        
        # ETAPA 3: Executar consulta APÓS CAPTCHA resolvido
        if not self._executar_consulta(ie):
            logger.error("Falha na consulta")
            return False
        
        # ETAPA 4: Validar resultados
        if not self._validar_resultados(ie):
            logger.error("Falha na validação")
            return False
        
        # Processar download apenas se houver notas
        total_notas = self.gerenciador_download.contar_notas_tabela()
        if total_notas > 0:
            logger.info(f"Encontradas {total_notas} notas - executando download")
            return self._processar_download(ie)
        else:
            logger.info(f"Nenhuma nota encontrada para IE {ie}")
            return False
    
    def _preencher_formulario(self, ie: str) -> bool:
        """Apenas preenche formulário - NÃO clica em nada"""
        def tentar_preencher():
            time.sleep(2)
            
            try:
                self.driver.switch_to.default_content()
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                
                # Preencher campos
                campos = {
                    "cmpDataInicial": self.config.data_inicio,
                    "cmpDataFinal": self.config.data_fim, 
                    "cmpNumIeDest": ie
                }
                
                for campo_id, valor in campos.items():
                    elemento = self.driver.find_element(By.ID, campo_id)
                    elemento.clear()
                    elemento.send_keys(valor)
                
                # Configurações adicionais
                seletor_modelo = Select(self.driver.find_element(By.ID, "cmpModelo"))
                seletor_modelo.select_by_value("-")
                
                try:
                    checkbox = self.driver.find_element(By.ID, "cmpExbNotasCanceladas")
                    if not checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                except:
                    pass
                
                logger.info("Formulário preenchido - aguardando CAPTCHA manual")
                self.driver.switch_to.default_content()
                return True
                
            except Exception as e:
                logger.error(f"Erro preencher formulário: {e}")
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False
        
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
        """Executa consulta APÓS CAPTCHA resolvido"""
        def tentar_consultar():
            try:
                # Entrar no iframe para executar consulta
                self.driver.switch_to.default_content()
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                
                # Verificar se o formulário ainda está preenchido
                try:
                    campo_ie = self.driver.find_element(By.ID, "cmpNumIeDest")
                    if campo_ie.get_attribute("value") != ie:
                        logger.warning("IE não preenchida - preenchendo novamente")
                        campo_ie.clear()
                        campo_ie.send_keys(ie)
                except:
                    logger.error("Campo IE não encontrado")
                    self.driver.switch_to.default_content()
                    return False
                
                # AGORA SIM clicar no botão Pesquisar
                logger.info("Executando consulta...")
                botao_pesquisar = self.driver.find_element(By.ID, "btnPesquisar")
                botao_pesquisar.click()
                
                self.driver.switch_to.default_content()
                time.sleep(8)  # Aguardar resultados
                return True
                
            except Exception as e:
                logger.error(f"Erro executar consulta: {e}")
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False
        
        return gerenciador_retry.executar_com_retry(
            tentar_consultar, max_tentativas=2, nome_operacao="Executar Consulta"
        )
    
    def _validar_resultados(self, ie: str) -> bool:
        """Valida resultados da consulta"""
        try:
            total_notas = self.gerenciador_download.contar_notas_tabela()
            logger.info(f"Consulta retornou {total_notas} notas para IE {ie}")
            return True
        except Exception as e:
            logger.error(f"Erro validar resultados: {e}")
            return False
    
    def _processar_download(self, ie: str) -> bool:
        """Processa download das notas"""
        try:
            from datetime import datetime
            data_referencia = datetime.strptime(self.config.data_inicio, "%d/%m/%Y")
            
            resultado = self.gerenciador_download.executar_fluxo_download_completo(ie, data_referencia)
            
            if resultado.total_baixado > 0:
                logger.info(f"Download concluído: {resultado.total_baixado} arquivo(s)")
                self._voltar_pagina_consulta()
                return True
            else:
                logger.warning("Download não gerou arquivos")
                return False
                
        except Exception as e:
            logger.error(f"Erro processar download: {e}")
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