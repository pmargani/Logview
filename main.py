import sys
from PySide6.QtWidgets import QApplication 
import matplotlib
matplotlib.use('Qt5Agg')  # Use the Qt5Agg backend for matplotlib

from LogViewWindow import LogViewWindow

def run_app():
    app = QApplication(sys.argv)
    window = LogViewWindow(app)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()