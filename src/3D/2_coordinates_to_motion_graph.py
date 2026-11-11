import csv
import numpy as np
import os

# ============================================================
# DATEIPFADE
# ============================================================

script_dir = os.path.dirname(os.path.abspath(__file__))

input_csv = os.path.abspath(
    os.path.join(
        script_dir,
        '..',
        '..',
        'generated',
        'roboter_bewegungsdaten_3d.csv'
    )
)

output_csv = os.path.abspath(
    os.path.join(
        script_dir,
        '..',
        '..',
        'generated',
        'nao_arm_paths.csv'
    )
)

# ============================================================
# PARAMETER
# ============================================================

# 0.1 Sekunden pro Frame = 10 FPS
# Für echte 20 FPS wäre hier 0.05 einzutragen.
zeit_pro_frame = 0.1

# NAO Schulterabstand
NAO_SCHULTERABSTAND = 0.20

# ------------------------------------------------------------
# Glättung der MediaPipe-Daten
#
# 0.0 = keine neue Messung übernehmen
# 1.0 = keine Glättung
#
# Ein Wert von ca. 0.3 - 0.4 ist ein guter Anfang.
# ------------------------------------------------------------

SMOOTHING_ALPHA = 0.35

# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def punkt(row, prefix):
    """
    Liest einen 3D-Punkt aus der CSV.
    """
    return np.array([
        float(row[prefix + '_X']),
        float(row[prefix + '_Y']),
        float(row[prefix + '_Z'])
    ])


def normiere(v):
    """
    Normalisiert einen Vektor.
    """
    laenge = np.linalg.norm(v)

    if laenge < 1e-8:
        return np.zeros(3)

    return v / laenge


def smooth_points(points, alpha):
    """
    Einfache exponentielle Glättung einer Punktfolge.
    """
    if len(points) == 0:
        return points

    result = np.zeros_like(points)

    result[0] = points[0]

    for i in range(1, len(points)):
        result[i] = (
            alpha * points[i]
            +
            (1.0 - alpha) * result[i - 1]
        )

    return result


# ============================================================
# CSV EINLESEN
# ============================================================

print("Lese Eingabedatei:")
print(input_csv)

with open(input_csv, 'r') as file:
    raw_data = list(csv.DictReader(file))

if len(raw_data) == 0:
    raise RuntimeError("Die Eingabe-CSV enthält keine Daten.")

print("Anzahl Frames:", len(raw_data))

# ============================================================
# SCHRITT 1:
# MEDIAPIPE-PUNKTE AUS CSV AUSLESEN
# ============================================================

left_shoulder = []
right_shoulder = []

left_hip = []
right_hip = []

left_wrist = []
right_wrist = []

for row in raw_data:

    left_shoulder.append(
        punkt(row, 'LShoulderRoll')
    )

    right_shoulder.append(
        punkt(row, 'RShoulderRoll')
    )

    left_hip.append(
        punkt(row, 'LHipRoll')
    )

    right_hip.append(
        punkt(row, 'RHipRoll')
    )

    left_wrist.append(
        punkt(row, 'LWrist')
    )

    right_wrist.append(
        punkt(row, 'RWrist')
    )


left_shoulder = np.array(left_shoulder)
right_shoulder = np.array(right_shoulder)

left_hip = np.array(left_hip)
right_hip = np.array(right_hip)

left_wrist = np.array(left_wrist)
right_wrist = np.array(right_wrist)

# ============================================================
# SCHRITT 2:
# MEDIAPIPE-DATEN GLÄTTEN
# ============================================================

left_shoulder = smooth_points(
    left_shoulder,
    SMOOTHING_ALPHA
)

right_shoulder = smooth_points(
    right_shoulder,
    SMOOTHING_ALPHA
)

left_hip = smooth_points(
    left_hip,
    SMOOTHING_ALPHA
)

right_hip = smooth_points(
    right_hip,
    SMOOTHING_ALPHA
)

left_wrist = smooth_points(
    left_wrist,
    SMOOTHING_ALPHA
)

right_wrist = smooth_points(
    right_wrist,
    SMOOTHING_ALPHA
)

# ============================================================
# SCHRITT 3:
# DYNAMISCHE PROPORTIONAL-SKALIERUNG
#
# Jetzt wird der vollständige 3D-Schulterabstand verwendet.
# ============================================================

first_left_shoulder = left_shoulder[0]
first_right_shoulder = right_shoulder[0]

mp_shoulder_dist = np.linalg.norm(
    first_left_shoulder
    -
    first_right_shoulder
)

