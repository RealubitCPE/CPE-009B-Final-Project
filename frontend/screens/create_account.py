# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
# Import Qt alignment and text-display options.
from PyQt6.QtCore import Qt
# Import the error type raised by persistent storage.
from backend.storage import StorageError
# Import the reusable four-digit PIN control.
from frontend.components.pin_input import PinInputWidget

# Collect the account name, mobile number, and new PIN.
class CreateAccountScreen(QWidget):
    # Initialize the screen and its shared application reference.
    def __init__(self, app_main):
        # Initialize the inherited Qt widget or shared form.
        super().__init__()
        # Keep access to application navigation and account operations.
        self.app_main = app_main
        # Construct and connect this screen interface.
        self.init_ui()

    # Build the screen controls and connect their actions.
    def init_ui(self):
        # Create the main layout for this widget.
        layout = QVBoxLayout()
        # Set the space between this layout and its edges.
        layout.setContentsMargins(40, 20, 40, 20)

        # Create the heading for this screen.
        title = QLabel("Create Account")
        # Select the matching named stylesheet rule.
        title.setObjectName("titleLabel")
        # Place the widget in its layout or screen stack.
        layout.addWidget(title)

        # Create the label for this screen element.
        name_label = QLabel("Name")
        # Place the widget in its layout or screen stack.
        layout.addWidget(name_label)
        # Create the text entry field.
        self.name_input = QLineEdit()
        # Associate the label with its keyboard focus target.
        name_label.setBuddy(self.name_input)
        # Expose a descriptive name to assistive technology.
        self.name_input.setAccessibleName("Name")
        # Show an example while the field is empty.
        self.name_input.setPlaceholderText("Juan Dela Cruz")
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.name_input)

        # Insert extra space between form sections.
        layout.addSpacing(10)

        # Create the label for this screen element.
        mobile_label = QLabel("Mobile Number")
        # Place the widget in its layout or screen stack.
        layout.addWidget(mobile_label)
        # Create the text entry field.
        self.mobile_input = QLineEdit()
        # Associate the label with its keyboard focus target.
        mobile_label.setBuddy(self.mobile_input)
        # Expose a descriptive name to assistive technology.
        self.mobile_input.setAccessibleName("Mobile Number")
        # Show an example while the field is empty.
        self.mobile_input.setPlaceholderText("0917 000 0000")
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.mobile_input)

        # Insert extra space between form sections.
        layout.addSpacing(10)

        # Create the label for this screen element.
        pin_label = QLabel("Create a 4-digit PIN")
        # Place the widget in its layout or screen stack.
        layout.addWidget(pin_label)
        # Create the masked four-digit PIN entry control.
        self.pin_input = PinInputWidget()
        # Associate the label with its keyboard focus target.
        pin_label.setBuddy(self.pin_input.inputs[0])
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.pin_input)

        # Create the label for this screen element.
        confirm_label = QLabel("Confirm PIN")
        # Place the widget in its layout or screen stack.
        layout.addWidget(confirm_label)
        # Create the masked four-digit PIN entry control.
        self.confirm_pin_input = PinInputWidget()
        # Associate the label with its keyboard focus target.
        confirm_label.setBuddy(self.confirm_pin_input.inputs[0])
        # Give each PIN digit a distinct accessible label.
        for index, field in enumerate(self.pin_input.inputs, 1):
            # Expose a descriptive name to assistive technology.
            field.setAccessibleName(f"New PIN digit {index}")
        # Give each PIN digit a distinct accessible label.
        for index, field in enumerate(self.confirm_pin_input.inputs, 1):
            # Expose a descriptive name to assistive technology.
            field.setAccessibleName(f"Confirm PIN digit {index}")
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.confirm_pin_input)

        # Create the label for this screen element.
        self.error_label = QLabel("")
        # Select the matching named stylesheet rule.
        self.error_label.setObjectName("errorLabel")
        # Display text literally without interpreting markup.
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        # Allow long text to wrap within the available width.
        self.error_label.setWordWrap(True)
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.error_label)

        # Push the remaining controls toward the bottom.
        layout.addStretch()

        # Arrange navigation and submission actions side by side.
        btn_layout = QHBoxLayout()

        # Create the button for this wallet action.
        self.back_btn = QPushButton("Back to Login")
        # Select the shared stylesheet class for this control.
        self.back_btn.setProperty("class", "secondary")
        # Connect this button to its wallet action.
        self.back_btn.clicked.connect(self.app_main.go_to_login)
        # Place the widget in its layout or screen stack.
        btn_layout.addWidget(self.back_btn)

        # Create the button for this wallet action.
        self.create_btn = QPushButton("Create Account")
        # Select the shared stylesheet class for this control.
        self.create_btn.setProperty("class", "primary")
        # Connect this button to its wallet action.
        self.create_btn.clicked.connect(self.on_create)
        # Let Enter submit from the final input field.
        self.confirm_pin_input.inputs[-1].returnPressed.connect(self.on_create)
        # Place the widget in its layout or screen stack.
        btn_layout.addWidget(self.create_btn)

        # Place the grouped controls in the parent layout.
        layout.addLayout(btn_layout)
        # Attach the completed layout to this widget.
        self.setLayout(layout)

    # Clear screen state before it is reused.
    def reset(self):
        # Erase the previous account name.
        self.name_input.clear()
        # Erase the previous mobile number.
        self.mobile_input.clear()
        # Erase the entered PIN digits.
        self.pin_input.clear()
        # Erase the entered PIN digits.
        self.confirm_pin_input.clear()
        # Clear the previous validation or storage error.
        self.error_label.clear()
        # Move keyboard focus to the intended input.
        self.name_input.setFocus()

    # Submit registration details and display validation errors.
    def on_create(self):
        # Ignore another request while registration is submitting.
        if not self.create_btn.isEnabled():
            # Stop this request before performing the next action.
            return
        # Prevent duplicate submissions while this request runs.
        self.create_btn.setEnabled(False)
        # Clear the previous validation or storage error.
        self.error_label.clear()
        # Handle failures from the following wallet operation.
        try:
            # Pass the entered account details to registration.
            self.app_main.register_account(
                self.name_input.text().strip(), self.mobile_input.text().strip(),
                self.pin_input.get_pin(), self.confirm_pin_input.get_pin(),
            )
        # Show validation or storage failures within the screen.
        except (ValueError, StorageError) as error:
            # Show the operation failure as a readable error message.
            self.error_label.setText(str(error))
        # Restore controls and clear sensitive entry after any outcome.
        finally:
            # Erase the entered PIN digits.
            self.pin_input.clear()
            # Erase the entered PIN digits.
            self.confirm_pin_input.clear()
            # Allow another submission after the request finishes.
            self.create_btn.setEnabled(True)
