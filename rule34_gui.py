import sys
import os
import subprocess
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QProgressBar, QTextEdit, QScrollArea,
    QLabel, QGridLayout, QFrame, QSpinBox, QDialog, QFormLayout, QComboBox,
    QCheckBox, QCompleter
)
from PySide6.QtCore import Qt, QThread, Signal, QRunnable, QThreadPool, QObject, QStringListModel, QTimer
from PySide6.QtGui import QPixmap, QFont, QImage
from core.engine import R34Downloader

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

class ImageWidget(QFrame):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setFixedSize(180, 240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.file_path = file_path
        ext = os.path.splitext(file_path)[1].lower()
        self.is_video = ext in ['.mp4', '.webm', '.mov']
        
        # Image / Placeholder
        self.image_label = QLabel()
        self.image_label.setFixedSize(160, 160)
        self.image_label.setScaledContents(False) # Mudado para False para controle manual
        self.image_label.setAlignment(Qt.AlignCenter)
        
        if self.is_video:
            self.image_label.setText("🎥 VIDEO")
            self.image_label.setStyleSheet("background-color: #444; color: #fff; font-weight: bold; font-size: 16px; border-radius: 4px;")
        else:
            self.image_label.setText("Loading...")
            self.image_label.setStyleSheet("background-color: #222; color: #555; border-radius: 4px;")
        
        layout.addWidget(self.image_label)
        
        # Info
        file_name = os.path.basename(file_path)
        try:
            file_size = os.path.getsize(file_path) / 1024 # KB
            size_str = f"{file_size:.1f} KB" if file_size < 1024 else f"{file_size/1024:.2f} MB"
        except:
            size_str = "Unknown size"
            
        self.info_label = QLabel(f"<b>{file_name}</b><br>{size_str}")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 10px; color: #ccc;")
        layout.addWidget(self.info_label)

    def set_pixmap(self, pixmap):
        if not self.is_video:
            self.image_label.setText("")
            self.image_label.setPixmap(pixmap)
            self.image_label.setStyleSheet("background-color: transparent; border-radius: 4px;")

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
        
        words = self.text().split()
        if not words:
            self.setText(completion + " ")
            return
        
        # Substituir apenas a última palavra parcial
        words[-1] = completion
        self.setText(" ".join(words) + " ")
        self.setFocus()

    def text_under_cursor(self):
        text = self.text()
        pos = self.cursorPosition()
        before_cursor = text[:pos]
        words = before_cursor.split()
        if not words:
            return ""
        return words[-1]

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
        self.resize(1200, 800)
        
        self.output_dir = "downloads"
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4) # Limitar threads de renderização para não travar CPU
        
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
        self.autocomplete_timer.timeout.connect(self.update_autocomplete)

        self.setup_ui()
        self.worker = None

    def apply_theme(self, theme_name):
        themes = {
            "Dark Elite": """
                QMainWindow { background-color: #1a1a1a; }
                QWidget#ImageContainer { background-color: #121212; }
                QFrame#HeaderFrame { background-color: #252525; border-radius: 8px; }
                QLineEdit, QSpinBox, QComboBox { background-color: #333; color: #fff; border: 1px solid #444; border-radius: 4px; padding: 5px; }
                QPushButton { background-color: #3a3a3a; color: #fff; border-radius: 6px; }
                QPushButton:hover { background-color: #4a4a4a; }
                QProgressBar { background-color: #333; border: none; border-radius: 4px; }
                QProgressBar::chunk { background-color: #0078d4; }
                QTextEdit { background-color: #1e1e1e; color: #00ff00; border: 1px solid #333; font-family: 'Consolas'; }
            """,
            "Cyberpunk Neon": """
                QMainWindow { background-color: #0d0221; }
                QWidget#ImageContainer { background-color: #050110; }
                QFrame#HeaderFrame { background-color: #0d0221; border: 2px solid #ff00ff; border-radius: 0px; }
                QLineEdit, QSpinBox, QComboBox { 
                    background-color: #0d0221; color: #00ffff; border: 1px solid #00ffff; border-radius: 0px; 
                    font-family: 'Impact'; font-size: 14px;
                }
                QPushButton { 
                    background-color: #ff00ff; color: #fff; border-radius: 0px; font-weight: bold; 
                    border-bottom: 4px solid #800080; 
                }
                QPushButton:hover { background-color: #ff55ff; border-bottom: 2px solid #800080; }
                QProgressBar { background-color: #1a0033; border: 1px solid #ff00ff; border-radius: 0px; }
                QProgressBar::chunk { background-color: #00ffff; }
                QTextEdit { 
                    background-color: #050110; color: #ff00ff; border: 1px solid #00ffff; 
                    font-family: 'Courier New'; font-weight: bold;
                }
                QLabel { color: #00ffff; text-transform: uppercase; font-weight: bold; }
            """,
            "Retro Hacker": """
                QMainWindow { background-color: #000; }
                QWidget#ImageContainer { background-color: #000; border: 2px solid #00ff00; }
                QFrame#HeaderFrame { background-color: #000; border-bottom: 2px solid #00ff00; }
                QLineEdit, QSpinBox, QComboBox { 
                    background-color: #000; color: #00ff00; border: 1px solid #00ff00; 
                    font-family: 'Courier New'; font-size: 12px;
                }
                QPushButton { 
                    background-color: #000; color: #00ff00; border: 2px solid #00ff00; 
                    font-family: 'Courier New'; font-weight: bold;
                }
                QPushButton:hover { background-color: #004400; }
                QProgressBar { background-color: #000; border: 1px solid #00ff00; }
                QProgressBar::chunk { background-color: #00ff00; }
                QTextEdit { background-color: #000; color: #00ff00; border: 1px solid #00ff00; }
                QLabel { color: #00ff00; font-family: 'Courier New'; }
            """,
            "Nordic Frost": """
                QMainWindow { background-color: #eceff4; }
                QWidget#ImageContainer { background-color: #fff; border-radius: 15px; margin: 10px; }
                QFrame#HeaderFrame { background-color: #e5e9f0; border-radius: 20px; border: 1px solid #d8dee9; }
                QLineEdit, QSpinBox, QComboBox { 
                    background-color: #fff; color: #2e3440; border: 1px solid #d8dee9; 
                    border-radius: 10px; padding: 8px;
                }
                QPushButton { 
                    background-color: #88c0d0; color: #fff; border-radius: 12px; font-weight: 500;
                }
                QPushButton:hover { background-color: #81a1c1; }
                QProgressBar { background-color: #d8dee9; border-radius: 10px; height: 12px; }
                QProgressBar::chunk { background-color: #81a1c1; border-radius: 10px; }
                QTextEdit { background-color: #fff; color: #4c566a; border-radius: 10px; border: 1px solid #d8dee9; }
                QLabel { color: #4c566a; }
            """,
            "Amoled": """
                QMainWindow { background-color: #000000; }
                QWidget#ImageContainer { background-color: #000000; }
                QFrame#HeaderFrame { background-color: #000000; border: 1px solid #222; border-radius: 0px; }
                QLineEdit, QSpinBox, QComboBox { 
                    background-color: #000; color: #fff; border: 1px solid #333; 
                    border-radius: 0px;
                }
                QPushButton { background-color: #111; color: #fff; border: 1px solid #333; border-radius: 0px; }
                QPushButton:hover { background-color: #222; }
                QProgressBar { background-color: #111; border: none; }
                QProgressBar::chunk { background-color: #fff; }
                QTextEdit { background-color: #000; color: #aaa; border: 1px solid #222; }
                QLabel { color: #888; }
            """
        }
        
        style = themes.get(theme_name, themes["Dark Elite"])
        self.setStyleSheet(style)
        
        # Atualizar widgets específicos que precisam de estilo manual
        for i in range(self.image_grid.count()):
            widget = self.image_grid.itemAt(i).widget()
            if widget:
                if theme_name == "Cyberpunk Neon":
                    widget.setStyleSheet("background-color: #0d0221; border: 1px solid #00ffff; border-radius: 0px;")
                elif theme_name == "Retro Hacker":
                    widget.setStyleSheet("background-color: #000; border: 1px solid #00ff00; border-radius: 0px;")
                elif theme_name == "Nordic Frost":
                    widget.setStyleSheet("background-color: #fff; border: 1px solid #d8dee9; border-radius: 15px;")
                elif theme_name == "Amoled":
                    widget.setStyleSheet("background-color: #000; border: 1px solid #222; border-radius: 0px;")
                else:
                    widget.setStyleSheet("background-color: #222; border-radius: 8px;")

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)

        # Header / Search area
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QVBoxLayout(header_frame)
        
        search_layout = QHBoxLayout()
        self.tag_input = TagEdit()
        self.tag_input.setPlaceholderText("Enter tags here... (e.g. cat_ears, solo, high_res)")
        self.tag_input.setMinimumHeight(45)
        self.tag_input.setFont(QFont("Segoe UI", 12))
        self.tag_input.returnPressed.connect(self.start_download)
        self.tag_input.setCompleter(self.completer)
        self.tag_input.textChanged.connect(lambda: self.autocomplete_timer.start(500))
        search_layout.addWidget(self.tag_input)

        self.start_btn = QPushButton("SEARCH & DOWNLOAD")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_download)
        self.start_btn.setStyleSheet("background-color: #0078d4; font-weight: bold; color: white; border: none;")
        search_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_download)
        self.stop_btn.setStyleSheet("background-color: #d83b01; font-weight: bold; color: white; border: none;")
        search_layout.addWidget(self.stop_btn)
        
        header_layout.addLayout(search_layout)
        
        # Settings row
        settings_layout = QHBoxLayout()
        
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 50)
        self.threads_spin.setValue(10)
        self.threads_spin.setPrefix("Threads: ")
        self.threads_spin.setMinimumHeight(30)
        settings_layout.addWidget(self.threads_spin)
        
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 10000)
        self.limit_spin.setValue(100)
        self.limit_spin.setPrefix("Quantity: ")
        self.limit_spin.setMinimumHeight(30)
        settings_layout.addWidget(self.limit_spin)

        self.score_spin = QSpinBox()
        self.score_spin.setRange(0, 10000)
        self.score_spin.setValue(0)
        self.score_spin.setPrefix("Min Score: ")
        self.score_spin.setMinimumHeight(30)
        settings_layout.addWidget(self.score_spin)
        
        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["Any Rating", "Rating: Safe", "Rating: Questionable", "Rating: Explicit"])
        self.rating_combo.setMinimumHeight(30)
        self.rating_combo.setStyleSheet("background-color: #333; color: white; border: 1px solid #444; border-radius: 4px; padding: 2px 10px;")
        settings_layout.addWidget(self.rating_combo)
        
        self.mass_download_check = QCheckBox("Download All")
        self.mass_download_check.setStyleSheet("color: white;")
        self.mass_download_check.toggled.connect(self.limit_spin.setDisabled)
        settings_layout.addWidget(self.mass_download_check)

        self.ignore_blacklist_check = QCheckBox("Ignore Blacklist")
        self.ignore_blacklist_check.setStyleSheet("color: white;")
        settings_layout.addWidget(self.ignore_blacklist_check)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["All Files", "Images Only", "Videos Only"])
        self.type_filter.setMinimumHeight(30)
        settings_layout.addWidget(self.type_filter)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Elite", "Cyberpunk Neon", "Retro Hacker", "Nordic Frost", "Amoled"])
        self.theme_combo.setMinimumHeight(30)
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        settings_layout.addWidget(self.theme_combo)
        
        settings_layout.addStretch()
        
        self.open_folder_btn = QPushButton("📁 Open Downloads")
        self.open_folder_btn.setMinimumHeight(30)
        self.open_folder_btn.clicked.connect(self.open_downloads)
        settings_layout.addWidget(self.open_folder_btn)
        
        self.creds_btn = QPushButton("🔑 Credentials")
        self.creds_btn.setMinimumHeight(30)
        self.creds_btn.clicked.connect(self.setup_credentials)
        settings_layout.addWidget(self.creds_btn)

        self.blacklist_btn = QPushButton("🚫 Blacklist")
        self.blacklist_btn.setMinimumHeight(30)
        self.blacklist_btn.clicked.connect(self.setup_blacklist)
        settings_layout.addWidget(self.blacklist_btn)
        
        header_layout.addLayout(settings_layout)
        main_layout.addWidget(header_frame)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Split view: Images and Logs
        content_layout = QHBoxLayout()
        
        # Images Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.image_container = QWidget()
        self.image_container.setObjectName("ImageContainer")
        self.image_grid = QGridLayout(self.image_container)
        self.image_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll_area.setWidget(self.image_container)
        content_layout.addWidget(self.scroll_area, 4) # 80% width

        # Log area
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        log_title = QLabel("ACTIVITY LOG")
        log_title.setStyleSheet("font-weight: bold; color: #888; margin-bottom: 5px;")
        log_layout.addWidget(log_title)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        
        content_layout.addWidget(log_container, 1) # 20% width
        
        main_layout.addLayout(content_layout)
        
        self.image_count = 0
        self.columns = 4
        self.image_widgets = {} # Track widgets by file_path for async updates

        # Style
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a1a; }
            QWidget#ImageContainer { background-color: #121212; }
            QFrame#HeaderFrame { background-color: #252525; border-radius: 8px; padding: 5px; }
            QLabel { color: #e1e1e1; }
            QLineEdit { 
                background-color: #333; 
                color: #fff; 
                border: 1px solid #444; 
                border-radius: 6px; 
                padding: 0 12px;
            }
            QLineEdit:focus { border: 1px solid #0078d4; }
            QPushButton { 
                color: #fff; 
                border-radius: 6px; 
                padding: 5px 15px;
                background-color: #3a3a3a;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #222; color: #555; }
            
            QSpinBox {
                background-color: #333;
                color: #fff;
                border: 1px solid #444;
                padding: 5px;
                border-radius: 4px;
            }
            
            QProgressBar { 
                border: none; 
                background-color: #333; 
                border-radius: 4px; 
            }
            QProgressBar::chunk { 
                background-color: #0078d4; 
                border-radius: 4px;
            }
            
            QTextEdit { 
                background-color: #1e1e1e; 
                color: #00ff00; 
                border: 1px solid #333; 
                border-radius: 4px;
                font-family: 'Consolas', 'Monaco', monospace; 
                font-size: 10px; 
            }
            
            QFrame { border: 1px solid #333; border-radius: 6px; }
        """)

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

    def update_autocomplete(self):
        text = self.tag_input.text()
        if not text: return
        
        last_word = self.tag_input.text_under_cursor()
        if len(last_word) < 2: 
            self.completer.popup().hide()
            return

        try:
            results = self.engine.autocomplete_tags(last_word)
            tags = [res.get('value', '') for res in results]
            if tags:
                self.completer_model.setStringList(tags)
                cr = self.tag_input.cursorRect()
                cr.setWidth(self.completer.popup().sizeHintForColumn(0) 
                             + self.completer.popup().verticalScrollBar().sizeHint().width())
                self.completer.complete(cr)
            else:
                self.completer.popup().hide()
        except:
            pass

    def stop_download(self):
        if self.worker:
            self.worker.stop()
            self.log_message("[!] Enviando comando de parada...")
            self.stop_btn.setEnabled(False)
            self.start_btn.setText("STOPPING...")
            self.start_btn.setStyleSheet("background-color: #555; font-weight: bold; color: white; border: none;")

    def update_progress(self, val):
        self.progress_bar.setValue(self.progress_bar.value() + 1) # Just increment

    def log_message(self, msg):
        self.log_area.append(msg)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

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
        
        # Aplicar estilo do tema atual
        theme_name = self.theme_combo.currentText()
        if theme_name == "Cyberpunk Neon":
            img_widget.setStyleSheet("background-color: #0d0221; border: 1px solid #00ffff; border-radius: 0px;")
        elif theme_name == "Retro Hacker":
            img_widget.setStyleSheet("background-color: #000; border: 1px solid #00ff00; border-radius: 0px;")
        elif theme_name == "Nordic Frost":
            img_widget.setStyleSheet("background-color: #fff; border: 1px solid #d8dee9; border-radius: 15px;")
        elif theme_name == "Amoled":
            img_widget.setStyleSheet("background-color: #000; border: 1px solid #222; border-radius: 0px;")
        
        self.image_widgets[file_path] = img_widget
        self.image_grid.addWidget(img_widget, row, col)
        self.image_count += 1
        
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