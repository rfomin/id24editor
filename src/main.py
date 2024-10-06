import sys
from PySide6.QtCore import QStringListModel
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsScene
from ui_mainwindow import Ui_MainWindow

from sbardef import SBarDef
from omg import WAD


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

    def updateScale(self, value: int):
        s = value / 100.0
        self.ui.graphicsView.resetTransform()
        self.ui.graphicsView.scale(s, s)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()

    model = QStringListModel()
    wad = WAD()
    wad.from_file(r"c:\downloads\wads\DOOM2.WAD")
    wad.from_file(r"c:\downloads\wads\id1.wad")
    lumps = wad.graphics + wad.patches + wad.sprites
    model.setStringList(lumps)
    window.ui.listView.setModel(model)

    scene = QGraphicsScene()

    window.ui.treeWidget.setColumnCount(2)
    window.ui.treeWidget.setHeaderLabels(["Key", "Value"])
    sbardef = SBarDef(scene, window.ui.treeWidget, window.ui.comboBox, wad)
    window.ui.comboBox.currentIndexChanged.connect(sbardef.draw)
    sbardef.draw(0)

    window.ui.graphicsView.setScene(scene)
    window.ui.horizontalSlider.valueChanged.connect(window.updateScale)
    window.updateScale(200)

    window.show()

    sys.exit(app.exec())
