# \file    camera.py
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

import os
import time

from os.path import exists
from video_recorder import VideoRecorder
from collections import deque
from ids_peak import ids_peak
from ids_peak_ipl import ids_peak_ipl
from ids_peak import ids_peak_ipl_extension


TARGET_PIXEL_FORMAT = ids_peak_ipl.PixelFormatName_BGRa8
os.environ["LD_PRELOAD"] = os.environ.get("LD_PRELOAD", "") + ":/lib/aarch64-linux-gnu/libGLdispatch.so.0"
os.environ["QT_XCB_GL_INTEGRATION"] = "none"

class Camera:
    def __init__(self, device_manager, interface):
        if interface is None:
            raise ValueError("Interface is None")

        self.device_manager = device_manager
        self._interface = interface
        self._device = None
        self._datastream = None
        self.acquisition_mode = 0 #0: Real Time, #1: HW Trigger, #2: SW Trigger
        self.acquisition_running = False
        self.node_map = None
        self._buffer_list = []

        self.target_gain = 1
        self.max_gain = 1
        self.killed = False
        self.save_image = False
        self.frame_times = deque(maxlen=120)  # ✅ Store timestamps of the last 120 frames

        self._get_device()
        self._setup_device_and_datastream()
        self._interface.set_camera(self)

        self._image_converter = ids_peak_ipl.ImageConverter()
        self.video_recorder = VideoRecorder(interface)  # ✅ Initialize video recorder


    def __del__(self):
        self.close()

    def _get_device(self):
        # Update device manager to refresh the camera list
        self.device_manager.Update()
        if self.device_manager.Devices().empty():
            print("No device found. Exiting Program.")
            sys.exit(1)
        selected_device = None

        # Initialize first device found if only one is available
        if len(self.device_manager.Devices()) == 1:
            selected_device = 0
        else:
            # List all available devices
            for i, device in enumerate(self.device_manager.Devices()):
                print(
                    f"{str(i)}:  {device.ModelName()} ("
                    f"{device.ParentInterface().DisplayName()} ; "
                    f"{device.ParentInterface().ParentSystem().DisplayName()} v." 
                    f"{device.ParentInterface().ParentSystem().version()})")
            while True:
                try:
                    # Let the user decide which device to open
                    selected_device = int(input("Select device to open: "))
                    if selected_device < len(self.device_manager.Devices()):
                        break
                    else:
                        print("Invalid ID.")
                except ValueError:
                    print("Please enter a correct id.")
                    continue

        # Opens the selected device in control mode
        self._device = self.device_manager.Devices()[selected_device].OpenDevice(
            ids_peak.DeviceAccessType_Control)
        self.node_map = self._device.RemoteDevice().NodeMaps()[0]

        self.max_gain = self.node_map.FindNode("Gain").Maximum()

        # Load the default settings
        self.node_map.FindNode("UserSetSelector").SetCurrentEntry("Default")
        self.node_map.FindNode("UserSetLoad").Execute()
        self.node_map.FindNode("UserSetLoad").WaitUntilDone()
    
    def get_actual_fps(self):
        """Calculate FPS as the average over the last 2 seconds."""
        current_time = time.time()
        self.frame_times.append(current_time)  # ✅ Store current timestamp

        # ✅ Remove timestamps older than 2 seconds
        while self.frame_times and self.frame_times[0] < current_time - 2:
            self.frame_times.popleft()

        # ✅ Calculate FPS based on the number of frames in the last 2 seconds
        if len(self.frame_times) > 1:
            self.GUIfps = round(len(self.frame_times) / 2)  # Average over 2 seconds
        else:
            self.GUIfps = 0  # No frames captured in the last 2 seconds

        return self.GUIfps

    def _init_data_stream(self):
        # Open device's datastream
        self._datastream = self._device.DataStreams()[0].OpenDataStream()
        # Allocate image buffer for image acquisition
        self.revoke_and_allocate_buffer()

    def conversion_supported(self, source_pixel_format: int) -> bool:
        """
        Check if the image_converter supports the conversion of the
        `source_pixel_format` to our `TARGET_PIXEL_FORMAT`
        """
        return any(
            TARGET_PIXEL_FORMAT == supported_pixel_format
            for supported_pixel_format in
            self._image_converter.SupportedOutputPixelFormatNames(
                source_pixel_format))
        

    def _setup_device_and_datastream(self):
        self._datastream = self._device.DataStreams()[0].OpenDataStream()
        # Disable auto gain and auto exposure to enable custom gain in program
        self._find_and_set_remote_device_enumeration("GainAuto", "Off")
        self._find_and_set_remote_device_enumeration("ExposureAuto", "Off")
        
        # Set camera frame rate to 60 FPS
        try:
            self.node_map.FindNode("AcquisitionFrameRate").SetValue(60)
            print("Acquisition frame rate set to 60 FPS")
        except Exception as e:
            print(f"Failed to set AcquisitionFrameRate: {e}")

        # Allocate image buffer for image acquisition
        payload_size = self.node_map.FindNode("PayloadSize").Value()
        # Use more buffers
        max_buffer = self._datastream.NumBuffersAnnouncedMinRequired() * 5
        for idx in range(max_buffer):
            buffer = self._datastream.AllocAndAnnounceBuffer(payload_size)
            self._datastream.QueueBuffer(buffer)
        print("Allocated buffers, finished opening device")
    

    def close(self):
        self.stop_recording()
        self.stop_realtime_acquisition()
        self.stop_hardware_acquisition()

        # If datastream has been opened, revoke and deallocate all buffers
        if self._datastream is not None:
            try:
                for buffer in self._datastream.AnnouncedBuffers():
                    self._datastream.RevokeBuffer(buffer)
            except Exception as e:
                print(f"Exception (close): {str(e)}")

    
    def _find_and_set_remote_device_enumeration(self, name: str, value: str):
        all_entries = self.node_map.FindNode(name).Entries()
        available_entries = []
        for entry in all_entries:
            if (entry.AccessStatus() != ids_peak.NodeAccessStatus_NotAvailable
                    and entry.AccessStatus() != ids_peak.NodeAccessStatus_NotImplemented):
                available_entries.append(entry.SymbolicValue())
        if value in available_entries:
            self.node_map.FindNode(name).SetCurrentEntry(value)

    def set_remote_device_value(self, name: str, value: any):
        try:
            self.node_map.FindNode(name).SetValue(value)
        except ids_peak.Exception:
            self.interface.warning(f"Could not set value for {name}!")

    #RealTime Acquisition
    def start_realtime_acquisition(self):
        self.acquisition_mode = 0 #0: Real Time, #1: HW Trigger, #2: SW Trigger

        if self._device is None or self.acquisition_running:
            return False
        
        if self._datastream is None:
            self._init_data_stream()

        for buffer in self._buffer_list:
            self._datastream.QueueBuffer(buffer)


        # Constant Acquisition Test
        try:
            allEntries = self.node_map.FindNode("TriggerSelector").Entries()
            availableEntries = []
            for entry in allEntries:
                if (entry.AccessStatus() != ids_peak.NodeAccessStatus_NotAvailable
                        and entry.AccessStatus() != ids_peak.NodeAccessStatus_NotImplemented):
                    availableEntries.append(entry.SymbolicValue())

            if len(availableEntries) == 0:
                raise Exception("RT Acquisition not supported")
            elif "ExposureStart" not in availableEntries:
                self.node_map.FindNode("TriggerSelector").SetCurrentEntry(
                    availableEntries[0])
            else:
                self.node_map.FindNode(
                    "TriggerSelector").SetCurrentEntry("ExposureStart")
            # Set trigger mode to 'Off' for continuous acquisition
            self.node_map.FindNode("TriggerMode").SetCurrentEntry("Off")

            # Start the data stream and acquisition
            self._datastream.StartAcquisition()
            self.node_map.FindNode("AcquisitionStart").Execute()
            self.acquisition_running = True
        except Exception as e:
            print(f"Exception during start_realtime_acquisition: {e}")
            return False
        return True


    def stop_realtime_acquisition(self):
        if self._device is None or self.acquisition_running is False:
            return
        try:
            self.node_map.FindNode("AcquisitionStop").Execute()

            # Kill the datastream to exit out of pending `WaitForFinishedBuffer`
            # calls
            #self._datastream.KillWait() TODO: GAIN (?)
            self._datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)
            # Discard all buffers from the acquisition engine
            # They remain in the announced buffer pool
            self._datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

            self.acquisition_running = False

            # Unlock parameters
            self.node_map.FindNode("TLParamsLocked").SetValue(0)
            self.revoke_and_allocate_buffer()
            
            print("Closed RT Acq")

        except Exception as e:
            print(f"Exception (stop acquisition): {str(e)}")


    # Hardware Acquisition
    def start_hardware_acquisition(self):
        self.acquisition_mode = 1 #0: Real Time, #1: HW Trigger, #2: SW Trigger

        if self._device is None or self.acquisition_running:
            return False
        
        if self._datastream is None:
            self._init_data_stream()

        for buffer in self._buffer_list:
            self._datastream.QueueBuffer(buffer)

        # HW Acquisition Test
        try:
            allEntries = self.node_map.FindNode("TriggerSelector").Entries()
            availableEntries = []
            for entry in allEntries:
                if (entry.AccessStatus() != ids_peak.NodeAccessStatus_NotAvailable
                        and entry.AccessStatus() != ids_peak.NodeAccessStatus_NotImplemented):
                    availableEntries.append(entry.SymbolicValue())

            if len(availableEntries) == 0:
                raise Exception("Hardware Trigger not supported")
            elif "ExposureStart" not in availableEntries:
                self.node_map.FindNode("TriggerSelector").SetCurrentEntry(
                    availableEntries[0])
            else:
                self.node_map.FindNode(
                    "TriggerSelector").SetCurrentEntry("ExposureStart")
            self.node_map.FindNode("TriggerMode").SetCurrentEntry("On")
            self.node_map.FindNode("TriggerSource").SetCurrentEntry("Line0")

            # Start the data stream and acquisition
            self._datastream.StartAcquisition()
            self.node_map.FindNode("AcquisitionStart").Execute()
            self.acquisition_running = True

            print("Hardware Acquisition started!")
        except Exception as e:
            print(f"Exception during start_hardware_acquisition: {e}")
            return False
        return True


    def stop_hardware_acquisition(self):
        print("Trigger Mode:", self.node_map.FindNode("TriggerMode").CurrentEntry().SymbolicValue())
        print("Trigger Source:", self.node_map.FindNode("TriggerSource").CurrentEntry().SymbolicValue())

        if self._device is None or self.acquisition_running is False:
            return
        try:
            self.node_map.FindNode("AcquisitionStop").Execute()

            # Kill the datastream to exit out of pending `WaitForFinishedBuffer`
            # calls
            #self._datastream.KillWait() TODO: GAIN (?)
            self._datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)
            # Discard all buffers from the acquisition engine
            # They remain in the announced buffer pool
            self._datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

            self.acquisition_running = False

            # Unlock parameters
            self.node_map.FindNode("TLParamsLocked").SetValue(0)
            self.revoke_and_allocate_buffer()
            print("Closed HW Acq")
        except Exception as e:
            print(f"Exception (stop hardware acquisition): {str(e)}")


    def start_recording(self):
        if self._datastream is None:
            self._init_data_stream()
        fps = int(self.node_map.FindNode("AcquisitionFrameRate").Value()) if self.acquisition_mode == 0 else self.GUIfps
        self.video_recorder.start_recording(fps)

    def stop_recording(self):
        self.video_recorder.stop_recording()

    def _valid_name(self, path: str, ext: str):
        num = 0

        def build_string():
            return f"{path}_{num}{ext}"

        while exists(build_string()):
            num += 1
        return build_string()


    def revoke_and_allocate_buffer(self):
        if self._datastream is None:
            return

        try:
            # Check if buffers are already allocated
            if self._datastream is not None:
                # Remove buffers from the announced pool
                for buffer in self._datastream.AnnouncedBuffers():
                    self._datastream.RevokeBuffer(buffer)
                self._buffer_list = []

            payload_size = self.node_map.FindNode("PayloadSize").Value()
            buffer_amount = self._datastream.NumBuffersAnnouncedMinRequired()

            for _ in range(buffer_amount):
                buffer = self._datastream.AllocAndAnnounceBuffer(payload_size)
                self._buffer_list.append(buffer)
        except Exception as e:
            self._interface.warning(str(e))

    def change_pixel_format(self, pixel_format: str):
        try:
            self.node_map.FindNode("PixelFormat").SetCurrentEntry(pixel_format)
            self.revoke_and_allocate_buffer()
        except Exception as e:
            self._interface.warning(f"Cannot change pixelformat: {str(e)}")
        
        
    def get_data_stream_image(self):
        try:
            cwd = os.getcwd()
            converted_ipl_image = None
            buffer = self._datastream.WaitForFinishedBuffer(500)  # Short timeout

            if buffer is None:
                return None  # No buffer available, skip processing

            ipl_image = ids_peak_ipl_extension.BufferToImage(buffer)
            converted_ipl_image = self._image_converter.Convert(ipl_image, TARGET_PIXEL_FORMAT)
            self._datastream.QueueBuffer(buffer)
            self._interface.on_image_received(converted_ipl_image)

            self.video_recorder.add_frame(converted_ipl_image)  # ✅ Use new VideoRecorder

            if self.save_image:
                print("Saving image...")
                ids_peak_ipl.ImageWriter.WriteAsPNG(self._valid_name(cwd + "/image", ".png"), converted_ipl_image)
                print("Saved!")
                self.save_image = False

            return converted_ipl_image
        except ids_peak.Exception as e:
            print(f"No buffer available: {e}")
            return None

    def acquisition_thread(self):
        while not self.killed:
            try:
                self.get_data_stream_image()
            except Exception as e:
                self._interface.warning(f"Acquisition error: {str(e)}")
                self.save_image = False

