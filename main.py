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

videos = []


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("YT Downloader")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        central = QWidget(self)

        self.video_url_text = QLineEdit(placeholderText="Url of the video")
        self.video_image_frame = QLabel()
        self.video_image = QPixmap()
        video_streams = QListWidget()
        self.video_image_frame.setPixmap(self.video_image)
        search_button = QPushButton("Search")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(400)
        download_button = QPushButton("Download")
        clear_button = QPushButton("Clear")
        self.video_frame = QWebEngineView()
        self.stream_list_widget = QListWidget()
        self.show_details_button = QPushButton("Show details")
        self.audio_only_button = QRadioButton("Audio Only")
        self.single_video_button = QRadioButton("Video")
        self.playlist_button = QRadioButton("Playlist")
        self.single_video_button.setChecked(True)

        search_button.clicked.connect(self.search_video)
        download_button.clicked.connect(self.download_video_thread)
        clear_button.clicked.connect(self.clear)
        self.show_details_button.clicked.connect(self.show_details)

        layout = QVBoxLayout()
        layout_gbox = QHBoxLayout()
        video_type_gbox = QGroupBox()
        layout_bottom = QHBoxLayout()
        bottom_gbox = QGroupBox()
        bottom_gbox.setMaximumWidth(800)
        bottom_gbox.setMaximumHeight(40)
        video_type_gbox.setMaximumWidth(800)
        video_type_gbox.setMaximumHeight(35)
        layout_gbox.addWidget(self.single_video_button)
        layout_gbox.addWidget(self.playlist_button)
        video_type_gbox.setLayout(layout_gbox)
        layout_bottom.addWidget(self.audio_only_button)
        layout_bottom.addWidget(self.progress_bar)
        bottom_gbox.setLayout(layout_bottom)

        layout.addWidget(self.video_url_text)
        layout.addWidget(video_type_gbox)
        layout.addWidget(search_button)
        layout.addWidget(clear_button)
        layout.addWidget(self.video_frame)
        # layout.addWidget(self.video_image_frame)
        # layout.addWidget(video_streams)
        layout.addWidget(bottom_gbox)
        layout.addWidget(self.stream_list_widget)
        self.stream_list_widget.hide()
        layout.addWidget(self.show_details_button)
        layout.addWidget(download_button)

        central.setLayout(layout)
        self.setCentralWidget(central)

    def search_video(self):
        try:
            self.show_details_button.setText("Show details")

            video_url = self.video_url_text.text()
            self.video = YouTube(video_url)

            self.video.register_on_complete_callback(self.on_complete_callback)
            self.video.register_on_progress_callback(self.on_progress_callback)

            self.stream_list_widget.hide()

            params = video_url.split("?")[-1].split("&")
            print(params)
            for param in params:
                key, value = param.split('=')
                if key == 'v':
                    video_id = value
                
            if video_id is None:
                QMessageBox.critical(self.window, "Error", "An error occurred: Video can't be found!")

            print(video_id)
            
            embed_link = "https://www.youtube.com/embed/" + video_id
            embed_link_complete = "<iframe width=\"750\" height=\"340\" src=\"" + embed_link + "\" title=\"" + self.video.title +" \"frameborder=\"0\" allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\" allowfullscreen></iframe>"
            self.video_frame.setHtml(embed_link_complete)

            """
            <iframe width="1280" height="720" src="https://www.youtube.com/embed/665rzOSSxWA" title="Computing the Euclidean Algorithm in raw ARM Assembly" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>"""

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

    def on_complete_callback(self, stream, file_path):
        pass

    def on_progress_callback(self, chunk, file_handle, bytes_remaining):
        # total_size = stream.filesize
        # bytes_downloaded = total_size - bytes_remaining
        # percentage = int((bytes_downloaded / total_size) * 100)

        # global filesize
        remaining = (100 * bytes_remaining) / self.filesize
        step = 100 - int(remaining)

        self.progress_bar.setValue(step)


    def download_video_thread(self):
        thread = QThread()
        self.download_video_worker = DownloaderWorker(self)

        #   self.download_video_worker.moveToThread(thread)
        self.download_video_worker.started.connect(self.progress_bar.setValue)
        
        self.download_video_worker.start()

class DownloaderWorker(QThread):
    started = Signal(int)
    finished = Signal()
    #progress = Signal()
    #error = Signal(tuple)

    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def run(self):
        self.started.emit(0)
        if self.window.playlist_button.isChecked():
            return
        if self.window.stream_list_widget.selectedItems():
            index = self.window.stream_list_widget.currentRow()
            video_download = self.window.streams[index]
        else:
            if self.window.audio_only_button.isChecked():
                try:
                    video_download = self.window.video.streams.filter(file_extension="mp4", only_audio=True).first()
                except Exception as err:
                    QMessageBox.critical(self.window, "Error", "An error occurred: " + err.__str__())
                    return 0
            else:
                try:
                    video_download = self.window.video.streams.filter(file_extension="mp4").get_highest_resolution()
                    QMessageBox.critical(self.window, "Error", "An error occurred: " + err.__str__())
                except Exception as err:
                    return 0
            self.window.filesize = self.window.video_download.filesize
        home_dir = os.path.expanduser('~')
        if os.name == "nt":
            video_download.download(f"{home_dir}/Videos")
        else:
            video_download.download(f"{home_dir}/Videos")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    frame = MainWindow()

    frame.show()
    app.exec()
