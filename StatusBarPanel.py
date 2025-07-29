from PySide6.QtWidgets import QStatusBar, QLabel, QWidget, QProgressBar, QHBoxLayout

class StatusBarPanel(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status_left = QLabel('Ready')
        self.status_center = QLabel('')
        self.status_progress = QProgressBar()
        self.status_progress.setMinimum(0)
        self.status_progress.setMaximum(100)
        self.status_progress.setValue(0)
        self.status_progress.setTextVisible(True)
        outline_style = "border: 1px solid #444; padding: 2px; border-radius: 3px;"
        self.status_left.setStyleSheet(outline_style)
        self.status_center.setStyleSheet(outline_style)
        self.status_progress.setStyleSheet(outline_style)
        self.setStyleSheet("QStatusBar { border: 1px solid #222; }")
        status_container = QWidget()
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(0)
        status_layout.addWidget(self.status_left, stretch=70)
        status_layout.addWidget(self.status_center, stretch=15)
        status_layout.addWidget(self.status_progress, stretch=15)
        status_container.setLayout(status_layout)
        self.addPermanentWidget(status_container, 1)
