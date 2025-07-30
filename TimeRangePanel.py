from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox, QDateTimeEdit
from datetime import datetime, timedelta
from PySide6.QtCore import Qt

class TimeRangePanel(QGroupBox):

    """
    This class provides many different ways to specify a time range that is used to 
    select what data to plot.  The basic methods and associated widgets are:
       * buttons for choosing last hour, day, week or month (most recent period)
       * widgets for choosing a relative time
       * finally, two time pickers for choosing directly start and end times
    All downstream widgets are set if an upstream widget is set; that is, if a user
    clicks the 'last week' button, this updates the relative and direct time widgets
    to cover this time range.   
    """

    def __init__(self, parent=None):
        super().__init__("Time Range", parent)
        self.layout = QVBoxLayout()
        
        # 1. first the most recent period buttons
        # Using most recent label
        self.using_most_recent_label = QLabel("Using most recent period:")
        self.layout.addWidget(self.using_most_recent_label)

        # Quick range buttons
        self.quick_range_layout = QHBoxLayout()
        self.last_hour_btn = QPushButton("Last Hour")
        self.last_day_btn = QPushButton("Last Day")
        self.last_week_btn = QPushButton("Last Week")
        self.last_month_btn = QPushButton("Last Month")
        for btn in [self.last_hour_btn, self.last_day_btn, self.last_week_btn, self.last_month_btn]:
            self.quick_range_layout.addWidget(btn)
        self.layout.addLayout(self.quick_range_layout)

        # 2. now the relative time widgets
        # "or by relative time" label
        self.or_by_relative_label = QLabel("or by relative time")
        self.layout.addWidget(self.or_by_relative_label)

        # We need a widget where you can only enter digits:
        class NumberOnlyTextEdit(QTextEdit):
            def keyPressEvent(self, event):
                if event.text().isdigit() or event.key() in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right, Qt.Key_Tab, Qt.Key_Enter, Qt.Key_Return):
                    super().keyPressEvent(event)
                else:
                    event.ignore()
        self.for_row_layout = QHBoxLayout()
        self.for_label = QLabel("For")
        self.for_row_layout.addWidget(self.for_label)
        self.for_text = NumberOnlyTextEdit()
        self.for_text.setFixedHeight(self.for_text.fontMetrics().height() + 12)
        self.for_text.setFixedWidth(120)
        self.for_text.setText('1')
        self.for_row_layout.addWidget(self.for_text)
        self.interval_dropdown = QComboBox()
        self.interval_dropdown.addItems(["hour(s)", "day(s)", "week(s)", "month(s)"])
        self.for_row_layout.addWidget(self.interval_dropdown)
        self.direction_dropdown = QComboBox()
        self.direction_dropdown.addItems(['before', 'around', 'after'])
        self.for_row_layout.addWidget(self.direction_dropdown)
        self.for_picker = QDateTimeEdit()
        self.for_picker.setObjectName('for_picker')
        self.for_picker.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        self.for_picker.setDateTime(datetime.utcnow())
        self.for_row_layout.addWidget(self.for_picker)
        self.layout.addLayout(self.for_row_layout)

        # 3. finally the direct start and end widgets
        # "or directly:" label
        self.or_directly_label = QLabel("or directly:")
        self.layout.addWidget(self.or_directly_label)

        # Start/end pickers
        self.pickers_layout = QHBoxLayout()
        self.start_picker = QDateTimeEdit()
        self.start_picker.setObjectName('start')
        self.start_picker.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        self.start_picker.setDateTime(datetime.utcnow() - timedelta(hours=1))
        self.end_picker = QDateTimeEdit()
        self.end_picker.setObjectName('end')
        self.end_picker.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        self.end_picker.setDateTime(datetime.utcnow())
        self.pickers_layout.addWidget(QLabel('From'))
        self.pickers_layout.addWidget(self.start_picker)
        self.pickers_layout.addWidget(QLabel('To'))
        self.pickers_layout.addWidget(self.end_picker)
        self.pickers_layout.addWidget(QLabel('UTC'))
        self.layout.addLayout(self.pickers_layout)

        self.setLayout(self.layout)

        # --- Logic for quick range and interval changes ---
        def set_quick_range(hours):
            "called when a most recent period button is clicked"
            now = datetime.utcnow()
            start = now - timedelta(hours=hours)
            # change the downstream widgets:
            # the direct start and end widgets
            self.start_picker.setDateTime(start)
            self.end_picker.setDateTime(now)
            # and the relative time widgets
            self.for_text.setText("1")
            choices = {
                1: 'hour(s)',
                24: 'day(s)',
                24 * 7: 'week(s)',
                24 * 30: 'month(s)'
            }
            self.interval_dropdown.setCurrentText(choices.get(hours, 'day(s)'))
            self.direction_dropdown.setCurrentText('before')
            self.for_picker.setDateTime(datetime.now())

        def on_interval_changed():
            "called when one of the realtive time widgets is called"
            now = datetime.utcnow()
            # convert the widget values to a time range
            try:
                value = int(self.for_text.toPlainText())
            except ValueError:
                value = 1
            interval = self.interval_dropdown.currentText()
            if interval == "hour(s)":
                delta = timedelta(hours=value)
            elif interval == "day(s)":
                delta = timedelta(days=value)
            elif interval == "week(s)":
                delta = timedelta(weeks=value)
            elif interval == "month(s)":
                delta = timedelta(days=30 * value)
            else:
                delta = timedelta(days=value)
            direction = self.direction_dropdown.currentText()
            ref_time = self.for_picker.dateTime().toPython()
            if direction == 'before':
                start = ref_time - delta
                end = ref_time
            elif direction == 'after':
                start = ref_time
                end = ref_time + delta
            elif direction == 'around':
                half = delta / 2
                start = ref_time - half
                end = ref_time + half
            else:
                start = ref_time - delta
                end = ref_time
            # and set the downstream direct start and end widgets    
            self.start_picker.setDateTime(start)
            self.end_picker.setDateTime(end)

        # define the behavior of the most recent period buttons
        self.last_hour_btn.clicked.connect(lambda: set_quick_range(1))
        self.last_day_btn.clicked.connect(lambda: set_quick_range(24))
        self.last_week_btn.clicked.connect(lambda: set_quick_range(24 * 7))
        self.last_month_btn.clicked.connect(lambda: set_quick_range(24 * 30))

        # define the behavior of the relative time widgets
        self.for_text.textChanged.connect(on_interval_changed)
        self.interval_dropdown.currentIndexChanged.connect(on_interval_changed)
        self.direction_dropdown.currentIndexChanged.connect(on_interval_changed)
        self.for_picker.dateTimeChanged.connect(on_interval_changed)
