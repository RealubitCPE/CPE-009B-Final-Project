# Access command-line arguments and the application exit status.
import sys

# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget

# Import persistent wallet account and transaction operations.
from backend import storage
# Import credential verification and authentication errors.
from backend.user import AuthenticationError, login
# Import the incoming-funds screen.
from frontend.screens.cash_in import CashInScreen
# Import the withdrawal screen.
from frontend.screens.cash_out import CashOutScreen
# Import the PIN confirmation screen.
from frontend.screens.confirm_transaction import ConfirmTransactionScreen
# Import the registration screen.
from frontend.screens.create_account import CreateAccountScreen
# Import the credential-entry screen.
from frontend.screens.login import LoginScreen
# Import the balance and wallet-action menu.
from frontend.screens.main_menu import MainMenuScreen
# Import the bill-payment screen.
from frontend.screens.payment import PaymentScreen
# Import the completed-transaction receipt screen.
from frontend.screens.receipt import ReceiptScreen
# Import the money-transfer screen.
from frontend.screens.send_money import SendMoneyScreen
# Import the shared application stylesheet.
from frontend.style import STYLE_SHEET


# Coordinate wallet screens, session state, and storage actions.
class EWalletApp(QMainWindow):
    # Initialize application state and create every wallet screen.
    def __init__(self):
        # Initialize the inherited Qt widget or shared form.
        super().__init__()
        # Set the title shown in the window frame.
        self.setWindowTitle("E-Wallet")
        # Keep the wallet window at its designed dimensions.
        self.setFixedSize(450, 750)
        # Apply the existing stylesheet to this widget.
        self.setStyleSheet(STYLE_SHEET)
        # Clear the authenticated account reference.
        self.current_user = None
        # Discard the staged transaction to prevent reuse.
        self.pending_transaction = None
        # Retain a storage failure for later display.
        self.storage_error = None
        # Handle failures from the following wallet operation.
        try:
            # Keep the loaded account records available to wallet operations.
            self.users = storage.load_users()
        # Handle failure while reading or saving the account records.
        except storage.StorageError as error:
            # Keep an empty account list after the load failure.
            self.users = []
            # Retain a storage failure for later display.
            self.storage_error = str(error)

        # Create the container that displays one screen at a time.
        self.stacked_widget = QStackedWidget()
        # Use the screen stack as the main window content.
        self.setCentralWidget(self.stacked_widget)

        # Import styles and screens
        # Create the login screen with application access.
        self.login_screen = LoginScreen(self)
        # Create the registration screen with application access.
        self.create_account_screen = CreateAccountScreen(self)
        # Create the balance and wallet-action screen.
        self.main_menu_screen = MainMenuScreen(self)
        # Create the money-transfer form.
        self.send_screen = SendMoneyScreen(self)
        # Create the bill-payment form.
        self.payment_screen = PaymentScreen(self)
        # Create the incoming-funds form.
        self.cash_in_screen = CashInScreen(self)
        # Create the withdrawal form.
        self.cash_out_screen = CashOutScreen(self)
        # Create the transaction review and PIN screen.
        self.confirm_screen = ConfirmTransactionScreen(self)
        # Create the completed-transaction receipt screen.
        self.receipt_screen = ReceiptScreen(self)
        # Collect screens for registration and session resets.
        self.screens = (
            self.login_screen, self.create_account_screen,
            self.main_menu_screen, self.send_screen, self.payment_screen,
            self.cash_in_screen, self.cash_out_screen,
            self.confirm_screen, self.receipt_screen,
        )
        # Visit each screen to register it or reset its state.
        for screen in self.screens:
            # Place the widget in its layout or screen stack.
            self.stacked_widget.addWidget(screen)
        # Display login with all session state cleared.
        self.go_to_login()

    # Stop operations when loading the saved users failed.
    def _check_storage(self):
        # Surface any error encountered while loading saved users.
        if self.storage_error:
            # Report why the requested wallet operation cannot proceed.
            raise storage.StorageError(self.storage_error)

    # Authenticate the entered credentials and open the menu.
    def authenticate(self, mobile, pin):
        # Require usable persistent storage before proceeding.
        self._check_storage()
        # Keep the account returned by credential verification.
        self.current_user = login(mobile, pin, self.users)
        # Erase the entered PIN digits.
        self.login_screen.pin_input.clear()
        # Refresh and display the signed-in account menu.
        self.go_to_main_menu()

    # Validate matching PINs and save the new account.
    def register_account(self, name, mobile, pin, confirm_pin):
        # Require usable persistent storage before proceeding.
        self._check_storage()
        # Reject registration when the two PIN entries differ.
        if pin != confirm_pin:
            # Report why the requested wallet operation cannot proceed.
            raise ValueError("PINs do not match.")
        # Save the new account and sign in as its owner.
        self.current_user = storage.register_and_save(name, mobile, pin, self.users)
        # Erase the entered PIN digits.
        self.create_account_screen.pin_input.clear()
        # Erase the entered PIN digits.
        self.create_account_screen.confirm_pin_input.clear()
        # Refresh and display the signed-in account menu.
        self.go_to_main_menu()

    # Clear session state and show the login screen.
    def go_to_login(self):
        # Clear the authenticated account reference.
        self.current_user = None
        # Discard the staged transaction to prevent reuse.
        self.pending_transaction = None
        # Visit each screen to register it or reset its state.
        for screen in self.screens:
            # Find an optional screen reset method.
            reset = getattr(screen, "reset", None)
            # Reset screens that provide their own cleanup method.
            if reset:
                # Clear this screen before ending the session.
                reset()
        # Discard the previous confirmation action.
        self.confirm_screen.kind = None
        # Discard the previous confirmation details.
        self.confirm_screen.details = None
        # Erase the entered PIN digits.
        self.confirm_screen.pin_input.clear()
        # Display the selected screen in the application stack.
        self.stacked_widget.setCurrentWidget(self.login_screen)
        # Surface any error encountered while loading saved users.
        if self.storage_error:
            # Show the account-storage problem on the login screen.
            self.login_screen.error_label.setText(self.storage_error)

    # Open the registration screen.
    def go_to_create_account(self):
        # Display the selected screen in the application stack.
        self.stacked_widget.setCurrentWidget(self.create_account_screen)

    # Refresh the signed-in balance and show the menu.
    def go_to_main_menu(self):
        # Require an authenticated account before continuing.
        if self.current_user is None:
            # Display login with all session state cleared.
            self.go_to_login()
            # Stop this request before performing the next action.
            return
        # Discard the staged transaction to prevent reuse.
        self.pending_transaction = None
        # Discard the previous confirmation action.
        self.confirm_screen.kind = None
        # Discard the previous confirmation details.
        self.confirm_screen.details = None
        # Erase the entered PIN digits.
        self.confirm_screen.pin_input.clear()
        # Refresh the balance shown on the main menu.
        self.main_menu_screen.refresh()
        # Display the selected screen in the application stack.
        self.stacked_widget.setCurrentWidget(self.main_menu_screen)

    # Reset and open a form for the signed-in user.
    def _show_form(self, screen):
        # Require an authenticated account before continuing.
        if self.current_user is None:
            # Display login with all session state cleared.
            self.go_to_login()
            # Stop this request before performing the next action.
            return
        # Discard the staged transaction to prevent reuse.
        self.pending_transaction = None
        # Clear previous screen state before continuing.
        screen.reset()
        # Display the selected screen in the application stack.
        self.stacked_widget.setCurrentWidget(screen)

    # Open the send-money form.
    def go_to_send(self):
        # Reset and display the money-transfer form.
        self._show_form(self.send_screen)

    # Open the bill-payment form.
    def go_to_payment(self):
        # Reset and display the bill-payment form.
        self._show_form(self.payment_screen)

    # Open the cash-in form.
    def go_to_cash_in(self):
        # Reset and display the incoming-funds form.
        self._show_form(self.cash_in_screen)

    # Open the cash-out form.
    def go_to_cash_out(self):
        # Reset and display the withdrawal form.
        self._show_form(self.cash_out_screen)

    # Stage the selected transaction for PIN confirmation.
    def go_to_confirm(self, kind, details, summary):
        # Require an authenticated account before continuing.
        if self.current_user is None:
            # Report why the requested wallet operation cannot proceed.
            raise AuthenticationError("Log in before making a transaction.")
        # Accept only the four supported transaction actions.
        if kind not in ("send", "payment", "cash_in", "cash_out"):
            # Report why the requested wallet operation cannot proceed.
            raise ValueError("Unknown transaction type.")
        # Track the transaction awaiting PIN verification.
        self.pending_transaction = (kind, details)
        # Populate the next screen with the selected transaction data.
        self.confirm_screen.load(kind, details, summary)
        # Display the selected screen in the application stack.
        self.stacked_widget.setCurrentWidget(self.confirm_screen)

    # Verify the staged transaction and call its storage action.
    def execute_transaction(self, kind, details, pin):
        # Require usable persistent storage before proceeding.
        self._check_storage()
        # Reject an absent session or an incorrect PIN.
        if self.current_user is None or not self.current_user.checkPin(pin):
            # Report why the requested wallet operation cannot proceed.
            raise AuthenticationError("Incorrect PIN. Try again.")
        # Read the transaction staged for confirmation.
        pending = self.pending_transaction
        # Require the exact details object staged for this action.
        if pending is None or pending[0] != kind or pending[1] is not details:
            # Report why the requested wallet operation cannot proceed.
            raise ValueError("No pending transaction. Start a new transaction.")
        # Map transaction kinds to their persistent storage operations.
        actions = {
            "send": storage.send_and_save,
            "payment": storage.pay_and_save,
            "cash_in": storage.deposit_and_save,
            "cash_out": storage.withdraw_and_save,
        }
        # Handle failures from the following wallet operation.
        try:
            # Run the selected transaction and retain its receipt.
            receipt = actions[kind](self.current_user, details, self.users)
        # Handle failure while reading or saving the account records.
        except storage.StorageError as error:
            # Prevent retrying a transaction that was already saved.
            if error.committed:
                # Discard the staged transaction to prevent reuse.
                self.pending_transaction = None
            # Propagate the storage failure to the calling screen.
            raise
        # Discard the staged transaction to prevent reuse.
        self.pending_transaction = None
        # Return the completed transaction receipt to the interface.
        return receipt

    # Load the completed transaction receipt and display it.
    def go_to_receipt(self, receipt):
        # Populate the next screen with the selected transaction data.
        self.receipt_screen.load(receipt)
        # Display the selected screen in the application stack.
        self.stacked_widget.setCurrentWidget(self.receipt_screen)


# Create the Qt application and run its event loop.
def launch():
    # Create the Qt application using command-line arguments.
    app = QApplication(sys.argv)
    # Create the wallet application window.
    window = EWalletApp()
    # Display the wallet window.
    window.show()
    # Run the Qt event loop and return its exit status.
    sys.exit(app.exec())


# Start the desktop interface when this module runs directly.
if __name__ == "__main__":
    # Launch the GUI when this application module is run directly.
    launch()
