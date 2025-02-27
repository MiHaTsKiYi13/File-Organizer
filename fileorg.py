import sys
import os
import shutil
from datetime import datetime

from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel, QFileDialog, QTextEdit, QProgressBar,
                             QGraphicsDropShadowEffect, QGraphicsOpacityEffect)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal, QThread, QEasingCurve
from PyQt6.QtGui import QFont, QColor

from PIL import Image
from PIL.ExifTags import TAGS

# Поддерживаемые расширения для фотографий
PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tiff"}

def get_image_year(filepath):
    """
    Определяет год создания изображения.
    Сначала пробует прочитать EXIF DateTimeOriginal, если не удалось — берёт год модификации.
    """
    try:
        with Image.open(filepath) as img:
            exif_data = img._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    if TAGS.get(tag, tag) == "DateTimeOriginal":
                        return value.split(":")[0]
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y")

class Worker(QThread):
    progress_update = pyqtSignal(int)
    log_update = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, folder):
        super().__init__()
        self.folder = folder
        self._is_running = True

    def run(self):
        files = [f for f in os.listdir(self.folder) if os.path.isfile(os.path.join(self.folder, f))]
        total = len(files)
        if total == 0:
            self.log_update.emit("Нет файлов для организации.")
            self.finished_signal.emit()
            return

        # Если все файлы — фото, используем режим сортировки по году
        if all(f.lower().split('.')[-1] in PHOTO_EXTENSIONS for f in files if '.' in f):
            mode = "photo"
            self.log_update.emit("Сортируем фотографии по году.")
        else:
            mode = "default"
            self.log_update.emit("Сортируем файлы по расширению.")

        processed = 0
        for filename in files:
            if not self._is_running:
                self.log_update.emit("Операция отменена.")
                break
            filepath = os.path.join(self.folder, filename)
            if mode == "photo":
                year = get_image_year(filepath)
                target_dir = os.path.join(self.folder, f"Фотографии {year}")
            else:
                ext = filename.split('.')[-1] if '.' in filename else "без_расширения"
                target_dir = os.path.join(self.folder, ext)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                self.log_update.emit(f"Создана папка: {target_dir}")
            try:
                shutil.move(filepath, os.path.join(target_dir, filename))
                self.log_update.emit(f"{filename} → {os.path.basename(target_dir)}")
            except Exception as e:
                self.log_update.emit(f"Ошибка с {filename}: {e}")
            processed += 1
            progress = int((processed / total) * 100)
            self.progress_update.emit(progress)
            self.msleep(100)
        self.log_update.emit("Организация завершена.")
        self.finished_signal.emit()

    def stop(self):
        self._is_running = False

class FileOrganizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Органайзер файлов")
        self.setFixedSize(500, 400)
        self.worker = None
        self.setup_ui()
        self.fade_in()

    def setup_ui(self):
        self.central = QWidget()
        self.setCentralWidget(self.central)
        layout = QVBoxLayout(self.central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Органайзер файлов")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        folder_layout = QHBoxLayout()
        self.folder_line = QLineEdit()
        self.folder_line.setPlaceholderText("Выберите папку")
        self.folder_line.setReadOnly(True)
        folder_btn = QPushButton("Выбрать папку")
        folder_btn.setFont(QFont("Segoe UI", 10))
        folder_btn.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_line)
        folder_layout.addWidget(folder_btn)
        layout.addLayout(folder_layout)

        self.organize_btn = QPushButton("Организовать")
        self.organize_btn.setFont(QFont("Segoe UI", 14))
        self.organize_btn.clicked.connect(self.start_organization)
        layout.addWidget(self.organize_btn)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        layout.addWidget(self.progress)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        # Стиль Windows 11
        self.central.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border-radius: 10px;
            }
            QLineEdit, QTextEdit {
                background-color: #2d2d30;
                border: none;
                padding: 8px;
                border-radius: 5px;
                font-family: "Segoe UI";
            }
            QPushButton {
                background-color: #0078d7;
                border: none;
                padding: 8px;
                border-radius: 5px;
                font-family: "Segoe UI";
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QProgressBar {
                background-color: #2d2d30;
                border: 1px solid #444444;
                border-radius: 5px;
                text-align: center;
                font-family: "Segoe UI";
                color: #ffffff;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #0078d7, stop:1 #00bcf2);
                border-radius: 5px;
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.central.setGraphicsEffect(shadow)

    def fade_in(self):
        effect = QGraphicsOpacityEffect(self.central)
        self.central.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(1000)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        self.anim = anim  # сохраняем ссылку

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.folder_line.setText(folder)
            self.log(f"Папка выбрана: {folder}")

    def start_organization(self):
        folder = self.folder_line.text()
        if not folder or not os.path.isdir(folder):
            self.log("Неверная папка.")
            return
        self.organize_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log("Начинаем организацию...")
        self.worker = Worker(folder)
        self.worker.progress_update.connect(self.progress.setValue)
        self.worker.log_update.connect(self.log)
        self.worker.finished_signal.connect(self.finish)
        self.worker.start()

    def finish(self):
        self.organize_btn.setEnabled(True)
        self.log("Готово!")

    def log(self, message):
        self.log_area.append(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileOrganizerApp()
    window.show()
    sys.exit(app.exec())
