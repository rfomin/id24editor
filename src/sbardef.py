import json

from omg import WAD
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


sbc_weaponowned = 0
sbc_weaponselected = 1
sbc_weaponnotselected = 2
sbc_weaponhasammo = 3
sbc_selectedweaponhasammo = 4
sbc_selectedweaponammotype = 5
sbc_weaponslotowned = 6
sbc_weaponslotnotowned = 7
sbc_weaponslotselected = 8
sbc_weaponslotnotselected = 9
sbc_itemowned = 10
sbc_itemnotowned = 11
sbc_featurelevelgreaterequal = 12
sbc_featurelevelless = 13
sbc_sessiontypeeequal = 14
sbc_sessiontypenotequal = 15
sbc_modeeequal = 16
sbc_modenotequal = 17
sbc_hudmodeequal = 18

wp_fist = 0
wp_pistol = 1
wp_shotgun = 2
wp_chaingun = 3
wp_missile = 4
wp_plasma = 5
wp_bfg = 6
wp_chainsaw = 7
wp_supershotgun = 8

weapons = [
    ["First", 1],
    ["Pistol", 1],
    ["Shotgun", 1],
    ["Chaingun", 1],
    ["Rocket Launcher", 1],
    ["Plasmagun", 1],
    ["BFG", 1],
    ["Chainsaw", 1],
    ["Super Shotgun", 1],
]

am_clip  = 0  # Pistol / chaingun ammo.
am_shell = 1  # Shotgun / double barreled shotgun.
am_cell = 2   # Plasma rifle, BFG.
am_misl = 3   # Missile launcher.
am_noammo = 5

ammo = [
    ["Bullets", 1],
    ["Shells", 1],
    ["Cells", 1],
    ["Rockets", 1]
]

slots = [
    ["1", 1],
    ["2", 1],
    ["3", 1],
    ["4", 1],
    ["5", 1],
    ["6", 1],
    ["7", 1]
]

weapons_ammo = (
    am_noammo,
    am_clip,
    am_shell,
    am_clip,
    am_misl,
    am_cell,
    am_cell,
    am_clip,
    am_shell,
)

weapons_slots = (1, 2, 3, 4, 5, 6, 7, 1, 3)

selectedweapon = wp_pistol
selectedslot = 1

singleplayer = 0
cooperative = 1
deathmatch = 2

sessiontype = [
    ["Singleplayer", 1],
    ["Cooperative", 0],
    ["Deathmatch", 0],
]

currentsession = singleplayer

shareware = 0    # DOOM 1 shareware, E1, M9
registered = 1   # DOOM 1 registered, E3, M27
commercial = 2   # DOOM 2 retail, E1 M34 
retail = 3       # DOOM 1 retail, E4, M36
indetermined = 4

gamemode = [
    ["Shareware", 0],
    ["Registered", 0],
    ["Commercial", 1],
    ["Retail", 0],
    ["Indetermined", 0],
]

currentgamemode = commercial

other = [
    ["CompactHUD", 0]
]

conditions = ammo + weapons + slots + other

def checkConditions(elem: dict[str, object]) -> bool:
    result = True
    if elem["conditions"] is not None:
        for condition in elem["conditions"]:
            cond = condition["condition"]
            param = condition["param"]

            if cond == sbc_weaponowned:
                result &= weapons[param][1]

            elif cond == sbc_weaponselected:
                result &= selectedweapon == param

            elif cond == sbc_weaponnotselected:
                result &= selectedweapon != param

            elif cond == sbc_weaponhasammo:
                result &= weapons_ammo[param] != am_noammo

            elif cond == sbc_selectedweaponhasammo:
                result &= weapons_ammo[selectedweapon] != am_noammo

            elif cond == sbc_selectedweaponammotype:
                result &= weapons_ammo[selectedweapon] == param

            elif cond == sbc_weaponslotowned:
                result &= slots[weapons_slots[param - 1] - 1][1]

            elif cond == sbc_weaponslotnotowned:
                result &= not slots[weapons_slots[param - 1] - 1][1]

            elif cond == sbc_weaponslotselected:
                result &= selectedslot == param

            elif cond == sbc_weaponslotnotselected:
                result &= selectedslot != param

            elif cond == sbc_sessiontypeeequal:
                result &= currentsession == param

            elif cond == sbc_sessiontypenotequal:
                result &= currentsession != param

            elif cond == sbc_modeeequal:
                result &= currentgamemode == param

            elif cond == sbc_modenotequal:
                result &= currentgamemode != param

            elif cond == sbc_hudmodeequal:
                result &= other[0][1] == param

    return result


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
        wad: WAD,
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
        index = self.populateSubTree(index, "Ammo", ammo)
        index = self.populateSubTree(index, "Weapons", weapons)
        index = self.populateSubTree(index, "Slots", slots)

        for name, value in other:
            item = SBarCondItem([name], index)
            item.setCheckState(1, Qt.Checked if value == 1 else Qt.Unchecked)
            self.cond.insertTopLevelItem(0, item)
            index += 1

        self.comboWeap = QComboBox()
        self.populateCombo(self.comboWeap, "Selected Weapon", weapons)

        self.comboSlot = QComboBox()
        self.populateCombo(self.comboSlot, "Selected Slot", slots)

        self.comboSession = QComboBox()
        self.populateCombo(self.comboSession, "Session Type", sessiontype)

        self.comboGameMode = QComboBox()
        self.populateCombo(self.comboGameMode, "Game Mode", gamemode)
        self.comboGameMode.setCurrentIndex(currentgamemode)

    def updateCombo(self):
        global selectedweapon
        selectedweapon = self.comboWeap.currentIndex()

        global selectedslot
        selectedslot = self.comboSlot.currentIndex()

        global currentsession
        currentsession = self.comboSession.currentIndex()

        global currentgamemode
        currentgamemode = self.comboGameMode.currentIndex()

        self.draw(self.barindex)

    def updateConditions(self, item: SBarCondItem):
        conditions[item.cond][1] = 1 if item.checkState(1) == Qt.Checked else 0
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

        rect = QRect(0, 0, SCREENWIDTH, self.screenheight)
        self.scene.setSceneRect(rect)
        item = QGraphicsRectItem(rect)
        item.setBrush(QColor(255, 0, 255, 255))
        self.scene.addItem(item)

        if statusbar["children"] is not None:
            for child in statusbar["children"]:
                self.drawElem(0, 0, child)
