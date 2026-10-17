# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
# Import Qt alignment and text-display options.
from PyQt6.QtCore import Qt
# Import the error type raised by persistent storage.
from backend.storage import StorageError
# Import the reusable four-digit PIN control.
from frontend.components.pin_input import PinInputWidget

# Collect credentials for an existing account.
class LoginScreen(QWidget):
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
        layout.setContentsMargins(40, 40, 40, 40)

        # Create the heading for this screen.
        title = QLabel("User Login")
        # Select the matching named stylesheet rule.
        title.setObjectName("titleLabel")
        # Place the widget in its layout or screen stack.
        layout.addWidget(title)

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
        layout.addSpacing(20)

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
            field.setAccessibleName(f"Login PIN digit {index}")
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.pin_input)

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

        # Create the button for this wallet action.
        self.login_btn = QPushButton("Login")
        # Select the shared stylesheet class for this control.
        self.login_btn.setProperty("class", "primary")
        # Connect this button to its wallet action.
        self.login_btn.clicked.connect(self.on_login)
        # Let Enter submit from the final input field.
        self.pin_input.inputs[-1].returnPressed.connect(self.on_login)
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.login_btn)

        # Insert extra space between form sections.
        layout.addSpacing(10)

        # Create the button for this wallet action.
        self.create_btn = QPushButton("Create Account")
        # Select the shared stylesheet class for this control.
        self.create_btn.setProperty("class", "secondary")
        # Connect this button to its wallet action.
        self.create_btn.clicked.connect(self.app_main.go_to_create_account)
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.create_btn)

        # Attach the completed layout to this widget.
        self.setLayout(layout)

    # Clear screen state before it is reused.
    def reset(self):
        # Erase the previous mobile number.
        self.mobile_input.clear()
        # Erase the entered PIN digits.
        self.pin_input.clear()
        # Clear the previous validation or storage error.
        self.error_label.clear()
        # Move keyboard focus to the intended input.
        self.mobile_input.setFocus()

    # Submit login details and display authentication errors.
    def on_login(self):
        # Ignore another request while login is submitting.
        if not self.login_btn.isEnabled():
            # Stop this request before performing the next action.
            return
        # Prevent duplicate submissions while this request runs.
        self.login_btn.setEnabled(False)
        # Clear the previous validation or storage error.
        self.error_label.clear()
        # Handle failures from the following wallet operation.
        try:
            # Authenticate with the trimmed mobile number and entered PIN.
            self.app_main.authenticate(self.mobile_input.text().strip(), self.pin_input.get_pin())
        # Show validation or storage failures within the screen.
        except (ValueError, StorageError) as error:
            # Show the operation failure as a readable error message.
            self.error_label.setText(str(error))
        # Restore controls and clear sensitive entry after any outcome.
        finally:
            # Erase the entered PIN digits.
            self.pin_input.clear()
            # Allow another submission after the request finishes.
            self.login_btn.setEnabled(True)
