from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from components.pin_input import PinInputWidget

class LoginScreen(QWidget):
    def __init__(self, app_main):
        super().__init__()
        self.app_main = app_main
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel("User Login")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addWidget(QLabel("Mobile Number"))
        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("0917 000 0000")
        layout.addWidget(self.mobile_input)
        
        layout.addSpacing(20)
        
        layout.addWidget(QLabel("Enter your 4-digit PIN"))
        self.pin_input = PinInputWidget()
        layout.addWidget(self.pin_input)
        
        layout.addStretch()
        
        self.login_btn = QPushButton("Login")
        self.login_btn.setProperty("class", "primary")
        self.login_btn.clicked.connect(self.app_main.go_to_main_menu)
        layout.addWidget(self.login_btn)
        
        layout.addSpacing(10)
        
        self.create_btn = QPushButton("Create Account")
        self.create_btn.setProperty("class", "secondary")
        self.create_btn.clicked.connect(self.app_main.go_to_create_account)
        layout.addWidget(self.create_btn)
        
        self.setLayout(layout)
