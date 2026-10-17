"""Offscreen wallet flow regressions; every storage path is temporary."""

# Set the Qt platform before importing its widgets.
import os
# Use Decimal to compare money without floating-point rounding.
from decimal import Decimal
# Build paths and inspect temporary test files.
from pathlib import Path
# Keep test wallet files in disposable temporary directories.
from tempfile import TemporaryDirectory
# Use the standard test runner and assertion helpers.
import unittest
# Temporarily replace dependencies and inspect recorded calls.
from unittest.mock import patch

# Run Qt without requiring a visible desktop display.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Control Qt event processing and plain-text rendering checks.
from PyQt6.QtCore import QCoreApplication, QEvent, Qt
# Load available system fonts for offscreen UI tests.
from PyQt6.QtGui import QFontDatabase
# Create the Qt application and inspect receipt labels.
from PyQt6.QtWidgets import QApplication, QLabel

# Exercise wallet persistence through the storage module.
from backend import storage
# Use the transaction detail types and confirmation helpers under test.
from backend.transactions import PAYMENT_STRUCTURE, account_details, deposit_details, payment_details, withdraw_details
# Keep the public launcher import covered by the UI tests.
from main import EWalletApp
# Compare the relocated implementation with the public launcher export.
from frontend.app import EWalletApp as FrontendEWalletApp
# Check the compatibility name for the confirmation screen.
from frontend.screens.confirm import ConfirmScreen
# Compare the canonical confirmation screen class.
from frontend.screens.confirm_transaction import ConfirmTransactionScreen
# Check that menu routes open transaction form screens.
from frontend.screens.transaction_form import TransactionFormScreen