if mp_shoulder_dist < 1e-8:
    print("WARNUNG: Schulterabstand ist 0.")
    mp_shoulder_dist = 1.0

skalierung = (
    NAO_SCHULTERABSTAND
    /
    mp_shoulder_dist
)

print("MediaPipe Schulterabstand 3D:",
      mp_shoulder_dist)

print("NAO Schulterabstand:",
      NAO_SCHULTERABSTAND)

print("Verwendete Skalierung:",
      skalierung)

# ============================================================
# SCHRITT 4:
# TRAJEKTORIEN VORBEREITEN
# ============================================================

path_r_arm = []
path_l_arm = []
time_list = []

current_time = 0.0

# ============================================================
# SCHRITT 5:
# TORUS-KOORDINATENSYSTEM + ARMVEKTOREN
# ============================================================

for i in range(len(raw_data)):

    current_time += zeit_pro_frame

    time_list.append(current_time)

    # --------------------------------------------------------
    # Aktuelle Körperpunkte
    # --------------------------------------------------------

    LShoulder = left_shoulder[i]
    RShoulder = right_shoulder[i]

    LHip = left_hip[i]
    RHip = right_hip[i]

    LWrist = left_wrist[i]
    RWrist = right_wrist[i]

    # ========================================================
    # SCHRITT 5.1:
    # SCHULTER- UND HÜFTMITTELPUNKT
    # ========================================================

    shoulder_center = (
        LShoulder
        +
        RShoulder
    ) / 2.0

    hip_center = (
        LHip
        +
        RHip
    ) / 2.0

    # ========================================================
    # SCHRITT 5.2:
    # MENSCHLICHE AUFWÄRTS-ACHSE
    #
    # MediaPipe:
    # Y zeigt nach unten.
    #
    # Deshalb wird die Achse vom Hüftzentrum
    # zum Schulterzentrum verwendet und anschließend
    # für NAO-Z als "oben" interpretiert.
    # ========================================================

    up_axis = (
        shoulder_center
        -
        hip_center
    )

    up_axis = normiere(up_axis)

    # ========================================================
    # SCHRITT 5.3:
    # MENSCHLICHE LINKS/RECHTS-ACHSE
    #
    # Von rechter Schulter zu linker Schulter.
    #
    # Dadurch zeigt die Achse in Richtung
    # menschlich links.
    # ========================================================

    left_axis = (
        LShoulder
        -
        RShoulder
    )

    left_axis = normiere(left_axis)

    # ========================================================
    # SCHRITT 5.4:
    # VORWÄRTS-ACHSE DES MENSCHEN
    #
    # Kreuzprodukt aus Seitenachse und Aufwärtsachse.
    #
    # Damit erhalten wir eine Achse, die ungefähr
    # nach vorne zeigt.
    # ========================================================

    forward_axis = np.cross(
        left_axis,
        up_axis
    )

    forward_axis = normiere(forward_axis)

    # --------------------------------------------------------
    # Orthogonalisierung
    #
    # MediaPipe-Punkte sind nicht mathematisch perfekt
    # orthogonal. Deshalb wird die Linksachse nochmals
    # aus den beiden anderen Achsen berechnet.
    # --------------------------------------------------------

    left_axis = np.cross(
        up_axis,
        forward_axis
    )

    left_axis = normiere(left_axis)

    # ========================================================
    # SCHRITT 5.5:
    # ARMVEKTOR SCHULTER -> HAND
    # ========================================================

    # --------------------------------------------------------
    # Rechter Arm
    # --------------------------------------------------------

    arm_r = (
        RWrist
        -
        RShoulder
    )

    # --------------------------------------------------------
    # Linker Arm
    # --------------------------------------------------------

    arm_l = (
        LWrist
        -
        LShoulder
    )

    # ========================================================
    # SCHRITT 5.6:
    # MENSCHLICHER ARMVEKTOR
    # -> LOKALES TORSO-KOORDINATENSYSTEM
    #
    # Lokales menschliches System:
    #
    # X = vorne
    # Y = links
    # Z = oben
    # ========================================================

    # --------------------------------------------------------
    # Rechter Arm
    # --------------------------------------------------------

    human_r_x = np.dot(
        arm_r,
        forward_axis
    )

    human_r_y = np.dot(
        arm_r,
        left_axis
    )

    human_r_z = np.dot(
        arm_r,
        up_axis
    )

    # --------------------------------------------------------
    # Linker Arm
    # --------------------------------------------------------

    human_l_x = np.dot(
        arm_l,
        forward_axis
    )

    human_l_y = np.dot(
        arm_l,
        left_axis
    )

    human_l_z = np.dot(
        arm_l,
        up_axis
    )

    # ========================================================
    # SCHRITT 5.7:
    # MENSCHLICHES LOKALES SYSTEM
    # -> NAO KOORDINATENSYSTEM
    #
    # NAO:
    #
    # X = vorne
    # Y = links
    # Z = oben
    #
    # Der wichtige Unterschied zur alten Version:
    #
    # NAO-Y bekommt jetzt direkt den lokalen
    # Links/Rechts-Wert.
    #
    # Es gibt kein zusätzliches "- dx".
    # ========================================================

    # --------------------------------------------------------
    # Rechter Arm
    # --------------------------------------------------------

    nao_rx = (
        0.16
        +
        human_r_x * skalierung
    )

    nao_ry = (
        -0.10
        +
        human_r_y * skalierung
    )

    nao_rz = (
        0.10
        +
        human_r_z * skalierung
    )

    # --------------------------------------------------------
    # Linker Arm
    # --------------------------------------------------------

    nao_lx = (
        0.16
        +
        human_l_x * skalierung
    )

    nao_ly = (
        0.10
        +
        human_l_y * skalierung
    )

    nao_lz = (
        0.10
        +
        human_l_z * skalierung
    )

    # ========================================================
    # SCHRITT 5.8:
    # FINALER 6D-PUNKT
    #
    # [X, Y, Z, Wx, Wy, Wz]
    #
    # Wir verwenden bewusst KEINE Rotation.
    #
    # Die spätere NAO-Ausführung kann deshalb mit
    # axisMask = 7 arbeiten:
    #
    # 1 = X
    # 2 = Y
    # 4 = Z
    # 7 = X + Y + Z
    # ========================================================

    path_r_arm.append([
        nao_rx,
        nao_ry,
        nao_rz,
        0.0,
        0.0,
        0.0
    ])

    path_l_arm.append([
        nao_lx,
        nao_ly,
        nao_lz,
        0.0,
        0.0,
        0.0
    ])

