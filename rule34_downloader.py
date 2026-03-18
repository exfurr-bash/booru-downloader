import os
import sys
import argparse
import logging
import getpass
from dotenv import load_dotenv, set_key
from core.engine import R34Downloader

# --- CONFIGURAÇÃO DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs.txt", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Carrega variáveis
load_dotenv()

# --- MÉTODOS DE SETUP (CLI) ---

def setup_interactive_cli() -> tuple:
    print("\n--- Setup Interativo Rule34 ---")
    user_id = input("user_id: ").strip()
    api_key = getpass.getpass("api_key (oculto): ").strip()
    if input("Salvar em .env? (y/n): ").lower() == 'y':
        try:
            with open(".env", "a"): pass
            set_key(".env", "R34_API_KEY", api_key)
            set_key(".env", "R34_USER_ID", user_id)
            print("[*] Credenciais salvas!")
        except Exception as e:
            print(f"[!] Erro ao salvar .env: {e}")
            with open(".env", "w") as f:
                f.write(f"R34_API_KEY={api_key}\nR34_USER_ID={user_id}\n")
    return api_key, user_id

def main():
    parser = argparse.ArgumentParser(
        description="Rule34 Downloader v3.0 - Ferramenta de download em massa via API.",
        epilog="Exemplos:\n  python rule34_downloader.py \"cat_ears high_res\"\n  python rule34_downloader.py --total 50 --filter images \"solo\"\n  python rule34_downloader.py (para modo interativo)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("tags", nargs="*", help="Tags de busca (ex: 'blue_eyes large_files'). Se omitido, o script solicitará via prompt.")
    parser.add_argument("-o", "--output", default="downloads", help="Diretório onde os arquivos serão salvos (padrão: 'downloads').")
    parser.add_argument("-l", "--limit", type=int, default=1000, help="Limite de posts retornados por página da API (1-1000).")
    parser.add_argument("-n", "--total", type=int, default=0, help="Quantidade total de arquivos para baixar. Use 0 para baixar TUDO o que for encontrado.")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Número de downloads simultâneos (padrão: 10).")
    parser.add_argument("-f", "--filter", choices=["all", "images", "videos"], default="all", help="Filtrar por tipo de mídia (padrão: all).")
    parser.add_argument("--ignore-blacklist", action="store_true", help="Ignorar o arquivo 'blacklist.txt' local para esta sessão.")
    args = parser.parse_args()

    print("\033[95m=== Rule34 Downloader v3.0 ===\033[0m")
    
    if not os.getenv("R34_API_KEY") or not os.getenv("R34_USER_ID"):
        if input("Credenciais não encontradas. Configurar agora? (y/n): ").lower() == 'y':
            api_key, user_id = setup_interactive_cli()
            # Garante que os valores fiquem na memória para a sessão atual
            os.environ["R34_API_KEY"] = api_key
            os.environ["R34_USER_ID"] = user_id
            load_dotenv() # Recarrega para garantir sincronia se salvou no arquivo

    user_tags = " ".join(args.tags)
    if not user_tags:
        user_tags = input("Tags: ").strip()

    if not user_tags: return

    downloader = R34Downloader(
        output_dir=args.output, 
        threads=args.threads, 
        page_limit=args.limit, 
        total_limit=args.total, 
        file_type=args.filter,
        ignore_blacklist=args.ignore_blacklist
    )
    total = downloader.start_download(user_tags)
    
    print(f"\n\033[92mConcluído! {total} arquivos processados.\033[0m")

if __name__ == "__main__":
    try: 
        main()
    except KeyboardInterrupt: 
        sys.exit(0)
