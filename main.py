import sys
import os
from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel,
                               QLineEdit, QHBoxLayout, QVBoxLayout,
                               QPushButton, QWidget, QListWidget,
                               QListWidgetItem, QRadioButton, QGroupBox,
                               QProgressBar, QMessageBox)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QPixmap
from pytube import YouTube, Playlist
import threading

videos = []
WINDOW_HEIGHT = 700
WINDOW_WIDTH = 800

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("YT Downloader")
        self.setMinimumWidth(WINDOW_WIDTH)
        self.setMinimumHeight(WINDOW_HEIGHT)

        central = QWidget(self)

        self.video_url_text = QLineEdit(placeholderText="Url of the video")
        self.video_image_frame = QLabel()
        self.video_image = QPixmap()
        video_streams = QListWidget()
        self.video_image_frame.setPixmap(self.video_image)
        self.search_button = QPushButton("Search")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(400)
        self.download_button = QPushButton("Download")
        self.clear_button = QPushButton("Clear")
        self.video_frame = QWebEngineView()
        self.stream_list_widget = QListWidget()
        self.show_details_button = QPushButton("Show details")
        self.audio_only_button = QRadioButton("Audio Only")
        self.single_video_button = QRadioButton("Video")
        self.playlist_button = QRadioButton("Playlist")
        self.single_video_button.setChecked(True)

        self.video_url_text.setMinimumHeight(35)
        self.search_button.setMinimumHeight(35)
        self.clear_button.setMinimumHeight(35)
        self.download_button.setMinimumHeight(35)
        self.show_details_button.setMinimumHeight(35)

        self.search_button.clicked.connect(self.search_video)
        self.download_button.clicked.connect(lambda: self.video_downloader_handler(self.video))
        self.clear_button.clicked.connect(self.clear)
        self.show_details_button.clicked.connect(self.show_details)

        layout = QVBoxLayout()
        layout_gbox = QHBoxLayout()
        video_type_gbox = QGroupBox()
        layout_bottom = QHBoxLayout()
        bottom_gbox = QGroupBox()
        #bottom_gbox.setMaximumWidth(800)
        bottom_gbox.setMaximumHeight(50)
        bottom_gbox.setMinimumHeight(35)
        video_type_gbox.setMinimumHeight(35)
        #video_type_gbox.setMaximumWidth(800)
        video_type_gbox.setMaximumHeight(50)
        video_type_gbox.setMinimumHeight(35)
        layout_gbox.addWidget(self.single_video_button)
        layout_gbox.addWidget(self.playlist_button)
        video_type_gbox.setLayout(layout_gbox)
        layout_bottom.addWidget(self.audio_only_button)
        layout_bottom.addWidget(self.progress_bar)
        bottom_gbox.setLayout(layout_bottom)

        layout.addWidget(self.video_url_text)
        layout.addWidget(video_type_gbox)
        layout.addWidget(self.search_button)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.video_frame)
        # layout.addWidget(self.video_image_frame)
        # layout.addWidget(video_streams)
        layout.addWidget(bottom_gbox)
        layout.addWidget(self.stream_list_widget)
        self.stream_list_widget.hide()
        layout.addWidget(self.show_details_button)
        layout.addWidget(self.download_button)

        central.setLayout(layout)
        self.setCentralWidget(central)

    def search_video(self):
        try:
            self.show_details_button.setText("Show details")

            video_url = self.video_url_text.text()
            self.video = YouTube(video_url)

            self.stream_list_widget.hide()

            params = video_url.split("?")[-1].split("&")
            
            for param in params:
                key, value = param.split('=')
                if key == 'v':
                    video_id = value
                
            if video_id is None:
                QMessageBox.critical(self.window, "Error", "An error occurred: Video can't be found!")
            
            embed_link = "https://www.youtube.com/embed/" + video_id
            embed_link_complete = f"<style>body {{background-color: #121212; /* Dark background color */color: #FFFFFF; /* Text color */}}</style><iframe width=\"{min(1000, self.size().width()-35)}\" height=\"{min(720, (self.size().height()/2)-30)}\" src=\"{embed_link}\" title=\"{self.video.title}\" \"frameborder=\"0\" allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\" allowfullscreen></iframe>"
            self.video_frame.setHtml(embed_link_complete)

            videos.append(self.video)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}") 

    def clear(self):
        self.video_frame.setHtml("")
        self.video_url_text.setText("")

    def show_details(self):
        self.streams = {}
        if self.stream_list_widget.isVisible():
            self.stream_list_widget.hide()
            self.show_details_button.setText("Show details")
        else:
            self.show_details_button.setText("Hide details")
            if self.stream_list_widget.count() > 1:
                self.stream_list_widget.clear()
            for index, stream in enumerate(self.video.streams):
                stream_item = QListWidgetItem(str(stream))
                self.stream_list_widget.addItem(stream_item)
                self.streams[index] = stream
            self.stream_list_widget.show()

    def video_downloader_handler(self, video):
        stream = None
        if self.audio_only_button.isChecked():     
            stream = self.video.streams.filter(file_extension="mp4", only_audio=True).first()
        elif self.stream_list_widget.selectedItems():
            index = self.stream_list_widget.currentRow()
            video_download = self.streams[index]
        else:
            stream = self.video.streams.filter(file_extension="mp4").get_highest_resolution()
            
        print("video:", video)
        print("stream:", stream)

        self.video_downloader_thread = QThread()
        self.video_downloader = VideoDownloaderWorker(video, stream)
        self.video_downloader.moveToThread(self.video_downloader_thread)
        self.video_downloader_thread.started.connect(self.video_downloader.download_video)
        self.video_downloader.progress.connect(lambda step: self.progress_bar.setValue(step))
        self.video_downloader.error.connect(lambda err: QMessageBox.critical(self, "Error", "An error occurred: " + err.__str__()))

        self.video_downloader_thread.start()

class VideoDownloaderWorker(QThread):
    started = Signal(int)
    finished = Signal()
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, video, stream):
        super().__init__()
        self.video = video
        self.stream = stream

        self.video.register_on_complete_callback(self.on_complete_callback)
        self.video.register_on_progress_callback(self.on_progress_callback)            

    def download_video(self):
        self.started.emit(0)
        # This part is for playlist installation, will check it later
        #if self.window.playlist_button.isChecked():
            #return

        # This is for progress bar
        #self.window.filesize = stream.filesize
        try:            
            home_dir = os.path.expanduser('~')
            if os.name == "nt":
                self.stream.download(f"{home_dir}/Videos")
            else:
                self.stream.download(f"{home_dir}/Videos")
        except Exception as err:
            return self.error.emit(err.__str__())
        self.finished.emit()

    def on_complete_callback(self, stream, file_path):
        pass

    def on_progress_callback(self, chunk, file_handle, bytes_remaining):
        # TODO: change this when fixing progress bar
        self.filesize = self.stream.filesize
        # total_size = stream.filesize
        # bytes_downloaded = total_size - bytes_remaining
        # percentage = int((bytes_downloaded / total_size) * 100)

        # global filesize
        remaining = (100 * bytes_remaining) / self.filesize
        step = 100 - int(remaining)

        #Change this to step
        self.progress.emit(step)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    frame = MainWindow()

    frame.show()
    app.exec()
