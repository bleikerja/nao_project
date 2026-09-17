import csv
import math


coordinate_map = {
    "LShoulderRoll": "LElbowRoll",
    "LElbowRoll": "RWrist",
    "LHipRoll": "LKnee",
    # "LKnee": "LAnkle",
    "RShoulderRoll": "RElbowRoll",
    "RElbowRoll": "RWrist",
    "RHipRoll": "RKnee",
    # "RKnee": "RAnkle"
}

angles = []

def calculate_angle(x_1, y_1, x_2, y_2) -> float:
    return math.atan2(y_2 - y_1, x_2 - x_1)

with open('roboter_bewegungsdaten.csv', 'r', encoding='utf-8', newline='') as file:
    reader = csv.DictReader(file)
    for row in reader:
        angles_row = {}
        for key in coordinate_map.keys():
            x1_key = f"{key}_X"
            y1_key = f"{key}_Y"
            x2_key = f"{coordinate_map[key]}_X"
            y2_key = f"{coordinate_map[key]}_Y"
            
            x1 = int(row[x1_key])
            y1 = int(row[y1_key])
            x2 = int(row[x2_key])
            y2 = int(row[y2_key])
            
            angle = calculate_angle(x1, y1, x2, y2)
            angles_row[key] = angle
        angles.append(angles_row)
    print(angles)
    with open("nao_angles.csv", mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=angles[0].keys())
        writer.writeheader() 
        writer.writerows(angles)
 
