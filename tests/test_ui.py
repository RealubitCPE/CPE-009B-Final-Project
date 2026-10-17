"""Offscreen wallet flow regressions; every storage path is temporary."""

import os
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtCore import QCoreApplication, QEvent, Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication, QLabel

from backend import storage
from backend.transactions import PAYMENT_STRUCTURE, account_details, deposit_details, payment_details, withdraw_details
from main import EWalletApp
from frontend.app import EWalletApp as FrontendEWalletApp
from frontend.screens.confirm import ConfirmScreen
from frontend.screens.confirm_transaction import ConfirmTransactionScreen
from frontend.screens.transaction_form import TransactionFormScreen


class WalletUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create one offscreen Qt application and load available fonts."""
        cls.qt_app = QApplication.instance() or QApplication([])
        for font in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
            if Path(font).is_file():
                QFontDatabase.addApplicationFont(font)

    def setUp(self):
        """Build a fresh window with storage redirected to a temporary directory."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.data_dir = Path(temporary.name)
        for name, filename in (("USERS_FILE", "users.json"), ("TRANSACTIONS_FILE", "transactions.json")):
            storage_patch = patch.object(storage, name, str(self.data_dir / filename))
            storage_patch.start()
            self.addCleanup(storage_patch.stop)
        self.window = EWalletApp()
        self.window.show()
        self.flush_events()

    def tearDown(self):
        """Close the window and process its deferred Qt cleanup."""
        self.window.close()
        self.window.deleteLater()
        self.flush_events()

    def flush_events(self):
        """Process deferred deletions and repeated Qt layout passes."""
        # Scroll areas need a second layout pass after their content width changes.
        for _ in range(3):
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.qt_app.processEvents()

    @staticmethod
    def enter_pin(widget, value="1234"):
        """Fill the individual PIN input fields."""
        widget.clear()
        for field, digit in zip(widget.inputs, value):
            field.setText(digit)

    def register(self):
        """Register and sign in the standard test account through the UI."""
        self.window.login_screen.create_btn.click()
        screen = self.window.create_account_screen
        screen.name_input.setText("Alice Example")
        screen.mobile_input.setText("09170000001")
        self.enter_pin(screen.pin_input)
        self.enter_pin(screen.confirm_pin_input)
        screen.create_btn.click()
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.main_menu_screen)

    def fill_form(self, screen, values, amount="100.00"):
        """Fill transaction fields and submit the requested amount."""
        for key, value in values.items():
            screen.inputs[key].setText(value)
        screen.amount_input.setText(amount)
        screen.action_btn.click()

    def verify(self, pin="1234"):
        """Submit the confirmation PIN through the UI."""
        self.enter_pin(self.window.confirm_screen.pin_input, pin)
        self.window.confirm_screen.verify_btn.click()

    def deposit(self, amount="250.00"):
        """Complete a deposit through the UI and return to the menu."""
        self.window.go_to_cash_in()
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"}, amount)
        self.verify()
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.receipt_screen)
        self.window.receipt_screen.done_btn.click()

    def test_launcher_exports_canonical_frontend_application(self):
        """Keep the public launcher tied to the canonical frontend class."""
        self.assertIs(EWalletApp, FrontendEWalletApp)

    def test_login_requires_actual_credentials_and_clears_pin(self):
        """Reject wrong credentials and clear PIN fields after each login attempt."""
        self.register()
        self.window.main_menu_screen.logout_btn.click()
        screen = self.window.login_screen
        screen.mobile_input.setText("09170000001")
        self.enter_pin(screen.pin_input, "9999")
        screen.login_btn.click()
        self.assertIs(self.window.stacked_widget.currentWidget(), screen)
        self.assertIsNone(self.window.current_user)
        self.assertTrue(screen.error_label.text())
        self.assertEqual(screen.pin_input.get_pin(), "")
        self.enter_pin(screen.pin_input)
        screen.login_btn.click()
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.main_menu_screen)
        self.assertEqual(screen.pin_input.get_pin(), "")

    def test_registration_rejects_mismatched_pins_without_navigation(self):
        """Keep invalid registration on its form and clear both PIN fields."""
        self.window.go_to_create_account()
        screen = self.window.create_account_screen
        screen.name_input.setText("Alice Example")
        screen.mobile_input.setText("09170000001")
        self.enter_pin(screen.pin_input)
        self.enter_pin(screen.confirm_pin_input, "5678")
        screen.create_btn.click()
        self.assertIs(self.window.stacked_widget.currentWidget(), screen)
        self.assertIn("match", screen.error_label.text())
        self.assertEqual(screen.pin_input.get_pin(), "")
        self.assertEqual(screen.confirm_pin_input.get_pin(), "")
        self.assertFalse((self.data_dir / "users.json").exists())
        screen.back_btn.click()
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.login_screen)

    def test_authentication_and_registration_storage_errors_are_inline(self):
        """Show storage errors as plain text on the originating account form."""
        cases = (
            (self.window.login_screen, "authenticate", "login_btn"),
            (self.window.create_account_screen, "register_account", "create_btn"),
        )
        for screen, method, button in cases:
            with self.subTest(method=method):
                self.window.stacked_widget.setCurrentWidget(screen)
                with patch.object(self.window, method, side_effect=storage.StorageError("<b>Disk full</b>")):
                    getattr(screen, button).click()
                self.assertIs(self.window.stacked_widget.currentWidget(), screen)
                self.assertEqual(screen.error_label.text(), "<b>Disk full</b>")
                self.assertEqual(screen.error_label.textFormat(), Qt.TextFormat.PlainText)
                self.assertTrue(getattr(screen, button).isEnabled())

    def test_all_menu_buttons_route_once_and_cancel(self):
        """Open each transaction form once and allow cancellation to the menu."""
        self.register()
        menu = self.window.main_menu_screen
        for button, target in (
            (menu.send_btn, self.window.send_screen),
            (menu.pay_btn, self.window.payment_screen),
            (menu.cashin_btn, self.window.cash_in_screen),
            (menu.cashout_btn, self.window.cash_out_screen),
        ):
            with self.subTest(target=target.kind):
                with patch.object(self.window, "_show_form", wraps=self.window._show_form) as show:
                    button.click()
                show.assert_called_once_with(target)
                self.assertIsInstance(target, TransactionFormScreen)
                self.assertIs(self.window.stacked_widget.currentWidget(), target)
                target.cancel_btn.click()
                self.assertIs(self.window.stacked_widget.currentWidget(), menu)

    def test_all_transaction_flows_persist_and_refresh_actual_balance(self):
        """Persist each UI transaction and refresh the displayed balance."""
        self.register()
        storage.register_and_save("Bob Example", "09170000002", "5678", self.window.users)
        self.deposit()
        self.assertEqual(self.window.main_menu_screen.balance_label.text(), "PHP 250.00")
        cases = (
            (self.window.go_to_cash_out, self.window.cash_out_screen,
             {"destination": "Bank", "number": "123456789"}, "30.00", withdraw_details),
            (self.window.go_to_payment, self.window.payment_screen,
             {"biller": "Utility", "reference": "ABC-123"}, "20.00", payment_details),
            (self.window.go_to_send, self.window.send_screen,
             {"number": "09170000002", "name": "Bob Example"}, "50.00", account_details),
        )
        for navigate, screen, values, amount, detail_type in cases:
            with self.subTest(kind=screen.kind):
                navigate()
                self.fill_form(screen, values, amount)
                self.assertIs(self.window.stacked_widget.currentWidget(), self.window.confirm_screen)
                self.assertIsInstance(self.window.confirm_screen.details, detail_type)
                self.assertIsInstance(self.window.confirm_screen.details.amount, Decimal)
                self.verify()
                self.assertIs(self.window.stacked_widget.currentWidget(), self.window.receipt_screen)
                self.window.receipt_screen.done_btn.click()
        self.assertEqual(self.window.main_menu_screen.balance_label.text(), "PHP 150.00")
        users = storage.load_users()
        self.assertEqual(users[0].balance, Decimal("150.00"))
        self.assertEqual(users[1].balance, Decimal("50.00"))
        self.assertEqual(len(storage.load_transactions()), 5)

    def test_payment_categories_and_subcategories_reset_together(self):
        """Keep payment subcategories synchronized with category selection."""
        screen = self.window.payment_screen
        for category, subcategories in PAYMENT_STRUCTURE.items():
            screen.category_combo.setCurrentText(category)
            self.assertEqual(
                [screen.subcategory_combo.itemText(i) for i in range(screen.subcategory_combo.count())],
                subcategories,
            )
        screen.reset()
        category = screen.category_combo.currentText()
        self.assertEqual(screen.subcategory_combo.currentText(), PAYMENT_STRUCTURE[category][0])

    def test_amount_text_preserves_precision_and_rejects_bad_grouping(self):
        """Reject invalid amount text while preserving valid decimal precision."""
        self.register()
        self.window.go_to_cash_in()
        screen = self.window.cash_in_screen
        screen.inputs["source"].setText("Bank")
        for invalid in ("", "0", "-1", "nan", "inf", "1.001", "1.00000000000000001", "1,,2", "1,23"):
            with self.subTest(amount=invalid):
                screen.amount_input.setText(invalid)
                screen.action_btn.click()
                self.assertIs(self.window.stacked_widget.currentWidget(), screen)
                self.assertIsNone(self.window.pending_transaction)
                self.assertTrue(screen.error_label.text())
        screen.amount_input.setText("1,200.00")
        screen.action_btn.click()
        self.assertIsInstance(self.window.confirm_screen.details, deposit_details)
        self.assertEqual(self.window.confirm_screen.details.amount, Decimal("1200.00"))

    def test_empty_forms_do_not_open_confirmation(self):
        """Keep incomplete transactions on their forms without pending details."""
        self.register()
        for navigate, screen in (
            (self.window.go_to_send, self.window.send_screen),
            (self.window.go_to_payment, self.window.payment_screen),
            (self.window.go_to_cash_in, self.window.cash_in_screen),
            (self.window.go_to_cash_out, self.window.cash_out_screen),
        ):
            navigate()
            screen.amount_input.setText("10.00")
            screen.action_btn.click()
            self.assertIs(self.window.stacked_widget.currentWidget(), screen)
            self.assertTrue(screen.error_label.text())
            self.assertIsNone(self.window.pending_transaction)

    def test_wrong_pin_and_storage_error_leave_confirmation_retryable(self):
        """Allow confirmation retries after wrong PINs or uncommitted save errors."""
        self.register()
        self.window.go_to_cash_in()
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"})
        screen = self.window.confirm_screen
        pending = self.window.pending_transaction
        self.verify("9999")
        self.assertIs(self.window.stacked_widget.currentWidget(), screen)
        self.assertIs(self.window.pending_transaction, pending)
        self.assertEqual(screen.pin_input.get_pin(), "")
        self.assertTrue(screen.verify_btn.isEnabled())
        with patch.object(storage, "deposit_and_save", side_effect=storage.StorageError("Disk full")):
            self.verify()
        self.assertEqual(screen.error_label.text(), "Disk full")
        self.assertIs(self.window.stacked_widget.currentWidget(), screen)
        self.assertIs(self.window.pending_transaction, pending)
        self.assertEqual(self.window.current_user.balance, 0)
        self.verify()
        self.assertIs(self.window.stacked_widget.currentWidget(), self.window.receipt_screen)
        self.assertEqual(self.window.current_user.balance, 100)

    def test_verification_cannot_execute_twice_or_reenter(self):
        """Prevent duplicate and reentrant transaction confirmation."""
        self.register()
        self.window.go_to_cash_in()
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"})
        screen = self.window.confirm_screen
        execute = self.window.execute_transaction

        def reenter(kind, details, pin):
            """Try confirmation again while the original transaction is executing."""
            self.assertFalse(screen.verify_btn.isEnabled())
            self.assertFalse(screen.cancel_btn.isEnabled())
            screen.on_verify()
            return execute(kind, details, pin)

        with patch.object(self.window, "execute_transaction", side_effect=reenter) as mocked:
            self.verify()
            screen.on_verify()
            mocked.assert_called_once()
        self.assertIsNone(screen.kind)
        self.assertIsNone(screen.details)
        self.assertIsNone(self.window.pending_transaction)
        self.assertEqual(screen.pin_input.get_pin(), "")
        self.assertFalse(screen.verify_btn.isEnabled())
        self.assertEqual(len(storage.load_transactions()), 1)

    def test_committed_storage_error_clears_confirmation_and_prevents_retry(self):
        """Consume confirmation when a save committed before reporting an error."""
        self.register()
        self.window.go_to_cash_in()
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"})
        screen = self.window.confirm_screen
        deposit = storage.deposit_and_save

        def commit_then_report_cleanup_failure(*args):
            """Commit a deposit before simulating a cleanup failure."""
            deposit(*args)
            raise storage.StorageError("Saved; marker cleanup failed. Reconcile before continuing.", committed=True)

        with patch.object(storage, "deposit_and_save", side_effect=commit_then_report_cleanup_failure) as action:
            self.verify()
            self.assertIs(self.window.stacked_widget.currentWidget(), screen)
            self.assertIn("marker cleanup failed", screen.error_label.text())
            self.assertEqual(screen.pin_input.get_pin(), "")
            self.assertIsNone(screen.kind)
            self.assertIsNone(screen.details)
            self.assertIsNone(self.window.pending_transaction)
            self.assertFalse(screen.verify_btn.isEnabled())
            self.assertEqual(self.window.current_user.balance, Decimal("100.00"))
            self.assertEqual(storage.load_users()[0].balance, Decimal("100.00"))
            self.assertEqual(len(storage.load_transactions()), 1)
            # Reconciliation permits further actions, but this confirmation stays consumed.
            self.enter_pin(screen.pin_input)
            screen.on_verify()
            screen.verify_btn.click()
            action.assert_called_once()
        self.assertEqual(len(storage.load_transactions()), 1)

    def test_cancel_confirmation_discards_pending_details(self):
        """Clear pending transaction details and PIN input on cancellation."""
        self.register()
        self.window.go_to_cash_in()
        self.fill_form(self.window.cash_in_screen, {"source": "Bank"})
        self.enter_pin(self.window.confirm_screen.pin_input)
        self.window.confirm_screen.cancel_btn.click()
        self.assertIsNone(self.window.pending_transaction)
        self.assertIsNone(self.window.confirm_screen.details)
        self.assertEqual(self.window.confirm_screen.pin_input.get_pin(), "")
        self.window.confirm_screen.on_verify()
        self.assertEqual(storage.load_transactions(), [])

    def test_logout_resets_sensitive_fields_and_receipt(self):
        """Clear account state and sensitive screen contents on logout."""
        self.register()
        self.deposit()
        self.window.go_to_send()
        self.fill_form(self.window.send_screen, {"number": "09170000002", "name": "Bob"})
        self.enter_pin(self.window.confirm_screen.pin_input)
        self.window.go_to_login()
        self.assertIsNone(self.window.current_user)
        self.assertIsNone(self.window.pending_transaction)
        self.assertEqual(self.window.login_screen.mobile_input.text(), "")
        self.assertEqual(self.window.create_account_screen.name_input.text(), "")
        self.assertIsNone(self.window.confirm_screen.details)
        self.assertEqual(self.window.confirm_screen.card_layout.count(), 0)
        self.assertEqual(self.window.receipt_screen.card_layout.count(), 0)
        for screen in (self.window.send_screen, self.window.payment_screen,
                       self.window.cash_in_screen, self.window.cash_out_screen):
            self.assertEqual(screen.amount_input.text(), "")

    def test_startup_storage_error_is_plain_text_on_login(self):
        """Display startup storage errors literally and prevent login."""
        with patch.object(storage, "load_users", side_effect=storage.StorageError("<b>Corrupt file</b>")):
            other = EWalletApp()
        try:
            self.assertEqual(other.login_screen.error_label.text(), "<b>Corrupt file</b>")
            self.assertEqual(other.login_screen.error_label.textFormat(), Qt.TextFormat.PlainText)
            other.login_screen.login_btn.click()
            self.assertIs(other.stacked_widget.currentWidget(), other.login_screen)
        finally:
            other.close()
            other.deleteLater()

    def test_confirmation_alias_and_literal_summary(self):
        """Keep the confirmation alias and render summary content literally."""
        self.assertIs(ConfirmScreen, ConfirmTransactionScreen)
        self.register()
        self.window.go_to_cash_in()
        self.fill_form(self.window.cash_in_screen, {"source": "<b>Bank</b>"})
        for label in self.window.confirm_screen.card.findChildren(QLabel):
            self.assertEqual(label.textFormat(), Qt.TextFormat.PlainText)
            self.assertTrue(label.wordWrap())
        self.assertIn("<b>Bank</b>", self.window.confirm_screen.card_layout.itemAt(0).widget().text())

    def test_receipt_long_unbroken_references_wrap_and_scroll(self):
        """Wrap long receipt references and scroll within the fixed window size."""
        receipt = {
            "Name": "Alexandra " * 8, "Amount": 1250.50,
            "Account Details": "Reference: " + "1234567890" * 12,
            "Transaction Number": "DEP-000000001", "Date": "2026-10-18", "Time": "12:00:00",
        }
        self.window.go_to_receipt(receipt)
        self.flush_events()
        screen = self.window.receipt_screen
        row = screen.card_layout.itemAt(4).widget().layout()
        reference = row.itemAt(1).widget()
        self.assertEqual(reference.accessibleName(), receipt["Account Details"])
        self.assertEqual(reference.text().replace("\u200b", ""), receipt["Account Details"])
        self.assertGreater(reference.heightForWidth(reference.width()), 32)
        self.assertGreaterEqual(reference.height(), reference.heightForWidth(reference.width()))
        receipt["Account Details"] = "Reference: " + "1234567890" * 400
        self.window.go_to_receipt(receipt)
        self.flush_events()
        self.assertGreater(screen.receipt_scroll.verticalScrollBar().maximum(), 0)
        self.assertEqual(screen.receipt_scroll.horizontalScrollBar().maximum(), 0)
        reference = screen.card_layout.itemAt(4).widget().layout().itemAt(1).widget()
        self.assertGreaterEqual(reference.height(), reference.heightForWidth(reference.width()))
        self.assertEqual(self.window.size().width(), 450)
        self.assertEqual(self.window.size().height(), 750)
        for label in screen.card.findChildren(QLabel):
            self.assertEqual(label.textFormat(), Qt.TextFormat.PlainText)


if __name__ == "__main__":
    unittest.main()
