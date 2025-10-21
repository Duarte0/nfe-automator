import pandas as pd
import logging
from pathlib import Path
from typing import List, Dict

from .validador_ie import ValidadorIE

logger = logging.getLogger(__name__)

class CarregadorIEs:
    def __init__(self, caminho_planilha: str = "dados/empresas.xlsx"):
        self.caminho_planilha = Path(caminho_planilha)
        self.validador = ValidadorIE()
    
    def carregar_empresas_validas(self) -> List[Dict]:
        """Retorna lista de dicionários com IE e Nome"""
        try:
            if not self.caminho_planilha.exists():
                logger.error(f"Planilha não encontrada: {self.caminho_planilha}")
                return []
            
            df = pd.read_excel(self.caminho_planilha)

            coluna_nome = df.columns[0] 
            coluna_ie = df.columns[2]   
            
            empresas = []
            for _, row in df.iterrows():
                ie = str(row[coluna_ie]).strip() if pd.notna(row[coluna_ie]) else ""
                nome = str(row[coluna_nome]).strip() if pd.notna(row[coluna_nome]) else f"Empresa_{ie}"
                
                # Filtrar IEs inválidas
                if ie and ie not in ['NÃO TEM', 'NAO TEM', 'N TEM', 'SEM IE']:
                    # CORREÇÃO: Tratar o retorno como tupla (valido, resultado)
                    valido, ie_normalizada = self.validador.validar_ie(ie)
                    if valido:
                        empresas.append({'ie': ie_normalizada, 'nome': nome})
                    else:
                        logger.warning(f"IE inválida ignorada: {ie} - {nome} - Motivo: {ie_normalizada}")
            
            logger.info(f"Carregadas {len(empresas)} empresas válidas")
            return empresas
            
        except Exception as e:
            logger.error(f"Erro ao carregar planilha: {e}")
            return []

    def carregar_ies_validas(self) -> List[str]:
        """Método legado - retorna apenas IEs para compatibilidade"""
        empresas = self.carregar_empresas_validas()
        return [empresa['ie'] for empresa in empresas]