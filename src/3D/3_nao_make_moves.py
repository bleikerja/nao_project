# -*- coding: utf-8 -*-
"""
Fuehrt eine aus dem Video abgeleitete NAO-Bewegung aus.

Bevorzugter Modus (posegenauer):
    Die CSV enthaelt NAO-Gelenkwinkel in Radiant, z. B.
    RShoulderPitch, RShoulderRoll, RElbowYaw, RElbowRoll, RWristYaw,
    LShoulderPitch, LShoulderRoll, LElbowYaw, LElbowRoll, LWristYaw.
    Dann wird angleInterpolation() verwendet.

Fallback-Modus (nur Handbahn):
    Die bisherige CSV enthaelt R_X ... R_WZ und L_X ... L_WZ.
    Dann wird positionInterpolations() verwendet. Dieser Modus kann die
    Handbahn nachfahren, aber nicht eindeutig dieselbe Ellbogen-/Armhaltung
    wie im Video reproduzieren.

Python-2.7-kompatibel fuer klassische NAOqi-Installationen.
"""
from __future__ import print_function

import csv
import math
import os
import sys
import time
from naoqi import ALProxy

# ============================================================
# KONFIGURATION
# ============================================================
IP = "127.0.0.1"
PORT = 9559

FRAME_TORSO = 0
AXIS_MASK_POSITION = 7  # X, Y, Z
START_TRANSITION_TIME = 1.5
USE_COLLISION_PROTECTION = True
ENABLE_LEFT_ARM = True
ENABLE_RIGHT_ARM = True

# 1.0 = Originalgeschwindigkeit. 2.0 = halb so schnell.
TIME_SCALE = 1.0

# Kleine Zeitwerte koennen in Choregraphe/NAOqi unruhig werden.
MIN_TIME_STEP = 0.04

# Steifigkeit der Arme waehrend der Wiedergabe.
ARM_STIFFNESS = 1.0
STIFFNESS_RAMP_SECONDS = 0.6

# Nach der Bewegung Arme entspannt lassen oder zur Ausgangshaltung fahren.
RETURN_TO_STAND_INIT = True
RELAX_ARMS_AFTERWARDS = False

JOINT_ORDER = [
    "HeadYaw", "HeadPitch",
    "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RWristYaw",
    "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LWristYaw",
]

CARTESIAN_COLUMNS = [
    "R_X", "R_Y", "R_Z", "R_WX", "R_WY", "R_WZ",
    "L_X", "L_Y", "L_Z", "L_WX", "L_WY", "L_WZ",
]


def ask_user(prompt):
    try:
        return raw_input(prompt)
    except NameError:
        return input(prompt)


