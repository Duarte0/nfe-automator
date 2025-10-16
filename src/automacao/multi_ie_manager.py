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
    
    def carregar_estado(self):
        if not self.arquivo_estado.exists():
            return
        
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
        except Exception as e:
            logger.error(f"Erro carregar estado: {e}")
            self.estados = {}
    
    def salvar_estado(self):
        try:
            dados = {ie: asdict(estado) for ie, estado in self.estados.items()}
            for estado_data in dados.values():
                if estado_data['ultima_tentativa']:
                    estado_data['ultima_tentativa'] = estado_data['ultima_tentativa'].isoformat()
            
            self.arquivo_estado.parent.mkdir(exist_ok=True)
            with open(self.arquivo_estado, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro salvar estado: {e}")
    
    def adicionar_ies(self, inscricoes: List[str]):
        for ie in inscricoes:
            if ie not in self.estados:
                self.estados[ie] = EstadoIE(inscricao=ie, status='pendente')
        self.salvar_estado()
    
    def obter_proxima_ie(self) -> Optional[str]:
        total_processadas = sum(1 for estado in self.estados.values() if estado.tentativas > 0)
        total_ies = len(self.estados)
        
        if total_processadas < total_ies:
            for ie, estado in self.estados.items():
                if estado.tentativas == 0:
                    return ie
        else:
            for ie, estado in self.estados.items():
                if estado.status in ['pendente', 'erro'] and estado.tentativas == 1:
                    return ie
        
        return None
    
    def _atualizar_estado(self, ie: str, status: str, erro: str = None):
        if ie in self.estados:
            self.estados[ie].status = status
            self.estados[ie].erro = erro
            self.estados[ie].ultima_tentativa = datetime.now()
            self.salvar_estado()
    
    def marcar_em_andamento(self, ie: str):
        if ie in self.estados:
            self.estados[ie].tentativas += 1
            self._atualizar_estado(ie, 'em_andamento')
    
    def marcar_concluido(self, ie: str):
        self._atualizar_estado(ie, 'concluido')
    
    def marcar_erro(self, ie: str, erro: str):
        self._atualizar_estado(ie, 'erro', erro)
    
    def marcar_pendente(self, ie: str, motivo: str = ""):
        self._atualizar_estado(ie, 'pendente', motivo)
    
    def obter_relatorio(self) -> Dict:
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
    
    def limpar_estado(self):
        self.estados.clear()
        if self.arquivo_estado.exists():
            self.arquivo_estado.unlink(missing_ok=True)