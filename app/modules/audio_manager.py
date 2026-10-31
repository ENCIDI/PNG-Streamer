import math
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from app import paths
from app.modules import logging_manager as logm

_LOGGER = logm.get_logger(__name__)


def _use_bundled_portaudio() -> None:
    # sounddevice locates PortAudio with ctypes.util.find_library, which cannot
    # see libraries bundled inside an AppImage/PyInstaller build. Fall back to
    # the bundled copy when the system has none.
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "libportaudio.so.2"
    if not (sys.platform.startswith("linux") and paths.is_frozen() and bundled.exists()):
        return
    import ctypes.util

    original = ctypes.util.find_library

    def _find_library(name: str) -> Optional[str]:
        found = original(name)
        if found is None and name == "portaudio":
            return str(bundled)
        return found

    ctypes.util.find_library = _find_library


_use_bundled_portaudio()

try:
    import numpy
except ImportError:
    numpy = None

try:
    import sounddevice
except (ImportError, OSError):
    _LOGGER.exception("sounddevice is unavailable, microphone input disabled")
    sounddevice = None


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
_monitor_error: Optional[str] = None

NOISE_ALGORITHMS = ("adaptive", "fixed")
_LINUX_PREFERRED = ("pipewire", "pulse", "default", "sysdefault")


def log_environment() -> None:
    """Write the audio setup to the log; essential for remote microphone issues."""
    if sounddevice is None:
        _LOGGER.warning("Audio: sounddevice unavailable")
        return
    try:
        _LOGGER.info("Audio: %s", sounddevice.get_portaudio_version()[1])
        for api in list_host_apis():
            names = [d.name for d in list_audio_devices(api.index) if d.device_id is not None and not d.is_output]
            _LOGGER.info("Audio: host API %s: %s inputs %s", api.name, len(names), names)
    except Exception:
        _LOGGER.exception("Audio: failed to describe devices")


def list_host_apis() -> List[HostAPI]:
    apis = []
    if sounddevice is None:
        return apis
    try:
        for idx, info in enumerate(sounddevice.query_hostapis()):
            apis.append(HostAPI(index=idx, name=info.get("name", f"API {idx}")))
    except Exception:
        pass
    return apis


def list_audio_devices(host_api_index: Optional[int] = None) -> List[AudioDevice]:
    devices = [AudioDevice(device_id=None, name="Default")]
    if sounddevice is None:
        return devices
    try:
        all_devices = list(sounddevice.query_devices())

        for idx, info in enumerate(all_devices):
            if info.get("max_input_channels", 0) > 0:
                api_idx = info.get("hostapi")
                if host_api_index is not None and api_idx != host_api_index:
                    continue
                devices.append(
                    AudioDevice(
                        device_id=idx,
                        name=info.get("name", f"Input {idx}"),
                        hostapi=api_idx,
                    )
                )

        if sys.platform.startswith("linux"):
            # PipeWire/PulseAudio are reached through these ALSA virtual devices;
            # show them first, raw hw: devices are usually busy under a sound server.
            inputs = devices[1:]
            inputs.sort(key=lambda d: _LINUX_PREFERRED.index(d.name) if d.name in _LINUX_PREFERRED else len(_LINUX_PREFERRED))
            devices[1:] = inputs

        for idx, info in enumerate(all_devices):
            if info.get("max_output_channels", 0) > 0:
                api_idx = info.get("hostapi")
                if host_api_index is not None and api_idx != host_api_index:
                    continue
                devices.append(
                    AudioDevice(
                        device_id=idx,
                        name=info.get("name", f"Output {idx}"),
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


def _open_input_stream(device: Optional[int], callback):
    # Mono is enough for a volume level, but some ALSA devices only open in stereo;
    # the callback averages over all channels either way.
    error: Optional[Exception] = None
    for channels in (1, 2):
        try:
            stream = sounddevice.InputStream(device=device, channels=channels, callback=callback)
            stream.start()
            return stream
        except sounddevice.PortAudioError as exc:
            error = exc
    raise error


def start_monitor(device_id: Optional[int] = None) -> None:
    global _stream, _selected_device, _noise_floor, _smoothed_volume, _monitor_error
    stop_monitor()
    _selected_device = device_id
    _noise_floor = 0.0
    _smoothed_volume = 0.0
    _monitor_error = None
    if sounddevice is None or numpy is None:
        _monitor_error = "unavailable"
        _update_volume(0.0)
        return

    def callback(indata, frames, time, status):
        if status:
            return
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
        _stream = _open_input_stream(actual_device, callback)
    except Exception:
        _LOGGER.exception("Failed to open input device %s", actual_device)
        _stream = None
        if actual_device is not None:
            try:
                _stream = _open_input_stream(None, callback)
                _monitor_error = "fallback"
            except Exception:
                _LOGGER.exception("Failed to open default input device")
                _stream = None
        if _stream is None:
            _monitor_error = "failed"
            _update_volume(0.0)


def stop_monitor() -> None:
    global _stream
    if _stream is not None:
        try:
            _stream.stop()
            _stream.close()
        except Exception:
            _LOGGER.exception("Failed to close input stream")
        _stream = None


def get_monitor_error() -> Optional[str]:
    """None when the selected device works, "fallback" when the default device is used
    instead, "failed"/"unavailable" when there is no input at all."""
    return _monitor_error


def get_selected_device() -> Optional[int]:
    return _selected_device
