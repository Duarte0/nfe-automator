import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Any, List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
@dataclass
class EstadoEmpresa:
    ie: str
    nome: str
    status: str
    tentativas: int = 0
    ultima_tentativa: Optional[datetime] = None
    erro: Optional[str] = None
    arquivos_baixados: List[str] = None
    etapa_atual: str = "inicio"
    progresso_download: int = 0
    dados_sessao: Dict[str, Any] = None
    checkpoint_time: Optional[datetime] = None
    total_notas: int = 0
    notas_processadas: int = 0
    
    def __post_init__(self):
        if self.arquivos_baixados is None:
            self.arquivos_baixados = []
        if self.dados_sessao is None:
            self.dados_sessao = {}

class GerenciadorMultiplasEmpresas:
    def __init__(self, arquivo_estado: str = "estado/processamento_empresas.json"):
        self.arquivo_estado = Path(arquivo_estado)
        self.estados: Dict[str, EstadoEmpresa] = {} 
        self.carregar_estado()
    
    def carregar_estado(self) -> bool:
        """Carrega estado do arquivo JSON com desserialização de datetime"""
        if not self.arquivo_estado.exists():
            return False
        
        try:
            with open(self.arquivo_estado, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            for ie, estado_data in dados.items():
                ultima_tentativa = None
                checkpoint_time = None
                
                if estado_data['ultima_tentativa']:
                    from datetime import datetime
                    ultima_tentativa = datetime.fromisoformat(estado_data['ultima_tentativa'])
                
                if estado_data['checkpoint_time']:
                    from datetime import datetime
                    checkpoint_time = datetime.fromisoformat(estado_data['checkpoint_time'])
                
                self.estados[ie] = EstadoEmpresa(
                    ie=ie,
                    nome=estado_data['nome'],
                    status=estado_data['status'],
                    tentativas=estado_data['tentativas'],
                    ultima_tentativa=ultima_tentativa,
                    erro=estado_data['erro'],
                    arquivos_baixados=estado_data['arquivos_baixados'],
                    etapa_atual=estado_data['etapa_atual'],
                    progresso_download=estado_data['progresso_download'],
                    dados_sessao=estado_data['dados_sessao'],
                    checkpoint_time=checkpoint_time,
                    total_notas=estado_data.get('total_notas', 0),
                    notas_processadas=estado_data.get('notas_processadas', 0)
                )
            return True
        except Exception as e:
            logger.error(f"Erro carregar estado: {e}")
            self.estados = {}
            return False
    
    def salvar_estado(self) -> bool:
        """Salva estado no arquivo JSON com serialização de datetime"""
        try:
            dados = {}
            for ie, estado in self.estados.items():
                estado_dict = {
                    'ie': estado.ie,
                    'nome': estado.nome,
                    'status': estado.status,
                    'tentativas': estado.tentativas,
                    'ultima_tentativa': estado.ultima_tentativa.isoformat() if estado.ultima_tentativa else None,
                    'erro': estado.erro,
                    'arquivos_baixados': estado.arquivos_baixados,
                    'etapa_atual': estado.etapa_atual,
                    'progresso_download': estado.progresso_download,
                    'dados_sessao': estado.dados_sessao,
                    'checkpoint_time': estado.checkpoint_time.isoformat() if estado.checkpoint_time else None,
                    'total_notas': estado.total_notas,
                    'notas_processadas': estado.notas_processadas
                }
                dados[ie] = estado_dict
            
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
        for ie, estado in self.estados.items():
            if estado.tentativas == 0:
                return {'ie': ie, 'nome': estado.nome}
        
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
        
    def criar_checkpoint(self, empresa: Dict, etapa: str, progresso: int = 0, 
                    dados_sessao: Dict = None, total_notas: int = None,
                    notas_processadas: int = None) -> bool:
        """Cria checkpoint durante o processamento de uma IE"""
        try:
            ie = empresa['ie']
            if ie not in self.estados:
                logger.warning(f"Tentativa de checkpoint para IE não registrada: {ie}")
                return False
                
            estado = self.estados[ie]
            estado.etapa_atual = etapa
            estado.progresso_download = max(0, min(100, progresso)) 
            estado.checkpoint_time = datetime.now()
            
            if dados_sessao:
                estado.dados_sessao.update(dados_sessao)
                
            if total_notas is not None:
                estado.total_notas = total_notas
                
            if notas_processadas is not None:
                estado.notas_processadas = notas_processadas
            
            if progresso < 100:
                estado.status = 'em_andamento'
            else:
                estado.status = 'concluido'
            
            self.salvar_estado()
            logger.debug(f"Checkpoint criado para {ie} - {etapa} ({progresso}%)")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar checkpoint para {empresa.get('ie', 'unknown')}: {e}")
            return False
            
    def rollback_etapa(self, empresa: Dict, etapa_anterior: str, motivo: str = "") -> bool:
        """Reverte para etapa anterior em caso de erro"""
        try:
            ie = empresa['ie']
            if ie not in self.estados:
                return False
                
            estado = self.estados[ie]
            
            progressos_etapas = {
                "inicio": 0,
                "formulario": 20, 
                "captcha": 40,
                "consulta": 60,
                "download": 80,
                "concluido": 100
            }
            
            estado.etapa_atual = etapa_anterior
            estado.progresso_download = progressos_etapas.get(etapa_anterior, 0)
            estado.tentativas += 1
            estado.status = 'erro' if estado.tentativas >= 3 else 'pendente'
            
            if motivo:
                estado.erro = f"{motivo} (rollback para {etapa_anterior})"
            
            self.salvar_estado()
            logger.info(f"Rollback realizado: {ie} -> {etapa_anterior} ({estado.progresso_download}%)")
            return True
            
        except Exception as e:
            logger.error(f"Erro no rollback para {empresa.get('ie', 'unknown')}: {e}")
            return False
            
    def recuperar_sessao_interrompida(self, tempo_maximo_minutos: int = 30) -> List[Dict]:
        """Encontra IEs com processamento interrompido para retomada"""
        try:
            empresas_interrompidas = []
            tempo_limite = tempo_maximo_minutos * 60 
            
            for ie, estado in self.estados.items():

                if (estado.status == 'em_andamento' and 
                    estado.checkpoint_time and 
                    estado.etapa_atual != 'concluido'):
                    
                    tempo_desde_checkpoint = (datetime.now() - estado.checkpoint_time).total_seconds()
                    
                    if tempo_desde_checkpoint <= tempo_limite:
                        empresas_interrompidas.append({
                            'ie': ie,
                            'nome': estado.nome,
                            'etapa': estado.etapa_atual,
                            'progresso': estado.progresso_download,
                            'tentativas': estado.tentativas,
                            'total_notas': estado.total_notas,
                            'notas_processadas': estado.notas_processadas,
                            'tempo_desde_checkpoint': int(tempo_desde_checkpoint)
                        })
                        logger.info(f"Sessão interrompida encontrada: {ie} - {estado.etapa_atual} ({estado.progresso_download}%)")
            
            logger.info(f"Encontradas {len(empresas_interrompidas)} sessões interrompidas")
            return empresas_interrompidas
            
        except Exception as e:
            logger.error(f"Erro ao recuperar sessões interrompidas: {e}")
            return []
        
    def limpar_checkpoints_antigos(self, dias: int = 7) -> int:
        """Remove checkpoints mais antigos que X dias"""
        try:
            limite_tempo = datetime.now() - timedelta(days=dias)
            removidos = 0
            
            for ie, estado in list(self.estados.items()):
                if (estado.checkpoint_time and 
                    estado.checkpoint_time < limite_tempo and 
                    estado.status in ['concluido', 'erro']):
                    
                    estado.dados_sessao = {}
                    estado.checkpoint_time = None
                    removidos += 1
            
            if removidos > 0:
                self.salvar_estado()
                logger.info(f"Limpeza: {removidos} checkpoints antigos removidos")
            
            return removidos
            
        except Exception as e:
            logger.error(f"Erro na limpeza de checkpoints: {e}")
            return 0