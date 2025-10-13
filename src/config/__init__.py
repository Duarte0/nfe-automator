"""
Módulos de configuração
"""

from .config_manager import SEFAZConfig, GerenciadorConfig, gerenciador_config
from .constants import SELECTORS, TIMEOUTS, RETRY_CONFIG, SEFAZ_LOGIN_URL, SEFAZ_DASHBOARD_URL, SEFAZ_ACESSO_RESTRITO_URL

__all__ = [
    'SEFAZConfig',
    'GerenciadorConfig',
    'gerenciador_config',
    'SELECTORS',
    'TIMEOUTS', 
    'RETRY_CONFIG',
    'SEFAZ_LOGIN_URL',
    'SEFAZ_DASHBOARD_URL',
    'SEFAZ_ACESSO_RESTRITO_URL'
]