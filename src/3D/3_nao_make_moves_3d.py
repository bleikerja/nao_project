# -*- coding: utf-8 -*-
# import csv
# import time
# import numpy as np
# from naoqi import ALProxy
# import os
#
# IP = "127.0.0.1"
# PORT = 9559
#
# motion = ALProxy("ALMotion", IP, PORT)
# posture = ALProxy("ALRobotPosture", IP, PORT)
#
# # 1. NAO aufwecken und stabil hinstellen
# motion.wakeUp()
# posture.goToPosture("StandInit", 1.0)
#
# # 2. GANZKÖRPER-SCHUTZ & BALANCE AKTIVIEREN
# motion.setCollisionProtectionEnabled("Arms", True)
# motion.wbEnable(True)  # Whole Body Control aktivieren
# # Ganz wichtig: Füße fixieren, damit der Torso die Beine beugen kann
# #motion.wbEnableBalanceConstraint(True, "Legs")
#
# script_dir = os.path.dirname(os.path.abspath(__file__))
# csv_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'generated', 'roboter_bewegungsdaten_3d.csv'))
#
# with open(csv_path, 'r') as file:
#     raw_data = list(csv.DictReader(file))
#
# # Listen für die 3D-Wegpunkte vorbereiten
# path_r_arm = []
# path_l_arm = []
# path_torso = []  # Steuert die Beinbeugung / Hüftbewegung
# time_list = []
#
# current_time = 0.0
# zeit_pro_frame = 0.05  # 20 FPS
#
# #R_DEFAULT_ROT = [1.57, 0.0, 0.0]
# #L_DEFAULT_ROT = [1.57, 0.0, 0.0]
#
# # Daten einlesen, transformieren und skalieren
# # -*- coding: utf-8 -*-
# # ... (Anfang deines Skripts bleibt gleich)
#
# for i, row in enumerate(raw_data):
#     current_time += zeit_pro_frame
#     time_list.append(current_time)
#
#     # 1. 3D-Daten der Hände holen
#     mp_rx, mp_ry, mp_rz = float(row['RWrist_X']), float(row['RWrist_Y']), float(row['RWrist_Z'])
#     mp_lx, mp_ly, mp_lz = float(row['LWrist_X']), float(row['LWrist_Y']), float(row['LWrist_Z'])
#
#     # 2. 3D-Daten der Schultern holen (Wichtig: Wir nehmen die Schultern als festen Bezugspunkt!)
#     mp_rsx, mp_rsy, mp_rsz = float(row['RShoulderRoll_X']), float(row['RShoulderRoll_Y']), float(row['RShoulderRoll_Z'])
#     mp_lsx, mp_lsy, mp_lsz = float(row['LShoulderRoll_X']), float(row['LShoulderRoll_Y']), float(row['LShoulderRoll_Z'])
#
#     # 3. 3D-Daten der Hüfte für die Beinarbeit (Mittelwert)
#     mp_hx = (float(row['LHipRoll_X']) + float(row['RHipRoll_X'])) / 2.0
#     mp_hy = (float(row['LHipRoll_Y']) + float(row['RHipRoll_Y'])) / 2.0
#     mp_hz = (float(row['LHipRoll_Z']) + float(row['RHipRoll_Z'])) / 2.0
#
#     # --- DIREKTE SCHULTER-ZU-HAND-TRANSFORMATION ---
#     # Wir berechnen, wie weit die Hand von der Schulter entfernt ist.
#     # Da MediaPipe-Y nach unten zählt, bedeutet ein kleinerer Y-Wert bei der Hand,
#     # dass die Hand HÖHER als die Schulter ist -> (mp_rsy - mp_ry) wird positiv!
#
#     delta_rx = (mp_rsz - mp_rz)  # Tiefe relativ zur Schulter
#     delta_ry = (mp_rsx - mp_rx)  # Links/Rechts relativ zur Schulter
#     delta_rz = (mp_rsy - mp_ry)  # Höhe relativ zur Schulter (Positiv = Hand über Schulter)
#
#     delta_lx = (mp_lsz - mp_lz)
#     delta_ly = (mp_lsx - mp_lx)
#     delta_lz = (mp_lsy - mp_ly)
#
#     # RECHTER ARM: Umrechnung auf NAO-Arbeitsraum mit festem, sicherem Brust-Offset
#     # Der NAO-Arm startet mechanisch an der Schulter (ca. X=0.0, Y=-0.1, Z=0.1)
#     nao_rx = 0.2 #delta_rx * 0.4 + 0.18  # Stabil 18 cm vor der Brust halten
#     nao_ry = delta_ry * 0.6 + 0.18  # Seitliche Winkbewegung verstärkt auf Faktor 0.5
#     nao_rz = delta_rz * 0.7 + 0.20  # Höhenbewegung massiv verstärkt (Faktor 0.6) + Grundhöhe 12 cm
#
#     # LINKER ARM: Analog für die linke Seite
#     nao_lx = 0.2 #delta_lx * 0.4 + 0.18
#     nao_ly = delta_ly * 0.6 + 0.15
#     nao_lz = delta_lz * 0.7 + 0.12
#
#     # Begrenzung (Clipping), damit der Arm nicht in ungesunde Extrembereiche gerät
#     # nao_ry = np.clip(nao_ry, -0.28, -0.05)
#     # nao_ly = np.clip(nao_ly, 0.05, 0.28)
#     # nao_rz = np.clip(nao_rz, 0.02, 0.35)  # Erlaubt eine Höhe bis zu 35 cm über der Brust
#     # nao_lz = np.clip(nao_lz, 0.02, 0.35)
#
#     # Ergonomische Handgelenks-Rotation (Wy): Verhindert das Sperren der Schulter bei hoher Position
#     r_wy = np.clip(nao_rz * 1.5, -0.1, 0.8)
#     l_wy = np.clip(nao_lz * 1.5, -0.1, 0.8)
#
#     # TORSO / BEINE: Extrem dämpfen, damit der Fokus rein auf dem Winken liegt
#     nao_tx = 0.0
#     nao_ty = 0.0
#     # Nutzt den ersten Frame als stabile Standhöhe. Geht nur minimal mit (max 2cm Hocke)
#     nao_tz = -(mp_hy - float(raw_data[0]['RHipRoll_Y'])) * 0.05
#     nao_tz = np.clip(nao_tz, -0.02, 0.02)
#
#     # Format: [X, Y, Z, Wx, Wy, Wz] (Wir nutzen 1.57 rad / 90 Grad Drehung für eine natürliche Handhaltung)
#     path_r_arm.append([nao_rx, nao_ry, nao_rz, 1.57, 0.0, 0.0])
#     path_l_arm.append([nao_lx, nao_ly, nao_lz, 1.57, 0.0, 0.0])
#     path_torso.append([nao_tx, nao_ty, nao_tz, 0.0, 0.0, 0.0])
#
# # 3. Bewegung für ARME und BEINE (Torso) synchron starten
# # FRAME_ROBOT (2) nutzen wir hier, da sich der Torso relativ zu den festen Füßen bewegt
# effectors = ["RArm", "LArm"]#["RArm", "LArm", "Torso"]
# frame = 0#2  # FRAME_ROBOT (Stabil für kombinierten Torso-Bein-Einsatz)
# axis_mask = [7, 7]  # 7 = Nur X, Y, Z steuern (Orientierung bleibt stabil)
#
# print("Starte sichere Ganzkörper-Bewegung inkl. Beinarbeit...")
#
# # Sendet Arm- und Hüftdaten komplett parallel an den Roboter.
# # Wenn der Torso nach unten steuert (nao_tz sinkt), geht der NAO automatisch in die Knie.
# motion.positionInterpolations(
#     effectors,
#     frame,
#     [path_r_arm, path_l_arm],
#     axis_mask,
#     [time_list, time_list]
# )
#
# # Nach der Bewegung Whole Body Control wieder ausschalten
# motion.wbEnable(False)
# print("Ganzkörper-Bewegung erfolgreich beendet.")
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# import csv
# import time
# import numpy as np
# from naoqi import ALProxy
# import os
#
# IP = "127.0.0.1"
# PORT = 9559
#
# motion = ALProxy("ALMotion", IP, PORT)
# posture = ALProxy("ALRobotPosture", IP, PORT)
#
# # 1. NAO aufwecken und in stabile Standard-Pose bringen
# motion.wakeUp()
# posture.goToPosture("StandInit", 1.0)
#
# # 2. Universal-Schutz aktivieren und Beinzappeln stoppen
# motion.setCollisionProtectionEnabled("Arms", True)
# motion.wbEnable(False)  # Verhindert, dass die Beine sich ungewollt mitbewegen
#
# script_dir = os.path.dirname(os.path.abspath(__file__))
# csv_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'generated', 'roboter_bewegungsdaten_3d.csv'))
#
# with open(csv_path, 'r') as file:
#     raw_data = list(csv.DictReader(file))
#
# path_r_arm = []
# path_l_arm = []
# time_list = []
#
# current_time = 0.0
# zeit_pro_frame = 0.1  # 20 FPS
#
# # --- SCHRITT 1: DYNAMISCHE PROPORTIONAL-SKALIERUNG ---
# # Wir messen im ersten Frame den Schulterabstand des Menschen.
# # Das setzen wir ins Verhältnis zu NAOs echtem Schulterabstand (ca. 0.20 Meter).
# first_row = raw_data[0]
# mp_shoulder_dist = np.linalg.norm(
#     np.array([float(first_row['LShoulderRoll_X']), float(first_row['LShoulderRoll_Y'])]) -
#     np.array([float(first_row['RShoulderRoll_X']), float(first_row['RShoulderRoll_Y'])])
# )
# if mp_shoulder_dist == 0:
#     mp_shoulder_dist = 1.0
#
# skalierung = 0.20 / mp_shoulder_dist
#
# # --- SCHRITT 2: UNIVERSAL-VEKTOR-BERECHNUNG ---
# for i, row in enumerate(raw_data):
#     current_time += zeit_pro_frame
#     time_list.append(current_time)
#
#     # 3D-Koordinaten aus der CSV auslesen
#     mp_rx, mp_ry, mp_rz = float(row['RWrist_X']), float(row['RWrist_Y']), float(row['RWrist_Z'])
#     mp_lx, mp_ly, mp_lz = float(row['LWrist_X']), float(row['LWrist_Y']), float(row['LWrist_Z'])
#
#     mp_rsx, mp_rsy, mp_rsz = float(row['RShoulderRoll_X']), float(row['RShoulderRoll_Y']), float(row['RShoulderRoll_Z'])
#     mp_lsx, mp_lsy, mp_lsz = float(row['LShoulderRoll_X']), float(row['LShoulderRoll_Y']), float(row['LShoulderRoll_Z'])
#
#     # KORRIGIERTE VEKTOR-MAPPING (MediaPipe 3D -> NAO Torso)
#     # MediaPipe: X=rechts, Y=unten, Z=Tiefe
#     # NAO Torso: X=vorne (-mp_z), Y=links (-mp_x), Z=oben (-mp_y)
#
#     # Abstand Hand zu Schulter berechnen
#     dx_r = (mp_rsx - mp_rx)
#     dy_r = (mp_rsy - mp_ry)
#     dz_r = (mp_rsz - mp_rz)
#
#     dx_l = (mp_lsx - mp_lx)
#     dy_l = (mp_lsy - mp_ly)
#     dz_l = (mp_lsz - mp_lz)
#
#     # Umrechnung in NAOs physikalisches System unter Berücksichtigung der Achsenrichtungen:
#     # Vorwärts (X): Orientiert an der Tiefe (Z)
#     # Seitwärts (Y): Invertiert für die korrekte Rechts-/Links-Spiegelung
#     # Höhenachse (Z): Invertiert, da MediaPipe-Y nach unten geht
#     nao_rx = 0.16 + (dz_r * skalierung)  # +0.16m Sicherheits-Offset nach vorne
#     nao_ry = -0.10 - (dx_r * skalierung)  # Verankert an rechter Schulter (-0.10)
#     nao_rz = 0.10 + (dy_r * skalierung)  # Verankert an Schulterhöhe (0.10)
#
#     nao_lx = 0.16 + (dz_l * skalierung)
#     nao_ly = 0.10 - (dx_l * skalierung)  # Verankert an linker Schulter (+0.10)
#     nao_lz = 0.10 + (dy_l * skalierung)
#
#     # DYNAMISCHES SCHULTER-AUSPLANELELN (Wy Rotation):
#     # Je höher der Arm geht, desto mehr drehen wir das Handgelenk mit (in Radiant),
#     # damit die Schulter mechanisch komplett freigegeben wird.
#     r_wy = np.clip(nao_rz * 1.5, 0.0, 0.8)
#     l_wy = np.clip(nao_lz * 1.5, 0.0, 0.8)
#
#     # Format: [X, Y, Z, Wx, Wy, Wz]
#     # Wx = 1.57 stellt die Handfläche ergonomisch aufrecht (wie beim Winken oder Zeigen)
#     path_r_arm.append([nao_rx, nao_ry, nao_rz, 1.57, r_wy, 0.0])
#     path_l_arm.append([nao_lx, nao_ly, nao_lz, 1.57, l_wy, 0.0])
#
# # 3. Bewegung starten
# effectors = ["RArm", "LArm"]
# frame = 0  # FRAME_TORSO
# axis_mask = [63, 63]  # 63 = Nutzt Position UND Rotation. Zwingt den Arm, sich flüssig auszudrehen.
#
# print("Starte universelle, proportionale 3D-Bewegung...")
#
# motion.positionInterpolations(
#     effectors,
#     frame,
#     [path_r_arm, path_l_arm],
#     axis_mask,
#     [time_list, time_list]
# )
#
# print("Bewegung erfolgreich beendet.")
import csv
import os
from naoqi import ALProxy

