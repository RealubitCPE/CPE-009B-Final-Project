from pathlib import Path

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from backend.storage import StorageError
from frontend.components.pin_input import PinInputWidget

LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "digicash-logo.png"

class LoginScreen(QWidget):
    def __init__(self, app_main):
        """Initialize the screen and build its controls."""
        super().__init__()
        self.app_main = app_main
        self.init_ui()

    def init_ui(self):
        """Build the screen layout and connect its actions."""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        pixmap = QPixmap(str(LOGO_PATH))
        if not pixmap.isNull():
            self.logo_label = QLabel()
            self.logo_label.setPixmap(
                pixmap.scaledToWidth(
                    130, Qt.TransformationMode.SmoothTransformation
                )
            )
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.logo_label.setAccessibleName("DigiCash logo")
            layout.addWidget(self.logo_label)

        title = QLabel("User Login")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        mobile_label = QLabel("Mobile Number")
        layout.addWidget(mobile_label)
        self.mobile_input = QLineEdit()
        mobile_label.setBuddy(self.mobile_input)
        self.mobile_input.setAccessibleName("Mobile Number")
        self.mobile_input.setPlaceholderText("0917 000 0000")
        layout.addWidget(self.mobile_input)

        layout.addSpacing(20)

        pin_label = QLabel("Enter your 4-digit PIN")
        layout.addWidget(pin_label)
        self.pin_input = PinInputWidget()
        pin_label.setBuddy(self.pin_input.inputs[0])
        for index, field in enumerate(self.pin_input.inputs, 1):
            field.setAccessibleName(f"Login PIN digit {index}")
        layout.addWidget(self.pin_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        layout.addStretch()

        self.login_btn = QPushButton("Login")
        self.login_btn.setProperty("class", "primary")
        self.login_btn.clicked.connect(self.on_login)
        self.pin_input.inputs[-1].returnPressed.connect(self.on_login)
        layout.addWidget(self.login_btn)

        layout.addSpacing(10)

        self.create_btn = QPushButton("Create Account")
        self.create_btn.setProperty("class", "secondary")
        self.create_btn.clicked.connect(self.app_main.go_to_create_account)
        layout.addWidget(self.create_btn)

        self.setLayout(layout)

    def reset(self):
        """Clear login fields and focus the mobile number."""
        self.mobile_input.clear()
        self.pin_input.clear()
        self.error_label.clear()
        self.mobile_input.setFocus()

    def on_login(self):
        """Authenticate the entered credentials and clear the PIN afterward."""
        if not self.login_btn.isEnabled():
            return
        self.login_btn.setEnabled(False)
        self.error_label.clear()
        try:
            self.app_main.authenticate(self.mobile_input.text().strip(), self.pin_input.get_pin())
        except (ValueError, StorageError) as error:
            self.error_label.setText(str(error))
        finally:
            self.pin_input.clear()
            self.login_btn.setEnabled(True)
