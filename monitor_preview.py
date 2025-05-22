# monitor_preview.py
import logging

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QUrl, Qt, QEventLoop, QByteArray, QBuffer, Slot
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QGuiApplication
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply

logger = logging.getLogger(__name__)

class MonitorPreview(QLabel):
    def __init__(self, original_label, layout, monitor, stretch, shared_network_manager, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.network_manager = shared_network_manager
        self.monitor = monitor
        self.stretch = stretch

        # Copy and set properties
        self.setObjectName(original_label.objectName())
        self.setAlignment(original_label.alignment())
        self.setTextFormat(original_label.textFormat())
        self.setStyleSheet(original_label.styleSheet())
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        # Copy size policies
        self.setSizePolicy(original_label.sizePolicy())
        self.setMinimumSize(original_label.minimumSize())
        self.setMaximumSize(original_label.maximumSize())

        # Replace the original label with the new
        if layout is not None:
            for i in range(layout.count()):
                if layout.itemAt(i).widget() == original_label:
                    layout.replaceWidget(original_label, self)
                    break

        # Delete the original label
        original_label.deleteLater()

    def dragEnterEvent(self, event: QDragEnterEvent):
        # Accept event if it contains a URL or image
        mime_data = event.mimeData()
        if mime_data.hasUrls() or mime_data.hasImage():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            # Handle URLs (e.g., from browser drag)
            urls = mime_data.urls()
            if urls:
                image_url = urls[0].toString()
                self.load_image_from_url(image_url)
        elif mime_data.hasImage():
            # Handle image data directly
            image = mime_data.imageData()
            if image:
                if self.stretch:
                    self.setPixmap(QPixmap.fromImage(image.scaled(self.size())))
                else:
                    self.setPixmap(QPixmap.fromImage(image.scaledToHeight(self.size().height())))

                self.monitor.showSlide(image, self.stretch)
        event.acceptProposedAction()

    def load_image(self, image):
        if image:
            if self.stretch:
                self.setPixmap(QPixmap.fromImage(image.scaled(self.size())))
            else:
                self.setPixmap(QPixmap.fromImage(image.scaledToHeight(self.size().height())))
            self.monitor.showImage(image, self.stretch)

    def load_image_from_url(self, droppped_url: str):
        # Use QNetworkAccessManager to fetch the image
        url = QUrl(droppped_url)
        request = QNetworkRequest(url)
        reply = self.network_manager.get(request)

        # Wait for the reply to finish
        event_loop = QEventLoop()
        reply.finished.connect(event_loop.quit)
        event_loop.exec()

        # Process the downloaded data
        if reply.error() == QNetworkReply.NetworkError.NoError:
            # Read data into a QByteArray
            image_data = reply.readAll()

            # Use QBuffer to wrap the QByteArray and load the pixmap
            buffer = QBuffer(QByteArray(image_data))
            buffer.open(QBuffer.ReadOnly)
            pixmap = QPixmap()
            if pixmap.loadFromData(buffer.data()):
                if self.stretch:
                    self.setPixmap(pixmap.scaled(self.size()))
                else:
                    self.setPixmap(pixmap.scaledToHeight(self.size().height()))

                self.monitor.dropImage(pixmap, self.stretch)
            else:
                logger.warning(f"Failed to load image from URL {url.toDisplayString()}")
        else:
            logger.warning(f"Error downloading image: {reply.errorString()}")
        reply.deleteLater()

    @Slot()
    def blackout(self):
        self.clear()
        self.setStyleSheet("background:black; color:black")
        self.monitor.blackout()

    @Slot()
    def paste_image(self):
        pixmap = QGuiApplication.clipboard().pixmap()
        if pixmap != None:
            if self.stretch:
                self.setPixmap(pixmap.scaled(self.size()))
            else:
                self.setPixmap(pixmap.scaledToHeight(self.size().height()))

            self.monitor.pasteImage(self.stretch)

    @Slot(bool)
    def previewStretch(self, stretchState):
        if stretchState ==  Qt.Checked:
            self.stretch = True
        else:
            self.stretch = False

