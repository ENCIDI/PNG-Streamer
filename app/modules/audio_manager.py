import importlib
import math
import threading
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MicrophoneDevice:
    device_id: Optional[int]
    name: str


_lock = threading.Lock()
_current_volume = 0.0
current_volume = 0.0
_noise_floor = 0.0
_noise_suppression = False
_stream = None
_selected_device = None


def _sounddevice_available() -> bool:
    return importlib.util.find_spec("sounddevice") is not None


def _numpy_available() -> bool:
    return importlib.util.find_spec("numpy") is not None


def list_input_devices() -> List[MicrophoneDevice]:
    devices = [MicrophoneDevice(device_id=None, name="Default")]
    if not _sounddevice_available():
        return devices
    sounddevice = importlib.import_module("sounddevice")
    for idx, info in enumerate(sounddevice.query_devices()):
        if info.get("max_input_channels", 0) > 0:
            devices.append(MicrophoneDevice(device_id=idx, name=info.get("name", f"Input {idx}")))
    return devices


def set_noise_suppression(enabled: bool) -> None:
    global _noise_suppression
    with _lock:
        _noise_suppression = enabled


def get_current_volume() -> float:
    with _lock:
        return _current_volume


def _update_volume(level: float) -> None:
    global _current_volume, current_volume
    with _lock:
        _current_volume = level
        current_volume = level


def _update_noise_floor(level: float) -> None:
    global _noise_floor
    alpha = 0.9
    if _noise_floor == 0.0:
        _noise_floor = level
    else:
        _noise_floor = alpha * _noise_floor + (1 - alpha) * level


def start_monitor(device_id: Optional[int] = None) -> None:
    global _stream, _selected_device, _noise_floor
    stop_monitor()
    _selected_device = device_id
    _noise_floor = 0.0
    if not _sounddevice_available():
        _update_volume(0.0)
        return
    sounddevice = importlib.import_module("sounddevice")

    def callback(indata, frames, time, status):
        if status:
            return
        if not _numpy_available():
            return
        numpy = importlib.import_module("numpy")
        rms = numpy.sqrt(numpy.mean(numpy.square(indata)))
        rms_value = float(rms)
        if rms_value <= 1e-7:
            rms_value = 1e-7
        db = 20 * math.log10(rms_value)
        level = max(min((db + 60) / 60 * 100, 100), 0)
        if _noise_suppression:
            if level < 20:
                _update_noise_floor(level)
            adjusted_level = max(level - _noise_floor, 0)
            _update_volume(adjusted_level)
        else:
            _update_volume(level)

    _stream = sounddevice.InputStream(
        device=device_id,
        channels=1,
        callback=callback,
    )
    _stream.start()


def stop_monitor() -> None:
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None


def get_selected_device() -> Optional[int]:
    return _selected_device
