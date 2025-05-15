import logging
import struct

from PySide6.QtNetwork import QUdpSocket, QHostAddress
from PySide6.QtCore import QByteArray, QObject

logger = logging.getLogger(__name__)

class LightingFeature(QObject):
    def __init__(self, ui, settings, host: str, port: int):
        self.host = QHostAddress(host)
        self.port = port
        self.socket = QUdpSocket()

        self.ui = ui
        self._settings = settings

        self.connect_slots()

    def connect_slots(self):
        # Connect text feature components
        self.ui.oscMessagePB.clicked.connect(self.send_osc_message)

    def send_osc_message(self):
        # Sends an OSC message
        address = self.ui.oscMessageLE.text()
        values = []
        values.append(self.ui.oscValueSP.value())
        message = self._build_osc_message(address, values)
        self.socket.writeDatagram(message, self.host, self.port)
        logger.warning(f"Sent {values} to {address}")

    def _build_osc_message(self, address: str, values: list) -> QByteArray:
        # Builds an OSC message as a QByteArray
        data = QByteArray()
        data.append(address.encode('utf-8'))
        data.append(b'\0' * (4 - len(address) % 4))  # Pad to 4-byte boundary

        # Add type tag string
        type_tags = ',' + ''.join('f' if isinstance(v, float) else 'i' for v in values)
        data.append(type_tags.encode('utf-8'))
        data.append(b'\0' * (4 - len(type_tags) % 4))  # Pad to 4-byte boundary

        # Add arguments
        for value in values:
            if isinstance(value, int):
                data.append(value.to_bytes(4, byteorder='big', signed=True))
            elif isinstance(value, float):
                data.append(QByteArray.fromRawData(bytearray(struct.pack('>f', value))))

            # Debug print statement for Hex Dump
            self._print_hex_dump(data.data())

            return data

    def _print_hex_dump(self, raw_data: bytes):
        """Prints the raw data in a hex dump format."""
        logger.info("Hex Dump of OSC Message:")
        for i in range(0, len(raw_data), 16):
            chunk = raw_data[i:i+16]
            hex_chunk = ' '.join(f"{byte:02x}" for byte in chunk)
            ascii_chunk = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in chunk)
            logger.info(f"{i:08x}  {hex_chunk:<48}  {ascii_chunk}")
