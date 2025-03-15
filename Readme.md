# VigilEyeX: AI-Powered Real-Time Violence Detection System

<div align="center">
  <h2>Making public spaces safer through intelligent surveillance</h2>
</div>

## Overview

VigilEyeX is an advanced surveillance system that leverages deep learning to detect violent incidents in real-time. By combining MobileNetv2 and LSTM networks, our system efficiently processes video feeds to identify potential security threats, automatically alerting authorities with enhanced imagery and precise location data.

Unlike traditional surveillance systems that require constant human monitoring, VigilEyeX operates autonomously, significantly reducing response times and improving public safety. Our solution is designed to be deployed on cost-effective hardware like Raspberry Pi, making it accessible for schools, campuses, and public facilities.

## Features

- **Real-time Violence Detection**: Processes video streams to identify violent incidents with high accuracy (96%)
- **Automated Alert System**: Sends immediate notifications via Telegram with incident details
- **Face Detection & Enhancement**: Utilizes MTCNN to identify and enhance images of individuals involved
- **Optimized for Edge Devices**: Engineered to run efficiently on Raspberry Pi and similar hardware
- **Privacy-Conscious Design**: Option to blur faces of non-involved individuals
- **Comprehensive Logging**: Maintains records of incidents with timestamps and locations for future analysis
- **Low Latency Processing**: Achieves near real-time performance with minimal processing delay

## Architecture

<!-- System architecture diagram would go here -->

Our system employs a two-stage deep learning approach:

1. **Spatial Feature Extraction**: MobileNetv2 processes each video frame to extract visual features
2. **Temporal Analysis**: LSTM networks analyze sequences of frames to detect patterns of violent behavior
3. **Alert Generation**: When violence is detected, the system:
   - Captures and enhances images of the incident
   - Detects and isolates faces of individuals involved
   - Sends alerts through Telegram with detailed information
   - Records the incident in a secure database

## Demo

<!-- Example of real-time violence detection and alert generation would go here -->

## Installation

### Prerequisites

- Python 3.8+
- TensorFlow 2.15
- OpenCV 4.7.0
- Raspberry Pi 4 (recommended) or similar hardware

### Quick Start

```bash
# Clone the repository
git clone https://github.com/VigilEyeX-Team/surveillance-system.git
cd vigileyex

# Install dependencies
pip install -r requirements.txt

# Configure your Telegram bot
cp config.example.py config.py
# Edit config.py with your Telegram bot token and chat ID

# Run the system
python vigileyex.py --source=0  # Use camera index 0
```



## Usage

### Basic Operation

```bash
# Start monitoring with default settings
python vigileyex.py --source=0

# Use a pre-recorded video file
python vigileyex.py --source=path/to/video.mp4

# Adjust detection sensitivity
python vigileyex.py --source=0 --threshold=0.65

# Enable face blurring for privacy
python vigileyex.py --source=0 --blur-faces
```

### Advanced Configuration

VigilEyeX can be extensively customized through the configuration file:

```python
# config.py
DETECTION_THRESHOLD = 0.60        # Violence detection confidence threshold
CONSECUTIVE_FRAMES = 30           # Required consecutive frames for alert
ALERT_COOLDOWN = 60               # Seconds between alerts
FACE_DETECTION_ENABLED = True     # Enable/disable face detection
IMAGE_ENHANCEMENT_LEVEL = 1.3     # Image sharpening factor
```



## Performance

Our system achieves state-of-the-art performance while maintaining real-time processing capabilities:

| Metric | Value |
|--------|-------|
| Violence Detection Accuracy | 96% |
| False Positive Rate | 4.3% |
| False Negative Rate | 3.7% |
| Processing Speed (Raspberry Pi 4) | 12-15 FPS |
| Processing Speed (Desktop GPU) | 25-30 FPS |
| Alert Generation Latency | <2 seconds |
| Model Size | 24.7 MB |
| RAM Usage | 380-450 MB |



## Research and Methodology

Our approach builds upon recent advancements in computer vision and deep learning for violence detection:

1. **Two-Stream Architecture**: We utilize spatial and temporal streams to capture both appearance and motion information
2. **Transfer Learning**: MobileNetv2 pre-trained on ImageNet provides a robust foundation for our spatial feature extraction
3. **Sequence Modeling**: LSTM networks analyze temporal patterns to distinguish between normal and violent activities
4. **Data Augmentation**: Extensive augmentation techniques ensure robustness across lighting conditions and camera angles
5. **Model Optimization**: Quantization and pruning techniques enable deployment on edge devices



## Future Work

We are actively working on several enhancements to the VigilEyeX system:

- **Audio Analysis**: Integrating sound detection for screams and aggressive speech
- **Multi-Camera Support**: Synchronized processing across multiple camera feeds
- **Weapon Detection**: Specialized models to identify potential weapons
- **Crowd Density Analysis**: Detecting unusual crowd movements or gatherings
- **Web Dashboard**: Comprehensive monitoring interface for security personnel

## Team

**VigilEyeX** was developed by students at Jaypee University of Information Technology, Waknaghat:

- **Aayush Sharma** (Roll No. 211193)
- **Parth Sharma** (Roll No. 211106)
- **Aditya Singh** (Roll No. 211194)

Under the supervision of **Dr. Rakesh Kanji**, Assistant Professor (SG), Department of Computer Science.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

We thank the following open-source projects and research papers that made this work possible:

- MobileNetv2 architecture by Sandler et al.
- MTCNN face detection implementation by Zhang et al.
- The Hockey Fight and Movies datasets for violence detection
- TensorFlow and OpenCV communities for their excellent tools and documentation

## Citation

If you use VigilEyeX in your research or project, please cite:

```
@article{sharma2025vigileyex,
  title={VigilEyeX: An AI-powered system for real-time monitoring and ensuring public safety},
  author={Sharma, Aayush and Sharma, Parth and Singh, Aditya and Kanji, Rakesh},
  institution={Jaypee University of Information Technology},
  year={2025}
}
```