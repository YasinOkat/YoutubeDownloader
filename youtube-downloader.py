import os

import qdarkstyle
import requests
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QRadioButton, QFileDialog, \
    QComboBox, QProgressBar, QWidget, QHBoxLayout, QMessageBox
from pytube import YouTube


class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle(parent.windowTitle())
        self.setFixedHeight(30)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.title_label = QLabel(self.parent.windowTitle())
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.layout.addWidget(self.title_label, alignment=Qt.AlignHCenter)

        self.button_minimize = QPushButton(self)
        close_icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "close_icon.png")
        minimize_icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "minimize_icon.png")
        self.button_minimize.setStyleSheet("background-color: transparent;")
        self.button_minimize.setIcon(QIcon(minimize_icon))
        self.button_minimize.setFixedSize(30, 30)
        self.button_minimize.clicked.connect(self.parent.showMinimized)

        self.button_close = QPushButton(self)
        self.button_close.setStyleSheet("background-color: transparent;")
        self.button_close.setIcon(QIcon(close_icon))
        self.button_close.setFixedSize(30, 30)
        self.button_close.clicked.connect(self.parent.close)

        self.layout.addStretch()
        self.layout.addWidget(self.button_minimize, alignment=Qt.AlignRight)
        self.layout.addWidget(self.button_close, alignment=Qt.AlignRight)
        self.setLayout(self.layout)

        self.drag_start_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.globalPos() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.parent.move(event.globalPos() - self.drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()


class DownloadThread(QThread):
    progress_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)

    def __init__(self, url, save_path, resolution=None):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.resolution = resolution

    def run(self):
        try:
            if self.resolution:
                self.download_video()
            else:
                self.download_audio()
        except requests.exceptions.ConnectionError:
            self.error_signal.emit("Connection error. Please check your internet connection.")
        except requests.exceptions.Timeout:
            self.error_signal.emit("Request timed out. Please try again later.")
        except requests.exceptions.RequestException:
            self.error_signal.emit("An error occurred during the download. Please try again.")
        except Exception as e:
            self.error_signal.emit(str(e))

    def download_video(self):
        try:
            yt = YouTube(self.url)
            video = yt.streams.filter(res=self.resolution).first()
            video_file = os.path.join(self.save_path, f"{video.default_filename}")
            response = requests.get(video.url, stream=True)

            total_size = int(response.headers.get("Content-Length", 0))
            downloaded_size = 0

            with open(video_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        progress = int((downloaded_size / total_size) * 100)
                        self.progress_signal.emit(progress)

            self.progress_signal.emit(100)
        except KeyError:
            self.error_signal.emit("Selected resolution is not available for this video.")
        except Exception as e:
            self.error_signal.emit(str(e))

    def download_audio(self):
        try:
            yt = YouTube(self.url)
            audio = yt.streams.filter(only_audio=True).first()
            audio_file = os.path.join(self.save_path, f"{audio.default_filename}")
            audio.download(self.save_path)
            mp3_file = os.path.join(self.save_path, "audio.mp3")

            total_size = os.path.getsize(audio_file)
            downloaded_size = 0

            with open(audio_file, "rb") as f:
                with open(mp3_file, "wb") as mp3:
                    while True:
                        chunk = f.read(1024)
                        if not chunk:
                            break

                        mp3.write(chunk)
                        downloaded_size += len(chunk)
                        int((downloaded_size / total_size) * 100)
                        self.emit_audio_progress(downloaded_size, total_size)

            os.remove(audio_file)
            self.progress_signal.emit(100)
        except Exception as e:
            self.error_signal.emit(str(e))

    def emit_audio_progress(self, processed_size, total_size):
        progress = int((processed_size / total_size) * 100)
        self.progress_signal.emit(progress)


class YouTubeDownloaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.setGeometry(100, 100, 400, 300)

        self.setWindowFlags(Qt.FramelessWindowHint)

        self.title_bar = CustomTitleBar(self)
        self.setMenuWidget(self.title_bar)

        self.setStyleSheet(qdarkstyle.load_stylesheet())

        self.url_label = QLabel("YouTube URL:", self)
        self.url_label.setGeometry(20, 40, 100, 20)

        self.url_entry = QLineEdit(self)
        self.url_entry.setGeometry(120, 40, 260, 20)

        self.folder_label = QLabel("Download Folder:", self)
        self.folder_label.setGeometry(20, 70, 100, 20)

        self.folder_entry = QLineEdit(self)
        self.folder_entry.setGeometry(120, 70, 200, 20)

        self.browse_button = QPushButton("Browse", self)
        self.browse_button.setGeometry(330, 70, 50, 20)
        self.browse_button.clicked.connect(self.browse_folder)

        self.format_label = QLabel("Download Format:", self)
        self.format_label.setGeometry(20, 100, 100, 20)

        self.format_mp3 = QRadioButton("MP3", self)
        self.format_mp3.setGeometry(120, 100, 100, 20)
        self.format_mp3.setChecked(True)
        self.format_mp3.clicked.connect(self.hide_resolution_options)

        self.format_mp4 = QRadioButton("MP4", self)
        self.format_mp4.setGeometry(230, 100, 100, 20)
        self.format_mp4.clicked.connect(self.show_resolution_options)

        self.resolution_label = QLabel("Resolution:", self)
        self.resolution_label.setGeometry(20, 130, 100, 20)
        self.resolution_label.hide()

        self.resolution_combo = QComboBox(self)
        self.resolution_combo.setGeometry(120, 130, 150, 20)
        self.resolution_combo.addItems(["360p", "480p", "720p", "1080p"])
        self.resolution_combo.hide()

        self.download_button = QPushButton("Download", self)
        self.download_button.setGeometry(150, 170, 100, 30)
        self.download_button.setStyleSheet("background-color: #428BCA; color: #FFFFFF;")
        self.download_button.clicked.connect(self.start_download)

        self.status_label = QLabel("", self)
        self.status_label.setGeometry(20, 210, 360, 20)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(20, 240, 360, 20)
        self.progress_bar.setTextVisible(False)

        self.download_thread = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_download_progress)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_start_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()

    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        self.folder_entry.setText(folder_path)

    def show_resolution_options(self):
        self.resolution_label.show()
        self.resolution_combo.show()

    def hide_resolution_options(self):
        self.resolution_label.hide()
        self.resolution_combo.hide()

    def start_download(self):
        url = self.url_entry.text()
        save_path = self.folder_entry.text()

        if not url or not save_path:
            self.status_label.setText("Please enter URL and select a folder!")
            return

        if not os.path.isdir(save_path):
            self.status_label.setText("Invalid folder path!")
            return

        choice = "MP4" if self.format_mp4.isChecked() else "MP3"
        resolution = self.resolution_combo.currentText() if choice == "MP4" else None

        self.progress_bar.setValue(0)

        self.download_thread = DownloadThread(url, save_path, resolution)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.error_signal.connect(self.show_error_message)
        self.download_thread.start()

        self.download_button.setEnabled(False)
        self.status_label.setText("Downloading...")
        self.timer.start(1000)

    def show_error_message(self, error_message):
        QMessageBox.critical(self, "Error", error_message)
        self.download_button.setEnabled(True)
        self.status_label.setText("Error occurred during download!")

    def check_download_progress(self):
        if self.download_thread.isFinished():
            self.timer.stop()

    def update_progress(self, progress):
        if progress == -1:
            self.progress_bar.setValue(0)
            self.status_label.setText("Error occurred during download!")
        elif progress == 100:
            self.progress_bar.setValue(100)
            self.status_label.setText("Download completed successfully!")
        else:
            self.progress_bar.setValue(progress)

        if progress == -1 or progress == 100:
            self.download_button.setEnabled(True)


if __name__ == "__main__":
    app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    window = YouTubeDownloaderGUI()
    window.show()
    app.exec_()
