import sys
from PySide6.QtWidgets import QApplication

from model import SBarModel
from view import View
from controller import Controller

if __name__ == "__main__":
    app = QApplication(sys.argv)

    model = SBarModel()
    view = View(model)
    controller = Controller(model, view)

    view.main_window.show()

    sys.exit(app.exec())