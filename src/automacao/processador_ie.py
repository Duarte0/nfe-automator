"""
Processador consolidado de IEs individuais
"""
import logging
import time
from typing import Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from .timeout_manager import TipoOperacao

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
        self.gerenciador_estado = None
        if hasattr(automator, 'gerenciador_multi_ie'):
            self.gerenciador_estado = automator.gerenciador_multi_ie
        
    def processar_ie(self, ie: str, nome_empresa: str = "") -> bool:
        """Processa uma IE individual com suporte a checkpoints e health check"""
        logger.info(f"Processando IE: {ie} - Empresa: {nome_empresa}")
        
        empresa = {'ie': ie, 'nome': nome_empresa}
        
        if hasattr(self.automator, 'health_check') and self.automator.health_check:
            def operacao_completa():
                estado_anterior = self._verificar_estado_anterior(ie)
                if estado_anterior:
                    return self._retomar_processamento(empresa, estado_anterior)
                return self._executar_fluxo_com_checkpoints(empresa)
                
            return self.automator.health_check.executar_com_verificacao(
                operacao_completa, f"Processar IE {ie}", max_tentativas=2
            )
        else:
            estado_anterior = self._verificar_estado_anterior(ie)
            if estado_anterior:
                return self._retomar_processamento(empresa, estado_anterior)
            return self._executar_fluxo_com_checkpoints(empresa)
    
    def _verificar_estado_anterior(self, ie: str) -> Optional[Dict]:
        """Verifica se existe estado anterior para retomada"""
        if not self.gerenciador_estado:
            return None
            
        try:
            sessoes_interrompidas = self.gerenciador_estado.recuperar_sessao_interrompida()
            for sessao in sessoes_interrompidas:
                if sessao['ie'] == ie:
                    logger.info(f"Encontrado estado anterior para {ie}: {sessao['etapa']} ({sessao['progresso']}%)")
                    return sessao
            return None
        except Exception as e:
            logger.error(f"Erro ao verificar estado anterior: {e}")
            return None
        
    def _retomar_processamento(self, empresa: Dict, estado_anterior: Dict) -> bool:
        """Retoma o processamento de onde parou"""
        ie = empresa['ie']
        etapa = estado_anterior['etapa']
        progresso = estado_anterior['progresso']
        
        logger.info(f"Retomando processamento de {ie} da etapa: {etapa}")
        
        retomadas = {
            'formulario': self._retomar_formulario,
            'captcha': self._retomar_captcha, 
            'consulta': self._retomar_consulta,
            'download': self._retomar_download,
            'validacao': self._retomar_validacao
        }
        
        if etapa in retomadas:
            return retomadas[etapa](empresa, estado_anterior)
        else:
            logger.warning(f"Etapa {etapa} não suporta retomada, reiniciando...")
            return self._executar_fluxo_com_checkpoints(empresa)
    
    def _retomar_formulario(self, empresa: Dict, estado_anterior: Dict) -> bool:
        """Retoma da etapa de formulário"""
        logger.info(f"Retomando formulário para {empresa['ie']}")
        return self._executar_fluxo_com_checkpoints(empresa)  # Reinicia do formulário
    
    def _retomar_captcha(self, empresa: Dict, estado_anterior: Dict) -> bool:
        """Retoma da etapa de CAPTCHA"""
        logger.info(f"Retomando CAPTCHA para {empresa['ie']}")
        self._criar_checkpoint(empresa, "captcha", 40)
        return self._executar_desde_captcha(empresa)
    
    def _retomar_consulta(self, empresa: Dict, estado_anterior: Dict) -> bool:
        """Retoma da etapa de consulta"""
        logger.info(f"Retomando consulta para {empresa['ie']}")
        self._criar_checkpoint(empresa, "consulta", 60)
        return self._executar_desde_consulta(empresa)
    
    def _retomar_validacao(self, empresa: Dict, estado_anterior: Dict) -> bool:
        """Retoma da etapa de validação"""
        logger.info(f"Retomando validação para {empresa['ie']}")
        self._criar_checkpoint(empresa, "validacao", 70)
        return self._executar_desde_validacao(empresa)
        
    def _retomar_download(self, empresa: Dict, estado_anterior: Dict) -> bool:
        """Retoma o processo na etapa de download"""
        ie = empresa['ie']
        logger.info(f"Retomando download para {ie}")
        
        try:
            if not self._validar_resultados(ie):
                logger.warning("Resultados não encontrados na retomada, reiniciando...")
                return self._executar_fluxo_com_checkpoints(empresa)
            
            return self._processar_download(ie, empresa['nome'])
            
        except Exception as e:
            logger.error(f"Erro na retomada do download: {e}")
            return self._executar_fluxo_com_checkpoints(empresa)
    
    def _executar_desde_captcha(self, empresa: Dict) -> bool:
        """Executa fluxo a partir do CAPTCHA"""
        ie = empresa['ie']
        
        self._criar_checkpoint(empresa, "captcha", 40)
        if not self._aguardar_captcha_manual():
            self._rollback_etapa(empresa, "formulario", "Falha no CAPTCHA")
            return False
        
        return self._executar_desde_consulta(empresa)
    
    def _executar_desde_consulta(self, empresa: Dict) -> bool:
        """Executa fluxo a partir da consulta"""
        ie = empresa['ie']
        
        self._criar_checkpoint(empresa, "consulta", 60)
        if not self._executar_consulta(ie):
            self._rollback_etapa(empresa, "captcha", "Falha na consulta")
            return False
        
        return self._executar_desde_validacao(empresa)
    
    def _executar_desde_validacao(self, empresa: Dict) -> bool:
        """Executa fluxo a partir da validação"""
        ie = empresa['ie']
        
        self._criar_checkpoint(empresa, "validacao", 70)
        if not self._validar_resultados(ie):
            logger.info("Nenhuma nota encontrada")
            self._criar_checkpoint(empresa, "concluido", 100, total_notas=0)
            return False
        
        total_notas = self.gerenciador_download.tem_notas_tabela()
        self._criar_checkpoint(empresa, "download", 80, total_notas=total_notas)
        
        if total_notas > 0:
            sucesso = self._processar_download(ie, empresa['nome'])
            if sucesso:
                self._criar_checkpoint(empresa, "concluido", 100, total_notas=total_notas)
            return sucesso
        else:
            self._criar_checkpoint(empresa, "concluido", 100, total_notas=0)
            return False
        
    def _executar_fluxo_com_checkpoints(self, empresa: Dict) -> bool:
        """Fluxo principal com checkpoints em cada etapa"""
        try:
            ie = empresa['ie']
            
            self._criar_checkpoint(empresa, "formulario", 20)
            if not self._preencher_formulario(ie):
                self._rollback_etapa(empresa, "inicio", "Falha no formulário")
                return False
            
            return self._executar_desde_captcha(empresa)
                
        except Exception as e:
            logger.error(f"Erro não esperado no fluxo: {e}")
            self._rollback_etapa(empresa, "inicio", f"Erro não esperado: {e}")
            return False
        
    def _criar_checkpoint(self, empresa: Dict, etapa: str, progresso: int, total_notas: int = None):
        """Wrapper para criar checkpoint"""
        if self.gerenciador_estado:
            dados_sessao = {
                'url_atual': self.driver.current_url,
                'titulo': self.driver.title
            }
            
            if total_notas is not None:
                total_notas_int = int(total_notas) 
            else:
                total_notas_int = None
                
            self.gerenciador_estado.criar_checkpoint(
                empresa, etapa, progresso, dados_sessao, total_notas_int, 0
            )

    def _rollback_etapa(self, empresa: Dict, etapa_anterior: str, motivo: str):
        """Wrapper para rollback"""
        if self.gerenciador_estado:
            self.gerenciador_estado.rollback_etapa(empresa, etapa_anterior, motivo)

    def _preencher_formulario(self, ie: str) -> bool:
        inicio = time.time()
        sucesso = False
        
        def tentar_preencher():
            nonlocal sucesso
            time.sleep(2)
            
            with self.gerenciador_iframe.contexto_iframe((By.ID, "iNetaccess")):
                if not self._preencher_data_com_mascara("cmpDataInicial", self.config.data_inicio):
                    return False
                    
                if not self._preencher_data_com_mascara("cmpDataFinal", self.config.data_fim):
                    return False
                
                try:
                    campo_ie = self.driver.find_element(By.ID, "cmpNumIeDest")
                    campo_ie.clear()
                    time.sleep(0.3)
                    campo_ie.send_keys(ie)
                    
                    if campo_ie.get_attribute("value") != ie:
                        self.driver.execute_script(f"arguments[0].value = '{ie}';", campo_ie)
                        
                except Exception as e:
                    logger.error(f"Erro ao preencher IE: {e}")
                    return False
                
                seletor_modelo = Select(self.driver.find_element(By.ID, "cmpModelo"))
                seletor_modelo.select_by_value("-")
                
                try:
                    checkbox = self.driver.find_element(By.ID, "cmpExbNotasCanceladas")
                    if not checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                except:
                    pass
                
                sucesso = True
                return True
        
        try:
            resultado = gerenciador_retry.executar_com_retry(
                tentar_preencher, max_tentativas=2, nome_operacao="Preencher Formulário"
            )
            return resultado
        finally:
            tempo_decorrido = time.time() - inicio
            if hasattr(self, 'automator') and hasattr(self.automator, 'timeout_manager'):
                self.automator.timeout_manager.registrar_tempo_operacao(
                    TipoOperacao.CONSULTA, tempo_decorrido, sucesso
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
            elemento.click() 
            elemento.clear()  
            
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
            
            elemento.click()
            for _ in range(10):
                elemento.send_keys(Keys.BACKSPACE)
                time.sleep(0.05)
            
            time.sleep(0.5)
            
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
        """Verifica se existe pelo menos uma nota"""
        tem_notas = self.gerenciador_download.tem_notas_tabela()
        logger.info(f"Notas encontradas para IE {ie}: {'SIM' if tem_notas else 'NÃO'}")
        return tem_notas
    
    def _processar_download(self, ie: str, nome_empresa: str) -> bool:
        try:
            logger.info(f"=== INICIANDO DOWNLOAD: {nome_empresa} ({ie}) ===")
            from datetime import datetime
            data_referencia = datetime.strptime(self.config.data_inicio, "%d/%m/%Y")
            
            resultado = self.gerenciador_download.executar_fluxo_download_completo(nome_empresa, data_referencia)
            logger.info(f"=== RESULTADO DOWNLOAD: {resultado.total_baixado}/{resultado.total_encontrado} arquivos ===")
            logger.info(f"=== ERROS: {resultado.erros} ===")
            
            if resultado.total_baixado > 0:
                self._voltar_pagina_consulta()
                return True
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