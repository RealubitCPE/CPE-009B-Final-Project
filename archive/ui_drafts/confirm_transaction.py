from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy, QLayout,
)
from PyQt6.QtCore import Qt
import re

from frontend.components.pin_input import PinInputWidget
from backend.storage import StorageError


class ConfirmTransactionScreen(QWidget):
    def __init__(self, main_window):
        """Build the transaction summary, PIN entry, and confirmation controls."""
        super().__init__()
        self.main_window = main_window
        self.kind = None
        self.details = None
        self._executing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 10, 30, 30)

        title = QLabel("Confirm Transaction")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        self.card = QFrame()
        self.card.setProperty("class", "card")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.summary_scroll = QScrollArea()
        self.summary_scroll.setWidgetResizable(True)
        self.summary_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.summary_scroll.setWidget(self.card)
        layout.addWidget(self.summary_scroll, 1)

        layout.addSpacing(10)
        pin_label = QLabel("Enter your 4-digit PIN")
        layout.addWidget(pin_label)
        self.pin_input = PinInputWidget()
        pin_label.setBuddy(self.pin_input.inputs[0])
        for index, field in enumerate(self.pin_input.inputs, 1):
            field.setAccessibleName(f"Transaction PIN digit {index}")
        layout.addWidget(self.pin_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setProperty("class", "secondary")
        self.cancel_btn.clicked.connect(self.on_cancel)
        self.verify_btn = QPushButton("Verify")
        self.verify_btn.setProperty("class", "primary")
        self.verify_btn.setEnabled(False)
        self.verify_btn.clicked.connect(self.on_verify)
        self.pin_input.inputs[-1].returnPressed.connect(self.on_verify)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.verify_btn)
        layout.addLayout(buttons)

    def reset(self):
        """Discard confirmation details, clear the card and PIN, and disable verification."""
        self.kind, self.details = None, None
        while self.card_layout.count():
            self.card_layout.takeAt(0).widget().deleteLater()
        self.pin_input.clear()
        self.error_label.clear()
        self.verify_btn.setEnabled(False)

    def load(self, kind, details, summary):
        """Display a transaction summary and enable PIN verification."""
        self.reset()
        self.kind, self.details = kind, details
        for line in summary:
            text = str(line)
            # Add wrap points while retaining the original accessible text.
            display_text = re.sub(r"\S{20,}", lambda token: "\u200b".join(token.group()), text)
            label = QLabel(display_text)
            label.setAccessibleName(text)
            label.setToolTip(text)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            policy.setHeightForWidth(True)
            label.setSizePolicy(policy)
            self.card_layout.addWidget(label)
        self.summary_scroll.verticalScrollBar().setValue(0)
        self.verify_btn.setEnabled(True)

    def on_cancel(self):
        """Clear confirmation and return to the menu when execution is idle."""
        if self._executing:
            return
        self.reset()
        self.main_window.go_to_main_menu()

    def on_verify(self):
        """Submit the staged transaction once and display its result or error."""
        # Ignore reentrant clicks and stale confirmation requests.
        if self._executing or self.kind is None or self.details is None:
            return
        self._executing = True
        self.verify_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.error_label.clear()
        try:
            receipt = self.main_window.execute_transaction(
                self.kind, self.details, self.pin_input.get_pin(),
            )
        except (ValueError, StorageError) as error:
            self.error_label.setText(str(error))
            self.pin_input.clear()
            # Discard saved details even when a later storage step reports an error.
            if isinstance(error, StorageError) and error.committed:
                self.kind, self.details = None, None
        else:
            self.reset()
            self.main_window.go_to_receipt(receipt)
        finally:
            self._executing = False
            self.verify_btn.setEnabled(self.details is not None)
            self.cancel_btn.setEnabled(True)
