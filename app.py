import sys
from datetime import datetime
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QTabWidget, QVBoxLayout, QMenuBar, QMenu, QFileDialog, QMessageBox, QDateTimeEdit, QHBoxLayout, QGroupBox, QComboBox
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QPushButton
import matplotlib
matplotlib.use('Qt5Agg')  # Use the Qt5Agg backend for matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
from PySide6.QtWidgets import QVBoxLayout

import os
from SamplerData import SamplerData
from PlotData import PlotData
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtWidgets import QGridLayout, QTextEdit, QLabel

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
    window.setWindowTitle('PySide6 Window')
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

    def open_folder():
        dir_path = QFileDialog.getExistingDirectory(window, 'Select Folder')
        if not dir_path:
            window.plot_button.setEnabled(False)
            window._sampler = None
            return
        sampler = SamplerData(dir_path)
        youngest_file = sampler.find_youngest_fits()
        if not youngest_file:
            QMessageBox.information(window, 'No FITS Files', 'No .fits files found in the selected directory.')
            window.plot_button.setEnabled(False)
            window._sampler = None
            return
        colnames = sampler.get_second_table_columns()
        if not colnames:
            QMessageBox.warning(window, 'FITS File', f'No second table HDU with columns found in {os.path.basename(youngest_file)}.')
            window.plot_button.setEnabled(False)
            window._sampler = None
            return
        window.x_dropdown.clear()
        window.y_list.clear()
        window.x_dropdown.addItems(colnames)
        for col in colnames:
            item = QListWidgetItem(col)
            window.y_list.addItem(item)
        window.plot_button.setEnabled(True)
        window._sampler = sampler
        # QMessageBox.information(window, 'FITS Columns', f'Columns in second table of {os.path.basename(youngest_file)}:\n' + ', '.join(colnames))

    def on_plot_clicked():
        sampler = getattr(window, '_sampler', None)
        if not sampler:
            QMessageBox.warning(window, 'No Data', 'No FITS data loaded.')
            return
        start_dt = start_picker.dateTime().toPython()
        end_dt = end_picker.dateTime().toPython()
        # testing:
        start_dt = datetime(2025, 7, 7, 0, 0, 0)
        end_dt = datetime(2025, 7, 8, 0, 0, 0)
        print('Start:', start_dt, 'End:', end_dt)
        if start_dt > end_dt:
            QMessageBox.critical(window, 'Date Error', 'Start date must be before or equal to end date.')
            return

        x_col = window.x_dropdown.currentText()
        y_selected_items = window.y_list.selectedItems()
        if not y_selected_items:
            QMessageBox.critical(window, 'Selection Error', 'Please select at least one y column.')
            return
        y_cols = [item.text() for item in y_selected_items]
        # For now, only use the first selected y column for compatibility with get_data
        # y_col = y_cols[0]
        try:
            cols = [x_col] + y_cols
            data = sampler.get_data(cols, (start_dt, end_dt))
            print('Data.shape:', data.shape)
            if data.shape[1] < 2:
                QMessageBox.critical(window, 'Data Error', 'Data does not have enough columns for x and y.')
                return
            # x = data[:, 0]
            # y = data[:, 1]
            x = data[:, 0]
            ys = [data[:, i] for i in range(1, data.shape[1])]
            y_col = y_cols
        except Exception as e:
            QMessageBox.critical(window, 'Plot Error', f'Error retrieving data: {e}')
            return
        plot_data = PlotData(x, ys, x_col, y_cols, sampler.sampler_name, date_plot=x_col == DMJD)
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

    # Time range panel
    time_range_panel = QGroupBox('time range')
    time_range_layout = QHBoxLayout()
    start_picker = QDateTimeEdit()
    start_picker.setObjectName('start')
    start_picker.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
    end_picker = QDateTimeEdit()
    end_picker.setObjectName('end')
    end_picker.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
    time_range_layout.addWidget(QLabel('Start:'))
    time_range_layout.addWidget(start_picker)
    time_range_layout.addWidget(QLabel('End:'))
    time_range_layout.addWidget(end_picker)
    time_range_panel.setLayout(time_range_layout)

    # Fit columns panel
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
    # window.x_expr.setVerticalScrollBarPolicy(False)
    # window.x_expr.setHorizontalScrollBarPolicy(False)

    window.y_expr = QTextEdit()
    window.y_expr.setText('y*1')
    window.y_expr.setFixedHeight(window.y_expr.fontMetrics().height() + 12)
    # window.y_expr.setVerticalScrollBarPolicy(False)
    # window.y_expr.setHorizontalScrollBarPolicy(False)

    window.y2_expr = QTextEdit()
    window.y2_expr.setText('y2*1')
    window.y2_expr.setFixedHeight(window.y2_expr.fontMetrics().height() + 12)
    # window.y2_expr.setVerticalScrollBarPolicy(False)
    # window.y2_expr.setHorizontalScrollBarPolicy(False)
    
    
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

    buttons_panel = QGroupBox('buttons')
    buttons_layout = QHBoxLayout()
    buttons_layout.addWidget(window.plot_button)
    buttons_panel.setLayout(buttons_layout)

    selection_layout.addWidget(time_range_panel)
    selection_layout.addWidget(fit_columns_panel)
    selection_layout.addWidget(buttons_panel)
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
