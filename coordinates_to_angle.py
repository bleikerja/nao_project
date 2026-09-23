import csv
import math
import numpy as np
from sympy import true
from sympy.core import facts

coordinate_map = {
    "LShoulderRoll": ["L_Shoulder", "L_Elbow"],
    "LElbowRoll": ["L_Shoulder", "L_Elbow", "L_Wrist"],
    "LHipRoll": ["L_Hip", "L_Knee"],
    # "LKnee"
    "RShoulderRoll": ["R_Shoulder", "R_Elbow"],
    "RElbowRoll": ["R_Shoulder", "R_Elbow", "R_Wrist"],
    "RHipRoll": ["R_Hip", "R_Knee"],
    # "RKnee"
}

angles = []

def calculate_angle2(a: tuple[int, int], b: tuple[int, int], negate = true) -> float:
    a = math.atan2(b[1] - a[1], b[0] - a[0])
    a = a - math.pi / 2
    return normalize_angle((-1 if negate else 1) * a)

def calculate_angle3(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int], negate = true) -> float:
    vector_ba = np.array([a[0] - b[0], a[1] - b[1]])
    vector_bc = np.array([c[0] - b[0], c[1] - b[1]])

    cos = np.dot(vector_ba, vector_bc) / (np.linalg.norm(vector_ba) * np.linalg.norm(vector_bc))

    return normalize_angle((-1 if negate else 1) * (math.pi - math.acos(cos)))

def normalize_angle(a):
    return (a + math.pi) % (2 * math.pi) - math.pi

with open('roboter_bewegungsdaten.csv', 'r', encoding='utf-8', newline='') as file:
    reader = csv.DictReader(file)
    for row in reader:
        angles_row = {}
        for key in coordinate_map.keys():
            points = []
            for point in coordinate_map[key]:
                points.append((int(row[f"{point}_X"]),int(row[f"{point}_Y"])))

            if len(points) == 2:
                angle = calculate_angle2(*points)
            else:
                angle = calculate_angle3(*points, negate=key.startswith("L"))

            angles_row[key] = angle
        angles.append(angles_row)
    with open("nao_angles.csv", mode='w', newline='') as new_file:
        writer = csv.DictWriter(new_file, fieldnames=angles[0].keys())
        writer.writeheader() 
        writer.writerows(angles)
 
