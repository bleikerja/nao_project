# -*- coding: utf-8 -*-
import math
from naoqi import ALProxy  # Benötigt die NAOqi SDK (Python 2.7 Umgebung)
import csv
import time

# --- Senden an den Choregraphe-Simulator ---
IP = "127.0.0.1"  # Localhost für den Simulator
PORT = 63984      # Standardport des virtuellen Roboters in Choregraphe

motion_proxy = ALProxy("ALMotion", IP, PORT)
bg_movement = ALProxy("ALBackgroundMovement", IP, PORT)

# 1. Hintergrundbewegungen ausschalten (verhindert das Zurückzucken)
bg_movement.setEnabled(False)

with open('../../generated/nao_angles.csv', 'r') as file:
    angles_list = list(csv.DictReader(file))
    angle_name_list = list(angles_list[0].keys())
    angle_name_list.append("RShoulderPitch")
    angle_name_list.append("RElbowYaw")
    angle_name_list.append("LShoulderPitch")
    angle_name_list.append("LElbowYaw")
    # Motoren einschalten (Stiffness aktivieren)
    motion_proxy.stiffnessInterpolation(angle_name_list, 1.0, 0.5)
    for i in range(0, len(angles_list)):
        row = angles_list[i]

        if float(row["RShoulderRoll"]) < -1.3265:
            row["RShoulderPitch"] = -math.pi / 2
            row["RElbowYaw"] = 0
            row["RShoulderRoll"] = -math.pi / 2 - (float(row["RShoulderRoll"]) + 1.3265)
        else:
            row["RShoulderPitch"] = math.pi / 2

        if float(row["LShoulderRoll"]) > 1.3265:
            row["LShoulderPitch"] = -math.pi / 2
            row["LElbowYaw"] = 0
            row["LShoulderRoll"] = math.pi / 2 - (float(row["LShoulderRoll"]) - 1.3265)
        else:
            row["LShoulderPitch"] = math.pi / 2

        if abs(float(row["RHipRoll"])) < 0.2:
            row["RHipRoll"] = 0
        if abs(float(row["LHipRoll"])) < 0.2:
            row["LHipRoll"] = 0

        # Gelenke im Simulator bewegen
        # Namen, Zielwinkel (Radiant), Zeitdauer (Sekunden), Absolut?
        motion_proxy.setAngles(row.keys(), [float(j) for j in row.values()], 1)
        time.sleep(0.1)
        print("frame " + str(i) + " transferred successfully!")

bg_movement.setEnabled(True)