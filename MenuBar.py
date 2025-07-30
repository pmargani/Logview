from PySide6.QtWidgets import QMenuBar, QMenu, QMessageBox
from PySide6.QtGui import QAction

class MenuBar(QMenuBar):

    """
    This class creates a menu bar for the application with File and Help menus.
    """
    
    def __init__(self, window, app, open_action_handler):   
        super().__init__(window)
        # File menu
        file_menu = QMenu('File', self)
        open_action = QAction('Open...', self)
        open_action.triggered.connect(open_action_handler)
        file_menu.addAction(open_action)

        # Exit action
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(app.quit)
        file_menu.addAction(exit_action)
        self.addMenu(file_menu)
        self.setNativeMenuBar(False)

        # Help menu
        help_menu = QMenu('Help', self)
        help_action = QAction('Help', self)
        def show_help_dialog():
            QMessageBox.information(window, 'Help', 'Please contact Customer Support')
        help_action.triggered.connect(show_help_dialog)
        help_menu.addAction(help_action)
        self.addMenu(help_menu)

        # Expose actions for external use if needed
        self.open_action = open_action
        self.exit_action = exit_action
        self.help_action = help_action
