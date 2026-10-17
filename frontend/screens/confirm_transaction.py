# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QSizePolicy, QLayout,
)
# Import Qt alignment and text-display options.
from PyQt6.QtCore import Qt
# Use regular expressions for text validation or wrapping.
import re

# Import the reusable four-digit PIN control.
from frontend.components.pin_input import PinInputWidget
# Import the error type raised by persistent storage.
from backend.storage import StorageError


# Show transaction details and request PIN verification.
class ConfirmTransactionScreen(QWidget):
    # Initialize the screen and its shared application reference.
    def __init__(self, main_window):
        # Initialize the inherited Qt widget or shared form.
        super().__init__()
        # Keep access to navigation and transaction operations.
        self.main_window = main_window
        # Track the transaction action represented by this screen.
        self.kind = None
        # Retain the transaction details awaiting submission.
        self.details = None
        # Mark transaction submission as idle.
        self._executing = False

        # Create the main layout for this widget.
        layout = QVBoxLayout(self)
        # Set the space between this layout and its edges.
        layout.setContentsMargins(30, 10, 30, 30)

        # Create the heading for this screen.
        title = QLabel("Confirm Transaction")
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
        self.summary_scroll = QScrollArea()
        # Resize the scroll content to use available space.
        self.summary_scroll.setWidgetResizable(True)
        # Hide the extra border around the scroll area.
        self.summary_scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Place the information card inside the scroll area.
        self.summary_scroll.setWidget(self.card)
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.summary_scroll, 1)

        # Insert extra space between form sections.
        layout.addSpacing(10)
        # Create the label for this screen element.
        pin_label = QLabel("Enter your 4-digit PIN")
        # Place the widget in its layout or screen stack.
        layout.addWidget(pin_label)
        # Create the masked four-digit PIN entry control.
        self.pin_input = PinInputWidget()
        # Associate the label with its keyboard focus target.
        pin_label.setBuddy(self.pin_input.inputs[0])
        # Give each PIN digit a distinct accessible label.
        for index, field in enumerate(self.pin_input.inputs, 1):
            # Expose a descriptive name to assistive technology.
            field.setAccessibleName(f"Transaction PIN digit {index}")
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.pin_input)

        # Create the label for this screen element.
        self.error_label = QLabel("")
        # Select the matching named stylesheet rule.
        self.error_label.setObjectName("errorLabel")
        # Allow long text to wrap within the available width.
        self.error_label.setWordWrap(True)
        # Display text literally without interpreting markup.
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.error_label)

        # Arrange the form actions side by side.
        buttons = QHBoxLayout()
        # Create the button for this wallet action.
        self.cancel_btn = QPushButton("Cancel")
        # Select the shared stylesheet class for this control.
        self.cancel_btn.setProperty("class", "secondary")
        # Connect this button to its wallet action.
        self.cancel_btn.clicked.connect(self.on_cancel)
        # Create the button for this wallet action.
        self.verify_btn = QPushButton("Verify")
        # Select the shared stylesheet class for this control.
        self.verify_btn.setProperty("class", "primary")
        # Prevent verification until this action is ready.
        self.verify_btn.setEnabled(False)
        # Connect this button to its wallet action.
        self.verify_btn.clicked.connect(self.on_verify)
        # Let Enter submit from the final input field.
        self.pin_input.inputs[-1].returnPressed.connect(self.on_verify)
        # Place the widget in its layout or screen stack.
        buttons.addWidget(self.cancel_btn)
        # Place the widget in its layout or screen stack.
        buttons.addWidget(self.verify_btn)
        # Place the grouped controls in the parent layout.
        layout.addLayout(buttons)

    # Clear screen state before it is reused.
    def reset(self):
        # Discard the action and details from the previous confirmation.
        self.kind, self.details = None, None
        # Remove all previously displayed information from the card.
        while self.card_layout.count():
            # Schedule the removed widget for safe Qt cleanup.
            self.card_layout.takeAt(0).widget().deleteLater()
        # Erase the entered PIN digits.
        self.pin_input.clear()
        # Clear the previous validation or storage error.
        self.error_label.clear()
        # Prevent verification until this action is ready.
        self.verify_btn.setEnabled(False)

    # Populate this screen with the supplied transaction information.
    def load(self, kind, details, summary):
        # Clear previous screen state before continuing.
        self.reset()
        # Retain the selected action and validated transaction details.
        self.kind, self.details = kind, details
        # Render each confirmation summary line.
        for line in summary:
            # Convert the summary value to displayable text.
            text = str(line)
            # Insert invisible break points into long confirmation references.
            display_text = re.sub(r"\S{20,}", lambda token: "\u200b".join(token.group()), text)
            # Create the label for this screen element.
            label = QLabel(display_text)
            # Expose a descriptive name to assistive technology.
            label.setAccessibleName(text)
            # Expose the original unbroken value on hover.
            label.setToolTip(text)
            # Display text literally without interpreting markup.
            label.setTextFormat(Qt.TextFormat.PlainText)
            # Allow long text to wrap within the available width.
            label.setWordWrap(True)
            # Allow the label to shrink within its container.
            label.setMinimumWidth(0)
            # Allow long text to shrink horizontally and grow vertically.
            policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            # Let wrapped text request additional vertical space.
            policy.setHeightForWidth(True)
            # Apply sizing rules that accommodate wrapped text.
            label.setSizePolicy(policy)
            # Place the widget in its layout or screen stack.
            self.card_layout.addWidget(label)
        # Return the scroll view to the top.
        self.summary_scroll.verticalScrollBar().setValue(0)
        # Allow verification of the loaded transaction.
        self.verify_btn.setEnabled(True)

    # Return to the menu when no transaction is executing.
    def on_cancel(self):
        # Keep navigation locked while submission is running.
        if self._executing:
            # Stop this request before performing the next action.
            return
        # Clear previous screen state before continuing.
        self.reset()
        # Return to the account menu.
        self.main_window.go_to_main_menu()

    # Submit the staged transaction once and handle its result.
    def on_verify(self):
        # Ignore duplicate submissions or missing transaction details.
        if self._executing or self.kind is None or self.details is None:
            # Stop this request before performing the next action.
            return
        # Block duplicate requests until this submission finishes.
        self._executing = True
        # Prevent verification until this action is ready.
        self.verify_btn.setEnabled(False)
        # Prevent cancellation while the transaction is executing.
        self.cancel_btn.setEnabled(False)
        # Clear the previous validation or storage error.
        self.error_label.clear()
        # Handle failures from the following wallet operation.
        try:
            # Run the selected transaction and retain its receipt.
            receipt = self.main_window.execute_transaction(
                self.kind, self.details, self.pin_input.get_pin(),
            )
        # Show validation or storage failures within the screen.
        except (ValueError, StorageError) as error:
            # Show the operation failure as a readable error message.
            self.error_label.setText(str(error))
            # Erase the entered PIN digits.
            self.pin_input.clear()
            # Discard details when storage reports an already committed change.
            if isinstance(error, StorageError) and error.committed:
                # Discard the action and details from the previous confirmation.
                self.kind, self.details = None, None
        # Continue with the receipt after a successful transaction.
        else:
            # Clear previous screen state before continuing.
            self.reset()
            # Display the completed transaction receipt.
            self.main_window.go_to_receipt(receipt)
        # Restore controls and clear sensitive entry after any outcome.
        finally:
            # Mark transaction submission as idle.
            self._executing = False
            # Allow retry only while valid staged details remain.
            self.verify_btn.setEnabled(self.details is not None)
            # Allow returning to the menu after execution finishes.
            self.cancel_btn.setEnabled(True)
