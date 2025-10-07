# 🚀 Automação SEFAZ Goiás - Download XML NFe

Automação para download em lote de XMLs de NFe de entrada do portal da SEFAZ Goiás, desenvolvida para empresas de contabilidade.

## ⚡ Funcionalidades

- ✅ **Login automático** no sistema SEFAZ Goiás
- ✅ **Navegação inteligente** até o módulo de download
- ✅ **Preenchimento automático** do formulário de consulta
- ✅ **Suporte a captcha** (resolução manual)
- ✅ **Pesquisa e download** em lote de XMLs
- ✅ **Configuração segura** de credenciais

## 🛠️ Tecnologias

- **Python 3.8+**
- **Selenium WebDriver**
- **Chrome Driver** (gerenciado automaticamente)
- **WebDriver Manager**

## Fluxo de Execução:

- ✅ Login automático no sistema

- ✅ Navegação para "Baixar XML NFE"

- ✅ Preenchimento do formulário

- ⏸️ Pausa para resolução manual do captcha

- ✅ Execução da pesquisa

- ✅ Download dos XMLs

## 🎯 Próximas Funcionalidades

- Automação de captcha com serviços externos

- Agendamento automático (cron)

- Interface web para configuração

- Notificações por e-mail

-  Integração com sistemas contábeis

  ## ⚠️ Limitações Atuais

- Captcha requer intervenção manual

- Necessário acesso válido ao sistema SEFAZ

- Dependente da estabilidade da interface web

- Contribuição

## 🤝 Fork o projeto

- Crie uma branch: git checkout -b feature/nova-funcionalidade

- Commit: git commit -m 'Add nova funcionalidade'

- Push: git push origin feature/nova-funcionalidade

- Abra um Pull Request

## 📦 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/nfe-automator.git
cd nfe-automator

### 2. Instale as dependências
pip install -r requirements.txt

### 3. Configure as credenciais
cp config.example.py config.py

# Edite o config.py com suas credenciais
CONFIG = {
    'usuario': 'seu_cpf_aqui',
    'senha': 'sua_senha_aqui',
    'inscricao_estadual': 'sua_ie_aqui',
    'data_inicio': '01/03/2024',
    'data_fim': '31/03/2024'
}

python main.py

