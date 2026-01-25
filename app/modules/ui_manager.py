from PyQt6 import uic
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

    def apply_settings(self):
        pass

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
        pass

    def noise_toggled(self, state):
        pass

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