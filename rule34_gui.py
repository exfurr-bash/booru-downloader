import sys
import os
import subprocess
import webbrowser
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QProgressBar, QTextEdit, QScrollArea,
    QLabel, QGridLayout, QFrame, QSpinBox, QDialog, QFormLayout, QComboBox,
    QCheckBox, QCompleter, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QRunnable, QThreadPool, QObject, QStringListModel, QTimer
from PySide6.QtGui import QPixmap, QFont, QImage
from core.engine import R34Downloader

class AutocompleteWorker(QThread):
    results_signal = Signal(list)

    def __init__(self, engine, query):
        super().__init__()
        self.engine = engine
        self.query = query

    def run(self):
        try:
            results = self.engine.autocomplete_tags(self.query)
            tags = [res.get('value', '') for res in results]
            self.results_signal.emit(tags)
        except Exception as e:
            print(f"Autocomplete error: {e}")
            self.results_signal.emit([])

class ImageLoaderSignals(QObject):
    finished = Signal(QPixmap, str)

class ImageLoader(QRunnable):
    def __init__(self, file_path, target_size=(160, 160)):
        super().__init__()
        self.file_path = file_path
        self.target_size = target_size
        self.signals = ImageLoaderSignals()

    def run(self):
        try:
            # Carregamento pesado fora da thread principal
            image = QImage(self.file_path)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image.scaled(
                    self.target_size[0], 
                    self.target_size[1], 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                ))
                self.signals.finished.emit(pixmap, self.file_path)
        except Exception as e:
            print(f"Error loading image {self.file_path}: {e}")

class DownloadWorker(QThread):
    progress_signal = Signal(int)
    log_signal = Signal(str)
    image_signal = Signal(str)
    finished_signal = Signal(int)

    def __init__(self, tags, output_dir, threads, total_limit, file_type, ignore_blacklist):
        super().__init__()
        self.tags = tags
        self.output_dir = output_dir
        self.threads = threads
        self.total_limit = total_limit
        self.file_type = file_type
        self.ignore_blacklist = ignore_blacklist
        self.downloader = R34Downloader(
            output_dir=output_dir, 
            threads=threads, 
            total_limit=total_limit, 
            file_type=file_type,
            ignore_blacklist=ignore_blacklist
        )

    def run(self):
        try:
            total = self.downloader.start_download(
                self.tags,
                log_callback=self.log_signal.emit,
                progress_callback=self.progress_signal.emit,
                image_callback=self.image_signal.emit
            )
            self.finished_signal.emit(total)
        except Exception as e:
            self.log_signal.emit(f"CRITICAL ERROR: {str(e)}")
            self.finished_signal.emit(0)

    def stop(self):
        self.downloader.running = False

