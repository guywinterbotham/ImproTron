from PySide6.QtCore import Slot, QTimer, QTime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLCDNumber

class CountdownTimer(QLCDNumber):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setSegmentStyle(QLCDNumber.Filled)
        self.setDigitCount(8)
        self.setWindowTitle(name)
        self.setFocusProxy(None)

        # Remove the boarder
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        # Countdown Timer
        self.countdownTimer = QTimer()
        self.countdownTimer.timeout.connect(self.countdown)

        self.countdownTime = QTime(0,0,0)
        self.startingTime = QTime(0,0,0)
        self.redTime = QTime(0,0,0)
        self.display("00:00:00")
        self.resetColor()

    def resetColor(self):
        self.setStyleSheet("background:black; color: white")

    def start(self, time, redTime):
        if not self.countdownTimer.isActive():
            self.countdownTime.setHMS(time.hour(), time.minute(), time.second())
            self.startingTime.setHMS(time.hour(), time.minute(), time.second())
            self.redTime.setHMS(redTime.hour(), redTime.minute(), redTime.second())
            self.resetColor()

            self.countdownTimer.start(1000)

    def pause(self):
        if self.countdownTimer.isActive():
            self.countdownTimer.stop()
        else:
            self.countdownTimer.start(1000)

    def reset(self, time, redTime):
        if self.countdownTimer.isActive():
            self.countdownTime.setHMS(time.hour(), time.minute(), time.second())
            self.startingTime.setHMS(time.hour(), time.minute(), time.second())
            self.redTime.setHMS(redTime.hour(), redTime.minute(), redTime.second())
            self.resetColor()

    @Slot()
    def countdown(self):
        self.countdownTime = self.countdownTime.addSecs(-1)
        text = self.countdownTime.toString("hh:mm:ss")

        # Blinking effect
        if (self.countdownTime.second() % 2) == 0:
            text = text.replace(":", " ")

        # Alert time - something is close to happening
        if self.countdownTime <= self.redTime:
            self.setStyleSheet("background:black; color: red")

        # Timeout - when countime rolls over and goes to midnight then
        # it has timed out. However the default comparison logic will see the rolled
        # over time as greater than zero time. SO detect the rollover instead.
        if self.countdownTime > self.startingTime:
            self.countdownTimer.stop()
            return

        self.display(text)

    # Maximize on the screen where the timer was moved to
    def showTimer(self, location, visible = False):
        height = location.height()/4
        location.translate(0,height*3)
        location.setHeight(height)
        self.setGeometry(location)
        self.setVisible(visible)
