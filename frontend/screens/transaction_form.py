# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton
# Import Qt alignment and text-display options.
from PyQt6.QtCore import Qt
# Use regular expressions for text validation or wrapping.
import re

# Import the error type raised by persistent storage.
from backend.storage import StorageError
# Import transaction detail validation and formatting helpers.
from backend.transactions import amount_decimal


# Share field layout and submission behavior across transactions.
class TransactionFormScreen(QWidget):
    """Base for Send, Payment, Cash In and Cash Out (same layout as the wireframes).

    Subclasses set: kind, title, action_text, fields = [(key, label, placeholder)]
    and implement build_details(values, amount) -> (details, summary).
    """
    # Identify this form transaction for confirmation and execution.
    kind = ""
    # Set the heading displayed by the shared transaction form.
    title = ""
    # Set the label on the shared form submission button.
    action_text = "Continue"
    # Declare field keys, labels, and example text for the shared form.
    fields = []

    # Initialize the screen and its shared application reference.
    def __init__(self, main_window):
        # Initialize the inherited Qt widget or shared form.
        super().__init__()
        # Keep access to navigation and transaction operations.
        self.main_window = main_window
        # Map transaction field keys to their controls.
        self.inputs = {}

        # Create the main layout for this widget.
        layout = QVBoxLayout(self)
        # Set the space between this layout and its edges.
        layout.setContentsMargins(30, 10, 30, 30)
        # Set the gap between neighboring controls.
        layout.setSpacing(6)

        # Create the heading for this screen.
        title = QLabel(self.title)
        # Select the matching named stylesheet rule.
        title.setObjectName("titleLabel")
        # Place the widget in its layout or screen stack.
        layout.addWidget(title)

        # Build the fields configured by the transaction screen.
        for key, label, placeholder in self.fields:
            # Create the label for this screen element.
            field_label = QLabel(label)
            # Place the widget in its layout or screen stack.
            layout.addWidget(field_label)
            # Create the field type chosen by this transaction screen.
            widget = self.create_input(key, placeholder)
            # Associate the label with its keyboard focus target.
            field_label.setBuddy(widget)
            # Expose a descriptive name to assistive technology.
            widget.setAccessibleName(label)
            # Store the field control under its configured key.
            self.inputs[key] = widget
            # Place the widget in its layout or screen stack.
            layout.addWidget(widget)

        # Create the label for this screen element.
        amount_label = QLabel("Amount")
        # Place the widget in its layout or screen stack.
        layout.addWidget(amount_label)
        # Create the text entry field.
        self.amount_input = QLineEdit()
        # Associate the label with its keyboard focus target.
        amount_label.setBuddy(self.amount_input)
        # Expose a descriptive name to assistive technology.
        self.amount_input.setAccessibleName("Amount")
        # Show an example while the field is empty.
        self.amount_input.setPlaceholderText("0.00")
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.amount_input)

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

        # Push the remaining controls toward the bottom.
        layout.addStretch()

        # Arrange the form actions side by side.
        buttons = QHBoxLayout()
        # Create the button for this wallet action.
        self.cancel_btn = QPushButton("Cancel")
        # Select the shared stylesheet class for this control.
        self.cancel_btn.setProperty("class", "secondary")
        # Connect this button to its wallet action.
        self.cancel_btn.clicked.connect(self.main_window.go_to_main_menu)
        # Create the button for this wallet action.
        self.action_btn = QPushButton(self.action_text)
        # Select the shared stylesheet class for this control.
        self.action_btn.setProperty("class", "primary")
        # Connect this button to its wallet action.
        self.action_btn.clicked.connect(self.on_submit)
        # Let Enter submit from the final input field.
        self.amount_input.returnPressed.connect(self.on_submit)
        # Place the widget in its layout or screen stack.
        buttons.addWidget(self.cancel_btn)
        # Place the widget in its layout or screen stack.
        buttons.addWidget(self.action_btn)
        # Place the grouped controls in the parent layout.
        layout.addLayout(buttons)

    # Create the control required for this form field.
    def create_input(self, key, placeholder):
        # Create an editable text field.
        field = QLineEdit()
        # Show an example while the field is empty.
        field.setPlaceholderText(placeholder)
        # Return the control created for this field.
        return field

    # Require each transaction screen to supply its own details.
    def build_details(self, values, amount):
        # Require a transaction-specific implementation in subclasses.
        raise NotImplementedError

    # Clear screen state before it is reused.
    def reset(self):
        # Restore every transaction field to its initial state.
        for widget in self.inputs.values():
            # Clear text fields when resetting the form.
            if isinstance(widget, QLineEdit):
                # Erase the previous value in this text field.
                widget.clear()
            # Restore dropdown fields to their first choice.
            elif isinstance(widget, QComboBox):
                # Restore the first dropdown choice.
                widget.setCurrentIndex(0)
        # Erase the previous transaction amount.
        self.amount_input.clear()
        # Clear the previous form error.
        self.error_label.setText("")

    # Validate thousands separators and convert the amount.
    def parse_amount(self):
        # Trim whitespace from the amount input.
        text = self.amount_input.text().strip()
        # Require commas to separate complete groups of three digits.
        if "," in text and re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?", text) is None:
            # Report why the requested wallet operation cannot proceed.
            raise ValueError("Use commas only between groups of three digits, such as 1,200.00.")
        # Remove display commas before validating the numeric amount.
        return amount_decimal(text.replace(",", ""))

    # Validate the form and open transaction confirmation.
    def on_submit(self):
        # Collect the cleaned form field values.
        values = {}
        # Read each transaction field from its matching control.
        for key, widget in self.inputs.items():
            # Read the selected option or the entered field text.
            text = widget.currentText() if isinstance(widget, QComboBox) else widget.text()
            # Store the field text without surrounding whitespace.
            values[key] = text.strip()
        # Require every transaction-specific field to be filled.
        if not all(values.values()):
            # Explain that all transaction fields are required.
            self.error_label.setText("Fill in every field.")
            # Stop this request before performing the next action.
            return

        # Clear the previous validation or storage error.
        self.error_label.clear()
        # Handle failures from the following wallet operation.
        try:
            # Parse and validate the entered transaction amount.
            amount = self.parse_amount()
            # Build validated transaction details and confirmation labels.
            details, summary = self.build_details(values, amount)
            # Show the validated details for PIN confirmation.
            self.main_window.go_to_confirm(self.kind, details, summary)
        # Show validation or storage failures within the screen.
        except (ValueError, StorageError) as error:
            # Show the operation failure as a readable error message.
            self.error_label.setText(str(error))
