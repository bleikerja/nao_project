# -*- coding: utf-8 -*-
from A_detect_points import detect_points
from B_coordinates_to_angle import coordinates_to_angle
import subprocess

detect_points("../../example-data/downloaded_video_2_hell.avi")
coordinates_to_angle()

subprocess.run([
    r"C:\Python27\python.exe",
    "C_nao_make_moves.py"
])