# ============================================================
# NAO VERBINDUNG
# ============================================================

IP = "127.0.0.1"
PORT = 9559

motion = ALProxy(
    "ALMotion",
    IP,
    PORT
)

posture = ALProxy(
    "ALRobotPosture",
    IP,
    PORT
)

# ============================================================
# DATEIPFAD
# ============================================================

script_dir = os.path.dirname(os.path.abspath(__file__))

input_csv = os.path.abspath(
    os.path.join(
        script_dir,
        '..',
        '..',
        'generated',
        'nao_arm_paths.csv'
    )
)

# ============================================================
# SICHERHEITSABFRAGE
# ============================================================

print("")
print("==========================================")
print("NAO BEWEGUNG")
print("==========================================")
print("Zu verwendende Trajektorie:")
print(input_csv)
print("")

antwort = raw_input(
    "Soll die Bewegung wirklich gestartet werden? [ja/nein]: "
)

if antwort.lower() != "ja":
    print("Bewegung abgebrochen.")
    exit()

# ============================================================
# CSV EINLESEN
# ============================================================

with open(input_csv, 'r') as file:
    data = list(csv.DictReader(file))

if len(data) == 0:
    raise RuntimeError(
        "Die Trajektorien-CSV enthält keine Daten."
    )

# ============================================================
# TRAJEKTORIEN AUS CSV LADEN
# ============================================================

