# STIMViewer
## Overview
STIMViewer is a GPU-accelerated image processing pipeline for the STIMscope fluorescence imaging microscope. This pipeline enables real-time neural activity analysis at 30 FPS with CUDA-optimized algorithms. The system is currently designed and opimized for usage with ARM64 platforms (primarily NVIDIA Jetson Platform on Ubuntu 20.04 LTS). Currently, the system only works for IDS Camera Sensors, but support for a in-house MIPI image sensor system and general support (w/ reduced features) for all image sensors is in progress. Projection is primarily done through a Texas Instruments DMD DLP4710, but most to all projectors are supported through the program.

## Requirements 
- NVIDIA Jetson platform (tested using ARM64 AGX Orin)
- Ubuntu (tested on 20.04), support for Windows and MacOS coming soon
- STIMScope setup
  - IDS Imaging Sensor
  - DMD/Projector (tested using Texas Instruments DMD DLP4710, but most projectors should be supported)
  - Waveform generator (for Hardware Triggering)


## Installation

```
git clone https://github.com/smalex-z/STIMViewer.git
cd STIMViewer
TODO: Requirements
usr/bin/python3 main_gui.py
```

## Demo

TODO: Demo
