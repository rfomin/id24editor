from PySide6.QtWidgets import (
    QMainWindow,
    QDialog,
    QGraphicsScene,
    QWidget,
    QGraphicsPixmapItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QTreeWidgetItem,
    QListView,
    QStyledItemDelegate,
    QStyle,
)
from PySide6.QtCore import (
    QObject,
    Signal,
    QPointF,
    QRect,
    QAbstractListModel,
    QSize,
    Qt,
    QSortFilterProxyModel,
)
from PySide6.QtGui import QPixmap, QColor

from PIL.ImageQt import ImageQt

from ui_mainwindow import Ui_MainWindow
from ui_editconditions import Ui_Dialog
from ui_lumpsdialog import Ui_LumpsDialog

from doomdata import SCREENWIDTH, Alignment

from typing import Callable


class MainWindow(QMainWindow):
    openWadFile = Signal()
    saveAsFile = Signal()
    showLumps = Signal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.actionOpenWAD.triggered.connect(self.openWadFile)
        self.ui.actionSaveAs.triggered.connect(self.saveAsFile)
        self.ui.actionShowLumps.triggered.connect(self.showLumps)

    def updateScale(self, value: int):
        s = value / 100.0
        self.ui.graphicsView.resetTransform()
        self.ui.graphicsView.scale(s, s)


