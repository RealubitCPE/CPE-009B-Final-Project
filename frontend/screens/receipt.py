from datetime import datetime
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy, QLayout,
)
from PyQt6.QtCore import Qt


class ReceiptScreen(QWidget):
    def __init__(self, main_window):
        """Build a scrollable receipt card and its return-to-menu action."""
        super().__init__()
        self.main_window = main_window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 10, 30, 30)

        title = QLabel("Transaction Receipt")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        self.card = QFrame()
        self.card.setProperty("class", "card")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.receipt_scroll = QScrollArea()
        self.receipt_scroll.setWidgetResizable(True)
        self.receipt_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.receipt_scroll.setWidget(self.card)
        layout.addWidget(self.receipt_scroll, 1)

        self.done_btn = QPushButton("Done")
        self.done_btn.setProperty("class", "primary")
        self.done_btn.clicked.connect(self.main_window.go_to_main_menu)
        layout.addWidget(self.done_btn)

    def load(self, receipt):
        """Format the saved receipt into labeled rows with wrapped references."""
        stamp = datetime.strptime(f"{receipt['Date']} {receipt['Time']}", "%Y-%m-%d %H:%M:%S")
        rows = [
            ("Name", receipt["Name"]),
            ("Amount", f"{receipt['Amount']:,.2f}"),
            ("Account Details", receipt["Account Details"]),
            ("Transaction No.", receipt["Transaction Number"]),
            ("Date", stamp.strftime("%m/%d/%Y")),
            ("Time", stamp.strftime("%I:%M %p")),
        ]
        self.reset()
        for i, (label, value) in enumerate(rows):
            row_widget = QWidget()
            row_widget.setStyleSheet("background-color: transparent;")
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            left = QLabel(label)
            left.setObjectName("subtitleLabel")
            left.setTextFormat(Qt.TextFormat.PlainText)
            left.setWordWrap(True)
            value = str(value)
            # Add wrap points while retaining the original accessible text.
            display_value = re.sub(r"\S{20,}", lambda token: "\u200b".join(token.group()), value)
            right = QLabel(display_value)
            right.setAccessibleName(value)
            right.setToolTip(value)
            right.setTextFormat(Qt.TextFormat.PlainText)
            right.setWordWrap(True)
            right.setMinimumWidth(0)
            policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            policy.setHeightForWidth(True)
            right.setSizePolicy(policy)
            right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(left, 2)
            row.addWidget(right, 3)
            self.card_layout.addWidget(row_widget)
            if i < len(rows) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                self.card_layout.addWidget(line)
        self.receipt_scroll.verticalScrollBar().setValue(0)

    def reset(self):
        """Remove all widgets and nested layouts from the receipt card."""
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    item.layout().takeAt(0).widget().deleteLater()
