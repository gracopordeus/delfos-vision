
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
from gi.repository import Gst, GstApp, GLib

import cv2
import numpy as np
import onnxruntime
import json
import os
import sys

# Add utils directory to sys.path for importing estimate_distance
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from estimate_distance import estimate_distance

# Initialize GStreamer
Gst.init(None)

class VideoAnalysisPipeline:
    def __init__(self, config_path, model_path, input_uri, srt_output_uri):
        self.config_path = config_path
        self.model_path = model_path
        self.input_uri = input_uri
        self.srt_output_uri = srt_output_uri

        self.config = self._load_config()
        self.focal_length = self.config.get("camera_focal_length_pixels", 0.0)
        self.object_real_widths = self.config.get("object_real_widths_cm", {})

        # Configure ONNX Runtime session options for VPS compatibility
        session_options = onnxruntime.SessionOptions()
        session_options.inter_op_num_threads = 1
        session_options.intra_op_num_threads = 1
        session_options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
        
        # Create session with conservative settings
        self.session = onnxruntime.InferenceSession(
            self.model_path, 
            sess_options=session_options,
            providers=['CPUExecutionProvider']
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]

        self.pipeline = None
        self._build_pipeline()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            print(f"Error: config.json not found at {self.config_path}")
            return {}
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def _build_pipeline(self):
        if self.input_uri.startswith("http://") or self.input_uri.startswith("https://"):
            input_pipeline_str = f"souphttpsrc location={self.input_uri} ! hlsdemux ! decodebin ! videoconvert ! video/x-raw,format=BGR ! appsink name=mysink"
        else:
            input_pipeline_str = f"filesrc location={self.input_uri} ! decodebin ! videoconvert ! video/x-raw,format=BGR ! appsink name=mysink"
        
        # Output pipeline (appsrc -> encode H.265 -> srtsink)
        # Note: The resolution and framerate should ideally match the input or be configured.
        # For simplicity, we'll assume a common resolution for the appsrc.
        output_pipeline_str = (
            f"appsrc name=mysource is-live=true format=time "
            f"caps=video/x-raw,format=BGR,width=640,height=480,framerate=30/1 ! "
            f"videoconvert ! x265enc ! h265parse ! mpegtsmux ! srtsink uri={self.srt_output_uri}"
        )

        full_pipeline_str = f"{input_pipeline_str} {output_pipeline_str}"
        self.pipeline = Gst.parse_launch(full_pipeline_str)

        self.appsink = self.pipeline.get_by_name("mysink")
        self.appsink.set_property("emit-signals", True)
        self.appsink.connect("new-sample", self._on_new_sample)

        self.appsrc = self.pipeline.get_by_name("mysource")
        # Set appsrc callbacks for handling data requests (push mode)
        self.appsrc.set_property("emit-signals", True)
        self.appsrc.connect("need-data", self._on_need_data)
        self.appsrc.connect("enough-data", self._on_enough_data)

    def _on_new_sample(self, sink):
        sample = sink.pull_sample()
        if sample:
            buffer = sample.get_buffer()
            caps = sample.get_caps()
            
            # Extract frame data
            # GStreamer buffer to numpy array
            # This part might need adjustment based on the exact caps format
            # Assuming BGR format for OpenCV
            width = caps.get_structure(0).get_value("width")
            height = caps.get_structure(0).get_value("height")
            
            # Ensure buffer data is contiguous for numpy
            success, mapinfo = buffer.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR

            frame_np = np.frombuffer(mapinfo.data, dtype=np.uint8).reshape((height, width, 3))
            buffer.unmap(mapinfo)

            processed_frame = self._process_frame(frame_np)
            
            # Push processed frame to appsrc
            self._push_frame_to_appsrc(processed_frame)

            return Gst.FlowReturn.OK
        return Gst.FlowReturn.ERROR

    def _process_frame(self, frame):
        # Preprocess frame for ONNX model (resize, normalize, etc.)
        # This is highly dependent on the specific MobileNet-SSD model's input requirements
        input_shape = self.session.get_inputs()[0].shape
        # Assuming input_shape is [1, H, W, 3] or [1, 3, H, W]
        # For MobileNet-SSD, typically it's [1, 300, 300, 3] or [1, 3, 300, 300]
        
        # Example preprocessing for a 300x300 input, assuming BGR and then converting to RGB if needed
        # and normalizing to [0, 1] or [-1, 1]
        resized_frame = cv2.resize(frame, (input_shape[2], input_shape[3])) # Assuming H, W are at index 2,3
        input_data = resized_frame.astype(np.float32)
        # Normalize if required by the model (e.g., / 255.0 or mean/std normalization)
        # input_data = (input_data / 127.5) - 1.0 # Example for [-1, 1] normalization
        input_data = np.expand_dims(input_data, axis=0) # Add batch dimension

        # If model expects NCHW, convert from NHWC
        if input_shape[1] == 3: # Check if channel is at index 1 (NCHW)
            input_data = input_data.transpose(0, 3, 1, 2) # NHWC to NCHW

        # Run inference
        outputs = self.session.run(self.output_names, {self.input_name: input_data})

        # Post-process outputs (parse detections, draw bounding boxes, estimate distance)
        # The output format of MobileNet-SSD can vary (e.g., detections, scores, classes)
        # This is a generic placeholder for drawing and distance estimation
        
        # Assuming outputs[0] contains detections in format [batch, num_detections, [ymin, xmin, ymax, xmax, score, class_id]]
        # Or similar, you'll need to adapt this based on your specific model's output.
        
        # Placeholder for parsing detections
        detections = outputs[0][0] # Assuming batch size 1

        for detection in detections:
            score = detection[2] # Example: score at index 2
            if score > 0.5: # Confidence threshold
                # Bounding box coordinates (normalized [0,1] or absolute)
                # Assuming normalized coordinates for now
                xmin, ymin, xmax, ymax = detection[3:7] # Example: bbox at index 3-6
                
                # Convert to absolute coordinates
                x1 = int(xmin * frame.shape[1])
                y1 = int(ymin * frame.shape[0])
                x2 = int(xmax * frame.shape[1])
                y2 = int(ymax * frame.shape[0])

                object_width_pixels = x2 - x1
                class_id = int(detection[1]) # Example: class_id at index 1
                
                # Map class_id to object type string (you'll need a class_id to name mapping)
                # For now, let's use a dummy mapping or assume a generic "object"
                object_type = "object" 
                if class_id in self.object_real_widths: # This needs a proper mapping
                    # This is a simplified example. You'd need a mapping from model's class_id to string.
                    # For now, let's just use a generic "object" or a hardcoded one for testing.
                    pass # Placeholder for actual class name mapping

                # Estimate distance
                distance = 0.0
                if self.focal_length > 0 and object_type in self.object_real_widths:
                    distance = estimate_distance(
                        object_width_pixels, 
                        self.object_real_widths[object_type], 
                        self.focal_length
                    )

                # Draw bounding box and text
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{object_type}: {score:.2f} Dist: {distance:.2f}cm"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame

    def _push_frame_to_appsrc(self, frame):
        # Convert numpy array to GStreamer buffer
        # Ensure the frame is in the correct format (e.g., BGR)
        data = frame.tobytes()
        buf = Gst.Buffer.new_wrapped(data)
        self.appsrc.emit("push-buffer", buf)

    def _on_need_data(self, appsrc, length):
        # This callback is for when appsrc needs data.
        # In our push-based model, we push data from _on_new_sample,
        # so this might not be strictly necessary if we always have data.
        # However, it's good practice to have it.
        pass

    def _on_enough_data(self, appsrc):
        # This callback is for when appsrc has enough data.
        pass

    def run(self):
        print("Starting GStreamer pipeline...")
        self.pipeline.set_state(Gst.State.PLAYING)
        try:
            # Run the GLib main loop
            loop = GLib.MainLoop()
            loop.run()
        except KeyboardInterrupt:
            print("Stopping pipeline...")
            self.pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    # Example usage:
    # python main.py --input-uri /path/to/your/video.mp4 --srt-output-uri srt://127.0.0.1:1234
    
    import argparse

    parser = argparse.ArgumentParser(description="Video Analysis Pipeline with Object Detection and Distance Estimation.")
    parser.add_argument("--config-path", type=str, default="../config.json",
                        help="Path to the configuration file (config.json).")
    parser.add_argument("--model-path", type=str, default="../models/mobilenet_ssd_quantized.onnx",
                        help="Path to the ONNX model file.")
    parser.add_argument("--input-uri", type=str, required=True,
                        help="Input video URI (e.g., file:///path/to/video.mp4 or rtsp://...).")
    parser.add_argument("--srt-output-uri", type=str, required=True,
                        help="SRT output URI (e.g., srt://<ip_destino>:<porta>).")

    args = parser.parse_args()

    # Adjust paths to be absolute relative to the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..')

    config_abs_path = os.path.join(project_root, args.config_path)
    model_abs_path = os.path.join(project_root, args.model_path)

    pipeline = VideoAnalysisPipeline(
        config_path=config_abs_path,
        model_path=model_abs_path,
        input_uri=args.input_uri,
        srt_output_uri=args.srt_output_uri
    )
    pipeline.run()
