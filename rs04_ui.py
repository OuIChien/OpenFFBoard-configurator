from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox
from base_ui import WidgetUI, CommunicationHandler
import main

class RS04UI(WidgetUI, CommunicationHandler):
    def __init__(self, main: 'main.MainUi'=None, unique=0):
        WidgetUI.__init__(self, main, 'rs04.ui')
        CommunicationHandler.__init__(self)
        self.main = main
        self.instance = unique
        self.timer = QTimer(self)

        # 绑定 UI 控件
        self.comboBox_protocol.currentIndexChanged.connect(self.protocolChanged)
        self.spinBox_canid.valueChanged.connect(self.canIdChanged)
        self.spinBox_maxtorque.valueChanged.connect(self.maxTorqueChanged)
        self.pushButton_refresh.clicked.connect(self.refreshParams)
        
        self.timer.timeout.connect(self.updateStatus)

        # 注册回调
        self.register_callback("rs04", "protocol", self.updateProtocolUI, self.instance, int)
        self.register_callback("rs04", "canid", self.spinBox_canid.setValue, self.instance, int)
        self.register_callback("rs04", "maxtorque", self.spinBox_maxtorque.setValue, self.instance, int)
        self.register_callback("rs04", "connected", self.updateConnectedStatus, self.instance, int)

        self.refreshParams()

    def refreshParams(self):
        self.send_commands("rs04", ["protocol", "canid", "maxtorque", "connected"], self.instance)

    def updateProtocolUI(self, val):
        self.comboBox_protocol.blockSignals(True)
        self.comboBox_protocol.setCurrentIndex(val)
        self.comboBox_protocol.blockSignals(False)
        # 如果是私有协议，显示特定提示
        mode = "Private" if val == 1 else "MIT"
        self.label_mode_hint.setText(f"Current Mode: {mode}")

    def protocolChanged(self, index):
        self.send_value("rs04", "protocol", index, instance=self.instance)
        QMessageBox.information(self, "Protocol Change", "Protocol changed. Please power cycle the motor or reset the FFBoard for changes to take effect.")

    def canIdChanged(self, val):
        self.send_value("rs04", "canid", val, instance=self.instance)

    def maxTorqueChanged(self, val):
        self.send_value("rs04", "maxtorque", val, instance=self.instance)

    def updateConnectedStatus(self, connected):
        status_text = "● MOTOR CONNECTED" if connected else "○ MOTOR DISCONNECTED"
        color = "#27ae60" if connected else "#c0392b"
        self.label_status.setText(status_text)
        self.label_status.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 14px;")

    def updateStatus(self):
        # 仅查询连接状态
        self.send_command("rs04", "connected", self.instance, typechar='?')

    def showEvent(self, event):
        self.refreshParams()
        self.timer.start(1000)

    def hideEvent(self, event):
        self.timer.stop()
