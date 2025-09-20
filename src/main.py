import sys
from PySide6.QtWidgets import QApplication

from model import SBarModel
from view import View
from controller import Controller

if __name__ == "__main__":
    app = QApplication(sys.argv)

    model = SBarModel()
    model.load_wad(r"c:\downloads\wads\DOOM2.WAD")
    model.load_wad(r"c:\downloads\wads\id1.wad")

    view = View(model)
    controller = Controller(model, view)

    controller.draw(0)

    view.main_window.show()

    sys.exit(app.exec())