"""
Automação SEFAZ - Download XML NFe
"""

import time
import logging
from typing import List, Optional

from datetime import datetime

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from ..config.config_manager import SEFAZConfig
from .driver_manager import GerenciadorDriver
from ..config.constants import SELECTORS, TIMEOUTS, SEFAZ_LOGIN_URL, SEFAZ_DASHBOARD_URL, SEFAZ_ACESSO_RESTRITO_URL
from .fluxo_utils import DetectorMudancas, GerenciadorWaitInteligente, VerificadorEstado

from .retry_manager import gerenciador_retry
from .download_manager import GerenciadorDownload

logger = logging.getLogger(__name__)

class AutomatorSEFAZ:
    def __init__(self):
        self.gerenciador_driver = GerenciadorDriver()
        self.wait = None
        self.config = None
        self.detector_mudancas = None
        self.wait_inteligente = None
        self.verificador_estado = None
        self.gerenciador_download = None
        
        self.estatisticas_fluxo = {
            'inicio_execucao': None,
            'etapas_executadas': 0,
            'etapas_com_erro': 0,
            'tempos_etapas': {}
        }
        
        self.timeouts = {
            'page_load': 3,
            'element_wait': 8,
            'action_delay': 1,
            'login_wait': 5,
            'popup_wait': 10,
        }
        
        self.etapas_fluxo = [
            ("LOGIN_PORTAL", self._fazer_login_portal, "Login no portal SEFAZ"),
            ("ACESSO_DASHBOARD", self._aguardar_dashboard, "Aguardar dashboard"),
            ("CLICAR_ACESSO_RESTRITO", self._clicar_acesso_restrito, "Clicar em Acesso Restrito"),
            ("ACESSAR_BAIXAR_XML", self._acessar_baixar_xml, "Encontrar e clicar em Baixar XML NFE"),
            ("AGUARDAR_POPUP_LOGIN", self._aguardar_e_preencher_popup, "Aguardar e preencher popup de login"),
            ("CLICAR_BAIXAR_XML_APOS_LOGIN", self._clicar_baixar_xml_apos_login, "Clicar novamente após login"),
            ("PREENCHER_FORMULARIO", self._preencher_formulario_consulta, "Preencher formulário de consulta"),
            ("EXECUTAR_CONSULTA", self._executar_consulta, "Executar pesquisa"),
            ("DOWNLOAD_LOTE", self._download_lote, "Download em lote"),
        ]
    
    def inicializar(self, config: SEFAZConfig) -> bool:
        logger.info("Inicializando automator")
        try:
            self.config = config
            driver = self.gerenciador_driver.configurar_driver()
            if not driver:
                return False
                
            self.wait = WebDriverWait(driver, self.timeouts['element_wait'])
            
            self.detector_mudancas = DetectorMudancas(driver)
            self.wait_inteligente = GerenciadorWaitInteligente(driver)
            self.verificador_estado = VerificadorEstado(driver)
            self.gerenciador_download = GerenciadorDownload(driver)
            
            logger.info("WebDriver e utilitários otimizados configurados")
            
            return True
        except Exception as e:
            logger.error(f"Erro inicializacao: {e}")
            return False
    
    @property
    def driver(self) -> Optional[WebDriver]:
        return self.gerenciador_driver.driver
    
    def executar_fluxo(self) -> bool:
        self.estatisticas_fluxo['inicio_execucao'] = datetime.now()
        logger.info("Iniciando fluxo de automação")
        logger.info(f"Total de etapas: {len(self.etapas_fluxo)}")
        
        try:
            for nome_etapa, funcao_etapa, descricao in self.etapas_fluxo:
                inicio_etapa = datetime.now()
                logger.info(f"Executando etapa: {descricao}")
                
                sucesso_etapa = funcao_etapa()
                tempo_etapa = (datetime.now() - inicio_etapa).total_seconds()
                
                self.estatisticas_fluxo['tempos_etapas'][nome_etapa] = tempo_etapa
                
                if not sucesso_etapa:
                    self.estatisticas_fluxo['etapas_com_erro'] += 1
                    logger.error(f"Falha na etapa: {nome_etapa} ({tempo_etapa:.1f}s)")
                    self._log_estatisticas_parciais()
                    return False
                
                self.estatisticas_fluxo['etapas_executadas'] += 1
                logger.info(f"Etapa concluída: {tempo_etapa:.1f}s")
            
            self._log_estatisticas_finais()
            return True
            
        except Exception as e:
            logger.error(f"Erro não esperado no fluxo: {e}")
            self._log_estatisticas_parciais()
            return False

    def _log_estatisticas_parciais(self):
        tempo_total = (datetime.now() - self.estatisticas_fluxo['inicio_execucao']).total_seconds()
        
        logger.info("=" * 50)
        logger.info("ESTATÍSTICAS PARCIAIS - FLUXO INTERROMPIDO")
        logger.info("=" * 50)
        logger.info(f"Tempo total: {tempo_total:.1f}s")
        logger.info(f"Etapas executadas: {self.estatisticas_fluxo['etapas_executadas']}/{len(self.etapas_fluxo)}")
        logger.info(f"Etapas com erro: {self.estatisticas_fluxo['etapas_com_erro']}")
        
        if self.estatisticas_fluxo['tempos_etapas']:
            logger.info("Tempos das etapas concluídas:")
            for etapa, tempo in self.estatisticas_fluxo['tempos_etapas'].items():
                logger.info(f"  {etapa}: {tempo:.1f}s")

    def _log_estatisticas_finais(self):
        tempo_total = (datetime.now() - self.estatisticas_fluxo['inicio_execucao']).total_seconds()
        stats_retry = gerenciador_retry.obter_estatisticas()
        
        logger.info("=" * 50)
        logger.info("ESTATÍSTICAS DA EXECUÇÃO")
        logger.info("=" * 50)
        logger.info(f"Tempo total: {tempo_total:.1f}s")
        logger.info(f"Etapas executadas: {self.estatisticas_fluxo['etapas_executadas']}/{len(self.etapas_fluxo)}")
        logger.info(f"Etapas com erro: {self.estatisticas_fluxo['etapas_com_erro']}")
        
        logger.info("-" * 30)
        logger.info("TEMPOS POR ETAPA:")
        for nome_etapa, funcao_etapa, descricao in self.etapas_fluxo:
            if nome_etapa in self.estatisticas_fluxo['tempos_etapas']:
                tempo = self.estatisticas_fluxo['tempos_etapas'][nome_etapa]
                logger.info(f"  {descricao}: {tempo:.1f}s")
        
        logger.info("-" * 30)
        logger.info("ESTATÍSTICAS DE RETRY:")
        logger.info(f"  Total operações: {stats_retry['total_operacoes']}")
        logger.info(f"  Operações com retry: {stats_retry['operacoes_com_retry']}")
        logger.info(f"  Total tentativas: {stats_retry['total_tentativas']}")
        logger.info(f"  Sucessos após retry: {stats_retry['sucessos_apos_retry']}")
        
        if stats_retry['total_operacoes'] > 0:
            eficiencia = (stats_retry['total_operacoes'] / stats_retry['total_tentativas']) * 100
            logger.info(f"  Eficiência: {eficiencia:.1f}%")
        
        logger.info("=" * 50)
    
    def _mostrar_mensagem_final(self, sucesso: bool, tempo_total: float = 0):
        print("\n" + "="*70)
        if sucesso:
            print("SUCESSO! Fluxo executado")
            print(f"Tempo: {tempo_total:.1f}s")
        else:
            print("FALHA - Verifique o problema")
        print("Navegador mantido aberto")
        print("="*70)
    
    def _fazer_login_portal(self) -> bool:
        logger.info("Fazendo login no portal")
        
        def tentar_login():
            url_anterior = self.driver.current_url
            self.driver.get(SEFAZ_LOGIN_URL)
            
            self.detector_mudancas.aguardar_carregamento()
            
            campo_usuario = self.wait_inteligente.aguardar_elemento_ou_alternativas(
                (By.ID, "username"),
                (By.NAME, "username"),
                (By.XPATH, "//input[@type='text']")
            )
            
            if not campo_usuario:
                campo_usuario = self.driver.find_element(By.ID, "username")
            
            campo_senha = self.wait_inteligente.aguardar_elemento_ou_alternativas(
                (By.ID, "password"), 
                (By.NAME, "password"),
                (By.XPATH, "//input[@type='password']")
            )
            
            if not campo_senha:
                campo_senha = self.driver.find_element(By.ID, "password")
            
            botao_login = self.wait_inteligente.aguardar_elemento_ou_alternativas(
                (By.ID, "btnAuthenticate"),
                (By.XPATH, "//button[contains(text(), 'Entrar')]"),
                (By.XPATH, "//input[@type='submit']")
            )
            
            if not botao_login:
                botao_login = self.driver.find_element(By.ID, "btnAuthenticate")
            
            campo_usuario.clear()
            campo_usuario.send_keys(self.config.usuario)
            campo_senha.clear()
            campo_senha.send_keys(self.config.senha)
            botao_login.click()
            
            time.sleep(self.timeouts['login_wait'])
            
            mudanca, url_atual = self.detector_mudancas.verificar_mudanca_url(url_anterior)
            if mudanca:
                logger.info(f"Mudança de página detectada após login: {url_atual}")
            
            if self.verificador_estado.esta_na_pagina_login():
                logger.warning("Ainda na página de login - possível falha")
            else:
                logger.info("Possível sucesso no login - saiu da página de login")
            
            return True 
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_login,
                max_tentativas=2,
                delay=3,
                nome_operacao="Login Portal"
            )
        except Exception as e:
            logger.error(f"Falha no login: {e}")
            return False
    
    def _aguardar_dashboard(self) -> bool:
        time.sleep(self.timeouts['action_delay'])
        
        if "portalsefaz-apps" not in self.driver.current_url:
            self.driver.get(SEFAZ_DASHBOARD_URL)
            time.sleep(self.timeouts['page_load'])
        
        return True
    
    def _clicar_acesso_restrito(self) -> bool:
        logger.info("Clicando em Acesso Restrito")
        
        def tentar_clicar():
            time.sleep(3)
            self.detector_mudancas.aguardar_carregamento()
            
            link_acesso = self.wait_inteligente.aguardar_elemento_ou_alternativas(
                (By.XPATH, "//h3[contains(text(), 'Acesso Restrito')]"),
                (By.XPATH, "//a[contains(@href, 'NETACCESS/default.asp')]"),
                (By.XPATH, "//a[@target='_blank' and contains(@href, 'NETACCESS')]"),
                (By.XPATH, "//a[contains(@class, 'dashboard-sistemas-item')]"),
                (By.XPATH, "//a[contains(@href, 'NETACCESS') and contains(@title, 'Acessar')]"),
                (By.XPATH, "//h3[contains(text(), 'Acesso Restrito')]/ancestor::a"),
            )
            
            if not link_acesso:
                link_acesso = self.wait_inteligente.buscar_elementos_similares("Acesso Restrito")
                
            if not link_acesso:
                logger.warning("Usando fallback manual para Acesso Restrito")
                for seletor in [
                    (By.XPATH, "//h3[contains(text(), 'Acesso Restrito')]"),
                    (By.XPATH, "//a[contains(@href, 'NETACCESS/default.asp')]"),
                ]:
                    try:
                        link_acesso = self.driver.find_element(*seletor)
                        break
                    except:
                        continue
            
            if not link_acesso:
                raise Exception("Nenhum seletor de acesso restrito funcionou")
            
            aba_original = self.driver.current_window_handle
            self.driver.execute_script("arguments[0].click();", link_acesso)
            time.sleep(5)
            
            abas = self.driver.window_handles
            if len(abas) > 1:
                nova_aba = abas[-1]
                self.driver.switch_to.window(nova_aba)
                logger.info("Mudou para nova aba")
                
                if self.verificador_estado.esta_no_acesso_restrito():
                    logger.info("Acesso restrito verificado com sucesso")
                else:
                    logger.warning("Possivelmente não está no acesso restrito")
            else:
                logger.info("Nenhuma nova aba aberta")
            
            return True
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_clicar,
                max_tentativas=3,
                delay=2,
                nome_operacao="Clicar Acesso Restrito"
            )
        except Exception as e:
            logger.error(f"Falha ao acessar restrito: {e}")
            return False
    
    def _acessar_baixar_xml(self) -> bool:
        logger.info("Acessando iframe e buscando Baixar XML NFE")
        
        def tentar_acessar():
            logger.info("Procurando iframe...")
            
            seletores_iframe = [
                (By.ID, "iNetaccess"),
                (By.NAME, "iNetaccess"),
                (By.XPATH, "//iframe[contains(@src, 'main.asp')]"),
                (By.TAG_NAME, "iframe"),
            ]
            
            iframe_encontrado = None
            for seletor in seletores_iframe:
                try:
                    iframe_encontrado = self.driver.find_element(*seletor)
                    logger.info(f"IFRAME ENCONTRADO: {seletor[1]}")
                    break
                except:
                    continue
            
            if not iframe_encontrado:
                logger.error("IFRAME NAO ENCONTRADO!")
                return False
            
            logger.info("Entrando no iframe...")
            self.driver.switch_to.frame(iframe_encontrado)
            logger.info("Dentro do iframe!")
            
            logger.info("Buscando Baixar XML NFE dentro do iframe...")
            
            seletores_link = [
                (By.XPATH, "//a[@onclick=\"OpenUrl('https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfe/consulta-notas-recebidas', false, '', 'False', 'true')\"]"),
                (By.XPATH, "//a[text()='Baixar XML NFE']"),
                (By.XPATH, "//a[contains(text(), 'Baixar XML NFE')]"),
                (By.XPATH, "//a[contains(@href, 'javascript:void') and contains(text(), 'Baixar XML')]"),
                (By.XPATH, "//a[contains(., 'Baixar XML')]"),
            ]
            
            link_encontrado = None
            for i, seletor in enumerate(seletores_link):
                try:
                    logger.info(f"Tentativa {i+1}: {seletor[1]}")
                    link_encontrado = self.driver.find_element(*seletor)
                    logger.info("LINK ENCONTRADO dentro do iframe!")
                    
                    try:
                        texto = link_encontrado.text
                        onclick = link_encontrado.get_attribute('onclick')
                        logger.info(f"Texto: '{texto}'")
                        logger.info(f"onClick: {onclick}")
                    except:
                        pass
                    
                    break
                except Exception as e:
                    continue
            
            if not link_encontrado:
                logger.error("Link nao encontrado dentro do iframe")
                self.driver.switch_to.default_content()
                return False
            
            logger.info("Clicando no link Baixar XML NFE...")
            try:
                self.driver.execute_script("arguments[0].click();", link_encontrado)
                logger.info("Clicado via JavaScript")
            except Exception as e:
                logger.error(f"Erro ao clicar: {e}")
                self.driver.switch_to.default_content()
                return False
            
            logger.info("Aguardando acao do clique...")
            time.sleep(5)
            
            try:
                current_url = self.driver.current_url
                logger.info(f"URL atual: {current_url}")
                
                if "consulta-notas-recebidas" in current_url:
                    logger.info("REDIRECIONADO PARA PAGINA DE CONSULTA!")
                    return True
                else:
                    logger.info("Permaneceu na mesma pagina - possivelmente popup aberto")
                    return True
                    
            except Exception as e:
                logger.warning(f"Erro ao verificar URL: {e}")
                return True
                
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_acessar,
                max_tentativas=3,
                delay=2,
                nome_operacao="Acessar Baixar XML"
            )
        except Exception as e:
            logger.error(f"Erro critico no acesso ao iframe: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def _aguardar_e_preencher_popup(self) -> bool:
        logger.info("Aguardando popup de login...")
        
        def tentar_popup():
            logger.info("Aguardando ate 15 segundos para popup aparecer...")
            
            for tentativa in range(15):
                if self._verificar_popup_login():
                    logger.info("POPUP DETECTADO! Preenchendo...")
                    return self._preencher_popup_login()
                
                logger.info(f"Aguardando popup... ({tentativa + 1}/15)")
                time.sleep(1)
            
            logger.error("TIMEOUT: Popup de login nao apareceu apos 15 segundos")
            logger.info("Possiveis causas:")
            logger.info(" - O link nao abriu o popup")
            logger.info(" - Popup bloqueado pelo navegador")
            logger.info(" - Necessita de interacao manual")
            return False
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_popup,
                max_tentativas=2,
                delay=2,
                nome_operacao="Aguardar Popup"
            )
        except Exception as e:
            logger.error(f"Erro ao aguardar popup: {e}")
            return False
    
    def _verificar_popup_login(self) -> bool:
        try:
            elementos_popup = [
                (By.ID, "NetAccess.Login"),
                (By.ID, "NetAccess.Password"),
                (By.ID, "btnAuthenticate"),
            ]
            
            for elemento in elementos_popup:
                try:
                    if self.driver.find_element(*elemento):
                        logger.info(f"Elemento de popup encontrado: {elemento[1]}")
                        return True
                except:
                    continue
            
            textos_popup = [
                "Para se autenticar, favor informar suas credenciais",
                "Caro usuario",
                "realize a confirmacao",
            ]
            
            page_source = self.driver.page_source
            for texto in textos_popup:
                if texto in page_source:
                    logger.info(f"Texto de popup encontrado: {texto}")
                    return True
            
            return False
        except:
            return False
    
    def _preencher_popup_login(self) -> bool:
        logger.info("Preenchendo popup de login...")
        
        try:
            campo_cpf = self.driver.find_element(By.ID, "NetAccess.Login")
            campo_cpf.clear()
            campo_cpf.send_keys(self.config.usuario)
            logger.info("CPF preenchido no popup")
            
            campo_senha = self.driver.find_element(By.ID, "NetAccess.Password")
            campo_senha.clear()
            campo_senha.send_keys(self.config.senha)
            logger.info("Senha preenchida no popup")
            
            botao_autenticar = self.driver.find_element(By.ID, "btnAuthenticate")
            botao_autenticar.click()
            logger.info("Clicou em Autenticar no popup")
            
            logger.info("Aguardando processamento do login no popup...")
            time.sleep(5)
            
            if not self._verificar_popup_login():
                logger.info("Login no popup realizado com sucesso!")
                return True
            else:
                logger.error("Falha no login - popup ainda esta aberto")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao preencher popup: {e}")
            return False
    
    def _clicar_baixar_xml_apos_login(self) -> bool:
        logger.info("Clicando novamente em Baixar XML NFE apos login...")
        
        def tentar_clicar_apos_login():
            time.sleep(3)
            
            logger.info("Entrando novamente no iframe apos login...")
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("DENTRO DO IFRAME NOVAMENTE!")
            except Exception as e:
                logger.error(f"Nao conseguiu entrar no iframe apos login: {e}")
                return False
            
            logger.info("Procurando link novamente apos login...")
            
            seletores_link = [
                (By.XPATH, "//a[@onclick=\"OpenUrl('https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfe/consulta-notas-recebidas', false, '', 'False', 'true')\"]"),
                (By.XPATH, "//a[text()='Baixar XML NFE']"),
                (By.XPATH, "//a[contains(text(), 'Baixar XML NFE')]"),
            ]
            
            link_encontrado = None
            for seletor in seletores_link:
                try:
                    link_encontrado = self.driver.find_element(*seletor)
                    logger.info("Link encontrado apos login!")
                    break
                except:
                    continue
            
            if not link_encontrado:
                logger.error("Nao encontrou link apos login")
                self.driver.switch_to.default_content()
                return False
            
            logger.info("Clicando no link apos login...")
            try:
                self.driver.execute_script("arguments[0].click();", link_encontrado)
                logger.info("Clicado via JavaScript apos login")
            except Exception as e:
                logger.error(f"Erro ao clicar apos login: {e}")
                self.driver.switch_to.default_content()
                return False
            
            self.driver.switch_to.default_content()
            logger.info("Aguardando redirecionamento apos segundo clique...")
            time.sleep(5)
            
            current_url = self.driver.current_url
            logger.info(f"URL apos segundo clique: {current_url}")
            
            if "consulta-notas-recebidas" in current_url:
                logger.info("REDIRECIONADO PARA FORMULARIO DE CONSULTA!")
                return True
            else:
                logger.info("Nao redirecionado - possivelmente ja esta na pagina correta")
                return True
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_clicar_apos_login,
                max_tentativas=3,
                delay=2,
                nome_operacao="Clicar Apos Login"
            )
        except Exception as e:
            logger.error(f"Erro no segundo clique: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def _preencher_formulario_consulta(self) -> bool:
        logger.info("Preenchendo formulario dentro do iframe...")
        
        def tentar_preencher():
            time.sleep(3)
            
            logger.info("Entrando no iframe para preencher formulario...")
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("DENTRO DO IFRAME DO FORMULARIO!")
            except Exception as e:
                logger.error(f"Nao conseguiu entrar no iframe do formulario: {e}")
                return False
            
            current_url = self.driver.current_url
            logger.info(f"URL dentro do iframe: {current_url}")
            
            try:
                campo_teste = self.driver.find_element(By.ID, "cmpDataInicial")
                logger.info("FORMULARIO ENCONTRADO DENTRO DO IFRAME!")
            except:
                logger.error("Formulario nao encontrado dentro do iframe")
                self.driver.switch_to.default_content()
                return False
            
            logger.info("Preenchendo campos do formulario...")
            
            try:
                campo_data_inicio = self.driver.find_element(By.ID, "cmpDataInicial")
                campo_data_inicio.clear()
                campo_data_inicio.send_keys(self.config.data_inicio)
                logger.info("Data inicio preenchida")
                
                campo_data_fim = self.driver.find_element(By.ID, "cmpDataFinal")
                campo_data_fim.clear()
                campo_data_fim.send_keys(self.config.data_fim)
                logger.info("Data fim preenchida")
                
                campo_ie = self.driver.find_element(By.ID, "cmpNumIeDest")
                campo_ie.clear()
                campo_ie.send_keys(self.config.inscricao_estadual)
                logger.info("Inscricao estadual preenchida")
                
                seletor_modelo = Select(self.driver.find_element(By.ID, "cmpModelo"))
                seletor_modelo.select_by_value("55")
                logger.info("Modelo selecionado (55 - NFe)")
                
                radio_entrada = self.driver.find_element(By.XPATH, "//input[@value='0' and @name='cmpTipoNota']")
                if not radio_entrada.is_selected():
                    radio_entrada.click()
                    logger.info("Tipo de nota selecionado (Entrada)")
                
                try:
                    checkbox_canceladas = self.driver.find_element(By.ID, "cmpExbNotasCanceladas")
                    if not checkbox_canceladas.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox_canceladas)
                        logger.info("CHECKBOX Exibir notas canceladas MARCADO!")
                    else:
                        logger.info("Checkbox Exibir notas canceladas ja estava marcado")
                except Exception as e:
                    logger.warning(f"Nao conseguiu marcar checkbox de notas canceladas: {e}")
                
                logger.info("FORMULARIO PREENCHIDO COM SUCESSO!")
                
                self.driver.switch_to.default_content()
                
                return self._captcha_manual()
                
            except Exception as e:
                logger.error(f"Erro ao preencher formulario: {e}")
                self.driver.switch_to.default_content()
                return False
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_preencher,
                max_tentativas=2,
                delay=1,
                nome_operacao="Preencher Formulario"
            )
        except Exception as e:
            logger.error(f"Erro critico no formulario: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def _captcha_manual(self) -> bool:
        logger.info("CAPTCHA REQUERIDO")
        
        try:
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            self.driver.switch_to.frame(iframe)
            logger.info("Dentro do iframe para captcha")
        except:
            logger.info("Nao conseguiu entrar no iframe para captcha")
        
        print("\n" + "="*50)
        print("RESOLVA O CAPTCHA NO NAVEGADOR!")
        print("="*50)
        print("1. Resolva o CAPTCHA na janela do Chrome")
        print("2. Aguarde o processamento") 
        print("3. Volte e pressione ENTER")
        print("="*50)
        
        try:
            self.driver.switch_to.default_content()
            
            input("\nENTER apos resolver o CAPTCHA: ")
            logger.info("Captcha resolvido")
            time.sleep(2)
            return True
        except:
            logger.info("Continuando...")
            return True
    
    def _executar_consulta(self) -> bool:
        logger.info("Executando consulta dentro do iframe...")
        
        def tentar_consultar():
            logger.info("Entrando no iframe para executar consulta...")
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("DENTRO DO IFRAME PARA CONSULTA!")
            except Exception as e:
                logger.error(f"Nao conseguiu entrar no iframe: {e}")
                return False
            
            logger.info("Clicando no botao Pesquisar...")
            
            try:
                botao_pesquisar = self.driver.find_element(By.ID, "btnPesquisar")
                logger.info("Botao Pesquisar encontrado!")
                
                botao_pesquisar.click()
                logger.info("CONSULTA EXECUTADA COM SUCESSO!")
                
            except Exception as e:
                logger.error(f"Erro ao clicar no botao: {e}")
                
                logger.info("Tentando seletores alternativos...")
                seletores_alternativos = [
                    (By.XPATH, "//button[contains(text(), 'Pesquisar')]"),
                    (By.XPATH, "//button[@id='btnPesquisar']"),
                    (By.XPATH, "//input[@type='submit']"),
                    (By.XPATH, "//button[@type='submit']"),
                ]
                
                for seletor in seletores_alternativos:
                    try:
                        botao = self.driver.find_element(*seletor)
                        botao.click()
                        logger.info(f"Clicado com seletor alternativo: {seletor[1]}")
                        break
                    except:
                        continue
                else:
                    logger.error("Nenhum seletor alternativo funcionou")
                    self.driver.switch_to.default_content()
                    return False
            
            self.driver.switch_to.default_content()
            logger.info("Aguardando resultados da consulta...")
            time.sleep(8)
            
            return True
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_consultar,
                max_tentativas=3,
                delay=2,
                nome_operacao="Executar Consulta"
            )
        except Exception as e:
            logger.error(f"Erro na execucao da consulta: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
        
    def _download_lote(self) -> bool:
        logger.info("Iniciando download em lote")
        
        try:
            if not self.gerenciador_download:
                logger.error("Gerenciador download não inicializado")
                return False
            
            resultado = self.gerenciador_download.processar_download_lote()
            
            # Log direto e simples
            logger.info(f"Resumo: {resultado.total_baixado}/{resultado.total_encontrado} notas")
            
            if resultado.erros:
                logger.error(f"Erro: {resultado.erros[0]}")
                return False
            
            return resultado.total_baixado > 0
            
        except Exception as e:
            logger.error(f"Erro download lote: {e}")
            return False
    
    def limpar_recursos(self):
        logger.info("Navegador mantido aberto")
        print("\n" + "="*60)
        print("Fluxo concluido - Navegador aberto para inspecao")
        print("="*60)