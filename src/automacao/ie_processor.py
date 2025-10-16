import pandas as pd
import logging
from pathlib import Path
from typing import List
import re

logger = logging.getLogger(__name__)

class ProcessadorPlanilhaIEs:
    def __init__(self, caminho_planilha: str = "dados/empresas.xlsx"):
        self.caminho_planilha = Path(caminho_planilha)
    
    def carregar_ies_validas(self) -> List[str]:
        try:
            if not self.caminho_planilha.exists():
                logger.error(f"Planilha não encontrada: {self.caminho_planilha}")
                return []
            
            df = pd.read_excel(self.caminho_planilha)
            colunas = list(df.columns)
            coluna_ie = colunas[2] if len(colunas) > 2 else colunas[-1]
            
            ies_validas = []
            for ie in df[coluna_ie].dropna():
                ie_str = str(ie).replace('.0', '')
                if (ie_str not in ['NÃO TEM', 'NAO TEM', 'N TEM'] and 
                    len(ie_str) <= 15 and 
                    ie_str.replace('.', '').isdigit()):
                    ies_validas.append(ie_str)
            
            logger.info(f"Carregadas {len(ies_validas)} IEs válidas")
            return ies_validas
            
        except Exception as e:
            logger.error(f"Erro ao carregar planilha: {e}")
            return []