path_r_arm = []
path_l_arm = []
time_list = []

for row in data:
    time_list.append(
        float(row['time'])
    )

    # --------------------------------------------------------
    # Rechter Arm
    # --------------------------------------------------------

    path_r_arm.append([
        float(row['R_X']),
        float(row['R_Y']),
        float(row['R_Z']),
        float(row['R_WX']),
        float(row['R_WY']),
        float(row['R_WZ'])
    ])

    # --------------------------------------------------------
    # Linker Arm
    # --------------------------------------------------------

    path_l_arm.append([
        float(row['L_X']),
        float(row['L_Y']),
        float(row['L_Z']),
        float(row['L_WX']),
        float(row['L_WY']),
        float(row['L_WZ'])
    ])

# ============================================================
# NAO VORBEREITEN
# ============================================================

print("")
print("Wecke NAO auf...")

motion.wakeUp()

print("Gehe in StandInit...")

posture.goToPosture(
    "StandInit",
    1.0
)

# ============================================================
# SICHERHEIT
# ============================================================

print("Aktiviere Armschutz...")

motion.setCollisionProtectionEnabled(
    "Arms",
    True
)

# Whole Body Motion deaktivieren,
# damit die Beine nicht ungewollt mitbewegt werden.
motion.wbEnable(False)

# ============================================================
# BEWEGUNG
# ============================================================

effectors = [
    "RArm",
    "LArm"
]

# FRAME_TORSO
frame = 0

# 63 = Position + Orientierung
axis_mask = [
    7,
    7
]

print("")
print("==========================================")
print("STARTE BEWEGUNG")
print("==========================================")
print("Frames:", len(time_list))
print("Dauer:", time_list[-1], "Sekunden")
print("")

motion.positionInterpolations(
    effectors,
    frame,
    [
        path_r_arm,
        path_l_arm
    ],
    axis_mask,
    [
        time_list,
        time_list
    ]
)

# ============================================================
# ENDE
# ============================================================

print("")
print("==========================================")
print("BEWEGUNG ERFOLGREICH BEENDET")
print("==========================================")
