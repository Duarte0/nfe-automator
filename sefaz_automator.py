"""
Automação SEFAZ - Download XML NFe
"""

import time
import logging
from typing import List, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from config_manager import SEFAZConfig
from driver_manager import GerenciadorDriver
from constants import SELECTORS, TIMEOUTS, SEFAZ_LOGIN_URL, SEFAZ_DASHBOARD_URL, SEFAZ_ACESSO_RESTRITO_URL

logger = logging.getLogger(__name__)


class GerenciadorRetry:
    """Sistema de retry simples"""
    
    def executar_com_retry(self, funcao, max_tentativas=3, delay=2, nome_operacao="Operação"):
        ultima_excecao = None
        for tentativa in range(1, max_tentativas + 1):
            try:
                logger.debug(f"{nome_operacao} - Tentativa {tentativa}/{max_tentativas}")
                return funcao()
            except Exception as e:
                ultima_excecao = e
                if tentativa == max_tentativas:
                    logger.error(f"Falha após {max_tentativas} tentativas em {nome_operacao}: {e}")
                    break
                logger.info(f"Tentativa {tentativa} falhou, retry em {delay}s")
                time.sleep(delay)
        raise ultima_excecao


gerenciador_retry = GerenciadorRetry()


class AutomatorSEFAZ:
    """
    Automatização SEFAZ - Focada no link correto e popup de login.
    NÃO usa URL direta - apenas o fluxo correto.
    """
    
    def __init__(self):
        self.gerenciador_driver = GerenciadorDriver()
        self.wait: Optional[WebDriverWait] = None
        self.config: Optional[SEFAZConfig] = None
        
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
        ]
    
    def inicializar(self, config: SEFAZConfig) -> bool:
        logger.info("Inicializando automator")
        try:
            self.config = config
            driver = self.gerenciador_driver.configurar_driver()
            if not driver:
                return False
            self.wait = WebDriverWait(driver, self.timeouts['element_wait'])
            logger.info("WebDriver configurado")
            return True
        except Exception as e:
            logger.error(f"Erro: {e}")
            return False
    
    @property
    def driver(self) -> Optional[WebDriver]:
        return self.gerenciador_driver.driver
    
    def executar_fluxo(self) -> bool:
        logger.info("Iniciando fluxo de automacao")
        inicio_total = time.time()
        
        try:
            for nome_etapa, funcao_etapa, descricao in self.etapas_fluxo:
                inicio_etapa = time.time()
                logger.info(f"Executando: {descricao}")
                
                if not funcao_etapa():
                    logger.error(f"Falha: {nome_etapa}")
                    self._mostrar_mensagem_final(False)
                    return False
                
                tempo_etapa = time.time() - inicio_etapa
                logger.info(f"Etapa concluida em {tempo_etapa:.1f}s")
            
            tempo_total = time.time() - inicio_total
            self._mostrar_mensagem_final(True, tempo_total)
            return True
            
        except Exception as e:
            logger.error(f"Erro: {e}")
            self._mostrar_mensagem_final(False)
            return False
    
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
            self.driver.get(SEFAZ_LOGIN_URL)
            time.sleep(self.timeouts['page_load'])
            
            campo_usuario = self.driver.find_element(By.ID, "username")
            campo_senha = self.driver.find_element(By.ID, "password")
            botao_login = self.driver.find_element(By.ID, "btnAuthenticate")
            
            campo_usuario.clear()
            campo_usuario.send_keys(self.config.usuario)
            campo_senha.clear()
            campo_senha.send_keys(self.config.senha)
            botao_login.click()
            
            time.sleep(self.timeouts['login_wait'])
            return True
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_login,
                max_tentativas=2,
                delay=3,
                nome_operacao="Login Portal"
            )
        except Exception as e:
            logger.error(f"Erro login: {e}")
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
            logger.info(f"URL atual: {self.driver.current_url}")
            
            seletores_acesso = [
                (By.XPATH, "//h3[contains(text(), 'Acesso Restrito')]"),
                (By.XPATH, "//a[contains(@href, 'NETACCESS/default.asp')]"),
                (By.XPATH, "//a[@target='_blank' and contains(@href, 'NETACCESS')]"),
                (By.XPATH, "//a[contains(@class, 'dashboard-sistemas-item')]"),
                (By.XPATH, "//a[contains(@href, 'NETACCESS') and contains(@title, 'Acessar')]"),
                (By.XPATH, "//h3[contains(text(), 'Acesso Restrito')]/ancestor::a"),
            ]
            
            link_acesso = None
            for i, seletor in enumerate(seletores_acesso):
                try:
                    logger.info(f"Tentativa {i+1}: {seletor}")
                    link_acesso = self.driver.find_element(*seletor)
                    logger.info(f"Encontrado com: {seletor}")
                    
                    try:
                        href = link_acesso.get_attribute('href')
                        texto = link_acesso.text
                        logger.info(f"href: {href}")
                        logger.info(f"texto: {texto}")
                    except:
                        pass
                    
                    break
                except Exception as e:
                    continue
            
            if not link_acesso:
                logger.error("Nenhum seletor funcionou")
                
                logger.info("Procurando elementos relacionados...")
                try:
                    elementos_acesso = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Acesso') or contains(text(), 'Restrito')]")
                    logger.info(f"Elementos com Acesso ou Restrito: {len(elementos_acesso)}")
                    
                    for elem in elementos_acesso[:10]:
                        try:
                            tag = elem.tag_name
                            texto = elem.text.strip()
                            if texto:
                                logger.info(f"{tag}: '{texto}'")
                        except:
                            pass
                except Exception as e:
                    logger.error(f"Erro no debug: {e}")
                
                return False
            
            aba_original = self.driver.current_window_handle
            logger.info(f"Aba original: {aba_original}")
            
            logger.info("Clicando no link...")
            self.driver.execute_script("arguments[0].click();", link_acesso)
            logger.info("Clicou via JavaScript")
            
            logger.info("Aguardando nova aba...")
            time.sleep(5)
            
            abas = self.driver.window_handles
            logger.info(f"Abas abertas: {len(abas)}")
            
            if len(abas) > 1:
                nova_aba = abas[-1]
                self.driver.switch_to.window(nova_aba)
                logger.info("Mudou para nova aba")
                logger.info(f"URL nova aba: {self.driver.current_url}")
                
                if "netaccess" in self.driver.current_url.lower():
                    logger.info("ACESSO RESTRITO CONSEGUIDO!")
                else:
                    logger.warning(f"URL inesperada: {self.driver.current_url}")
            else:
                logger.info("Nenhuma nova aba aberta")
                logger.info(f"Permaneceu em: {self.driver.current_url}")
            
            return True
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_clicar,
                max_tentativas=3,
                delay=2,
                nome_operacao="Clicar Acesso Restrito"
            )
        except Exception as e:
            logger.error(f"Erro critico: {e}")
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
    
    def limpar_recursos(self):
        logger.info("Navegador mantido aberto")
        print("\n" + "="*60)
        print("Fluxo concluido - Navegador aberto para inspecao")
        print("="*60)