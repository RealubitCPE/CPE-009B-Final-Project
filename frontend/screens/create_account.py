from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt
from backend.storage import StorageError
from frontend.components.pin_input import PinInputWidget

class CreateAccountScreen(QWidget):
    def __init__(self, app_main):
        """Initialize the screen and build its controls."""
        super().__init__()
        self.app_main = app_main
        self.init_ui()

    def init_ui(self):
        """Build the screen layout and connect its actions."""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 20, 40, 20)

        title = QLabel("Create Account")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        name_label = QLabel("Name")
        layout.addWidget(name_label)
        self.name_input = QLineEdit()
        name_label.setBuddy(self.name_input)
        self.name_input.setAccessibleName("Name")
        self.name_input.setPlaceholderText("Juan Dela Cruz")
        layout.addWidget(self.name_input)

        layout.addSpacing(10)

        mobile_label = QLabel("Mobile Number")
        layout.addWidget(mobile_label)
        self.mobile_input = QLineEdit()
        mobile_label.setBuddy(self.mobile_input)
        self.mobile_input.setAccessibleName("Mobile Number")
        self.mobile_input.setPlaceholderText("0917 000 0000")
        layout.addWidget(self.mobile_input)

        layout.addSpacing(10)

        pin_label = QLabel("Create a 4-digit PIN")
        layout.addWidget(pin_label)
        self.pin_input = PinInputWidget()
        pin_label.setBuddy(self.pin_input.inputs[0])
        layout.addWidget(self.pin_input)

        confirm_label = QLabel("Confirm PIN")
        layout.addWidget(confirm_label)
        self.confirm_pin_input = PinInputWidget()
        confirm_label.setBuddy(self.confirm_pin_input.inputs[0])
        for index, field in enumerate(self.pin_input.inputs, 1):
            field.setAccessibleName(f"New PIN digit {index}")
        for index, field in enumerate(self.confirm_pin_input.inputs, 1):
            field.setAccessibleName(f"Confirm PIN digit {index}")
        layout.addWidget(self.confirm_pin_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()

        self.back_btn = QPushButton("Back to Login")
        self.back_btn.setProperty("class", "secondary")
        self.back_btn.clicked.connect(self.app_main.go_to_login)
        btn_layout.addWidget(self.back_btn)

        self.create_btn = QPushButton("Create Account")
        self.create_btn.setProperty("class", "primary")
        self.create_btn.clicked.connect(self.on_create)
        self.confirm_pin_input.inputs[-1].returnPressed.connect(self.on_create)
        btn_layout.addWidget(self.create_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def reset(self):
        """Clear registration fields and focus the account name."""
        self.name_input.clear()
        self.mobile_input.clear()
        self.pin_input.clear()
        self.confirm_pin_input.clear()
        self.error_label.clear()
        self.name_input.setFocus()

    def on_create(self):
        """Submit registration details and clear the PIN fields afterward."""
        if not self.create_btn.isEnabled():
            return
        self.create_btn.setEnabled(False)
        self.error_label.clear()
        try:
            self.app_main.register_account(
                self.name_input.text().strip(), self.mobile_input.text().strip(),
                self.pin_input.get_pin(), self.confirm_pin_input.get_pin(),
            )
        except (ValueError, StorageError) as error:
            self.error_label.setText(str(error))
        finally:
            self.pin_input.clear()
            self.confirm_pin_input.clear()
            self.create_btn.setEnabled(True)
