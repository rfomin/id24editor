import json
import omg

from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtCore import QObject, QPointF, QRect, Qt, Signal, Slot
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSceneMouseEvent,
    QTreeWidget,
    QTreeWidgetItem,
)

import doomdata
from doomdata import (
    Alignment,
    Ammo,
    Weapon,
    Slots,
    Session,
    GameMode,
    sbc
)


def checkConditions(elem: dict[str, object]) -> bool:
    result = True
    if elem["conditions"] is not None:
        for condition in elem["conditions"]:
            cond = condition["condition"]
            param = condition["param"]

            if cond == sbc.weaponowned:
                result &= Weapon.items[param][1]

            elif cond == sbc.weaponselected:
                result &= Weapon.selected== param

            elif cond == sbc.weaponnotselected:
                result &= Weapon.selected!= param

            elif cond == sbc.weaponhasammo:
                result &= Ammo.weapon[param] != Ammo.noammo

            elif cond == sbc.selectedweaponhasammo:
                result &= Ammo.weapon[Weapon.selected] != Ammo.noammo

            elif cond == sbc.selectedweaponammotype:
                result &= Ammo.weapon[Weapon.selected] == param

            elif cond == sbc.weaponslotowned:
                result &= Slots.items[Slots.weapon[param - 1] - 1][1]

            elif cond == sbc.weaponslotnotowned:
                result &= not Slots.items[Slots.weapon[param - 1] - 1][1]

            elif cond == sbc.weaponslotselected:
                result &= Slots.selected == param

            elif cond == sbc.weaponslotnotselected:
                result &= Slots.selected != param

            elif cond == sbc.sessiontypeeequal:
                result &= Session.current == param

            elif cond == sbc.sessiontypenotequal:
                result &= Session.current != param

            elif cond == sbc.modeeequal:
                result &= GameMode.current == param

            elif cond == sbc.modenotequal:
                result &= GameMode.current != param

            elif cond == sbc.hudmodeequal:
                result &= doomdata.other[0][1] == param

    return result


def clamp(smallest, largest, n):
    return max(smallest, min(n, largest))


def cyanToAlpha(image: Image) -> Image:
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


def imageToPixmap(image: Image) -> QPixmap:
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

    def addNumber(self, image: Image):
        self.numbers.append(cyanToAlpha(image))
        self.maxwidth = max(self.maxwidth, image.width)
        self.maxheight = max(self.maxheight, image.height)

    def addMinus(self, image: Image):
        self.minus = cyanToAlpha(image)

    def addPercent(self, image: Image):
        self.percent = cyanToAlpha(image)

    def getPixmap(self, elem: dict[str, object], pct: bool) -> QPixmap:
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

    def __init__(
        self,
        x: int,
        y: int,
        elem: dict[str, object],
        screenheight: int,
        pixmap: QPixmap,
    ):
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
            x = clamp(0, doomdata.SCREENWIDTH - width + 1, x)
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


class SBarCondItem(QTreeWidgetItem):
    def __init__(self, strings: list[str], cond: int):
        QTreeWidgetItem.__init__(self, strings)
        self.cond = cond


class SBarDef:
    def __init__(
        self,
        scene: QGraphicsScene,
        prop: QTreeWidget,
        cond: QTreeWidget,
        combo: QComboBox,
        wad: omg.WAD,
    ):
        self.scene = scene
        self.combo = combo
        self.wad = wad

        self.lumps = wad.graphics + wad.patches + wad.sprites

        self.sbardef = json.loads(self.wad.data["SBARDEF"].data)

        for statusbar in self.sbardef["data"]["statusbars"]:
            if statusbar["fullscreenrender"] is True:
                self.combo.addItem("Fullscreen")
            else:
                self.combo.addItem("Statusbar")
        self.barindex = 0

        self.loadFonts()

        prop.setColumnCount(2)
        prop.setHeaderLabels(["Key", "Value"])
        self.prop = prop

        cond.setColumnCount(2)
        cond.setHeaderLabels(["Condition", "Param"])
        cond.itemChanged.connect(self.updateConditions)
        self.cond = cond
        self.populateConditions()

    def populateSubTree(self, index: int, name: str, items: list) -> int:
        parent = QTreeWidgetItem([name])
        for name, value in items:
            item = SBarCondItem([name], index)
            item.setCheckState(1, Qt.Checked if value == 1 else Qt.Unchecked)
            parent.addChild(item)
            index += 1
        self.cond.insertTopLevelItem(0, parent)
        return index

    def populateCombo(self, combo: QComboBox, name: str, items: list):
        item = QTreeWidgetItem([name])
        for name, value in items:
            combo.addItem(name)
        combo.currentIndexChanged.connect(self.updateCombo)
        self.cond.insertTopLevelItem(0, item)
        self.cond.setItemWidget(item, 1, combo)

    def populateConditions(self):
        index = 0
        index = self.populateSubTree(index, "Ammo", Ammo.items)
        index = self.populateSubTree(index, "Weapons", Weapon.items)
        index = self.populateSubTree(index, "Slots", Slots.items)

        for name, value in doomdata.other:
            item = SBarCondItem([name], index)
            item.setCheckState(1, Qt.Checked if value == 1 else Qt.Unchecked)
            self.cond.insertTopLevelItem(0, item)
            index += 1

        self.comboWeap = QComboBox()
        self.populateCombo(self.comboWeap, "Selected Weapon", Weapon.items)

        self.comboSlot = QComboBox()
        self.populateCombo(self.comboSlot, "Selected Slot", Slots.items)

        self.comboSession = QComboBox()
        self.populateCombo(self.comboSession, "Session Type", Session.items)

        self.comboGameMode = QComboBox()
        self.populateCombo(self.comboGameMode, "Game Mode", GameMode.items)
        self.comboGameMode.setCurrentIndex(GameMode.current)

    def updateCombo(self):
        Weapon.selected= self.comboWeap.currentIndex()
        Slots.selected = self.comboSlot.currentIndex()
        Session.current = self.comboSession.currentIndex()
        GameMode.current = self.comboGameMode.currentIndex()

        self.draw(self.barindex)

    def updateConditions(self, item: SBarCondItem):
        doomdata.conditions[item.cond][1] = 1 if item.checkState(1) == Qt.Checked else 0
        self.draw(self.barindex)

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

    def updateElem(self, x: int, y: int, elem: dict[str, object]):
        values = next(iter(elem.values()))

        x += values["x"]
        y += values["y"]

        values["sceneitem"].setPos(QPointF(x, y))

        if values["children"] is not None:
            for child in values["children"]:
                self.updateElem(x, y, child)

    @Slot(dict)
    def update(self, elem: dict[str, object]):
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

    def addToScene(self, x: int, y: int, elem: dict[str, object], pixmap: QPixmap):
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

    def drawElem(self, x: int, y: int, elem: dict[str, object]):
        type = next(iter(elem))
        values = next(iter(elem.values()))

        if checkConditions(values) is False:
            return

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
        self.barindex = barindex
        self.scene.clear()

        statusbar = self.sbardef["data"]["statusbars"][barindex]

        self.screenheight = statusbar["height"]

        rect = QRect(0, 0, doomdata.SCREENWIDTH, self.screenheight)
        self.scene.setSceneRect(rect)
        item = QGraphicsRectItem(rect)
        item.setBrush(QColor(255, 0, 255, 255))
        self.scene.addItem(item)

        if statusbar["children"] is not None:
            for child in statusbar["children"]:
                self.drawElem(0, 0, child)
