from pathlib import Path
import subprocess
import sys

# Define a pasta raiz do projeto
DIRETORIO_RAIZ = Path("./app-RFID")

# Estrutura de pastas e arquivos da imagem
pastas_e_arquivos = [
    ".vscode/",
    "assets/icons/",
    "assets/icons/logo_trans.png",
    "assets/icons/logo.png",
    "flet.toml",
    "main.py",
    "requirements.txt"
]

def criar_ambiente_completo(raiz: Path, itens):
    # 1. Cria a estrutura de pastas e arquivos
    raiz.mkdir(parents=True, exist_ok=True)
    print(f"📁 Pasta raiz criada: {raiz}")
    
    for item in itens:
        caminho_item = raiz / item
        if item.endswith("/"):
            caminho_item.mkdir(parents=True, exist_ok=True)
            print(f"📁 Pasta criada: {caminho_item}")
        else:
            caminho_item.parent.mkdir(parents=True, exist_ok=True)
            if not caminho_item.exists():
                caminho_item.touch()
                print(f"📄 Arquivo criado: {caminho_item}")

    # 2. Cria o ambiente virtual (.venv) dentro da pasta do projeto
    pasta_venv = raiz / ".venv"
    if not pasta_venv.exists():
        print(f"\n⚙️ A criar o ambiente virtual (.venv)...")
        subprocess.run([sys.executable, "-m", "venv", str(pasta_venv)], check=True)
        print(f"✅ Ambiente virtual criado em: {pasta_venv}")
    else:
        print(f"\nℹ️ O ambiente virtual já existe.")

if __name__ == "__main__":
    criar_ambiente_completo(DIRETORIO_RAIZ, pastas_e_arquivos)
    print("\n🎉 Ambiente de desenvolvimento configurado por completo!")