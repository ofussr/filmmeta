"""Background Qt jobs with progress and interruption signals."""

from typing import Callable

from PySide6.QtCore import QThread, Signal


class Job(QThread):
    result = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, function: Callable, parent):
        super().__init__(parent)
        self.function = function

    def run(self):
        try:
            self.result.emit(
                self.function(self.progress.emit, self.isInterruptionRequested)
            )
        except Exception as error:
            self.failed.emit(str(error))
