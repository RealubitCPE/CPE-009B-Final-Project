# Import receipt date and time parsing.
from datetime import datetime
# Use regular expressions for text validation or wrapping.
import re

# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy, QLayout,
)
# Import Qt alignment and text-display options.
from PyQt6.QtCore import Qt


# Display the saved transaction receipt in a scrollable card.
class ReceiptScreen(QWidget):
    # Initialize the screen and its shared application reference.
    def __init__(self, main_window):
        # Initialize the inherited Qt widget or shared form.
        super().__init__()
        # Keep access to navigation and transaction operations.
        self.main_window = main_window

        # Create the main layout for this widget.
        layout = QVBoxLayout(self)
        # Set the space between this layout and its edges.
        layout.setContentsMargins(30, 10, 30, 30)

        # Create the heading for this screen.
        title = QLabel("Transaction Receipt")
        # Select the matching named stylesheet rule.
        title.setObjectName("titleLabel")
        # Place the widget in its layout or screen stack.
        layout.addWidget(title)

        # Create the frame for the transaction information card.
        self.card = QFrame()
        # Select the shared stylesheet class for this control.
        self.card.setProperty("class", "card")
        # Arrange the transaction information inside the card.
        self.card_layout = QVBoxLayout(self.card)
        # Keep the layout large enough for its contents.
        self.card_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        # Keep transaction details anchored at the top of the card.
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # Create a scrollable area for long transaction details.
        self.receipt_scroll = QScrollArea()
        # Resize the scroll content to use available space.
        self.receipt_scroll.setWidgetResizable(True)
        # Hide the extra border around the scroll area.
        self.receipt_scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Place the information card inside the scroll area.
        self.receipt_scroll.setWidget(self.card)
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.receipt_scroll, 1)

        # Create the button for this wallet action.
        self.done_btn = QPushButton("Done")
        # Select the shared stylesheet class for this control.
        self.done_btn.setProperty("class", "primary")
        # Connect this button to its wallet action.
        self.done_btn.clicked.connect(self.main_window.go_to_main_menu)
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.done_btn)

    # Populate this screen with the supplied transaction information.
    def load(self, receipt):
        # Parse the saved receipt date and time for display formatting.
        stamp = datetime.strptime(f"{receipt['Date']} {receipt['Time']}", "%Y-%m-%d %H:%M:%S")
        # Choose and format the receipt fields for display.
        rows = [
            ("Name", receipt["Name"]),
            ("Amount", f"{receipt['Amount']:,.2f}"),
            ("Account Details", receipt["Account Details"]),
            ("Transaction No.", receipt["Transaction Number"]),
            ("Date", stamp.strftime("%m/%d/%Y")),
            ("Time", stamp.strftime("%I:%M %p")),
        ]
        # Clear previous screen state before continuing.
        self.reset()
        # Render the receipt fields in their chosen order.
        for i, (label, value) in enumerate(rows):
            # Group one receipt label and its value.
            row_widget = QWidget()
            # Let each receipt row share the card background.
            row_widget.setStyleSheet("background-color: transparent;")
            # Arrange this receipt label and value horizontally.
            row = QHBoxLayout(row_widget)
            # Set the space between this layout and its edges.
            row.setContentsMargins(0, 0, 0, 0)
            # Keep the layout large enough for its contents.
            row.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            # Create the label for this screen element.
            left = QLabel(label)
            # Select the matching named stylesheet rule.
            left.setObjectName("subtitleLabel")
            # Display text literally without interpreting markup.
            left.setTextFormat(Qt.TextFormat.PlainText)
            # Allow long text to wrap within the available width.
            left.setWordWrap(True)
            # Convert the receipt value to plain display text.
            value = str(value)
            # Plain-text QLabel needs break opportunities inside long references.
            # Insert invisible break points into long receipt references.
            display_value = re.sub(r"\S{20,}", lambda token: "\u200b".join(token.group()), value)
            # Create the label for this screen element.
            right = QLabel(display_value)
            # Expose a descriptive name to assistive technology.
            right.setAccessibleName(value)
            # Expose the original unbroken value on hover.
            right.setToolTip(value)
            # Display text literally without interpreting markup.
            right.setTextFormat(Qt.TextFormat.PlainText)
            # Allow long text to wrap within the available width.
            right.setWordWrap(True)
            # Allow the label to shrink within its container.
            right.setMinimumWidth(0)
            # Allow long text to shrink horizontally and grow vertically.
            policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            # Let wrapped text request additional vertical space.
            policy.setHeightForWidth(True)
            # Apply sizing rules that accommodate wrapped text.
            right.setSizePolicy(policy)
            # Align receipt values against the right edge.
            right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Place the widget in its layout or screen stack.
            row.addWidget(left, 2)
            # Place the widget in its layout or screen stack.
            row.addWidget(right, 3)
            # Place the widget in its layout or screen stack.
            self.card_layout.addWidget(row_widget)
            # Separate each receipt row except the final one.
            if i < len(rows) - 1:
                # Create a separator between receipt rows.
                line = QFrame()
                # Draw a horizontal separator between receipt rows.
                line.setFrameShape(QFrame.Shape.HLine)
                # Place the widget in its layout or screen stack.
                self.card_layout.addWidget(line)
        # Return the scroll view to the top.
        self.receipt_scroll.verticalScrollBar().setValue(0)

    # Clear screen state before it is reused.
    def reset(self):
        # Remove all previously displayed information from the card.
        while self.card_layout.count():
            # Remove the next layout item for cleanup.
            item = self.card_layout.takeAt(0)
            # Clean up a widget removed from the receipt layout.
            if item.widget():
                # Schedule the removed widget for safe Qt cleanup.
                item.widget().deleteLater()
            # Clean up any nested receipt layout contents.
            elif item.layout():
                # Remove the remaining widgets from this nested layout.
                while item.layout().count():
                    # Schedule the removed widget for safe Qt cleanup.
                    item.layout().takeAt(0).widget().deleteLater()
