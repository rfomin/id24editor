from PySide6.QtCore import QObject, Signal, Slot, Qt, QRect, QPointF
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsSceneMouseEvent,
    QTreeWidget,
    QTreeWidgetItem,
)
from PySide6.QtGui import QPixmap, QColor

from PIL import Image
from PIL.ImageQt import ImageQt
from omg import WAD

import json

SCREENWIDTH = 320
SCREENHEIGHT = 200


class Alignment:
    h_left = 0x00
    h_middle = 0x01
    h_right = 0x02
    h_mask = 0x03
    v_top = 0x00
    v_middle = 0x04
    v_bottom = 0x08
    v_mask = 0x0C


def clamp(smallest, largest, n):
    return max(smallest, min(n, largest))


def cyanToAlpha(image: Image.Image) -> Image.Image:
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


def lumpToPixmap(lump) -> QPixmap:
    image = lump.to_Image()
    image = cyanToAlpha(image)
    return QPixmap(ImageQt(image))


def imageToPixmap(image: Image.Image) -> QPixmap:
    image = cyanToAlpha(image)
    return QPixmap(ImageQt(image))


class NumberFont:
    def __init__(self, name: str):
        self.name = name
        self.numbers = []
        self.maxwidth = 0
        self.maxheight = 0
        self.minus = None
        self.percent = None

    def addNumber(self, image: Image.Image):
        self.numbers.append(cyanToAlpha(image))
        self.maxwidth = max(self.maxwidth, image.width)
        self.maxheight = max(self.maxheight, image.height)

    def addMinus(self, image: Image.Image):
        self.minus = cyanToAlpha(image)

    def addPercent(self, image: Image.Image):
        self.percent = cyanToAlpha(image)

    def getPixmap(self, elem: dict, pct: bool) -> QPixmap:
        maxlength = int(elem["maxlength"])
        totalwidth = self.maxwidth * maxlength

        if pct is True and self.percent is not None:
            totalwidth += self.percent.width

        image = Image.new("RGBA", (totalwidth, self.maxheight))
        number = self.numbers[0]
        for i in range(0, maxlength):
            image.paste(number, (i * number.width, 0))

        if pct is True and self.percent is not None:
            image.paste(self.percent, (totalwidth - self.percent.width, 0))

        return QPixmap(ImageQt(image))


class SBarElem(QObject, QGraphicsPixmapItem):
    updateElem = Signal(dict)

    def __init__(self, x: int, y: int, elem: dict, screenheight: int, pixmap: QPixmap):
        QObject.__init__(self)
        QGraphicsPixmapItem.__init__(self, pixmap)

        self.elem = elem
        self.x_diff = x - elem["x"]
        self.y_diff = y - elem["y"]
        self.screenheight = screenheight
        self.setFlags(
            self.flags()
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
        )

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
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
            x += width >> 1
        elif alignment & Alignment.h_right:
            x += width
        if alignment & Alignment.v_middle:
            y += height >> 1
        elif alignment & Alignment.v_bottom:
            y += height

        self.elem["x"] = x - self.x_diff
        self.elem["y"] = y - self.y_diff

        self.updateElem.emit(self.elem)

        return super().mouseReleaseEvent(event)


