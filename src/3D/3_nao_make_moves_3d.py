# -*- coding: utf-8 -*-
"""
Fuehrt die von coordinates_to_motion_graph erzeugte Armtrajektorie aus.

Hinweis:
- Fuer klassische NAOqi-Installationen ist dieses Skript mit Python 2.7 kompatibel.
- Zuerst in Choregraphe bzw. mit niedriger Geschwindigkeit testen.
"""

from __future__ import print_function

import csv
import os
import sys

from naoqi import ALProxy


# ============================================================
# KONFIGURATION
# ============================================================

IP = "127.0.0.1"
PORT = 9559

# Nur X, Y und Z aus der Trajektorie verwenden.
AXIS_MASK = 7
FRAME_TORSO = 0


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def ask_user(prompt):
    """Kompatible Eingabe fuer Python 2 und Python 3."""
    try:
        return raw_input(prompt)
    except NameError:
        return input(prompt)


def load_trajectory(csv_path):
    """Liest und validiert die Armtrajektorie."""
    required_columns = [
        'time',
        'R_X', 'R_Y', 'R_Z', 'R_WX', 'R_WY', 'R_WZ',
        'L_X', 'L_Y', 'L_Z', 'L_WX', 'L_WY', 'L_WZ'
    ]

    with open(csv_path, 'r') as csv_file:
        reader = csv.DictReader(csv_file)

        if reader.fieldnames is None:
            raise RuntimeError("Die Trajektorien-CSV besitzt keine Kopfzeile.")

        missing = [name for name in required_columns if name not in reader.fieldnames]
        if missing:
            raise RuntimeError(
                "Fehlende CSV-Spalten: {0}".format(", ".join(missing))
            )

        rows = list(reader)

    if not rows:
        raise RuntimeError("Die Trajektorien-CSV enthaelt keine Daten.")

    right_path = []
    left_path = []
    times = []
    previous_time = 0.0

    for index, row in enumerate(rows, start=2):
        try:
            timestamp = float(row['time'])
            right_point = [
                float(row['R_X']), float(row['R_Y']), float(row['R_Z']),
                float(row['R_WX']), float(row['R_WY']), float(row['R_WZ'])
            ]
            left_point = [
                float(row['L_X']), float(row['L_Y']), float(row['L_Z']),
                float(row['L_WX']), float(row['L_WY']), float(row['L_WZ'])
            ]
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                "Ungueltiger Zahlenwert in CSV-Zeile {0}: {1}".format(index, error)
            )

        if timestamp <= previous_time:
            raise RuntimeError(
                "Zeitwerte muessen streng aufsteigend sein. Fehler in Zeile {0}.".format(index)
            )

        previous_time = timestamp
        times.append(timestamp)
        right_path.append(right_point)
        left_path.append(left_point)

    return times, right_path, left_path


# ============================================================
# HAUPTPROGRAMM
# ============================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.abspath(
        os.path.join(script_dir, '..', '..', 'generated', 'nao_arm_paths.csv')
    )

    print("")
    print("==========================================")
    print("NAO BEWEGUNG")
    print("==========================================")
    print("Zu verwendende Trajektorie:")
    print(input_csv)
    print("")

    if not os.path.isfile(input_csv):
        raise RuntimeError("Trajektorien-Datei nicht gefunden: {0}".format(input_csv))

    answer = ask_user(
        "Soll die Bewegung wirklich gestartet werden? [ja/nein]: "
    ).strip().lower()

    if answer != "ja":
        print("Bewegung abgebrochen.")
        return

    times, right_path, left_path = load_trajectory(input_csv)

    motion = ALProxy("ALMotion", IP, PORT)
    posture = ALProxy("ALRobotPosture", IP, PORT)

    print("")
    print("Wecke NAO auf...")
    motion.wakeUp()

    try:
        print("Gehe in StandInit...")
        if not posture.goToPosture("StandInit", 1.0):
            raise RuntimeError("StandInit konnte nicht erreicht werden.")

        print("Aktiviere Kollisionsschutz fuer die Arme...")
        motion.setCollisionProtectionEnabled("Arms", True)

        # Verhindert eine ungewollte Ganzkoerperkompensation.
        motion.wbEnable(False)

        print("")
        print("==========================================")
        print("STARTE BEWEGUNG")
        print("==========================================")
        print("Frames: {0}".format(len(times)))
        print("Dauer: {0:.3f} Sekunden".format(times[-1]))
        print("")

        motion.positionInterpolations(
            ["RArm", "LArm"],
            FRAME_TORSO,
            [right_path, left_path],
            [AXIS_MASK, AXIS_MASK],
            [times, times]
        )

        print("")
        print("==========================================")
        print("BEWEGUNG ERFOLGREICH BEENDET")
        print("==========================================")
    finally:
        # Auch bei einem Fehler keinen Whole-Body-Modus aktiv lassen.
        motion.wbEnable(False)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FEHLER: {0}".format(error))
        sys.exit(1)
