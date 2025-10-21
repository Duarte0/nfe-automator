"""
Gerenciador de Configurações para automação SEFAZ."""

import os
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)

@dataclass
class SEFAZConfig:
    usuario: str
    senha: str
    inscricao_estadual: str
    data_inicio: str
    data_fim: str
    
    def validar_formatos(self) -> List[str]:
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
        
        # Validar datas
        data_erros = self._validar_datas()
        erros.extend(data_erros)
        
        return erros
    
    def _validar_datas(self) -> List[str]:
        """Validação rigorosa das datas"""
        erros = []
        
        try:
            data_inicio_obj = datetime.strptime(self.data_inicio, "%d/%m/%Y")
            data_fim_obj = datetime.strptime(self.data_fim, "%d/%m/%Y")
            
            # Data fim não pode ser anterior à data início
            if data_fim_obj < data_inicio_obj:
                erros.append("Data fim não pode ser anterior à data início")
            
            # Período muito longo (mais de 2 anos)
            diferenca = data_fim_obj - data_inicio_obj
            if diferenca.days > 730:  # 2 anos
                erros.append("Período muito longo (máximo 2 anos)")
            
            # Data início no futuro
            if data_inicio_obj > datetime.now():
                erros.append("Data início não pode ser no futuro")
            
            # Data fim no futuro (pode ser aceitável, mas avisar)
            if data_fim_obj > datetime.now():
                logger.warning("Data fim está no futuro")
            
        except ValueError as e:
            erros.append(f"Formato de data inválido: {e}. Use DD/MM/AAAA")
        
        return erros
    
    def obter_periodo_mes_anterior(self) -> Tuple[str, str]:
        """Retorna período do mês anterior automaticamente"""
        hoje = datetime.now()
        primeiro_dia_mes_atual = hoje.replace(day=1)
        ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
        primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
        
        data_inicio = primeiro_dia_mes_anterior.strftime("%d/%m/%Y")
        data_fim = ultimo_dia_mes_anterior.strftime("%d/%m/%Y")
        
        return data_inicio, data_fim
    
    def usar_periodo_mes_anterior(self):
        """Configura automaticamente para o mês anterior"""
        self.data_inicio, self.data_fim = self.obter_periodo_mes_anterior()
        logger.info(f"Período configurado automaticamente: {self.data_inicio} a {self.data_fim}")


class GerenciadorConfig:
    
    def __init__(self, caminho_config: str = "config.py"):
        self.caminho_config = caminho_config
    
    def carregar_config(self) -> SEFAZConfig:
        if not os.path.exists(self.caminho_config):
            self._mostrar_erro_config_ausente()
            return None
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", self.caminho_config)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            config_dict = getattr(config_module, 'CONFIG', {})
            
            config = SEFAZConfig(
                usuario=config_dict.get('usuario', '').strip(),
                senha=config_dict.get('senha', '').strip(),
                inscricao_estadual=str(config_dict.get('inscricao_estadual', '')).strip(),
                data_inicio=config_dict.get('data_inicio', '').strip(),
                data_fim=config_dict.get('data_fim', '').strip()
            )
            
            # Se datas estão vazias, usar período automático
            if not config.data_inicio or not config.data_fim:
                logger.info("Datas não configuradas, usando período automático")
                config.usar_periodo_mes_anterior()
            
            logger.info("Configurações carregadas com sucesso")
            return config
            
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            return None
    
    def _mostrar_erro_config_ausente(self):
        """Exibe mensagem de erro amigável"""
        print("\n" + "="*60)
        print("CONFIGURAÇÃO NÃO ENCONTRADA")
        print("="*60)
        print("Para configurar o sistema:")
        print("1. Copie 'config.example.py' para 'config.py'")
        print("2. Edite o arquivo com suas credenciais:")
        print("   - CPF/Usuário")
        print("   - Senha do portal SEFAZ") 
        print("   - Inscrição Estadual")
        print("3. As datas podem ser deixadas em branco para uso automático")
        print("="*60)
        print("Arquivo de exemplo: config.example.py")
        print("="*60)
    
    def validar_config_arquivo(self) -> bool:
        """Valida se o arquivo de configuração existe e é válido"""
        if not os.path.exists(self.caminho_config):
            return False
        
        config = self.carregar_config()
        if not config:
            return False
        
        erros = config.validar_formatos()
        return len(erros) == 0


gerenciador_config = GerenciadorConfig()