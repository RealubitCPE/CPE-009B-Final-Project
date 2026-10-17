from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton
from PyQt6.QtCore import Qt
import re

from backend.storage import StorageError
from backend.transactions import amount_decimal


class TransactionFormScreen(QWidget):
    """Base for Send, Payment, Cash In and Cash Out (same layout as the wireframes).

    Subclasses set: kind, title, action_text, fields = [(key, label, placeholder)]
    and implement build_details(values, amount) -> (details, summary).
    """
    kind = ""
    title = ""
    action_text = "Continue"
    fields = []

    def __init__(self, main_window):
        """Build configured transaction fields, amount entry, and submission controls."""
        super().__init__()
        self.main_window = main_window
        self.inputs = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 10, 30, 30)
        layout.setSpacing(6)

        title = QLabel(self.title)
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        for key, label, placeholder in self.fields:
            field_label = QLabel(label)
            layout.addWidget(field_label)
            widget = self.create_input(key, placeholder)
            field_label.setBuddy(widget)
            widget.setAccessibleName(label)
            self.inputs[key] = widget
            layout.addWidget(widget)

        amount_label = QLabel("Amount")
        layout.addWidget(amount_label)
        self.amount_input = QLineEdit()
        amount_label.setBuddy(self.amount_input)
        self.amount_input.setAccessibleName("Amount")
        self.amount_input.setPlaceholderText("0.00")
        layout.addWidget(self.amount_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.error_label)

        layout.addStretch()

        buttons = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "secondary")
        self.cancel_btn.clicked.connect(self.main_window.go_to_main_menu)
        self.action_btn = QPushButton(self.action_text)
        self.action_btn.setProperty("class", "primary")
        self.action_btn.clicked.connect(self.on_submit)
        self.amount_input.returnPressed.connect(self.on_submit)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.action_btn)
        layout.addLayout(buttons)

    def create_input(self, key, placeholder):
        """Create a text input using the supplied placeholder."""
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        return field

    def build_details(self, values, amount):
        """Require subclasses to return transaction details and confirmation text."""
        raise NotImplementedError

    def reset(self):
        """Clear text values, restore first dropdown choices, and remove errors."""
        for widget in self.inputs.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
        self.amount_input.clear()
        self.error_label.setText("")

    def parse_amount(self):
        """Validate comma grouping and return the entered decimal amount."""
        text = self.amount_input.text().strip()
        # Check comma grouping before removing display separators.
        if "," in text and re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?", text) is None:
            raise ValueError("Use commas only between groups of three digits, such as 1,200.00.")
        return amount_decimal(text.replace(",", ""))

    def on_submit(self):
        """Validate all form values and open transaction confirmation."""
        values = {}
        for key, widget in self.inputs.items():
            text = widget.currentText() if isinstance(widget, QComboBox) else widget.text()
            values[key] = text.strip()
        if not all(values.values()):
            self.error_label.setText("Fill in every field.")
            return

        self.error_label.clear()
        try:
            amount = self.parse_amount()
            details, summary = self.build_details(values, amount)
            self.main_window.go_to_confirm(self.kind, details, summary)
        except (ValueError, StorageError) as error:
            self.error_label.setText(str(error))
