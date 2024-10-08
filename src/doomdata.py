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


class sbc:
    weaponowned = 0
    weaponselected = 1
    weaponnotselected = 2
    weaponhasammo = 3
    selectedweaponhasammo = 4
    selectedweaponammotype = 5
    weaponslotowned = 6
    weaponslotnotowned = 7
    weaponslotselected = 8
    weaponslotnotselected = 9
    itemowned = 10
    itemnotowned = 11
    featurelevelgreaterequal = 12
    featurelevelless = 13
    sessiontypeeequal = 14
    sessiontypenotequal = 15
    modeeequal = 16
    modenotequal = 17
    hudmodeequal = 18


class Weapon:
    fist = 0
    pistol = 1
    shotgun = 2
    chaingun = 3
    missile = 4
    plasma = 5
    bfg = 6
    chainsaw = 7
    supershotgun = 8
    selected = pistol

    items = [
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


class Ammo:
    clip = 0  # Pistol / chaingun ammo.
    shell = 1  # Shotgun / double barreled shotgun.
    cell = 2  # Plasma rifle, BFG.
    misl = 3  # Missile launcher.
    noammo = 5

    items = [["Bullets", 1], ["Shells", 1], ["Cells", 1], ["Rockets", 1]]

    weapon = (
        noammo,
        clip,
        shell,
        clip,
        misl,
        cell,
        cell,
        clip,
        shell,
    )


class Slots:
    selected = 1

    items = [["1", 1], ["2", 1], ["3", 1], ["4", 1], ["5", 1], ["6", 1], ["7", 1]]

    weapon = (1, 2, 3, 4, 5, 6, 7, 1, 3)


class Session:
    singleplayer = 0
    cooperative = 1
    deathmatch = 2
    current = singleplayer

    items = [
        ["Singleplayer", 1],
        ["Cooperative", 0],
        ["Deathmatch", 0],
    ]


class GameMode:
    shareware = 0  # DOOM 1 shareware, E1, M9
    registered = 1  # DOOM 1 registered, E3, M27
    commercial = 2  # DOOM 2 retail, E1 M34
    retail = 3  # DOOM 1 retail, E4, M36
    indetermined = 4
    current = commercial

    items = [
        ["Shareware", 0],
        ["Registered", 0],
        ["Commercial", 1],
        ["Retail", 0],
        ["Indetermined", 0],
    ]


other = [["CompactHUD", 0]]

conditions = Ammo.items + Weapon.items + Slots.items + other
