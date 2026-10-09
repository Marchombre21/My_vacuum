# Plan d'implantation d'Aspi pour FreeCAD.
#
# Crée un NOUVEAU document (ne touche pas aux fichiers de Bureau\Modèles).
# Dans FreeCAD : Fichier > Ouvrir ce fichier .py, puis Macro > Exécuter la macro (Ctrl+F6).
# Pour changer une taille ou une position : modifier les nombres ci-dessous et relancer.
#
# Repère (le même que ROS, pour reprendre les positions telles quelles dans l'URDF) :
#   origine = au sol, sous le milieu de l'axe des roues
#   x = vers l'avant, y = vers la gauche, z = vers le haut. Unités : mm.

import math

import FreeCAD as App
import Part

V = App.Vector

# ---------------------------------------------------------------- Dimensions
# Coque (Base.FCStd)
BODY_R = 125.0          # rayon extérieur
WALL = 5.0              # épaisseur de paroi
BODY_H = 150.0          # hauteur du dessus de la coque
FLOOR_T = 3.0           # épaisseur du plancher et de l'étage
DECK_Z = 70.0           # hauteur de l'étage (dessous) qui porte Pi, ESP32, IMU

# Roues motrices (Roue_motrice.FCStd, diamètre mesuré : 67)
WHEEL_D = 67.0
WHEEL_W = 27.0
DRIVE_MOTOR_D = 25.0
DRIVE_MOTOR_L = 69.0
WHEEL_GAP = 2.0         # jeu entre le pneu et l'intérieur de la paroi

# Roue folle pivotante, montée par le dessus : sa platine est vissée SUR le plancher
# et la partie qui pivote passe par un trou. Sa hauteur fixe celle du plancher.
CASTER_H = 20.0                 # du sol au dessus de la platine
CASTER_PLATE = (26.0, 22.0, 1.0)    # x, y, épaisseur
CASTER_SCREWS = (20.0, 15.0)    # écart des trous de vis (centre à centre), en x et en y
CASTER_SCREW_D = 2.5            # diamètre des trous de vis (à vérifier)
CASTER_NECK_D = 19.0            # pièce ronde entre la platine et la roue
CASTER_HOLE_D = 20.0            # trou dans le plancher
CASTER_SWEEP_D = 32.0           # cercle balayé par la roue en pivotant (estimé)
CASTER_SWEEP_TOP = 13.0         # hauteur du haut de la partie qui balaie (mesuré : 12-13)
CASTER_X = 95.0

# Aspiration (moteur pas encore reçu : longueur provisoire)
SUCTION_D = 30.0
SUCTION_L = 60.0
FILTER_T = 8.0
BIN_HALF_W = 60.0       # demi-largeur du bac (en y)
BIN_BOTTOM = 5.0        # hauteur du dessous du bac (la fente d'aspiration)
BIN_TOP = DECK_Z - 2.0

# Pièces posées : (fichier d'origine, dimensions x, y, z, centre x, centre y)
# Sur le plancher :
FLOOR_PARTS = {
    'Batterie': ((37.0, 66.0, 35.0), 55.0, 0.0),        # couchée, en travers
    'L298N': ((43.0, 43.0, 27.0), 60.0, 60.0),
    'Convertisseur': ((63.0, 30.0, 12.0), 55.0, -60.0),
}
# Sur l'étage :
DECK_PARTS = {
    'Raspberry_Pi': ((57.0, 88.0, 18.0), 55.0, 0.0),
    'ESP32': ((28.0, 51.0, 11.0), -55.0, 55.0),
    'IMU': ((15.0, 26.0, 11.0), 0.0, 0.0),             # au centre de rotation
}
# Sur le dessus :
LIDAR = (55.0, 55.0, 42.0)

# Couleurs (r, g, b de 0 à 1) et transparence (0 à 100)
COLORS = {
    'Coque': ((0.85, 0.85, 0.85), 80),
    'Plancher': ((0.6, 0.6, 0.6), 50),
    'Etage': ((0.6, 0.6, 0.6), 60),
    'Bac': ((0.3, 0.6, 1.0), 40),
    'Filtre': ((1.0, 1.0, 1.0), 0),
    'Moteur_aspiration': ((1.0, 0.5, 0.0), 0),
    'Batterie': ((0.1, 0.5, 0.1), 0),
    'LIDAR': ((0.1, 0.1, 0.1), 0),
}
DEFAULT_COLOR = ((0.8, 0.2, 0.2), 0)


