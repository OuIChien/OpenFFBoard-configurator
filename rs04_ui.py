import typing
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox
from base_ui import WidgetUI, CommunicationHandler

if typing.TYPE_CHECKING:
    import main

class RS04UI(WidgetUI, CommunicationHandler):
    def __init__(self, main: 'main.MainUi'=None, unique=0):
        WidgetUI.__init__(self, main, 'rs04.ui')
        CommunicationHandler.__init__(self)
        self.main = main
        self.instance = unique
        self.timer = QTimer(self)
        self._last_fault_val = 0

        # 绑定 UI 控件
        self.comboBox_protocol.currentIndexChanged.connect(self.protocolChanged)
        self.spinBox_canid.valueChanged.connect(self.canIdChanged)
        self.spinBox_maxtorque.valueChanged.connect(self.maxTorqueChanged)
        self.pushButton_refresh.clicked.connect(self.refreshParams)
        
        self.timer.timeout.connect(self.updateStatus)

        # 注册回调
        self.register_callback("rs04", "protocol", self.updateProtocolUI, self.instance, int)
        self.register_callback("rs04", "canid", self.canIdChangedCallback, self.instance, int)
        self.register_callback("rs04", "maxtorque", self.maxTorqueChangedCallback, self.instance, int)
        self.register_callback("rs04", "connected", self.updateConnectedStatus, self.instance, int)
        self.register_callback("rs04", "rawcan", self.updateRawCan, self.instance, int)
        self.register_callback("rs04", "lasterr", self.updateLastError, self.instance, int)
        self.register_callback("rs04", "version", self.updateVersion, self.instance, str)
        self.register_callback("rs04", "faultbits", self.updateFaultBits, self.instance, int)
        self.register_callback("rs04", "damper", self.updateDamperUI, self.instance, int)

        self.log("RS04 UI Initialized.")
        
        # Add dynamic debug labels and Save button
        from PyQt6.QtWidgets import QLabel, QPushButton, QHBoxLayout
        
        self.label_version = QLabel("Motor Version: Requesting...")
        self.label_raw_id = QLabel("Last Raw CAN ID: 0x00000000")
        self.label_last_error = QLabel("Rejection Reason: None")
        self.label_faults = QLabel("Motor Faults: None")
        self.label_faults.setWordWrap(True)
        self.label_faults.setStyleSheet("color: #27ae60; font-weight: bold;")
        
        # Damper Control
        from PyQt6.QtWidgets import QCheckBox
        self.checkBox_damper = QCheckBox("Disable Drag Protection (Damper)")
        self.checkBox_damper.setToolTip("Sets motor parameter 0x2028. Prevents motor from braking when unpowered/stopped.")
        self.checkBox_damper.stateChanged.connect(self.damperChanged)
        
        # Debug Buttons
        debug_layout = QHBoxLayout()
        self.pushButton_enable = QPushButton("ENABLE")
        self.pushButton_enable.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 30px;")
        self.pushButton_enable.clicked.connect(self.enableMotor)
        
        self.pushButton_stop = QPushButton("STOP / CLEAR FAULT")
        self.pushButton_stop.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; height: 30px;")
        self.pushButton_stop.clicked.connect(self.stopMotor)
        
        self.pushButton_setzero = QPushButton("SET ZERO")
        self.pushButton_setzero.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; height: 30px;")
        self.pushButton_setzero.clicked.connect(self.setZeroPosition)
        
        debug_layout.addWidget(self.pushButton_enable)
        debug_layout.addWidget(self.pushButton_stop)
        debug_layout.addWidget(self.pushButton_setzero)

        self.pushButton_save = QPushButton("SAVE PARAMETERS TO MOTOR")
        self.pushButton_save.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold;")
        self.pushButton_save.clicked.connect(self.saveMotorParams)
        
        # Insert before logs
        idx = self.verticalLayout.indexOf(self.label_log_title)
        self.verticalLayout.insertWidget(idx, self.label_version)
        self.verticalLayout.insertWidget(idx+1, self.label_raw_id)
        self.verticalLayout.insertWidget(idx+2, self.label_last_error)
        self.verticalLayout.insertWidget(idx+3, self.label_faults)
        self.verticalLayout.insertWidget(idx+4, self.checkBox_damper)
        self.verticalLayout.insertLayout(idx+5, debug_layout)
        self.verticalLayout.insertWidget(idx+6, self.pushButton_save)
        
        self.refreshParams()

    def log(self, message):
        self.textEdit_log.appendPlainText(message)

    def damperChanged(self, state):
        val = 1 if state == 2 else 0 
        self.send_value("rs04", "damper", val, instance=self.instance)
        self.log(f"Drag Protection {'Disabled' if val else 'Enabled'} command sent.")

    def enableMotor(self):
        self.send_value("rs04", "enable", 1, instance=self.instance)
        self.log("Enable command sent.")

    def stopMotor(self):
        self.send_value("rs04", "stop", 1, instance=self.instance)
        self.log("Stop / Clear Fault command sent.")

    def setZeroPosition(self):
        ret = QMessageBox.warning(self, "Set Mechanical Zero", "This will set current position as 0 rad. Ensure motor is in safe position. Continue?", 
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self.send_value("rs04", "setzero", 1, instance=self.instance)
            self.log("Set Zero command sent.")

    def refreshParams(self):
        self.log("Requesting parameters from motor...")
        self.send_commands("rs04", ["protocol", "canid", "maxtorque", "connected", "version", "damper"], self.instance)

    def saveMotorParams(self):
        ret = QMessageBox.question(self, "Save to Motor", "This will permanently save current settings (CAN ID, Protocol, etc.) to the motor's internal EEPROM. Continue?", 
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            self.send_value("rs04", "savemotor", 1, instance=self.instance)
            self.log("Save command sent to motor.")

    def updateVersion(self, version):
        self.label_version.setText(f"Motor Version: {version}")
        self._last_version = version

    def updateDamperUI(self, val):
        self.checkBox_damper.blockSignals(True)
        self.checkBox_damper.setChecked(val == 1)
        self.checkBox_damper.blockSignals(False)

    def updateFaultBits(self, val):
        if not hasattr(self, "_last_fault_val"):
            self._last_fault_val = 0

        # Only log if fault status changed
        if val == self._last_fault_val:
            return

        if val == 0:
            self.label_faults.setText("Motor Faults: None (System Normal)")
            self.label_faults.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.log("INFO: Motor fault cleared. System is now normal.")
            self._last_fault_val = 0
            return

        faults = []
        mapping = {
            0: "Over-temperature",
            1: "Driver chip fault",
            2: "Undervoltage",
            3: "Overvoltage",
            4: "Phase B sensor fault",
            5: "Phase C sensor fault",
            7: "Encoder not calibrated",
            8: "Hardware identify err",
            9: "Pos init err",
            14: "Stall protection",
            16: "Phase A sensor fault"
        }
        for bit, msg in mapping.items():
            if val & (1 << bit):
                faults.append(msg)
        
        err_str = ", ".join(faults) if faults else f"Unknown ({hex(val)})"
        self.label_faults.setText(f"Motor Faults: {err_str}")
        self.label_faults.setStyleSheet("color: #c0392b; font-weight: bold;")
        self.log(f"CRITICAL: Motor reported faults: {err_str}")
        self._last_fault_val = val

    def updateProtocolUI(self, val):
        self.comboBox_protocol.blockSignals(True)
        self.comboBox_protocol.setCurrentIndex(val)
        self.comboBox_protocol.blockSignals(False)
        mode = "Private" if val == 1 else "MIT"
        self.label_mode_hint.setText(f"Current Mode: {mode}")
        self.log(f"Protocol updated from firmware: {mode}")

    def protocolChanged(self, index):
        mode = "Private" if index == 1 else "MIT"
        self.log(f"Setting protocol to: {mode}")
        self.send_value("rs04", "protocol", index, instance=self.instance)
        QMessageBox.information(self, "Protocol Change", "Protocol changed. Please power cycle the motor or reset the FFBoard for changes to take effect.")

    def canIdChanged(self, val):
        self.send_value("rs04", "canid", val, instance=self.instance)

    def canIdChangedCallback(self, val):
        self.spinBox_canid.blockSignals(True)
        self.spinBox_canid.setValue(val)
        self.spinBox_canid.blockSignals(False)
        self.log(f"Motor CAN ID confirmed: {val}")

    def maxTorqueChanged(self, val):
        self.send_value("rs04", "maxtorque", val, instance=self.instance)

    def maxTorqueChangedCallback(self, val):
        self.spinBox_maxtorque.blockSignals(True)
        self.spinBox_maxtorque.setValue(val)
        self.spinBox_maxtorque.blockSignals(False)
        self.log(f"Max Torque confirmed: {val/100.0} Nm")

    def updateConnectedStatus(self, connected):
        status_text = "● MOTOR CONNECTED" if connected else "○ MOTOR DISCONNECTED"
        color = "#27ae60" if connected else "#c0392b"
        self.label_status.setText(status_text)
        self.label_status.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 14px;")
        if not hasattr(self, "_last_conn") or self._last_conn != connected:
            self.log(f"Connection state changed: {'Connected' if connected else 'Disconnected'}")
            self._last_conn = connected

    def updateRawCan(self, val):
        if hasattr(self, "label_raw_id"):
            self.label_raw_id.setText(f"Last Raw CAN ID: 0x{val:08X}")

    def updateLastError(self, val):
        err_map = {
            0: "No Error",
            1: "Wrong MotorID (Private Mode)",
            2: "Wrong Msg Type (Private Mode)",
            3: "Wrong MasterID (MIT Mode)",
            4: "Wrong MotorID (MIT Mode)"
        }
        err_msg = err_map.get(val, f"Unknown Error ({val})")
        if hasattr(self, "label_last_error"):
            self.label_last_error.setText(f"Rejection Reason: {err_msg}")

    def updateStatus(self):
        # Query status, debug info and version periodically
        self.send_commands("rs04", ["connected", "rawcan", "lasterr", "faultbits"], self.instance)

    def showEvent(self, event):
        self.refreshParams()
        self.timer.start(250) # 4Hz refresh for debugging

    def hideEvent(self, event):
        self.timer.stop()
