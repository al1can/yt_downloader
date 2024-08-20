import sys
import os
from PySide6.QtCore import Qt, QThread, QObject, Signal, QTimer, QMetaObject, Q_ARG, Slot
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel,
                               QLineEdit, QHBoxLayout, QVBoxLayout,
                               QPushButton, QWidget, QListWidget,
                               QListWidgetItem, QRadioButton, QGroupBox,
                               QProgressBar, QMessageBox, QStyle,
                               QFileDialog, QDialog)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QPixmap, QColor, QPainter, QIcon
from pytubefix import YouTube, Playlist
import threading
import configparser

WINDOW_HEIGHT = 700
WINDOW_WIDTH = 800

class MainWindow(QMainWindow):
    started = Signal(int)
    progress_updated = Signal(int)
    download_completed = Signal(int)
    
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.config_init()

        self.setWindowTitle("YT Downloader")
        self.setMinimumWidth(WINDOW_WIDTH)
        self.setMinimumHeight(WINDOW_HEIGHT)

        central = QWidget(self)

        self.url_text = QLineEdit(placeholderText="Url of the video")
        self.video_image_frame = QLabel()
        self.video_image = QPixmap()
        video_streams = QListWidget()
        self.video_image_frame.setPixmap(self.video_image)
        self.search_button = QPushButton("Search")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(400)
        self.download_button = QPushButton("Download")
        self.directory_button = QPushButton('')
        pixmapi = getattr(QStyle, 'SP_DirIcon')
        icon = self.style().standardIcon(pixmapi)
        colored_icon = self.create_colored_icon(icon, 'white')
        self.directory_button.setIcon(colored_icon)
        self.clear_button = QPushButton("Clear")
        self.video_frame = QWebEngineView()
        self.stream_list_widget = QListWidget()
        self.show_details_button = QPushButton("Show details")
        self.audio_only_button = QRadioButton("Audio Only")
        self.single_video_button = QRadioButton("Video")
        self.playlist_button = QRadioButton("Playlist")
        self.single_video_button.setChecked(True)

        self.url_text.setMinimumHeight(35)
        self.search_button.setMinimumHeight(35)
        self.clear_button.setMinimumHeight(35)
        self.download_button.setMinimumHeight(35)
        self.directory_button.setMinimumHeight(35)
        self.show_details_button.setMinimumHeight(35)

        self.directory_button.setMaximumWidth(50)

        self.search_button.clicked.connect(self.search)
        self.download_button.clicked.connect(self.download_handler)
        self.clear_button.clicked.connect(self.clear)
        self.show_details_button.clicked.connect(self.show_details)
        self.directory_button.clicked.connect(self.change_download_directory)

        self.download_completed.connect(self.on_download_complete)
        self.progress_updated.connect(self.update_progress)

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

        layout.addWidget(self.url_text)
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

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.download_button)
        bottom_layout.addWidget(self.directory_button)

        layout.addLayout(bottom_layout)

        central.setLayout(layout)
        self.setCentralWidget(central)

        self.video = None
        self.videos = []

        self.resolution_window = None

    def config_init(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        try:
            self.download_directory = config.get('General', 'download_directory')
        except:        
            home_dir = os.path.expanduser('~')
            self.download_directory = f"{home_dir}/Videos"
            config['General'] = {'download_directory': self.download_directory}
            with open('config.ini', 'w') as configfile:
                config.write(configfile)

    def config_change_directory(self):
        config = configparser.ConfigParser()
        config['General'] = {'download_directory': self.download_directory}
        with open('config.ini', 'w+') as configfile:
            config.write(configfile)

    def create_colored_icon(self, base_icon, color):
        pixmap = base_icon.pixmap(64, 64)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color))
        painter.end()
        return QIcon(pixmap)

    @Slot(int)
    def update_progress(self, value):
        self.progress_bar.setValue(value)

    @Slot()
    def on_download_complete(self):
        QMessageBox.information(self, "Download Complete", f"Download finished: {self.download_directory}")

    def search(self):
        if self.single_video_button.isChecked():
            self.search_video()
        elif self.playlist_button.isChecked():
            self.search_playlist()

    def search_video(self):
        self.progress_updated.emit(0)
        
        try:
            self.show_details_button.setText("Show details")

            video_url = self.url_text.text()
            self.video = YouTube(video_url)

            self.video.register_on_complete_callback(self._on_complete_callback)
            self.video.register_on_progress_callback(self._on_progress_callback)

            self.stream_list_widget.hide()

            params = video_url.split("?")[-1].split("&")
            
            for param in params:
                key, value = param.split('=')
                if key == 'v':
                    video_id = value
                
            if video_id is None:
                QMessageBox.critical(self, "Error", "An error occurred: Video can't be found!")
            
            embed_link = "https://www.youtube.com/embed/" + video_id
            embed_link_complete = f"<style>body {{background-color: #121212; /* Dark background color */color: #FFFFFF; /* Text color */}}</style><iframe width=\"{min(1000, self.size().width()-35)}\" height=\"{min(720, (self.size().height()/2)-30)}\" src=\"{embed_link}\" title=\"{self.video.title}\" \"frameborder=\"0\" allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\" allowfullscreen></iframe>"
            self.video_frame.setHtml(embed_link_complete)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}") 

    def search_playlist(self):
        self.progress_updated.emit(0)

        try:
            playlist_url = self.url_text.text()
            self.playlist = Playlist(playlist_url)
            
            #self.playlist.register_on_complete_callback(self._on_complete_callback)
            #self.playlist.register_on_progress_callback(self._on_progress_callback)

            self.stream_list_widget.hide()

            # https://www.youtube.com/playlist?list=OLAK5uy_mWtWynXa5NeLQEJjvrmVZmmO48G4eBBWg
            params = playlist_url.split("?")[-1].split("&")

            for param in params:
                key, value = param.split('=')
                if key == 'list':
                    playlist_id = value

            if playlist_id is None:
                QMessageBox.critical(self, "Error", "An error occurred: Video can't be found!")

            embed_link = "https://www.youtube.com/embed/videoseries?list=" + playlist_id
            embed_link_complete = f"<style>body {{background-color: #121212; /* Dark background color */color: #FFFFFF; /* Text color */}}</style><iframe width=\"{min(1000, self.size().width()-35)}\" height=\"{min(720, (self.size().height()/2)-30)}\" src=\"{embed_link}\" title=\"YouTube video player\" \"frameborder=\"0\" allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share\" allowfullscreen></iframe>"
            self.video_frame.setHtml(embed_link_complete)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}") 


    def clear(self):
        self.video_frame.setHtml("")
        self.url_text.setText("")

        self.progress_updated.emit(0)

    def show_details(self):
        self.streams = {}
        if self.video is None:
            return
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

    def _on_complete_callback(self, stream, file_path):
        self.download_completed.emit(file_path)

    def _on_complete_callback_playlist(self, stream, file_path):
        self.downloaded_video_playlist+=1
        if self.downloaded_video_playlist==len(self.playlist_streams):
            self.download_completed.emit(file_path)
        
    def _on_progress_callback(self, chunk, file_handle, bytes_remaining):
        self.filesize = self.stream.filesize
        remaining = (100 * bytes_remaining) / self.filesize
        step = 100 - int(remaining)

        # Update progress bar in the main thread
        #QMetaObject.invokeMethod(self.window.progress_bar, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
        #self.progress_bar.setValue(step)
        self.progress_updated.emit(int(step))

    def _on_progress_callback_playlist(self, chunk, file_handle, bytes_remaining):
        #TODO: progress bar is broken 
        self.downloaded_bytes_playlist=self.playlist_video_stream.filesize - bytes_remaining
        step = (100 * self.downloaded_bytes_playlist) / self.playlist_total_size

        # Update progress bar in the main thread
        #QMetaObject.invokeMethod(self.window.progress_bar, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
        #self.progress_bar.setValue(step)
        self.progress_updated.emit(int(step)) 

    def change_download_directory(self):
        options = QFileDialog.Options()
        folder_dialog = QFileDialog.getExistingDirectory(self, "Select Directory", options=options)

        if folder_dialog:
            self.download_directory = folder_dialog
        
        self.config_change_directory()

    @Slot()
    def download_handler(self):
        if self.single_video_button.isChecked():
            self.video_downloader_handler()
        elif self.playlist_button.isChecked():
            self.playlist_downloader_handler()

    def video_downloader_handler(self):
        self.stream = None
        if self.audio_only_button.isChecked():     
            self.stream = self.video.streams.filter(file_extension="mp4", only_audio=True).first()
        elif self.stream_list_widget.selectedItems():
            index = self.stream_list_widget.currentRow()
            self.stream = self.streams[index]
        else:
            self.stream = self.video.streams.filter(file_extension="mp4").get_highest_resolution()
            
        print("video:", self.video)
        print("stream:", self.stream)

        #self.stream.download(self.download_directory)

        download_thread = threading.Thread(target=self.download_video)
        download_thread.daemon = True
        download_thread.start()

        #self.video_downloader_thread = QThread()
        #self.video_downloader = VideoDownloaderWorker(video, self.stream, self.download_directory)
        #self.video_downloader.moveToThread(self.video_downloader_thread)
        #self.video_downloader_thread.started.connect(self.video_downloader.download_video)
        #self.video_downloader.error.connect(lambda err: QMessageBox.critical(self, "Error", "An error occurred: " + err.__str__()))

        #self.video_downloader_thread.start()

    def set_resolution_window(self):
        pass
        
    def playlist_downloader_handler(self):
        self.resolution_window = ResolutionWindow()
        self.resolution_window.select_button.clicked.connect(self.resolution_window.return_state)
        self.resolution_window.select_button.clicked.connect(self.resolution_window.hide)
        #self.resolution_window.resolution_selected.connect(self.start_download_thread)
        if self.audio_only_button.isChecked()==False:
            self.resolution_window.exec()
        self.playlist_total_size = 0
        self.downloaded_video_playlist = 0
        self.downloaded_bytes_playlist = 0
        self.playlist_streams = []
        for video_url in self.playlist:
            self.playlist_video = YouTube(video_url)
            self.playlist_video.register_on_complete_callback(self._on_complete_callback_playlist)
            self.playlist_video.register_on_progress_callback(self._on_progress_callback_playlist)

            if self.audio_only_button.isChecked():
                self.playlist_video_stream = self.playlist_video.streams.filter(file_extension="mp4", only_audio=True).first()
            else:
                self.playlist_video_stream = self.playlist_video.streams.filter(res=self.resolution_window.resolution_selected, file_extension="mp4").first()
            if self.playlist_video_stream is None:
                self.playlist_video_stream = self.playlist_video.streams.filter(file_extension="mp4").first()

            self.playlist_total_size+=self.playlist_video_stream.filesize

            print(self.playlist_video_stream)
            self.playlist_streams.append(self.playlist_video_stream)
        for stream in self.playlist_streams:
            stream.download()

    def start_download_thread(self, resolution):
        download_thread = threading.Thread(target=self.download_playlist, args=(resolution,))
        download_thread.daemon = True
        download_thread.start()

    def download_video(self):
        try:
            self.resolution_window.hide()
        except:
            pass

        try:
            self.stream.download(self.download_directory)
        except Exception as err:
            QMessageBox.critical(self, "Error", "An error occurred: Video couldn't be downloaded!" + err.__str__())
    
        # This is for progress bar
        #self.window.filesize = self.stream.filesize

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)

