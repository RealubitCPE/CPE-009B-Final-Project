# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit
# Import Qt alignment and the digit-matching expression type.
from PyQt6.QtCore import Qt, QRegularExpression
# Import PIN validation and font helpers.
from PyQt6.QtGui import QRegularExpressionValidator, QFont

# Present four masked digit boxes as one PIN control.
class PinInputWidget(QWidget):
    # Build four centered, masked PIN digit boxes.
    def __init__(self, parent=None):
        # Initialize the inherited Qt widget or shared form.
        super().__init__(parent)
        # Create the main layout for this widget.
        layout = QHBoxLayout()
        # Set the gap between neighboring controls.
        layout.setSpacing(15)
        # Set the space between this layout and its edges.
        layout.setContentsMargins(0, 10, 0, 10)
        # Keep the PIN boxes in digit order.
        self.inputs = []
        # Accept exactly one ASCII digit in each PIN box.
        regex = QRegularExpression(r"^[0-9]$")
        # Apply the single-digit rule to PIN entry.
        validator = QRegularExpressionValidator(regex)

        # Build one input box for each of the four PIN digits.
        for i in range(4):
            # Create one PIN digit box.
            line_edit = QLineEdit()
            # Give every PIN digit box the same square size.
            line_edit.setFixedSize(60, 60)
            # Center the PIN boxes or their digit text.
            line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Mask the entered PIN digit.
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            # Use a large bold font for PIN entry.
            line_edit.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            # Restrict the box to one numeric PIN digit.
            line_edit.setValidator(validator)
            # Move focus automatically when a PIN digit changes.
            line_edit.textChanged.connect(self._text_changed)

            # Simple styling for pin boxes
            # Apply the existing stylesheet to this widget.
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

            # Retain this PIN box in display order.
            self.inputs.append(line_edit)
            # Place the widget in its layout or screen stack.
            layout.addWidget(line_edit)

        # Center the PIN boxes or their digit text.
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Attach the completed layout to this widget.
        self.setLayout(layout)

    # Advance focus when a PIN digit is entered.
    def _text_changed(self, text):
        # Identify the PIN box whose text changed.
        sender = self.sender()
        # Advance only after the current box contains a digit.
        if text:
            # Find the changed box in the PIN sequence.
            idx = self.inputs.index(sender)
            # Keep focus within the four available PIN boxes.
            if idx < 3:
                # Move keyboard focus to the intended input.
                self.inputs[idx + 1].setFocus()

    # Collect the four PIN boxes in their display order.
    def get_pin(self):
        # Join the digit values into the complete PIN.
        return "".join([inp.text() for inp in self.inputs])

    # Erase the PIN and return focus to its first box.
    def clear(self):
        # Clear each digit box in sequence.
        for inp in self.inputs:
            # Erase the entered PIN digits.
            inp.clear()
        # Move keyboard focus to the intended input.
        self.inputs[0].setFocus()
