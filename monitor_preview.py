import logging
from PySide6.QtCore import QUrl, Qt, Slot
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QGuiApplication
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply

# Import our text-overlay rendering engine class
from games_feature import SmartOverlayLabel

logger = logging.getLogger(__name__)

class MonitorPreview(SmartOverlayLabel):
    """
    Manages the display monitors' dashboard previews. Inherits directly
    from SmartOverlayLabel to share the permanent, leak-protected animation engine.
    """
    def __init__(self, original_label, layout, monitor, stretch, shared_network_manager, parent=None):
        # Initialize the single permanent QMovie container inside SmartOverlayLabel
        super().__init__(parent)

        self.setAcceptDrops(True)
        self.network_manager = shared_network_manager
        self.monitor = monitor
        self.stretch = stretch

        # Copy and set properties from placeholder configuration elements
        self.setObjectName(original_label.objectName())
        self.setAlignment(original_label.alignment())
        self.setTextFormat(original_label.textFormat())
        self.setStyleSheet(original_label.styleSheet())
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        # Copy size policies
        self.setSizePolicy(original_label.sizePolicy())
        self.setMinimumSize(original_label.minimumSize())
        self.setMaximumSize(original_label.maximumSize())

        # Replace the original label with the new one dynamically inside layout tracking
        if layout is not None:
            for i in range(layout.count()):
                if layout.itemAt(i).widget() == original_label:
                    layout.replaceWidget(original_label, self)
                    break

        # Delete the placeholder instance cleanly
        original_label.deleteLater()

    def capture_window(self):
        """Grabs the current frame content of the projection QMainWindow surface."""
        pixmap = self.monitor.grab()
        self.clear_asset()

        scaled_pixmap = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled_pixmap)

    def dragEnterEvent(self, event: QDragEnterEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls() or mime_data.hasImage():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                image_url = urls[0].toString()
                self.load_image_from_url(image_url)
        elif mime_data.hasImage():
            image = mime_data.imageData()
            self.load_image(image)
        event.acceptProposedAction()

    def load_image(self, image):
        if image:
            self.clear_asset()

            if self.stretch:
                self.setPixmap(QPixmap.fromImage(image.scaled(self.size())))
            else:
                self.setPixmap(QPixmap.fromImage(image.scaledToHeight(self.size().height())))
            self.monitor.showImage(image, self.stretch)

    def load_image_from_url(self, dropped_url: str):
        """
        Asynchronously fetches graphics from an external web URL stream.
        Guarantees zero UI stuttering or event delays on the main loop thread.
        """
        url = QUrl(dropped_url)
        request = QNetworkRequest(url)

        # Fire request asynchronously and continue running the application immediately
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self._on_network_reply_finished(reply, url))

    def _on_network_reply_finished(self, reply, url):
        """Processes downloaded image payloads safely off the active interface track."""
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                image_data = reply.readAll()
                pixmap = QPixmap()

                if pixmap.loadFromData(image_data):
                    self.clear_asset()
                    if self.stretch:
                        self.setPixmap(pixmap.scaled(self.size()))
                    else:
                        self.setPixmap(pixmap.scaledToHeight(self.size().height()))

                    self.monitor.dropImage(pixmap, self.stretch)
                else:
                    logger.warning(f"Failed to parse downloaded image bytes from URL: {url.toDisplayString()}")
            else:
                logger.warning(f"Error downloading network image asset: {reply.errorString()}")
        finally:
            reply.deleteLater()

    @Slot()
    def blackout(self):
        self.clear_asset()
        self.setStyleSheet("background:black; color:black")
        self.monitor.blackout()

    @Slot()
    def paste_image(self):
        pixmap = QGuiApplication.clipboard().pixmap()
        if pixmap is not None:
            self.clear_asset()

            if self.stretch:
                self.setPixmap(pixmap.scaled(self.size()))
            else:
                self.setPixmap(pixmap.scaledToHeight(self.size().height()))

            self.monitor.pasteImage(self.stretch)

    @Slot(int)
    def previewStretch(self, stretchState):
        # PySide6 checkboxes return state flags rather than pure booleans
        self.stretch = (stretchState == Qt.CheckState.Checked or stretchState == True)

    def set_preview_movie(self, file_name):
        """
        Routes external, framework-managed animations safely through our
        reusable component container window.
        """
        # Flush our active background loops and text tracking caches completely
        self.clear_asset()

        # Safely reuse the single, long-lived internal movie container allocated by SmartOverlayLabel
        self._reusable_movie.setFileName(file_name)
        if not self._reusable_movie.isValid():
            logger.error(f"Failed to load framework animation sequence {file_name}. Error: {self._reusable_movie.errorString()}")
            return False

        self._reusable_movie.setScaledSize(self.size())
        self.setMovie(self._reusable_movie)
        self._reusable_movie.start()
        return True
