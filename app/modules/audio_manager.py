import importlib
import math
import threading
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AudioDevice:
    device_id: Optional[int]
    name: str
    hostapi: Optional[int] = None
    is_output: bool = False


@dataclass
class HostAPI:
    index: int
    name: str


_lock = threading.Lock()
_current_volume = 0.0
current_volume = 0.0
_noise_floor = 0.0
_noise_suppression = False
_noise_algorithm = "adaptive"
_noise_threshold = 15.0
_compressor_enabled = False
_compressor_threshold = 60.0
_compressor_ratio = 4.0
_smoothed_volume = 0.0
_stream = None
_selected_device = None

NOISE_ALGORITHMS = ("adaptive", "fixed")


def _sounddevice_available() -> bool:
    return importlib.util.find_spec("sounddevice") is not None


def _numpy_available() -> bool:
    return importlib.util.find_spec("numpy") is not None


def _speech_recognition_available() -> bool:
    return importlib.util.find_spec("speech_recognition") is not None


def list_host_apis() -> List[HostAPI]:
    apis = []
    if not _sounddevice_available():
        return apis
    try:
        sounddevice = importlib.import_module("sounddevice")
        for idx, info in enumerate(sounddevice.query_hostapis()):
            apis.append(HostAPI(index=idx, name=info.get("name", f"API {idx}")))
    except Exception:
        pass
    return apis


def list_audio_devices(host_api_index: Optional[int] = None) -> List[AudioDevice]:
    devices = [AudioDevice(device_id=None, name="Default")]
    if not _sounddevice_available():
        if not _speech_recognition_available():
            return devices
        try:
            speech_recognition = importlib.import_module("speech_recognition")
            for idx, name in enumerate(speech_recognition.Microphone.list_microphone_names()):
                devices.append(AudioDevice(device_id=idx, name=f"🎤 {name}"))
        except Exception:
            return devices
        return devices
    try:
        sounddevice = importlib.import_module("sounddevice")
        all_devices = list(sounddevice.query_devices())

        for idx, info in enumerate(all_devices):
            if info.get("max_input_channels", 0) > 0:
                api_idx = info.get("hostapi")
                if host_api_index is not None and api_idx != host_api_index:
                    continue
                devices.append(
                    AudioDevice(
                        device_id=idx,
                        name=f"🎤 {info.get('name', f'Input {idx}')}",
                        hostapi=api_idx,
                    )
                )

        for idx, info in enumerate(all_devices):
            if info.get("max_output_channels", 0) > 0:
                api_idx = info.get("hostapi")
                if host_api_index is not None and api_idx != host_api_index:
                    continue
                devices.append(
                    AudioDevice(
                        device_id=idx,
                        name=f"🔊 {info.get('name', f'Output {idx}')}",
                        hostapi=api_idx,
                        is_output=True,
                    )
                )
    except Exception:
        return devices
    return devices


def set_noise_suppression(enabled: bool) -> None:
    global _noise_suppression
    with _lock:
        _noise_suppression = enabled


def set_noise_algorithm(name: str) -> None:
    global _noise_algorithm
    with _lock:
        _noise_algorithm = name if name in NOISE_ALGORITHMS else "adaptive"


def set_noise_threshold(value: float) -> None:
    global _noise_threshold
    with _lock:
        _noise_threshold = max(0.0, min(float(value), 100.0))


def set_compressor(enabled: bool) -> None:
    global _compressor_enabled
    with _lock:
        _compressor_enabled = enabled


def set_compressor_threshold(value: float) -> None:
    global _compressor_threshold
    with _lock:
        _compressor_threshold = max(0.0, min(float(value), 100.0))


def set_compressor_ratio(value: float) -> None:
    global _compressor_ratio
    with _lock:
        _compressor_ratio = max(1.0, min(float(value), 20.0))


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
    if _noise_floor == 0.0:
        _noise_floor = level
        return

    capped_level = min(level, _noise_floor + 8.0)
    if capped_level < _noise_floor:
        alpha = 0.7
    elif capped_level > _noise_floor:
        alpha = 0.97
    else:
        alpha = 0.9
    _noise_floor = alpha * _noise_floor + (1 - alpha) * capped_level
    _noise_floor = max(min(_noise_floor, 80.0), 0.0)


def _apply_noise_gate(level: float) -> float:
    threshold = _noise_floor + 6.0
    if level <= threshold:
        return 0.0
    adjusted = (level - threshold) * 100.0 / max(100.0 - threshold, 1.0)
    return max(min(adjusted, 100.0), 0.0)


def _apply_fixed_gate(level: float, threshold: float) -> float:
    if level <= threshold:
        return 0.0
    adjusted = (level - threshold) * 100.0 / max(100.0 - threshold, 1.0)
    return max(min(adjusted, 100.0), 0.0)


def _apply_compressor(level: float, threshold: float, ratio: float) -> float:
    if level <= threshold:
        return level
    excess = level - threshold
    compressed = threshold + excess / max(ratio, 1.0)
    return max(min(compressed, 100.0), 0.0)


def _smooth_volume(target: float) -> float:
    global _smoothed_volume
    if target > _smoothed_volume:
        alpha = 0.6
    else:
        alpha = 0.85
    _smoothed_volume = alpha * _smoothed_volume + (1 - alpha) * target
    return _smoothed_volume


def start_monitor(device_id: Optional[int] = None) -> None:
    global _stream, _selected_device, _noise_floor, _smoothed_volume
    stop_monitor()
    _selected_device = device_id
    _noise_floor = 0.0
    _smoothed_volume = 0.0
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
            if _noise_algorithm == "fixed":
                level = _apply_fixed_gate(level, _noise_threshold)
            else:
                _update_noise_floor(level)
                level = _apply_noise_gate(level)
        if _compressor_enabled:
            level = _apply_compressor(level, _compressor_threshold, _compressor_ratio)
        _update_volume(_smooth_volume(level))

    actual_device = device_id
    if device_id is not None:
        try:
            info = sounddevice.query_devices(device_id)
            if info.get("max_input_channels", 0) == 0 and info.get("max_output_channels", 0) > 0:
                name = info.get("name")
                api = info.get("hostapi")
                for i, other in enumerate(sounddevice.query_devices()):
                    if other.get("hostapi") == api and other.get("max_input_channels", 0) > 0:
                        if name in other.get("name") or "Loopback" in other.get("name"):
                            actual_device = i
                            break
        except Exception:
            pass

    try:
        _stream = sounddevice.InputStream(
            device=actual_device,
            channels=1,
            callback=callback,
        )
        _stream.start()
    except Exception:
        if actual_device is not None:
            try:
                _stream = sounddevice.InputStream(
                    device=None,
                    channels=1,
                    callback=callback,
                )
                _stream.start()
            except Exception:
                _update_volume(0.0)


def stop_monitor() -> None:
    global _stream
    if _stream is not None:
        _stream.stop()
        _stream.close()
        _stream = None


def get_selected_device() -> Optional[int]:
    return _selected_device