# ---------------------------------------------------------------- Calculs
FLOOR_Z = CASTER_H - CASTER_PLATE[2] - FLOOR_T     # dessous du plancher
INNER_R = BODY_R - WALL
WHEEL_R = WHEEL_D / 2
# Le pneu est un disque vertical : son coin le plus loin du centre est à
# (rayon de roue, bord extérieur). Il doit rester dans le cercle intérieur.
WHEEL_OUTER_Y = math.sqrt((INNER_R - WHEEL_GAP) ** 2 - WHEEL_R ** 2)
WHEEL_Y = WHEEL_OUTER_Y - WHEEL_W / 2   # centre du pneu
SUCTION_FRONT_X = -(DRIVE_MOTOR_D / 2 + 3.0)
FILTER_FRONT_X = SUCTION_FRONT_X - SUCTION_L
BIN_FRONT_X = FILTER_FRONT_X - FILTER_T
SUCTION_Z = FLOOR_Z + FLOOR_T + SUCTION_D / 2 + 2.0


def box(size, cx, cy, z):
    sx, sy, sz = size
    return Part.makeBox(sx, sy, sz, V(cx - sx / 2, cy - sy / 2, z))


def cyl(r, h, pnt, axis):
    return Part.makeCylinder(r, h, pnt, axis)


def bin_region(z0, z1, front_x=BIN_FRONT_X):
    """Le volume du bac : l'arrière du robot, derrière le filtre."""
    b = Part.makeBox(BODY_R, 2 * BIN_HALF_W, z1 - z0,
                     V(front_x - BODY_R, -BIN_HALF_W, z0))
    return b.common(cyl(BODY_R, z1 - z0, V(0, 0, z0), V(0, 0, 1)))


def build():
    parts = {}

    shell = cyl(BODY_R, BODY_H - FLOOR_Z, V(0, 0, FLOOR_Z), V(0, 0, 1))
    shell = shell.cut(cyl(INNER_R, BODY_H - FLOOR_Z - FLOOR_T,
                          V(0, 0, FLOOR_Z), V(0, 0, 1)))
    parts['Coque'] = shell.cut(bin_region(BIN_BOTTOM, BIN_TOP))

    floor = cyl(INNER_R, FLOOR_T, V(0, 0, FLOOR_Z), V(0, 0, 1))
    for side in (1, -1):
        well = box((WHEEL_D + 6, WHEEL_W + 6, FLOOR_T), 0, side * WHEEL_Y, FLOOR_Z)
        floor = floor.cut(well)
    # Le plancher s'arrête devant le filtre : bac et filtre descendent jusqu'en bas.
    floor = floor.cut(cyl(CASTER_HOLE_D / 2, FLOOR_T, V(CASTER_X, 0, FLOOR_Z), V(0, 0, 1)))
    for sx in (1, -1):
        for sy in (1, -1):
            floor = floor.cut(cyl(CASTER_SCREW_D / 2, FLOOR_T,
                                  V(CASTER_X + sx * CASTER_SCREWS[0] / 2,
                                    sy * CASTER_SCREWS[1] / 2, FLOOR_Z), V(0, 0, 1)))
    parts['Plancher'] = floor.cut(bin_region(BIN_BOTTOM, BIN_TOP, FILTER_FRONT_X))

    deck = cyl(INNER_R, FLOOR_T, V(0, 0, DECK_Z), V(0, 0, 1))
    parts['Etage'] = deck

    for side, name in ((1, 'gauche'), (-1, 'droite')):
        y_in = side * (WHEEL_Y - WHEEL_W / 2)
        parts['Roue_' + name] = cyl(WHEEL_R, WHEEL_W,
                                    V(0, side * (WHEEL_Y + WHEEL_W / 2), WHEEL_R),
                                    V(0, -side, 0))
        parts['Moteur_roue_' + name] = cyl(DRIVE_MOTOR_D / 2, DRIVE_MOTOR_L,
                                           V(0, y_in, WHEEL_R), V(0, -side, 0))

    # Roue folle : la partie qui balaie (cylindre du cercle balayé), le pivot, la platine.
    plate_z = CASTER_H - CASTER_PLATE[2]
    caster = cyl(CASTER_SWEEP_D / 2, CASTER_SWEEP_TOP, V(CASTER_X, 0, 0), V(0, 0, 1))
    caster = caster.fuse(cyl(CASTER_NECK_D / 2, plate_z - CASTER_SWEEP_TOP,
                             V(CASTER_X, 0, CASTER_SWEEP_TOP), V(0, 0, 1)))
    caster = caster.fuse(box(CASTER_PLATE, CASTER_X, 0, plate_z))
    parts['Roue_folle'] = caster

    parts['Moteur_aspiration'] = cyl(SUCTION_D / 2, SUCTION_L,
                                     V(SUCTION_FRONT_X, 0, SUCTION_Z), V(-1, 0, 0))
    parts['Filtre'] = box((FILTER_T, 2 * BIN_HALF_W, BIN_TOP - BIN_BOTTOM),
                          FILTER_FRONT_X - FILTER_T / 2, 0, BIN_BOTTOM)
    parts['Bac'] = bin_region(BIN_BOTTOM, BIN_TOP)

    for name, (size, cx, cy) in FLOOR_PARTS.items():
        parts[name] = box(size, cx, cy, FLOOR_Z + FLOOR_T)
    for name, (size, cx, cy) in DECK_PARTS.items():
        parts[name] = box(size, cx, cy, DECK_Z + FLOOR_T)

    lidar = box((LIDAR[0], LIDAR[1], 23.0), 0, 0, BODY_H)
    lidar = lidar.fuse(cyl(25.0, LIDAR[2] - 23.0, V(0, 0, BODY_H + 23.0), V(0, 0, 1)))
    parts['LIDAR'] = lidar
    return parts


