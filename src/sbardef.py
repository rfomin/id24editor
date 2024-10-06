from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (QComboBox, QGraphicsItem, QGraphicsPixmapItem,
    QGraphicsScene, QGraphicsSceneMouseEvent,
    QTreeWidget, QTreeWidgetItem)
from PySide6.QtGui import QPixmap

from PIL import Image
from PIL.ImageQt import ImageQt
from omg import WAD
import json

SCREENWIDTH  = 320
SCREENHEIGHT = 200

sbe_h_left   = 0x00
sbe_h_middle = 0x01
sbe_h_right  = 0x02
sbe_h_mask   = 0x03
sbe_v_top    = 0x00
sbe_v_middle = 0x04
sbe_v_bottom = 0x08
sbe_v_mask   = 0x0C

def clamp(smallest, largest, n):
    return max(smallest, min(n, largest))

def cyanToAlpha(image: Image.Image) -> Image.Image:
    image = image.convert('RGBA')
    data = image.getdata()
    newData = []
    for item in data:
        if item[0] == 255 and item[1] == 0 and item[2] == 255:
            newData.append((255, 0, 255, 0))
        else:
            newData.append(item)
    image.putdata(newData)
    return image

class SBarElem(QGraphicsPixmapItem):
    def __init__(self, elem: dict, x: int, y: int, screenheight: int,
                 pixmap: QPixmap, tree: QTreeWidget):
        super().__init__(pixmap)
        self.elem = elem
        self.x_diff = x - elem['x']
        self.y_diff = y - elem['y']
        self.screenheight = screenheight
        self.setFlags(self.flags() | QGraphicsItem.ItemIsSelectable
                      | QGraphicsItem.ItemIsMovable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.tree = tree

    def loadElem(self, x, y):
        self.elem['x'] = x - self.x_diff
        self.elem['y'] = y - self.y_diff

        items = []
        for key, value in self.elem.items():
            item = QTreeWidgetItem([key, str(value)])
            items.append(item)
        self.tree.clear()
        self.tree.insertTopLevelItems(0, items)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        x = int(self.x())
        y = int(self.y())
        size = self.boundingRect().size()
        x = clamp(0, SCREENWIDTH - int(size.width()) + 1, x)
        y = clamp(0, self.screenheight - int(size.height()) + 1, y)
        self.loadElem(x, y)
        self.setPos(QPointF(x, y))
        return super().mouseReleaseEvent(event)

class SBarDef:
    def __init__(self, scene: QGraphicsScene, tree: QTreeWidget,
                 combo: QComboBox, wad: WAD):
        self.scene = scene
        self.tree = tree
        self.combo = combo
        self.wad = wad
        self.lumps = wad.graphics + wad.patches + wad.sprites

        self.sbardef = json.loads(self.wad.data['SBARDEF'].data)
        for statusbar in self.sbardef['data']['statusbars']:
            if statusbar['fullscreenrender'] is True:
                self.combo.addItem('Fullscreen')
            else:
                self.combo.addItem('Statusbar')

    def addToScene(self, x, y, elem):
        alignment = elem['alignment']

        if 'patch' in elem:
            name = elem['patch']
            if name in self.lumps:
                image = self.lumps[name].to_Image()
                image = cyanToAlpha(image)
                pixmap = QPixmap(ImageQt(image))
                item = SBarElem(elem, x, y, self.screenheight, pixmap, self.tree)

                width, height = image.size
                if alignment & sbe_h_middle:
                    x -= (width >> 1);
                elif alignment & sbe_h_right:
                    x -= width;
                if alignment & sbe_v_middle:
                    y -= (height >> 1)
                elif alignment & sbe_v_bottom:
                    y -= height

                item.setPos(QPointF(x, y))
                self.scene.addItem(item)

    def drawElem(self, x, y, elem):
        x += elem['x']
        y += elem['y']

        self.addToScene(x, y, elem)

        if elem['children'] is not None:
            for child in elem['children']:
                elem = next(iter(child.values()))
                self.drawElem(x, y, elem)

    def draw(self, barindex: int):
        self.scene.clear()

        statusbar = self.sbardef['data']['statusbars'][barindex]
        self.screenheight = statusbar['height']
        if statusbar['children'] is not None:
            for child in statusbar['children']:
                elem = next(iter(child.values()))
                self.drawElem(0, 0, elem)

        self.scene.setSceneRect(0, 0, SCREENWIDTH, self.screenheight)

    def print(self):
        print(json.dumps(self.sbardef, indent=2))
