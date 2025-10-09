import time
import logging
from typing import Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GerenciadorRetry:
    """
    Gerencia tentativas automáticas com estatísticas
    """
    
    def __init__(self):
        self.estatisticas = {
            'total_operacoes': 0,
            'operacoes_com_retry': 0,
            'total_tentativas': 0,
            'sucessos_apos_retry': 0
        }
    
    def executar_com_retry(
        self, 
        funcao: Callable, 
        max_tentativas: int = 3, 
        delay: float = 2,
        nome_operacao: str = "Operação"
    ) -> Any:
        """
        Executa função com múltiplas tentativas e coleta estatísticas.
        """
        self.estatisticas['total_operacoes'] += 1
        ultima_excecao = None
        inicio = datetime.now()
        
        for tentativa in range(1, max_tentativas + 1):
            self.estatisticas['total_tentativas'] += 1
            
            try:
                logger.debug(f"{nome_operacao} - Tentativa {tentativa}/{max_tentativas}")
                resultado = funcao()
                
                # Registrar se houve retry
                if tentativa > 1:
                    self.estatisticas['operacoes_com_retry'] += 1
                    self.estatisticas['sucessos_apos_retry'] += 1
                    tempo_decorrido = (datetime.now() - inicio).total_seconds()
                    logger.info(f"{nome_operacao} - Sucesso após {tentativa} tentativas ({tempo_decorrido:.1f}s)")
                else:
                    logger.debug(f"{nome_operacao} - Sucesso na primeira tentativa")
                
                return resultado
                
            except Exception as e:
                ultima_excecao = e
                
                if tentativa == max_tentativas:
                    tempo_decorrido = (datetime.now() - inicio).total_seconds()
                    logger.error(f"{nome_operacao} - Falha após {max_tentativas} tentativas ({tempo_decorrido:.1f}s): {e}")
                    break
                
                logger.warning(f"{nome_operacao} - Tentativa {tentativa} falhou, retry em {delay}s: {e}")
                time.sleep(delay)
        
        raise ultima_excecao
    
    def obter_estatisticas(self) -> dict:
        """Retorna estatísticas de uso do retry."""
        return self.estatisticas.copy()
    
    def limpar_estatisticas(self):
        """Limpa as estatísticas."""
        self.estatisticas = {
            'total_operacoes': 0,
            'operacoes_com_retry': 0,
            'total_tentativas': 0,
            'sucessos_apos_retry': 0
        }


# Instância global
gerenciador_retry = GerenciadorRetry()