import re
import os
import time
import logging
from datetime import datetime
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .retry_manager import gerenciador_retry
from .iframe_manager import GerenciadorIframe
from ..utils.data_models import ResultadoDownload

logger = logging.getLogger(__name__)


class GerenciadorDownload:
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        self.gerenciador_iframe = GerenciadorIframe(driver)
        self.estatisticas_erros = {}
        
    def _deve_tentar_novamente(self, erro: Exception, tentativa: int, operacao: str) -> bool:
        """Decide se deve retentar baseado no tipo de erro"""
        erros_fatais = [
            'FileNotFoundError',
            'PermissionError', 
            'ElementNotInteractableException'
        ]
        
        self.estatisticas_erros[operacao] = self.estatisticas_erros.get(operacao, 0) + 1
        
        erro_str = str(erro).lower()
        
        if any(msg in erro_str for msg in ['timeout', 'stale', 'click', 'temporarily']):
            return True
        
        if any(fatal in str(type(erro)) for fatal in erros_fatais):
            return False
            
        return tentativa < 2
    
    def criar_estrutura_pastas(self, nome_empresa: str, data_referencia: datetime = None) -> str:
        if data_referencia is None:
            data_referencia = datetime.now()
            
        ano = data_referencia.strftime("%Y")
        mes = data_referencia.strftime("%m")
        
        # Limpar caracteres inválidos do nome
        nome_limpo = re.sub(r'[<>:"/\\|?*]', '_', nome_empresa.strip())
        
        pasta_destino = Path.home() / "Downloads" / "SEFAZ" / nome_limpo / ano / mes
        os.makedirs(pasta_destino, exist_ok=True)
        
        return str(pasta_destino)
    
    def tem_notas_tabela(self) -> bool:
        """Verifica rapidamente se existe pelo menos uma nota na tabela"""
        try:
            with self.gerenciador_iframe.contexto_iframe((By.ID, "iNetaccess")):
                seletores_rapidos = [
                    "//table//tr[contains(@class, 'tbody-row')]",
                    "//table//tr[position()>1]",
                    "//tbody/tr"
                ]
                
                for seletor in seletores_rapidos:
                    try:
                        if self.driver.find_elements(By.XPATH, seletor):
                            return True
                    except:
                        continue
                return False
        except Exception:
            return False
    
    def _clicar_botao_baixar_xml(self) -> bool:
        def tentar_clicar_botao():
            with self.gerenciador_iframe.contexto_iframe((By.ID, "iNetaccess")):
                seletores_botao = [
                    (By.XPATH, "//button[contains(text(), 'Baixar XML')]"),
                    (By.XPATH, "//a[contains(text(), 'Baixar XML')]"),
                    (By.ID, "btnBaixarXml"),
                    (By.XPATH, "//button[contains(@onclick, 'baixar')]"),
                    (By.XPATH, "//button[contains(@class, 'btn') and contains(text(), 'Baixar')]")
                ]
                
                for seletor in seletores_botao:
                    try:
                        botao = self.driver.find_element(*seletor)
                        if botao.is_displayed() and botao.is_enabled():
                            self.driver.execute_script("arguments[0].click();", botao)
                            return True
                    except:
                        continue
                
                return False
        
        return gerenciador_retry.executar_com_retry(
            tentar_clicar_botao, max_tentativas=3, nome_operacao="Clicar Botão Baixar XML"
        )
    
    def _processar_modal_download(self) -> bool:
        """Processa a modal de confirmação de download"""
        def tentar_processar_modal():
            try:
                timeout_modal = self._obter_timeout_operacao('modal')  # NOVO
                wait_modal = WebDriverWait(self.driver, timeout_modal)  # NOVO
                
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                
                # Aguardar modal aparecer com timeout específico
                modal = wait_modal.until(  # MODIFICADO
                    EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Confirme a solicitação')]"))
                )
                # Selecionar opção documentos e eventos
                opcao = self.driver.find_element(
                    By.XPATH, "//label[contains(text(), 'Baixar documentos e eventos')]"
                )
                self.driver.execute_script("arguments[0].click();", opcao)
                
                # Clicar em confirmar
                botao_confirmar = self.driver.find_element(By.ID, "dnwld-all-btn-ok")
                self.driver.execute_script("arguments[0].click();", botao_confirmar)
                
                self.driver.switch_to.default_content()
                time.sleep(3)
                return True
                
            except Exception as e:
                logger.error(f"Erro na modal: {e}")
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False
        
        return gerenciador_retry.executar_com_retry(
            tentar_processar_modal,
            max_tentativas=2,
            delay=2,
            nome_operacao="Processar Modal Download"
        )
    
    def _processar_historico_downloads(self) -> bool:
        """Processa links do histórico de downloads"""
        def tentar_processar_historico():
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                
                # Buscar todos os links de download
                links_download = self.driver.find_elements(By.CSS_SELECTOR, "a.btn.btn-info")
                
                downloads_realizados = 0
                for link in links_download[:1]:  # Apenas primeiro link
                    try:
                        if "Baixar XML" in link.text:
                            self.driver.execute_script("arguments[0].click();", link)
                            downloads_realizados += 1
                            time.sleep(2)
                            break  # Apenas um download
                    except Exception as e:
                        logger.error(f"Erro ao clicar link: {e}")
                        continue
                
                self.driver.switch_to.default_content()
                return downloads_realizados > 0
                
            except Exception as e:
                logger.error(f"Erro no histórico: {e}")
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False
        
        return gerenciador_retry.executar_com_retry(
            tentar_processar_historico,
            max_tentativas=2,
            delay=2,
            nome_operacao="Processar Histórico"
        )
    
    def executar_fluxo_download_completo(self, nome_empresa: str, mes_referencia: datetime = None) -> ResultadoDownload:
        tem_notas = self.tem_notas_tabela() > 0
        
        if not tem_notas:
            return ResultadoDownload(
                total_encontrado=0, total_baixado=0, erros=["Sem notas"],
                notas_baixadas=[], caminho_download=""
            )
        
        pasta_destino = self.criar_estrutura_pastas(nome_empresa, mes_referencia)
        
        try:
            if (self._clicar_botao_baixar_xml() and 
                self._processar_modal_download() and 
                self._processar_historico_downloads()):
                
                arquivos_baixados = self.organizar_arquivos_baixados(pasta_destino)
                
                return ResultadoDownload(
                    total_encontrado=1 if tem_notas else 0,
                    total_baixado=len(arquivos_baixados),
                    erros=[], notas_baixadas=arquivos_baixados, caminho_download=pasta_destino
                )
            else:
                return ResultadoDownload(
                    total_encontrado=1 if tem_notas else 0, total_baixado=0,
                    erros=["Falha no fluxo"], notas_baixadas=[], caminho_download=pasta_destino
                )
        except Exception as e:
            return ResultadoDownload(
                total_encontrado=1 if tem_notas else 0, total_baixado=0,
                erros=[f"Erro: {str(e)}"], notas_baixadas=[], caminho_destination=pasta_destino
            )
    
    def processar_download_unico(self, ie: str, mes_referencia: datetime = None) -> ResultadoDownload:
        """Mantido para compatibilidade - usa fluxo completo"""
        return self.executar_fluxo_download_completo(ie, mes_referencia)
    
    def organizar_arquivos_baixados(self, pasta_destino: str) -> int:
        arquivos_movidos = []
        
        try:
            downloads_dir = Path.home() / "Downloads"
            time.sleep(8)
            
            for arquivo in downloads_dir.glob("*.zip"):
                if not self._validar_arquivo_download(arquivo):
                    continue
                    
                caminho_destino = Path(pasta_destino) / arquivo.name
                
                if caminho_destino.exists():
                    caminho_destino.unlink() 
                
                # Mover arquivo
                arquivo.rename(caminho_destino)
                arquivos_movidos.append(arquivo.name)
                    
            logger.info(f"Organizados {len(arquivos_movidos)} arquivo(s) em {pasta_destino}")
            return arquivos_movidos
            
        except Exception as e:
            logger.error(f"Erro ao organizar arquivos: {e}")
            return arquivos_movidos

    def _validar_arquivo_download(self, arquivo: Path) -> bool:
        """Valida se o arquivo é um download válido do SEFAZ - abordagem simples"""
        try:
            if not arquivo.exists():
                return False
                
            if arquivo.stat().st_size < 1000:
                return False
                
            nome = arquivo.name
            return (nome.endswith('.zip') and 
                    '_' in nome and 
                    nome.count('_') >= 3)
            
        except Exception:
            return False

    def _sao_arquivos_iguais(self, arquivo1: Path, arquivo2: Path) -> bool:
        """No contexto SEFAZ, arquivos com mesmo nome são sempre substituições"""
        try:
            if not (arquivo1.exists() and arquivo2.exists()):
                return False
                
            # Remover o antigo e mover o novo
            arquivo2.unlink()
            return True
                    
        except Exception:
            return False
        
    def _obter_timeout_operacao(self, operacao: str) -> int:
        """Timeout específico por tipo de operação"""
        timeouts = {
            'modal': 10,
            'download_link': 30,
            'arquivo_download': 60,
            'processamento_servidor': 15
        }
        timeout = timeouts.get(operacao, 15)
        logger.debug(f"Timeout para {operacao}: {timeout}s")
        return timeout