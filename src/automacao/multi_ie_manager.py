import json
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class EstadoIE:
    inscricao: str
    status: str
    tentativas: int = 0
    ultima_tentativa: Optional[datetime] = None
    erro: Optional[str] = None
    arquivos_baixados: List[str] = None
    
    def __post_init__(self):
        if self.arquivos_baixados is None:
            self.arquivos_baixados = []

class GerenciadorMultiplasIEs:
    def __init__(self, arquivo_estado: str = "estado/processamento_ies.json"):
        self.arquivo_estado = Path(arquivo_estado)
        self.estados: Dict[str, EstadoIE] = {}
        self.carregar_estado()
    
    def carregar_estado(self) -> bool:
        """Carrega estado do arquivo JSON"""
        if not self.arquivo_estado.exists():
            return False
        
        try:
            with open(self.arquivo_estado, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            for ie, estado_data in dados.items():
                ultima_tentativa = None
                if estado_data['ultima_tentativa']:
                    ultima_tentativa = datetime.fromisoformat(estado_data['ultima_tentativa'])
                
                self.estados[ie] = EstadoIE(
                    inscricao=ie,
                    status=estado_data['status'],
                    tentativas=estado_data['tentativas'],
                    ultima_tentativa=ultima_tentativa,
                    erro=estado_data['erro'],
                    arquivos_baixados=estado_data['arquivos_baixados']
                )
            return True
        except Exception as e:
            logger.error(f"Erro carregar estado: {e}")
            self.estados = {}
            return False
    
    def salvar_estado(self) -> bool:
        """Salva estado no arquivo JSON"""
        try:
            dados = {ie: asdict(estado) for ie, estado in self.estados.items()}
            
            # Converter datetime para string
            for estado_data in dados.values():
                if estado_data['ultima_tentativa']:
                    estado_data['ultima_tentativa'] = estado_data['ultima_tentativa'].isoformat()
            
            self.arquivo_estado.parent.mkdir(exist_ok=True)
            with open(self.arquivo_estado, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erro salvar estado: {e}")
            return False
    
    def adicionar_ies(self, inscricoes: List[str]):
        """Adiciona IEs para processamento"""
        for ie in inscricoes:
            if ie not in self.estados:
                self.estados[ie] = EstadoIE(inscricao=ie, status='pendente')
        self.salvar_estado()
    
    def obter_proxima_ie(self) -> Optional[str]:
        """Obtém próxima IE para processamento"""
        # Primeiro: IEs nunca processadas
        for ie, estado in self.estados.items():
            if estado.tentativas == 0:
                return ie
        
        # Segundo: IEs com status pendente ou erro (apenas 1 tentativa)
        for ie, estado in self.estados.items():
            if estado.status in ['pendente', 'erro'] and estado.tentativas == 1:
                return ie
        
        return None
    
    def _atualizar_estado(self, ie: str, status: str, erro: str = None):
        """Atualiza estado de uma IE"""
        if ie in self.estados:
            self.estados[ie].status = status
            self.estados[ie].erro = erro
            self.estados[ie].ultima_tentativa = datetime.now()
            self.salvar_estado()
    
    def marcar_em_andamento(self, ie: str):
        """Marca IE como em processamento"""
        if ie in self.estados:
            self.estados[ie].tentativas += 1
            self._atualizar_estado(ie, 'em_andamento')
    
    def marcar_concluido(self, ie: str):
        """Marca IE como concluída"""
        self._atualizar_estado(ie, 'concluido')
    
    def marcar_erro(self, ie: str, erro: str):
        """Marca IE como erro"""
        self._atualizar_estado(ie, 'erro', erro)
    
    def marcar_pendente(self, ie: str, motivo: str = ""):
        """Marca IE como pendente"""
        self._atualizar_estado(ie, 'pendente', motivo)
    
    def obter_relatorio(self) -> Dict:
        """Relatório básico do processamento"""
        status_count = {}
        for estado in self.estados.values():
            status_count[estado.status] = status_count.get(estado.status, 0) + 1
        
        return {
            'total': len(self.estados),
            'concluidos': status_count.get('concluido', 0),
            'pendentes': status_count.get('pendente', 0),
            'erros': status_count.get('erro', 0),
            'progresso': f"{status_count.get('concluido', 0)}/{len(self.estados)}"
        }
    
    def obter_relatorio_detalhado(self) -> Dict:
        """Relatório detalhado do processamento"""
        status_count = {}
        ies_com_notas = []
        ies_sem_notas = []
        ies_com_erro = []
        
        for ie, estado in self.estados.items():
            status_count[estado.status] = status_count.get(estado.status, 0) + 1
            
            if estado.status == 'concluido':
                ies_com_notas.append(ie)
            elif estado.status == 'pendente':
                ies_sem_notas.append(ie)
            elif estado.status == 'erro':
                ies_com_erro.append(ie)
        
        return {
            'total': len(self.estados),
            'concluidos': status_count.get('concluido', 0),
            'pendentes': status_count.get('pendente', 0),
            'erros': status_count.get('erro', 0),
            'progresso': f"{status_count.get('concluido', 0)}/{len(self.estados)}",
            'ies_com_notas': ies_com_notas,
            'ies_sem_notas': ies_sem_notas,
            'ies_com_erro': ies_com_erro
        }
    
    def limpar_estado(self):
        """Limpa estado do processamento"""
        self.estados.clear()
        if self.arquivo_estado.exists():
            self.arquivo_estado.unlink(missing_ok=True)
    
    def obter_estatisticas_tempo(self) -> Dict:
        """Estatísticas de tempo do processamento"""
        tempos = []
        for estado in self.estados.values():
            if estado.ultima_tentativa:
                tempos.append(estado.ultima_tentativa)
        
        if not tempos:
            return {}
        
        return {
            'primeira_tentativa': min(tempos),
            'ultima_tentativa': max(tempos),
            'total_ies': len(self.estados),
            'ies_processadas': sum(1 for e in self.estados.values() if e.tentativas > 0)
        }