"""
Processador consolidado de IEs individuais
"""
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from .retry_manager import gerenciador_retry
from .iframe_manager import GerenciadorIframe
from selenium.webdriver.common.keys import Keys

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
            return False
        
        total_notas = self.gerenciador_download.contar_notas_tabela()
        if total_notas > 0:
            return self._processar_download(ie)
        else:
            return False
    
    def _preencher_formulario(self, ie: str) -> bool:
        def tentar_preencher():
            time.sleep(2)
            
            with self.gerenciador_iframe.contexto_iframe((By.ID, "iNetaccess")):
                # Preencher datas primeiro - método específico para campos com máscara
                if not self._preencher_data_com_mascara("cmpDataInicial", self.config.data_inicio):
                    return False
                    
                if not self._preencher_data_com_mascara("cmpDataFinal", self.config.data_fim):
                    return False
                
                # Preencher IE (campo normal)
                try:
                    campo_ie = self.driver.find_element(By.ID, "cmpNumIeDest")
                    campo_ie.clear()
                    time.sleep(0.3)
                    campo_ie.send_keys(ie)
                    
                    # Verificar se IE foi preenchido
                    if campo_ie.get_attribute("value") != ie:
                        self.driver.execute_script(f"arguments[0].value = '{ie}';", campo_ie)
                        
                except Exception as e:
                    logger.error(f"Erro ao preencher IE: {e}")
                    return False
                
                # Configurações adicionais
                seletor_modelo = Select(self.driver.find_element(By.ID, "cmpModelo"))
                seletor_modelo.select_by_value("-")
                
                try:
                    checkbox = self.driver.find_element(By.ID, "cmpExbNotasCanceladas")
                    if not checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                except:
                    pass
                
                return True
        
        return gerenciador_retry.executar_com_retry(
            tentar_preencher, max_tentativas=2, nome_operacao="Preencher Formulário"
        )

    def _preencher_data_com_mascara(self, campo_id: str, data_str: str) -> bool:
        """Preenche campo de data com máscara usando múltiplas estratégias"""
        data_formatada = self._validar_e_formatar_data(data_str)
        
        for tentativa, metodo in enumerate([
            self._preencher_data_javascript,
            self._preencher_data_sequencial, 
            self._preencher_data_backspace
        ], 1):
            if metodo(campo_id, data_formatada):
                # Verificar se preencheu corretamente
                if self._verificar_data_preenchida(campo_id, data_formatada):
                    return True
                else:
                    logger.warning(f"Campo {campo_id} não validado na tentativa {tentativa}")
            
            time.sleep(1)
        
        logger.error(f"Todas as tentativas falharam para {campo_id}")
        return False

    def _preencher_data_javascript(self, campo_id: str, data: str) -> bool:
        """Preenche data via JavaScript - ignora máscara"""
        try:
            elemento = self.driver.find_element(By.ID, campo_id)
            self.driver.execute_script(f"arguments[0].value = '{data}';", elemento)
            return True
        except:
            return False

    def _preencher_data_sequencial(self, campo_id: str, data: str) -> bool:
        """Preenche data digitando caracter por caracter"""
        try:
            elemento = self.driver.find_element(By.ID, campo_id)
            elemento.click()  # Focar no campo
            elemento.clear()  # Limpar primeiro
            
            # Digitar cada caractere com pequeno delay
            for char in data:
                elemento.send_keys(char)
                time.sleep(0.1)
                
            return True
        except:
            return False

    def _preencher_data_backspace(self, campo_id: str, data: str) -> bool:
        """Limpa campo com Backspace e depois preenche"""
        try:
            elemento = self.driver.find_element(By.ID, campo_id)
            
            # Limpar com Backspace
            elemento.click()
            for _ in range(10):  # Limpar completamente
                elemento.send_keys(Keys.BACKSPACE)
                time.sleep(0.05)
            
            time.sleep(0.5)
            
            # Preencher nova data
            for char in data:
                elemento.send_keys(char)
                time.sleep(0.1)
                
            return True
        except:
            return False

    def _verificar_data_preenchida(self, campo_id: str, data_esperada: str) -> bool:
        """Verifica se a data foi preenchida corretamente"""
        try:
            elemento = self.driver.find_element(By.ID, campo_id)
            valor_obtido = elemento.get_attribute("value") or ""
            
            # Verificar se não está vazio e contém a data esperada
            return valor_obtido and data_esperada in valor_obtido
        except:
            return False

    def _validar_e_formatar_data(self, data_str: str) -> str:
        """Valida e formata data no padrão DD/MM/AAAA"""
        try:
            from datetime import datetime
            
            # Converter e validar data
            data_obj = datetime.strptime(data_str, "%d/%m/%Y")
            
            # Retornar no formato correto
            return data_obj.strftime("%d/%m/%Y")
            
        except ValueError as e:
            logger.error(f"Data inválida: {data_str} - {e}")
            # Fallback: usar data atual se a config estiver inválida
            from datetime import datetime
            data_fallback = datetime.now().strftime("%d/%m/%Y")
            logger.warning(f"Usando fallback: {data_fallback}")
            return data_fallback
        
    def _aguardar_captcha_manual(self) -> bool:
        """Aguarda resolução manual com verificação opcional"""
        logger.info("Aguardando resolução manual do CAPTCHA")
        
        print("\n" + "="*50)
        print("RESOLUÇÃO MANUAL DO CAPTCHA")
        print("="*50)
        print("1. Resolva o CAPTCHA no navegador")
        print("2. Aguarde processamento completo")
        print("3. Pressione ENTER quando concluído")
        print("="*50)
        
        try:
            input("Pressione ENTER após resolver o CAPTCHA: ")
            time.sleep(2)
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
            except:
                pass
            
            self.driver.switch_to.default_content()
            return True
            
        except Exception:
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return True