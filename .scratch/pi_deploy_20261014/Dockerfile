FROM ros:jazzy-ros-base-noble@sha256:066420e07f60aa18262f2479981def87ebcfcec42eefb0c0c57c4a46098348ca
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-mavros ros-jazzy-mavros-extras ros-jazzy-cv-bridge \
    ros-jazzy-web-video-server ros-jazzy-usb-cam ros-jazzy-xacro \
    ros-jazzy-robot-state-publisher ros-jazzy-py-trees \
    python3-opencv python3-numpy python3-scipy python3-serial \
    python3-websockets python3-pyzbar tesseract-ocr libzbar0 \
    geographiclib-tools \
    && /opt/ros/jazzy/lib/mavros/install_geographiclib_datasets.sh \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /home/aerothon && chown 1000:1000 /home/aerothon
ENV HOME=/home/aerothon ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=42
WORKDIR /workspace
