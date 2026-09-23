# -*- coding: utf-8 -*-
"""Send 3D-derived NAO joint angles to NAOqi.

This file must run with the Python 2.7 interpreter that contains NAOqi.
The pose detection and angle calculation run separately with Python 3.
"""

from __future__ import print_function

import csv
import math
import os
import time

from naoqi import ALProxy


ROBOT_IP = os.environ.get("NAO_IP", "127.0.0.1")
PORT = int(os.environ.get("NAO_PORT", "9559"))
INPUT_FILE = "../../generated/nao_angles_3d.csv"
STEP_SECONDS = 0.4

# Keep only joints that are present in nao_angles_3d.csv and supported by NAO.
NAO_JOINTS = [
    "LShoulderRoll",
    "LElbowRoll",
    "RShoulderRoll",
    "RElbowRoll",
    "LHipRoll",
    "RHipRoll",
    "LKneePitch",
    "RKneePitch",
]

# The 3D calculator writes LKnee/RKnee. Map them to the actual NAO joint names.
CSV_TO_NAO = {
    "LShoulderRoll": "LShoulderRoll",
    "LElbowRoll": "LElbowRoll",
    "RShoulderRoll": "RShoulderRoll",
    "RElbowRoll": "RElbowRoll",
    "LHipRoll": "LHipRoll",
    "RHipRoll": "RHipRoll",
    "LKnee": "LKneePitch",
    "RKnee": "RKneePitch",
}


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def read_motion_rows():
    with open(INPUT_FILE, "rb") as source:
        return list(csv.DictReader(source))


def main():
    rows = read_motion_rows()
    if not rows:
        raise RuntimeError("Die 3D-Winkel-CSV enthält keine Frames.")

    motion = ALProxy("ALMotion", ROBOT_IP, PORT)
    try:
        background = ALProxy("ALBackgroundMovement", ROBOT_IP, PORT)
        background.setEnabled(False)
    except Exception as error:
        print("ALBackgroundMovement konnte nicht deaktiviert werden: {}".format(error))

    names = []
    for csv_name, nao_name in CSV_TO_NAO.items():
        if csv_name in rows[0]:
            names.append(nao_name)

    if not names:
        raise RuntimeError("Keine passenden NAO-Gelenke in der 3D-Winkel-CSV gefunden.")

    motion.stiffnessInterpolation(names, 1.0, 0.5)
    last_angles = dict((name, 0.0) for name in names)

    for row in rows:
        target_names = []
        target_angles = []

        for csv_name, nao_name in CSV_TO_NAO.items():
            raw_value = row.get(csv_name, "")
            if raw_value in (None, ""):
                continue

            try:
                angle = float(raw_value)
                if not math.isfinite(angle):
                    continue
            except (TypeError, ValueError):
                continue

            # Protect the robot from impossible values. These are conservative
            # generic limits; verify them against the exact NAO model.
            angle = clamp(angle, -math.pi, math.pi)
            target_names.append(nao_name)
            target_angles.append(angle)
            last_angles[nao_name] = angle

        if target_names:
            motion.angleInterpolation(
                target_names,
                target_angles,
                STEP_SECONDS,
                True,
            )
        time.sleep(STEP_SECONDS)

    motion.stiffnessInterpolation(names, 0.0, 0.5)
    print("3D-Bewegung erfolgreich an den NAO übertragen.")


if __name__ == "__main__":
    main()
