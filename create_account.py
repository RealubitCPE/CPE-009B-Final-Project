from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator, QFont

class PinInputWidget(QWidget):
    def __init__(self, parent=None):
        """Build four centered, masked boxes that each accept one digit."""
        super().__init__(parent)
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(0, 10, 0, 10)
        self.inputs = []
        regex = QRegularExpression(r"^[0-9]$")
        validator = QRegularExpressionValidator(regex)

        for i in range(4):
            line_edit = QLineEdit()
            line_edit.setFixedSize(60, 60)
            line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            line_edit.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            line_edit.setValidator(validator)
            line_edit.textChanged.connect(self._text_changed)

            line_edit.setStyleSheet("""
                QLineEdit {
                    background-color: #241733;
                    color: #f3e6d0;
                    border: 1px solid #3b2757;
                    border-radius: 8px;
                }
                QLineEdit:focus {
                    border: 2px solid #ff7a1a;
                }
            """)

            self.inputs.append(line_edit)
            layout.addWidget(line_edit)

        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def _text_changed(self, text):
        """Advance focus after a PIN box receives a digit."""
        sender = self.sender()
        if text:
            idx = self.inputs.index(sender)
            if idx < 3:
                self.inputs[idx + 1].setFocus()

    def get_pin(self):
        """Return the PIN digits joined in display order."""
        return "".join([inp.text() for inp in self.inputs])

    def clear(self):
        """Erase all PIN digits and focus the first box."""
        for inp in self.inputs:
            inp.clear()
        self.inputs[0].setFocus()
