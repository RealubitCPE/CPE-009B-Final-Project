# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QGridLayout
# Import Qt alignment and text-display options.
from PyQt6.QtCore import Qt

# Show the balance and available wallet actions.
class MainMenuScreen(QWidget):
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
        title = QLabel("Main Menu")
        # Select the matching named stylesheet rule.
        title.setObjectName("titleLabel")
        # Place the widget in its layout or screen stack.
        layout.addWidget(title)

        # Balance Card
        # Create the frame containing the balance display.
        card = QFrame()
        # Select the shared stylesheet class for this control.
        card.setProperty("class", "card")
        # Stack the balance card contents vertically.
        card_layout = QVBoxLayout()
        # Place the widget in its layout or screen stack.
        card_layout.addWidget(QLabel("Current Balance"))
        # Create the label for this screen element.
        self.balance_label = QLabel("PHP 0.00")
        # Select the matching named stylesheet rule.
        self.balance_label.setObjectName("balanceLabel")
        # Display text literally without interpreting markup.
        self.balance_label.setTextFormat(Qt.TextFormat.PlainText)
        # Allow long text to wrap within the available width.
        self.balance_label.setWordWrap(True)
        # Place the widget in its layout or screen stack.
        card_layout.addWidget(self.balance_label)
        # Attach the completed layout to this widget.
        card.setLayout(card_layout)
        # Place the widget in its layout or screen stack.
        layout.addWidget(card)

        # Insert extra space between form sections.
        layout.addSpacing(20)

        # Grid of buttons
        # Arrange the four wallet actions in a grid.
        grid = QGridLayout()
        # Set the gap between neighboring controls.
        grid.setSpacing(15)

        # Create the button for this wallet action.
        self.send_btn = QPushButton("Send")
        # Select the shared stylesheet class for this control.
        self.send_btn.setProperty("class", "menuButton")
        # Connect this button to its wallet action.
        self.send_btn.clicked.connect(self.app_main.go_to_send)
        # Give the menu button a large click target.
        self.send_btn.setMinimumHeight(100)
        # Place the widget in its layout or screen stack.
        grid.addWidget(self.send_btn, 0, 0)

        # Create the button for this wallet action.
        self.pay_btn = QPushButton("Payment")
        # Select the shared stylesheet class for this control.
        self.pay_btn.setProperty("class", "menuButton")
        # Connect this button to its wallet action.
        self.pay_btn.clicked.connect(self.app_main.go_to_payment)
        # Give the menu button a large click target.
        self.pay_btn.setMinimumHeight(100)
        # Place the widget in its layout or screen stack.
        grid.addWidget(self.pay_btn, 0, 1)

        # Create the button for this wallet action.
        self.cashin_btn = QPushButton("Cash In")
        # Select the shared stylesheet class for this control.
        self.cashin_btn.setProperty("class", "menuButton")
        # Give the menu button a large click target.
        self.cashin_btn.setMinimumHeight(100)
        # Connect this button to its wallet action.
        self.cashin_btn.clicked.connect(self.app_main.go_to_cash_in)
        # Place the widget in its layout or screen stack.
        grid.addWidget(self.cashin_btn, 1, 0)

        # Create the button for this wallet action.
        self.cashout_btn = QPushButton("Cash Out")
        # Select the shared stylesheet class for this control.
        self.cashout_btn.setProperty("class", "menuButton")
        # Give the menu button a large click target.
        self.cashout_btn.setMinimumHeight(100)
        # Connect this button to its wallet action.
        self.cashout_btn.clicked.connect(self.app_main.go_to_cash_out)
        # Place the widget in its layout or screen stack.
        grid.addWidget(self.cashout_btn, 1, 1)

        # Place the grouped controls in the parent layout.
        layout.addLayout(grid)
        # Push the remaining controls toward the bottom.
        layout.addStretch()

        # Create the button for this wallet action.
        self.logout_btn = QPushButton("Log Out")
        # Select the shared stylesheet class for this control.
        self.logout_btn.setProperty("class", "secondary")
        # Connect this button to its wallet action.
        self.logout_btn.clicked.connect(self.app_main.go_to_login)
        # Place the widget in its layout or screen stack.
        layout.addWidget(self.logout_btn)

        # Attach the completed layout to this widget.
        self.setLayout(layout)

    # Update the displayed balance from the signed-in user.
    def refresh(self):
        # Read the account currently signed in.
        user = self.app_main.current_user
        # Use the account balance, or zero when signed out.
        balance = user.balance if user is not None else 0
        # Display the balance with currency and two decimal places.
        self.balance_label.setText(f"PHP {balance:,.2f}")
