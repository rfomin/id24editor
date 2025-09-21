import shiboken6
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

from doomdata import SCREENWIDTH, Alignment, sbn

from typing import Callable


class MainWindow(QMainWindow):
    openJSONFile = Signal()
    openWadFile = Signal()
    saveAsFile = Signal()
    showLumps = Signal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.actionOpenJSON.triggered.connect(self.openJSONFile)
        self.ui.actionOpenWAD.triggered.connect(self.openWadFile)
        self.ui.actionSaveAs.triggered.connect(self.saveAsFile)
        self.ui.addGraphic.clicked.connect(self.showLumps)

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
                pixmap = lump_to_pixmap(lump)
                source_model.pixmap_cache[lump_name] = pixmap
            except Exception as e:
                print(f"Could not convert lump {lump_name} to pixmap: {e}")
                pixmap = None

        painter.save()

        # Draw background if selected
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Define cell geometry
        cell_width = 100
        image_height = 80
        text_height = 20

        # Scale and draw icon
        if pixmap:
            scaled_pixmap = pixmap.scaled(cell_width, image_height, Qt.KeepAspectRatio, Qt.FastTransformation)
            
            # Center the pixmap
            x = option.rect.left() + (cell_width - scaled_pixmap.width()) / 2
            y = option.rect.top() + (image_height - scaled_pixmap.height()) / 2
            
            painter.drawPixmap(x, y, scaled_pixmap)

        # Draw text
        text_rect = QRect(option.rect.left(), option.rect.top() + image_height, cell_width, text_height)
        painter.drawText(text_rect, Qt.AlignCenter, lump_name)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(100, 100)


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


def lump_to_pixmap(lump) -> QPixmap:
    image = lump.to_Image()
    image = cyan_to_alpha(image)
    return QPixmap(ImageQt(image))


def image_to_pixmap(image) -> QPixmap:
    image = cyan_to_alpha(image)
    return QPixmap(ImageQt(image))


def cyan_to_alpha(image):
    image = image.convert("RGBA")

    data = image.getdata()
    newdata = []
    for item in data:
        if item[0] == 255 and item[1] == 0 and item[2] == 255:
            newdata.append((255, 0, 255, 0))
        else:
            newdata.append(item)
    image.putdata(newdata)

    return image


class View(QObject):
    elementRemoved = Signal(dict)

    def __init__(self, model):
        QObject.__init__(self)
        self.model = model
        self.scene = QGraphicsScene()
        self.main_window = MainWindow()
        self.edit_cond_dialog = EditCond(self.main_window)
        self.lumps_dialog = LumpsDialog(self.main_window)

        self.main_window.ui.graphicsView.setScene(self.scene)

        self.main_window.ui.removeElem.setEnabled(False)
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.main_window.ui.removeElem.clicked.connect(self.remove_selected_element)

    def on_selection_changed(self):
        if shiboken6.isValid(self.scene):
            selected_items = self.scene.selectedItems()
            self.main_window.ui.removeElem.setEnabled(len(selected_items) > 0)

    def remove_selected_element(self):
        selected_items = self.scene.selectedItems()
        if selected_items:
            self.elementRemoved.emit(selected_items[0].to_dict())

    def clear_scene(self):
        for item in self.scene.items():
            self.scene.removeItem(item)

    def draw(self, barindex: int, update: Callable):
        self.clear_scene()
        self.update_properties = update
        
        if self.model.sbardef is None:
            return

        statusbar = self.model.sbardef["data"]["statusbars"][barindex]

        self.screenheight = statusbar["height"]

        rect = QRect(0, 0, SCREENWIDTH, self.screenheight)
        self.scene.setSceneRect(rect)
        item = QGraphicsRectItem(rect)
        item.setBrush(QColor(255, 0, 255, 255))
        self.scene.addItem(item)

        if statusbar["children"] is not None:
            for child in statusbar["children"]:
                self.draw_elem(0, 0, child)

    def draw_elem(self, x: int, y: int, elem: dict):
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
                pixmap = lump_to_pixmap(lump)
                self.add_to_scene(x, y, values, pixmap)

        elif type == "number" or type == "percent":
            for font in self.model.numberfonts:
                if font.name == values["font"]:
                    numtype = values["type"]
                    num = 100
                    if numtype == sbn.health:
                        num = self.model.health
                    elif numtype == sbn.armor:
                        num = self.model.armor
                    pixmap = image_to_pixmap(
                        font.get_pixmap(
                            elem=values,
                            pct=True if type == "percent" else False,
                            val=num,
                        )
                    )
                    self.add_to_scene(x, y, values, pixmap)

        elif type == "face":
            lump = self.model.lumps["STFST00"]
            if lump is not None:
                x -= lump.x_offset
                y -= lump.y_offset
                pixmap = lump_to_pixmap(lump)
                self.add_to_scene(x, y, values, pixmap)

        if values["children"] is not None:
            for child in values["children"]:
                self.draw_elem(x, y, child)

    def add_to_scene(self, x: int, y: int, elem: dict, pixmap: QPixmap):
        alignment = elem["alignment"]

        item = SBarElem(x, y, elem=elem, screenheight=self.screenheight, pixmap=pixmap)

        item.updateElem.connect(self.update_properties)

        if alignment & Alignment.h_middle:
            x -= pixmap.width() / 2
        elif alignment & Alignment.h_right:
            x -= pixmap.width()
        if alignment & Alignment.v_middle:
            y -= pixmap.height() / 2
        elif alignment & Alignment.v_bottom:
            y -= pixmap.height()

        item.setPos(QPointF(x, y))
        self.scene.addItem(item)
