
import cv2
import numpy as np
import json
import os

def estimate_distance(object_width_in_pixels, known_width_in_cm, focal_length_in_pixels):
    """
    Estimates the distance to an object using similar triangles.
    Formula: Distance = (Known_Width_of_Object * Focal_Length) / Object_Width_in_Pixels
    """
    if object_width_in_pixels == 0:
        return 0.0
    distance = (known_width_in_cm * focal_length_in_pixels) / object_width_in_pixels
    return distance

if __name__ == "__main__":
    # Example usage (placeholders)
    # In a real scenario, focal_length and object_real_widths would come from config.json
    
    # Dummy config for demonstration
    config = {
        "camera_focal_length_pixels": 1000,
        "object_real_widths_cm": {
            "person": 50,
            "car": 180
        }
    }

    # Simulate an object detection result
    detected_object_width_pixels = 100 # Example: object detected as 100 pixels wide
    object_type = "person"

    focal_length = config["camera_focal_length_pixels"]
    known_width = config["object_real_widths_cm"].get(object_type, 0)

    if known_width > 0:
        distance = estimate_distance(detected_object_width_pixels, known_width, focal_length)
        print(f"Estimated distance to {object_type}: {distance:.2f} cm")
    else:
        print(f"Known width for object type '{object_type}' not found in config.")
