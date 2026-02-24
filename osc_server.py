import logging
import struct
from PySide6.QtCore import QObject, Signal, Slot, QCoreApplication
from PySide6.QtNetwork import QUdpSocket, QHostAddress

logger = logging.getLogger(__name__)

# Common OSC routes for integration with Improtron
OSC_SOUND_PLAY = "/sound/play"
OSC_SOUND_SEEK = "/sound/seek"
OSC_SOUND_STOP = "/sound/stop"
OSC_SOUND_STINGER = "/sound/stinger"
OSC_SOUND_FADE = "/sound/fade"
OSC_SOUND_PLAYLIST = "/sound/playlist"
OSC_MEDIA_SHOW = "/media/show"
OSC_SPINBOX_CHANGE = "/spinbox/change"
OSC_BUTTON_PRESS = "/button/press"
OSC_SFX_PLAY = "/soundfx/play"
OSC_SFX_STOP = "/soundfx/stop"

class OSCServer(QObject):
    buttonAction = Signal(str)
    spinBoxAction = Signal(str, float)
    mediaAction = Signal(str, str)
    soundAction = Signal(str)
    playlistAction = Signal(str)
    stingerAction = Signal(str)
    sfxPlayAction = Signal(str)
    stopAllSFXSignal = Signal()
    fadeAction = Signal(float)
    seekAction = Signal(float, str)

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

        return address.strip(), args

    # Dispatch OSC message to the correct signal handler
    def _dispatch_message(self, address: str, args: list):
        if address == OSC_SOUND_PLAY:
            if args:
                self.soundAction.emit(str(args[0]))
            else:
                logger.warning(f"OSCServer: Missing sound tag list in {args}")
        elif address == OSC_SOUND_PLAYLIST:
            if args:
                self.playlistAction.emit(str(args[0]))
            else:
                logger.warning(f"OSCServer: Missing playlist in {args}")
        elif address == OSC_SOUND_STINGER:
            if args:
                self.stingerAction.emit(str(args[0]))
            else:
                logger.warning(f"OSCServer: Missing stinger tag list in {args}")
        elif address == OSC_SOUND_SEEK:
            # Check for at least one arg (seek time) and a second arg (tag list)
            if args and len(args) >= 2:
                arg_value = args[0] # Get the first argument (potential seek time)

                try:
                    # Attempt to convert the first value to a float
                    float_value = float(arg_value)

                    # Convert the rest of the arguments (args[1:]) into a space-delimited string
                    tag_string = " ".join(str(arg) for arg in args[1:])

                    # Emit the seek time (float) and the tag string
                    # NOTE: You MUST define self.seekAction = Signal(float, str)
                    self.seekAction.emit(float_value, tag_string)

                    logger.debug(f"OSC Seek Command: Seek Time={float_value}s, Tags='{tag_string}'")

                except (ValueError, TypeError):
                    logger.error(f"OSCServer: SEEK Command's first argument must be a float (seconds), received '{arg_value}'.")
            else:
                logger.warning(f"OSCServer: Missing seek parameter and/or tags in {args}. Requires float (seconds) and at least one tag.")
        elif address == OSC_SOUND_FADE:
            if args and args[0] is not None:

                arg_value = args[0] # Get the first argument

                # Use try/except to safely attempt conversion
                try:
                    # Attempt to convert the value to a float
                    float_value = float(arg_value)

                    # If successful, emit a signal that expects a float
                    self.fadeAction.emit(float_value)

                except (ValueError, TypeError):
                    logger.error(f"OSCServer: Fade Command should be a floating numer of seconds {args}")

            else:
                logger.warning(f"OSCServer: Missing fade parameter in {args}")
        elif address == OSC_SOUND_STOP:
            self.soundAction.emit("")  # empty string = stop all
        elif address == OSC_MEDIA_SHOW:
            self.handle_media_action(args)
        elif address == OSC_SPINBOX_CHANGE:
            if len(args) >= 2:
                self.spinBoxAction.emit(str(args[0]), float(args[1]))
            else:
                logger.warning(f"OSCServer: Invalid spinbox args {args}")
        elif address == OSC_BUTTON_PRESS:
            button_id = str(args[0]) if args else ""
            self.buttonAction.emit(button_id)
        elif address == OSC_SFX_PLAY:
            if args:
                self.sfxPlayAction.emit(str(args[0]))
            else:
                logger.warning(f"OSCServer: Missing sound fx tag list in {args}")
        elif address == OSC_SFX_STOP:
            self.sfxPlayAction.emit("")  # empty string = stop all sound fx
        else:
            logger.info(f"OSCServer: Unhandled OSC address {address} with args {args}")

    # Handles OSC messages for media playback. Expects args[0] to be the monitor name.
    # The remaining args are concatenated into a space-delimited string of search tags.
    def handle_media_action(self, args):
        # Ensure there is at least one argument (the monitor)
        if not args:
            self.logger.warning("OSCServer: Missing monitor argument for media action.")
            return

        # Extract the monitor name from args[0]
        # Use str() to ensure it's a string, regardless of the OSC type tag.
        monitor = str(args[0]).lower()

        # Extract the remaining arguments (args[1] onwards)
        tag_components = [str(arg) for arg in args[1:]]

        # Concatenate the components into a single, space-delimited file string
        # If there are no components, 'file' will be an empty string.
        tags = " ".join(tag_components)

        # Emit the signal with the new order (monitor,file)
        self.mediaAction.emit(monitor, tags)
