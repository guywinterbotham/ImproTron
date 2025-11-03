import logging
import struct
from PySide6.QtCore import QObject, Signal, Slot, QCoreApplication
from PySide6.QtNetwork import QUdpSocket, QHostAddress

logger = logging.getLogger(__name__)

# Common OSC routes for integration with Improtron
OSC_SOUND_ACTION = "/sound/play"
OSC_STOP_ALL_ACTION = "/sound/stop_all"
OSC_MEDIA_ACTION = "/media/play"
OSC_SPINBOX_ACTION = "/spinbox/change"
OSC_BUTTON_ACTION = "/button/press"


class OSCServer(QObject):
    """A Qt-based OSC server with Touch Portal-style integration."""
    buttonAction = Signal(str)
    spinBoxAction = Signal(str, float)
    mediaAction = Signal(str, str)
    soundAction = Signal(str)

    def __init__(self, listen_host="127.0.0.1", listen_port=9000, parent=None):
        super().__init__(parent)
        self.listen_host = QHostAddress(listen_host)
        self.listen_port = listen_port
        self.socket = QUdpSocket(self)

        # Connect signals
        self.socket.readyRead.connect(self._on_ready_read)
        QCoreApplication.instance().aboutToQuit.connect(self.disconnectOSCServer)

        self._bind_socket()

    # ----------------------------------------------------------------------
    # Connection management
    # ----------------------------------------------------------------------
    def _bind_socket(self):
        if not self.socket.bind(self.listen_host, self.listen_port):
            logger.error(f"OSCServer: Failed to bind on {self.listen_host.toString()}:{self.listen_port}")
        else:
            logger.info(f"OSCServer: Listening for OSC on {self.listen_host.toString()}:{self.listen_port}")

    def disconnectOSCServer(self):
        if self.socket.isValid():
            self.socket.close()
            logger.info("OSCServer disconnected cleanly.")

    # ----------------------------------------------------------------------
    # Data handling
    # ----------------------------------------------------------------------
    @Slot()
    def _on_ready_read(self):
        """Triggered when data is available on the UDP socket."""
        while self.socket.hasPendingDatagrams():
            datagram, host, port = self.socket.readDatagram(self.socket.pendingDatagramSize())
            # --- FIX: Convert QByteArray to Python bytes ---
            data_bytes = bytes(datagram)
            try:
                address, args = self._parse_osc_message(data_bytes)
                self._dispatch_message(address, args)
            except Exception as e:
                logger.warning(f"OSCServer: Failed to parse OSC message from {host.toString()}:{port}: {e}")

    # ----------------------------------------------------------------------
    # Message parsing and routing
    # ----------------------------------------------------------------------
    def _parse_osc_message(self, data: bytes):
        """Parse a single OSC message."""
        # Parse address
        address_end = data.find(b'\0')
        address = data[:address_end].decode('utf-8')
        offset = (address_end + 4) & ~0x03  # 4-byte alignment

        # Parse typetags
        type_start = offset
        type_end = data.find(b'\0', type_start)
        typetags = data[type_start + 1:type_end].decode('utf-8')  # skip leading comma
        offset = (type_end + 4) & ~0x03

        # Parse arguments
        args = []
        for tag in typetags:
            if tag == 'i':
                args.append(struct.unpack('>i', data[offset:offset + 4])[0])
                offset += 4
            elif tag == 'f':
                args.append(struct.unpack('>f', data[offset:offset + 4])[0])
                offset += 4
            elif tag == 's':
                end = data.find(b'\0', offset)
                val = data[offset:end].decode('utf-8')
                args.append(val)
                offset = (end + 4) & ~0x03
            else:
                logger.warning(f"OSCServer: Unknown typetag '{tag}' in message {address}")

        return address, args

    def _dispatch_message(self, address: str, args: list):
        """Dispatch OSC message to the correct signal handler."""
        if address == OSC_SOUND_ACTION:
            self.handle_sound_action(args)
        elif address == OSC_STOP_ALL_ACTION:
            self.soundAction.emit("")  # empty string = stop all
        elif address == OSC_MEDIA_ACTION:
            self.handle_media_action(args)
        elif address == OSC_SPINBOX_ACTION:
            self.handle_spinbox_action(args)
        elif address == OSC_BUTTON_ACTION:
            self.handle_button_action(args)
        else:
            logger.info(f"OSCServer: Unhandled OSC address {address} with args {args}")

    # ----------------------------------------------------------------------
    # Handlers (Signal Emitters)
    # ----------------------------------------------------------------------
    def handle_button_action(self, args):
        button_id = str(args[0]) if args else ""
        self.buttonAction.emit(button_id)

    def handle_spinbox_action(self, args):
        if len(args) >= 2:
            self.spinBoxAction.emit(str(args[0]), float(args[1]))
        else:
            logger.warning(f"OSCServer: Invalid spinbox args {args}")

    def handle_media_action(self, args):
        """
        Handles OSC messages for media playback.
        Expects args[0] to be the monitor name.
        The remaining args are concatenated into a space-delimited string (the file path).
        """
        # Ensure there is at least one argument (the monitor)
        if not args:
            self.logger.warning("OSCServer: Missing monitor argument for media action.")
            return

        # 1. Extract the monitor name from args[0]
        # Use str() to ensure it's a string, regardless of the OSC type tag.
        monitor = str(args[0]).lower()

        # 2. Extract the remaining arguments (args[1] onwards)
        tag_components = [str(arg) for arg in args[1:]]

        # 3. Concatenate the components into a single, space-delimited file string
        # If there are no components, 'file' will be an empty string.
        tags = " ".join(tag_components)

        # 4. Emit the signal with the new order (file, monitor)
        self.mediaAction.emit(tags, monitor)

    def handle_sound_action(self, args):
        if args:
            self.soundAction.emit(str(args[0]))
        else:
            logger.warning(f"OSCServer: Missing tag list in {args}")
