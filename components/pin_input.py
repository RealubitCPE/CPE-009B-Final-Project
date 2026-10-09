from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator, QFont

class PinInputWidget(QWidget):
    def __init__(self, parent=None):
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
            
            # Simple styling for pin boxes
            line_edit.setStyleSheet("""
                QLineEdit {
                    background-color: #ffffff;
                    border: 1px solid #888888;
                    border-radius: 4px;
                }
                QLineEdit:focus {
                    border: 2px solid #195cbb;
                }
            """)
            
            self.inputs.append(line_edit)
            layout.addWidget(line_edit)
        
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def _text_changed(self, text):
        sender = self.sender()
        if text:
            idx = self.inputs.index(sender)
            if idx < 3:
                self.inputs[idx + 1].setFocus()
    
    def get_pin(self):
        return "".join([inp.text() for inp in self.inputs])
    
    def clear(self):
        for inp in self.inputs:
            inp.clear()
        self.inputs[0].setFocus()