def read_csv(csv_path):
    with open(csv_path, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise RuntimeError("Die CSV besitzt keine Kopfzeile.")
        rows = list(reader)
        fieldnames = [name.strip() for name in reader.fieldnames]

    if not rows:
        raise RuntimeError("Die CSV enthaelt keine Daten.")
    if "time" not in fieldnames:
        raise RuntimeError("Die Pflichtspalte 'time' fehlt.")
    return fieldnames, rows


def parse_float(row, column, line_number):
    try:
        value = float(row[column])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError(
            "Ungueltiger Wert fuer {0} in CSV-Zeile {1}.".format(
                column, line_number
            )
        )
    if math.isnan(value) or math.isinf(value):
        raise RuntimeError(
            "Nicht-endlicher Wert fuer {0} in CSV-Zeile {1}.".format(
                column, line_number
            )
        )
    return value


def prepare_times(rows):
    raw_times = []
    for line_number, row in enumerate(rows, start=2):
        timestamp = parse_float(row, "time", line_number) * TIME_SCALE
        raw_times.append(timestamp)
    first_timestamp = raw_times[0]

    times = []
    previous=0.0
    for timestamp in raw_times:
        relative_time = timestamp - first_timestamp

        new_timestamp = relative_time + START_TRANSITION_TIME
        if times and new_timestamp - previous < MIN_TIME_STEP:
            new_timestamp = previous + MIN_TIME_STEP
        if new_timestamp <= previous:
            raise RuntimeError("Zeitwerte muessen streng aufsteigend sein.")
        times.append(new_timestamp)
        previous = new_timestamp
    return times


def detect_mode(fieldnames):
    available_joints = [name for name in JOINT_ORDER if name in fieldnames]
    has_cartesian = all(name in fieldnames for name in CARTESIAN_COLUMNS)

    if available_joints:
        return "joints", available_joints
    if has_cartesian:
        return "cartesian", []

    raise RuntimeError(
        "CSV-Format nicht erkannt. Erwartet werden entweder NAO-Gelenkspalten "
        "oder die bisherigen R_X.../L_X...-Spalten."
    )


def filter_enabled_joints(joints):
    result = []
    for joint in joints:
        if joint.startswith("R") and not ENABLE_RIGHT_ARM:
            continue
        if joint.startswith("L") and not ENABLE_LEFT_ARM:
            continue
        result.append(joint)
    return result


def load_joint_trajectory(rows, joints, times):
    joints = filter_enabled_joints(joints)
    if not joints:
        raise RuntimeError("Durch die Arm-Konfiguration bleibt kein Gelenk uebrig.")

    angle_lists = []
    time_lists = []

    for joint in joints:
        values = []
        for line_number, row in enumerate(rows, start=2):
            values.append(parse_float(row, joint, line_number))
        angle_lists.append(values)
        time_lists.append(list(times))

    return joints, angle_lists, time_lists


def load_cartesian_trajectory(rows, times):
    effectors = []
    paths = []
    masks = []
    time_lists = []

    definitions = []
    if ENABLE_RIGHT_ARM:
        definitions.append(("RArm", ["R_X", "R_Y", "R_Z", "R_WX", "R_WY", "R_WZ"]))
    if ENABLE_LEFT_ARM:
        definitions.append(("LArm", ["L_X", "L_Y", "L_Z", "L_WX", "L_WY", "L_WZ"]))

    if not definitions:
        raise RuntimeError("Mindestens ein Arm muss aktiviert sein.")

    for effector, columns in definitions:
        path = []
        for line_number, row in enumerate(rows, start=2):
            path.append([parse_float(row, column, line_number) for column in columns])
        effectors.append(effector)
        paths.append(path)
        masks.append(AXIS_MASK_POSITION)
        time_lists.append(list(times))

    return effectors, paths, masks, time_lists


def print_cartesian_diagnostics(effectors, paths):
    print("")
    print("Kartesische Diagnose:")
    for effector, path in zip(effectors, paths):
        xyz = [point[:3] for point in path]
        minimum = [min(point[axis] for point in xyz) for axis in range(3)]
        maximum = [max(point[axis] for point in xyz) for axis in range(3)]
        movement = [maximum[axis] - minimum[axis] for axis in range(3)]
        print("  {0} min XYZ: {1}".format(effector, minimum))
        print("  {0} max XYZ: {1}".format(effector, maximum))
        print("  {0} Wegspanne: {1}".format(effector, movement))
        if max(movement) < 0.025:
            print("  WARNUNG: Bewegung unter 2.5 cm; visuell vermutlich kaum erkennbar.")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.abspath(
        os.path.join(script_dir, "..", "..", "generated", "nao_arm_paths.csv")
    )

    print("")
    print("==========================================")
    print("NAO VIDEO-BEWEGUNG")
    print("==========================================")
    print("CSV: {0}".format(input_csv))

    if not os.path.isfile(input_csv):
        raise RuntimeError("Trajektorien-Datei nicht gefunden: {0}".format(input_csv))

    fieldnames, rows = read_csv(input_csv)
    times = prepare_times(rows)
    mode, available_joints = detect_mode(fieldnames)

    print("Frames: {0}".format(len(rows)))
    print("Dauer: {0:.3f} Sekunden".format(times[-1]))
    print("Modus: {0}".format(mode))

    if mode == "cartesian":
        print("WARNUNG: Die CSV enthaelt nur Handpositionen.")
        print("Die Handbahn kann nachgefahren werden, die Ellbogenhaltung aus dem")
        print("Video ist damit jedoch mathematisch nicht eindeutig rekonstruierbar.")
        effectors, paths, masks, time_lists = load_cartesian_trajectory(rows, times)
        print_cartesian_diagnostics(effectors, paths)
    else:
        joints, angle_lists, time_lists = load_joint_trajectory(
            rows, available_joints, times
        )
        print("Verwendete Gelenke: {0}".format(", ".join(joints)))

    answer = ask_user("Bewegung starten? [ja/nein]: ").strip().lower()
    if answer != "ja":
        print("Bewegung abgebrochen.")
        return

    motion = ALProxy("ALMotion", IP, PORT)
    posture = ALProxy("ALRobotPosture", IP, PORT)

    motion.wakeUp()
    motion.setStiffnesses("Arms", ARM_STIFFNESS)
    time.sleep(STIFFNESS_RAMP_SECONDS)

    try:
        if not posture.goToPosture("StandInit", 0.5):
            raise RuntimeError("StandInit konnte nicht erreicht werden.")

        motion.setCollisionProtectionEnabled("Arms", USE_COLLISION_PROTECTION)
        motion.wbEnable(False)

        print("Starte Bewegung...")
        if mode == "joints":
            # isAbsolute=True: CSV enthaelt absolute NAO-Gelenkwinkel in Radiant.
            motion.angleInterpolation(joints, angle_lists, time_lists, True)
        else:
            motion.positionInterpolations(
                effectors,
                FRAME_TORSO,
                paths,
                masks,
                time_lists
            )

        print("Bewegung beendet.")

        if RETURN_TO_STAND_INIT:
            posture.goToPosture("StandInit", 0.35)
    finally:
        motion.wbEnable(False)
        if RELAX_ARMS_AFTERWARDS:
            motion.setStiffnesses("Arms", 0.0)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("FEHLER: {0}".format(error))
        sys.exit(1)
