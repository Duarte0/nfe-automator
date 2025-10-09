#!/usr/bin/env python3
"""
SCRIPT DE COMMITS CORRIGIDO - PRÁTICO E DIRETO
"""

import os
import subprocess
import sys

def executar_comando(comando: str) -> bool:
    """Executa comando shell com tratamento de erro."""
    try:
        print(f"   🔄 Executando: {comando}")
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if resultado.returncode != 0:
            print(f"   ❌ Erro: {resultado.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"   💥 Exceção: {e}")
        return False

def main():
    print("🚀 COMMITS DIRETOS - IGNORANDO ARQUIVOS SENSÍVEIS")
    print("=" * 50)
    
    # Criar .gitignore simples se não existir
    if not os.path.exists('.gitignore'):
        with open('.gitignore', 'w') as f:
            f.write("config.py\n__pycache__/\nlogs/\n*.log\n")
        print("✅ .gitignore criado")
    
    # COMMITS DIRETOS - ignorando config.py e tempCodeRunnerFile.py
    commits = [
        {
            "arquivos": ["pyproject.toml", "requirements.txt", "config.example.py"],
            "mensagem": "feat: adiciona configuração do projeto e dependências"
        },
        {
            "arquivos": ["config_manager.py", "constants.py", "data_models.py"],
            "mensagem": "feat: implementa sistema de configuração e modelos"
        },
        {
            "arquivos": ["driver_manager.py"],
            "mensagem": "feat: adiciona gerenciamento de WebDriver"
        },
        {
            "arquivos": ["sefaz_automator.py"],
            "mensagem": "feat: implementa núcleo da automação SEFAZ"
        },
        {
            "arquivos": ["main.py"],
            "mensagem": "feat: implementa ponto de entrada principal"
        },
        {
            "arquivos": ["README.md", "troubleshooting.md"],
            "mensagem": "docs: adiciona documentação"
        },
        {
            "arquivos": ["install.bat"],
            "mensagem": "feat: adiciona script de instalação"
        }
    ]
    
    # Executar commits diretos
    print(f"\n📦 EXECUTANDO {len(commits)} COMMITS...")
    
    for i, commit in enumerate(commits, 1):
        print(f"\n🎯 Commit {i}/{len(commits)}: {commit['mensagem']}")
        print("-" * 40)
        
        # Verificar quais arquivos existem
        arquivos_existentes = [f for f in commit["arquivos"] if os.path.exists(f)]
        
        if not arquivos_existentes:
            print("   ⚠️  Nenhum arquivo encontrado")
            continue
            
        print(f"   📁 Arquivos: {', '.join(arquivos_existentes)}")
        
        # Fazer commit
        if executar_comando(f"git add {' '.join(arquivos_existentes)}"):
            if executar_comando(f'git commit -m "{commit["mensagem"]}"'):
                print(f"   ✅ Commit {i} realizado!")
    
    # Status final
    print("\n📋 Status final do git:")
    executar_comando("git status")
    
    print("\n🎉 Commits concluídos! Arquivos sensíveis preservados.")
    print("💡 config.py e tempCodeRunnerFile.py não foram commitados")

if __name__ == "__main__":
    main()