"""
Gerenciador de configurações - Versão Simplificada
"""

import os
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

@dataclass
class SEFAZConfig:
    usuario: str
    senha: str
    inscricao_estadual: str
    data_inicio: str
    data_fim: str
    
    def validar_formatos(self) -> List[str]:
        """Valida formatos e retorna lista de erros."""
        erros = []
        
        # CPF - pelo menos tem que ter algo
        if not self.usuario or len(self.usuario.strip()) < 11:
            erros.append("CPF deve ter pelo menos 11 caracteres")
        
        # Senha - não pode estar vazia
        if not self.senha or len(self.senha.strip()) < 3:
            erros.append("Senha deve ter pelo menos 3 caracteres")
        
        # IE - apenas números
        if not self.inscricao_estadual or not self.inscricao_estadual.strip().isdigit():
            erros.append("Inscricao Estadual deve conter apenas numeros")
        
        # Datas - formato correto
        try:
            datetime.strptime(self.data_inicio, "%d/%m/%Y")
        except:
            erros.append("Data inicio invalida. Use DD/MM/AAAA")
        
        try:
            datetime.strptime(self.data_fim, "%d/%m/%Y")
        except:
            erros.append("Data fim invalida. Use DD/MM/AAAA")
        
        return erros


class GerenciadorConfig:
    
    def __init__(self, caminho_config: str = "config.py"):
        self.caminho_config = caminho_config
    
    def carregar_config(self):
        """Carrega configurações do arquivo."""
        if not os.path.exists(self.caminho_config):
            print("\n" + "="*50)
            print("ARQUIVO config.py NAO ENCONTRADO")
            print("="*50)
            print("1. Copie config.example.py para config.py")
            print("2. Edite com suas credenciais")
            print("3. Execute novamente")
            print("="*50)
            return None
        
        try:
            # Importação direta
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", self.caminho_config)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            config_dict = getattr(config_module, 'CONFIG', {})
            
            config = SEFAZConfig(
                usuario=config_dict.get('usuario', ''),
                senha=config_dict.get('senha', ''),
                inscricao_estadual=config_dict.get('inscricao_estadual', ''),
                data_inicio=config_dict.get('data_inicio', ''),
                data_fim=config_dict.get('data_fim', '')
            )
            
            logger.info("Configuracoes carregadas")
            return config
            
        except Exception as e:
            logger.error(f"Erro carregar configuracoes: {e}")
            return None


# Instância global
gerenciador_config = GerenciadorConfig()