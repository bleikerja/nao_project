# -*- coding: utf-8 -*-
"""Play proportionally retargeted 3D motion on a NAO (Python 2.7/NAOqi)."""
from __future__ import print_function

import csv
import math
import os
import time

from naoqi import ALProxy


ROBOT_IP = os.environ.get("NAO_IP", "127.0.0.1")
PORT = int(os.environ.get("NAO_PORT", "9559"))
INPUT_FILE = "../../generated/nao_angles_3d.csv"
STEP_SECONDS = 0.08

# These are the actual NAO joint names produced by the proportional retargeter.
JOINTS = [
    "LShoulderPitch", "LShoulderRoll", "LElbowRoll",
    "RShoulderPitch", "RShoulderRoll", "RElbowRoll",
    "LHipPitch", "LHipRoll", "LKneePitch",
    "RHipPitch", "RHipRoll", "RKneePitch",
]


def finite(value):
    return not (math.isnan(value) or math.isinf(value))


def read_rows():
    with open(INPUT_FILE, "rb") as source:
        return list(csv.DictReader(source))


def main():
    rows = read_rows()
    if not rows:
        raise RuntimeError("Die 3D-Winkel-CSV enthält keine Frames.")

    motion = ALProxy("ALMotion", ROBOT_IP, PORT)
    try:
        background = ALProxy("ALBackgroundMovement", ROBOT_IP, PORT)
        background.setEnabled(False)
    except Exception as error:
        print("Hintergrundbewegung konnte nicht deaktiviert werden: {}".format(error))

    available = [name for name in JOINTS if name in rows[0]]
    if not available:
        raise RuntimeError("Keine passenden NAO-Gelenke in der CSV gefunden.")

    motion.stiffnessInterpolation(available, 1.0, 0.5)
    last = dict((name, 0.0) for name in available)

    try:
        for row in rows:
            names = []
            angles = []
            for name in available:
                raw = row.get(name, "")
                try:
                    value = float(raw)
                    if not finite(value):
                        raise ValueError()
                except (TypeError, ValueError):
                    value = last[name]
                names.append(name)
                angles.append(value)
                last[name] = value

            motion.setAngles(names, angles, 0.7)
            time.sleep(STEP_SECONDS)
    finally:
        motion.stiffnessInterpolation(available, 0.0, 0.5)

    print("Proportionale 3D-Bewegung erfolgreich an den NAO übertragen.")


if __name__ == "__main__":
    main()
