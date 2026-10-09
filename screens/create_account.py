from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from components.pin_input import PinInputWidget

class CreateAccountScreen(QWidget):
    def __init__(self, app_main):
        super().__init__()
        self.app_main = app_main
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 20, 40, 20)
        
        title = QLabel("Create Account")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addWidget(QLabel("Name"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Juan Dela Cruz")
        layout.addWidget(self.name_input)
        
        layout.addSpacing(10)

        layout.addWidget(QLabel("Mobile Number"))
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("0917 000 0000")
        layout.addWidget(self.mobile_input)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Create a 4-digit PIN"))
        self.pin_input = PinInputWidget()
        layout.addWidget(self.pin_input)

        layout.addWidget(QLabel("Confirm PIN"))
        self.confirm_pin_input = PinInputWidget()
        layout.addWidget(self.confirm_pin_input)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        
        self.back_btn = QPushButton("Back to Login")
        self.back_btn.setProperty("class", "secondary")
        self.back_btn.clicked.connect(self.app_main.go_to_login)
        btn_layout.addWidget(self.back_btn)
        
        self.create_btn = QPushButton("Create Account")
        self.create_btn.setProperty("class", "primary")
        self.create_btn.clicked.connect(self.app_main.go_to_main_menu)
        btn_layout.addWidget(self.create_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
