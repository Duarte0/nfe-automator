"""
Gerenciador de configurações com validação robusta.
"""
import os
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)

@dataclass
class SEFAZConfig:
    """Configurações validadas para automação SEFAZ."""
    usuario: str
    senha: str
    inscricao_estadual: str
    data_inicio: str
    data_fim: str
    timeout_elementos: int = 15
    timeout_pagina: int = 10
    
    def validar(self) -> bool:
        """Valida configurações retornando status booleano."""
        try:
            # Validações básicas
            if not self.usuario or "SEU_" in self.usuario.upper() or "AQUI" in self.usuario.upper():
                return False
            
            if not self.senha or len(self.senha) < 3:
                return False
                
            if not self.inscricao_estadual or not self.inscricao_estadual.strip():
                return False
                
            # Validação de datas
            datetime.strptime(self.data_inicio, "%d/%m/%Y")
            datetime.strptime(self.data_fim, "%d/%m/%Y")
            
            return True
            
        except ValueError:
            return False
        except Exception:
            return False
    
    def obter_erros_validacao(self) -> List[str]:
        """Retorna lista detalhada de erros de validação."""
        erros = []
        
        if not self.usuario or "SEU_" in self.usuario.upper() or "AQUI" in self.usuario.upper():
            erros.append("Usuário/CPF não configurado corretamente")
        
        if not self.senha or len(self.senha) < 3:
            erros.append("Senha inválida ou muito curta")
            
        if not self.inscricao_estadual or not self.inscricao_estadual.strip():
            erros.append("Inscrição estadual não informada")
            
        # Validação de datas
        try:
            datetime.strptime(self.data_inicio, "%d/%m/%Y")
        except ValueError:
            erros.append("Data início inválida. Use DD/MM/AAAA")
            
        try:
            datetime.strptime(self.data_fim, "%d/%m/%Y")
        except ValueError:
            erros.append("Data fim inválida. Use DD/MM/AAAA")
        
        return erros


class GerenciadorConfig:
    """Gerencia carregamento e validação de configurações."""
    
    def __init__(self, caminho_config: str = "config.py"):
        self.caminho_config = caminho_config
        self._config: Optional[SEFAZConfig] = None
    
    def carregar_config(self) -> Optional[SEFAZConfig]:
        """Carrega e valida configurações do arquivo."""
        if self._config is not None:
            return self._config
            
        if not self._arquivo_config_existe():
            self._mostrar_erro_config()
            return None
        
        try:
            # Importação dinâmica do arquivo de configuração
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", self.caminho_config)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            config_dict = getattr(config_module, 'CONFIG', {})
            
            # Criar instância de SEFAZConfig
            self._config = SEFAZConfig(
                usuario=config_dict.get('usuario', ''),
                senha=config_dict.get('senha', ''),
                inscricao_estadual=config_dict.get('inscricao_estadual', ''),
                data_inicio=config_dict.get('data_inicio', ''),
                data_fim=config_dict.get('data_fim', '')
            )
            
            # Validar configurações
            if not self._config.validar():
                erros = self._config.obter_erros_validacao()
                logger.error("❌ CONFIGURAÇÕES INVÁLIDAS:")
                for erro in erros:
                    logger.error(f"   - {erro}")
                return None
                
            logger.info("✅ Configurações carregadas e validadas com sucesso")
            return self._config
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar configurações: {e}")
            return None
    
    def _arquivo_config_existe(self) -> bool:
        """Verifica se arquivo de configuração existe."""
        return os.path.exists(self.caminho_config)
    
    def _mostrar_erro_config(self):
        """Exibe mensagem de erro amigável."""
        from constants import MESSAGES
        print(MESSAGES['config_not_found'])


# Instância global para uso na aplicação
gerenciador_config = GerenciadorConfig()