class EditCond(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.dlg = Ui_Dialog()
        self.dlg.setupUi(self)


class LumpsDialog(QDialog):
    lumpSelected = Signal(str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.dlg = Ui_LumpsDialog()
        self.dlg.setupUi(self)
        self.dlg.listView.setViewMode(QListView.IconMode)
        self.dlg.listView.setItemDelegate(LumpItemDelegate(self))

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.dlg.listView.setModel(self.proxy_model)

        self.dlg.filterLineEdit.textChanged.connect(self.proxy_model.setFilterRegularExpression)

        self.dlg.pushOK.clicked.connect(self.accept)
        self.dlg.pushCancel.clicked.connect(self.reject)

    def setModel(self, model):
        self.proxy_model.setSourceModel(model)

    def accept(self):
        selected_indexes = self.dlg.listView.selectedIndexes()
        if selected_indexes:
            proxy_index = selected_indexes[0]
            lump_name = self.proxy_model.data(proxy_index, Qt.DisplayRole)
            self.lumpSelected.emit(lump_name)
        super().accept()


class LumpItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        source_model = index.model().sourceModel()
        lump_name = index.data(Qt.DisplayRole)

        # Get pixmap from cache or load it
        if lump_name in source_model.pixmap_cache:
            pixmap = source_model.pixmap_cache[lump_name]
        else:
            try:
                lump = source_model.lumps[lump_name]
                pixmap = lumpToPixmap(lump)
                source_model.pixmap_cache[lump_name] = pixmap
            except Exception as e:
                print(f"Could not convert lump {lump_name} to pixmap: {e}")
                pixmap = None

        # Draw the item
        painter.save()

        # Draw background if selected
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Draw icon
        if pixmap:
            painter.drawPixmap(option.rect.topLeft(), pixmap)

        # Draw text
        if pixmap:
            text_rect = QRect(option.rect.left(), option.rect.top() + pixmap.height(), option.rect.width(), 20)
        else:
            text_rect = option.rect
        painter.drawText(text_rect, Qt.AlignCenter, lump_name)

        painter.restore()

    def sizeHint(self, option, index):
        source_model = index.model().sourceModel()
        lump_name = index.data(Qt.DisplayRole)

        lump = source_model.lumps[lump_name]
        # Add some padding for the name
        return QSize(max(lump.width + 20, 100), lump.height + 20)


class LumpModel(QAbstractListModel):
    def __init__(self, lumps, parent=None):
        super().__init__(parent)
        self.lumps = lumps
        self.lump_names = list(lumps.keys())
        self.pixmap_cache = {}

    def rowCount(self, parent):
        return len(self.lump_names)

    def data(self, index, role):
        if not index.isValid():
            return None

        row = index.row()
        lump_name = self.lump_names[row]

        if role == Qt.DisplayRole:
            return lump_name

        return None


class SBarElem(QObject, QGraphicsPixmapItem):
    updateElem = Signal(dict)

    def __init__(
        self,
        x: int,
        y: int,
        elem: dict,
        screenheight: int,
        pixmap: QPixmap,
    ):
        QObject.__init__(self)
        QGraphicsPixmapItem.__init__(self, pixmap)

        self.elem = elem
        self.x_diff = x - int(elem["x"])
        self.y_diff = y - int(elem["y"])
        self.screenheight = screenheight
        self.setFlags(
            self.flags()
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def mouseReleaseEvent(self, event) -> None:
        x = int(self.x())
        y = int(self.y())
        width = int(self.boundingRect().width())
        height = int(self.boundingRect().height())
        alignment = self.elem["alignment"]

        if not alignment & Alignment.h_middle:
            x = clamp(0, SCREENWIDTH - width + 1, x)
        if not alignment & Alignment.v_middle:
            y = clamp(0, self.screenheight - height + 1, y)

        self.setPos(QPointF(x, y))

        if alignment & Alignment.h_middle:
            x += width / 2
        elif alignment & Alignment.h_right:
            x += width
        if alignment & Alignment.v_middle:
            y += height / 2
        elif alignment & Alignment.v_bottom:
            y += height

        self.elem["x"] = x - self.x_diff
        self.elem["y"] = y - self.y_diff

        self.updateElem.emit(self.elem)

        return super().mouseReleaseEvent(event)

    def to_dict(self):
        return self.elem


class SBarCondItem(QTreeWidgetItem):
    def __init__(self, strings: list[str], cond: int):
        super().__init__(strings)
        self.cond = cond


def clamp(smallest, largest, n):
    return max(smallest, min(n, largest))


def lumpToPixmap(lump) -> QPixmap:
    image = lump.to_Image()
    image = cyanToAlpha(image)
    return QPixmap(ImageQt(image))


def imageToPixmap(image) -> QPixmap:
    image = cyanToAlpha(image)
    return QPixmap(ImageQt(image))


def cyanToAlpha(image):
    image = image.convert("RGBA")

    data = image.getdata()
    newData = []
    for item in data:
        if item[0] == 255 and item[1] == 0 and item[2] == 255:
            newData.append((255, 0, 255, 0))
        else:
            newData.append(item)
    image.putdata(newData)

    return image


class View:
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.scene = QGraphicsScene()
        self.main_window = MainWindow()
        self.edit_cond_dialog = EditCond(self.main_window)
        self.lumps_dialog = LumpsDialog(self.main_window)

        self.main_window.ui.graphicsView.setScene(self.scene)

    def clear_scene(self):
        for item in self.scene.items():
            self.scene.removeItem(item)

    def draw(self, barindex: int, update: Callable):
        self.clear_scene()
        self.updateProperties = update

        statusbar = self.model.sbardef["data"]["statusbars"][barindex]

        self.screenheight = statusbar["height"]

        rect = QRect(0, 0, SCREENWIDTH, self.screenheight)
        self.scene.setSceneRect(rect)
        item = QGraphicsRectItem(rect)
        item.setBrush(QColor(255, 0, 255, 255))
        self.scene.addItem(item)

        if statusbar["children"] is not None:
            for child in statusbar["children"]:
                self.drawElem(0, 0, child)

    def drawElem(self, x: int, y: int, elem: dict):
        type = next(iter(elem))
        values = next(iter(elem.values()))

        if self.model.check_conditions(values) is False:
            return

        x += values["x"]
        y += values["y"]

        if type == "graphic":
            patch = values["patch"]
            if patch in self.model.lumps:
                lump = self.model.lumps[patch]
                x -= lump.x_offset
                y -= lump.y_offset
                pixmap = lumpToPixmap(lump)
                self.addToScene(x, y, values, pixmap)

        elif type == "number" or type == "percent":
            for font in self.model.numberfonts:
                if font.name == values["font"]:
                    pixmap = imageToPixmap(
                        font.getPixmap(
                            values, pct=True if type == "percent" else False
                        )
                    )
                    self.addToScene(x, y, values, pixmap)

        elif type == "face":
            lump = self.model.lumps["STFST00"]
            if lump is not None:
                x -= lump.x_offset
                y -= lump.y_offset
                pixmap = lumpToPixmap(lump)
                self.addToScene(x, y, values, pixmap)

        if values["children"] is not None:
            for child in values["children"]:
                self.drawElem(x, y, child)

    def addToScene(self, x: int, y: int, elem: dict, pixmap: QPixmap):
        alignment = elem["alignment"]

        item = SBarElem(x, y, elem=elem, screenheight=self.screenheight, pixmap=pixmap)

        item.updateElem.connect(self.updateProperties)

        if alignment & Alignment.h_middle:
            x -= pixmap.width() / 2
        elif alignment & Alignment.h_right:
            x -= pixmap.width()
        if alignment & Alignment.v_middle:
            y -= pixmap.height() / 2
        elif alignment & Alignment.v_bottom:
            y -= pixmap.height()

        item.setPos(QPointF(x, y))
        elem["sceneitem"] = item
        self.scene.addItem(item)
