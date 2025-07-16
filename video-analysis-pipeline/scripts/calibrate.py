
import cv2
import json
import os

def calibrate_camera(known_width_cm, known_distance_cm, image_path):
    """
    This is a placeholder for the camera calibration script.
    In a real scenario, this would involve:
    1. Loading an image of a known object at a known distance.
    2. Manually or automatically detecting the object in the image.
    3. Measuring the object's width in pixels.
    4. Calculating the focal length using the formula:
       Focal_Length = (Object_Width_in_Pixels * Known_Distance) / Known_Width_of_Object
    5. Saving the focal length to config.json.
    """
    print(f"Calibrating camera using image: {image_path}")
    print(f"Known object width: {known_width_cm} cm, Known distance: {known_distance_cm} cm")

    # Simulate object detection and pixel measurement
    # In a real scenario, you'd use OpenCV to detect and measure
    object_width_pixels = 200 # Example: object appears 200 pixels wide in the image

    if object_width_pixels == 0:
        print("Error: Object not detected or pixel width is zero.")
        return None

    focal_length = (object_width_pixels * known_distance_cm) / known_width_cm
    print(f"Calculated Focal Length: {focal_length:.2f} pixels")

    return focal_length

if __name__ == "__main__":
    # Example usage (placeholders)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(base_dir, '..')
    config_path = os.path.join(project_root, 'config.json')
    calibration_image_path = os.path.join(project_root, 'data', 'calibration_image_1.jpg')

    # Dummy calibration parameters
    known_width_of_object_cm = 21.0  # e.g., A4 paper width
    known_distance_from_camera_cm = 50.0 # e.g., 50 cm away

    focal_length_result = calibrate_camera(
        known_width_of_object_cm,
        known_distance_from_camera_cm,
        calibration_image_path
    )

    if focal_length_result:
        # Load existing config or create new
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)

        config["camera_focal_length_pixels"] = focal_length_result
        
        # Add dummy object real widths if not present
        if "object_real_widths_cm" not in config:
            config["object_real_widths_cm"] = {
                "person": 50,
                "car": 180
            }

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Focal length saved to {config_path}")
    else:
        print("Calibration failed. Focal length not saved.")
