import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from config import CONFIG

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SEFAZAutomator:
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Configura o Chrome Driver com opções otimizadas"""
        try:
            options = webdriver.ChromeOptions()
            
            # Otimizações para evitar detecção
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Para desenvolvimento, manter visível
            # options.add_argument("--headless")  # Descomente em produção
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Enganar detecção de automation
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 20)
            logger.info("✅ Driver configurado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao configurar driver: {e}")
            return False

    def login(self):
        """Realiza login no sistema SEFAZ"""
        try:
            logger.info("🌐 Navegando para SEFAZ Goiás")
            self.driver.get("https://www.sefaz.go.gov.br/netaccess/000System/acessoRestrito/")
            time.sleep(3)
            
            # Preencher credenciais
            usuario_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            usuario_field.clear()
            usuario_field.send_keys(CONFIG['usuario'])
            
            senha_field = self.driver.find_element(By.ID, "password")
            senha_field.clear()
            senha_field.send_keys(CONFIG['senha'])
            
            logger.info("🔑 Credenciais preenchidas, realizando login...")
            login_btn = self.driver.find_element(By.ID, "btnAuthenticate")
            login_btn.click()
            
            # Aguardar login
            time.sleep(5)
            
            if "acessoRestrito" in self.driver.current_url:
                logger.info("✅ Login realizado com sucesso")
                return True
            else:
                logger.error("❌ Falha no login - verifique credenciais")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro no login: {e}")
            return False

    def navegar_para_download_xml(self):
        """Navega até a página de download de XML"""
        try:
            logger.info("📂 Navegando para Download XML...")
            time.sleep(3)
            
            # Usar XPath pelo texto do link
            menu_xml = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Baixar XML NFE')]"))
            )
            menu_xml.click()
            
            # Aguardar carregamento da nova página
            time.sleep(5)
            
            if "consulta-notas-recebidas" in self.driver.current_url:
                logger.info("✅ Navegação para Download XML concluída")
                return True
            else:
                logger.warning("⚠️ Possível problema na navegação")
                return True  # Continua mesmo com warning
                
        except Exception as e:
            logger.error(f"❌ Erro na navegação: {e}")
            return False

    def preencher_formulario(self):
        """Preenche o formulário de consulta"""
        try:
            logger.info("📝 Preenchendo formulário de consulta...")
            
            # Aguardar elementos do formulário
            data_inicio_field = self.wait.until(EC.presence_of_element_located((By.ID, "cmpDataInicial")))
            
            # Preencher campos
            data_inicio_field.clear()
            data_inicio_field.send_keys(CONFIG['data_inicio'])
            
            data_fim_field = self.driver.find_element(By.ID, "cmpDataFinal")
            data_fim_field.clear()
            data_fim_field.send_keys(CONFIG['data_fim'])
            
            ie_field = self.driver.find_element(By.ID, "cmpNumIeDest")
            ie_field.clear()
            ie_field.send_keys(CONFIG['inscricao_estadual'])
            
            # Selecionar modelo NF-e
            modelo_select = Select(self.driver.find_element(By.ID, "cmpModelo"))
            modelo_select.select_by_value("55")
            
            logger.info("✅ Formulário preenchido")
            logger.info("🛑 AGUARDANDO RESOLUÇÃO MANUAL DO CAPTCHA...")
            
            # Aguardar captcha manual
            input("👉 Resolva o CAPTCHA e pressione ENTER para continuar...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao preencher formulário: {e}")
            return False

    def executar_pesquisa(self):
        """Executa a pesquisa após captcha"""
        try:
            logger.info("🔍 Executando pesquisa...")
            
            pesquisar_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "btnPesquisar"))
            )
            pesquisar_btn.click()
            
            logger.info("✅ Pesquisa executada - aguardando resultados...")
            time.sleep(10)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na pesquisa: {e}")
            return False

    def run(self):
        """Executa o fluxo completo"""
        logger.info("🚀 Iniciando automação SEFAZ")
        
        if not self.setup_driver():
            return False
            
        try:
            steps = [
                self.login,
                self.navegar_para_download_xml,
                self.preencher_formulario,
                self.executar_pesquisa
            ]
            
            for step in steps:
                if not step():
                    logger.error(f"❌ Falha no passo: {step.__name__}")
                    return False
                    
            logger.info("🎉 Processo concluído com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"💥 Erro no processo: {e}")
            return False
        finally:
            if self.driver:
                input("Pressione ENTER para fechar o navegador...")
                self.driver.quit()

if __name__ == "__main__":
    automator = SEFAZAutomator()
    automator.run()