# Use an official Ubuntu image as a base
FROM ubuntu:22.04

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install system dependencies
# This includes Python3, pip, and all necessary GStreamer packages for video processing
# and SRT streaming.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-gi \
    python3-gst-1.0 \
    gir1.2-gstreamer-1.0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-rtsp \
    gstreamer1.0-plugins-base-apps \
    gstreamer1.0-tools \
    libgstrtspserver-1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer1.0-dev \
    build-essential \
    git \
    curl \
    && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Create models directory and download ONNX models
RUN mkdir -p models && \
    echo "Downloading MobileNet-SSD ONNX models..." && \
    curl -L -o models/mobilenet_ssd_quantized.onnx "https://github.com/onnx/models/raw/main/validated/vision/object_detection_segmentation/ssd-mobilenetv1/model/ssd_mobilenet_v1_10.onnx" && \
    curl -L -o models/mobilenet_ssd.onnx "https://github.com/onnx/models/raw/main/validated/vision/object_detection_segmentation/ssd-mobilenetv1/model/ssd_mobilenet_v1_10.onnx" && \
    echo "Models downloaded successfully. Checking file sizes:" && \
    ls -lh models/ && \
    echo "Verifying model files are not empty:" && \
    test -s models/mobilenet_ssd_quantized.onnx && \
    test -s models/mobilenet_ssd.onnx && \
    echo "✅ All models downloaded and verified successfully!"

# Copy the rest of the application code
COPY . .

# Expose the SRT port (example, adjust as needed)
# This is the port where the SRT stream will be sent from the container
EXPOSE 1234

# Command to run the application
# This is a default command. Users can override it when running the container.
# Example usage:
# docker run -it --rm -p 1234:1234/udp video-analysis-pipeline \
#   python3 scripts/main.py --input-uri "rtmp://your_rtmp_server/live/stream_key" --srt-output-uri "srt://0.0.0.0:1234"
CMD ["python3", "scripts/main.py"]
