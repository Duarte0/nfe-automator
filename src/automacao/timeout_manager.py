import logging
import time
from typing import Dict, List
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class TipoOperacao(Enum):
    PAGINA_CARREGAMENTO = "page_load"
    ELEMENTO_WAIT = "element_wait" 
    ACAO_CLIQUE = "action_click"
    LOGIN = "login_wait"
    POPUP = "popup_wait"
    CAPTCHA = "captcha_wait"
    DOWNLOAD = "download_wait"
    CONSULTA = "consulta_wait"
    MODAL = "modal_wait"

class EstadoServidor(Enum):
    OTIMO = "otimo"
    NORMAL = "normal"
    LENTO = "lento"
    INSTAVEL = "instavel"

class TimeoutManager:
    def __init__(self):
        self.timeouts_base = {
            TipoOperacao.PAGINA_CARREGAMENTO: 10,
            TipoOperacao.ELEMENTO_WAIT: 15,
            TipoOperacao.ACAO_CLIQUE: 2,
            TipoOperacao.LOGIN: 5,
            TipoOperacao.POPUP: 10,
            TipoOperacao.CAPTCHA: 60,
            TipoOperacao.DOWNLOAD: 30,
            TipoOperacao.CONSULTA: 20,
            TipoOperacao.MODAL: 10
        }
        
        self.estatisticas_tempo = {
            op_type: [] for op_type in TipoOperacao
        }
        
        self.erros_recentes = []
        self.estado_servidor = EstadoServidor.NORMAL
        self.fator_adaptacao = 1.0
        self.padroes_horario = {}
        
        # Configurações de adaptação
        self.config_adaptacao = {
            'max_timeout': 60,
            'min_timeout': 3,
            'max_backoff': 5,
            'janela_estatisticas': 20,  # últimas 20 operações
            'limite_erros_instavel': 3,  # 3 erros consecutivos = instável
        }
    
    def registrar_tempo_operacao(self, tipo: TipoOperacao, tempo_decorrido: float, sucesso: bool = True):
        """Registra tempo de operação para adaptação futura"""
        try:
            # Adicionar à lista de estatísticas
            if tipo in self.estatisticas_tempo:
                self.estatisticas_tempo[tipo].append({
                    'tempo': tempo_decorrido,
                    'sucesso': sucesso,
                    'timestamp': datetime.now()
                })
                
                # Manter apenas as últimas operações
                if len(self.estatisticas_tempo[tipo]) > self.config_adaptacao['janela_estatisticas']:
                    self.estatisticas_tempo[tipo].pop(0)
            
            # Registrar erros
            if not sucesso:
                self.erros_recentes.append({
                    'tipo': tipo,
                    'timestamp': datetime.now()
                })
                # Limpar erros antigos (últimos 10 minutos)
                self.erros_recentes = [
                    erro for erro in self.erros_recentes 
                    if (datetime.now() - erro['timestamp']).total_seconds() < 600
                ]
            
            self._atualizar_estado_servidor()
            self._atualizar_fator_adaptacao()
            
        except Exception as e:
            logger.error(f"Erro ao registrar tempo de operação: {e}")
    
    def _atualizar_estado_servidor(self) -> EstadoServidor:
        """Atualiza estado do servidor baseado em performance recente"""
        
        # Calcular taxa de erro recente
        total_operacoes = sum(len(ops) for ops in self.estatisticas_tempo.values())
        if total_operacoes == 0:
            return EstadoServidor.NORMAL
        
        erros_recentes = sum(1 for ops in self.estatisticas_tempo.values() 
                           for op in ops if not op['sucesso'])
        taxa_erro = erros_recentes / total_operacoes
        
        # Calcular tempo médio recente
        tempos_recentes = []
        for ops in self.estatisticas_tempo.values():
            tempos_recentes.extend([op['tempo'] for op in ops[-5:]])  # Últimas 5 de cada tipo
        
        if not tempos_recentes:
            return EstadoServidor.NORMAL
        
        tempo_medio = sum(tempos_recentes) / len(tempos_recentes)
        
        # Determinar estado
        if taxa_erro > 0.3 or len(self.erros_recentes) >= self.config_adaptacao['limite_erros_instavel']:
            novo_estado = EstadoServidor.INSTAVEL
        elif tempo_medio > 8.0:
            novo_estado = EstadoServidor.LENTO
        elif tempo_medio < 3.0:
            novo_estado = EstadoServidor.OTIMO
        else:
            novo_estado = EstadoServidor.NORMAL
        
        if novo_estado != self.estado_servidor:
            logger.info(f"Estado do servidor alterado: {self.estado_servidor.value} -> {novo_estado.value}")
            self.estado_servidor = novo_estado
        
        return novo_estado
    
    def _atualizar_fator_adaptacao(self):
        """Atualiza fator de adaptação baseado no estado do servidor"""
        fatores_estado = {
            EstadoServidor.OTIMO: 0.7,
            EstadoServidor.NORMAL: 1.0,
            EstadoServidor.LENTO: 1.5,
            EstadoServidor.INSTAVEL: 2.0
        }
        
        # Fator baseado no estado
        fator_estado = fatores_estado.get(self.estado_servidor, 1.0)
        
        # Ajuste adicional baseado em horário (SEFAZ costuma ser mais lento em horários comerciais)
        hora_atual = datetime.now().hour
        if 9 <= hora_atual <= 11 or 14 <= hora_atual <= 16:  # Horários de pico
            fator_horario = 1.2
        elif 0 <= hora_atual <= 6:  # Madrugada - geralmente mais rápido
            fator_horario = 0.8
        else:
            fator_horario = 1.0
        
        self.fator_adaptacao = fator_estado * fator_horario
        logger.debug(f"Fator adaptação: {self.fator_adaptacao:.2f} (estado: {self.estado_servidor.value})")
    
    def get_timeout(self, tipo: TipoOperacao, tentativa: int = 1) -> int:
        """Retorna timeout adaptado para o tipo de operação e tentativa"""
        try:
            timeout_base = self.timeouts_base.get(tipo, 10)
            
            # Aplicar fator de adaptação
            timeout_adaptado = timeout_base * self.fator_adaptacao
            
            # Aplicar backoff exponencial para tentativas
            if tentativa > 1:
                backoff = min(2 ** (tentativa - 1), self.config_adaptacao['max_backoff'])
                timeout_adaptado *= backoff
            
            # Limites mínimos e máximos
            timeout_adaptado = max(
                self.config_adaptacao['min_timeout'], 
                min(timeout_adaptado, self.config_adaptacao['max_timeout'])
            )
            
            timeout_final = int(timeout_adaptado)
            
            logger.debug(f"Timeout {tipo.value}: {timeout_final}s (tentativa {tentativa}, estado: {self.estado_servidor.value})")
            return timeout_final
            
        except Exception as e:
            logger.error(f"Erro ao calcular timeout: {e}")
            return self.timeouts_base.get(tipo, 10)
    
    def get_delay(self, tipo: TipoOperacao) -> float:
        """Retorna delay adaptado para ações"""
        try:
            delay_base = self.timeouts_base.get(tipo, 2)
            delay_adaptado = delay_base * self.fator_adaptacao
            
            # Limites para delays (mais restritos que timeouts)
            delay_adaptado = max(1.0, min(delay_adaptado, 10.0))
            
            return delay_adaptado
            
        except Exception as e:
            logger.error(f"Erro ao calcular delay: {e}")
            return 2.0
    
    def calcular_backoff_erro(self, tipo_erro: str, tentativa: int) -> float:
        """Calcula backoff inteligente para erros específicos"""
        backoffs_especificos = {
            'timeout': 2,
            'element_not_found': 3,
            'stale_element': 1,
            'connection_error': 5,
            'captcha_failed': 10
        }
        
        base_backoff = backoffs_especificos.get(tipo_erro, 2)
        backoff = base_backoff * (1.5 ** (tentativa - 1))
        
        # Limitar backoff máximo
        backoff = min(backoff, 30)
        
        logger.debug(f"Backoff para {tipo_erro}: {backoff}s (tentativa {tentativa})")
        return backoff
    
    def obter_recomendacao_estrategia(self) -> Dict:
        """Retorna recomendações de estratégia baseadas no estado atual"""
        recomendacoes = {
            'estado_servidor': self.estado_servidor.value,
            'timeouts_sugeridos': {},
            'estrategias': []
        }
        
        # Timeouts sugeridos por tipo
        for tipo in TipoOperacao:
            recomendacoes['timeouts_sugeridos'][tipo.value] = self.get_timeout(tipo)
        
        # Estratégias baseadas no estado
        if self.estado_servidor == EstadoServidor.INSTAVEL:
            recomendacoes['estrategias'] = [
                "Aumentar timeouts significativamente",
                "Considerar pausa prolongada entre operações",
                "Verificar status do servidor SEFAZ",
                "Reduzir número de tentativas para evitar sobrecarga"
            ]
        elif self.estado_servidor == EstadoServidor.LENTO:
            recomendacoes['estrategias'] = [
                "Aumentar timeouts moderadamente",
                "Inserir delays entre operações sequenciais",
                "Evitar horários de pico se possível"
            ]
        elif self.estado_servidor == EstadoServidor.OTIMO:
            recomendacoes['estrategias'] = [
                "Manter timeouts atuais",
                "Processamento pode ser mais agressivo",
                "Bom momento para processamento em lote"
            ]
        
        return recomendacoes
    
    def obter_relatorio_performance(self) -> Dict:
        """Retorna relatório completo de performance"""
        relatorio = {
            'estado_servidor': self.estado_servidor.value,
            'fator_adaptacao': self.fator_adaptacao,
            'estatisticas_por_tipo': {},
            'recomendacoes': self.obter_recomendacao_estrategia(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Estatísticas por tipo de operação
        for tipo, operacoes in self.estatisticas_tempo.items():
            if operacoes:
                tempos = [op['tempo'] for op in operacoes]
                sucessos = sum(1 for op in operacoes if op['sucesso'])
                
                relatorio['estatisticas_por_tipo'][tipo.value] = {
                    'total_operacoes': len(operacoes),
                    'taxa_sucesso': sucessos / len(operacoes),
                    'tempo_medio': sum(tempos) / len(tempos),
                    'tempo_maximo': max(tempos),
                    'tempo_minimo': min(tempos)
                }
        
        # Estatísticas gerais
        relatorio['erros_recentes'] = len(self.erros_recentes)
        relatorio['total_operacoes_monitoradas'] = sum(len(ops) for ops in self.estatisticas_tempo.values())
        
        return relatorio
    
    def reiniciar_estatisticas(self):
        """Reinicia todas as estatísticas"""
        self.estatisticas_tempo = {op_type: [] for op_type in TipoOperacao}
        self.erros_recentes = []
        self.estado_servidor = EstadoServidor.NORMAL
        self.fator_adaptacao = 1.0
        logger.info("Estatísticas de timeout reiniciadas")