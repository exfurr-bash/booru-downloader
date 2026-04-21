import os
import requests
import urllib.parse
import logging
import threading
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- CONFIGURAÇÃO DE LOGGING ---
logger = logging.getLogger(__name__)

class R34Downloader:
    def __init__(
        self, 
        output_dir: str = "downloads", 
        threads: int = 10, 
        page_limit: int = 1000, 
        total_limit: int = 0, 
        file_type: str = "all", 
        ignore_blacklist: bool = False
    ):
        self.output_dir = output_dir
        self.threads = threads
        self.page_limit = page_limit
        self.total_limit = total_limit # 0 means no limit (mass download)
        self.file_type = file_type # "all", "images", "videos"
        self.ignore_blacklist = ignore_blacklist
        self.api_key = os.getenv("R34_API_KEY")
        self.user_id = os.getenv("R34_USER_ID")
        self.blacklist_file = "blacklist.txt"
        self.running = False
        self.downloaded_count = 0
        self._lock = threading.Lock()
        
        # Sessão HTTP Persistente com Lógica de Retry
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({"User-Agent": "Rule34Downloader/3.0 (Elite Edition)"})

    def get_blacklist(self) -> str:
        if self.ignore_blacklist or not os.path.exists(self.blacklist_file):
            return ""
        try:
            with open(self.blacklist_file, "r") as f:
                tags = f.read().split()
                return " ".join([f"-{tag}" for tag in tags])
        except Exception as e:
            logger.warning(f"Erro ao ler blacklist: {e}")
            return ""

    def autocomplete_tags(self, query: str) -> List[Dict[str, Any]]:
        """Busca sugestões de tags na API de autocomplete."""
        if not query or len(query) < 2:
            return []
        
        url = "https://api.rule34.xxx/autocomplete.php"
        params = {"q": query}
        
        try:
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Erro no autocomplete: {e}")
        return []

    def fetch_page(self, tags: str, pid: int) -> List[Dict[str, Any]]:
        params = {
            "page": "dapi", "s": "post", "q": "index", "tags": tags,
            "limit": self.page_limit, "pid": pid, "json": 1
        }
        
        if self.api_key and self.user_id:
            params["api_key"], params["user_id"] = self.api_key, self.user_id

        try:
            url = "https://api.rule34.xxx/index.php"
            safe_tags = urllib.parse.quote(tags)
            logger.debug(f"Acessando: {url}?page=dapi&s=post&q=index&tags={safe_tags}&pid={pid}&limit={self.page_limit}")
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    # Caso a API retorne algo que não seja JSON (comum em erros graves)
                    logger.error(f"Resposta inválida da API na página {pid}")
                    return []

                if isinstance(data, dict) and data.get("success") is False:
                    logger.error(f"Erro na API: {data.get('message', 'Erro desconhecido')}")
                    return []
                return data
            else:
                logger.error(f"Erro HTTP {response.status_code} na página {pid}")
        except Exception as e:
            logger.error(f"Erro ao buscar página {pid}: {e}")
        return []

    def save_post(
        self, 
        post: Dict[str, Any], 
        pbar: Optional[Any] = None, 
        log_callback: Optional[Callable[[str], None]] = None, 
        image_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        if not self.running or not isinstance(post, dict):
            return False
        
        with self._lock:
            if self.total_limit > 0 and self.downloaded_count >= self.total_limit:
                return False

        file_url = post.get('file_url')
        if not file_url: return False

        ext = os.path.splitext(file_url)[1].lower()
        
        # Filtro de tipo
        is_video = ext in ['.mp4', '.webm', '.mov']
        if self.file_type == "images" and is_video:
            if pbar: pbar.update(1)
            return False
        if self.file_type == "videos" and not is_video:
            if pbar: pbar.update(1)
            return False

        post_id = post.get('id')
        filename = os.path.join(self.output_dir, f"{post_id}{ext}")

        # Sanitização básica de caminho (embora id e ext sejam controlados)
        filename = os.path.abspath(filename)
        if not filename.startswith(os.path.abspath(self.output_dir)):
            logger.error(f"Tentativa de Path Traversal detectada: {filename}")
            return False

        if os.path.exists(filename):
            if pbar: pbar.update(1)
            if image_callback: image_callback(filename)
            with self._lock:
                self.downloaded_count += 1
            return True

        try:
            response = self.session.get(file_url, stream=True, timeout=20)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                msg = f"Sucesso: {post_id}{ext}"
                logger.info(msg)
                if log_callback: log_callback(msg)
                if image_callback: image_callback(filename)
                with self._lock:
                    self.downloaded_count += 1
                return True
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
        return False

    def start_download(
        self, 
        user_tags: str, 
        log_callback: Optional[Callable[[str], None]] = None, 
        progress_callback: Optional[Callable[[int], None]] = None, 
        image_callback: Optional[Callable[[str], None]] = None
    ) -> int:
        self.running = True
        with self._lock:
            self.downloaded_count = 0
            
        os.makedirs(self.output_dir, exist_ok=True)
        full_query = f"{user_tags} {self.get_blacklist()}".strip()
        
        if self.api_key and self.user_id:
            logger.info(f"Sessão iniciada com credenciais (User ID: {self.user_id[:3]}...)")
        else:
            logger.info("Sessão iniciada em modo ANÔNIMO.")
        
        if self.ignore_blacklist:
            logger.info("Blacklist IGNORADA para esta sessão.")

        logger.info(f"Busca iniciada para: {user_tags}")
        if self.total_limit > 0:
            logger.info(f"Limite de download: {self.total_limit} arquivos.")
        else:
            logger.info("Modo MASS DOWNLOAD: baixando tudo disponível.")
        
        pid = 0
        
        try:
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                while self.running:
                    with self._lock:
                        if self.total_limit > 0 and self.downloaded_count >= self.total_limit:
                            logger.info("Limite total atingido.")
                            break

                    posts = self.fetch_page(full_query, pid)
                    if not posts or not isinstance(posts, list):
                        logger.info("Fim dos resultados da API.")
                        break

                    logger.info(f"Página {pid}: {len(posts)} posts encontrados.")
                    if log_callback:
                        log_callback(f"[*] Página {pid}: Baixando {len(posts)} posts...")
                    
                    futures = []
                    for p in posts:
                        if not self.running: break
                        futures.append(executor.submit(self.save_post, p, None, log_callback, image_callback))
                    
                    for future in futures:
                        if not self.running: break
                        try:
                            if future.result() and progress_callback:
                                progress_callback(1)
                        except Exception as e:
                            logger.error(f"Erro em thread de download: {e}")
                        
                        with self._lock:
                            if self.total_limit > 0 and self.downloaded_count >= self.total_limit:
                                self.running = False
                                break

                    pid += 1
        except KeyboardInterrupt:
            self.running = False
            logger.warning("\n[!] Interrupção detectada! Parando threads...")
        finally:
            self.running = False
            
        logger.info(f"Sessão finalizada. Total baixado/processado: {self.downloaded_count}")
        return self.downloaded_count
