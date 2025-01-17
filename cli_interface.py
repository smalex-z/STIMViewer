# \file    cli_interface.py
# \author  IDS Imaging Development Systems GmbH
# \date    2024-02-20
#
# \brief   This sample showcases the usage of the ids_peak API
#          in setting camera parameters, starting/stopping the image acquisition
#          and how to record a video using the ids_peak_ipl API.
#
# \version 1.0
#
# Copyright (C) 2024, IDS Imaging Development Systems GmbH.
#
# The information in this document is subject to change without notice
# and should not be construed as a commitment by IDS Imaging Development Systems GmbH.
# IDS Imaging Development Systems GmbH does not assume any responsibility for any errors
# that may appear in this document.
#
# This document, or source code, is provided solely as an example of how to utilize
# IDS Imaging Development Systems GmbH software libraries in a sample application.
# IDS Imaging Development Systems GmbH does not assume any responsibility
# for the use or reliability of any portion of this document.
#
# General permission to copy or modify is hereby granted.

import threading
import time

from typing import Optional

from camera import Camera, RecordingStatistics


class Interface:
    """
    Interface provides methods to interact with the camera on the command line,
    but it is not necessary to understand how to use the API of ids_peak or
    ids_peak_ipl.
    """

    def __init__(self, cam_module: Optional[Camera] = None):
        self._camera = cam_module
        self._acquisition_thread: Optional[threading.Thread] = None

    # Common interface start

    def set_camera(self, cam_module:Camera):
        self._camera = cam_module

    def start_window(self):
        pass

    def start_interface(self):
        self.prompt()

    def information(self, message: str):
        print(message)

    def warning(self, message: str):
        print("Warning:", message)

    def on_image_received(self, image):
        pass

    def done_recording(self, stats: RecordingStatistics):
        if stats.frames_encoded != 0:
            print("Recording done!\n"
                  "Statistics:\n"
                  f"  Total Frames recorded: {stats.frames_encoded}\n"
                  f"  Frames dropped by video recorder: {stats.frames_video_dropped}\n"
                  f"  Frames dropped by image stream: {stats.frames_stream_dropped}\n"
                  f"  Frames lost by image stream: {stats.frames_lost_stream}\n"
                  f"  Frame rate: {stats.fps()}")

    # Common interface end

    def print_help(self):
        print("Commands:\n"
              "help: Display help text\n"
              "exit: Exit the program (alias quit)\n"
              "set_framerate: Set the target framerate\n"
              "set_gain: Set the gain\n"
              "start: Start the image acquisition record a video")

    def get_value(self, prompt_text: str, default: float):
        while True:
            string = input(prompt_text)
            if not string.strip():
                continue

            try:
                return float(string)
            except ValueError:
                print(f"Error: '{string}' is not convertible to a float!")

    def prompt(self):
        if self._camera is None:
            raise RuntimeError("Missing camera!")

        self.print_help()
        try:
            while True:
                command = input("> ").strip()
                if command in ("quit", "exit"):
                    break
                elif command == "help":
                    self.print_help()
                elif command == "set_framerate":
                    self._camera.target_fps = self.get_value(
                        f"Camera framerate (current: {self._camera.target_fps:.2f}): ",
                        self._camera.target_fps)
                elif command == "set_gain":
                    self._camera.target_gain = self.get_value(
                        f"Camera gain (current: {self._camera.target_gain:.2f}): ",
                        self._camera.target_gain)
                elif command == "start":
                    print("Will use the following settings for recording:\n"
                          f"Camera framerate: {self._camera.target_fps:.2f}\n"
                          f"Camera gain:      {self._camera.target_gain:.2f}")
                    self._camera.start_recording = True
                    while self._camera.start_recording:
                        time.sleep(0.01)
                else:
                     print(f"Command: {command} not found!")
        except KeyboardInterrupt:
            print("KeyboardInterrupt: Stopping...")
        finally:
            self._camera.killed = True
            if self._acquisition_thread is not None:
                self._acquisition_thread.join()
