import json
import omg

from PIL import Image

from doomdata import (
    Ammo,
    Weapon,
    Slots,
    Session,
    GameMode,
    sbc
)


class SBarModel:
    def __init__(self):
        self.wad = omg.WAD()
        self.sbardef = None
        self.lumps = None
        self.numberfonts = []

        self.weapon_items = [
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
        self.ammo_items = [["Bullets", 1], ["Shells", 1], ["Cells", 1], ["Rockets", 1]]
        self.slot_items = [
            ["1", 1],
            ["2", 1],
            ["3", 1],
            ["4", 1],
            ["5", 1],
            ["6", 1],
            ["7", 1],
        ]
        self.session_items = [
            ["Singleplayer", 1],
            ["Cooperative", 0],
            ["Deathmatch", 0],
        ]
        self.gamemode_items = [
            ["Shareware", 0],
            ["Registered", 0],
            ["Commercial", 1],
            ["Retail", 0],
            ["Indetermined", 0],
        ]
        self.other_items = [["CompactHUD", 0]]

        self.conditions = (
            self.ammo_items
            + self.weapon_items
            + self.slot_items
            + self.other_items
        )

        self.weapon_selected = Weapon.pistol
        self.slot_selected = 1
        self.session_current = Session.singleplayer
        self.gamemode_current = GameMode.commercial

    def load_wad(self, path: str):
        self.wad.from_file(path)
        self.lumps = self.wad.graphics + self.wad.patches + self.wad.sprites
        if "SBARDEF" in self.wad.data:
            self.sbardef = json.loads(self.wad.data["SBARDEF"].data)
            self.load_fonts()

    def load_fonts(self):
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

    def check_conditions(self, elem: dict) -> bool:
        result = True
        if elem["conditions"] is not None:
            for condition in elem["conditions"]:
                cond = condition["condition"]
                param = condition["param"]

                if cond == sbc.weaponowned:
                    result &= self.weapon_items[param][1]

                elif cond == sbc.weaponselected:
                    result &= self.weapon_selected == param

                elif cond == sbc.weaponnotselected:
                    result &= self.weapon_selected != param

                elif cond == sbc.weaponhasammo:
                    result &= Ammo.weapon[param] != Ammo.noammo

                elif cond == sbc.selectedweaponhasammo:
                    result &= Ammo.weapon[self.weapon_selected] != Ammo.noammo

                elif cond == sbc.selectedweaponammotype:
                    result &= Ammo.weapon[self.weapon_selected] == param

                elif cond == sbc.weaponslotowned:
                    result &= self.slot_items[Slots.weapon[param - 1] - 1][1]

                elif cond == sbc.weaponslotnotowned:
                    result &= not self.slot_items[Slots.weapon[param - 1] - 1][1]

                elif cond == sbc.weaponslotselected:
                    result &= self.slot_selected == param

                elif cond == sbc.weaponslotnotselected:
                    result &= self.slot_selected != param

                elif cond == sbc.sessiontypeeequal:
                    result &= self.session_current == param

                elif cond == sbc.sessiontypenotequal:
                    result &= self.session_current != param

                elif cond == sbc.modeeequal:
                    result &= self.gamemode_current == param

                elif cond == sbc.modenotequal:
                    result &= self.gamemode_current != param

                elif cond == sbc.hudmodeequal:
                    result &= self.other_items[0][1] == param

        return result


class NumberFont:
    def __init__(self, name: str):
        self.name = name
        self.numbers = []
        self.maxwidth = 0
        self.maxheight = 0
        self.minus = None
        self.percent = None

    def addNumber(self, image):
        self.numbers.append(cyanToAlpha(image))
        self.maxwidth = max(self.maxwidth, image.width)
        self.maxheight = max(self.maxheight, image.height)

    def addMinus(self, image):
        self.minus = cyanToAlpha(image)

    def addPercent(self, image):
        self.percent = cyanToAlpha(image)

    def getPixmap(self, elem: dict, pct: bool):
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

        return image


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
