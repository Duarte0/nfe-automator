"""
Automação SEFAZ - Download XML NFe
"""

import time
import logging
from typing import List, Optional, Dict

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
from .multi_ie_manager import GerenciadorMultiplasIEs
from .ie_processor import ProcessadorPlanilhaIEs

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
        self.seletor_baixar_xml_cache = None
        self.processador_ies = ProcessadorPlanilhaIEs()
        
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
            ("PROCESSAR_MULTIPLAS_IES", self._processar_multiplas_ies, "Processar todas as IEs"),
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
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("Dentro do iframe!")
            except:
                logger.error("IFRAME NAO ENCONTRADO!")
                return False
            
            logger.info("Buscando Baixar XML NFE...")
            
            # USAR MÉTODO PRIORITÁRIO
            link_encontrado = self._encontrar_link_baixar_xml()
            
            if not link_encontrado:
                logger.error("Link nao encontrado dentro do iframe")
                self.driver.switch_to.default_content()
                return False
            
            logger.info("Clicando no link...")
            try:
                self.driver.execute_script("arguments[0].click();", link_encontrado)
                logger.info("Clicado via JavaScript")
            except Exception as e:
                logger.error(f"Erro ao clicar: {e}")
                self.driver.switch_to.default_content()
                return False
            
            logger.info("Aguardando acao do clique...")
            time.sleep(5)
            
            # Verificar se redirecionou
            try:
                current_url = self.driver.current_url
                if "consulta-notas-recebidas" in current_url:
                    logger.info("REDIRECIONADO PARA PAGINA DE CONSULTA!")
                    return True
                else:
                    logger.info("Permaneceu na mesma pagina")
                    return True
            except:
                return True
        
        return gerenciador_retry.executar_com_retry(
            tentar_acessar,
            max_tentativas=3,
            delay=2,
            nome_operacao="Acessar Baixar XML"
        )
    
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
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
            except:
                return False
            
            # USAR MÉTODO PRIORITÁRIO
            link_encontrado = self._encontrar_link_baixar_xml()
            
            if not link_encontrado:
                self.driver.switch_to.default_content()
                return False
            
            try:
                self.driver.execute_script("arguments[0].click();", link_encontrado)
            except:
                self.driver.switch_to.default_content()
                return False
            
            self.driver.switch_to.default_content()
            time.sleep(5)
            return True
        
        return gerenciador_retry.executar_com_retry(
            tentar_clicar_apos_login,
            max_tentativas=3,
            delay=2,
            nome_operacao="Clicar Apos Login"
        )
        
    def _encontrar_link_baixar_xml(self):
        if self.seletor_baixar_xml_cache:
            try:
                elemento = self.driver.find_element(*self.seletor_baixar_xml_cache)
                logger.info(f"Usando seletor em cache: {self.seletor_baixar_xml_cache[1]}")
                return elemento
            except:
                self.seletor_baixar_xml_cache = None 
        
        seletores_prioridade = [
            (By.XPATH, "//a[@onclick=\"OpenUrl('https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfe/consulta-notas-recebidas', false, '', 'False', 'true')\"]"),
            (By.XPATH, "//a[text()='Baixar XML NFE']"),
            (By.XPATH, "//a[contains(text(), 'Baixar XML NFE')]"),
        ]
        
        for seletor in seletores_prioridade:
            try:
                elemento = self.driver.find_element(*seletor)
                logger.info(f"Seletor encontrado: {seletor[1]}")
                self.seletor_baixar_xml_cache = seletor 
                return elemento
            except:
                continue
        
        try:
            elemento = self.driver.find_element(By.XPATH, "//a[contains(., 'Baixar XML')]")
            logger.info("Usando fallback genérico")
            return elemento
        except:
            return None
    
    def _preencher_formulario_consulta(self) -> bool:
        logger.info("Preenchendo formulario dentro do iframe...")
        
        def tentar_preencher():
            time.sleep(3)
            
            try:
                self.driver.switch_to.default_content()
            except:
                pass
                
            logger.info("Entrando no iframe para preencher formulario...")
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("DENTRO DO IFRAME DO FORMULARIO!")
            except Exception as e:
                logger.error(f"Nao conseguiu entrar no iframe do formulario: {e}")
                return False
            
            try:
                campo_teste = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "cmpDataInicial"))
                )
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
                seletor_modelo.select_by_value("-")
                logger.info("Modelo selecionado (Todos)")
                
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
                
            except Exception as e:
                logger.error(f"Erro ao preencher formulario: {e}")
                self.driver.switch_to.default_content()
                return False
            
            logger.info("SOLICITANDO RESOLUCAO DO CAPTCHA...")
            self.driver.switch_to.default_content()
            sucesso_captcha = self._captcha_manual()
            
            return sucesso_captcha
        
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
        """CAPTCHA REAL - aguarda resolução manual"""
        logger.info("CAPTCHA CLOUDFLARE REQUERIDO")
        
        print("\n" + "="*60)
        print("CAPTCHA REQUERIDO - RESOLUÇÃO MANUAL")
        print("="*60)
        print("1. Resolva o CAPTCHA no navegador")
        print("2. Aguarde o processamento completo")
        print("3. A página deve recarregar automaticamente")
        print("4. Pressione ENTER apenas quando o CAPTCHA estiver resolvido")
        print("="*60)
        
        try:
            # Aguardar input manual - usuário deve confirmar resolução
            input("Pressione ENTER após resolver o CAPTCHA: ")
            
            # Aguardar processamento pós-CAPTCHA
            time.sleep(3)
            
            logger.info("CAPTCHA resolvido - continuando fluxo")
            return True
            
        except Exception as e:
            logger.error(f"Erro no CAPTCHA manual: {e}")
            return False
    
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
            
            from datetime import datetime
            data_referencia = datetime.strptime(self.config.data_inicio, "%d/%m/%Y")
            
            resultado = self.gerenciador_download.processar_download_lote(self.config.inscricao_estadual, data_referencia)
            
            logger.info(f"Resumo: {resultado.total_baixado}/{resultado.total_encontrado} notas")
            logger.info(f"Arquivos salvos em: {resultado.caminho_download}")
            
            if resultado.erros:
                logger.error(f"Erro: {resultado.erros[0]}")
                return False
            
            return resultado.total_baixado > 0
            
        except Exception as e:
            logger.error(f"Erro download lote: {e}")
            return False
    
    def _validar_apos_captcha(self) -> bool:
        logger.info("Validando estado pós-CAPTCHA")
        
        try:
            current_url = self.driver.current_url
            if "challenges.cloudflare.com" in current_url:
                logger.error("Ainda na página de CAPTCHA - não resolvido")
                return False
            
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            self.driver.switch_to.frame(iframe)
            
            try:
                self.driver.find_element(By.ID, "cmpDataInicial")
                logger.info("Formulário carregado pós-CAPTCHA")
                self.driver.switch_to.default_content()
                return True
            except:
                logger.error("Formulário não encontrado pós-CAPTCHA")
                self.driver.switch_to.default_content()
                return False
            
        except Exception as e:
            logger.error(f"Erro na validação pós-CAPTCHA: {e}")
            return False
        
    def _validar_resultados_consulta(self) -> bool:
        logger.info("Validando resultados da consulta")
        
        try:
            if not self.gerenciador_download:
                return False
            
            total_notas = self.gerenciador_download.contar_notas_tabela()
            
            if total_notas == 0:
                logger.warning("Consulta não retornou notas - pulando download")
                return True  
            
            logger.info(f"Consulta retornou {total_notas} notas")
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação de resultados: {e}")
            return False
        
    def _download_unico_ie(self) -> bool:
        logger.info("Iniciando download único para IE atual")
        
        try:
            if not self.gerenciador_download:
                return False
            
            total_notas = self.gerenciador_download.contar_notas_tabela()
            
            if total_notas == 0:
                logger.info("Nenhuma nota para download - resultado válido")
                return True 
            
            from datetime import datetime
            data_referencia = datetime.strptime(self.config.data_inicio, "%d/%m/%Y")
            
            resultado = self.gerenciador_download.executar_fluxo_download_completo(
                self.config.inscricao_estadual, 
                data_referencia
            )
            
            logger.info(f"Resumo único IE {self.config.inscricao_estadual}: {resultado.total_baixado} arquivo(s)")
            
            return True
                
        except Exception as e:
            logger.error(f"Erro download único: {e}")
            return False
        
    def _processar_multiplas_ies(self) -> bool:
        logger.info("Iniciando processamento de múltiplas IEs")
        
        gerenciador_ies = GerenciadorMultiplasIEs()
        gerenciador_ies.limpar_estado()
        
        ies_validas = self.processador_ies.carregar_ies_validas()
        if not ies_validas:
            logger.error("Nenhuma IE válida encontrada")
            return False
        
        ies_teste = ies_validas[:2] 
        logger.info(f"TESTE: Processando {len(ies_teste)} IEs")
        
        gerenciador_ies.adicionar_ies(ies_teste)
        
        total_processadas = 0
        total_com_notas = 0
        ie_atual = gerenciador_ies.obter_proxima_ie()
        
        while ie_atual:
            estado_atual = gerenciador_ies.estados[ie_atual]
            tentativa_numero = estado_atual.tentativas + 1
            
            logger.info(f"Processando IE: {ie_atual} (tentativa {tentativa_numero})")
            gerenciador_ies.marcar_em_andamento(ie_atual)
            
            try:
                self.config.inscricao_estadual = ie_atual
                sucesso = self._executar_fluxo_individual_ie(ie_atual)
                
                if sucesso:
                    # Encontrou notas e fez download
                    gerenciador_ies.marcar_concluido(ie_atual)
                    total_processadas += 1
                    total_com_notas += 1
                    logger.info(f"✅ IE {ie_atual} CONCLUÍDA - {tentativa_numero}ª tentativa")
                else:
                    # Não encontrou notas
                    gerenciador_ies.marcar_pendente(ie_atual, "Nenhuma nota encontrada")
                    total_processadas += 1
                    logger.info(f"⏳ IE {ie_atual} PENDENTE - {tentativa_numero}ª tentativa (sem notas)")
                
            except Exception as e:
                # Erro no processamento
                gerenciador_ies.marcar_erro(ie_atual, str(e))
                total_processadas += 1
                logger.info(f"❌ IE {ie_atual} ERRO - {tentativa_numero}ª tentativa: {e}")
            
            time.sleep(2)
            ie_atual = gerenciador_ies.obter_proxima_ie()
        
        # Relatório final
        relatorio = gerenciador_ies.obter_relatorio()
        logger.info("=" * 60)
        logger.info("RELATÓRIO FINAL DO PROCESSAMENTO")
        logger.info("=" * 60)
        logger.info(f"Total de IEs processadas: {total_processadas}")
        logger.info(f"IEs com notas (CONCLUÍDAS): {total_com_notas}")
        logger.info(f"IEs sem notas (PENDENTES): {relatorio['pendentes']}")
        logger.info(f"IEs com erro: {relatorio['erros']}")
        logger.info("=" * 60)
        
        self._mostrar_relatorio_final(relatorio)
        
        return total_com_notas > 0

    def _executar_fluxo_completo_ie(self, ie: str) -> bool:
        """Executa o fluxo completo para uma IE específica"""
        etapas_ie = [
            ("PREENCHER_FORMULARIO", self._preencher_formulario_consulta, f"Preencher formulário {ie}"),
            ("VALIDAR_CAPTCHA", self._validar_apos_captcha, f"Validar pós-CAPTCHA {ie}"),
            ("EXECUTAR_CONSULTA", self._executar_consulta, f"Executar consulta {ie}"),
            ("VALIDAR_RESULTADOS", self._validar_resultados_consulta, f"Validar resultados {ie}"),
            ("DOWNLOAD_UNICO", self._download_unico_ie, f"Download único {ie}"),
            ("VOLTAR_CONSULTA", self._voltar_pagina_consulta, f"Voltar para consulta"),
        ]
        
        for nome_etapa, funcao_etapa, descricao in etapas_ie:
            logger.info(f"Executando: {descricao}")
            
            sucesso_etapa = funcao_etapa()
            if not sucesso_etapa:
                logger.error(f"Falha na etapa {nome_etapa} para IE {ie}")
                return False
            
            time.sleep(1)
        
        return True

    def _voltar_pagina_consulta(self) -> bool:
        logger.info("Verificando se precisa voltar para consulta...")
        
        try:
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            self.driver.switch_to.frame(iframe)
            
            try:
                botao_nova_consulta = self.driver.find_element(
                    By.XPATH, "//button[contains(text(), 'Nova Consulta')]"
                )
                if botao_nova_consulta.is_displayed():
                    botao_nova_consulta.click()
                    logger.info("Voltou para página de consulta")
                    self.driver.switch_to.default_content()
                    time.sleep(2)
                    return True
                else:
                    logger.info("Botão Nova Consulta não visível - já está na página de consulta")
                    self.driver.switch_to.default_content()
                    return True
            except:
                logger.info("Não está na página de resultados - já está na página de consulta")
                self.driver.switch_to.default_content()
                return True
                
        except Exception as e:
            logger.info(f"Não precisa voltar - já está na página correta: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return True
        
    def _executar_fluxo_individual_ie(self, ie: str) -> bool:
        logger.info(f"Iniciando fluxo individual para IE: {ie}")
        
        etapas_ie = [
            ("PREENCHER_FORMULARIO", self._preencher_formulario_consulta, f"Preencher formulário {ie}"),
            ("VALIDAR_CAPTCHA", self._validar_apos_captcha, f"Validar pós-CAPTCHA {ie}"),
            ("EXECUTAR_CONSULTA", self._executar_consulta, f"Executar consulta {ie}"),
            ("VALIDAR_RESULTADOS", self._validar_resultados_consulta, f"Validar resultados {ie}"),
        ]
        
        for nome_etapa, funcao_etapa, descricao in etapas_ie:
            logger.info(f"Executando: {descricao}")
            
            sucesso_etapa = funcao_etapa()
            if not sucesso_etapa:
                logger.error(f"Falha na etapa {nome_etapa} para IE {ie}")
                return False
            
            time.sleep(1)
        
        total_notas = self.gerenciador_download.contar_notas_tabela()
        
        if total_notas > 0:
            logger.info(f"Encontradas {total_notas} notas - executando download")
            etapas_download = [
                ("DOWNLOAD_UNICO", self._download_unico_ie, f"Download único {ie}"),
                ("VOLTAR_CONSULTA", self._voltar_pagina_consulta, f"Voltar para consulta"),
            ]
            
            for nome_etapa, funcao_etapa, descricao in etapas_download:
                logger.info(f"Executando: {descricao}")
                
                sucesso_etapa = funcao_etapa()
                if not sucesso_etapa:
                    logger.error(f"Falha na etapa {nome_etapa} para IE {ie}")
                    return False
                
                time.sleep(1)
            
            return True
        else:
            logger.info(f"Nenhuma nota encontrada para IE {ie} - mantendo como pendente")
            return False

    def _mostrar_relatorio_final(self, relatorio: Dict):
        print("\n" + "="*60)
        print("RELATÓRIO FINAL - PROCESSAMENTO")
        print("="*60)
        print(f"Total IEs: {relatorio['total']}")
        print(f"Concluídas: {relatorio['concluidos']}")
        print(f"Com erro: {relatorio['erros']}")
        print(f"Progresso: {relatorio['progresso']}")
        print("="*60)
    
    def limpar_recursos(self):
        logger.info("Navegador mantido aberto")
        print("\n" + "="*60)
        print("Fluxo concluido - Navegador aberto para inspecao")
        print("="*60)
        