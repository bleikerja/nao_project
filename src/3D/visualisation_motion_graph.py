import csv
import os
import numpy as np
import matplotlib.pyplot as plt

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

output_png = os.path.abspath(
    os.path.join(
        script_dir,
        '..',
        '..',
        'generated',
        'nao_arm_traektorien_3d.png'
    )
)

# ============================================================
# CSV EINLESEN
# ============================================================

print("Lese:")
print(input_csv)

with open(input_csv, 'r') as file:
    data = list(csv.DictReader(file))

if len(data) == 0:
    raise RuntimeError("Die CSV enthält keine Daten.")

# ============================================================
# DATEN EXTRAHIEREN
# ============================================================

time = np.array([
    float(row['time'])
    for row in data
])

# Rechter Arm
rx = np.array([float(row['R_X']) for row in data])
ry = np.array([float(row['R_Y']) for row in data])
rz = np.array([float(row['R_Z']) for row in data])

# Linker Arm
lx = np.array([float(row['L_X']) for row in data])
ly = np.array([float(row['L_Y']) for row in data])
lz = np.array([float(row['L_Z']) for row in data])

# ============================================================
# 3D-GRAFIK
# ============================================================

fig = plt.figure(figsize=(12, 9))

ax = fig.add_subplot(
    111,
    projection='3d'
)

# ============================================================
# TRAJEKTORIEN
# ============================================================

ax.plot(
    rx,
    ry,
    rz,
    linewidth=2,
    label='Rechter Arm'
)

ax.plot(
    lx,
    ly,
    lz,
    linewidth=2,
    label='Linker Arm'
)

# ============================================================
# STARTPUNKTE
# ============================================================

ax.scatter(
    rx[0],
    ry[0],
    rz[0],
    s=80,
    marker='o',
    label='Start rechts'
)

ax.scatter(
    lx[0],
    ly[0],
    lz[0],
    s=80,
    marker='o',
    label='Start links'
)

# ============================================================
# ENDPUNKTE
# ============================================================

ax.scatter(
    rx[-1],
    ry[-1],
    rz[-1],
    s=100,
    marker='X',
    label='Ende rechts'
)

ax.scatter(
    lx[-1],
    ly[-1],
    lz[-1],
    s=100,
    marker='X',
    label='Ende links'
)

# ============================================================
# TORSO / SCHULTERN DARSTELLEN
# ============================================================

# NAO Schulterpositionen
shoulder_y_right = -0.10
shoulder_y_left = 0.10

shoulder_x = 0.16
shoulder_z = 0.10

ax.scatter(
    shoulder_x,
    shoulder_y_right,
    shoulder_z,
    s=100,
    marker='s',
    label='Rechte Schulter'
)

ax.scatter(
    shoulder_x,
    shoulder_y_left,
    shoulder_z,
    s=100,
    marker='s',
    label='Linke Schulter'
)

# Verbindungslinie zwischen den Schultern
ax.plot(
    [shoulder_x, shoulder_x],
    [shoulder_y_right, shoulder_y_left],
    [shoulder_z, shoulder_z],
    linewidth=2
)

# ============================================================
# BESCHRIFTUNG
# ============================================================

ax.set_xlabel('X – Vorne [m]')
ax.set_ylabel('Y – Links [m]')
ax.set_zlabel('Z – Oben [m]')

ax.set_title(
    'NAO Arm-Trajektorien\n'
    '3D-Darstellung der berechneten Bewegung'
)

ax.legend()
ax.grid(True)

# ============================================================
# GLEICHE SKALIERUNG AUF ALLEN ACHSEN
# ============================================================

all_x = np.concatenate([rx, lx])
all_y = np.concatenate([ry, ly])
all_z = np.concatenate([rz, lz])

max_range = max(
    all_x.max() - all_x.min(),
    all_y.max() - all_y.min(),
    all_z.max() - all_z.min()
) / 2.0

mid_x = (all_x.max() + all_x.min()) / 2.0
mid_y = (all_y.max() + all_y.min()) / 2.0
mid_z = (all_z.max() + all_z.min()) / 2.0

ax.set_xlim(
    mid_x - max_range,
    mid_x + max_range
)

ax.set_ylim(
    mid_y - max_range,
    mid_y + max_range
)

ax.set_zlim(
    mid_z - max_range,
    mid_z + max_range
)

# ============================================================
# KAMERAPOSITION
# ============================================================

ax.view_init(
    elev=25,
    azim=-60
)

# ============================================================
# SPEICHERN
# ============================================================

plt.tight_layout()

plt.savefig(
    output_png,
    dpi=300,
    bbox_inches='tight'
)

print("")
print("==========================================")
print("VISUALISIERUNG ERSTELLT")
print("==========================================")
print("Gespeichert:")
print(output_png)
print("==========================================")

plt.show()
