import logging

from PySide6.QtCore import Slot, Qt, QFileInfo, QUrl, QSize, QRect, QBuffer, QIODevice, QByteArray
from PySide6.QtGui import QFont, QColor, QMovie, QPixmap, QPainter, QDragEnterEvent, QDropEvent, QGuiApplication, QFontMetrics, QImageReader, QImage, QPalette
from PySide6.QtWidgets import QLabel
from PySide6.QtNetwork import QNetworkRequest, QNetworkReply
import utilities

# Import our text-overlay rendering engine class

logger = logging.getLogger(__name__)

# A custom QLabel that handles either a running animated background or a static background image, overlaying dynamic text dynamically
# It manages the distribution oh behaviors for the features that use it. It provides a feature by feature interface so
# the implementation can be abstrted and the parameters needing to be orchestrated for a given effect and maintained in a cosistent state.
# It is responsingle for managing it's internal support for movie playing and scaling, especially cleaning up when required to display a new
# feature's visuals
class SmartOverlayLabel(QLabel):
    def __init__(self, parent=None, stretch:bool=True, single_loop:bool = False):
        super().__init__(parent)
        self.stretch = stretch

        # Each of these variable should there value passed in or asserted at the start of each method
        self.stretch = True                     # Most features will want to stretch what is being view to fit inside the full area
        self.team_text = ""                     # Used only for the roster feature to hold the role of the player
        self.overlay_text = ""                  # Used for features needing a single line of overlay text but also a player name
        self.overlay_font = QFont()             # Font to be used
        self.scale = 100.0                      # Scale to be applied to the font
        self.background_color, self.overlay_color = QColor(Qt.GlobalColor.black), QColor(Qt.GlobalColor.black)

        self.is_player_mode = False             # Used to branch rendering to use both the team and player name
        self.background_file = ""               # location of the background media
        self.movie = None                       # Instantiated dynamically to allow full garbage collection
        self._single_loop = single_loop         # Enables an additional event handler to stop the movie after one run
        self._current_buffer = None             # Used for animated content from a drag and drop

        # Force background palette to solid black at initialization
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.black)

        self.setPalette(palette)
        self.setAutoFillBackground(True) # Ensures Qt paints the dark palette background before paintEvent

    def _get_target_rect(self, source_size: QSize) -> QRect:
        """Calculates perfectly centered or stretched destination bounds."""
        if self.stretch or source_size.isEmpty() or not source_size.isValid():
            return self.rect()

        scaled_size = source_size.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio
        )
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2
        return QRect(x, y, scaled_size.width(), scaled_size.height())

    def _get_aspect_ratio_mode(self) -> Qt.AspectRatioMode:
            return (
                Qt.AspectRatioMode.IgnoreAspectRatio
                if self.stretch
                else Qt.AspectRatioMode.KeepAspectRatio
            )

    # -------------------------------------------------------------------------
    # Public Setup Methods (Unifies asset loading & overlay text setup)
    # -------------------------------------------------------------------------
    def set_stretch(self, enable: bool):
        """Updates scaling state and triggers immediate recalculation."""
        if self.stretch == enable:
            return

        self.stretch = enable

        # Instantly update active movie bounds if running
        if self.movie and self.movie.isValid():
            self.movie.setScaledSize(self._calculate_movie_size())

        # Trigger a paintEvent to recalculate static images
        self.update()

    # Clear the display
    def blackout(self):
        self._clear_asset()
        self.update()

    # Load text with a colored background
    def set_plain_text(
        self,
        text: str,
        font: QFont = None,
        background_color: QColor = None,
    ):
        self._clear_asset()

        """Renders plain/multiline text with optional background asset and styling."""
        self.is_player_mode = False
        self.overlay_text = text.strip() if text else ""

        if font:
            self.overlay_font = QFont(font)

        if background_color and background_color.isValid():
            self.background_color =  QColor(background_color)
            self.overlay_color = utilities.team_font(background_color)

        self.update()

    # Load a background image
    def set_background(self, file_name: str):
        self._clear_asset()
        self._set_background_asset(file_name)
        self.update()

    # Set the background to an image, stretching if needed
    def set_background_image(self, image: QImage):
        self._clear_asset()
        if image.isNull():
            logger.warning("Smart Overlay Set Background: No Background")
            return

        # Scaling and Display
        if self.stretch:
            # Stretch to fill the label
            scaled_pixmap = QPixmap.fromImage(image.scaled(self.size(),
                                                              Qt.IgnoreAspectRatio,
                                                              Qt.SmoothTransformation))
        else:
            # Scale maintaining aspect ratio
            scaled_pixmap = QPixmap.fromImage(image.scaled(self.size(),
                                                              Qt.KeepAspectRatio,
                                                              Qt.SmoothTransformation))

        self.setPixmap(scaled_pixmap)

        self.update()

    # Set the background to an image, stretching if needed
    def set_background_pixmap(self, pixmap: QPixmap):
        self._clear_asset()
        if pixmap.isNull():
            logger.warning("Smart Overlay set to pixmap: No Background")
            return

        # Scaling and Display
        if pixmap != None:
            if self.stretch:
                # Stretch to fill
                self.setPixmap(pixmap.scaled(self.size(),
                                Qt.IgnoreAspectRatio,
                                Qt.SmoothTransformation))
            else:
                self.setPixmap(pixmap.scaled(self.size(),
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation))

        self.update()

    # The game feature needs the background stretched by default
    def set_text_overlay(
        self,
        background_path: str,
        overlay_text: str,
        font: QFont,
        scale: float,
        color: QColor = QColor(Qt.GlobalColor.white),
    ):
        self._clear_asset()

        # Standard single-line game title display mode.
        self.stretch = True
        self.is_player_mode = False
        self.overlay_text = overlay_text.strip() if overlay_text else ""
        self.overlay_font = QFont(font)
        self.scale = float(scale)
        self.overlay_color = QColor(color)

        self._set_background_asset(background_path)
        self.update()

    # The game feature needs the background stretched by default and the player mode of overlay
    def set_player_overlay(
        self,
        background_path: str,
        player_name: str,
        team_name: str,
        font: QFont,
        scale: float,
        color: QColor = QColor(Qt.GlobalColor.white),
    ):
        self._clear_asset()

        # Roster mode for displaying teams and players (with '/' splitting)
        self.stretch = True
        self.is_player_mode = True
        self.overlay_text = player_name.strip() if player_name else ""
        self.team_text = team_name.strip() if team_name else ""
        self.overlay_font = QFont(font)
        self.scale = float(scale)
        self.overlay_color = QColor(color)

        self._set_background_asset(background_path)
        self.update()

    # Loads and plays animated GIF/WEBP binary stream from memory.
    def set_animated_buffer(self, raw_data: QByteArray):
        self._clear_asset()

        # Store buffer reference on instance to prevent GC
        self._current_buffer = QBuffer(self)
        self._current_buffer.setData(raw_data)
        self._current_buffer.open(QIODevice.OpenModeFlag.ReadOnly)

        self.movie = QMovie(self._current_buffer, parent=self)
        if not self.movie.isValid():
            self._clear_asset()
            return

        # Force initial frame decode and connect repaints
        self.movie.jumpToFrame(0)
        self.movie.frameChanged.connect(self._trigger_movie_repaint)

        # Calculate initial scale and play
        self.movie.setScaledSize(self._calculate_movie_size())
        self.setMovie(self.movie)
        self.movie.start()

    # Internal function that load an image or movie from a file without altering the text
    def _set_background_asset(self, file_name: str):
        if not file_name or not QFileInfo.exists(file_name):
            self._clear_asset()
            logger.warning(f"Smart Overlay: Missing Asset {file_name}.")
            return

        if self.background_file == file_name:
            return

        self.background_file = file_name
        suffix = QFileInfo(file_name).suffix().lower()

        # Clean up existing movie state
        if self.movie is not None:
            self.movie.stop()
            try:
                self.movie.frameChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.movie.deleteLater()
            self.movie = None

        # Check if the format could be animated
        is_animated = False
        if bytes(suffix, "ascii") in QMovie.supportedFormats():
            temp_movie = QMovie(file_name, parent=self)
            if temp_movie.isValid():
                frame_count = temp_movie.frameCount()
                # If frameCount is 1, it's a static image (e.g., static WebP)
                if frame_count > 1:
                    is_animated = True
                elif frame_count == 0:
                    # Some animated WEBP/GIF files report 0 frames initially;
                    # check if a second frame actually exists.
                    temp_movie.jumpToFrame(0)
                    is_animated = temp_movie.jumpToNextFrame()

                if is_animated:
                    self.movie = temp_movie
                    self.movie.jumpToFrame(0)
                    self.movie.frameChanged.connect(self._trigger_movie_repaint)
                    if self._single_loop:
                        self.movie.frameChanged.connect(self._handle_single_loop)
                    self.movie.setScaledSize(self._calculate_movie_size())
                    self.movie.setSpeed(100)
                    self.movie.start()
                else:
                    temp_movie.deleteLater()

        # Fallback to static QImageReader (handles static WebP, PNG, JPG, etc.)
        if not is_animated:
            reader = QImageReader(self.background_file)
            reader.setAutoTransform(True)
            new_image = reader.read()

            if new_image.isNull():
                logger.warning(f"Smart Overlay: Failed to read image {self.background_file}.")
                self._clear_asset()
                return

            target_size = self.size()
            aspect_mode = Qt.AspectRatioMode.IgnoreAspectRatio if self.stretch else Qt.AspectRatioMode.KeepAspectRatio

            scaled_pixmap = QPixmap.fromImage(
                new_image.scaled(target_size, aspect_mode, Qt.TransformationMode.SmoothTransformation)
            )
            self.setPixmap(scaled_pixmap)

    # Clears the display and releases all video/image memory buffers explicitly.
    def _clear_asset(self):
        if self.movie is not None:
            self.movie.stop()
            try:
                self.movie.frameChanged.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.movie.deleteLater()
            self.movie = None

        # Explicitly clear internal C++ pixmap allocations
        self.clear()

        self.background_file = ""
        self.team_text = ""
        self.overlay_text = ""
        self.is_player_mode = False
        self.background_color = QColor(Qt.GlobalColor.black)
        self.overlay_color = QColor(Qt.GlobalColor.black)
        self.scale = 100.0

        # ... stop movie/clear pixmaps ...
        if getattr(self, "_current_buffer", None) is not None:
            self._current_buffer.close()
            self._current_buffer.deleteLater()
            self._current_buffer = None

    # Fits font size so text fits cleanly inside target_rect across BOTH
    # width and height constraints with horizontal safety margins.
    def _fit_font_to_rect(
        self, text: str, base_font: QFont, target_rect: QRect, scale_pct: float = 100.0
    ) -> QFont:
        if not text or target_rect.isEmpty():
            return base_font

        font = QFont(base_font)
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 110)

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return base_font

        scale_factor = scale_pct / 100.0
        max_allowed_width = target_rect.width() * scale_factor
        max_allowed_height = target_rect.height() * scale_factor

        line_count = len(lines)

        # 1. Initial rough estimate using total allowed height divided by line count
        # Base estimate must use lineSpacing ratio (roughly 1.2x pixel size for most fonts)
        estimated_line_height = max_allowed_height / line_count
        pixel_size = max(8, int(estimated_line_height * 0.75))
        font.setPixelSize(pixel_size)

        fm = QFontMetrics(font)

        # 2. Measure actual total text bounding using Qt's real lineSpacing()
        longest_line_width = max(fm.horizontalAdvance(line) for line in lines)
        total_text_height = fm.lineSpacing() * line_count

        # 3. Calculate restricting ratio
        width_ratio = (
            max_allowed_width / longest_line_width if longest_line_width > 0 else 1.0
        )
        height_ratio = (
            max_allowed_height / total_text_height if total_text_height > 0 else 1.0
        )

        limiting_ratio = min(width_ratio, height_ratio)
        adjusted_pixel_size = max(8, int(pixel_size * limiting_ratio))
        font.setPixelSize(adjusted_pixel_size)

        # 4. Final verification pass: Step down pixel size if lineSpacing still overflows
        fm = QFontMetrics(font)
        while adjusted_pixel_size > 8:
            current_height = fm.lineSpacing() * line_count
            current_width = max(fm.horizontalAdvance(line) for line in lines)

            if current_height <= max_allowed_height and current_width <= max_allowed_width:
                break

            adjusted_pixel_size -= 1
            font.setPixelSize(adjusted_pixel_size)
            fm = QFontMetrics(font)

        return font

    # -------------------------------------------------------------------------
    # Qt Event Handlers
    # -------------------------------------------------------------------------
    @Slot(int)
    def _trigger_movie_repaint(self, frame_number):
        self.update()

    @Slot(int)
    def _handle_single_loop(self, frame_number: int):
        total_frames = self.movie.frameCount()

        # If valid total frame count and we hit or passed the last frame
        if total_frames > 0 and frame_number >= total_frames - 1:
            self.movie.setPaused(True)  # Freeze on the final frame
            try:
                # Disconnect only this handler so repaints can still happen if resized
                self.movie.frameChanged.disconnect(self._handle_single_loop)
            except (RuntimeError, TypeError):
                pass

    def _calculate_movie_size(self) -> QSize:
            target_size = self.size()
            if target_size.isEmpty() or target_size.width() <= 1:
                return QSize()

            if self.stretch:  # Unified variable
                return target_size

            orig_size = self.movie.currentPixmap().size()
            if not orig_size.isValid() or orig_size.isEmpty():
                self.movie.jumpToFrame(0)
                orig_size = self.movie.currentPixmap().size()

            if orig_size.isValid() and not orig_size.isEmpty():
                return orig_size.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio)

            return target_size

    def setMovie(self, movie: QMovie) -> None:
        if movie:
            self.setScaledContents(False)
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            movie.setScaledSize(self._calculate_movie_size())
        super().setMovie(movie)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        # 1. Handle active animation streams (file-based or in-memory buffer)
        if hasattr(self, "movie") and self.movie and self.movie.isValid():
            self.movie.setScaledSize(self._calculate_movie_size())
            return

        # 2. Handle static background files
        if getattr(self, "background_file", None):
            pixmap = QPixmap(self.background_file)
            if not pixmap.isNull():
                self.setPixmap(
                    pixmap.scaled(
                        self.size(),
                        self._get_aspect_ratio_mode(),
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

    def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            rect = self.rect()
            if rect.isEmpty():
                painter.end()
                return

            # 1. Background Fill
            bg_color = (
                self.background_color
                if isinstance(self.background_color, QColor)
                else QColor(self.background_color)
            )
            if bg_color.isValid():
                painter.fillRect(rect, bg_color)

            # 2. Render Media
            if self.movie and self.movie.state() != QMovie.MovieState.NotRunning:
                # Draw directly from currentPixmap to avoid heap churn
                current_pix = self.movie.currentPixmap()
                if not current_pix.isNull():
                    target_rect = self._get_target_rect(current_pix.size())
                    painter.drawPixmap(target_rect, current_pix)

            elif self.pixmap() and not self.pixmap().isNull():
                target_rect = self._get_target_rect(self.pixmap().size())
                painter.drawPixmap(target_rect, self.pixmap())

            # 3. Overlay Text
            h_margin = int(self.rect().width() * 0.03)
            widget_rect = self.rect().adjusted(h_margin, 0, -h_margin, 0)

            if self.is_player_mode:
                if self.team_text:
                    team_rect = widget_rect.adjusted(
                        0,
                        int(widget_rect.height() * 0.05),
                        0,
                        -int(widget_rect.height() * 0.65),
                    )
                    fitted_team_font = self._fit_font_to_rect(
                        self.team_text, self.overlay_font, team_rect, scale_pct=60.0
                    )
                    fitted_team_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 110)
                    painter.setFont(fitted_team_font)
                    painter.setPen(self.overlay_color)
                    painter.drawText(team_rect, Qt.AlignmentFlag.AlignCenter, self.team_text)

                if self.overlay_text:
                    player_rect = widget_rect.adjusted(
                        0,
                        int(widget_rect.height() * 0.30),
                        0,
                        -int(widget_rect.height() * 0.05),
                    )
                    display_lines = [line.strip() for line in self.overlay_text.split("/") if line.strip()]
                    clean_multiline_text = "\n".join(display_lines)

                    fitted_player_font = self._fit_font_to_rect(
                        clean_multiline_text, self.overlay_font, player_rect, scale_pct=self.scale
                    )
                    painter.setFont(fitted_player_font)
                    painter.setPen(self.overlay_color)
                    painter.drawText(player_rect, Qt.AlignmentFlag.AlignCenter, clean_multiline_text)
            else:
                if self.overlay_text:
                    active_font = self.overlay_font if self.overlay_font.family() else self.font()
                    active_color = (
                        self.overlay_color
                        if self.overlay_color.isValid()
                        else self.palette().text().color()
                    )

                    fitted_font = self._fit_font_to_rect(
                        self.overlay_text, active_font, widget_rect, scale_pct=self.scale
                    )
                    painter.setFont(fitted_font)
                    painter.setPen(active_color)
                    painter.drawText(widget_rect, Qt.AlignmentFlag.AlignCenter, self.overlay_text)

            painter.end()

# Manages the display monitors' dashboard previews. Inherits directly
# from SmartOverlayLabel to share the permanent animation engine.
class MonitorPreview(SmartOverlayLabel):
    def __init__(self, original_label, layout, monitor, stretch, shared_network_manager, parent=None):
        # Initialize the single permanent QMovie container inside SmartOverlayLabel
        super().__init__(parent=parent, stretch=stretch, single_loop = True)

        self.setAcceptDrops(True)
        self.network_manager = shared_network_manager
        self.monitor = monitor
        self.monitor.set_stretch(stretch)

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
        self._clear_asset()

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
                url = urls[0]
                if url.isLocalFile():
                    # Handle local file paths (GIF, WEBP, PNG, JPG)
                    file_path = url.toLocalFile()
                    self.load_media_from_file(file_path)
                else:
                    # Handle remote URLs
                    self.load_image_from_url(url.toString())
        elif mime_data.hasImage():
            image = mime_data.imageData()
            self.load_image(image)

        event.acceptProposedAction()

    def load_media_from_file(self, file_path: str):
        """Routes local file path to the overlay engine and synchs the monitor."""
        if not QFileInfo.exists(file_path):
            return

        # Load locally inside preview (SmartOverlayLabel determines QMovie vs QPixmap)
        self.set_background(file_path)

        # Notify external monitor display engine
        if hasattr(self.monitor, "set_background"):
            self.monitor.set_background(file_path)

    def load_image_from_url(self, dropped_url: str):
        url = QUrl(dropped_url)
        request = QNetworkRequest(url)

        reply = self.network_manager.get(request)
        reply.finished.connect(
            Slot()(lambda r=reply, u=url: self._on_network_reply_finished(r, u))
        )

    def _on_network_reply_finished(self, reply, url):
            try:
                if reply.error() == QNetworkReply.NetworkError.NoError:
                    raw_data = reply.readAll()

                    # Check if buffer is an animated format (GIF/WEBP)
                    buffer = QBuffer(self)
                    buffer.setData(raw_data)
                    buffer.open(QIODevice.OpenModeFlag.ReadOnly)

                    movie = QMovie(buffer, parent=self)
                    if movie.isValid() and movie.frameCount() > 1:
                        buffer.close()

                        # Use set_animated_buffer locally to handle aspect scaling and playback
                        self.set_animated_buffer(raw_data)

                        if hasattr(self.monitor, "show_animated_buffer"):
                            self.monitor.show_animated_buffer(raw_data)
                    else:
                        # Static frame payload handling
                        buffer.close()
                        pixmap = QPixmap()
                        if pixmap.loadFromData(raw_data):
                            self.set_background_pixmap(pixmap)
                            if hasattr(self.monitor, "show_pixmap"):
                                self.monitor.show_pixmap(pixmap)
                else:
                    logger.warning(f"Error downloading image: {reply.errorString()}")
            finally:
                reply.deleteLater()

    @Slot()
    def blackout(self):
        super().blackout()
        self.monitor.blackout()

    @Slot()
    def paste_image(self):
        pixmap = QGuiApplication.clipboard().pixmap()
        if pixmap is not None:
            self.set_background_pixmap(pixmap)

            self.monitor.show_pixmap(pixmap)

    # Remember the monitor stretch status
    @Slot(Qt.CheckState)
    def fit_to_width(self, check_state):
        if check_state == Qt.Checked:
            self.stretch = True
            self.monitor.set_stretch(True)
        else:
            self.stretch = False
            self.monitor.set_stretch(False)
