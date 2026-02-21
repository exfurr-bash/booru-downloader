import os
import requests
import urllib.parse
import sys
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor

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

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, *args, **kwargs): pass
        def update(self, n=1): pass
        def set_description(self, desc): pass
        def close(self): pass


if load_dotenv:
    load_dotenv()
else:
    logger.warning(".env não carregado, credenciais podem não funcionar.")
# Carrega variáveis
load_dotenv()

# --- NÚCLEO DO DOWNLOADER ---

class R34Downloader:
    def __init__(self, output_dir="downloads", threads=10, limit=1000, file_type="all"):
        self.output_dir = output_dir
        self.threads = threads
        self.limit = limit
        self.file_type = file_type # "all", "images", "videos"
        self.api_key = os.getenv("R34_API_KEY")
        self.user_id = os.getenv("R34_USER_ID")
        self.blacklist_file = "disgustingthings-aka-blacklist.txt"
        self.running = False

    def get_blacklist(self):
        if not os.path.exists(self.blacklist_file): return ""
        try:
            with open(self.blacklist_file, "r") as f:
                tags = f.read().split()
                return " ".join([f"-{tag}" for tag in tags])
        except Exception as e:
            logger.warning(f"Erro ao ler blacklist: {e}")
            return ""

    def fetch_page(self, tags, pid):
        params = {
            "page": "dapi", "s": "post", "q": "index", "tags": tags,
            "limit": self.limit, "pid": pid, "json": 1
        }
        
        # Só adiciona se ambos existirem e não forem vazios
        if self.api_key and self.user_id:
            params["api_key"], params["user_id"] = self.api_key, self.user_id

        headers = {"User-Agent": "Rule34Downloader/2.0"}
        try:
            url = "https://api.rule34.xxx/index.php"
            # Log da URL para depuração (sem mostrar a API KEY inteira)
            safe_tags = urllib.parse.quote(tags)
            logger.debug(f"Acessando: {url}?page=dapi&s=post&q=index&tags={safe_tags}&pid={pid}")
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                # A API às vezes retorna um dicionário com 'success': false se houver erro
                if isinstance(data, dict) and data.get("success") is False:
                    logger.error(f"Erro na API: {data.get('message', 'Erro desconhecido')}")
                    return []
                return data
            else:
                logger.error(f"Erro HTTP {response.status_code} na página {pid}")
        except Exception as e:
            logger.error(f"Erro ao buscar página {pid}: {e}")
        return []

    def save_post(self, post, pbar=None, log_callback=None, image_callback=None):
        if not self.running or not isinstance(post, dict):
            return
        file_url = post.get('file_url')
        if not file_url: return

        ext = os.path.splitext(file_url)[1].lower()
        
        # Filtro de tipo
        is_video = ext in ['.mp4', '.webm', '.mov']
        if self.file_type == "images" and is_video:
            if pbar: pbar.update(1)
            return
        if self.file_type == "videos" and not is_video:
            if pbar: pbar.update(1)
            return

        post_id = post.get('id')
        filename = os.path.join(self.output_dir, f"{post_id}{ext}")

        if os.path.exists(filename):
            if pbar: pbar.update(1)
            if image_callback: image_callback(filename)
            return

        try:
            headers = {"User-Agent": "Rule34Downloader/2.0"}
            response = requests.get(file_url, stream=True, headers=headers, timeout=20)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                msg = f"Sucesso: {post_id}{ext}"
                logger.info(msg)
                if log_callback: log_callback(msg)
                if image_callback: image_callback(filename)
            else:
                msg = f"Falha HTTP {response.status_code}: {post_id}"
                logger.warning(msg)
                if log_callback: log_callback(msg)
        except Exception as e:
            msg = f"Erro no download {post_id}: {str(e)}"
            logger.error(msg)
            if log_callback: log_callback(msg)
        finally:
            if pbar: pbar.update(1)

    def start_download(self, user_tags, log_callback=None, progress_callback=None, image_callback=None):
        self.running = True
        os.makedirs(self.output_dir, exist_ok=True)
        full_query = f"{user_tags} {self.get_blacklist()}".strip()
        
        if self.api_key and self.user_id:
            logger.info(f"Sessão iniciada com credenciais (User ID: {self.user_id[:3]}...)")
        else:
            logger.info("Sessão iniciada em modo ANÔNIMO.")
        
        logger.info(f"Busca iniciada para: {user_tags}")
        
        pid = 0
        total_processed = 0
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            while self.running:
                posts = self.fetch_page(full_query, pid)
                if not posts or not isinstance(posts, list):
                    logger.info("Fim dos resultados da API.")
                    break

                logger.info(f"Página {pid}: {len(posts)} posts encontrados.")
                if log_callback:
                    log_callback(f"[*] Página {pid}: Baixando {len(posts)} posts...")
                
                futures = [executor.submit(self.save_post, p, None, log_callback, image_callback) for p in posts]
                
                for future in futures:
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Erro em thread de download: {e}")
                    if progress_callback:
                        progress_callback(1)

                total_processed += len(posts)
                pid += 1
        
        self.running = False
        logger.info(f"Sessão finalizada. Total processado: {total_processed}")
        return total_processed

# --- MÉTODOS DE SETUP (CLI) ---

def setup_interactive_cli():
    print("\n--- Setup Interativo Rule34 ---")
    user_id = input("user_id: ").strip()
    api_key = input("api_key: ").strip()
    if input("Salvar em .env? (y/n): ").lower() == 'y':
        try:
            with open(".env", "a"): pass
            set_key(".env", "R34_API_KEY", api_key)
            set_key(".env", "R34_USER_ID", user_id)
            print("[*] Credenciais salvas!")
        except:
            with open(".env", "w") as f:
                f.write(f"R34_API_KEY={api_key}\nR34_USER_ID={user_id}\n")
    return api_key, user_id

def main():
    parser = argparse.ArgumentParser(description="Rule34 Downloader v2.0 - Core Engine")
    parser.add_argument("tags", nargs="*", help="Tags de busca")
    parser.add_argument("-o", "--output", default="downloads")
    parser.add_argument("-l", "--limit", type=int, default=1000)
    parser.add_argument("-t", "--threads", type=int, default=10)
    parser.add_argument("-f", "--filter", choices=["all", "images", "videos"], default="all")
    args = parser.parse_args()

    print("\033[95m=== Rule34 Downloader v2.0 ===\033[0m")
    
    if not os.getenv("R34_API_KEY") or not os.getenv("R34_USER_ID"):
        if input("Credenciais não encontradas. Configurar agora? (y/n): ").lower() == 'y':
            setup_interactive_cli()
            load_dotenv()

    user_tags = " ".join(args.tags)
    if not user_tags:
        user_tags = input("Tags: ").strip()

    if not user_tags: return

    downloader = R34Downloader(args.output, args.threads, args.limit, args.filter)
    total = downloader.start_download(user_tags)
    
    print(f"\n\033[92mConcluído! {total} arquivos processados.\033[0m")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: sys.exit(0)
