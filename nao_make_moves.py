# -*- coding: utf-8 -*-
import math
from naoqi import ALProxy  # Benötigt die NAOqi SDK (Python 2.7 Umgebung)
import csv
import time

# --- Senden an den Choregraphe-Simulator ---
IP = "127.0.0.1"  # Localhost für den Simulator
PORT = 60996      # Standardport des virtuellen Roboters in Choregraphe

motion_proxy = ALProxy("ALMotion", IP, PORT)
bg_movement = ALProxy("ALBackgroundMovement", IP, PORT)

# 1. Hintergrundbewegungen ausschalten (verhindert das Zurückzucken)
bg_movement.setEnabled(False)


with open('nao_angles.csv', 'r') as file:
    angles_list = list(csv.DictReader(file))
    for i in range(0, len(angles_list), 10):
        row = angles_list[i]
        # Motoren einschalten (Stiffness aktivieren)
        motion_proxy.stiffnessInterpolation(row.keys(), 1.0, 0.5)
        # Gelenk im Simulator bewegen
        # Name, Zielwinkel (Radiant), Zeitdauer (Sekunden), Absolut?
        motion_proxy.angleInterpolation(row.keys(), [float(i) for i in row.values()], 0.5, True)
        print("Winkel erfolgreich an Simulator übertragen!")