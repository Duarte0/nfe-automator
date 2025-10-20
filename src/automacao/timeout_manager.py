# timeout_manager.py
import logging
import time
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class TimeoutManager:
    def __init__(self):
        self.timeouts_base = {
            'page_load': 10,
            'element_wait': 15,
            'action_delay': 2,
            'login_wait': 5,
            'popup_wait': 10,
            'captcha_wait': 60
        }
        self.estatisticas_tempo = {
            'page_loads': [],
            'element_waits': [],
            'actions': []
        }
        self.fator_adaptacao = 1.0
    
    def registrar_tempo_operacao(self, tipo: str, tempo_decorrido: float):
        """Registra tempo de operações para adaptação futura"""
        if tipo in self.estatisticas_tempo:
            self.estatisticas_tempo[tipo].append(tempo_decorrido)
            
            if len(self.estatisticas_tempo[tipo]) > 10:
                self.estatisticas_tempo[tipo].pop(0)
            
            self._atualizar_fator_adaptacao()
    
    def _atualizar_fator_adaptacao(self):
        """Atualiza fator de adaptação baseado nos tempos recentes"""
        tempos_recentes = []
        
        for tipo, tempos in self.estatisticas_tempo.items():
            if tempos:
                tempos_recentes.extend(tempos[-3:]) 
        if not tempos_recentes:
            return
        
        tempo_medio = sum(tempos_recentes) / len(tempos_recentes)
        
        if tempo_medio > 8.0:   # Muito lento
            self.fator_adaptacao = 1.5
        elif tempo_medio > 5.0:  # Lento
            self.fator_adaptacao = 1.2
        elif tempo_medio < 2.0:  # Rápido
            self.fator_adaptacao = 0.8
        else:  # Normal
            self.fator_adaptacao = 1.0
        
        logger.debug(f"Fator adaptação: {self.fator_adaptacao:.1f} (tempo médio: {tempo_medio:.1f}s)")
    
    def get_timeout(self, tipo: str) -> int:
        """Retorna timeout adaptado para o tipo de operação"""
        timeout_base = self.timeouts_base.get(tipo, 10)
        timeout_adaptado = int(timeout_base * self.fator_adaptacao)
        
        # Limites mínimos e máximos
        timeout_adaptado = max(5, min(timeout_adaptado, 30))
        
        return timeout_adaptado
    
    def get_delay(self, tipo: str) -> float:
        """Retorna delay adaptado para ações"""
        delay_base = self.timeouts_base.get(tipo, 2)
        delay_adaptado = delay_base * self.fator_adaptacao
        
        # Limites para delays
        delay_adaptado = max(1.0, min(delay_adaptado, 5.0))
        
        return delay_adaptado
    
    def obter_relatorio(self) -> Dict:
        """Retorna relatório de performance"""
        return {
            'fator_adaptacao': self.fator_adaptacao,
            'timeouts_atuais': {tipo: self.get_timeout(tipo) for tipo in self.timeouts_base},
            'estatisticas': {tipo: len(tempos) for tipo, tempos in self.estatisticas_tempo.items()}
        }