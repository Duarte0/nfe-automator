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
    
    def criar_estrutura_pastas(self, ie: str, data_referencia: datetime = None) -> str:
        if data_referencia is None:
            data_referencia = datetime.now()
            
        ano = data_referencia.strftime("%Y")
        mes = data_referencia.strftime("%m")
        
        pasta_destino = Path.home() / "Downloads" / "SEFAZ" / f"IE_{ie}" / ano / mes
        os.makedirs(pasta_destino, exist_ok=True)
        logger.info(f"Estrutura criada para IE {ie}: {pasta_destino}")
        
        return str(pasta_destino)
    
    def organizar_arquivos_baixados(self, pasta_destino: str) -> int:
        arquivos_movidos = 0
        
        try:
            downloads_dir = Path.home() / "Downloads"
            time.sleep(10)
            
            for arquivo in downloads_dir.glob("*.zip"):
                caminho_destino = Path(pasta_destino) / arquivo.name
                arquivo.rename(caminho_destino)
                logger.info(f"Arquivo movido: {arquivo.name}")
                arquivos_movidos += 1
                
            logger.info(f"Total arquivos movidos: {arquivos_movidos}")
                
        except Exception as e:
            logger.error(f"Erro ao organizar arquivos: {e}")
            
        return arquivos_movidos
    
    def contar_notas_tabela(self) -> int:
        try:
            with self.gerenciador_iframe.contexto_iframe((By.ID, "iNetaccess")):
                seletores_tabela = [
                    "//table//tr[contains(@class, 'tbody-row')]",
                    "//table//tr[position()>1]",
                    "//tbody/tr"
                ]
                
                for seletor in seletores_tabela:
                    try:
                        linhas = self.driver.find_elements(By.XPATH, seletor)
                        if linhas:
                            logger.info(f"Notas encontradas: {len(linhas)}")
                            return len(linhas)
                    except:
                        continue
                return 0
                
        except Exception as e:
            logger.warning(f"Erro ao contar notas: {e}")
            return 0
    
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
                            logger.info(f"Botão Baixar XML encontrado e clicado: {seletor[1]}")
                            return True
                    except:
                        continue
                
                return False
        
        return gerenciador_retry.executar_com_retry(
            tentar_clicar_botao, max_tentativas=3, nome_operacao="Clicar Botão Baixar XML"
        )
    
    def _processar_modal_download(self) -> bool:
        """Processa a modal de confirmação de download"""
        logger.info("Processando modal de download...")
        
        def tentar_processar_modal():
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                
                # Aguardar modal aparecer
                modal = self.wait.until(
                    EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Confirme a solicitação')]"))
                )
                logger.info("Modal detectada")
                
                # Selecionar opção documentos e eventos
                opcao = self.driver.find_element(
                    By.XPATH, "//label[contains(text(), 'Baixar documentos e eventos')]"
                )
                self.driver.execute_script("arguments[0].click();", opcao)
                logger.info("Opção selecionada")
                
                # Clicar em confirmar
                botao_confirmar = self.driver.find_element(By.ID, "dnwld-all-btn-ok")
                self.driver.execute_script("arguments[0].click();", botao_confirmar)
                logger.info("Download confirmado")
                
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
        logger.info("Processando histórico de downloads...")
        
        def tentar_processar_historico():
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                
                # Buscar todos os links de download
                links_download = self.driver.find_elements(By.CSS_SELECTOR, "a.btn.btn-info")
                logger.info(f"Encontrados {len(links_download)} links de download")
                
                downloads_realizados = 0
                for link in links_download[:1]:  # Apenas primeiro link
                    try:
                        if "Baixar XML" in link.text:
                            self.driver.execute_script("arguments[0].click();", link)
                            logger.info("Download iniciado via histórico")
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
    
    def executar_fluxo_download_completo(self, ie: str, mes_referencia: datetime = None) -> ResultadoDownload:
        logger.info(f"Iniciando download IE: {ie}")
        
        total_notas = self.contar_notas_tabela()
        logger.debug(f"Notas encontradas: {total_notas}")
        
        if total_notas == 0:
            logger.info(f"Nenhuma nota para IE {ie}")
            return ResultadoDownload(
                total_encontrado=0, total_baixado=0, erros=["Nenhuma nota"],
                notas_baixadas=[], caminho_download=""
            )
        
        pasta_destino = self.criar_estrutura_pastas(ie, mes_referencia)
        
        try:
            if (self._clicar_botao_baixar_xml() and 
                self._processar_modal_download() and 
                self._processar_historico_downloads()):
                
                arquivos_baixados = self.organizar_arquivos_baixados(pasta_destino)
                logger.info(f"Download concluído: {arquivos_baixados} arquivo(s)")
                
                return ResultadoDownload(
                    total_encontrado=total_notas,
                    total_baixado=arquivos_baixados,
                    erros=[], notas_baixadas=[], caminho_download=pasta_destino
                )
            else:
                logger.error("Falha no fluxo de download")
                return ResultadoDownload(
                    total_encontrado=total_notas, total_baixado=0,
                    erros=["Falha no fluxo"], notas_baixadas=[], caminho_download=pasta_destino
                )
                
        except Exception as e:
            logger.error(f"Erro no download: {e}")
            return ResultadoDownload(
                total_encontrado=total_notas, total_baixado=0,
                erros=[f"Erro: {str(e)}"], notas_baixadas=[], caminho_download=pasta_destino
            )
    
    def processar_download_unico(self, ie: str, mes_referencia: datetime = None) -> ResultadoDownload:
        """Mantido para compatibilidade - usa fluxo completo"""
        return self.executar_fluxo_download_completo(ie, mes_referencia)