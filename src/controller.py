import json
from PySide6.QtWidgets import QComboBox, QPushButton, QTreeWidgetItem, QFileDialog
from PySide6.QtCore import Qt, Slot, QPointF

from view import SBarCondItem, LumpModel


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
        self.view.main_window.openJSONFile.connect(self.open_json_file)
        self.view.main_window.openWadFile.connect(self.open_wad_file)
        self.view.main_window.saveAsFile.connect(self.save_as_file)
        self.view.main_window.showLumps.connect(self.show_lumps)
        self.view.lumps_dialog.lumpSelected.connect(self.add_graphic_element)
        self.view.elementRemoved.connect(self.remove_data_element)

        self.prop = self.view.main_window.ui.treeProp
        self.prop.setColumnCount(2)
        self.prop.setHeaderLabels(["Key", "Value"])

        self.cond = self.view.main_window.ui.treeCond
        self.cond.setColumnCount(2)
        self.cond.setHeaderLabels(["Condition", "Param"])
        self.cond.itemChanged.connect(self.update_conditions)

        self.conddlg = self.view.edit_cond_dialog
        self.editcond = self.conddlg.dlg.treeWidget

        self.populate_statusbar_combo()
        self.populate_conditions()

    def populate_statusbar_combo(self):
        statusbar_combo = self.view.main_window.ui.comboBox
        statusbar_combo.clear()
        for statusbar in self.model.sbardef["data"]["statusbars"]:
            if statusbar["fullscreenrender"] is True:
                statusbar_combo.addItem("Fullscreen")
            else:
                statusbar_combo.addItem("Statusbar")

    def populate_subtree(self, index: int, name: str, items: list) -> int:
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

    def populate_combo(self, combo: QComboBox, name: str, items: list):
        item = QTreeWidgetItem([name])
        for name, value in items:
            combo.addItem(name)
        combo.currentIndexChanged.connect(self.update_combo)
        self.cond.insertTopLevelItem(0, item)
        self.cond.setItemWidget(item, 1, combo)

    def populate_conditions(self):
        index = 0
        index = self.populate_subtree(index, "Ammo", self.model.ammo_items)
        index = self.populate_subtree(index, "Weapons", self.model.weapon_items)
        index = self.populate_subtree(index, "Slots", self.model.slot_items)

        for name, value in self.model.other_items:
            item = SBarCondItem([name], index)
            item.setCheckState(
                1, Qt.CheckState.Checked if value == 1 else Qt.CheckState.Unchecked
            )
            self.cond.insertTopLevelItem(0, item)
            index += 1

        self.comboWeap = QComboBox()
        self.populate_combo(self.comboWeap, "Selected Weapon", self.model.weapon_items)

        self.comboSlot = QComboBox()
        self.populate_combo(self.comboSlot, "Selected Slot", self.model.slot_items)

        self.comboSession = QComboBox()
        self.populate_combo(self.comboSession, "Session Type", self.model.session_items)

        self.comboGameMode = QComboBox()
        self.populate_combo(self.comboGameMode, "Game Mode", self.model.gamemode_items)
        self.comboGameMode.setCurrentIndex(self.model.gamemode_current)

    def update_combo(self):
        self.model.weapon_selected = self.comboWeap.currentIndex()
        self.model.slot_selected = self.comboSlot.currentIndex()
        self.model.session_current = self.comboSession.currentIndex()
        self.model.gamemode_current = self.comboGameMode.currentIndex()

        self.draw(self.barindex)

    def update_conditions(self, item: SBarCondItem):
        self.model.conditions[item.cond][1] = (
            1 if item.checkState(1) == Qt.CheckState.Checked else 0
        )
        self.draw(self.barindex)

    def update_elem(self, x: int, y: int, elem: dict):
        values = next(iter(elem.values()))

        x += values["x"]
        y += values["y"]

        if "sceneitem" in values:
            values["sceneitem"].setPos(QPointF(x, y))

        if values["children"] is not None:
            for child in values["children"]:
                self.update_elem(x, y, child)

    def populate_edit_cond(self, elem: dict):
        self.editcond.clear()
        item = QTreeWidgetItem([str(elem)])
        self.editcond.insertTopLevelItem(0, item)

    def launch_cond_dialog(self):
        self.conddlg.exec()

    @Slot(dict)
    def update_properties(self, elem: dict):
        self.prop.clear()

        for key, value in elem.items():
            if key != "children":
                item = QTreeWidgetItem([key, str(value)])
                if key == "conditions" and value is not None:
                    button = QPushButton(text="Edit")
                    self.populate_edit_cond(elem=value)
                    button.pressed.connect(self.launch_cond_dialog)
                    self.prop.insertTopLevelItem(0, item)
                    self.prop.setItemWidget(item, 1, button)
                    continue
                self.prop.insertTopLevelItem(0, item)

        if elem["children"] is not None:
            x = elem["x"]
            y = elem["y"]
            for child in elem["children"]:
                self.update_elem(x, y, child)

    def draw(self, barindex: int):
        self.barindex = barindex
        self.view.draw(barindex, self.update_properties)

    def open_json_file(self):
        fileName, _ = QFileDialog.getOpenFileName(self.view.main_window, "Open JSON file", "", "JSON files (*.json)")
        if fileName:
            self.model.load_json(fileName)
            self.populate_statusbar_combo()
            self.draw(0)

    def open_wad_file(self):
        fileName, _ = QFileDialog.getOpenFileName(self.view.main_window, "Open WAD file", "", "WAD files (*.wad)")
        if fileName:
            self.model.load_wad(fileName)
            self.populate_statusbar_combo()
            self.draw(0)

    def save_as_file(self):
        fileName, _ = QFileDialog.getSaveFileName(self.view.main_window, "Save SBARDEF as...", "", "JSON files (*.json)")
        if fileName:
            with open(fileName, 'w') as f:
                json.dump(self.model.sbardef, f, indent=2)

    def show_lumps(self):
        lumps = self.model.lumps
        if lumps:
            model = LumpModel(lumps)
            self.view.lumps_dialog.setModel(model)
        self.view.lumps_dialog.show()

    def add_graphic_element(self, lump_name):
        new_element = {
            "graphic": {
                "x": 0,
                "y": 0,
                "patch": lump_name,
                "alignment": 0,
                "conditions": None,
                "children": None
            }
        }

        statusbar = self.model.sbardef["data"]["statusbars"][self.barindex]
        if statusbar["children"] is None:
            statusbar["children"] = []
        statusbar["children"].append(new_element)

        self.draw(self.barindex)

    def remove_data_element(self, elem_data: dict):

        def find_and_remove(parent, elem_to_remove):
            if "children" in parent and parent["children"] is not None:
                for i, child in enumerate(parent["children"]):
                    elem = next(iter(child.values()))
                    if elem == elem_to_remove:
                        del parent["children"][i]
                        return True
                    if find_and_remove(elem, elem_to_remove):
                        return True
            return False

        find_and_remove(self.model.sbardef["data"]["statusbars"][self.barindex], elem_data)

        self.draw(self.barindex)
