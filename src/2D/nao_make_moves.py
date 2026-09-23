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

motion_proxy.stiffnessInterpolation("LShoulderPitch", 1.0, 1.0)
# Gelenk im Simulator bewegen
# Name, Zielwinkel (Radiant), Zeitdauer (Sekunden), Absolut?
# motion_proxy.angleInterpolation("LShoulderPitch", 2.0, 1.0, True)

with open('../../generated/nao_angles.csv', 'r') as file:
    angles_list = list(csv.DictReader(file))
    motion_proxy.stiffnessInterpolation(angles_list[0].keys(), 1.0, 0.5)
    for i in range(0, len(angles_list)):
        row = angles_list[i]
        # Motoren einschalten (Stiffness aktivieren)
        # Gelenk im Simulator bewegen
        # Name, Zielwinkel (Radiant), Zeitdauer (Sekunden), Absolut?
        motion_proxy.angleInterpolation(row.keys(), [float(i) for i in row.values()], 0.4, True)
        print("Winkel erfolgreich an Simulator übertragen!")