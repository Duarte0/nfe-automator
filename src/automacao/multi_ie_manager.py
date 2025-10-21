import json
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class EstadoEmpresa:
    ie: str
    nome: str
    status: str
    tentativas: int = 0
    ultima_tentativa: Optional[datetime] = None
    erro: Optional[str] = None
    arquivos_baixados: List[str] = None
    
    def __post_init__(self):
        if self.arquivos_baixados is None:
            self.arquivos_baixados = []

class GerenciadorMultiplasEmpresas:
    def __init__(self, arquivo_estado: str = "estado/processamento_empresas.json"):
        self.arquivo_estado = Path(arquivo_estado)
        self.estados: Dict[str, EstadoEmpresa] = {}  # Key: IE
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
                
                self.estados[ie] = EstadoEmpresa(
                    ie=ie,
                    nome=estado_data['nome'],
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
    
    def adicionar_empresas(self, empresas: List[Dict]):
        """Adiciona empresas para processamento"""
        for empresa in empresas:
            ie = empresa['ie']
            if ie not in self.estados:
                self.estados[ie] = EstadoEmpresa(
                    ie=ie, 
                    nome=empresa['nome'], 
                    status='pendente'
                )
        self.salvar_estado()
    
    def obter_proxima_empresa(self) -> Optional[Dict]:
        """Obtém próxima empresa para processamento"""
        # Primeiro: Empresas nunca processadas
        for ie, estado in self.estados.items():
            if estado.tentativas == 0:
                return {'ie': ie, 'nome': estado.nome}
        
        # Segundo: Empresas com status pendente ou erro (apenas 1 tentativa)
        for ie, estado in self.estados.items():
            if estado.status in ['pendente', 'erro'] and estado.tentativas == 1:
                return {'ie': ie, 'nome': estado.nome}
        
        return None
    
    def _atualizar_estado(self, ie: str, status: str, erro: str = None):
        """Atualiza estado de uma empresa"""
        if ie in self.estados:
            self.estados[ie].status = status
            self.estados[ie].erro = erro
            self.estados[ie].ultima_tentativa = datetime.now()
            self.salvar_estado()
    
    def marcar_em_andamento(self, empresa: Dict):
        """Marca empresa como em processamento"""
        ie = empresa['ie']
        if ie in self.estados:
            self.estados[ie].tentativas += 1
            self._atualizar_estado(ie, 'em_andamento')
    
    def marcar_concluido(self, empresa: Dict):
        """Marca empresa como concluída"""
        self._atualizar_estado(empresa['ie'], 'concluido')
    
    def marcar_erro(self, empresa: Dict, erro: str):
        """Marca empresa como erro"""
        self._atualizar_estado(empresa['ie'], 'erro', erro)
    
    def marcar_pendente(self, empresa: Dict, motivo: str = ""):
        """Marca empresa como pendente"""
        self._atualizar_estado(empresa['ie'], 'pendente', motivo)
    
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
        """Relatório detalhado usando nomes das empresas"""
        empresas_com_notas = []
        empresas_sem_notas = []
        empresas_com_erro = []
        
        for estado in self.estados.values():
            if estado.status == 'concluido':
                empresas_com_notas.append(estado.nome)
            elif estado.status == 'pendente':
                empresas_sem_notas.append(estado.nome)
            elif estado.status == 'erro':
                empresas_com_erro.append(estado.nome)
        
        return {
            'total': len(self.estados),
            'concluidos': len(empresas_com_notas),
            'pendentes': len(empresas_sem_notas),
            'erros': len(empresas_com_erro),
            'progresso': f"{len(empresas_com_notas)}/{len(self.estados)}",
            'empresas_com_notas': empresas_com_notas,
            'empresas_sem_notas': empresas_sem_notas,
            'empresas_com_erro': empresas_com_erro
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
            'total_empresas': len(self.estados),
            'empresas_processadas': sum(1 for e in self.estados.values() if e.tentativas > 0)
        }

    # Método legado para compatibilidade
    def adicionar_ies(self, inscricoes: List[str]):
        """Método legado - adiciona apenas IEs para compatibilidade"""
        empresas = [{'ie': ie, 'nome': f"Empresa_{ie}"} for ie in inscricoes]
        self.adicionar_empresas(empresas)

    # Método legado para compatibilidade
    def obter_proxima_ie(self) -> Optional[str]:
        """Método legado - retorna apenas IE para compatibilidade"""
        empresa = self.obter_proxima_empresa()
        return empresa['ie'] if empresa else None