class SBarDef:
    def __init__(
        self,
        scene: QGraphicsScene,
        prop: QTreeWidget,
        cond: QTreeWidget,
        combo: QComboBox,
        wad: WAD,
    ):
        self.scene = scene

        prop.setColumnCount(2)
        prop.setHeaderLabels(["Key", "Value"])
        self.prop = prop

        cond.setColumnCount(2)
        cond.setHeaderLabels(["Condition", "Param"])
        item = QTreeWidgetItem(["Compact"], 0)
        item.setCheckState(1, Qt.Unchecked)
        cond.insertTopLevelItem(0, item)
        self.cond = cond

        self.combo = combo

        self.wad = wad
        self.lumps = wad.graphics + wad.patches + wad.sprites

        self.sbardef = json.loads(self.wad.data["SBARDEF"].data)

        for statusbar in self.sbardef["data"]["statusbars"]:
            if statusbar["fullscreenrender"] is True:
                self.combo.addItem("Fullscreen")
            else:
                self.combo.addItem("Statusbar")

        self.loadFonts()

    def loadFonts(self):
        self.numberfonts = []

        for numberfont in self.sbardef["data"]["numberfonts"]:
            font = NumberFont(numberfont["name"])
            stem = numberfont["stem"]

            for num in range(0, 10):
                name = stem + "NUM" + str(num)
                if name in self.lumps:
                    font.addNumber(self.lumps[name].to_Image())

            name = stem + "MINUS"
            if name in self.lumps:
                font.addMinus(self.lumps[name].to_Image())

            name = stem + "PRCNT"
            if name in self.lumps:
                font.addPercent(self.lumps[name].to_Image())

            self.numberfonts.append(font)

    def updateElem(self, x: int, y: int, elem: dict):
        values = next(iter(elem.values()))

        x += values["x"]
        y += values["y"]

        values["sceneitem"].setPos(QPointF(x, y))

        if values["children"] is not None:
            for child in values["children"]:
                self.updateElem(x, y, child)

    @Slot(dict)
    def update(self, elem: dict):
        items = []
        for key, value in elem.items():
            if key != "sceneitem" and key != "children":
                item = QTreeWidgetItem([key, str(value)])
                items.append(item)
        self.prop.clear()
        self.prop.insertTopLevelItems(0, items)

        if elem["children"] is not None:
            x = elem["x"]
            y = elem["y"]
            for child in elem["children"]:
                self.updateElem(x, y, child)

    def addToScene(self, x: int, y: int, elem: dict, pixmap: QPixmap):
        alignment = elem["alignment"]

        item = SBarElem(x, y, elem=elem, screenheight=self.screenheight, pixmap=pixmap)

        item.updateElem.connect(self.update)

        if alignment & Alignment.h_middle:
            x -= pixmap.width() >> 1
        elif alignment & Alignment.h_right:
            x -= pixmap.width()
        if alignment & Alignment.v_middle:
            y -= pixmap.height() >> 1
        elif alignment & Alignment.v_bottom:
            y -= pixmap.height()

        item.setPos(QPointF(x, y))
        elem["sceneitem"] = item
        self.scene.addItem(item)

    def drawElem(self, x: int, y: int, elem: dict):
        type = next(iter(elem))
        values = next(iter(elem.values()))

        x += values["x"]
        y += values["y"]

        if type == "graphic":
            patch = values["patch"]
            if patch in self.lumps:
                lump = self.lumps[patch]
                x -= lump.x_offset
                y -= lump.y_offset
                pixmap = lumpToPixmap(lump)
                self.addToScene(x, y, values, pixmap)

        elif type == "number" or type == "percent":
            for font in self.numberfonts:
                if font.name == values["font"]:
                    pixmap = font.getPixmap(
                        values, pct=True if type == "percent" else False
                    )
                    self.addToScene(x, y, values, pixmap)

        elif type == "face":
            lump = self.lumps["STFST00"]
            if lump is not None:
                x -= lump.x_offset
                y -= lump.y_offset
                pixmap = lumpToPixmap(lump)
                self.addToScene(x, y, values, pixmap)

        if values["children"] is not None:
            for child in values["children"]:
                self.drawElem(x, y, child)

    def draw(self, barindex: int):
        self.scene.clear()

        statusbar = self.sbardef["data"]["statusbars"][barindex]

        self.screenheight = statusbar["height"]

        rect = QRect(0, 0, SCREENWIDTH, self.screenheight)
        self.scene.setSceneRect(rect)
        item = QGraphicsRectItem(rect)
        item.setBrush(QColor(255, 0, 255, 255))
        self.scene.addItem(item)

        if statusbar["children"] is not None:
            for child in statusbar["children"]:
                self.drawElem(0, 0, child)
