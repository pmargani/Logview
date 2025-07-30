from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QComboBox, QListWidget, QListWidgetItem, QGridLayout, QMessageBox
import os

class DataSelectionPanel(QGroupBox):

    """
    This class creates a panel for selecting data columns and aliases.
    It allows users to choose x, y, and y2 columns, set expressions for them,
    and load data from predefined aliases.
    """

    def __init__(self, aliases, loadSampler, parent=None):
        super().__init__(parent)
        self.setTitle('Data Selection')
        layout = QHBoxLayout()

        # Fit columns panel (left)
        fit_columns_panel = QGroupBox('fit columns')
        grid_layout = QGridLayout()
        # create the widgets for choosing what cols to plot
        self.x_dropdown = QComboBox()
        self.x_dropdown.setObjectName('x')
        self.y_list = QListWidget()
        self.y_list.setObjectName('y')
        self.y_list.setSelectionMode(QListWidget.MultiSelection)
        self.y2_list = QListWidget()
        self.y2_list.setObjectName('y2')
        self.y2_list.setSelectionMode(QListWidget.MultiSelection)
        # create the widgets for expressions to apply to the column data
        # here we default to expressions that won't change the actual data values
        self.x_expr = QTextEdit()
        self.x_expr.setText('x+0')
        self.x_expr.setFixedHeight(self.x_expr.fontMetrics().height() + 12)
        self.y_expr = QTextEdit()
        self.y_expr.setText('y*1')
        self.y_expr.setFixedHeight(self.y_expr.fontMetrics().height() + 12)
        self.y2_expr = QTextEdit()
        self.y2_expr.setText('y2*1')
        self.y2_expr.setFixedHeight(self.y2_expr.fontMetrics().height() + 12)
        # layout the widgets in a grid, along with labels
        grid_layout.addWidget(QLabel('Axis:'), 0, 0)
        grid_layout.addWidget(QLabel('Column:'), 0, 1)
        grid_layout.addWidget(QLabel('Exprresion:'), 0, 2)
        grid_layout.addWidget(QLabel('x:'), 1, 0)
        grid_layout.addWidget(self.x_dropdown, 1, 1)
        grid_layout.addWidget(self.x_expr, 1, 2)
        grid_layout.addWidget(QLabel('y:'), 2, 0)
        grid_layout.addWidget(self.y_list, 2, 1)
        grid_layout.addWidget(self.y_expr, 2, 2)
        grid_layout.addWidget(QLabel('y2:'), 3, 0)
        grid_layout.addWidget(self.y2_list, 3, 1)
        grid_layout.addWidget(self.y2_expr, 3, 2)
        fit_columns_panel.setLayout(grid_layout)

        # Right hand side panel 
        # this contains a list of aliases that get populated from a config file;
        # an alias is a shorthand for a directory named after a sampler holding FITS files
        right_panel = QGroupBox('Aliases')
        right_panel_layout = QVBoxLayout()
        self.alias_list = QListWidget()
        self.alias_list.setSelectionMode(QListWidget.SingleSelection)
        self.alias_list.addItems(aliases.keys())
        right_panel_layout.addWidget(self.alias_list)
        self.load_button = QPushButton('Load')
        right_panel_layout.addWidget(self.load_button)
        # the load button stays disabled until an alias is selected
        self.load_button.setEnabled(False)
        def on_alias_selection_changed():
            selected = self.alias_list.selectedItems()
            self.load_button.setEnabled(bool(selected))
        self.alias_list.itemSelectionChanged.connect(on_alias_selection_changed)
        def on_load_button_clicked():
            "when load button is clicked, populate widgets with sampler columns"
            selected_items = self.alias_list.selectedItems()
            # no alias selected?
            if not selected_items:
                QMessageBox.warning(self, 'No Alias Selected', 'Please select an alias to load.')
                return
            alias = selected_items[0].text()
            dir_path = aliases.get(alias)
            # directory really exists?
            if not dir_path or not os.path.isdir(dir_path):
                QMessageBox.critical(self, 'Invalid Directory', f'The directory {dir_path} for alias "{alias}" does not exist.')
                return
            # finally call the function given that reads the FITS files to populate the column widgets
            loadSampler(dir_path)
        self.load_button.clicked.connect(on_load_button_clicked)
        right_panel.setLayout(right_panel_layout)

        layout.addWidget(fit_columns_panel)
        layout.addWidget(right_panel)
        self.setLayout(layout)
