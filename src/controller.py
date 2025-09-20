from PySide6.QtWidgets import QComboBox, QPushButton, QTreeWidgetItem, QFileDialog
from PySide6.QtCore import Qt, Slot, QPointF

from view import SBarCondItem


class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.barindex = 0

        self.view.main_window.ui.comboBox.currentIndexChanged.connect(self.draw)
        self.view.main_window.ui.horizontalSlider.valueChanged.connect(
            self.view.main_window.updateScale
        )
        self.view.main_window.updateScale(200)
        self.view.main_window.openWadFile.connect(self.open_wad_file)

        self.prop = self.view.main_window.ui.treeProp
        self.prop.setColumnCount(2)
        self.prop.setHeaderLabels(["Key", "Value"])

        self.cond = self.view.main_window.ui.treeCond
        self.cond.setColumnCount(2)
        self.cond.setHeaderLabels(["Condition", "Param"])
        self.cond.itemChanged.connect(self.updateConditions)

        self.dlg = self.view.edit_cond_dialog
        self.editcond = self.view.edit_cond_dialog.dlg.treeWidget

        self.populate_statusbar_combo()
        self.populate_conditions()

    def populate_statusbar_combo(self):
        for statusbar in self.model.sbardef["data"]["statusbars"]:
            if statusbar["fullscreenrender"] is True:
                self.view.main_window.ui.comboBox.addItem("Fullscreen")
            else:
                self.view.main_window.ui.comboBox.addItem("Statusbar")

    def populateSubTree(self, index: int, name: str, items: list) -> int:
        parent = QTreeWidgetItem([name])
        for name, value in items:
            item = SBarCondItem([name], index)
            item.setCheckState(
                1, Qt.CheckState.Checked if value == 1 else Qt.CheckState.Unchecked
            )
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

    def populate_conditions(self):
        index = 0
        index = self.populateSubTree(index, "Ammo", self.model.ammo_items)
        index = self.populateSubTree(index, "Weapons", self.model.weapon_items)
        index = self.populateSubTree(index, "Slots", self.model.slot_items)

        for name, value in self.model.other_items:
            item = SBarCondItem([name], index)
            item.setCheckState(
                1, Qt.CheckState.Checked if value == 1 else Qt.CheckState.Unchecked
            )
            self.cond.insertTopLevelItem(0, item)
            index += 1

        self.comboWeap = QComboBox()
        self.populateCombo(self.comboWeap, "Selected Weapon", self.model.weapon_items)

        self.comboSlot = QComboBox()
        self.populateCombo(self.comboSlot, "Selected Slot", self.model.slot_items)

        self.comboSession = QComboBox()
        self.populateCombo(self.comboSession, "Session Type", self.model.session_items)

        self.comboGameMode = QComboBox()
        self.populateCombo(self.comboGameMode, "Game Mode", self.model.gamemode_items)
        self.comboGameMode.setCurrentIndex(self.model.gamemode_current)

    def updateCombo(self):
        self.model.weapon_selected = self.comboWeap.currentIndex()
        self.model.slot_selected = self.comboSlot.currentIndex()
        self.model.session_current = self.comboSession.currentIndex()
        self.model.gamemode_current = self.comboGameMode.currentIndex()

        self.draw(self.barindex)

    def updateConditions(self, item: SBarCondItem):
        self.model.conditions[item.cond][1] = (
            1 if item.checkState(1) == Qt.CheckState.Checked else 0
        )
        self.draw(self.barindex)

    def updateElem(self, x: int, y: int, elem: dict):
        values = next(iter(elem.values()))

        x += values["x"]
        y += values["y"]

        if "sceneitem" in values:
            values["sceneitem"].setPos(QPointF(x, y))

        if values["children"] is not None:
            for child in values["children"]:
                self.updateElem(x, y, child)

    def populateEditCond(self, elem: dict):
        self.editcond.clear()
        item = QTreeWidgetItem([str(elem)])
        self.editcond.insertTopLevelItem(0, item)

    def launchDialog(self):
        self.dlg.exec()

    @Slot(dict)
    def update(self, elem: dict):
        self.prop.clear()

        for key, value in elem.items():
            if key != "sceneitem" and key != "children":
                item = QTreeWidgetItem([key, str(value)])
                if key == "conditions" and value is not None:
                    button = QPushButton(text="Edit")
                    self.populateEditCond(elem=value)
                    button.pressed.connect(self.launchDialog)
                    self.prop.insertTopLevelItem(0, item)
                    self.prop.setItemWidget(item, 1, button)
                    continue
                self.prop.insertTopLevelItem(0, item)

        if elem["children"] is not None:
            x = elem["x"]
            y = elem["y"]
            for child in elem["children"]:
                self.updateElem(x, y, child)

    def draw(self, barindex: int):
        self.barindex = barindex
        self.view.draw(barindex, self.update)

    def open_wad_file(self):
        fileName, _ = QFileDialog.getOpenFileName(self.view.main_window, "Open WAD file", "", "WAD files (*.wad)")
        if fileName:
            self.model.load_wad(fileName)
            self.populate_statusbar_combo()
            self.draw(0)
