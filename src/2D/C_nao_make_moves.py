# -*- coding: utf-8 -*-
import math
import csv

from naoqi import ALProxy  # Benötigt die NAOqi SDK (Python 2.7 Umgebung)

# --- Senden an den Choregraphe-Simulator ---
IP = "127.0.0.1"  # Localhost für den Simulator
PORT = 63984      # Port des virtuellen Roboters in Choregraphe

# --- Timing ---
FRAME_DURATION = 0.1    # Sekunden pro Frame
START_DELAY = 1.0       # Zeit, um von StandInit in den ersten Frame zu fahren
MAX_SPEED = 3.0         # rad/s, maximale Geschwindigkeit pro Gelenk

# --- Kollisionsschutz Arm/Körper (nur wenn der Arm nach unten zeigt) ---
MIN_SHOULDER_ROLL = 0.15  # rad, Mindestabstand des Oberarms vom Körper
UPPER_ARM = 105.0         # mm, Länge Oberarm NAO
FOREARM = 114.0           # mm, Länge Unterarm + Hand NAO (ca.)
MIN_HAND_OFFSET = 0.0     # mm, Hand darf nicht weiter innen sein als die Schulter

JOINT_NAMES = ["ShoulderPitch", "ShoulderRoll", "ElbowRoll"]
JOINTS = (["L" + j for j in JOINT_NAMES] + ["R" + j for j in JOINT_NAMES])


def read_frames(path):
    with open(path, 'r') as f:
        return [dict((k, float(v)) for k, v in row.items()) for row in csv.DictReader(f)]


def max_safe_bend(roll_out):
    """Maximale Ellbogenbeugung, bei der die Hand nicht in den Körper fährt."""
    x = (MIN_HAND_OFFSET - UPPER_ARM * math.sin(roll_out)) / FOREARM
    return roll_out - math.asin(min(1.0, max(-1.0, x)))

def clamp_angles_to_limits(frame, limits):
    for j in frame:
        frame[j] = min(max(frame[j], limits[j][0]), limits[j][1])


def rate_limit(frames, start, times):
    """Begrenzt die Winkeländerung pro Frame."""
    previous, previous_time = start, 0.0
    for frame, t in zip(frames, times):
        max_step = MAX_SPEED * (t - previous_time)
        for j in frame:
            delta = frame[j] - previous[j]
            frame[j] = previous[j] + min(max(delta, -max_step), max_step)
        previous, previous_time = frame, t


def make_moves():
    motion_proxy = ALProxy("ALMotion", IP, PORT)
    bg_movement = ALProxy("ALBackgroundMovement", IP, PORT)
    posture = ALProxy("ALRobotPosture", IP, PORT)

    bg_movement.setEnabled(False)
    posture.goToPosture("StandInit", 1.0)
    motion_proxy.setCollisionProtectionEnabled("Arms", True)
    motion_proxy.stiffnessInterpolation(JOINTS + ["LElbowYaw", "RElbowYaw"], 1.0, 0.5)

    # ElbowYaw einmal auf 0: Ellbogen beugt dann in der Frontalebene
    motion_proxy.angleInterpolation(["LElbowYaw", "RElbowYaw"], [0.0, 0.0], 1.0, True)

    limits = dict((j, motion_proxy.getLimits(j)[0][:2]) for j in JOINTS)
    start_angles = dict(zip(JOINTS, motion_proxy.getAngles(JOINTS, True)))

    frames = []
    for row in read_frames('../../generated/nao_angles.csv'):
        if row["RShoulderRoll"] < -1.3265:
            row["RShoulderPitch"] = -math.pi / 2
            row["RShoulderRoll"] = -math.pi / 2 - (row["RShoulderRoll"] + 1.3265)
        else:
            row["RShoulderPitch"] = math.pi / 2
            # Kollisionsschutz: Arm nicht zu nah am Körper, Hand nicht in den Körper
            row["RShoulderRoll"] = min(row["RShoulderRoll"], -MIN_SHOULDER_ROLL)
            row["RElbowRoll"] = min(row["RElbowRoll"], max_safe_bend(-row["RShoulderRoll"]))

        if row["LShoulderRoll"] > 1.3265:
            row["LShoulderPitch"] = -math.pi / 2
            row["LShoulderRoll"] = math.pi / 2 - (row["LShoulderRoll"] - 1.3265)
        else:
            row["LShoulderPitch"] = math.pi / 2
            # Kollisionsschutz: Arm nicht zu nah am Körper, Hand nicht in den Körper
            row["LShoulderRoll"] = max(row["LShoulderRoll"], MIN_SHOULDER_ROLL)
            row["LElbowRoll"] = max(row["LElbowRoll"], -max_safe_bend(row["LShoulderRoll"]))

        frame = dict((j, row[j]) for j in JOINTS)
        clamp_angles_to_limits(frame, limits)
        frames.append(frame)

    times = [START_DELAY + i * FRAME_DURATION for i in range(len(frames))]
    rate_limit(frames, start_angles, times)

    # Gesamte Bewegung auf einmal schicken: NAOqi interpoliert glatt zwischen den Frames
    angle_lists = [[frame[j] for frame in frames] for j in JOINTS]
    time_lists = [times] * len(JOINTS)
    print("sending " + str(len(frames)) + " frames ...")
    motion_proxy.angleInterpolation(JOINTS, angle_lists, time_lists, True)
    print("done")

    bg_movement.setEnabled(True)

if __name__ == "__main__":
    make_moves()
