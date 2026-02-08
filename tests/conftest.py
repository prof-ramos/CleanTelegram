"""Configuração de testes para CleanTelegram."""

import sys
from pathlib import Path

# Adicionar src/ ao path ANTES de qualquer outra coisa para importar o módulo correto
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and src_path.is_dir():
    sys.path.insert(0, str(src_path))
else:
    raise RuntimeError(f"Diretório src/ não encontrado em {src_path}. Verifique a estrutura do projeto.")

# Remover o diretório raiz do path para evitar conflito
root_path = Path(__file__).parent.parent
root_path_str = str(root_path)
# Remover TODAS as ocorrências, não apenas a primeira
sys.path = [p for p in sys.path if p != root_path_str]