class ResolutionWindow(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Resolution")
        self.setMaximumHeight(200)
        self.setMaximumWidth(300)
        self.setMinimumHeight(200)
        self.setMinimumWidth(300)

        # Radio buttons for resolution selection
        self.radio_button_1080p = QRadioButton("1080p")
        self.radio_button_720p = QRadioButton("720p")
        self.radio_button_480p = QRadioButton("480p")
        self.radio_button_360p = QRadioButton("360p")

        # Select button
        self.select_button = QPushButton("Select")
        # self.select_button.clicked.connect(self.return_button_state)

        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select the resolution you want to download:"))
        layout.addWidget(self.radio_button_1080p)
        layout.addWidget(self.radio_button_720p)
        layout.addWidget(self.radio_button_480p)
        layout.addWidget(self.radio_button_360p)
        layout.addWidget(self.select_button)

        self.setLayout(layout)

    def return_state(self):
        if self.radio_button_1080p.isChecked():
            self.resolution_selected = "1080p"
        elif self.radio_button_720p.isChecked():
            self.resolution_selected = "720p"
        elif self.radio_button_480p.isChecked():
            self.resolution_selected = "480p"
        elif self.radio_button_360p.isChecked():
            self.resolution_selected = "360p"

class VideoDownloaderWorker(QObject):
    started = Signal(int)
    finished = Signal()
    #progress = Signal()
    error = Signal(str)

    def __init__(self, video, stream, download_directory):
        super().__init__()
        self.video = video
        self.stream = stream
        self.download_directory = download_directory

    def download_video(self):
        self.started.emit(0)
        # This part is for playlist installation, will check it later
        #if self.window.playlist_button.isChecked():
            #return

        # This is for progress bar
        self.window.filesize = self.stream.filesize
        self.stream.download(self.download_directory)
        try:
            self.stream.download(self.download_directory)
            print("adasdsad")
        except Exception as err:
            print("dadasdasd")
            return self.error.emit(err.__str__())
        self.finished.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    frame = MainWindow()

    frame.show()
    app.exec()