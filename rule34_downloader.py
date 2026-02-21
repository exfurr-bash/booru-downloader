import os
import requests
import urllib.parse
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor
try:
    from tqdm import tqdm
except ImportError:
    # Robust fallback if tqdm is missing
    class tqdm:
        def __init__(self, total=None, desc=None, unit=None, leave=True):
            self.total = total
        def update(self, n=1): pass
        def set_description(self, desc): pass
        def close(self): pass

try:
    from dotenv import load_dotenv, set_key
except ImportError:
    def load_dotenv(): pass

# Load environment variables
load_dotenv()

# Constants
ENV_FILE = ".env"
BLACKLIST_FILE = "disgustingthings-aka-blacklist.txt"

def get_credentials():
    """Fetches credentials from .env, environment variables, or interactive input."""
    api_key = os.getenv("R34_API_KEY")
    user_id = os.getenv("R34_USER_ID")

    if api_key and user_id:
        return api_key, user_id

    # Fallback/Migration: Check old api.txt
    if not api_key or not user_id:
        if os.path.exists("api.txt"):
            try:
                with open("api.txt", "r") as f:
                    content = f.read().strip().lstrip('&')
                    params = urllib.parse.parse_qs(content)
                    api_key = api_key or params.get('api_key', [None])[0]
                    user_id = user_id or params.get('user_id', [None])[0]
                    if api_key and user_id:
                        print(f"[*] Migrating api.txt to {ENV_FILE}...")
                        try:
                            with open(ENV_FILE, "a"): pass
                            set_key(ENV_FILE, "R34_API_KEY", api_key)
                            set_key(ENV_FILE, "R34_USER_ID", user_id)
                        except: pass
            except: pass

    if not api_key or not user_id:
        print("\n--- Setup Interativo Rule34 ---")
        print("Você pode encontrar suas chaves em: https://rule34.xxx/index.php?page=account&s=options")
        
        choice = input("Configurar credenciais agora? (y/N): ").lower()
        if choice == 'y':
            user_id = input("user_id: ").strip()
            api_key = input("api_key: ").strip()
            save = input(f"Salvar em {ENV_FILE}? (y/N): ").lower()
            if save == 'y':
                try:
                    with open(ENV_FILE, "a"): pass
                    set_key(ENV_FILE, "R34_API_KEY", api_key)
                    set_key(ENV_FILE, "R34_USER_ID", user_id)
                except:
                    with open(ENV_FILE, "w") as f:
                        f.write(f"R34_API_KEY={api_key}\nR34_USER_ID={user_id}\n")
                print(f"[*] Credenciais salvas!")
        else:
            print("[!] Prosseguindo de forma anônima (limites de taxa reduzidos).")
            return None, None
            
    return api_key, user_id

def get_blacklist():
    """Reads the blacklist file and formats tags for the API query."""
    if not os.path.exists(BLACKLIST_FILE):
        return ""
    try:
        with open(BLACKLIST_FILE, "r") as f:
            tags = f.read().split()
            return " ".join([f"-{tag}" for tag in tags])
    except:
        return ""

def download_page(tags, pid, api_key, user_id, limit=1000):
    """Fetches a single page of post metadata."""
    params = {
        "page": "dapi", "s": "post", "q": "index", "tags": tags,
        "limit": limit, "pid": pid, "json": 1
    }
    if api_key and user_id:
        params["api_key"], params["user_id"] = api_key, user_id

    headers = {"User-Agent": "Rule34Downloader/1.5"}
    try:
        response = requests.get("https://api.rule34.xxx/index.php", params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
    except: pass
    return []

def save_image(post, download_dir, pbar=None):
    """Downloads and saves an image/video from a post object."""
    file_url = post.get('file_url')
    if not file_url:
        return

    ext = os.path.splitext(file_url)[1]
    filename = os.path.join(download_dir, f"{post.get('id')}{ext}")

    if os.path.exists(filename):
        if pbar: pbar.update(1)
        return

    try:
        headers = {"User-Agent": "Rule34Downloader/1.5"}
        response = requests.get(file_url, stream=True, headers=headers, timeout=15)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
    except: pass
    finally:
        if pbar: pbar.update(1)

def main():
    parser = argparse.ArgumentParser(description="Downloader profissional para Rule34.xxx")
    parser.add_argument("tags", nargs="*", help="Tags de busca (ex: cat_ears high_res)")
    parser.add_argument("-o", "--output", default="downloads", help="Pasta de destino (default: downloads)")
    parser.add_argument("-l", "--limit", type=int, default=1000, help="Máximo de posts por página (max 1000)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Número de downloads simultâneos (default: 10)")
    args = parser.parse_args()

    print("\033[95m=== Rule34 Downloader v1.5 ===\033[0m")
    
    api_key, user_id = get_credentials()
    
    user_tags = " ".join(args.tags)
    if not user_tags:
        print("\n\033[93mEntrada manual:\033[0m")
        user_tags = input("Tags para baixar: ").strip()
        if not user_tags:
            print("Nenhuma tag fornecida. Encerrando.")
            return

    blacklist_tags = get_blacklist()
    full_query = f"{user_tags} {blacklist_tags}".strip()
    os.makedirs(args.output, exist_ok=True)

    print(f"[*] Buscando: {user_tags}")
    if blacklist_tags: print(f"[*] Blacklist ativa de: {BLACKLIST_FILE}")

    pid = 0
    total_processed = 0
    
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        while True:
            posts = download_page(full_query, pid, api_key, user_id, args.limit)
            if not posts:
                print("\033[92m[✓] Fim dos resultados ou galeria completa.\033[0m")
                break

            pbar = tqdm(total=len(posts), desc=f"Página {pid}", unit="post", leave=False)
            
            # Submete downloads em paralelo
            futures = [executor.submit(save_image, post, args.output, pbar) for post in posts]
            # Espera a página atual terminar para não inundar de threads infinitas
            for f in futures: f.result()
            
            pbar.close()
            total_processed += len(posts)
            print(f"[*] Processado Página {pid} ({total_processed} entradas totais)")
            pid += 1

    print(f"\n\033[92mConcluído! {total_processed} imagens processadas na pasta '{args.output}'.\033[0m")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n\033[91mEncerrado pelo usuário.\033[0m")
        sys.exit(0)