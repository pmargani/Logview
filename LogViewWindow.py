import os
import numpy as np

from PySide6.QtWidgets import QApplication 

from PySide6.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QFileDialog, QMessageBox, QGroupBox, QHBoxLayout, QPushButton, QListWidgetItem
from PySide6.QtGui import QGuiApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
from SamplerData import SamplerData
from PlotData import PlotData
from TimeRangePanel import TimeRangePanel
from DataSelectionPanel import DataSelectionPanel
from StatusBarPanel import StatusBarPanel
from MenuBar import MenuBar

DMJD = "DMJD"

class LogViewWindow(QWidget):

    """
    This is the main window for the GBT LogView application.  This application if for plotting elements
    of data contained in FITS files produced by the GBT program sampler2log.
    Components include:
       * TimeRangePanel for choosing the start and end times for which data will be plotted
       * DataSelectionPanel for choosing what FITS files to load and which of the columns to plot
       * StatusBarPanel for updating progress of loading data
       * standard Menu
       * PlotData (model) for constructing matplotlib figure of selected data
       * SamplerData (model) for reading the data to be plotted from FITS files created by sampler2log
    """
    
    def __init__(self, app):
        super().__init__()
        self.setWindowTitle('GBT LogView')
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            width = screen_geometry.width() // 2
            height = screen_geometry.height() // 2
            left = screen_geometry.left() + (screen_geometry.width() - width) // 2
            top = screen_geometry.top() + (screen_geometry.height() - height) // 2
        else:
            width, height, left, top = 400, 300, 100, 100
        self.setGeometry(left, top, width, height)

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.aliases = {
            "Weather-Weather2-weather2": os.path.join(base_dir, 'Weather-Weather2-weather2'),
            "does not exist": None,
        }

        # creaate and layout the major widget components
        self.menubar = MenuBar(self, app, self.open_folder)
        self.plot_button = QPushButton('Plot')
        self.plot_button.setEnabled(False)
        self.status_bar_panel = StatusBarPanel(self)
        self.time_range_panel = TimeRangePanel(self)
        self.data_selection_panel = DataSelectionPanel(self.aliases, self.loadSampler, self)
        self.buttons_panel = QGroupBox('buttons')
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.plot_button)
        self.buttons_panel.setLayout(buttons_layout)
        self.tab_widget = QTabWidget(self)
        self.selection_tab = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_tab)
        self.selection_layout.addWidget(self.time_range_panel)
        self.selection_layout.addWidget(self.data_selection_panel)
        self.selection_layout.addWidget(self.buttons_panel)
        self.selection_layout.addWidget(self.status_bar_panel)
        self.selection_tab.setLayout(self.selection_layout)
        self.tab_widget.addTab(self.selection_tab, 'selection')
        self.graph_tab = QWidget()
        self.tab_widget.addTab(self.graph_tab, 'graph')
        layout = QVBoxLayout(self)
        layout.setMenuBar(self.menubar)
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        self.plot_button.clicked.connect(self.on_plot_clicked)
        self._sampler = None
        self._col_units = None

    def open_folder(self):
        "called by the Open menu action: calls loadSampler function"
        dir_path = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if not dir_path:
            self.plot_button.setEnabled(False)
            self._sampler = None
            return
        self.loadSampler(dir_path)

    def loadSampler(self, dir_path):
        "called by Open menu action AND if an alias is loaded in the DataSelectionPanel"
        sampler = SamplerData(dir_path)
        # we use the youngest file to figure out the meta-data: columns and units
        youngest_file = sampler.find_youngest_fits()
        if not youngest_file:
            QMessageBox.information(self, 'No FITS Files', 'No .fits files found in the selected directory.')
            self.plot_button.setEnabled(False)
            self._sampler = None
            return
        colnames = sampler.get_second_table_columns()
        colunits = sampler.get_second_table_units()
        col_map = {col: colunits[i] for i, col in enumerate(colnames)}
        if not colnames:
            QMessageBox.warning(self, 'FITS File', f'No second table HDU with columns found in {os.path.basename(youngest_file)}.')
            self.plot_button.setEnabled(False)
            self._sampler = None
            return
        # populate the data selection col widgets with the col and unit info
        self.data_selection_panel.x_dropdown.clear()
        self.data_selection_panel.y_list.clear()
        # the x dropdown is simple enough
        for i, col in enumerate(colnames):
            display_text = f"{col} ({colunits[i]})" if colunits and i < len(colunits) else f"Column: {col}"
            self.data_selection_panel.x_dropdown.addItem(display_text, userData=col)
        self.data_selection_panel.x_dropdown.addItems(colnames)
        # y dropdowns are more complicated: we want to display "col (units)", but return
        # just the col value upon selection
        for col in colnames:
            display_text = f"{col} ({col_map[col]})"
            item = QListWidgetItem(display_text)
            item.setData(0x0100, col)
            self.data_selection_panel.y_list.addItem(item)
            item2 = QListWidgetItem(display_text)
            item2.setData(0x0100, col)
            self.data_selection_panel.y2_list.addItem(item2)
        self.plot_button.setEnabled(True)
        self._sampler = sampler
        self._col_units = col_map

    def on_plot_clicked(self):
        "called when the plot button is clicked - will determine data to plot and plot it"
        sampler = getattr(self, '_sampler', None)
        if not sampler:
            QMessageBox.warning(self, 'No Data', 'No FITS data loaded.')
            return
        # get the time range of the data to plot
        start_dt = self.time_range_panel.start_picker.dateTime().toPython()
        end_dt = self.time_range_panel.end_picker.dateTime().toPython()
        if start_dt > end_dt:
            QMessageBox.critical(self, 'Date Error', 'Start date must be before or equal to end date.')
            return
        # get the columns to plot
        x_col = self.data_selection_panel.x_dropdown.currentData()
        y_selected_items = self.data_selection_panel.y_list.selectedItems()
        if not y_selected_items:
            QMessageBox.critical(self, 'Selection Error', 'Please select at least one y column.')
            return
        y_cols = [item.data(0x0100) for item in y_selected_items]
        y2_selected_items = self.data_selection_panel.y2_list.selectedItems()
        y2_cols = [item.data(0x0100) for item in y2_selected_items]
        try:
            num_y_cols = len(y_cols)
            num_y2_cols = len(y2_cols)
            cols = [x_col] + y_cols + y2_cols
            def show_file_status(file_path, nfile, num_files):
                "a function for updating the status bar with info on how we are loading data"
                self.status_bar_panel.status_left.setText(f"Opening: {os.path.basename(file_path)}")
                self.status_bar_panel.status_center.setText(f"{nfile+1}/{num_files}")
                progress = int((nfile + 1) / num_files * 100) if num_files > 0 else 0
                self.status_bar_panel.status_progress.setValue(progress)
                QApplication.processEvents()
            # now that we know what data we want to plot and when, collect the data, updating
            # the status bar as we go, since it could take a while    
            data = sampler.get_data(cols, (start_dt, end_dt), pre_open_hook=show_file_status)
            if data.shape[1] < 2:
                QMessageBox.critical(self, 'Data Error', 'Data does not have enough columns for x and y.')
                return
            # we are done collecting data and are ready to plot, so update the status bar
            self.status_bar_panel.status_left.setText("Plotting Data")
            self.status_bar_panel.status_center.setText("")
            self.status_bar_panel.status_progress.setValue(0)
            QApplication.processEvents()

            # here we apply the expressions defined by users to the data we collected
            x = data[:, 0]
            apply_expr = self.data_selection_panel.x_expr.toPlainText().replace('x', 'data')
            x = sampler.apply_expression_to_data(x, apply_expr)
            ys = np.array([data[:, i] for i in range(1, num_y_cols+1)])
            apply_expr = self.data_selection_panel.y_expr.toPlainText().replace('y', 'data')
            ys = sampler.apply_expression_to_data(ys, apply_expr)
            y_expr = apply_expr.replace('data', '')
            ys2 = np.array([data[:, i] for i in range(num_y_cols+1, num_y_cols+1 + num_y2_cols)])
            apply_expr = self.data_selection_panel.y2_expr.toPlainText().replace('y2', 'data')
            ys2 = sampler.apply_expression_to_data(ys2, apply_expr)
            y2_expr = apply_expr.replace('data', '')
        except Exception as e:
            QMessageBox.critical(self, 'Plot Error', f'Error retrieving data: {e}')
            return
        # finally, we are ready to create a plot figure 
        plot_data = PlotData(x, ys, x_col, y_cols, y_expr, sampler.sampler_name, self._col_units, y2_list=ys2, y2_cols=y2_cols, y2_expr=y2_expr, date_plot=x_col == DMJD)
        fig, ax = plot_data.plot_data()
        # and we update the graph tab to show this plot
        if hasattr(self, 'canvas'):
            self.canvas.setParent(None)
            del self.canvas
        if hasattr(self, 'toolbar'):
            self.toolbar.setParent(None)
            del self.toolbar
        self.canvas = FigureCanvas(fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self.graph_tab)
        if not hasattr(self, 'graph_layout'):
            self.graph_layout = QVBoxLayout(self.graph_tab)
            self.graph_tab.setLayout(self.graph_layout)
        else:
            while self.graph_layout.count():
                item = self.graph_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
        self.graph_layout.addWidget(self.toolbar)
        self.graph_layout.addWidget(self.canvas)
        self.tab_widget.setCurrentWidget(self.graph_tab)
