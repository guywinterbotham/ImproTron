import json
import logging
from PySide6.QtCore import QObject, QIODevice, Slot, Signal, QCoreApplication
from PySide6.QtNetwork import QTcpSocket

logger = logging.getLogger(__name__)

# Constants for JSON keys
BUTTON_ACTION_ID = "improtron.button.action"
MEDIA_ACTION_ID = "improtron.media.action"
SPINBOX_ACTION_ID = "improtron.spinbox.action"
SOUND_ACTION_ID = "improtron.sound.action"

class TouchPortal(QObject):
    buttonAction = Signal(str)    # Custom signal with a string argument of a touch portal button matching the UI ID
    spinBoxAction = Signal(str, float)   # Custom signal with a string UI ID of a Spin Box and the delta. 0 = reset to zero
    mediaAction = Signal(str, str) # Custom signal with string arguments for the file and target monitor
    soundAction = Signal(str)     # Custom signal with a string argument for a sound file

    def __init__(self, host='127.0.0.1', port=12136):
        super().__init__()
        self.host = host
        self.port = port
        self.socket = QTcpSocket(self)
        self.socket.readyRead.connect(self.receive_message)
        self.socket.connected.connect(self.on_connected)
        self.socket.errorOccurred.connect(self.on_error)
        self.socket.disconnected.connect(self.on_disconnected)

        # Graceful shutdown
        QCoreApplication.instance().aboutToQuit.connect(self.disconnectTouchPortal)

    def connectTouchPortal(self):
        self.socket.connectToHost(self.host, self.port, QIODevice.ReadWrite)

    def on_connected(self):
        logger.info(f"Connected to Touch Portal at {self.host}:{self.port}")
        self.pair()

    def on_error(self, socket_error):
        logger.warn(f"Touch Portal enabled but failed to connect. Connection error: {socket_error}")

    def on_disconnected(self):
        logger.info("Disconnected from Touch Portal.")

    def disconnectTouchPortal(self):
        if self.socket.state() == QTcpSocket.ConnectedState:
            self.socket.disconnectFromHost()
            logger.info("Touch Portal disconnected.")

    def send_message(self, message):
        if self.socket.state() == QTcpSocket.ConnectedState:
            try:
                self.socket.write((json.dumps(message) + '\n').encode())
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
        else:
            logger.info("Not connected to Touch Portal")

    @Slot()
    def receive_message(self):
        while self.socket.bytesAvailable():
            data = self.socket.readAll()
            try:
                json_obj = json.loads(data.data().decode())
                self.handle_message(json_obj)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON message: {e}")

    def handle_message(self, json_obj):
        message_type = json_obj.get("type")

        if message_type == "action":
            action_id = json_obj.get("actionId")
            action_dispatch = {
                BUTTON_ACTION_ID: self.handle_button_action,
                MEDIA_ACTION_ID: self.handle_media_action,
                SPINBOX_ACTION_ID: self.handle_spinbox_action,
                SOUND_ACTION_ID: self.handle_sound_action,
            }

            action_handler = action_dispatch.get(action_id)
            if action_handler:
                action_handler(json_obj.get("data", []))
            else:
                logger.info(f"Unknown Action ID: {action_id}")

        elif message_type == "broadcast":
            logger.debug(f"Broadcast message received: {json_obj}")

        elif message_type == "info":
            logger.debug(f"Info message received: {json_obj}")

        else:
            logger.warning(f"Unhandled inbound message: {json_obj}")

    def handle_button_action(self, data):
        button_id = data[0].get("value", "")
        self.buttonAction.emit(button_id)

    def handle_media_action(self, data):
        file, monitor = "", ""
        for item in data:
            if item["id"] == "improtron.media.file.data":
                file = item["value"]
            elif item["id"] == "improtron.media.monitor.data":
                monitor = item["value"]
        self.mediaAction.emit(file, monitor)

    def handle_spinbox_action(self, data):
        button_id, change = "", 0.0
        for item in data:
            if item["id"] == "improtron.spinbox.id":
                button_id = item["value"]
            elif item["id"] == "improtron.spinbox.changevalue":
                change = float(item["value"])
        self.spinBoxAction.emit(button_id, change)

    def handle_sound_action(self, data):
        file = data[0].get("value", "")
        self.soundAction.emit(file)

    def close(self):
        logger.info("Disconnected from Touch Portal.")
        self.socket.disconnectFromHost()

    def pair(self):
        pair_message = {
            "type": "pair",
            "id": "improtron"
        }
        self.send_message(pair_message)
