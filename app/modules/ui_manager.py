from PyQt6 import uic
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox
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
        self.selectProfile.currentIndexChanged.connect(self.profile_changed)

        self.settings = sm.load_settings()
        self._populate_microphones()
        self._populate_profiles()
        self._apply_settings_to_ui()
        self._start_volume_updates()

    def apply_settings(self):
        selected_device = self.microChoose.currentData()
        selected_name = self.microChoose.currentText() or "Default"
        server_port = self._parse_port(self.serverPortButton.text())
        sm.update_settings(
            {
                "microphone": selected_name,
                "unnoised": self.noiseCheckbox.isChecked(),
                "server-port": server_port,
            }
        )
        am.set_noise_suppression(self.noiseCheckbox.isChecked())
        am.start_monitor(selected_device)
        self.serverPortButton.setText(str(server_port))

    def edit_profile(self):
        profile_id = self.selectProfile.currentData()
        if profile_id is None:
            return
        profile = sm.get_profile_by_id(profile_id)
        if not profile:
            QMessageBox.warning(self, "PNG Streamer", "Profile not found.")
            return
        dialog = ProfilesCustomizationScreen(profile=profile)
        if dialog.exec():
            sm.update_profile(dialog.result_profile)
            self._populate_profiles()
            self._select_profile_id(dialog.result_profile.get("id"))

    def delete_profile(self):
        profile_id = self.selectProfile.currentData()
        if profile_id is None:
            return
        if (
            QMessageBox.question(
                self,
                "PNG Streamer",
                "Delete selected profile?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        sm.delete_profile(profile_id)
        profiles = sm.list_profiles()
        new_active = profiles[0].get("id") if profiles else 1
        sm.update_settings({"active-profile-id": new_active})
        self._populate_profiles()
        self._select_profile_id(new_active)

    def create_profile(self):
        dialog = ProfilesCustomizationScreen(profile=None)
        if dialog.exec():
            created = sm.create_profile(
                name=dialog.result_profile.get("name", "profile"),
                images=dialog.result_profile.get("images", []),
                blink=dialog.result_profile.get("blink", {}),
                blink_images=dialog.result_profile.get("blink-images", []),
            )
            sm.update_settings({"active-profile-id": created.get("id")})
            self._populate_profiles()
            self._select_profile_id(created.get("id"))

    def start_server(self):
        port = self._parse_port(self.serverPortButton.text())
        started, status = wm.start_server("127.0.0.1", port)
        if not started and status != "already_running":
            QMessageBox.warning(self, "PNG Streamer", "Unable to start server.")
        self._update_server_ui()
        sm.update_settings({"server-port": port})

    def stop_server(self):
        wm.stop_server()
        self._update_server_ui()

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

    def _populate_profiles(self):
        self.selectProfile.clear()
        profiles = sm.list_profiles()
        for profile in profiles:
            self.selectProfile.addItem(profile.get("name", "profile"), profile.get("id"))

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
        self.serverPortButton.setText(str(settings.get("server-port", 8642)))
        self._select_profile_id(settings.get("active-profile-id", 1))
        self._update_server_ui()

    def _start_volume_updates(self):
        self.volume_timer = QTimer(self)
        self.volume_timer.setInterval(200)
        self.volume_timer.timeout.connect(self._update_volume_label)
        self.volume_timer.start()

    def _update_volume_label(self):
        volume = am.get_current_volume()
        self.volumeLabel.setText(str(int(volume)))
        self._update_widget_if_running()

    def _update_widget_if_running(self):
        if wm.is_running():
            self.widgetIpLine.setText(self._widget_url())

    def _widget_url(self):
        port = self._parse_port(self.serverPortButton.text())
        return f"http://127.0.0.1:{port}/widget"

    def _parse_port(self, value: str) -> int:
        try:
            port = int(value)
        except (TypeError, ValueError):
            return 8642
        if port < 1 or port > 65535:
            return 8642
        return port

    def _update_server_ui(self):
        if wm.is_running():
            self.serverStatusLine.setText("Running")
            self.widgetIpLine.setText(self._widget_url())
        else:
            self.serverStatusLine.setText("Stopped")
            self.widgetIpLine.setText("")

    def _select_profile_id(self, profile_id):
        if profile_id is None:
            return
        target_index = self.selectProfile.findData(profile_id)
        if target_index == -1 and self.selectProfile.count() > 0:
            target_index = 0
        if target_index >= 0:
            self.selectProfile.setCurrentIndex(target_index)

    def profile_changed(self, index):
        profile_id = self.selectProfile.itemData(index)
        if profile_id is None:
            return
        sm.update_settings({"active-profile-id": profile_id})


class ProfilesCustomizationScreen(QDialog):
    def __init__(self, profile=None):
        super().__init__()
        uic.loadUi("app/ui/profiles.ui", self)
        self.result_profile = None
        self._profile = profile
        self._images = lm.list_available_images()

        self.exitButton.clicked.connect(self.close)
        self.cancelButton.clicked.connect(self.cancel_changes)
        self.saveButton.clicked.connect(self.save_settings)
        if hasattr(self, "addButton"):
            self.addButton.clicked.connect(self.add_setting)

        self._image_boxes = [
            self.path1,
            self.path2,
            self.path3,
            self.path4,
            self.path5,
            self.path6,
            self.path7,
            self.path8,
            self.path9,
            self.path10,
        ]
        self._blink_boxes = [
            getattr(self, "pathClip1", None),
            getattr(self, "pathClip2", None),
            getattr(self, "pathClip3", None),
            getattr(self, "pathClip4", None),
            getattr(self, "pathClip5", None),
            getattr(self, "pathClip6", None),
            getattr(self, "pathClip7", None),
            getattr(self, "pathClip8", None),
            getattr(self, "pathClip9", None),
            getattr(self, "pathClip10", None),
        ]
        self._blink_boxes = [box for box in self._blink_boxes if box is not None]
        self._db_boxes = [
            self.db1,
            self.db2,
            self.db3,
            self.db4,
            self.db5,
            self.db6,
            self.db7,
            self.db8,
            self.db9,
            self.db10,
        ]
        self._blink_min_box = getattr(self, "clipLenthMin", None)
        self._blink_max_box = getattr(self, "clipLenthMax", None)
        self._blink_duration_box = getattr(self, "clipDuration", None)

        self._populate_images()
        self._load_profile()

    def add_setting(self):
        pass

    def save_settings(self):
        name = (self.profile_name.text() or "").strip()
        if not name:
            QMessageBox.warning(self, "PNG Streamer", "Please enter a profile name.")
            return
        images = []
        for idx, (combo, db_box) in enumerate(zip(self._image_boxes, self._db_boxes)):
            path_value = combo.currentText().strip()
            if not path_value:
                continue
            try:
                volume_level = int(db_box.text().strip())
            except (TypeError, ValueError):
                QMessageBox.warning(self, "PNG Streamer", "Threshold must be a number.")
                return
            images.append(
                {
                    "id": idx,
                    "path-to-image": path_value,
                    "volume-level": volume_level,
                }
            )
        blink_images = []
        for idx, combo in enumerate(self._blink_boxes):
            path_value = combo.currentText().strip()
            if not path_value:
                continue
            blink_images.append(
                {
                    "id": idx,
                    "path-to-image": path_value,
                }
            )
        blink_min = 0
        if self._blink_min_box is not None:
            blink_min_text = (self._blink_min_box.text() or "").strip()
            if blink_min_text:
                try:
                    blink_min = int(blink_min_text)
                except (TypeError, ValueError):
                    QMessageBox.warning(self, "PNG Streamer", "Blink min must be a number.")
                    return
        blink_max = 0
        if self._blink_max_box is not None:
            blink_max_text = (self._blink_max_box.text() or "").strip()
            if blink_max_text:
                try:
                    blink_max = int(blink_max_text)
                except (TypeError, ValueError):
                    QMessageBox.warning(self, "PNG Streamer", "Blink max must be a number.")
                    return
        blink_duration = 0
        if self._blink_duration_box is not None:
            blink_duration_text = (self._blink_duration_box.text() or "").strip()
            if blink_duration_text:
                try:
                    blink_duration = int(blink_duration_text)
                except (TypeError, ValueError):
                    QMessageBox.warning(self, "PNG Streamer", "Blink duration must be a number.")
                    return
        profile_id = self._profile.get("id") if self._profile else None
        self.result_profile = {
            "id": profile_id,
            "name": name,
            "images": images,
            "blink": {
                "interval-min-ms": blink_min,
                "interval-max-ms": blink_max,
                "duration-ms": blink_duration,
            },
            "blink-images": blink_images,
        }
        self.accept()

    def cancel_changes(self):
        self.reject()

    def _populate_images(self):
        for combo in self._image_boxes:
            combo.clear()
            combo.addItem("")
            for image_name in self._images:
                combo.addItem(image_name)
        for combo in self._blink_boxes:
            combo.clear()
            combo.addItem("")
            for image_name in self._images:
                combo.addItem(image_name)

    def _load_profile(self):
        if not self._profile:
            return
        self.profile_name.setText(self._profile.get("name", ""))
        images = {
            img.get("id"): img
            for img in self._profile.get("images", [])
            if isinstance(img, dict)
        }
        for idx, (combo, db_box) in enumerate(zip(self._image_boxes, self._db_boxes)):
            image = images.get(idx)
            if not image:
                continue
            path_value = str(image.get("path-to-image", ""))
            if path_value and combo.findText(path_value) == -1:
                combo.addItem(path_value)
            combo.setCurrentText(path_value)
            db_box.setText(str(image.get("volume-level", "")))
        blink = self._profile.get("blink", {}) if isinstance(self._profile.get("blink", {}), dict) else {}
        if self._blink_min_box is not None:
            self._blink_min_box.setText(str(blink.get("interval-min-ms", "")))
        if self._blink_max_box is not None:
            self._blink_max_box.setText(str(blink.get("interval-max-ms", "")))
        if self._blink_duration_box is not None:
            self._blink_duration_box.setText(str(blink.get("duration-ms", "")))
        blink_images = {
            img.get("id"): img
            for img in self._profile.get("blink-images", [])
            if isinstance(img, dict)
        }
        for idx, combo in enumerate(self._blink_boxes):
            image = blink_images.get(idx)
            if not image:
                continue
            path_value = str(image.get("path-to-image", ""))
            if path_value and combo.findText(path_value) == -1:
                combo.addItem(path_value)
            combo.setCurrentText(path_value)

    def closeEvent(self, event):
        self.reject()
        event.accept()


def start_program():
    app = QApplication(sys.argv)
    window = PNGStreamerApp()
    window.show()
    app.exec()
