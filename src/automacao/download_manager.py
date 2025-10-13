"""
Gerenciador de download de XMLs - CORRIGIDO PARA MODAL DENTRO DO IFRAME
"""

import os
import time
import logging
from datetime import datetime
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .retry_manager import gerenciador_retry
from ..utils.data_models import ResultadoDownload

logger = logging.getLogger(__name__)


class GerenciadorDownload:
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        
    def criar_pasta_download(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pasta_download = f"downloads/xml_nfe_{timestamp}"
        os.makedirs(pasta_download, exist_ok=True)
        logger.info(f"Pasta download: {pasta_download}")
        return pasta_download
    
    def contar_notas_tabela(self) -> int:
        try:
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            self.driver.switch_to.frame(iframe)
            
            try:
                elemento_container = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'table-legend-right-container') and contains(text(), 'Total de notas:')]"
                )
                
                texto_completo = elemento_container.text
                logger.info(texto_completo)
                
                import re
                match = re.search(r'Total de notas:\s*(\d+)', texto_completo)
                if match:
                    total = int(match.group(1))
                    logger.info(f"Total de notas encontrado: {total}")
                else:
                    raise Exception("Número não encontrado no texto")
                
            except Exception as e:
                logger.warning(f"Erro ao buscar total, usando fallback: {e}")
                linhas = self.driver.find_elements(By.CSS_SELECTOR, "tr.tbody-row.paginated-row")
                total = len(linhas)
                logger.info(f"Notas na página atual (fallback): {total}")
            
            self.driver.switch_to.default_content()
            return total
            
        except Exception as e:
            logger.warning(f"Erro ao contar notas: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return 0
    
    def _aguardar_modal_opcoes(self) -> bool:
        logger.info("Processando modal de download...")
        
        def tentar_selecionar_opcao():
            try:
                iframe = self.driver.find_element(By.ID, "iNetaccess")
                self.driver.switch_to.frame(iframe)
                logger.info("Dentro do iframe para modal")
            except Exception as e:
                logger.error(f"Erro ao entrar no iframe: {e}")
                raise e
            
            try:
                modal_title = self.wait.until(
                    EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Confirme a solicitação de download')]"))
                )
                logger.info("Modal detectada")
            except Exception as e:
                logger.error(f"Modal não encontrada: {e}")
                raise e
            
            try:
                label_opcao = self.driver.find_element(
                    By.XPATH, "//label[contains(text(), 'Baixar documentos e eventos')]"
                )
                self.driver.execute_script("arguments[0].click();", label_opcao)
                logger.info("Opção 'documentos e eventos' selecionada")
                time.sleep(1)
            except Exception as e:
                logger.error(f"Erro ao selecionar opção: {e}")
                raise e
            
            try:
                botao_baixar_modal = self.driver.find_element(By.ID, "dnwld-all-btn-ok")
                self.driver.execute_script("arguments[0].click();", botao_baixar_modal)
                logger.info("Botão Baixar (modal) clicado")
            except Exception as e:
                logger.error(f"Erro ao clicar no botão da modal: {e}")
                raise e
            
            self.driver.switch_to.default_content()
            
            logger.info("Aguardando histórico carregar...")
            time.sleep(5)
            
            sucesso_downloads = self._processar_historico_downloads()
            
            return sucesso_downloads
        
        try:
            return gerenciador_retry.executar_com_retry(
                tentar_selecionar_opcao,
                max_tentativas=2,
                delay=3,
                nome_operacao="Processar Modal Download"
            )
        except Exception as e:
            logger.error(f"Falha no processamento da modal: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
        
    def _processar_historico_downloads(self) -> bool:
            logger.info("Processando histórico de downloads...")
            
            def tentar_processar_historico():
                try:
                    iframe = self.driver.find_element(By.ID, "iNetaccess")
                    self.driver.switch_to.frame(iframe)
                    logger.info("Dentro do iframe do histórico")
                except Exception as e:
                    logger.error(f"Erro ao entrar no iframe: {e}")
                    raise e
                
                try:
                    titulo_historico = self.wait.until(
                        EC.visibility_of_element_located((By.XPATH, "//label[contains(text(), 'Histórico de Downloads de XMLs')]"))
                    )
                    logger.info("Histórico de downloads carregado")
                except Exception as e:
                    logger.error(f"Histórico não carregado: {e}")
                    raise e
                
                page_source = self.driver.page_source
                if "Baixar XML" in page_source:
                    logger.info("Texto 'Baixar XML' encontrado no source")
                else:
                    logger.warning("Texto 'Baixar XML' NÃO encontrado no source")
                
                links_download = []
                
                try:
                    links_download = self.driver.find_elements(
                        By.XPATH, "//a[contains(text(), 'Baixar XML')]"
                    )
                    logger.info(f"Seletor por texto: {len(links_download)} links")
                except Exception as e:
                    logger.warning(f"Seletor por texto falhou: {e}")
                
                if not links_download:
                    try:
                        links_download = self.driver.find_elements(
                            By.CSS_SELECTOR, "a.btn.btn-info"
                        )
                        logger.info(f"Seletor por classe: {len(links_download)} links")
                    except Exception as e:
                        logger.warning(f"Seletor por classe falhou: {e}")
                
                if not links_download:
                    try:
                        links_download = self.driver.find_elements(
                            By.XPATH, "//a[contains(@class, 'glyphicon-circle-arrow-down')]"
                        )
                        logger.info(f"Seletor por ícone: {len(links_download)} links")
                    except Exception as e:
                        logger.warning(f"Seletor por ícone falhou: {e}")
                
                if not links_download:
                    try:
                        links_download = self.driver.find_elements(
                            By.CSS_SELECTOR, "table a"
                        )
                        logger.info(f"Seletor genérico: {len(links_download)} links")
                    except Exception as e:
                        logger.warning(f"Seletor genérico falhou: {e}")
                
                logger.info(f"Total de links encontrados: {len(links_download)}")
                
                if not links_download:
                    logger.info("Analisando estrutura da tabela...")
                    try:
                        linhas_tabela = self.driver.find_elements(By.CSS_SELECTOR, "tr.tbody-row.paginated-row")
                        logger.info(f"Linhas na tabela: {len(linhas_tabela)}")
                        
                        for i, linha in enumerate(linhas_tabela):
                            logger.info(f"Linha {i+1}: {linha.get_attribute('outerHTML')[:200]}...")
                    except Exception as e:
                        logger.error(f"Erro ao analisar tabela: {e}")
                
                downloads_realizados = 0
                for i, link in enumerate(links_download):
                    try:
                        link_text = link.text
                        link_href = link.get_attribute('href')
                        
                        logger.info(f"Link {i+1}: texto='{link_text}', href='{link_href}'")
                        
                        if "Baixar XML" in link_text and link_href:
                            # Clicar no link de download
                            self.driver.execute_script("arguments[0].click();", link)
                            logger.info(f"Download iniciado: {link_text}")
                            downloads_realizados += 1
                            
                            time.sleep(2)
                            
                    except Exception as e:
                        logger.error(f"Erro ao processar link {i+1}: {e}")
                        continue
                
                self.driver.switch_to.default_content()
                
                logger.info(f"Downloads realizados: {downloads_realizados}/{len(links_download)}")
                return downloads_realizados > 0
            
            try:
                return gerenciador_retry.executar_com_retry(
                    tentar_processar_historico,
                    max_tentativas=2,
                    delay=3,
                    nome_operacao="Processar Historico Downloads"
                )
            except Exception as e:
                logger.error(f"Falha no processamento do histórico: {e}")
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                return False

    def baixar_todos_arquivos(self) -> bool:
        logger.info("Iniciando download em lote...")
        
        def executar_download_lote():
            iframe = self.driver.find_element(By.ID, "iNetaccess")
            self.driver.switch_to.frame(iframe)
            
            try:
                botao_todos = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Baixar todos os arquivos')]")
                self.driver.execute_script("arguments[0].click();", botao_todos)
                logger.info("Botão 'Baixar todos os arquivos' clicado")
            except Exception as e:
                logger.error(f"Erro ao clicar no botão de download em lote: {e}")
                try:
                    botao_todos = self.driver.find_element(By.CLASS_NAME, "btn-download-all")
                    self.driver.execute_script("arguments[0].click();", botao_todos)
                    logger.info("Botão de download em lote clicado via classe")
                except:
                    self.driver.switch_to.default_content()
                    raise e
            
            self.driver.switch_to.default_content()
            
            sucesso_modal = self._aguardar_modal_opcoes()
            
            return sucesso_modal
        
        try:
            return gerenciador_retry.executar_com_retry(
                executar_download_lote,
                max_tentativas=3,
                delay=5,
                nome_operacao="Download Lote"
            )
        except Exception as e:
            logger.error(f"Falha download lote: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False
    
    def processar_download_lote(self) -> ResultadoDownload:
        logger.info("Processando download em lote...")
        
        pasta_download = self.criar_pasta_download()
        total_notas = self.contar_notas_tabela()
        
        if total_notas == 0:
            logger.warning("Nenhuma nota encontrada")
            return ResultadoDownload(
                total_encontrado=0,
                total_baixado=0,
                erros=["Nenhuma nota na tabela"],
                notas_baixadas=[],
                caminho_download=pasta_download
            )
        
        logger.info(f"Download lote para {total_notas} notas")
        
        sucesso = self.baixar_todos_arquivos()
        
        if sucesso:
            logger.info("Download lote concluído")
            return ResultadoDownload(
                total_encontrado=total_notas,
                total_baixado=total_notas, 
                erros=[],
                notas_baixadas=[],
                caminho_download=pasta_download
            )
        else:
            logger.error("Falha no download lote")
            return ResultadoDownload(
                total_encontrado=total_notas,
                total_baixado=0,
                erros=["Falha no download em lote"],
                notas_baixadas=[],
                caminho_download=pasta_download
            )