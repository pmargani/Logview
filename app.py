import sys
from datetime import datetime
import os

import numpy as np
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QTabWidget, QVBoxLayout, QMenuBar, QMenu, QFileDialog, QMessageBox, QDateTimeEdit, QHBoxLayout, QGroupBox, QComboBox
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QPushButton
import matplotlib
matplotlib.use('Qt5Agg')  # Use the Qt5Agg backend for matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
from PySide6.QtWidgets import QVBoxLayout

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtWidgets import QGridLayout, QTextEdit, QLabel

from SamplerData import SamplerData
from PlotData import PlotData
from PySide6.QtCore import Qt
from datetime import timedelta

# constants
DMJD = "DMJD"

def run_app():

    screen = QGuiApplication.primaryScreen()
    if screen:
        screen_geometry = screen.geometry()
        width = screen_geometry.width() // 2
        height = screen_geometry.height() // 2
        left = screen_geometry.left() + (screen_geometry.width() - width) // 2
        top = screen_geometry.top() + (screen_geometry.height() - height) // 2
    else:
        print("No primary screen found, using fallback dimensions.")
        width, height, left, top = 400, 300, 100, 100  # fallback

    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle('GBT LogView')
    # window.setGeometry(100, 100, 400, 300)
    window.setGeometry(left, top, width, height)

    # Menu bar
    menubar = QMenuBar(window)
    file_menu = QMenu('File', menubar)
    open_action = QAction('Open...', menubar)
    file_menu.addAction(open_action)
    menubar.addMenu(file_menu)
    menubar.setNativeMenuBar(False)

    # Create plot_button before open_folder is defined so it exists on window

    window.plot_button = QPushButton('Plot')
    window.plot_button.setEnabled(False)

    # TBF: aliases should be loaded from sparrow.conf
    base_dir = os.path.dirname(os.path.abspath(__file__))
    aliases = {
        "Weather-Weather2-weather2": os.path.join(base_dir, 'Weather-Weather2-weather2'),
        "does not exist": None,
    }

    def open_folder():
        dir_path = QFileDialog.getExistingDirectory(window, 'Select Folder')
        if not dir_path:
            window.plot_button.setEnabled(False)
            window._sampler = None
            return
        loadSampler(dir_path)

    def loadSampler(dir_path):    
        sampler = SamplerData(dir_path)
        youngest_file = sampler.find_youngest_fits()
        if not youngest_file:
            QMessageBox.information(window, 'No FITS Files', 'No .fits files found in the selected directory.')
            window.plot_button.setEnabled(False)
            window._sampler = None
            return
        # get column information
        colnames = sampler.get_second_table_columns()
        colunits = sampler.get_second_table_units()
        col_map = {col: colunits[i] for i, col in enumerate(colnames)}  # Map column names to themselves
        if not colnames:
            QMessageBox.warning(window, 'FITS File', f'No second table HDU with columns found in {os.path.basename(youngest_file)}.')
            window.plot_button.setEnabled(False)
            window._sampler = None
            return
        
        # use these to populate the dropdown and list widgets
        window.x_dropdown.clear()
        window.y_list.clear()
        for i, col in enumerate(colnames):
            # For example, display "Column: <col>" but return <col>
            display_text = f"{col} ({colunits[i]})" if colunits and i < len(colunits) else f"Column: {col}"
            window.x_dropdown.addItem(display_text, userData=col)
        window.x_dropdown.addItems(colnames)
        for col in colnames:
            display_text = f"{col} ({col_map[col]})"
            
            item = QListWidgetItem(display_text)
            item.setData(0x0100, col)  # Qt.UserRole = 0x0100
            window.y_list.addItem(item)
            item2 = QListWidgetItem(display_text)
            item2.setData(0x0100, col)
            window.y2_list.addItem(item2)

        # finally we can enable the plot button    
        window.plot_button.setEnabled(True)
        window._sampler = sampler
        window._col_units = col_map
        # QMessageBox.information(window, 'FITS Columns', f'Columns in second table of {os.path.basename(youngest_file)}:\n' + ', '.join(colnames))

    def on_plot_clicked():
        sampler = getattr(window, '_sampler', None)
        if not sampler:
            QMessageBox.warning(window, 'No Data', 'No FITS data loaded.')
            return
        start_dt = start_picker.dateTime().toPython()
        end_dt = end_picker.dateTime().toPython()
        # testing:
        # start_dt = datetime(2025, 7, 7, 0, 0, 0)
        # end_dt = datetime(2025, 7, 8, 0, 0, 0)
        print('Start:', start_dt, 'End:', end_dt)
        if start_dt > end_dt:
            QMessageBox.critical(window, 'Date Error', 'Start date must be before or equal to end date.')
            return

        x_col = window.x_dropdown.currentData()
        print('Selected x column:', x_col)
        y_selected_items = window.y_list.selectedItems()
        if not y_selected_items:
            QMessageBox.critical(window, 'Selection Error', 'Please select at least one y column.')
            return       # Use the data (Qt.UserRole) instead of the displayed text
        y_cols = [item.data(0x0100) for item in y_selected_items]
        print('Selected y columns:', y_cols)
 
        y2_selected_items = window.y2_list.selectedItems()
        y2_cols = [item.data(0x0100) for item in y2_selected_items]
        # For now, only use the first selected y column for compatibility with get_data
        # y_col = y_cols[0]
        try:
            num_y_cols = len(y_cols)
            num_y2_cols = len(y2_cols)
            cols = [x_col] + y_cols + y2_cols
            def show_file_status(file_path, nfile, num_files):
                window.status_left.setText(f"Opening: {os.path.basename(file_path)}")
                window.status_center.setText(f"{nfile+1}/{num_files}")
                progress = int((nfile + 1) / num_files * 100) if num_files > 0 else 0
                window.status_progress.setValue(progress)
                QApplication.processEvents()  # Ensure UI updates immediately
            data = sampler.get_data(cols, (start_dt, end_dt), pre_open_hook=show_file_status)
            print('Data.shape:', data.shape)
            if data.shape[1] < 2:
                QMessageBox.critical(window, 'Data Error', 'Data does not have enough columns for x and y.')
                return
            # update status bar again
            window.status_left.setText("Plotting Data")
            window.status_center.setText("")
            window.status_progress.setValue(0)
            QApplication.processEvents()

            # extract the data and apply expressions
            x = data[:, 0]
            apply_expr = window.x_expr.toPlainText().replace('x', 'data')
            x = sampler.apply_expression_to_data(x, apply_expr)
            # x_expr = apply_expr.remove('data')

            ys = np.array([data[:, i] for i in range(1, num_y_cols+1)])
            print("ys:", ys)
            apply_expr = window.y_expr.toPlainText().replace('y', 'data')
            print("apply_expr:", apply_expr)
            ys = sampler.apply_expression_to_data(ys, apply_expr)
            print("ys:", ys)
            y_expr = apply_expr.replace('data', '')

            ys2 = np.array([data[:, i] for i in range(num_y_cols+1, num_y_cols+1 + num_y2_cols)])
            apply_expr = window.y2_expr.toPlainText().replace('y2', 'data')
            ys2 = sampler.apply_expression_to_data(ys2, apply_expr)
            print("ys2:", ys2)
            y2_expr = apply_expr.replace('data', '')

            y_col = y_cols
        except Exception as e:
            QMessageBox.critical(window, 'Plot Error', f'Error retrieving data: {e}')
            return

        plot_data = PlotData(x, ys, x_col, y_cols, y_expr, sampler.sampler_name, window._col_units, y2_list=ys2, y2_cols=y2_cols, y2_expr=y2_expr, date_plot=x_col == DMJD)
        fig, ax = plot_data.plot_data()
        # Remove previous plot if exists
        if hasattr(window, 'canvas'):
            window.canvas.setParent(None)
            del window.canvas
        if hasattr(window, 'toolbar'):
            window.toolbar.setParent(None)
            del window.toolbar

        # Create canvas and toolbar
        window.canvas = FigureCanvas(fig)
        window.toolbar = NavigationToolbar2QT(window.canvas, graph_tab)

        # Layout for graph_tab
        if not hasattr(window, 'graph_layout'):
            window.graph_layout = QVBoxLayout(graph_tab)
            graph_tab.setLayout(window.graph_layout)
        else:
            # Remove all widgets from layout
            while window.graph_layout.count():
                item = window.graph_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)

        window.graph_layout.addWidget(window.toolbar)
        window.graph_layout.addWidget(window.canvas)

        # Switch to graph tab
        tab_widget.setCurrentWidget(graph_tab)

    window.plot_button.clicked.connect(on_plot_clicked)
    open_action.triggered.connect(open_folder)

    tab_widget = QTabWidget(window)
    selection_tab = QWidget()
    selection_layout = QVBoxLayout(selection_tab)
    # Status bar for the selection tab (split into three parts)
    from PySide6.QtWidgets import QStatusBar, QLabel

    window.status_bar = QStatusBar()
    window.status_left = QLabel('Ready')
    window.status_center = QLabel('')
    from PySide6.QtWidgets import QProgressBar, QHBoxLayout
    window.status_progress = QProgressBar()
    window.status_progress.setMinimum(0)
    window.status_progress.setMaximum(100)
    window.status_progress.setValue(0)
    window.status_progress.setTextVisible(True)
    outline_style = "border: 1px solid #444; padding: 2px; border-radius: 3px;"
    window.status_left.setStyleSheet(outline_style)
    window.status_center.setStyleSheet(outline_style)
    window.status_progress.setStyleSheet(outline_style)
    window.status_bar.setStyleSheet("QStatusBar { border: 1px solid #222; }")
    status_container = QWidget()
    status_layout = QHBoxLayout()
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(0)
    status_layout.addWidget(window.status_left, stretch=70)
    status_layout.addWidget(window.status_center, stretch=15)
    status_layout.addWidget(window.status_progress, stretch=15)
    status_container.setLayout(status_layout)
    window.status_bar.addPermanentWidget(status_container, 1)

    # Time range panel with "For" and "or directly:" labels above the pickers
    time_range_panel = QGroupBox("Time Range")
    time_range_layout = QVBoxLayout()

    # Add label above quick range buttons
    using_most_recent_label = QLabel("Using most recent period:")
    time_range_layout.addWidget(using_most_recent_label)
    # Add quick range buttons above "or by relative time"
    quick_range_layout = QHBoxLayout()
    window.last_hour_btn = QPushButton("Last Hour")
    window.last_day_btn = QPushButton("Last Day")
    window.last_week_btn = QPushButton("Last Week")
    window.last_month_btn = QPushButton("Last Month")
    quick_range_layout.addWidget(window.last_hour_btn)
    quick_range_layout.addWidget(window.last_day_btn)
    quick_range_layout.addWidget(window.last_week_btn)
    quick_range_layout.addWidget(window.last_month_btn)
    time_range_layout.addLayout(quick_range_layout)

    def set_quick_range(hours):
        """Set the start and end pickers to a quick range."""
        now = datetime.utcnow()
        start = now - timedelta(hours=hours)
        start_picker.setDateTime(start)
        end_picker.setDateTime(now)
        # update the other widgets too
        window.for_text.setText("1")
        
        choices = {
            1: 'hour(s)',
            24: 'day(s)',
            24 * 7: 'week(s)',
            24 * 30: 'month(s)'
        }
        window.interval_dropdown.setCurrentText(choices.get(hours, 'day(s)'))   
        window.direction_dropdown.setCurrentText('before')  # Default to 'before' for quick ranges
        window.for_picker.setDateTime(datetime.now())

    def on_interval_changed():
        now = datetime.utcnow()
        try:
            value = int(window.for_text.toPlainText())
        except ValueError:
            value = 1
        interval = window.interval_dropdown.currentText()
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
        direction = window.direction_dropdown.currentText()
        ref_time = window.for_picker.dateTime().toPython()
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
        start_picker.setDateTime(start)
        end_picker.setDateTime(end)

    window.last_hour_btn.clicked.connect(lambda: set_quick_range(1))
    window.last_day_btn.clicked.connect(lambda: set_quick_range(24))
    window.last_week_btn.clicked.connect(lambda: set_quick_range(24 * 7))
    window.last_month_btn.clicked.connect(lambda: set_quick_range(24 * 30))
    # "or by relative time" label above the for_row
    or_by_relative_label = QLabel("or by relative time")
    time_range_layout.addWidget(or_by_relative_label)
    # "For" label with text widget to the right

    class NumberOnlyTextEdit(QTextEdit):
        def keyPressEvent(self, event):
            if event.text().isdigit() or event.key() in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right, Qt.Key_Tab, Qt.Key_Enter, Qt.Key_Return):
                super().keyPressEvent(event)
            else:
                event.ignore()

    for_row_layout = QHBoxLayout()
    for_label = QLabel("For")
    for_row_layout.addWidget(for_label)
    window.for_text = NumberOnlyTextEdit()
    window.for_text.setFixedHeight(window.for_text.fontMetrics().height() + 12)
    window.for_text.setFixedWidth(120)
    window.for_text.setText('1')
    window.for_text.textChanged.connect(on_interval_changed)
    for_row_layout.addWidget(window.for_text)

    # Add interval dropdown
    window.interval_dropdown = QComboBox()
    window.interval_dropdown.addItems(["hour(s)", "day(s)", "week(s)", "month(s)"])


    window.interval_dropdown.currentIndexChanged.connect(on_interval_changed)
    for_row_layout.addWidget(window.interval_dropdown)

    # Add direction dropdown after interval_dropdown
    window.direction_dropdown = QComboBox()
    window.direction_dropdown.addItems(['before', 'around', 'after'])
    window.direction_dropdown.currentIndexChanged.connect(on_interval_changed)

    for_row_layout.addWidget(window.direction_dropdown)

    # Add QDateTimeEdit widget called for_picker after direction_dropdown
    window.for_picker = QDateTimeEdit()
    window.for_picker.setObjectName('for_picker')
    window.for_picker.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
    window.for_picker.setDateTime(datetime.utcnow())
    window.for_picker.dateTimeChanged.connect(on_interval_changed)
    for_row_layout.addWidget(window.for_picker)

    time_range_layout.addLayout(for_row_layout)

    # "or directly:" label
    or_directly_label = QLabel("or directly:")
    time_range_layout.addWidget(or_directly_label)

    # Horizontal layout for the pickers
    pickers_layout = QHBoxLayout()
    start_picker = QDateTimeEdit()
    start_picker.setObjectName('start')
    start_picker.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
    start_picker.setDateTime(datetime.utcnow() - timedelta(hours=1))
    end_picker = QDateTimeEdit()
    end_picker.setObjectName('end')
    end_picker.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
    end_picker.setDateTime(datetime.utcnow())
    pickers_layout.addWidget(QLabel('From'))
    pickers_layout.addWidget(start_picker)
    pickers_layout.addWidget(QLabel('To'))
    pickers_layout.addWidget(end_picker)
    pickers_layout.addWidget(QLabel('UTC'))

    time_range_layout.addLayout(pickers_layout)
    time_range_panel.setLayout(time_range_layout)

    # Create a horizontal panel to hold fit_columns_panel (left) and a right panel (right)
    columns_and_right_panel = QGroupBox()
    columns_and_right_layout = QHBoxLayout()

    # Fit columns panel (left)
    fit_columns_panel = QGroupBox('fit columns')
    fit_columns_layout = QVBoxLayout()
    window.x_dropdown = QComboBox()
    window.x_dropdown.setObjectName('x')

    # Use QListWidget for multi-selection of y and y2
    window.y_list = QListWidget()
    window.y_list.setObjectName('y')
    window.y_list.setSelectionMode(QListWidget.MultiSelection)

    window.y2_list = QListWidget()
    window.y2_list.setObjectName('y2')
    window.y2_list.setSelectionMode(QListWidget.MultiSelection)

    window.x_expr = QTextEdit()
    window.x_expr.setText('x+0')
    window.x_expr.setFixedHeight(window.x_expr.fontMetrics().height() + 12)

    window.y_expr = QTextEdit()
    window.y_expr.setText('y*1')
    window.y_expr.setFixedHeight(window.y_expr.fontMetrics().height() + 12)

    window.y2_expr = QTextEdit()
    window.y2_expr.setText('y2*1')
    window.y2_expr.setFixedHeight(window.y2_expr.fontMetrics().height() + 12)

    grid_layout = QGridLayout()
    grid_layout.addWidget(QLabel('Axis:'), 0, 0)
    grid_layout.addWidget(QLabel('Column:'), 0, 1)
    grid_layout.addWidget(QLabel('Exprresion:'), 0, 2)

    grid_layout.addWidget(QLabel('x:'), 1, 0)
    grid_layout.addWidget(window.x_dropdown, 1, 1)
    grid_layout.addWidget(window.x_expr, 1, 2)

    grid_layout.addWidget(QLabel('y:'), 2, 0)
    grid_layout.addWidget(window.y_list, 2, 1)
    grid_layout.addWidget(window.y_expr, 2, 2)

    grid_layout.addWidget(QLabel('y2:'), 3, 0)
    grid_layout.addWidget(window.y2_list, 3, 1)
    grid_layout.addWidget(window.y2_expr, 3, 2)

    fit_columns_panel.setLayout(grid_layout)

    # Right hand side panel
    right_panel = QGroupBox('Aliases')
    right_panel_layout = QVBoxLayout()

    # QListWidget allowing only one selection
    window.alias_list = QListWidget()
    window.alias_list.setSelectionMode(QListWidget.SingleSelection)
    window.alias_list.addItems(aliases.keys())
    right_panel_layout.addWidget(window.alias_list)



    # "Load" button
    window.load_button = QPushButton('Load')
    right_panel_layout.addWidget(window.load_button)
    window.load_button.setEnabled(False)
    # don't enable the load button until an alias is selected
    def on_alias_selection_changed():
        selected = window.alias_list.selectedItems()
        window.load_button.setEnabled(bool(selected))
    window.alias_list.itemSelectionChanged.connect(on_alias_selection_changed)

    def on_load_button_clicked():
        selected_items = window.alias_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(window, 'No Alias Selected', 'Please select an alias to load.')
            return
        alias = selected_items[0].text()
        dir_path = aliases.get(alias)
        if not dir_path or not os.path.isdir(dir_path):
            QMessageBox.critical(window, 'Invalid Directory', f'The directory {dir_path} for alias "{alias}" does not exist.')
            return
        loadSampler(dir_path)

    window.load_button.clicked.connect(on_load_button_clicked)
    right_panel.setLayout(right_panel_layout)

    # Add panels to the horizontal layout
    columns_and_right_layout.addWidget(fit_columns_panel)
    columns_and_right_layout.addWidget(right_panel)
    columns_and_right_panel.setLayout(columns_and_right_layout)

    buttons_panel = QGroupBox('buttons')
    buttons_layout = QHBoxLayout()
    buttons_layout.addWidget(window.plot_button)
    buttons_panel.setLayout(buttons_layout)

    # Add the new columns_and_right_panel to the selection layout
    selection_layout.addWidget(time_range_panel)
    selection_layout.addWidget(columns_and_right_panel)
    selection_layout.addWidget(buttons_panel)
    selection_layout.addWidget(window.status_bar)
    selection_tab.setLayout(selection_layout)

    graph_tab = QWidget()
    tab_widget.addTab(selection_tab, 'selection')
    tab_widget.addTab(graph_tab, 'graph')

    layout = QVBoxLayout(window)
    layout.setMenuBar(menubar)
    layout.addWidget(tab_widget)
    window.setLayout(layout)

    window.show()
    sys.exit(app.exec())
