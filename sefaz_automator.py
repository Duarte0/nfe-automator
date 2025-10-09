
"""
Automação SEFAZ - FOCADA NO LINK CORRETO E POPUP
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
            'element_wait': 8,  # ⬆️ Aumentado para encontrar link
            'action_delay': 1,
            'login_wait': 5,
            'popup_wait': 10,   # ⬆️ Mais tempo para popup
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
        """Inicializa automator."""
        logger.info("🔧 INICIALIZANDO AUTOMATOR - SEM URL DIRETA")
        
        try:
            self.config = config
            driver = self.gerenciador_driver.configurar_driver()
            if not driver:
                return False
                
            self.wait = WebDriverWait(driver, self.timeouts['element_wait'])
            logger.info("✅ WebDriver configurado (foco no link correto)")
            return True
            
        except Exception as e:
            logger.error(f"💥 ERRO: {str(e)}")
            return False
    
    @property
    def driver(self) -> Optional[WebDriver]:
        return self.gerenciador_driver.driver
    
    def executar_fluxo(self) -> bool:
        """Executa fluxo focado no link correto."""
        logger.info("🎯 INICIANDO FLUXO - BUSCA PELO LINK CORRETO")
        logger.info("🔍 IGNORANDO URL DIRETA - apenas fluxo oficial")
        
        inicio_total = time.time()
        
        try:
            for nome_etapa, funcao_etapa, descricao in self.etapas_fluxo:
                inicio_etapa = time.time()
                logger.info(f"🔄 {nome_etapa}: {descricao}")
                
                if not funcao_etapa():
                    logger.error(f"❌ FALHA: {nome_etapa}")
                    self._mostrar_mensagem_final(False)
                    return False
                
                tempo_etapa = time.time() - inicio_etapa
                logger.info(f"✅ {nome_etapa} concluída em {tempo_etapa:.1f}s")
            
            tempo_total = time.time() - inicio_total
            self._mostrar_mensagem_final(True, tempo_total)
            return True
            
        except Exception as e:
            logger.error(f"💥 ERRO: {str(e)}")
            self._mostrar_mensagem_final(False)
            return False
    
    def _mostrar_mensagem_final(self, sucesso: bool, tempo_total: float = 0):
        """Mensagem final."""
        print("\n" + "="*70)
        if sucesso:
            print("🎉 SUCESSO! Fluxo correto executado")
            print(f"⏱️  Tempo: {tempo_total:.1f}s")
        else:
            print("⚠️  FALHA - Verifique o problema")
        print("🔍 Navegador mantido aberto")
        print("="*70)
    
    def _fazer_login_portal(self) -> bool:
        """Login no portal."""
        logger.info("🔐 LOGIN PORTAL...")
        
        try:
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
                
        except Exception as e:
            logger.error(f"❌ Erro login: {str(e)}")
            return False
    
    def _aguardar_dashboard(self) -> bool:
        """Aguardar dashboard."""
        time.sleep(self.timeouts['action_delay'])
        
        if "portalsefaz-apps" not in self.driver.current_url:
            self.driver.get(SEFAZ_DASHBOARD_URL)
            time.sleep(self.timeouts['page_load'])
        
        return True
    
    def _clicar_acesso_restrito(self) -> bool:
        """Clicar em Acesso Restrito com o seletor CORRETO."""
        logger.info("🚪 CLICANDO EM 'ACESSO RESTRITO'...")
        
        try:
            # 🔧 AGUARDAR PÁGINA CARREGAR
            time.sleep(3)
            logger.info(f"📍 URL atual: {self.driver.current_url}")
            
            # 🔧 SELETORES ESPECÍFICOS BASEADOS NO HTML QUE VOCÊ MOSTROU
            seletores_acesso = [
                # PELO TEXTO "Acesso Restrito" dentro do <h3>
                (By.XPATH, "//h3[contains(text(), 'Acesso Restrito')]"),
                
                # PELO LINK COM href específico
                (By.XPATH, "//a[contains(@href, 'NETACCESS/default.asp')]"),
                
                # PELO TARGET _blank
                (By.XPATH, "//a[@target='_blank' and contains(@href, 'NETACCESS')]"),
                
                # PELA CLASSE dashboard-sistemas-item
                (By.XPATH, "//a[contains(@class, 'dashboard-sistemas-item')]"),
                
                # PELO TEXTO NO href E NO título
                (By.XPATH, "//a[contains(@href, 'NETACCESS') and contains(@title, 'Acessar')]"),
                
                # PELO h3 E DEPOIS O LINK PAI
                (By.XPATH, "//h3[contains(text(), 'Acesso Restrito')]/ancestor::a"),
            ]
            
            link_acesso = None
            for i, seletor in enumerate(seletores_acesso):
                try:
                    logger.info(f"🔍 Tentativa {i+1}: {seletor}")
                    link_acesso = self.driver.find_element(*seletor)
                    logger.info(f"✅ ENCONTRADO com: {seletor}")
                    
                    try:
                        href = link_acesso.get_attribute('href')
                        texto = link_acesso.text
                        logger.info(f"   🔗 href: {href}")
                        logger.info(f"   📝 texto: {texto}")
                    except:
                        pass
                    
                    break
                except Exception as e:
                    logger.debug(f"   ❌ {seletor} - {e}")
                    continue
            
            if not link_acesso:
                logger.error("❌ Nenhum seletor funcionou")
                
                # 🔍 DEBUG: Listar todos os elementos com "Acesso" ou "Restrito"
                logger.info("🔍 Procurando elementos relacionados...")
                try:
                    elementos_acesso = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Acesso') or contains(text(), 'Restrito')]")
                    logger.info(f"📊 Elementos com 'Acesso' ou 'Restrito': {len(elementos_acesso)}")
                    
                    for elem in elementos_acesso[:10]:  # Primeiros 10
                        try:
                            tag = elem.tag_name
                            texto = elem.text.strip()
                            if texto:
                                logger.info(f"   🏷️  {tag}: '{texto}'")
                        except:
                            pass
                except Exception as e:
                    logger.error(f"❌ Erro no debug: {e}")
                
                return False
            
            # 🔧 CLICAR NO LINK ENCONTRADO
            aba_original = self.driver.current_window_handle
            logger.info(f"📑 Aba original: {aba_original}")
            
            logger.info("🖱️  Clicando no link...")
            self.driver.execute_script("arguments[0].click();", link_acesso)
            logger.info("✅ Clicou via JavaScript")
            
            # 🔧 AGUARDAR E MUDAR PARA NOVA ABA
            logger.info("⏳ Aguardando nova aba...")
            time.sleep(5)
            
            abas = self.driver.window_handles
            logger.info(f"📑 Abas abertas: {len(abas)}")
            
            if len(abas) > 1:
                nova_aba = abas[-1]
                self.driver.switch_to.window(nova_aba)
                logger.info(f"🔄 Mudou para nova aba")
                logger.info(f"📍 URL nova aba: {self.driver.current_url}")
                
                # Verificar se está na página correta
                if "netaccess" in self.driver.current_url.lower():
                    logger.info("✅ ✅ ✅ ACESSO RESTRITO CONSEGUIDO!")
                else:
                    logger.warning(f"⚠️  URL inesperada: {self.driver.current_url}")
            else:
                logger.info("ℹ️  Nenhuma nova aba aberta")
                logger.info(f"📍 Permaneceu em: {self.driver.current_url}")
            
            return True
                
        except Exception as e:
            logger.error(f"💥 Erro crítico: {str(e)}")
            return False
        
    def _acessar_baixar_xml(self) -> bool:
        """Método CORRIGIDO para iframe - ESPECÍFICO para SEFAZ GO."""
        logger.info("🎯 ACESSANDO IFRAME E BUSCANDO 'Baixar XML NFE'")
        
        try:
            # 🔧 PRIMEIRO: ENTRAR NO IFRAME
            logger.info("🔍 Procurando iframe...")
            
            # Estratégias para encontrar o iframe
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
                    logger.info(f"✅ IFRAME ENCONTRADO: {seletor[1]}")
                    break
                except:
                    continue
            
            if not iframe_encontrado:
                logger.error("❌ IFRAME NÃO ENCONTRADO!")
                return False
            
            # ENTRAR NO IFRAME
            logger.info("🚪 ENTRANDO NO IFRAME...")
            self.driver.switch_to.frame(iframe_encontrado)
            logger.info("✅ DENTRO DO IFRAME!")
            
            # 🔧 SEGUNDO: BUSCAR O LINK DENTRO DO IFRAME
            logger.info("🔍 Buscando 'Baixar XML NFE' dentro do iframe...")
            
            # Seletores ESPECÍFICOS baseados no HTML que você mostrou
            seletores_link = [
                # Pelo onclick exato que você mostrou
                (By.XPATH, "//a[@onclick=\"OpenUrl('https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfe/consulta-notas-recebidas', false, '', 'False', 'true')\"]"),
                
                # Pelo texto exato dentro de um link
                (By.XPATH, "//a[text()='Baixar XML NFE']"),
                
                # Pelo texto parcial
                (By.XPATH, "//a[contains(text(), 'Baixar XML NFE')]"),
                
                # Pelo href javascript e texto
                (By.XPATH, "//a[contains(@href, 'javascript:void') and contains(text(), 'Baixar XML')]"),
                
                # Qualquer link com "Baixar XML"
                (By.XPATH, "//a[contains(., 'Baixar XML')]"),
            ]
            
            link_encontrado = None
            for i, seletor in enumerate(seletores_link):
                try:
                    logger.info(f"🔍 Tentativa {i+1}: {seletor[1]}")
                    link_encontrado = self.driver.find_element(*seletor)
                    logger.info(f"✅ ✅ ✅ LINK ENCONTRADO dentro do iframe!")
                    
                    # Verificar informações do link
                    try:
                        texto = link_encontrado.text
                        onclick = link_encontrado.get_attribute('onclick')
                        logger.info(f"   📝 Texto: '{texto}'")
                        logger.info(f"   🖱️  onClick: {onclick}")
                    except:
                        pass
                    
                    break
                except Exception as e:
                    logger.debug(f"   ❌ {seletor[1]} - {e}")
                    continue
            
            if not link_encontrado:
                logger.error("❌ Link não encontrado dentro do iframe")
                self.driver.switch_to.default_content()  # Voltar para conteúdo principal
                return False
            
            # 🔧 TERCEIRO: CLICAR NO LINK
            logger.info("🖱️  Clicando no link 'Baixar XML NFE'...")
            try:
                # Usar JavaScript para clicar (mais confiável)
                self.driver.execute_script("arguments[0].click();", link_encontrado)
                logger.info("✅ Clicado via JavaScript")
            except Exception as e:
                logger.error(f"❌ Erro ao clicar: {e}")
                self.driver.switch_to.default_content()
                return False
            
            # 🔧 QUARTO: AGUARDAR E VERIFICAR RESULTADO
            logger.info("⏳ Aguardando ação do clique...")
            time.sleep(5)
            
            # Verificar se saímos do iframe (popup abriu)
            try:
                current_url = self.driver.current_url
                logger.info(f"📍 URL atual: {current_url}")
                
                # Se estamos ainda no iframe ou saímos
                if "consulta-notas-recebidas" in current_url:
                    logger.info("✅ ✅ ✅ REDIRECIONADO PARA PÁGINA DE CONSULTA!")
                    return True
                else:
                    logger.info("ℹ️  Permaneceu na mesma página - possivelmente popup aberto")
                    return True  # Pode ter aberto popup/janela
                    
            except Exception as e:
                logger.warning(f"⚠️  Erro ao verificar URL: {e}")
                return True  # Continuar mesmo com erro
                
        except Exception as e:
            logger.error(f"💥 Erro crítico no acesso ao iframe: {str(e)}")
            # Tentar voltar para o conteúdo principal em caso de erro
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def _procurar_todos_links_iframe(self):
        """Método de debug: lista todos os links dentro do iframe."""
        logger.info("🔍 LISTANDO TODOS OS LINKS DO IFRAME...")
        
        try:
            # Entrar no iframe primeiro
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            self.driver.switch_to.frame(iframe)
            
            # Buscar todos os links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"📊 Total de links dentro do iframe: {len(links)}")
            
            for i, link in enumerate(links):
                try:
                    texto = link.text.strip()
                    onclick = link.get_attribute('onclick')
                    href = link.get_attribute('href')
                    
                    if texto:  # Apenas links com texto
                        logger.info(f"   {i+1:2d}. '{texto}'")
                        if onclick:
                            logger.info(f"        🖱️  onClick: {onclick[:100]}{'...' if len(onclick) > 100 else ''}")
                        if href and 'javascript' not in href:
                            logger.info(f"        🔗 href: {href}")
                except:
                    continue
            
            # Voltar para conteúdo principal
            self.driver.switch_to.default_content()
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar links do iframe: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
    
    def _aguardar_e_preencher_popup(self) -> bool:
        """
        AGUARDAR O POPUP DE LOGIN APARECER E PREENCHER
        Esta etapa ESPERA o popup aparecer após clicar no link
        """
        logger.info("🪟 AGUARDANDO POPUP DE LOGIN...")
        
        try:
            # 🔧 AGUARDAR O POPUP APARECER
            logger.info("⏳ Aguardando até 15 segundos para popup aparecer...")
            
            for tentativa in range(15):  # 15 tentativas de 1 segundo = 15 segundos
                if self._verificar_popup_login():
                    logger.info("✅ POPUP DETECTADO! Preenchendo...")
                    return self._preencher_popup_login()
                
                logger.info(f"   ⏰ Aguardando popup... ({tentativa + 1}/15)")
                time.sleep(1)
            
            # Se chegou aqui, popup não apareceu
            logger.error("❌ TIMEOUT: Popup de login não apareceu após 15 segundos")
            logger.info("💡 Possíveis causas:")
            logger.info("   - O link não abriu o popup")
            logger.info("   - Popup bloqueado pelo navegador")
            logger.info("   - Necessita de interação manual")
            return False
            
        except Exception as e:
            logger.error(f"💥 Erro ao aguardar popup: {str(e)}")
            return False
    
    def _verificar_popup_login(self) -> bool:
        """Verifica se o popup de login está visível."""
        try:
            # Verificar elementos característicos do popup NETACCESS
            elementos_popup = [
                (By.ID, "NetAccess.Login"),
                (By.ID, "NetAccess.Password"),
                (By.ID, "btnAuthenticate"),
            ]
            
            for elemento in elementos_popup:
                try:
                    if self.driver.find_element(*elemento):
                        logger.info(f"✅ Elemento de popup encontrado: {elemento[1]}")
                        return True
                except:
                    continue
            
            # Verificar textos característicos
            textos_popup = [
                "Para se autenticar, favor informar suas credenciais",
                "Caro usuário",
                "realize a confirmação",
            ]
            
            page_source = self.driver.page_source
            for texto in textos_popup:
                if texto in page_source:
                    logger.info(f"✅ Texto de popup encontrado: {texto}")
                    return True
            
            return False
        except:
            return False
    
    def _preencher_popup_login(self) -> bool:
        """Preenche o formulário no popup de login."""
        logger.info("🔐 PREENCHENDO POPUP DE LOGIN...")
        
        try:
            # Preencher CPF no popup
            campo_cpf = self.driver.find_element(By.ID, "NetAccess.Login")
            campo_cpf.clear()
            campo_cpf.send_keys(self.config.usuario)
            logger.info("✅ CPF preenchido no popup")
            
            # Preencher senha no popup
            campo_senha = self.driver.find_element(By.ID, "NetAccess.Password")
            campo_senha.clear()
            campo_senha.send_keys(self.config.senha)
            logger.info("✅ Senha preenchida no popup")
            
            # Clicar em Autenticar
            botao_autenticar = self.driver.find_element(By.ID, "btnAuthenticate")
            botao_autenticar.click()
            logger.info("✅ Clicou em Autenticar no popup")
            
            # Aguardar processamento do login
            logger.info("⏳ Aguardando processamento do login no popup...")
            time.sleep(5)
            
            # Verificar se o popup sumiu (login bem sucedido)
            if not self._verificar_popup_login():
                logger.info("✅ Login no popup realizado com sucesso!")
                return True
            else:
                logger.error("❌ Falha no login - popup ainda está aberto")
                return False
                
        except Exception as e:
            logger.error(f"💥 Erro ao preencher popup: {str(e)}")
            return False
    
    def _clicar_baixar_xml_apos_login(self) -> bool:
        """Clicar novamente após login - CORRIGIDO para iframe."""
        logger.info("🖱️ CLICANDO NOVAMENTE EM 'Baixar XML NFE' APÓS LOGIN...")
        
        try:
            # Aguardar a página recarregar após login
            time.sleep(3)
            
            # 🔧 PRIMEIRO: ENTRAR NOVAMENTE NO IFRAME (a página pode ter atualizado)
            logger.info("🔍 Entrando novamente no iframe após login...")
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("✅ ✅ ✅ DENTRO DO IFRAME NOVAMENTE!")
            except Exception as e:
                logger.error(f"❌ Não conseguiu entrar no iframe após login: {e}")
                return False
            
            # 🔧 SEGUNDO: PROCURAR E CLICAR NO LINK NOVAMENTE
            logger.info("🔍 Procurando link novamente após login...")
            
            # Usar os mesmos seletores que funcionaram antes
            seletores_link = [
                (By.XPATH, "//a[@onclick=\"OpenUrl('https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfe/consulta-notas-recebidas', false, '', 'False', 'true')\"]"),
                (By.XPATH, "//a[text()='Baixar XML NFE']"),
                (By.XPATH, "//a[contains(text(), 'Baixar XML NFE')]"),
            ]
            
            link_encontrado = None
            for seletor in seletores_link:
                try:
                    link_encontrado = self.driver.find_element(*seletor)
                    logger.info(f"✅ Link encontrado após login!")
                    break
                except:
                    continue
            
            if not link_encontrado:
                logger.error("❌ Não encontrou link após login")
                
                # 🔍 DEBUG: Listar links disponíveis
                try:
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    logger.info(f"📊 Links disponíveis após login: {len(links)}")
                    for i, link in enumerate(links):
                        try:
                            texto = link.text.strip()
                            if texto:
                                logger.info(f"   {i+1}. '{texto}'")
                        except:
                            pass
                except Exception as e:
                    logger.error(f"❌ Erro no debug: {e}")
                
                self.driver.switch_to.default_content()
                return False
            
            # 🔧 TERCEIRO: CLICAR NO LINK
            logger.info("🖱️ Clicando no link após login...")
            try:
                self.driver.execute_script("arguments[0].click();", link_encontrado)
                logger.info("✅ Clicado via JavaScript após login")
            except Exception as e:
                logger.error(f"❌ Erro ao clicar após login: {e}")
                self.driver.switch_to.default_content()
                return False
            
            # 🔧 QUARTO: VOLTAR PARA CONTEÚDO PRINCIPAL E AGUARDAR
            self.driver.switch_to.default_content()
            logger.info("⏳ Aguardando redirecionamento após segundo clique...")
            time.sleep(5)
            
            # Verificar se foi redirecionado
            current_url = self.driver.current_url
            logger.info(f"📍 URL após segundo clique: {current_url}")
            
            if "consulta-notas-recebidas" in current_url:
                logger.info("✅ ✅ ✅ REDIRECIONADO PARA FORMULÁRIO DE CONSULTA!")
                return True
            else:
                logger.info("ℹ️  Não redirecionado - possivelmente já está na página correta")
                return True  # Continuar mesmo assim
                
        except Exception as e:
            logger.error(f"💥 Erro no segundo clique: {str(e)}")
            # Tentar voltar para conteúdo principal em caso de erro
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def _preencher_formulario_consulta(self) -> bool:
        """Método ATUALIZADO com checkbox de notas canceladas."""
        logger.info("📝 PREENCHENDO FORMULÁRIO DENTRO DO IFRAME...")
        
        try:
            time.sleep(3)
            
            # 🔧 PRIMEIRO: ENTRAR NO IFRAME
            logger.info("🔍 Entrando no iframe para preencher formulário...")
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("✅ ✅ ✅ DENTRO DO IFRAME DO FORMULÁRIO!")
            except Exception as e:
                logger.error(f"❌ Não conseguiu entrar no iframe do formulário: {e}")
                return False
            
            # 🔧 VERIFICAR SE O FORMULÁRIO ESTÁ DENTRO DO IFRAME
            current_url = self.driver.current_url
            logger.info(f"📍 URL dentro do iframe: {current_url}")
            
            # Verificar se encontramos elementos do formulário
            try:
                # Testar se encontramos algum campo do formulário
                campo_teste = self.driver.find_element(By.ID, "cmpDataInicial")
                logger.info("✅ ✅ ✅ FORMULÁRIO ENCONTRADO DENTRO DO IFRAME!")
            except:
                logger.error("❌ Formulário não encontrado dentro do iframe")
                self.driver.switch_to.default_content()
                return False
            
            # 🔧 AGORA PREENCHER OS CAMPOS
            logger.info("🖊️ Preenchendo campos do formulário...")
            
            try:
                # 1. Data Inicial
                campo_data_inicio = self.driver.find_element(By.ID, "cmpDataInicial")
                campo_data_inicio.clear()
                campo_data_inicio.send_keys(self.config.data_inicio)
                logger.info("✅ Data início preenchida")
                
                # 2. Data Final
                campo_data_fim = self.driver.find_element(By.ID, "cmpDataFinal")
                campo_data_fim.clear()
                campo_data_fim.send_keys(self.config.data_fim)
                logger.info("✅ Data fim preenchida")
                
                # 3. Inscrição Estadual
                campo_ie = self.driver.find_element(By.ID, "cmpNumIeDest")
                campo_ie.clear()
                campo_ie.send_keys(self.config.inscricao_estadual)
                logger.info("✅ Inscrição estadual preenchida")
                
                # 4. Modelo da Nota (55 - NFe)
                seletor_modelo = Select(self.driver.find_element(By.ID, "cmpModelo"))
                seletor_modelo.select_by_value("55")
                logger.info("✅ Modelo selecionado (55 - NFe)")
                
                # 5. Tipo de Nota (Entrada)
                radio_entrada = self.driver.find_element(By.XPATH, "//input[@value='0' and @name='cmpTipoNota']")
                if not radio_entrada.is_selected():
                    radio_entrada.click()
                    logger.info("✅ Tipo de nota selecionado (Entrada)")
                
                # 🔧 6. EXIBIR NOTAS CANCELADAS (SEMPRE MARCAR)
                try:
                    checkbox_canceladas = self.driver.find_element(By.ID, "cmpExbNotasCanceladas")
                    if not checkbox_canceladas.is_selected():
                        # Usar JavaScript para clicar (mais confiável para checkboxes)
                        self.driver.execute_script("arguments[0].click();", checkbox_canceladas)
                        logger.info("✅ ✅ ✅ CHECKBOX 'Exibir notas canceladas' MARCADO!")
                    else:
                        logger.info("✅ Checkbox 'Exibir notas canceladas' já estava marcado")
                except Exception as e:
                    logger.warning(f"⚠️  Não conseguiu marcar checkbox de notas canceladas: {e}")
                
                logger.info("✅ ✅ ✅ FORMULÁRIO PREENCHIDO COM SUCESSO!")
                
                # 🔧 VOLTAR PARA CONTEÚDO PRINCIPAL ANTES DO CAPTCHA
                self.driver.switch_to.default_content()
                
                # CAPTCHA MANUAL
                return self._captcha_manual()
                
            except Exception as e:
                logger.error(f"❌ Erro ao preencher formulário: {str(e)}")
                self.driver.switch_to.default_content()
                return False
                
        except Exception as e:
            logger.error(f"💥 Erro crítico no formulário: {str(e)}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def _verificar_pagina_consulta(self) -> bool:
        """Verificação MELHORADA que verifica dentro do iframe."""
        try:
            current_url = self.driver.current_url
            logger.info(f"🔍 Verificando página: {current_url}")
            
            # Se está na página do acesso restrito, verificar se tem iframe com formulário
            if "acessoRestrito" in current_url:
                logger.info("📍 Está na página do acesso restrito - verificando iframe...")
                
                try:
                    # Entrar no iframe para verificar
                    iframe = self.driver.find_element(By.ID, "iNetaccess")
                    self.driver.switch_to.frame(iframe)
                    
                    # Verificar se tem elementos do formulário
                    try:
                        self.driver.find_element(By.ID, "cmpDataInicial")
                        self.driver.find_element(By.ID, "cmpDataFinal")
                        logger.info("✅ ✅ ✅ FORMULÁRIO ENCONTRADO DENTRO DO IFRAME!")
                        self.driver.switch_to.default_content()
                        return True
                    except:
                        logger.info("❌ Formulário não encontrado dentro do iframe")
                        self.driver.switch_to.default_content()
                        return False
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao verificar iframe: {e}")
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass
                    return False
            
            # Verificação normal para URLs diretas
            return "consulta-notas-recebidas" in current_url
            
        except Exception as e:
            logger.error(f"❌ Erro na verificação: {e}")
            return False
    
    def _captcha_manual(self) -> bool:
        """Captcha manual - dentro do iframe."""
        logger.info("🛡️  CAPTCHA REQUERIDO")
        
        # 🔧 PRIMEIRO: ENTRAR NO IFRAME PARA MOSTRAR O CAPTCHA
        try:
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            self.driver.switch_to.frame(iframe)
            logger.info("✅ Dentro do iframe para captcha")
        except:
            logger.info("ℹ️  Não conseguiu entrar no iframe para captcha")
        
        print("\n" + "="*50)
        print("🚨 RESOLVA O CAPTCHA NO NAVEGADOR!")
        print("="*50)
        print("1. Resolva o CAPTCHA na janela do Chrome")
        print("2. Aguarde o processamento") 
        print("3. Volte e pressione ENTER")
        print("="*50)
        
        try:
            # 🔧 VOLTAR PARA CONTEÚDO PRINCIPAL ANTES DO INPUT
            self.driver.switch_to.default_content()
            
            input("\n👉 ENTER após resolver o CAPTCHA: ")
            logger.info("✅ Captcha resolvido")
            time.sleep(2)
            return True
        except:
            logger.info("ℹ️  Continuando...")
            return True
    
    def _executar_consulta(self) -> bool:
        """Executar consulta DENTRO do iframe."""
        logger.info("🔍 EXECUTANDO CONSULTA DENTRO DO IFRAME...")
        
        try:
            # 🔧 PRIMEIRO: ENTRAR NO IFRAME
            logger.info("🔍 Entrando no iframe para executar consulta...")
            
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("✅ ✅ ✅ DENTRO DO IFRAME PARA CONSULTA!")
            except Exception as e:
                logger.error(f"❌ Não conseguiu entrar no iframe: {e}")
                return False
            
            # 🔧 SEGUNDO: CLICAR NO BOTÃO PESQUISAR
            logger.info("🖱️ Clicando no botão Pesquisar...")
            
            try:
                # Tentar encontrar o botão pelo ID
                botao_pesquisar = self.driver.find_element(By.ID, "btnPesquisar")
                logger.info("✅ Botão Pesquisar encontrado!")
                
                # Clicar no botão
                botao_pesquisar.click()
                logger.info("✅ ✅ ✅ CONSULTA EXECUTADA COM SUCESSO!")
                
            except Exception as e:
                logger.error(f"❌ Erro ao clicar no botão: {e}")
                
                # 🔍 TENTAR OUTROS SELETORES
                logger.info("🔍 Tentando seletores alternativos...")
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
                        logger.info(f"✅ Clicado com seletor alternativo: {seletor[1]}")
                        break
                    except:
                        continue
                else:
                    logger.error("❌ Nenhum seletor alternativo funcionou")
                    self.driver.switch_to.default_content()
                    return False
            
            # 🔧 TERCEIRO: VOLTAR PARA CONTEÚDO PRINCIPAL E AGUARDAR
            self.driver.switch_to.default_content()
            logger.info("⏳ Aguardando resultados da consulta...")
            time.sleep(8)  # Mais tempo para carregar resultados
            
            return True
                
        except Exception as e:
            logger.error(f"💥 Erro na execução da consulta: {str(e)}")
            # Tentar voltar para conteúdo principal em caso de erro
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def limpar_recursos(self):
        """Mantém navegador aberto."""
        logger.info("🔍 NAVEGADOR MANTIDO ABERTO")
        print("\n" + "="*60)
        print("✅ Fluxo concluído - Navegador aberto para inspeção")
        print("="*60)