class FullscreenViewer(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(os.path.basename(file_path))
        self.setMinimumSize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("background-color: #000; border: none;")
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            # Redimensionar se for muito maior que a tela inicial, mas permitir scroll
            screen = QApplication.primaryScreen().size()
            if pixmap.width() > screen.width() or pixmap.height() > screen.height():
                self.image_label.setPixmap(pixmap.scaled(screen, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.image_label.setPixmap(pixmap)
                
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        # Shortcuts
        self.close_btn = QPushButton("CLOSE (ESC)")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setStyleSheet("background: rgba(0,0,0,0.5); color: white; border: none; padding: 10px;")
        layout.addWidget(self.close_btn)

class ImageWidget(QFrame):
    clicked = Signal(str)
    action_requested = Signal(str, str) # action_type, file_path

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 240)
        self.setObjectName("ImageCard")
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        self.file_path = file_path
        ext = os.path.splitext(file_path)[1].lower()
        self.is_video = ext in ['.mp4', '.webm', '.mov']
        
        # Image Container
        self.image_container = QFrame()
        self.image_container.setFixedSize(164, 164)
        self.image_container.setObjectName("ThumbnailContainer")
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        self.image_label.setFixedSize(164, 164)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        if self.is_video:
            self.image_label.setText("🎥 VIDEO")
            self.image_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        else:
            self.image_label.setText("Loading...")
            self.image_label.setStyleSheet("color: #888;")
        
        container_layout.addWidget(self.image_label)
        layout.addWidget(self.image_container)
        
        # Info
        file_name = os.path.basename(file_path)
        try:
            self.file_size_bytes = os.path.getsize(file_path)
            file_size = self.file_size_bytes / 1024 # KB
            size_str = f"{file_size:.1f} KB" if file_size < 1024 else f"{file_size/1024:.2f} MB"
        except:
            self.file_size_bytes = 0
            size_str = "Unknown"
            
        self.info_label = QLabel(f"<b>{file_name}</b><br>{size_str}")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.info_label.setObjectName("CardInfo")
        layout.addWidget(self.info_label)

    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                self.clicked.emit(self.file_path)
            super().mousePressEvent(event)
        except RuntimeError:
            pass # Objeto já foi deletado pelo gerenciador de memória

    def contextMenuEvent(self, event):
        try:
            menu = QMenu(self)
            open_folder = menu.addAction("📁 Open Folder")
            open_browser = menu.addAction("🌐 Open in Browser (ID)")
            menu.addSeparator()
            delete_file = menu.addAction("🗑️ Delete File")
            
            action = menu.exec(event.globalPos())
            if action == open_folder:
                self.action_requested.emit("open_folder", self.file_path)
            elif action == open_browser:
                self.action_requested.emit("open_browser", self.file_path)
            elif action == delete_file:
                self.action_requested.emit("delete", self.file_path)
        except RuntimeError:
            pass

    def set_pixmap(self, pixmap):
        if not self.is_video:
            self.image_label.setText("")
            self.image_label.setPixmap(pixmap)
            self.image_label.setStyleSheet("background: transparent;")

class TagEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._completer = None

    def setCompleter(self, completer):
        if self._completer:
            self._completer.activated.disconnect()
        self._completer = completer
        if not self._completer:
            return
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.activated.connect(self.insert_completion)

    def insert_completion(self, completion):
        if self._completer.widget() is not self:
            return
        
        text = self.text()
        pos = self.cursorPosition()
        
        # Encontrar a palavra sob o cursor para substituir
        before = text[:pos]
        after = text[pos:]
        
        words_before = before.split()
        if not words_before:
            self.setText(completion + " " + after)
            return

        words_before[-1] = completion
        new_before = " ".join(words_before) + " "
        self.setText(new_before + after)
        self.setCursorPosition(len(new_before))
        self.setFocus()

    def text_under_cursor(self):
        text = self.text()
        pos = self.cursorPosition()
        before_cursor = text[:pos]
        
        if not before_cursor or before_cursor.endswith(" "):
            return ""
            
        words = before_cursor.split()
        return words[-1] if words else ""

    def keyPressEvent(self, event):
        if self._completer and self._completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
                event.ignore()
                return
        super().keyPressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rule34 Downloader Elite")
        
        # Inicializar variáveis de estado ANTES de configurar a UI
        self.output_dir = "downloads"
        self.image_count = 0
        self.columns = 4
        self.image_widgets = {} 
        self.worker = None
        self.autocomplete_worker = None
        
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)
        
        self.resize(1200, 800)
        
        # Engine para Autocomplete
        self.engine = R34Downloader()
        self.completer_model = QStringListModel()
        self.completer = QCompleter()
        self.completer.setModel(self.completer_model)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        
        # Timer para evitar muitas requisições no autocomplete
        self.autocomplete_timer = QTimer()
        self.autocomplete_timer.setSingleShot(True)
        self.autocomplete_timer.timeout.connect(self.request_autocomplete)

        self.setup_ui()

    def apply_theme(self, theme_name):
        palettes = {
            "Dark Elite": {
                "bg": "#121212", "header": "#1e1e1e", "card": "#252525", "accent": "#0078d4",
                "text": "#ffffff", "text_dim": "#aaaaaa", "border": "#333333", "input": "#2d2d2d"
            },
            "Cyberpunk": {
                "bg": "#0d0221", "header": "#1a0b2e", "card": "#1a0b2e", "accent": "#ff00ff",
                "text": "#00ffff", "text_dim": "#ff00ff", "border": "#ff00ff", "input": "#0d0221"
            },
            "Midnight": {
                "bg": "#0a0e14", "header": "#151b23", "card": "#151b23", "accent": "#58a6ff",
                "text": "#adbac7", "text_dim": "#768390", "border": "#30363d", "input": "#0d1117"
            },
            "Emerald": {
                "bg": "#060f0e", "header": "#0d1f1d", "card": "#0d1f1d", "accent": "#10b981",
                "text": "#ecfdf5", "text_dim": "#6ee7b7", "border": "#134e4a", "input": "#061512"
            },
            "Nordic": {
                "bg": "#eceff4", "header": "#e5e9f0", "card": "#ffffff", "accent": "#81a1c1",
                "text": "#2e3440", "text_dim": "#4c566a", "border": "#d8dee9", "input": "#ffffff"
            }
        }
        
        p = palettes.get(theme_name, palettes["Dark Elite"])
        is_dark = theme_name != "Nordic"
        
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {p['bg']}; color: {p['text']}; }}
            QWidget#ImageContainer {{ background-color: {p['bg']}; }}
            QFrame#HeaderFrame {{ background-color: {p['header']}; border-bottom: 1px solid {p['border']}; }}
            QFrame#SettingsPanel {{ background-color: {p['header']}; border-right: 1px solid {p['border']}; }}
            
            QLabel {{ color: {p['text']}; }}
            QLabel#CardInfo {{ color: {p['text_dim']}; font-size: 10px; }}
            QLabel#SectionTitle {{ color: {p['accent']}; font-weight: bold; text-transform: uppercase; font-size: 11px; margin-top: 10px; }}
            
            QLineEdit, QSpinBox, QComboBox {{ 
                background-color: {p['input']}; color: {p['text']}; border: 1px solid {p['border']}; 
                border-radius: 6px; padding: 6px; 
            }}
            QLineEdit:focus {{ border: 1px solid {p['accent']}; }}
            
            QPushButton {{ 
                background-color: {p['card']}; color: {p['text']}; border: 1px solid {p['border']}; 
                border-radius: 6px; padding: 8px 15px; font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {p['accent']}; color: white; border: 1px solid {p['accent']}; }}
            QPushButton#PrimaryBtn {{ background-color: {p['accent']}; color: white; border: none; font-weight: bold; }}
            QPushButton#PrimaryBtn:hover {{ background-color: {p['accent']}dd; }}
            
            QProgressBar {{ background-color: {p['input']}; border: none; border-radius: 2px; height: 4px; }}
            QProgressBar::chunk {{ background-color: {p['accent']}; }}
            
            QTextEdit {{ 
                background-color: {p['input']}; color: {p['text_dim']}; border: 1px solid {p['border']}; 
                border-radius: 6px; font-family: 'Consolas'; font-size: 10px; 
            }}
            
            QFrame#ImageCard {{ background-color: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px; }}
            QFrame#ThumbnailContainer {{ background-color: {p['bg'] if is_dark else '#f0f0f0'}; border-radius: 8px; }}
            
            QScrollArea {{ border: none; background-color: transparent; }}
            QScrollBar:vertical {{ border: none; background: transparent; width: 8px; }}
            QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 4px; }}
            QScrollBar::handle:vertical:hover {{ background: {p['accent']}; }}
        """)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Sidebar / Settings Panel ---
        self.settings_panel = QFrame()
        self.settings_panel.setObjectName("SettingsPanel")
        self.settings_panel.setFixedWidth(280)
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)
        
        logo_label = QLabel("RULE34 ELITE")
        logo_label.setStyleSheet("font-size: 18px; font-weight: 900; letter-spacing: 2px; margin-bottom: 10px;")
        settings_layout.addWidget(logo_label)

        # Section: Configuration
        settings_layout.addWidget(QLabel("Download Settings", objectName="SectionTitle"))
        
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 50)
        self.threads_spin.setValue(10)
        self.threads_spin.setPrefix("Threads: ")
        settings_layout.addWidget(self.threads_spin)
        
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 10000)
        self.limit_spin.setValue(100)
        self.limit_spin.setPrefix("Total Limit: ")
        settings_layout.addWidget(self.limit_spin)

        self.mass_download_check = QCheckBox("Download All Results")
        self.mass_download_check.toggled.connect(self.limit_spin.setDisabled)
        settings_layout.addWidget(self.mass_download_check)

        # Section: Quick Tags
        settings_layout.addWidget(QLabel("Quick Tags", objectName="SectionTitle"))
        quick_tags_layout = QGridLayout()
        tags = ["high_res", "solo", "wide_shot", "score:>100"]
        for i, tag in enumerate(tags):
            btn = QPushButton(tag)
            btn.setStyleSheet("font-size: 10px; padding: 4px;")
            # Usamos uma lambda que ignora o argumento 'checked' enviado pelo sinal
            btn.clicked.connect(lambda checked=False, t=tag: self.add_quick_tag(t))
            quick_tags_layout.addWidget(btn, i // 2, i % 2)
        settings_layout.addLayout(quick_tags_layout)

        # Section: Filters
        settings_layout.addWidget(QLabel("Filters", objectName="SectionTitle"))
        
        self.score_spin = QSpinBox()
        self.score_spin.setRange(0, 10000)
        self.score_spin.setValue(0)
        self.score_spin.setPrefix("Min Score: ")
        settings_layout.addWidget(self.score_spin)
        
        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["Any Rating", "Safe", "Questionable", "Explicit"])
        settings_layout.addWidget(self.rating_combo)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Media", "Images Only", "Videos Only"])
        settings_layout.addWidget(self.type_filter)

        self.ignore_blacklist_check = QCheckBox("Ignore Blacklist")
        settings_layout.addWidget(self.ignore_blacklist_check)

        # Section: Session Stats
        settings_layout.addWidget(QLabel("Session Stats", objectName="SectionTitle"))
        self.stats_label = QLabel("Downloaded: 0 MB\nFiles: 0")
        self.stats_label.setStyleSheet("font-size: 11px; color: #888;")
        settings_layout.addWidget(self.stats_label)
        self.total_downloaded_size = 0
        self.total_files_count = 0

        # Section: Appearance & Tools
        settings_layout.addWidget(QLabel("System", objectName="SectionTitle"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Elite", "Cyberpunk", "Midnight", "Emerald", "Nordic"])
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        settings_layout.addWidget(self.theme_combo)
        
        tools_layout = QGridLayout()
        self.creds_btn = QPushButton("🔑 Creds")
        self.creds_btn.clicked.connect(self.setup_credentials)
        tools_layout.addWidget(self.creds_btn, 0, 0)
        
        self.blacklist_btn = QPushButton("🚫 Blacklist")
        self.blacklist_btn.clicked.connect(self.setup_blacklist)
        tools_layout.addWidget(self.blacklist_btn, 0, 1)
        
        self.open_folder_btn = QPushButton("📁 Downloads")
        self.open_folder_btn.clicked.connect(self.open_downloads)
        tools_layout.addWidget(self.open_folder_btn, 1, 0, 1, 2)
        
        settings_layout.addLayout(tools_layout)
        settings_layout.addStretch()
        
        main_layout.addWidget(self.settings_panel)

        # --- Main Content Area ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Header / Search Bar
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_frame.setFixedHeight(80)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 0, 20, 0)
        header_layout.setSpacing(10)
        
        self.toggle_settings_btn = QPushButton("☰")
        self.toggle_settings_btn.setFixedSize(45, 45)
        self.toggle_settings_btn.setCheckable(True)
        self.toggle_settings_btn.setChecked(True)
        self.toggle_settings_btn.toggled.connect(self.settings_panel.setVisible)
        header_layout.addWidget(self.toggle_settings_btn)

        self.tag_input = TagEdit()
        self.tag_input.setPlaceholderText("Search tags... (e.g. cat_ears, solo, score:>100)")
        self.tag_input.setFixedHeight(45)
        self.tag_input.setFont(QFont("Segoe UI", 11))
        self.tag_input.returnPressed.connect(self.start_download)
        self.tag_input.setCompleter(self.completer)
        self.tag_input.textChanged.connect(lambda: self.autocomplete_timer.start(500))
        header_layout.addWidget(self.tag_input)

        self.start_btn = QPushButton("SEARCH")
        self.start_btn.setObjectName("PrimaryBtn")
        self.start_btn.setFixedSize(120, 45)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_download)
        header_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setFixedSize(80, 45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_download)
        header_layout.addWidget(self.stop_btn)
        
        content_layout.addWidget(header_frame)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        content_layout.addWidget(self.progress_bar)

        # Split view: Images and Logs
        view_layout = QHBoxLayout()
        view_layout.setSpacing(0)
        
        # Images Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.image_container = QWidget()
        self.image_container.setObjectName("ImageContainer")
        self.image_grid = QGridLayout(self.image_container)
        self.image_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.image_grid.setSpacing(15)
        self.scroll_area.setWidget(self.image_container)
        view_layout.addWidget(self.scroll_area, 4)

        # Log area (collapsible/toggleable might be good later, but for now 20% width)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedWidth(250)
        view_layout.addWidget(self.log_area)
        
        content_layout.addLayout(view_layout)
        main_layout.addWidget(content_widget)

        self.apply_theme("Dark Elite")

    def start_download(self):
        from dotenv import load_dotenv
        load_dotenv() # Refresh credentials before starting
        
        tags = self.tag_input.text().strip()
        if not tags:
            return

        # Adicionar filtros automáticos
        score = self.score_spin.value()
        if score > 0:
            tags += f" score:>={score}"
        
        rating_idx = self.rating_combo.currentIndex()
        if rating_idx == 1: tags += " rating:safe"
        elif rating_idx == 2: tags += " rating:questionable"
        elif rating_idx == 3: tags += " rating:explicit"

        # Reset UI
        self.log_area.clear()
        self.clear_images()
        self.progress_bar.setValue(0)
        
        is_mass_download = self.mass_download_check.isChecked()
        total_limit = 0 if is_mass_download else self.limit_spin.value()
        ignore_blacklist = self.ignore_blacklist_check.isChecked()

        if is_mass_download:
            self.progress_bar.setRange(0, 0) # Marquee mode for indefinite
        else:
            self.progress_bar.setRange(0, total_limit)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        threads = self.threads_spin.value()
        
        # Get filter
        filter_map = {0: "all", 1: "images", 2: "videos"}
        file_type = filter_map.get(self.type_filter.currentIndex(), "all")
        
        # Start worker
        self.worker = DownloadWorker(
            tags, 
            self.output_dir, 
            threads=threads, 
            total_limit=total_limit, 
            file_type=file_type,
            ignore_blacklist=ignore_blacklist
        )
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.log_message)
        self.worker.image_signal.connect(self.add_image)
        self.worker.finished_signal.connect(self.download_finished)
        self.worker.start()
        
        self.log_message(f"[*] Buscando: {tags}")

    def request_autocomplete(self):
        last_word = self.tag_input.text_under_cursor()
        if len(last_word) < 2:
            self.completer.popup().hide()
            return

        if self.autocomplete_worker and self.autocomplete_worker.isRunning():
            self.autocomplete_worker.terminate() 

        self.autocomplete_worker = AutocompleteWorker(self.engine, last_word)
        self.autocomplete_worker.results_signal.connect(self.display_autocomplete)
        self.autocomplete_worker.start()

    def display_autocomplete(self, tags):
        if tags:
            self.completer_model.setStringList(tags)
            cr = self.tag_input.cursorRect()
            cr.setWidth(self.completer.popup().sizeHintForColumn(0) 
                         + self.completer.popup().verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

    def stop_download(self):
        if self.worker:
            self.worker.stop()
            self.log_message("[!] Enviando comando de parada...")
            self.stop_btn.setEnabled(False)
            self.start_btn.setText("STOPPING...")
            self.start_btn.setStyleSheet("background-color: #555; font-weight: bold; color: white; border: none;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rearrange_images()

    def rearrange_images(self):
        # Proteção: Verifica se os componentes da UI já foram criados
        if not hasattr(self, 'image_widgets') or not hasattr(self, 'image_grid'):
            return
            
        if not self.image_widgets:
            return
            
        width = self.scroll_area.width()
        new_columns = max(1, width // 200)
        
        if new_columns == self.columns:
            return
            
        self.columns = new_columns
        
        # Re-adicionar todos os widgets na nova grade
        widgets = []
        for i in range(self.image_grid.count()):
            item = self.image_grid.takeAt(0)
            if item.widget():
                widgets.append(item.widget())
        
        for i, widget in enumerate(widgets):
            row = i // self.columns
            col = i % self.columns
            self.image_grid.addWidget(widget, row, col)

    def update_progress(self, val):
        self.progress_bar.setValue(self.progress_bar.value() + 1) # Just increment

    def log_message(self, msg):
        self.log_area.append(msg)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def add_quick_tag(self, tag):
        if not isinstance(tag, str):
            return
        current_text = self.tag_input.text().strip()
        if tag not in current_text:
            self.tag_input.setText(f"{current_text} {tag}".strip())

    def handle_image_click(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.mp4', '.webm', '.mov']:
            self.open_downloads() # Melhore abrir pasta para vídeos por enquanto
        else:
            viewer = FullscreenViewer(file_path, self)
            viewer.exec()

    def handle_image_action(self, action_type, file_path):
        if action_type == "open_folder":
            folder = os.path.dirname(os.path.abspath(file_path))
            if sys.platform == 'win32': os.startfile(folder)
            elif sys.platform == 'darwin': subprocess.Popen(['open', folder])
            else: subprocess.Popen(['xdg-open', folder])
        elif action_type == "open_browser":
            # Extrair ID do nome do arquivo (ex: 12345.jpg -> 12345)
            post_id = os.path.basename(file_path).split('.')[0]
            if post_id.isdigit():
                webbrowser.open(f"https://rule34.xxx/index.php?page=post&s=view&id={post_id}")
        elif action_type == "delete":
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.log_message(f"[!] Arquivo excluído: {os.path.basename(file_path)}")
                
                # Limpar do dicionário e remover widget
                if file_path in self.image_widgets:
                    widget = self.image_widgets.pop(file_path)
                    widget.setParent(None)
                    widget.deleteLater()
            except Exception as e:
                self.log_message(f"[!] Erro ao excluir: {e}")

    def update_stats(self, file_path):
        try:
            size = os.path.getsize(file_path)
            self.total_downloaded_size += size
            self.total_files_count += 1
            mb = self.total_downloaded_size / (1024 * 1024)
            self.stats_label.setText(f"Downloaded: {mb:.2f} MB\nFiles: {self.total_files_count}")
        except:
            pass

    def add_image(self, file_path):
        # Determine number of columns based on width
        width = self.scroll_area.width()
        self.columns = max(1, width // 200)
        
        # Gerenciamento de Memória: Limitar exibição a 100 widgets
        if self.image_grid.count() >= 100:
            item = self.image_grid.takeAt(0)
            widget = item.widget()
            if widget:
                if hasattr(widget, 'file_path') and widget.file_path in self.image_widgets:
                    del self.image_widgets[widget.file_path]
                widget.setParent(None)
                widget.deleteLater()

        row = self.image_count // self.columns
        col = self.image_count % self.columns
        
        img_widget = ImageWidget(file_path)
        img_widget.clicked.connect(self.handle_image_click)
        img_widget.action_requested.connect(self.handle_image_action)
        
        # Aplicar estilo do tema atual
        palettes = {
            "Dark Elite": {"card": "#252525", "border": "#333333"},
            "Cyberpunk": {"card": "#1a0b2e", "border": "#ff00ff"},
            "Midnight": {"card": "#151b23", "border": "#30363d"},
            "Emerald": {"card": "#0d1f1d", "border": "#134e4a"},
            "Nordic": {"card": "#ffffff", "border": "#d8dee9"}
        }
        p = palettes.get(self.theme_combo.currentText(), palettes["Dark Elite"])
        img_widget.setStyleSheet(f"background-color: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px;")
        
        self.image_widgets[file_path] = img_widget
        self.image_grid.addWidget(img_widget, row, col)
        self.image_count += 1
        
        self.update_stats(file_path)
        
        # Iniciar carregamento assíncrono se não for vídeo
        if not img_widget.is_video:
            loader = ImageLoader(file_path)
            loader.signals.finished.connect(self.on_image_loaded)
            self.thread_pool.start(loader)

    def on_image_loaded(self, pixmap, file_path):
        if file_path in self.image_widgets:
            self.image_widgets[file_path].set_pixmap(pixmap)

    def clear_images(self):
        for i in reversed(range(self.image_grid.count())): 
            widget = self.image_grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.image_count = 0
        self.image_widgets.clear()

    def download_finished(self, total):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("SEARCH & DOWNLOAD")
        self.start_btn.setStyleSheet("background-color: #0078d4; font-weight: bold; color: white; border: none;")
        self.stop_btn.setEnabled(False)
        self.log_message(f"--- Sessão finalizada! Total: {total} ---")
        if self.progress_bar.maximum() > 0: # Check if not in marquee mode
             self.progress_bar.setValue(self.progress_bar.maximum())
        else:
             self.progress_bar.setRange(0, 100)
             self.progress_bar.setValue(100)

    def open_downloads(self):
        path = os.path.abspath(self.output_dir)
        if not os.path.exists(path):
            os.makedirs(path)
        if sys.platform == 'win32':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])

    def setup_credentials(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Setup Credentials")
        dialog.setFixedWidth(400)
        layout = QFormLayout(dialog)
        
        user_id_input = QLineEdit()
        user_id_input.setPlaceholderText("R34_USER_ID")
        api_key_input = QLineEdit()
        api_key_input.setPlaceholderText("R34_API_KEY")
        api_key_input.setEchoMode(QLineEdit.Password)
        
        # Load current if possible
        from dotenv import load_dotenv
        load_dotenv()
        user_id_input.setText(os.getenv("R34_USER_ID", ""))
        api_key_input.setText(os.getenv("R34_API_KEY", ""))
        
        layout.addRow("User ID:", user_id_input)
        layout.addRow("API Key:", api_key_input)
        
        btn_box = QHBoxLayout()
        save_btn = QPushButton("Save to .env")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addRow(btn_box)
        
        if dialog.exec():
            user_id = user_id_input.text().strip()
            api_key = api_key_input.text().strip()
            try:
                from dotenv import set_key
                with open(".env", "a"): pass
                set_key(".env", "R34_API_KEY", api_key)
                set_key(".env", "R34_USER_ID", user_id)
                self.log_message("[*] Credentials saved to .env")
            except Exception as e:
                self.log_message(f"[!] Error saving credentials: {e}")
                with open(".env", "w") as f:
                    f.write(f"R34_API_KEY={api_key}\nR34_USER_ID={user_id}\n")
                self.log_message("[*] Credentials written to .env")

    def setup_blacklist(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Blacklist Tags")
        dialog.setFixedWidth(500)
        layout = QVBoxLayout(dialog)
        
        info_label = QLabel("Tags separated by spaces/lines. These will be added as -tag to your queries.")
        info_label.setStyleSheet("color: #aaa; font-style: italic;")
        layout.addWidget(info_label)
        
        text_edit = QTextEdit()
        # Carregar atual
        if os.path.exists("blacklist.txt"):
            with open("blacklist.txt", "r") as f:
                text_edit.setText(f.read())
        
        layout.addWidget(text_edit)
        
        btn_box = QHBoxLayout()
        save_btn = QPushButton("Save Blacklist")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)
        
        if dialog.exec():
            content = text_edit.toPlainText().strip()
            with open("blacklist.txt", "w") as f:
                f.write(content)
            self.log_message("[*] Blacklist updated.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())