def show(parts):
    doc = App.newDocument('Aspi_implantation')
    for name, shape in parts.items():
        obj = doc.addObject('Part::Feature', name)
        obj.Shape = shape
        if App.GuiUp:
            color, transparency = COLORS.get(name, DEFAULT_COLOR)
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.Transparency = transparency
    doc.recompute()
    if App.GuiUp:
        import FreeCADGui
        FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
        FreeCADGui.SendMsgToActiveView('ViewFit')
    return doc


def report(parts):
    """Liste les pièces qui se chevauchent, et les positions utiles pour l'URDF."""
    names = list(parts)
    print('--- Chevauchements (volume commun en mm3) ---')
    found = False
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            vol = parts[a].common(parts[b]).Volume
            if vol > 1.0:
                print('  %s / %s : %.0f' % (a, b, vol))
                found = True
    if not found:
        print('  aucun')
    print('--- Positions pour l\'URDF (mm) ---')
    print('  centre des roues : y = +/-%.1f, z = %.1f (écartement %.1f)'
          % (WHEEL_Y, WHEEL_R, 2 * WHEEL_Y))
    print('  plancher : z = %.1f a %.1f' % (FLOOR_Z, FLOOR_Z + FLOOR_T))
    print('  roue folle : x = %.1f' % CASTER_X)
    screw_r = math.hypot(CASTER_SCREWS[0] / 2, CASTER_SCREWS[1] / 2)
    print('  matiere entre le trou de la roue folle et ses vis : %.2f mm'
          % (screw_r - CASTER_HOLE_D / 2 - CASTER_SCREW_D / 2))
    print('  marge sous les moteurs de roue : %.1f mm'
          % (WHEEL_R - DRIVE_MOTOR_D / 2 - (FLOOR_Z + FLOOR_T)))
    print('  marge entre le haut de la partie qui balaie et le plancher : %.1f mm'
          % (FLOOR_Z - CASTER_SWEEP_TOP))
    print('  IMU (centre) : z = %.1f' % (DECK_Z + FLOOR_T + DECK_PARTS['IMU'][0][2] / 2))
    print('  LIDAR (centre de la tete) : z = %.1f' % (BODY_H + 23.0 + (LIDAR[2] - 23.0) / 2))
    print('  bac : x de %.1f a l\'arriere, volume %.2f L'
          % (BIN_FRONT_X, parts['Bac'].Volume / 1e6))


parts = build()
show(parts)
report(parts)
