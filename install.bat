@echo off
chcp 65001 >nul
title Instalador - Automação SEFAZ NFe

echo.
echo ========================================
echo    INSTALADOR AUTOMAÇÃO SEFAZ NFe
echo ========================================
echo.

:: Verificar se Python está instalado
echo 🔍 Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python não encontrado!
    echo.
    echo 📥 Por favor, instale o Python:
    echo https://www.python.org/downloads/
    echo.
    echo ⚠️ Marque a opção "Add Python to PATH" durante a instalação
    echo.
    pause
    exit /b 1
)

echo ✅ Python encontrado!

:: Verificar se pip está disponível
echo 🔍 Verificando pip...
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Pip não encontrado!
    echo.
    echo 🔧 Execute: python -m ensurepip
    echo.
    pause
    exit /b 1
)

echo ✅ Pip encontrado!

:: Verificar Google Chrome
echo 🔍 Verificando Google Chrome...
where chrome >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Google Chrome não encontrado!
    echo.
    echo 📥 Por favor, instale o Google Chrome:
    echo https://www.google.com/chrome/
    echo.
    pause
    exit /b 1
)

echo ✅ Google Chrome encontrado!

:: Instalar dependências
echo.
echo 📦 Instalando dependências Python...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ❌ Erro ao instalar dependências!
    echo.
    echo 🔧 Soluções:
    echo 1. Execute como Administrador
    echo 2. Execute: pip install --user -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo ✅ Dependências instaladas!

:: Criar arquivo de configuração se não existir
if not exist "config.py" (
    echo.
    echo ⚙️ Criando arquivo de configuração...
    if exist "config.example.py" (
        copy "config.example.py" "config.py"
        echo ✅ Arquivo config.py criado!
        echo.
        echo 📝 EDITE o arquivo config.py com suas credenciais:
        echo    - CPF
        echo    - Senha SEFAZ  
        echo    - Inscrição Estadual
        echo.
    ) else (
        echo ❌ config.example.py não encontrado!
    )
)

echo.
echo ========================================
echo    INSTALAÇÃO CONCLUÍDA!
echo ========================================
echo.
echo 🚀 Para executar:
echo    1. Edite config.py com suas credenciais
echo    2. Execute run.bat ou python main.py
echo.
echo ❓ Dúvidas? Consulte README.md
echo.
pause