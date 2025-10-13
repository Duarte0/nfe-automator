@echo off
chcp 65001 >nul
title Instalador NFe Automator

echo 🚀 INSTALANDO NFÉ AUTOMATOR - ESTRUTURA ORGANIZADA
echo ========================================

:: Criar estrutura de pastas
echo 📁 Criando estrutura de pastas...
if not exist "src\automacao" mkdir src\automacao
if not exist "src\config" mkdir src\config
if not exist "src\utils" mkdir src\utils
if not exist "logs" mkdir logs
if not exist "drivers" mkdir drivers

:: Instalar dependências
echo 📦 Instalando dependências Python...
pip install -r requirements.txt

echo ✅ Instalação concluída!
echo 📝 Configure o arquivo config.py com suas credenciais
echo 🚀 Execute: python main.py
pause