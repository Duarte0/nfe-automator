"""
Automação SEFAZ - Download XML NFe
"""

import time
import logging
from typing import Optional, Dict
from datetime import datetime

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from .download_manager import GerenciadorDownload
from .fluxo_utils import DetectorMudancas, GerenciadorWaitInteligente, VerificadorEstado
from src.config.config_manager import SEFAZConfig
from .driver_manager import GerenciadorDriver
from ..config.constants import SELECTORS, SEFAZ_LOGIN_URL, SEFAZ_DASHBOARD_URL
from .retry_manager import gerenciador_retry
from .ie_loader import CarregadorIEs
from .processador_ie import ProcessadorIE
from .iframe_manager import GerenciadorIframe
from .health_check import HealthCheckDriver
from .timeout_manager import TimeoutManager

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
        self.carregador_ies = CarregadorIEs()
        self.processador_ie = None
        self.gerenciador_iframe = None
        self.health_check = None
        self.timeout_manager = TimeoutManager()
        
        self.estatisticas_fluxo = {
            'inicio_execucao': None,
            'etapas_executadas': 0,
            'etapas_com_erro': 0,
            'tempos_etapas': {}
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
                
            self.timeout_manager = TimeoutManager()
            
            self.detector_mudancas = DetectorMudancas(driver)
            self.verificador_estado = VerificadorEstado(driver)
            self.gerenciador_download = GerenciadorDownload(driver)
            
            timeout_elementos = self.timeout_manager.get_timeout('element_wait')
            self.wait = WebDriverWait(driver, timeout_elementos)
            self.wait_inteligente = GerenciadorWaitInteligente(driver, self.timeout_manager)
            
            self.health_check = HealthCheckDriver(driver)
            self.gerenciador_iframe = GerenciadorIframe(driver)
            
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
        logger.info("Efetuando login")
        
        def tentar_login():
            import time
            inicio = time.time()
            
            url_anterior = self.driver.current_url
            self.driver.get(SEFAZ_LOGIN_URL)
            self.detector_mudancas.aguardar_carregamento()
            
            campo_usuario = self.wait_inteligente.aguardar_elemento_ou_alternativas(
                SELECTORS['login']['usuario']
            )
            campo_senha = self.wait_inteligente.aguardar_elemento_ou_alternativas(
                SELECTORS['login']['senha']
            )
            botao_login = self.wait_inteligente.aguardar_elemento_ou_alternativas(
                SELECTORS['login']['botao_login']
            )
            
            if not all([campo_usuario, campo_senha, botao_login]):
                logger.error("Elementos de login não encontrados")
                return False
                
            campo_usuario.clear()
            campo_usuario.send_keys(self.config.usuario)
            campo_senha.clear()
            campo_senha.send_keys(self.config.senha)
            botao_login.click()
            
            # Usar timeout dinâmico
            delay_login = self.timeout_manager.get_delay('login_wait')
            time.sleep(delay_login)
            
            mudanca, url_atual = self.detector_mudancas.verificar_mudanca_url(url_anterior)
            
            tempo_decorrido = time.time() - inicio
            self.timeout_manager.registrar_tempo_operacao('login_wait', tempo_decorrido)
            
            return not self.verificador_estado.esta_na_pagina_login()
        
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
        delay_acao = self.timeout_manager.get_delay('action_delay')
        time.sleep(delay_acao)
        
        if "portalsefaz-apps" not in self.driver.current_url:
            self.driver.get(SEFAZ_DASHBOARD_URL)
            delay_page_load = self.timeout_manager.get_delay('page_load')
            time.sleep(delay_page_load)
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
            
            timeout_popup = self.timeout_manager.get_timeout('popup_wait')
            for tentativa in range(timeout_popup):
                if self._verificar_popup_login():
                    logger.info("POPUP DETECTADO! Preenchendo...")
                    return self._preencher_popup_login()
                
                logger.info(f"Aguardando popup... ({tentativa + 1}/15)")
                time.sleep(1)
            
            logger.error("TIMEOUT: Popup de login nao apareceu apos 15 segundos")
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
            delay_acao = self.timeout_manager.get_delay('action_delay')
            time.sleep(delay_acao)
            
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
            input("Pressione ENTER após resolver o CAPTCHA: ")
            time.sleep(3)
            logger.info("CAPTCHA resolvido - continuando fluxo")
            return True
            
        except Exception as e:
            logger.error(f"Erro no CAPTCHA manual: {e}")
            return False
    
    def _processar_multiplas_ies(self) -> bool:
        logger.info(f"Iniciando processamento de IEs")
        
        if not self.processador_ie:
            self.processador_ie = ProcessadorIE(self)
        
        ies_validas = self.carregador_ies.carregar_ies_validas()
        if not ies_validas:
            return False
        
        ies_com_notas = []
        
        for i, ie in enumerate(ies_validas, 1):
            if i % 10 == 1 or i == len(ies_validas):
                logger.info(f"[{i}/{len(ies_validas)}] IE {ie}")
            else:
                logger.debug(f"[{i}/{len(ies_validas)}] IE {ie}") 
            
            try:
                if self.processador_ie.processar_ie(ie):
                    ies_com_notas.append(ie)
                    logger.debug(f"  ✓ Baixado")
                else:
                    logger.debug(f"  - Sem notas") 
            except Exception as e:
                logger.error(f"  ✗ Erro: {e}") 
        
        logger.info(f"Concluído: {len(ies_com_notas)} IEs com notas de {len(ies_validas)} processadas")
        return len(ies_com_notas) > 0

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