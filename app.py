import sys
from datetime import datetime
from datetime import timedelta
import os

import numpy as np
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QTabWidget, QVBoxLayout, QFileDialog, QMessageBox, QDateTimeEdit, QHBoxLayout, QGroupBox, QComboBox
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QPushButton
import matplotlib
matplotlib.use('Qt5Agg')  # Use the Qt5Agg backend for matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
from PySide6.QtWidgets import QVBoxLayout

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtWidgets import QGridLayout, QTextEdit, QLabel
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStatusBar, QLabel

# this modules imports
from SamplerData import SamplerData
from PlotData import PlotData
from TimeRangePanel import TimeRangePanel
from DataSelectionPanel import DataSelectionPanel
from StatusBarPanel import StatusBarPanel
from MenuBar import MenuBar

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
        # No primary screen found, using fallback dimensions.
        width, height, left, top = 400, 300, 100, 100  # fallback

    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle('GBT LogView')
    # window.setGeometry(100, 100, 400, 300)
    window.setGeometry(left, top, width, height)

    # Menu bar (encapsulated)
    def open_folder():
        dir_path = QFileDialog.getExistingDirectory(window, 'Select Folder')
        if not dir_path:
            window.plot_button.setEnabled(False)
            window._sampler = None
            return
        loadSampler(dir_path)

    menubar = MenuBar(window, app, open_folder)

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
        data_selection_panel.x_dropdown.clear()
        data_selection_panel.y_list.clear()
        for i, col in enumerate(colnames):
            display_text = f"{col} ({colunits[i]})" if colunits and i < len(colunits) else f"Column: {col}"
            data_selection_panel.x_dropdown.addItem(display_text, userData=col)
        data_selection_panel.x_dropdown.addItems(colnames)
        for col in colnames:
            display_text = f"{col} ({col_map[col]})"
            item = QListWidgetItem(display_text)
            item.setData(0x0100, col)
            data_selection_panel.y_list.addItem(item)
            item2 = QListWidgetItem(display_text)
            item2.setData(0x0100, col)
            data_selection_panel.y2_list.addItem(item2)

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
        start_dt = time_range_panel.start_picker.dateTime().toPython()
        end_dt = time_range_panel.end_picker.dateTime().toPython()
        # print('Start:', start_dt, 'End:', end_dt)
        if start_dt > end_dt:
            QMessageBox.critical(window, 'Date Error', 'Start date must be before or equal to end date.')
            return

        x_col = data_selection_panel.x_dropdown.currentData()
        # print('Selected x column:', x_col)
        y_selected_items = data_selection_panel.y_list.selectedItems()
        if not y_selected_items:
            QMessageBox.critical(window, 'Selection Error', 'Please select at least one y column.')
            return
        y_cols = [item.data(0x0100) for item in y_selected_items]
        # print('Selected y columns:', y_cols)

        y2_selected_items = data_selection_panel.y2_list.selectedItems()
        y2_cols = [item.data(0x0100) for item in y2_selected_items]
        # For now, only use the first selected y column for compatibility with get_data
        # y_col = y_cols[0]
        try:
            num_y_cols = len(y_cols)
            num_y2_cols = len(y2_cols)
            cols = [x_col] + y_cols + y2_cols
            def show_file_status(file_path, nfile, num_files):
                status_bar_panel.status_left.setText(f"Opening: {os.path.basename(file_path)}")
                status_bar_panel.status_center.setText(f"{nfile+1}/{num_files}")
                progress = int((nfile + 1) / num_files * 100) if num_files > 0 else 0
                status_bar_panel.status_progress.setValue(progress)
                QApplication.processEvents()  # Ensure UI updates immediately
            data = sampler.get_data(cols, (start_dt, end_dt), pre_open_hook=show_file_status)
            # print('Data.shape:', data.shape)
            if data.shape[1] < 2:
                QMessageBox.critical(window, 'Data Error', 'Data does not have enough columns for x and y.')
                return
            # update status bar again
            status_bar_panel.status_left.setText("Plotting Data")
            status_bar_panel.status_center.setText("")
            status_bar_panel.status_progress.setValue(0)
            QApplication.processEvents()

            # extract the data and apply expressions
            x = data[:, 0]
            apply_expr = data_selection_panel.x_expr.toPlainText().replace('x', 'data')
            x = sampler.apply_expression_to_data(x, apply_expr)

            ys = np.array([data[:, i] for i in range(1, num_y_cols+1)])
            # print("ys:", ys)
            apply_expr = data_selection_panel.y_expr.toPlainText().replace('y', 'data')
            # print("apply_expr:", apply_expr)
            ys = sampler.apply_expression_to_data(ys, apply_expr)
            # print("ys:", ys)
            y_expr = apply_expr.replace('data', '')

            ys2 = np.array([data[:, i] for i in range(num_y_cols+1, num_y_cols+1 + num_y2_cols)])
            apply_expr = data_selection_panel.y2_expr.toPlainText().replace('y2', 'data')
            ys2 = sampler.apply_expression_to_data(ys2, apply_expr)
            # print("ys2:", ys2)
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

    # connect our buttons to actions
    window.plot_button.clicked.connect(on_plot_clicked)

    # the tab holds our selection panel and graph tab
    tab_widget = QTabWidget(window)

    # start the selection tab that has most of the widgets
    selection_tab = QWidget()
    selection_layout = QVBoxLayout(selection_tab)

    # Instantiate and add the status bar panel
    status_bar_panel = StatusBarPanel(window)

    # Instantiate and add the panel for selecting the time range
    time_range_panel = TimeRangePanel(window)

    # Instantiate and add the panel for selecting the data
    data_selection_panel = DataSelectionPanel(aliases, loadSampler, window)

    # right now we only have one button for plotting
    buttons_panel = QGroupBox('buttons')
    buttons_layout = QHBoxLayout()
    buttons_layout.addWidget(window.plot_button)
    buttons_panel.setLayout(buttons_layout)

    # Add the new panels to the selection layout
    selection_layout.addWidget(time_range_panel)
    selection_layout.addWidget(data_selection_panel)
    selection_layout.addWidget(buttons_panel)
    selection_layout.addWidget(status_bar_panel)
    selection_tab.setLayout(selection_layout)

    # Add the selection tab (first one) to the tab widget
    tab_widget.addTab(selection_tab, 'selection')

    # Create the graph tab - it's empty for now
    graph_tab = QWidget()
    tab_widget.addTab(graph_tab, 'graph')

    # Main layout for the window
    layout = QVBoxLayout(window)
    layout.setMenuBar(menubar)
    layout.addWidget(tab_widget)
    window.setLayout(layout)

    window.show()
    sys.exit(app.exec())
