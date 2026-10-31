from app.modules import audio_manager as am


class _FakeSoundDevice:
    def query_hostapis(self):
        return [{"name": "ALSA"}, {"name": "JACK Audio Connection Kit"}]

    def query_devices(self, device=None):
        devices = [
            {"name": "HDA Intel PCH: ALC892 Analog (hw:0,0)", "hostapi": 0, "max_input_channels": 2, "max_output_channels": 2},
            {"name": "sysdefault", "hostapi": 0, "max_input_channels": 128, "max_output_channels": 128},
            {"name": "USB Mic: Audio (hw:1,0)", "hostapi": 0, "max_input_channels": 1, "max_output_channels": 0},
            {"name": "pulse", "hostapi": 0, "max_input_channels": 32, "max_output_channels": 32},
            {"name": "pipewire", "hostapi": 0, "max_input_channels": 64, "max_output_channels": 64},
            {"name": "default", "hostapi": 0, "max_input_channels": 64, "max_output_channels": 64},
            {"name": "system", "hostapi": 1, "max_input_channels": 2, "max_output_channels": 2},
        ]
        return devices if device is None else devices[device]


def test_linux_lists_sound_server_devices_first(monkeypatch):
    monkeypatch.setattr(am, "sounddevice", _FakeSoundDevice())
    monkeypatch.setattr(am.sys, "platform", "linux")

    inputs = [d.name for d in am.list_audio_devices(0) if not d.is_output]

    assert inputs[:5] == ["Default", "pipewire", "pulse", "default", "sysdefault"]
    assert set(inputs[5:]) == {"HDA Intel PCH: ALC892 Analog (hw:0,0)", "USB Mic: Audio (hw:1,0)"}


def test_windows_order_is_unchanged(monkeypatch):
    monkeypatch.setattr(am, "sounddevice", _FakeSoundDevice())
    monkeypatch.setattr(am.sys, "platform", "win32")

    inputs = [d.name for d in am.list_audio_devices(0) if not d.is_output]

    assert inputs[1] == "HDA Intel PCH: ALC892 Analog (hw:0,0)"
