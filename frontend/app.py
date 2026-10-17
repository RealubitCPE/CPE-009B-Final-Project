import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from backend import storage
from backend.user import AuthenticationError, login
from frontend.screens.cash_in import CashInScreen
from frontend.screens.cash_out import CashOutScreen
from frontend.screens.confirm_transaction import ConfirmTransactionScreen
from frontend.screens.create_account import CreateAccountScreen
from frontend.screens.login import LoginScreen
from frontend.screens.main_menu import MainMenuScreen
from frontend.screens.payment import PaymentScreen
from frontend.screens.receipt import ReceiptScreen
from frontend.screens.send_money import SendMoneyScreen
from frontend.style import STYLE_SHEET


class EWalletApp(QMainWindow):
    def __init__(self):
        """Load account state and create the wallet screen stack."""
        super().__init__()
        self.setWindowTitle("E-Wallet")
        self.setFixedSize(450, 750)
        self.setStyleSheet(STYLE_SHEET)
        self.current_user = None
        self.pending_transaction = None
        self.storage_error = None
        try:
            self.users = storage.load_users()
        except storage.StorageError as error:
            self.users = []
            self.storage_error = str(error)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_screen = LoginScreen(self)
        self.create_account_screen = CreateAccountScreen(self)
        self.main_menu_screen = MainMenuScreen(self)
        self.send_screen = SendMoneyScreen(self)
        self.payment_screen = PaymentScreen(self)
        self.cash_in_screen = CashInScreen(self)
        self.cash_out_screen = CashOutScreen(self)
        self.confirm_screen = ConfirmTransactionScreen(self)
        self.receipt_screen = ReceiptScreen(self)
        self.screens = (
            self.login_screen, self.create_account_screen,
            self.main_menu_screen, self.send_screen, self.payment_screen,
            self.cash_in_screen, self.cash_out_screen,
            self.confirm_screen, self.receipt_screen,
        )
        for screen in self.screens:
            self.stacked_widget.addWidget(screen)
        self.go_to_login()

    def _check_storage(self):
        """Raise the stored error if account loading failed."""
        if self.storage_error:
            raise storage.StorageError(self.storage_error)

    def authenticate(self, mobile, pin):
        """Authenticate the credentials and open the account menu."""
        self._check_storage()
        self.current_user = login(mobile, pin, self.users)
        self.login_screen.pin_input.clear()
        self.go_to_main_menu()

    def register_account(self, name, mobile, pin, confirm_pin):
        """Save an account with matching PINs and sign in its owner."""
        self._check_storage()
        if pin != confirm_pin:
            raise ValueError("PINs do not match.")
        self.current_user = storage.register_and_save(name, mobile, pin, self.users)
        self.create_account_screen.pin_input.clear()
        self.create_account_screen.confirm_pin_input.clear()
        self.go_to_main_menu()

    def go_to_login(self):
        """Clear session and screen state, then show login."""
        self.current_user = None
        self.pending_transaction = None
        for screen in self.screens:
            reset = getattr(screen, "reset", None)
            if reset:
                reset()
        self.confirm_screen.kind = None
        self.confirm_screen.details = None
        self.confirm_screen.pin_input.clear()
        self.stacked_widget.setCurrentWidget(self.login_screen)
        if self.storage_error:
            self.login_screen.error_label.setText(self.storage_error)

    def go_to_create_account(self):
        """Show the account registration screen."""
        self.stacked_widget.setCurrentWidget(self.create_account_screen)

    def go_to_main_menu(self):
        """Clear pending confirmation and refresh the signed-in menu."""
        if self.current_user is None:
            self.go_to_login()
            return
        self.pending_transaction = None
        self.confirm_screen.kind = None
        self.confirm_screen.details = None
        self.confirm_screen.pin_input.clear()
        self.main_menu_screen.refresh()
        self.stacked_widget.setCurrentWidget(self.main_menu_screen)

    def _show_form(self, screen):
        """Reset and display a transaction form for the signed-in user."""
        if self.current_user is None:
            self.go_to_login()
            return
        self.pending_transaction = None
        screen.reset()
        self.stacked_widget.setCurrentWidget(screen)

    def go_to_send(self):
        """Open a fresh money-transfer form."""
        self._show_form(self.send_screen)

    def go_to_payment(self):
        """Open a fresh bill-payment form."""
        self._show_form(self.payment_screen)

    def go_to_cash_in(self):
        """Open a fresh incoming-funds form."""
        self._show_form(self.cash_in_screen)

    def go_to_cash_out(self):
        """Open a fresh withdrawal form."""
        self._show_form(self.cash_out_screen)

    def go_to_confirm(self, kind, details, summary):
        """Stage validated transaction details for PIN confirmation."""
        if self.current_user is None:
            raise AuthenticationError("Log in before making a transaction.")
        if kind not in ("send", "payment", "cash_in", "cash_out"):
            raise ValueError("Unknown transaction type.")
        self.pending_transaction = (kind, details)
        self.confirm_screen.load(kind, details, summary)
        self.stacked_widget.setCurrentWidget(self.confirm_screen)

    def execute_transaction(self, kind, details, pin):
        """Verify the PIN and staged details, then save the transaction."""
        self._check_storage()
        if self.current_user is None or not self.current_user.checkPin(pin):
            raise AuthenticationError("Incorrect PIN. Try again.")
        pending = self.pending_transaction
        # Require the exact staged object so stale confirmations cannot be replayed.
        if pending is None or pending[0] != kind or pending[1] is not details:
            raise ValueError("No pending transaction. Start a new transaction.")
        actions = {
            "send": storage.send_and_save,
            "payment": storage.pay_and_save,
            "cash_in": storage.deposit_and_save,
            "cash_out": storage.withdraw_and_save,
        }
        try:
            receipt = actions[kind](self.current_user, details, self.users)
        except storage.StorageError as error:
            # An already saved transaction must not be retried.
            if error.committed:
                self.pending_transaction = None
            raise
        self.pending_transaction = None
        return receipt

    def go_to_receipt(self, receipt):
        """Load and display the completed transaction receipt."""
        self.receipt_screen.load(receipt)
        self.stacked_widget.setCurrentWidget(self.receipt_screen)


def launch():
    """Create the wallet window and exit with the Qt event-loop status."""
    app = QApplication(sys.argv)
    window = EWalletApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
