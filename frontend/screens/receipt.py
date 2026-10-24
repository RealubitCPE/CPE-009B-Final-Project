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
