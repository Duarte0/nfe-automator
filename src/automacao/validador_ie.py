# validador_ie.py
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class ValidadorIE:
    @staticmethod
    def validar_formato_ie(ie: str) -> Tuple[bool, str]:
        """Valida formato básico da Inscrição Estadual"""
        if not ie or not isinstance(ie, str):
            return False, "IE vazia ou não é string"
        
        # Limpar caracteres não numéricos
        ie_limpa = re.sub(r'[^\d]', '', ie)
        
        # Verificar comprimento típico de IE
        if len(ie_limpa) < 8 or len(ie_limpa) > 14:
            return False, f"IE com comprimento inválido: {len(ie_limpa)} dígitos"
        
        # Verificar se não é sequência de zeros
        if ie_limpa == '0' * len(ie_limpa):
            return False, "IE é sequência de zeros"
        
        # Verificar se tem dígitos válidos
        if not ie_limpa.isdigit():
            return False, "IE contém caracteres inválidos"
        
        return True, ie_limpa
    
    @staticmethod
    def normalizar_ie(ie: str) -> str:
        """Normaliza IE removendo caracteres não numéricos"""
        return re.sub(r'[^\d]', '', ie)
    
    @staticmethod
    def filtrar_ies_validas(ies: List[str]) -> List[str]:
        """Filtra lista de IEs, removendo inválidas e retornando normalizadas"""
        ies_validas = []
        ies_invalidas = []
        
        for ie in ies:
            valido, resultado = ValidadorIE.validar_formato_ie(ie)
            if valido:
                ies_validas.append(resultado)  # resultado já é a IE normalizada
            else:
                ies_invalidas.append((ie, resultado))
        
        if ies_invalidas:
            logger.warning(f"Removidas {len(ies_invalidas)} IEs inválidas")
            for ie, motivo in ies_invalidas[:5]:  # Mostra apenas as 5 primeiras
                logger.debug(f"IE inválida: '{ie}' - {motivo}")
        
        logger.info(f"Total IEs válidas: {len(ies_validas)}")
        return ies_validas
    
    @staticmethod
    def validar_lote_ies(ies: List[str]) -> dict:
        """Retorna relatório detalhado da validação do lote"""
        relatorio = {
            'total_ies': len(ies),
            'validas': [],
            'invalidas': [],
            'taxa_validade': 0
        }
        
        for ie in ies:
            valido, resultado = ValidadorIE.validar_formato_ie(ie)
            if valido:
                relatorio['validas'].append(resultado)
            else:
                relatorio['invalidas'].append({'ie': ie, 'motivo': resultado})
        
        if relatorio['total_ies'] > 0:
            relatorio['taxa_validade'] = (len(relatorio['validas']) / relatorio['total_ies']) * 100
        
        return relatorio