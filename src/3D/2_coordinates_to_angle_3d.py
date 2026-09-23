import csv
import math
from pathlib import Path

import numpy as np


INPUT_FILE = "../../generated/roboter_bewegungsdaten_3d.csv"
OUTPUT_FILE = "../../generated/nao_angles_3d.csv"
MIN_VISIBILITY = 0.6

# Gelenke: (proximaler Punkt, Gelenkpunkt, distaler Punkt).
ANGLE_DEFINITION = {
    "LShoulderRoll": ("LHipRoll", "LShoulderRoll", "LElbowRoll"),
    "LElbowRoll": ("LShoulderRoll", "LElbowRoll", "LWrist"),
    "RShoulderRoll": ("RHipRoll", "RShoulderRoll", "RElbowRoll"),
    "RElbowRoll": ("RShoulderRoll", "RElbowRoll", "RWrist"),
    "LHipRoll": ("LShoulderRoll", "LHipRoll", "LKnee"),
    "RHipRoll": ("RShoulderRoll", "RHipRoll", "RKnee"),
    "LKnee": ("LHipRoll", "LKnee", "LAnkle"),
    "RKnee": ("RHipRoll", "RKnee", "RAnkle"),
}


def point(row, name):
    values = [float(row[f"{name}_{axis}"]) for axis in "XYZ"]
    visibility = float(row.get(f"{name}_visibility", 1.0) or 0.0)
    return np.asarray(values, dtype=float), visibility


def angle_at(a, b, c):
    first = a - b
    second = c - b
    first_length = np.linalg.norm(first)
    second_length = np.linalg.norm(second)
    if first_length == 0 or second_length == 0:
        return None
    cosine = np.dot(first, second) / (first_length * second_length)
    return math.acos(float(np.clip(cosine, -1.0, 1.0)))


def main():
    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))

    output_fields = ["Frame"] + list(ANGLE_DEFINITION)
    with output_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=output_fields)
        writer.writeheader()

        for row in rows:
            output = {"Frame": row["Frame"]}
            for joint, (first_name, joint_name, last_name) in ANGLE_DEFINITION.items():
                try:
                    first, first_visibility = point(row, first_name)
                    joint_point, joint_visibility = point(row, joint_name)
                    last, last_visibility = point(row, last_name)
                    if min(first_visibility, joint_visibility, last_visibility) < MIN_VISIBILITY:
                        output[joint] = ""
                    else:
                        value = angle_at(first, joint_point, last)
                        output[joint] = "" if value is None else value
                except (KeyError, TypeError, ValueError):
                    output[joint] = ""
            writer.writerow(output)

    print(f"3D-Winkel gespeichert: {output_path}")


if __name__ == "__main__":
    main()
