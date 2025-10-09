"""
Constantes atualizadas com fluxo correto.
"""
from selenium.webdriver.common.by import By

# URLs CORRETAS baseadas no fluxo real
SEFAZ_LOGIN_URL = "https://portal.sefaz.go.gov.br/portalsefaz-apps/auth/login-form"
SEFAZ_DASHBOARD_URL = "https://portal.sefaz.go.gov.br/portalsefaz-apps"
SEFAZ_ACESSO_RESTRITO_URL = "https://www.sefaz.go.gov.br/netaccess/000System/acessoRestrito/"
SEFAZ_DOWNLOAD_XML_URL = "https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfe/consulta-notas-recebidas"

# Seletores ATUALIZADOS
SELECTORS = {
    'login': {
        'usuario': (By.ID, "username"),
        'senha': (By.ID, "password"),  
        'botao_login': (By.ID, "btnAuthenticate"),
    },
    'dashboard': {
        'acesso_restrito': (By.XPATH, "//a[contains(text(), 'Acesso Restrito') or contains(@href, 'acessoRestrito')]"),
    },
    'acesso_restrito_page': {
        'baixar_xml': (By.XPATH, "//a[contains(text(), 'Baixar XML NFE') or contains(text(), 'Baixar XML')]"),
    },
    'formulario': {
        'data_inicio': (By.ID, "cmpDataInicial"),
        'data_fim': (By.ID, "cmpDataFinal"),
        'inscricao_estadual': (By.ID, "cmpNumIeDest"),
        'modelo_nota': (By.ID, "cmpModelo"),
        'botao_pesquisar': (By.ID, "btnPesquisar"),
    }
}

# Configurações de tempo (em segundos)
TIMEOUTS = {
    'element_wait': 15,
    'page_load': 10,
    'implicit_wait': 10,
    'captcha_wait': 60,
}

# 🔧 ADICIONE ESTAS CONSTANTES QUE ESTAVAM FALTANDO:
DRIVER_PATHS = [
    "./drivers/chromedriver.exe",
    "./chromedriver.exe",
    "chromedriver.exe",
]

MESSAGES = {
    'config_not_found': """
⚠️  ARQUIVO DE CONFIGURAÇÃO NÃO ENCONTRADO
===========================================
Por favor, siga estas etapas:

1. Renomeie 'config.example.py' para 'config.py'
2. Edite o arquivo com suas credenciais:
   - CPF (com pontos e traço)
   - Senha do sistema SEFAZ
   - Inscrição Estadual
   - Período de consulta (DD/MM/AAAA)

3. Execute o programa novamente
===========================================
""",
    'driver_error': """
❌ ERRO DE CONFIGURAÇÃO DO NAVEGADOR
====================================
Não foi possível configurar o WebDriver.

🔧 SOLUÇÕES:
1. Execute 'install.bat' como Administrador
2. Verifique se o Google Chrome está instalado
3. Consulte 'docs/troubleshooting.md'
====================================
"""
}

RETRY_CONFIG = {
    'login': 2,
    'navegacao': 3, 
    'iframe': 3,
    'elemento': 3,
    'popup': 2
}