# ============================================================
# BERECHNETE DATEN ALS CSV SPEICHERN
# ============================================================

os.makedirs(
    os.path.dirname(output_csv),
    exist_ok=True
)

with open(output_csv, 'w') as file:

    writer = csv.writer(file)

    writer.writerow([
        'time',

        'R_X',
        'R_Y',
        'R_Z',
        'R_WX',
        'R_WY',
        'R_WZ',

        'L_X',
        'L_Y',
        'L_Z',
        'L_WX',
        'L_WY',
        'L_WZ'
    ])

    for i in range(len(time_list)):

        writer.writerow([
            time_list[i],

            path_r_arm[i][0],
            path_r_arm[i][1],
            path_r_arm[i][2],
            path_r_arm[i][3],
            path_r_arm[i][4],
            path_r_arm[i][5],

            path_l_arm[i][0],
            path_l_arm[i][1],
            path_l_arm[i][2],
            path_l_arm[i][3],
            path_l_arm[i][4],
            path_l_arm[i][5]
        ])

# ============================================================
# SCHRITT 6:
# INFORMATIONEN ZUR TRAJEKTORIE
# ============================================================

r_array = np.array(path_r_arm)
l_array = np.array(path_l_arm)

print("")
print("==========================================")
print("BERECHNUNG ABGESCHLOSSEN")
print("==========================================")

print("Frames:", len(time_list))

print("Dauer:",
      time_list[-1],
      "Sekunden")

print("MediaPipe Schulterabstand 3D:",
      mp_shoulder_dist)

print("NAO Schulterabstand:",
      NAO_SCHULTERABSTAND)

print("Skalierung:",
      skalierung)

print("")
print("Rechter Arm:")
print("  X min/max:",
      np.min(r_array[:, 0]),
      np.max(r_array[:, 0]))

print("  Y min/max:",
      np.min(r_array[:, 1]),
      np.max(r_array[:, 1]))

print("  Z min/max:",
      np.min(r_array[:, 2]),
      np.max(r_array[:, 2]))

print("")
print("Linker Arm:")
print("  X min/max:",
      np.min(l_array[:, 0]),
      np.max(l_array[:, 0]))

print("  Y min/max:",
      np.min(l_array[:, 1]),
      np.max(l_array[:, 1]))

print("  Z min/max:",
      np.min(l_array[:, 2]),
      np.max(l_array[:, 2]))

print("")
print("Gespeichert:")
print(output_csv)

print("==========================================")