# Group the offscreen UI regression checks in a unittest test case.
class WalletUITests(unittest.TestCase):
    # Prepare shared resources once before this test class runs.
    @classmethod
    def setUpClass(cls):
        # Reuse the Qt application or create it once for the suite.
        cls.qt_app = QApplication.instance() or QApplication([])
        # Exercise each font in this case set.
        for font in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
            # Only load fonts that exist on this computer.
            if Path(font).is_file():
                # Load an available font for offscreen rendering.
                QFontDatabase.addApplicationFont(font)

    # Create fresh accounts, storage paths, or widgets for each test.
    def setUp(self):
        # Create temporary storage for this UI test.
        temporary = TemporaryDirectory()
        # Register cleanup even if the test fails.
        self.addCleanup(temporary.cleanup)
        # Keep the temporary directory path for file checks.
        self.data_dir = Path(temporary.name)
        # Exercise each name and filename in this case set.
        for name, filename in (("USERS_FILE", "users.json"), ("TRANSACTIONS_FILE", "transactions.json")):
            # Redirect this storage file into the temporary directory.
            storage_patch = patch.object(storage, name, str(self.data_dir / filename))
            # Activate the temporary override.
            storage_patch.start()
            # Register cleanup even if the test fails.
            self.addCleanup(storage_patch.stop)
        # Create the wallet window using temporary storage.
        self.window = EWalletApp()
        # Show the window so Qt can lay out its widgets.
        self.window.show()
        # Finish pending Qt layout and deletion work.
        self.flush_events()

    # Release this test window after each test.
    def tearDown(self):
        # Close the test window.
        self.window.close()
        # Schedule the Qt object for deletion.
        self.window.deleteLater()
        # Finish pending Qt layout and deletion work.
        self.flush_events()

    # Let Qt complete deferred deletion and repeated layout passes.
    def flush_events(self):
        # Scroll areas need a second layout pass after their content width changes.
        # Repeat the operation the required number of times.
        for _ in range(3):
            # Deliver deferred deletions before processing more events.
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            # Process pending Qt events and layout updates.
            self.qt_app.processEvents()

    # Enter a PIN through its individual digit fields.
    @staticmethod
    def enter_pin(widget, value="1234"):
        # Clear the widget before entering test digits.
        widget.clear()
        # Exercise each field and digit in this case set.
        for field, digit in zip(widget.inputs, value):
            # Fill the field with the test input.
            field.setText(digit)

    # Register the standard account through the UI.
    def register(self):
        # Simulate clicking the create button.
        self.window.login_screen.create_btn.click()
        # Keep a reference to the screen used by this scenario.
        screen = self.window.create_account_screen
        # Fill the field with the test input.
        screen.name_input.setText("Alice Example")
        # Fill the field with the test input.
        screen.mobile_input.setText("09170000001")
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(screen.pin_input)
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(screen.confirm_pin_input)
        # Simulate clicking the create button.
        screen.create_btn.click()
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.main_menu_screen)

    # Populate the form fields and submit the amount.
    def fill_form(self, screen, values, amount="100.00"):
        # Exercise each key and value in this case set.
        for key, value in values.items():
            # Fill the field with the test input.
            screen.inputs[key].setText(value)
        # Fill the field with the test input.
        screen.amount_input.setText(amount)
        # Simulate clicking the action button.
        screen.action_btn.click()

    # Submit the confirmation PIN through the UI.
    def verify(self, pin="1234"):
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(self.window.confirm_screen.pin_input, pin)
        # Simulate clicking the verify button.
        self.window.confirm_screen.verify_btn.click()

    # Exercise a complete deposit and return to the menu.
    def deposit(self, amount="250.00"):
        # Open the cash in screen.
        self.window.go_to_cash_in()
        # Fill and submit the transaction form.
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"}, amount)
        # Submit the test PIN through the confirmation screen.
        self.verify()
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.receipt_screen)
        # Simulate clicking the done button.
        self.window.receipt_screen.done_btn.click()

    # Keep the public launcher compatible with the relocated application.
    def test_launcher_exports_canonical_frontend_application(self):
        # Both import paths must expose one class rather than separate implementations.
        self.assertIs(EWalletApp, FrontendEWalletApp)

    # Verify that login requires actual credentials and clears pin.
    def test_login_requires_actual_credentials_and_clears_pin(self):
        # Create and sign in the standard test account.
        self.register()
        # Simulate clicking the logout button.
        self.window.main_menu_screen.logout_btn.click()
        # Keep a reference to the screen used by this scenario.
        screen = self.window.login_screen
        # Fill the field with the test input.
        screen.mobile_input.setText("09170000001")
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(screen.pin_input, "9999")
        # Simulate clicking the login button.
        screen.login_btn.click()
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), screen)
        # Check that the signed-in user is cleared.
        self.assertIsNone(self.window.current_user)
        # Check that validation displays an error message.
        self.assertTrue(screen.error_label.text())
        # Check that the entered PIN matches ''.
        self.assertEqual(screen.pin_input.get_pin(), "")
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(screen.pin_input)
        # Simulate clicking the login button.
        screen.login_btn.click()
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.main_menu_screen)
        # Check that the entered PIN matches ''.
        self.assertEqual(screen.pin_input.get_pin(), "")

    # Verify that registration rejects mismatched pins without navigation.
    def test_registration_rejects_mismatched_pins_without_navigation(self):
        # Open the create account screen.
        self.window.go_to_create_account()
        # Keep a reference to the screen used by this scenario.
        screen = self.window.create_account_screen
        # Fill the field with the test input.
        screen.name_input.setText("Alice Example")
        # Fill the field with the test input.
        screen.mobile_input.setText("09170000001")
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(screen.pin_input)
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(screen.confirm_pin_input, "5678")
        # Simulate clicking the create button.
        screen.create_btn.click()
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), screen)
        # Check that the expected item or message fragment is present.
        self.assertIn("match", screen.error_label.text())
        # Check that the entered PIN matches ''.
        self.assertEqual(screen.pin_input.get_pin(), "")
        # Check that the repeated PIN matches ''.
        self.assertEqual(screen.confirm_pin_input.get_pin(), "")
        # Check that this file was not created or was removed.
        self.assertFalse((self.data_dir / "users.json").exists())
        # Simulate clicking the back button.
        screen.back_btn.click()
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.login_screen)

    # Verify that authentication and registration storage errors are inline.
    def test_authentication_and_registration_storage_errors_are_inline(self):
        # Define the inputs and expected targets for each case.
        cases = (
            (self.window.login_screen, "authenticate", "login_btn"),
            (self.window.create_account_screen, "register_account", "create_btn"),
        )
        # Exercise each screen and method and button in this case set.
        for screen, method, button in cases:
            # Report failures separately for this combination of inputs.
            with self.subTest(method=method):
                # Display the screen under test.
                self.window.stacked_widget.setCurrentWidget(screen)
                # Replace this dependency temporarily to control the test scenario.
                with patch.object(self.window, method, side_effect=storage.StorageError("<b>Disk full</b>")):
                    # Simulate clicking the getattr(screen, button) button.
                    getattr(screen, button).click()
                # Check that the active screen is the expected object.
                self.assertIs(self.window.stacked_widget.currentWidget(), screen)
                # Check that the displayed error matches '<b>Disk full</b>'.
                self.assertEqual(screen.error_label.text(), "<b>Disk full</b>")
                # Check that the error rendering format matches plain text.
                self.assertEqual(screen.error_label.textFormat(), Qt.TextFormat.PlainText)
                # Check that the button state is true.
                self.assertTrue(getattr(screen, button).isEnabled())

    # Verify that all menu buttons route once and cancel.
    def test_all_menu_buttons_route_once_and_cancel(self):
        # Create and sign in the standard test account.
        self.register()
        # Keep a reference to the main menu.
        menu = self.window.main_menu_screen
        # Exercise each button and target in this case set.
        for button, target in (
            (menu.send_btn, self.window.send_screen),
            (menu.pay_btn, self.window.payment_screen),
            (menu.cashin_btn, self.window.cash_in_screen),
            (menu.cashout_btn, self.window.cash_out_screen),
        ):
            # Report failures separately for this combination of inputs.
            with self.subTest(target=target.kind):
                # Replace this dependency temporarily to control the test scenario.
                with patch.object(self.window, "_show_form", wraps=self.window._show_form) as show:
                    # Simulate clicking the button button.
                    button.click()
                # Check that the callback ran once with the expected argument.
                show.assert_called_once_with(target)
                # Check that target has the expected type.
                self.assertIsInstance(target, TransactionFormScreen)
                # Check that the active screen is the expected object.
                self.assertIs(self.window.stacked_widget.currentWidget(), target)
                # Simulate clicking the cancel button.
                target.cancel_btn.click()
                # Check that the active screen is the expected object.
                self.assertIs(self.window.stacked_widget.currentWidget(), menu)

    # Verify that all transaction flows persist and refresh actual balance.
    def test_all_transaction_flows_persist_and_refresh_actual_balance(self):
        # Create and sign in the standard test account.
        self.register()
        # Register the test account and persist it.
        storage.register_and_save("Bob Example", "09170000002", "5678", self.window.users)
        # Deposit the test amount into the user balance.
        self.deposit()
        # Check that the displayed balance matches 'PHP 250.00'.
        self.assertEqual(self.window.main_menu_screen.balance_label.text(), "PHP 250.00")
        # Define the inputs and expected targets for each case.
        cases = (
            (self.window.go_to_cash_out, self.window.cash_out_screen,
             {"destination": "Bank", "number": "123456789"}, "30.00", withdraw_details),
            (self.window.go_to_payment, self.window.payment_screen,
             {"biller": "Utility", "reference": "ABC-123"}, "20.00", payment_details),
            (self.window.go_to_send, self.window.send_screen,
             {"number": "09170000002", "name": "Bob Example"}, "50.00", account_details),
        )
        # Exercise each navigate and screen and values and amount and detail type in this case set.
        for navigate, screen, values, amount, detail_type in cases:
            # Report failures separately for this combination of inputs.
            with self.subTest(kind=screen.kind):
                # Open the transaction form for this case.
                navigate()
                # Fill and submit the transaction form.
                self.fill_form(screen, values, amount)
                # Check that the active screen is the expected object.
                self.assertIs(self.window.stacked_widget.currentWidget(), self.window.confirm_screen)
                # Check that the confirmation details has the expected type.
                self.assertIsInstance(self.window.confirm_screen.details, detail_type)
                # Check that amount has the expected type.
                self.assertIsInstance(self.window.confirm_screen.details.amount, Decimal)
                # Submit the test PIN through the confirmation screen.
                self.verify()
                # Check that the active screen is the expected object.
                self.assertIs(self.window.stacked_widget.currentWidget(), self.window.receipt_screen)
                # Simulate clicking the done button.
                self.window.receipt_screen.done_btn.click()
        # Check that the displayed balance matches 'PHP 150.00'.
        self.assertEqual(self.window.main_menu_screen.balance_label.text(), "PHP 150.00")
        # Reload users to check the values actually saved to disk.
        users = storage.load_users()
        # Check that balance matches the exact decimal value.
        self.assertEqual(users[0].balance, Decimal("150.00"))
        # Check that balance matches the exact decimal value.
        self.assertEqual(users[1].balance, Decimal("50.00"))
        # Check that the saved transaction count matches 5.
        self.assertEqual(len(storage.load_transactions()), 5)

    # Verify that payment categories and subcategories reset together.
    def test_payment_categories_and_subcategories_reset_together(self):
        # Keep a reference to the screen used by this scenario.
        screen = self.window.payment_screen
        # Exercise each category and subcategories in this case set.
        for category, subcategories in PAYMENT_STRUCTURE.items():
            # Select this payment category in the combo box.
            screen.category_combo.setCurrentText(category)
            # Check that the combo box lists this category's subcategories.
            self.assertEqual(
                [screen.subcategory_combo.itemText(i) for i in range(screen.subcategory_combo.count())],
                subcategories,
            )
        # Reset the form to its initial selection.
        screen.reset()
        # Read the category selected after resetting the form.
        category = screen.category_combo.currentText()
        # Check that reset selects the first subcategory for the current category.
        self.assertEqual(screen.subcategory_combo.currentText(), PAYMENT_STRUCTURE[category][0])

    # Verify that amount text preserves precision and rejects bad grouping.
    def test_amount_text_preserves_precision_and_rejects_bad_grouping(self):
        # Create and sign in the standard test account.
        self.register()
        # Open the cash in screen.
        self.window.go_to_cash_in()
        # Keep a reference to the screen used by this scenario.
        screen = self.window.cash_in_screen
        # Fill the field with the test input.
        screen.inputs["source"].setText("Bank")
        # Exercise each invalid in this case set.
        for invalid in ("", "0", "-1", "nan", "inf", "1.001", "1.00000000000000001", "1,,2", "1,23"):
            # Report failures separately for this combination of inputs.
            with self.subTest(amount=invalid):
                # Fill the field with the test input.
                screen.amount_input.setText(invalid)
                # Simulate clicking the action button.
                screen.action_btn.click()
                # Check that the active screen is the expected object.
                self.assertIs(self.window.stacked_widget.currentWidget(), screen)
                # Check that the pending transaction is cleared.
                self.assertIsNone(self.window.pending_transaction)
                # Check that validation displays an error message.
                self.assertTrue(screen.error_label.text())
        # Fill the field with the test input.
        screen.amount_input.setText("1,200.00")
        # Simulate clicking the action button.
        screen.action_btn.click()
        # Check that the confirmation details has the expected type.
        self.assertIsInstance(self.window.confirm_screen.details, deposit_details)
        # Check that amount matches the exact decimal value.
        self.assertEqual(self.window.confirm_screen.details.amount, Decimal("1200.00"))

    # Verify that empty forms do not open confirmation.
    def test_empty_forms_do_not_open_confirmation(self):
        # Create and sign in the standard test account.
        self.register()
        # Exercise each navigate and screen in this case set.
        for navigate, screen in (
            (self.window.go_to_send, self.window.send_screen),
            (self.window.go_to_payment, self.window.payment_screen),
            (self.window.go_to_cash_in, self.window.cash_in_screen),
            (self.window.go_to_cash_out, self.window.cash_out_screen),
        ):
            # Open the transaction form for this case.
            navigate()
            # Fill the field with the test input.
            screen.amount_input.setText("10.00")
            # Simulate clicking the action button.
            screen.action_btn.click()
            # Check that the active screen is the expected object.
            self.assertIs(self.window.stacked_widget.currentWidget(), screen)
            # Check that validation displays an error message.
            self.assertTrue(screen.error_label.text())
            # Check that the pending transaction is cleared.
            self.assertIsNone(self.window.pending_transaction)

    # Verify that wrong pin and storage error leave confirmation retryable.
    def test_wrong_pin_and_storage_error_leave_confirmation_retryable(self):
        # Create and sign in the standard test account.
        self.register()
        # Open the cash in screen.
        self.window.go_to_cash_in()
        # Fill and submit the transaction form.
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"})
        # Keep a reference to the screen used by this scenario.
        screen = self.window.confirm_screen
        # Keep the original pending transaction for identity checks.
        pending = self.window.pending_transaction
        # Submit the test PIN through the confirmation screen.
        self.verify("9999")
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), screen)
        # Check that the pending transaction is the expected object.
        self.assertIs(self.window.pending_transaction, pending)
        # Check that the entered PIN matches ''.
        self.assertEqual(screen.pin_input.get_pin(), "")
        # Check that the Verify button state is true.
        self.assertTrue(screen.verify_btn.isEnabled())
        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage, "deposit_and_save", side_effect=storage.StorageError("Disk full")):
            # Submit the test PIN through the confirmation screen.
            self.verify()
        # Check that the displayed error matches 'Disk full'.
        self.assertEqual(screen.error_label.text(), "Disk full")
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), screen)
        # Check that the pending transaction is the expected object.
        self.assertIs(self.window.pending_transaction, pending)
        # Check that the signed-in user's balance matches 0.
        self.assertEqual(self.window.current_user.balance, 0)
        # Submit the test PIN through the confirmation screen.
        self.verify()
        # Check that the active screen is the expected object.
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.receipt_screen)
        # Check that the signed-in user's balance matches 100.
        self.assertEqual(self.window.current_user.balance, 100)

    # Verify that verification cannot execute twice or reenter.
    def test_verification_cannot_execute_twice_or_reenter(self):
        # Create and sign in the standard test account.
        self.register()
        # Open the cash in screen.
        self.window.go_to_cash_in()
        # Fill and submit the transaction form.
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"})
        # Keep a reference to the screen used by this scenario.
        screen = self.window.confirm_screen
        # Keep the real transaction executor for the reentry mock.
        execute = self.window.execute_transaction

        # Try to confirm again while the first confirmation is executing.
        def reenter(kind, details, pin):
            # Check that the Verify button state is false.
            self.assertFalse(screen.verify_btn.isEnabled())
            # Check that the Cancel button state is false.
            self.assertFalse(screen.cancel_btn.isEnabled())
            # Attempt confirmation through its handler directly.
            screen.on_verify()
            # Finish the original transaction after the reentry attempt.
            return execute(kind, details, pin)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(self.window, "execute_transaction", side_effect=reenter) as mocked:
            # Submit the test PIN through the confirmation screen.
            self.verify()
            # Attempt confirmation through its handler directly.
            screen.on_verify()
            # Check that the mocked operation ran exactly once.
            mocked.assert_called_once()
        # Check that the pending transaction type is cleared.
        self.assertIsNone(screen.kind)
        # Check that the pending details are cleared.
        self.assertIsNone(screen.details)
        # Check that the pending transaction is cleared.
        self.assertIsNone(self.window.pending_transaction)
        # Check that the entered PIN matches ''.
        self.assertEqual(screen.pin_input.get_pin(), "")
        # Check that the Verify button state is false.
        self.assertFalse(screen.verify_btn.isEnabled())
        # Check that the saved transaction count matches 1.
        self.assertEqual(len(storage.load_transactions()), 1)

    # Verify that committed storage error clears confirmation and prevents retry.
    def test_committed_storage_error_clears_confirmation_and_prevents_retry(self):
        # Create and sign in the standard test account.
        self.register()
        # Open the cash in screen.
        self.window.go_to_cash_in()
        # Fill and submit the transaction form.
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"})
        # Keep a reference to the screen used by this scenario.
        screen = self.window.confirm_screen
        # Keep the deposit result or callable for later checks.
        deposit = storage.deposit_and_save

        # Commit the deposit and then report a committed storage failure.
        def commit_then_report_cleanup_failure(*args):
            # Commit the deposit before simulating the cleanup error.
            deposit(*args)
            # Simulate the storage failure expected by this test.
            raise storage.StorageError("Saved; marker cleanup failed. Reconcile before continuing.", committed=True)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage, "deposit_and_save", side_effect=commit_then_report_cleanup_failure) as action:
            # Submit the test PIN through the confirmation screen.
            self.verify()
            # Check that the active screen is the expected object.
            self.assertIs(self.window.stacked_widget.currentWidget(), screen)
            # Check that the expected item or message fragment is present.
            self.assertIn("marker cleanup failed", screen.error_label.text())
            # Check that the entered PIN matches ''.
            self.assertEqual(screen.pin_input.get_pin(), "")
            # Check that the pending transaction type is cleared.
            self.assertIsNone(screen.kind)
            # Check that the pending details are cleared.
            self.assertIsNone(screen.details)
            # Check that the pending transaction is cleared.
            self.assertIsNone(self.window.pending_transaction)
            # Check that the Verify button state is false.
            self.assertFalse(screen.verify_btn.isEnabled())
            # Check that the signed-in user's balance matches the exact decimal value.
            self.assertEqual(self.window.current_user.balance, Decimal("100.00"))
            # Check that balance matches the exact decimal value.
            self.assertEqual(storage.load_users()[0].balance, Decimal("100.00"))
            # Check that the saved transaction count matches 1.
            self.assertEqual(len(storage.load_transactions()), 1)
            # Reconciliation permits further actions, but this confirmation stays consumed.
            # Fill the individual PIN boxes with test digits.
            self.enter_pin(screen.pin_input)
            # Attempt confirmation through its handler directly.
            screen.on_verify()
            # Simulate clicking the verify button.
            screen.verify_btn.click()
            # Check that the mocked operation ran exactly once.
            action.assert_called_once()
        # Check that the saved transaction count matches 1.
        self.assertEqual(len(storage.load_transactions()), 1)

    # Verify that cancel confirmation discards pending details.
    def test_cancel_confirmation_discards_pending_details(self):
        # Create and sign in the standard test account.
        self.register()
        # Open the cash in screen.
        self.window.go_to_cash_in()
        # Fill and submit the transaction form.
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"})
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(self.window.confirm_screen.pin_input)
        # Simulate clicking the cancel button.
        self.window.confirm_screen.cancel_btn.click()
        # Check that the pending transaction is cleared.
        self.assertIsNone(self.window.pending_transaction)
        # Check that the confirmation details are cleared.
        self.assertIsNone(self.window.confirm_screen.details)
        # Check that the entered PIN matches ''.
        self.assertEqual(self.window.confirm_screen.pin_input.get_pin(), "")
        # Attempt confirmation through its handler directly.
        self.window.confirm_screen.on_verify()
        # Check that the saved transaction history matches an empty list.
        self.assertEqual(storage.load_transactions(), [])

    # Verify that logout resets sensitive fields and receipt.
    def test_logout_resets_sensitive_fields_and_receipt(self):
        # Create and sign in the standard test account.
        self.register()
        # Deposit the test amount into the user balance.
        self.deposit()
        # Open the send screen.
        self.window.go_to_send()
        # Fill and submit the transaction form.
        self.fill_form(self.window.send_screen, {"number": "09170000002", "name": "Bob"})
        # Fill the individual PIN boxes with test digits.
        self.enter_pin(self.window.confirm_screen.pin_input)
        # Open the login screen.
        self.window.go_to_login()
        # Check that the signed-in user is cleared.
        self.assertIsNone(self.window.current_user)
        # Check that the pending transaction is cleared.
        self.assertIsNone(self.window.pending_transaction)
        # Check that the displayed text matches ''.
        self.assertEqual(self.window.login_screen.mobile_input.text(), "")
        # Check that the displayed text matches ''.
        self.assertEqual(self.window.create_account_screen.name_input.text(), "")
        # Check that the confirmation details are cleared.
        self.assertIsNone(self.window.confirm_screen.details)
        # Check that the confirmation row count matches 0.
        self.assertEqual(self.window.confirm_screen.card_layout.count(), 0)
        # Check that the receipt row count matches 0.
        self.assertEqual(self.window.receipt_screen.card_layout.count(), 0)
        # Exercise each screen in this case set.
        for screen in (self.window.send_screen, self.window.payment_screen,
                       self.window.cash_in_screen, self.window.cash_out_screen):
            # Check that the displayed text matches ''.
            self.assertEqual(screen.amount_input.text(), "")

    # Verify that startup storage error is plain text on login.
    def test_startup_storage_error_is_plain_text_on_login(self):
        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage, "load_users", side_effect=storage.StorageError("<b>Corrupt file</b>")):
            # Create a second instance for this comparison or startup check.
            other = EWalletApp()
        # Check the extra startup window while ensuring it is closed afterward.
        try:
            # Check that the displayed text matches '<b>Corrupt file</b>'.
            self.assertEqual(other.login_screen.error_label.text(), "<b>Corrupt file</b>")
            # Check that the label rendering format matches plain text.
            self.assertEqual(other.login_screen.error_label.textFormat(), Qt.TextFormat.PlainText)
            # Simulate clicking the login button.
            other.login_screen.login_btn.click()
            # Check that the active screen is the expected object.
            self.assertIs(other.stacked_widget.currentWidget(), other.login_screen)
        finally:
            # Close the test window.
            other.close()
            # Schedule the Qt object for deletion.
            other.deleteLater()

    # Verify that confirmation alias and literal summary.
    def test_confirmation_alias_and_literal_summary(self):
        # Check that confirm screen is the expected object.
        self.assertIs(ConfirmScreen, ConfirmTransactionScreen)
        # Create and sign in the standard test account.
        self.register()
        # Open the cash in screen.
        self.window.go_to_cash_in()
        # Fill and submit the transaction form.
        self.fill_form(self.window.cash_in_screen, {"source": "<b>Bank</b>"})
        # Exercise each label in this case set.
        for label in self.window.confirm_screen.card.findChildren(QLabel):
            # Check that the label rendering format matches plain text.
            self.assertEqual(label.textFormat(), Qt.TextFormat.PlainText)
            # Check that the summary label allows word wrapping.
            self.assertTrue(label.wordWrap())
        # Check that the expected item or message fragment is present.
        self.assertIn("<b>Bank</b>", self.window.confirm_screen.card_layout.itemAt(0).widget().text())

    # Verify that receipt long unbroken references wrap and scroll.
    def test_receipt_long_unbroken_references_wrap_and_scroll(self):
        # Prepare the receipt data or capture the confirmed receipt.
        receipt = {
            "Name": "Alexandra " * 8, "Amount": 1250.50,
            "Account Details": "Reference: " + "1234567890" * 12,
            "Transaction Number": "DEP-000000001", "Date": "2026-10-18", "Time": "12:00:00",
        }
        # Display the supplied receipt.
        self.window.go_to_receipt(receipt)
        # Finish pending Qt layout and deletion work.
        self.flush_events()
        # Keep a reference to the screen used by this scenario.
        screen = self.window.receipt_screen
        # Find the receipt row containing the reference.
        row = screen.card_layout.itemAt(4).widget().layout()
        # Locate the reference label for wrapping checks.
        reference = row.itemAt(1).widget()
        # Check that assistive technology receives the complete reference.
        self.assertEqual(reference.accessibleName(), receipt["Account Details"])
        # Check that wrapping hints preserve the original reference text.
        self.assertEqual(reference.text().replace("\u200b", ""), receipt["Account Details"])
        # Check that the long reference needs more than one text line.
        self.assertGreater(reference.heightForWidth(reference.width()), 32)
        # Check that the actual height meets the required minimum.
        self.assertGreaterEqual(reference.height(), reference.heightForWidth(reference.width()))
        # Make the receipt reference much longer to force vertical scrolling.
        receipt["Account Details"] = "Reference: " + "1234567890" * 400
        # Display the supplied receipt.
        self.window.go_to_receipt(receipt)
        # Finish pending Qt layout and deletion work.
        self.flush_events()
        # Check that very long content can be scrolled vertically.
        self.assertGreater(screen.receipt_scroll.verticalScrollBar().maximum(), 0)
        # Check that the scrollbar range matches 0.
        self.assertEqual(screen.receipt_scroll.horizontalScrollBar().maximum(), 0)
        # Locate the reference label for wrapping checks.
        reference = screen.card_layout.itemAt(4).widget().layout().itemAt(1).widget()
        # Check that the actual height meets the required minimum.
        self.assertGreaterEqual(reference.height(), reference.heightForWidth(reference.width()))
        # Check that the wallet window keeps its 450-pixel width.
        self.assertEqual(self.window.size().width(), 450)
        # Check that the wallet window keeps its 750-pixel height.
        self.assertEqual(self.window.size().height(), 750)
        # Exercise each label in this case set.
        for label in screen.card.findChildren(QLabel):
            # Check that the label rendering format matches plain text.
            self.assertEqual(label.textFormat(), Qt.TextFormat.PlainText)


# Run the tests when this file is executed directly.
if __name__ == "__main__":
    # Run the test suite or CLI entry point.
    unittest.main()
