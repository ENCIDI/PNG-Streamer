from PyQt6 import uic
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QDialog
import sys

from app.modules import audio_manager as am, logic_manager as lm, storage_manager as sm, web_manager as wm

class PNGStreamerApp(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("app/ui/main.ui", self)

        self.applySettingsButton.clicked.connect(self.apply_settings)
        self.closeButton.clicked.connect(self.close)

        self.redactProfileButton.clicked.connect(self.edit_profile)
        self.deleteProfileButton.clicked.connect(self.delete_profile)
        self.createProfileButton.clicked.connect(self.create_profile)

        self.startServerButton.clicked.connect(self.start_server)
        self.stopServerButton.clicked.connect(self.stop_server)

        self.microChoose.currentIndexChanged.connect(self.micro_changed)
        self.noiseCheckbox.stateChanged.connect(self.noise_toggled)

        self.settings = sm.load_settings()
        self._populate_microphones()
        self._apply_settings_to_ui()
        self._start_volume_updates()

    def apply_settings(self):
        selected_device = self.microChoose.currentData()
        selected_name = self.microChoose.currentText() or "Default"
        sm.update_settings(
            {
                "microphone": selected_name,
                "unnoised": self.noiseCheckbox.isChecked(),
            }
        )
        am.set_noise_suppression(self.noiseCheckbox.isChecked())
        am.start_monitor(selected_device)

    def edit_profile(self):
        pass

    def delete_profile(self):
        pass

    def create_profile(self):
        pass

    def start_server(self):
        port = self.serverPortButton.text()
        pass

    def stop_server(self):
        pass

    def micro_changed(self, index):
        selected_device = self.microChoose.itemData(index)
        am.start_monitor(selected_device)

    def noise_toggled(self, state):
        enabled = self.noiseCheckbox.isChecked()
        am.set_noise_suppression(enabled)
        sm.update_settings({"unnoised": enabled})

    def _populate_microphones(self):
        self.microChoose.clear()
        devices = am.list_input_devices()
        for device in devices:
            self.microChoose.addItem(device.name, device.device_id)

    def _apply_settings_to_ui(self):
        settings = self.settings.get("settings", {})
        microphone = settings.get("microphone", "Default")
        if isinstance(microphone, int):
            target_index = self.microChoose.findData(microphone)
        else:
            target_index = self.microChoose.findText(str(microphone))
        if target_index == -1:
            target_index = 0
        self.microChoose.setCurrentIndex(target_index)
        self.noiseCheckbox.setChecked(bool(settings.get("unnoised", False)))
        selected_device = self.microChoose.currentData()
        am.set_noise_suppression(self.noiseCheckbox.isChecked())
        am.start_monitor(selected_device)

    def _start_volume_updates(self):
        self.volume_timer = QTimer(self)
        self.volume_timer.setInterval(200)
        self.volume_timer.timeout.connect(self._update_volume_label)
        self.volume_timer.start()

    def _update_volume_label(self):
        volume = am.get_current_volume()
        self.volumeLabel.setText(str(int(volume)))

class ProfilesCustomizationScreen(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("app/ui/profiles.ui",self)

        self.exitButton.clicked.connect(self.close)
        self.addButton.clicked.connect(self.add_setting)
        self.cancelButton.clicked.connect(self.cancel_changes)
        self.saveButton.clicked.connect(self.save_settings)

    def add_setting(self):
        pass

    def save_settings(self):
        pass

    def cancel_changes(self):
        pass


def start_program():
    app = QApplication(sys.argv)
    window = PNGStreamerApp()
    window.show()
    app.exec()
