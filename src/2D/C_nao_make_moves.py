# -*- coding: utf-8 -*-
import math
from naoqi import ALProxy  # Benötigt die NAOqi SDK (Python 2.7 Umgebung)
import csv

def set_angle_in_limits(angle_name, angle):
    limits = motion_proxy.getLimits(angle_name)
    return min(max(angle,limits[0][0]), limits[0][1])

# --- Senden an den Choregraphe-Simulator ---
IP = "127.0.0.1"  # Localhost für den Simulator
PORT = 63984      # Standardport des virtuellen Roboters in Choregraphe

JOINTS = ["LShoulderRoll", "LShoulderPitch", "LElbowRoll", "RShoulderRoll", "RShoulderPitch", "RElbowRoll"]

motion_proxy = ALProxy("ALMotion", IP, PORT)
bg_movement = ALProxy("ALBackgroundMovement", IP, PORT)
posture = ALProxy("ALRobotPosture", IP, PORT)

# 1. Hintergrundbewegungen ausschalten
bg_movement.setEnabled(False)
posture.goToPosture("StandInit", 1.0)
motion_proxy.setCollisionProtectionEnabled("Arms", True)
motion_proxy.wbEnable(True)
motion_proxy.wbEnableBalanceConstraint(True, "Legs")

with open('../../generated/nao_angles.csv', 'r') as file:
    angles_list = list(csv.DictReader(file))
    # Motoren einschalten (Stiffness aktivieren)
    motion_proxy.stiffnessInterpolation(JOINTS + ["LElbowYaw", "RElbowYaw"], 1.0, 0.5)
    motion_proxy.angleInterpolation(["LElbowYaw", "RElbowYaw"], [0.0, 0.0], 1.0, True)
    for i in range(0, len(angles_list)):
        row = angles_list[i]

        if float(row["RShoulderRoll"]) < -1.3265:
            row["RShoulderPitch"] = -math.pi / 2
            row["RShoulderRoll"] = -math.pi / 2 - (float(row["RShoulderRoll"]) + 1.3265)
        else:
            row["RShoulderPitch"] = math.pi / 2

        if float(row["LShoulderRoll"]) > 1.3265:
            row["LShoulderPitch"] = -math.pi / 2
            row["LShoulderRoll"] = math.pi / 2 - (float(row["LShoulderRoll"]) - 1.3265)
        else:
            row["LShoulderPitch"] = math.pi / 2

        for key in row.keys():
            row[key] = set_angle_in_limits(key, float(row[key]))

        # Gelenke bewegen
        motion_proxy.angleInterpolationWithSpeed(row.keys(), row.values(), 1)
        print("frame " + str(i) + " transferred successfully!")

bg_movement.setEnabled(True)