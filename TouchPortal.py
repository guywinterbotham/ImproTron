# This Python file uses the following encoding: utf-8
import sys
import json
from PySide6.QtCore import QObject, QIODevice, Slot, Signal
from PySide6.QtNetwork import QTcpSocket

class TouchPortal(QObject):
    buttonAction = Signal(str)    # Custom signal with a string argument of a touch portal button matching the UI ID
    spinBoxAction = Signal(str, int)   # Custom signal with a string UI ID of a Spin Box and the delta. 0 = reset to zero
    mediaAction = Signal(str,str) # Custom signal with a string arguments for the file and target monitor
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

    def connectTouchPortal(self):
        self.socket.connectToHost(self.host, self.port, QIODevice.ReadWrite)

    def on_connected(self):
        print(f"Connected to Touch Portal at {self.host}:{self.port}")
        self.pair()

    def on_error(self, socket_error):
        print(f"Connection error: {socket_error}")

    def on_disconnected(self):
        print("Disconnected from Touch Portal")

    def disconnectTouchPortal(self):
        if self.socket.state() == QTcpSocket.ConnectedState:
            self.close()

    def send_message(self, message):
        if self.socket.state() == QTcpSocket.ConnectedState:
            self.socket.write((json.dumps(message)+'\n').encode())
        else:
            print("Not connected to Touch Portal")

    @Slot()
    def receive_message(self):
        while self.socket.bytesAvailable():
            data = self.socket.readAll()
            # Parse the JSON string into a dictionary
            json_obj = json.loads(data.data().decode())

            # Extract the "value" from the first item in the "data" list and send the signal approiate to the action
            if json_obj["type"] == "action":
                if json_obj["actionId"] == "improtron.button.action":
                    buttonID = json_obj["data"][0]["value"]
                    self.buttonAction.emit(buttonID)
                elif json_obj["actionId"] == "improtron.media.action":
                    file = ""
                    monitor = ""
                    for item in json_obj['data']:
                        if item["id"] == "improtron.media.file.data":
                            file = item["value"]

                        if item["id"] == "improtron.media.monitor.data":
                            monitor = item["value"]
                    self.mediaAction.emit(file, monitor)
                elif json_obj["actionId"] == "improtron.spinbox.action":
                    buttonID = ""
                    change = 0
                    for item in json_obj['data']:
                        if item["id"] == "improtron.spinbox.id":
                            buttonID = item["value"]

                        if item["id"] == "improtron.spinbox.changevalue":
                            change = int(item["value"])
                    self.spinBoxAction.emit(buttonID, change)
                elif json_obj["actionId"] == "improtron.sound.action":
                    file = json_obj["data"][0]["value"]
                    self.soundAction.emit(file)
                else:
                    print(f"Unknown Action: {json_obj}")
            else:
                print(f"Unhandled inbound message: {json_obj}")

    def close(self):
        self.socket.disconnectFromHost()
        print("Connection closed")

    # Touch Panel Message Methods
    def pair(self):
        pair_message = {
        "type":"pair",
        "id":"improtron"
        }
        self.send_message(pair_message)
