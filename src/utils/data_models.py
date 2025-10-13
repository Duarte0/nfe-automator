"""
Modelos de dados para automação SEFAZ.
"""
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class EtapaStatus(Enum):
    PENDENTE = "pendente"
    EXECUTANDO = "executando" 
    SUCESSO = "sucesso"
    FALHA = "falha"
    IGNORADA = "ignorada"


@dataclass
class ConfiguracaoSEFAZ:
    usuario: str
    senha: str
    inscricao_estadual: str
    data_inicio: str
    data_fim: str
    timeout_elementos: int = 15
    timeout_pagina: int = 10
    
    def validar(self) -> bool:
        try:
            if not self.usuario or "SEU_" in self.usuario.upper() or "AQUI" in self.usuario.upper():
                return False
            
            if not self.senha or len(self.senha) < 3:
                return False
                
            if not self.inscricao_estadual or not self.inscricao_estadual.strip():
                return False
                
            from datetime import datetime
            datetime.strptime(self.data_inicio, "%d/%m/%Y")
            datetime.strptime(self.data_fim, "%d/%m/%Y")
            
            return True
            
        except ValueError:
            return False
        except Exception:
            return False
    
    def obter_erros_validacao(self) -> List[str]:
        erros = []
        
        if not self.usuario or "SEU_" in self.usuario.upper() or "AQUI" in self.usuario.upper():
            erros.append("Usuário/CPF não configurado corretamente")
        
        if not self.senha or len(self.senha) < 3:
            erros.append("Senha inválida ou muito curta")
            
        if not self.inscricao_estadual or not self.inscricao_estadual.strip():
            erros.append("Inscrição estadual não informada")
            
        try:
            datetime.strptime(self.data_inicio, "%d/%m/%Y")
        except ValueError:
            erros.append("Data início inválida. Use DD/MM/AAAA")
            
        try:
            datetime.strptime(self.data_fim, "%d/%m/%Y")
        except ValueError:
            erros.append("Data fim inválida. Use DD/MM/AAAA")
        
        return erros


@dataclass
class EtapaFluxo:
    nome: str
    funcao: Any 
    descricao: str
    criticos: bool = True
    timeout: int = 30


@dataclass
class ResultadoExecucao:
    sucesso: bool
    etapas_executadas: int
    etapas_totais: int
    erros: List[str]
    tempo_total: float
    timestamp: datetime
    
@dataclass
class ResultadoDownload:
    total_encontrado: int
    total_baixado: int
    erros: List[str]
    notas_baixadas: List 
    caminho_download: str


class EstadoAutomator:
    
    def __init__(self):
        self.etapa_atual: Optional[EtapaFluxo] = None
        self.etapas_completadas: List[EtapaFluxo] = []
        self.erros: List[str] = []
        self.inicio_execucao: Optional[datetime] = None
        self.url_atual: str = ""
        self.passo: int = 0
        self.total_passos: int = 0
    
    def iniciar_execucao(self, total_etapas: int):
        self.inicio_execucao = datetime.now()
        self.total_passos = total_etapas
        self.passo = 0
        self.etapas_completadas.clear()
        self.erros.clear()
    
    def registrar_etapa(self, etapa: EtapaFluxo, sucesso: bool, mensagem: str = ""):
        self.passo += 1
        if sucesso:
            self.etapas_completadas.append(etapa)
        else:
            self.erros.append(f"Etapa {etapa.nome}: {mensagem}")
    
    def obter_progresso(self) -> Tuple[int, int, float]:
        if self.total_passos == 0:
            return 0, 0, 0.0
        
        progresso = (self.passo / self.total_passos) * 100
        return self.passo, self.total_passos, progresso
    
    def obter_tempo_decorrido(self) -> float:
        if not self.inicio_execucao:
            return 0.0
        return (datetime.now() - self.inicio_execucao).total_seconds()