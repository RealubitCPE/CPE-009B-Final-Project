"""Backend checks use only temporary wallet files, never project data."""

from dataclasses import replace
from decimal import Decimal
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import call, patch

from backend import storage
from backend.transactions import (
    PAYMENT_STRUCTURE, account_details, confirm_deposit, confirm_payment,
    confirm_transaction, confirm_withdraw, deposit_details, payment_details,
    withdraw_details,
)
from backend.user import AuthenticationError, InsufficientFundsError, User, find_user, login, register


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Prepare the resources shared by this test class."""
        cls.pin_hash = User.hashPin("0123", b"0123456789abcdef")

    def setUp(self):
        """Give each test fresh wallet data and temporary storage."""
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.users_path = Path(self.directory.name, "users.json")
        self.transactions_path = Path(self.directory.name, "transactions.json")
        for name, value in (("USERS_FILE", str(self.users_path)),
                            ("TRANSACTIONS_FILE", str(self.transactions_path))):
            patcher = patch.object(storage, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.alice = User("Alice", "09123456789", self.pin_hash, "100.00")
        self.bob = User("Bob", "09987654321", self.pin_hash, "25.00")
        self.users = [self.alice, self.bob]
        storage.save_users(self.users)

    def assert_balances(self, alice="100.00", bob="25.00"):
        """Check account balances both in memory and on disk."""
        self.assertEqual([user.balance for user in self.users], [Decimal(alice), Decimal(bob)])
        self.assertEqual([user.balance for user in storage.load_users()], [Decimal(alice), Decimal(bob)])

    def samples(self):
        """Build valid details for each supported transaction type."""
        return [
            (confirm_deposit, deposit_details("Bank", "Alice", "1.25")),
            (confirm_withdraw, withdraw_details("Bank", "Alice", "123", "1.25")),
            (confirm_transaction, account_details(self.bob.mobile_number, "Bob", "1.25")),
            (confirm_payment, payment_details("Bills", "water", "Water Co", "123", "1.25")),
        ]

    def test_compatibility_imports_share_canonical_classes_and_storage_state(self):
        """Check that legacy imports share the canonical backend objects."""
        self.assertIs(importlib.import_module("user").User, User)
        self.assertIs(importlib.import_module("storage"), storage)
        for module in ("Transaction", "utils.transactions"):
            self.assertIs(importlib.import_module(module).account_details, account_details)
            self.assertIs(importlib.import_module(module).PAYMENT_STRUCTURE, PAYMENT_STRUCTURE)

    def test_default_storage_paths_stay_at_project_root(self):
        """Keep default wallet storage relative to the project root."""
        self.assertEqual(Path(storage.BASE_DIR), Path(__file__).resolve().parents[1])

    def test_salted_pin_hash_login_and_round_trip(self):
        """Check salted PIN hashing and authentication after serialization."""
        user = User.createNew(" Carol ", "09111-111-111", "0123")
        other = User.createNew("Carol", "09111111111", "0123")
        self.assertNotEqual(user.pin_hash, other.pin_hash)
        self.assertEqual(len(user.pin_hash), 97)
        self.assertTrue(user.checkPin("0123"))
        self.assertFalse(user.checkPin("9999"))
        self.assertFalse(user.checkPin(True))
        loaded = User.fromDict(user.toDict())
        self.assertIs(login("09111-111-111", "0123", [loaded]), loaded)
        self.assertIs(find_user("09111-111-111", [loaded]), loaded)
        for mobile, pin in ((user.mobile_number, "9999"), ("09000000000", "0123")):
            with self.assertRaises(AuthenticationError):
                login(mobile, pin, [loaded])

    def test_registration_validation_and_duplicates_leave_list_unchanged(self):
        """Reject invalid registrations without changing existing users."""
        invalid = [(" ", "09111111111", "1234"), ("Carol", "123", "1234"),
                   ("Carol", "09111111111", "12"), ("Carol", "09111111111", "abcd"),
                   ("Carol", "09111111111", "１２３４"),
                   ("Alice", self.alice.mobile_number, "1234")]
        for name, mobile, pin in invalid:
            with self.subTest(name=name, mobile=mobile, pin=pin), self.assertRaises(ValueError):
                register(name, mobile, pin, self.users)
            self.assertEqual(self.users, [self.alice, self.bob])

    def test_five_failed_pins_lock_correct_and_incorrect_attempts_without_hashing(self):
        """Block all PIN checks during cooldown without computing new hashes."""
        with patch("backend.user.time.monotonic", return_value=100):
            for _ in range(4):
                self.assertFalse(self.alice.checkPin("9999"))
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                self.alice.checkPin("9999")
            with patch.object(User, "hashPin") as hasher:
                for pin in ("0123", "9999"):
                    with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                        self.alice.checkPin(pin)
                hasher.assert_not_called()

    def test_pin_cooldown_expires_without_extending_on_blocked_attempts(self):
        """Keep blocked attempts from extending the PIN cooldown."""
        with patch("backend.user.time.monotonic", return_value=100) as clock:
            for _ in range(4):
                self.assertFalse(self.alice.checkPin("9999"))
            with self.assertRaises(AuthenticationError):
                self.alice.checkPin("9999")
            clock.return_value = 129.1
            with self.assertRaisesRegex(AuthenticationError, "1 second\\."):
                self.alice.checkPin("0123")
            clock.return_value = 130
            self.assertTrue(self.alice.checkPin("0123"))

    def test_cooldown_expiry_resets_failed_attempt_count_even_for_wrong_pin(self):
        """Start a fresh failure allowance after cooldown expires."""
        with patch("backend.user.time.monotonic", return_value=100) as clock:
            for _ in range(4):
                self.assertFalse(self.alice.checkPin("9999"))
            with self.assertRaises(AuthenticationError):
                self.alice.checkPin("9999")
            clock.return_value = 130
            for _ in range(4):
                self.assertFalse(self.alice.checkPin("9999"))
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                self.alice.checkPin("9999")

    def test_login_and_confirmation_share_failed_pin_attempts(self):
        """Share the PIN failure limit across login and transaction checks."""
        with patch("backend.user.time.monotonic", return_value=100):
            for _ in range(2):
                with self.assertRaisesRegex(AuthenticationError, "Invalid mobile number or PIN"):
                    login(self.alice.mobile_number, "9999", self.users)
                self.assertFalse(self.alice.checkPin("9999"))
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                login(self.alice.mobile_number, "9999", self.users)
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                self.alice.checkPin("0123")
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                login(self.alice.mobile_number, "0123", self.users)
            self.assertIs(login(self.bob.mobile_number, "0123", self.users), self.bob)

    def test_successful_pin_check_resets_previous_failures(self):
        """Clear earlier PIN failures after successful authentication."""
        with patch("backend.user.time.monotonic", return_value=100):
            for _ in range(4):
                self.assertFalse(self.alice.checkPin("9999"))
            self.assertIs(login(self.alice.mobile_number, "0123", self.users), self.alice)
            for _ in range(4):
                self.assertFalse(self.alice.checkPin("9999"))
            with self.assertRaises(AuthenticationError):
                self.alice.checkPin("9999")

    def test_malformed_pin_attempts_count_towards_cooldown(self):
        """Count malformed PIN input toward the retry limit."""
        with patch("backend.user.time.monotonic", return_value=100):
            for pin in (True, None, "", "12345"):
                self.assertFalse(self.alice.checkPin(pin))
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                self.alice.checkPin("abcd")

    def test_retry_guard_is_object_local_and_not_serialized(self):
        """Keep temporary PIN retry state out of saved account data."""
        with patch("backend.user.time.monotonic", return_value=100):
            for _ in range(4):
                self.assertFalse(self.alice.checkPin("9999"))
            with self.assertRaises(AuthenticationError):
                self.alice.checkPin("9999")
            self.assertEqual(set(self.alice.toDict()), {"name", "mobile_number", "pin_hash", "balance"})
            reloaded = User.fromDict(self.alice.toDict())
            self.assertTrue(reloaded.checkPin("0123"))

    def test_registration_persists_authentication(self):
        """Reload a registered account and authenticate its saved PIN."""
        user = storage.register_and_save("Carol", "09111111111", "1234", self.users)
        self.assertEqual(user.balance, Decimal(0))
        loaded = storage.load_users()
        self.assertEqual(login(user.mobile_number, "1234", loaded).name, "Carol")

    def test_registration_rolls_back_when_save_fails(self):
        """Undo registration when the account file cannot be saved."""
        original = self.users_path.read_bytes()
        with patch.object(storage.os, "replace", side_effect=OSError("blocked")):
            with self.assertRaises(storage.StorageError):
                storage.register_and_save("Carol", "09111111111", "1234", self.users)
        self.assertEqual(self.users, [self.alice, self.bob])
        self.assertEqual(self.users_path.read_bytes(), original)

    def test_decimal_arithmetic_has_no_fractional_cent_drift(self):
        """Keep deposits and withdrawals exact to the cent."""
        user = User("Alice", self.alice.mobile_number, self.pin_hash)
        user.deposit(0.1)
        user.deposit(0.2)
        self.assertEqual(user.balance, Decimal("0.3"))
        user.withdraw("0.30")
        self.assertEqual(user.balance, Decimal(0))
        with self.assertRaises(InsufficientFundsError):
            user.withdraw("0.01")
        self.assertEqual(user.balance, Decimal(0))

    def test_confirmations_accept_explicit_sequence_and_optional_sequence(self):
        """Support supplied receipt sequences and automatic unique numbers."""
        for confirm, details in self.samples():
            with self.subTest(confirm=confirm.__name__):
                receipt = confirm(details, sequence_value=42)
                self.assertEqual(receipt["Status"], "Success")
                self.assertTrue(receipt["Transaction Number"].endswith("000000042"))
                self.assertEqual(receipt["Amount"], 1.25)
                self.assertNotEqual(confirm(details)["Transaction Number"], confirm(details)["Transaction Number"])

    def test_all_payment_categories_and_case_normalization(self):
        """Accept every payment category with case-insensitive matching."""
        for category, subcategories in PAYMENT_STRUCTURE.items():
            for subcategory in subcategories:
                with self.subTest(category=category, subcategory=subcategory):
                    receipt = confirm_payment(payment_details(
                        category.upper(), subcategory.upper(), "Biller", "Ref", "2.00"))
                    self.assertEqual(receipt["Status"], "Success")
        with self.assertRaises(ValueError):
            confirm_payment(payment_details("Bank", "water", "Biller", "Ref", 2))

    def test_all_confirmations_reject_invalid_amounts(self):
        """Reject invalid or unsafe amounts for every transaction type."""
        amounts = [True, False, None, 0, -1, "", " ", "NaN", float("nan"),
                   "Infinity", float("inf"), float("-inf"), "1.001", Decimal("0.001"),
                   "1.000", "9007199254740992.01", Decimal("1e1000")]
        for confirm, details in self.samples():
            for amount in amounts:
                with self.subTest(confirm=confirm.__name__, amount=repr(amount)):
                    with self.assertRaises(ValueError):
                        confirm(replace(details, amount=amount))

    def test_required_fields_reject_whitespace_and_none(self):
        """Reject missing or blank transaction fields."""
        for confirm, details in self.samples():
            for field in details.__dataclass_fields__:
                if field == "amount":
                    continue
                for value in ("  ", None):
                    with self.subTest(confirm=confirm.__name__, field=field, value=value):
                        with self.assertRaises(ValueError):
                            confirm(replace(details, **{field: value}))

    def test_deposit_withdraw_payment_persist_receipts_and_history(self):
        """Check saved balances and history plus returned receipts."""
        deposit = storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", "0.10"), self.users)
        withdrawal = storage.withdraw_and_save(
            self.alice, withdraw_details("ATM", "Alice", "123", "0.20"), self.users)
        payment = storage.pay_and_save(
            self.alice, payment_details("Bills", "water", "Water Co", "123", "1.25"), self.users)
        self.assert_balances("98.65")
        history = storage.get_transactions(self.alice.mobile_number)
        self.assertEqual([record["type"] for record in history], ["deposit", "withdrawal", "payment"])
        for index, receipt in enumerate((deposit, withdrawal, payment), 1):
            self.assertEqual(receipt["Status"], "Success")
            self.assertTrue(receipt["Transaction Number"].endswith(f"{index:09d}"))
        self.assertEqual(storage.get_transactions(self.bob.mobile_number), [])

    def test_send_updates_both_accounts_and_both_histories(self):
        """Save both balances and linked histories for a transfer."""
        receipt = storage.send_and_save(
            self.alice, account_details("09987-654-321", " bob ", "12.34"), self.users)
        self.assertEqual(receipt["Status"], "Success")
        self.assert_balances("87.66", "37.34")
        sent = storage.get_transactions(self.alice.mobile_number)
        received = storage.get_transactions(self.bob.mobile_number)
        self.assertEqual(sent[0]["type"], "send")
        self.assertEqual(received[0]["type"], "receive")
        self.assertEqual(received[0]["related_transaction_id"], sent[0]["transaction_id"])
        self.assertEqual(storage.next_transaction_id(), 3)

    def test_send_rejects_unknown_self_mismatched_or_blank_recipient(self):
        """Reject invalid transfer recipients without saving changes."""
        cases = [("09000000000", "Nobody"), (self.alice.mobile_number, "Alice"),
                 (self.bob.mobile_number, "Not Bob"), (self.bob.mobile_number, " ")]
        for number, name in cases:
            with self.subTest(number=number, name=name), self.assertRaises(ValueError):
                storage.send_and_save(self.alice, account_details(number, name, "1.00"), self.users)
            self.assert_balances()
            self.assertEqual(storage.load_transactions(), [])

    def test_insufficient_funds_never_changes_balances_or_log(self):
        """Leave balances and history untouched when funds are insufficient."""
        actions = [
            (storage.withdraw_and_save, withdraw_details("ATM", "Alice", "123", "100.01")),
            (storage.pay_and_save, payment_details("Bills", "water", "Water Co", "123", "100.01")),
            (storage.send_and_save, account_details(self.bob.mobile_number, "Bob", "100.01")),
        ]
        for action, details in actions:
            with self.subTest(action=action.__name__), self.assertRaises(InsufficientFundsError):
                action(self.alice, details, self.users)
            self.assert_balances()
            self.assertEqual(storage.load_transactions(), [])

    def test_unregistered_active_user_is_rejected(self):
        """Reject account objects outside the registered user list."""
        detached = User.fromDict(self.alice.toDict())
        with self.assertRaises(ValueError):
            storage.deposit_and_save(detached, deposit_details("Bank", "Alice", 1), self.users)
        self.assert_balances()

    def test_invalid_transaction_leaves_existing_files_untouched(self):
        """Preserve existing wallet bytes when transaction validation fails."""
        storage.add_transaction(self.alice.mobile_number, "deposit", "1.00")
        original_users = self.users_path.read_bytes()
        original_transactions = self.transactions_path.read_bytes()
        for amount in (True, "NaN", "0.001", "9007199254740992.01"):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", amount), self.users)
        self.assertEqual(self.users_path.read_bytes(), original_users)
        self.assertEqual(self.transactions_path.read_bytes(), original_transactions)
        self.assert_balances()

    def test_unrepresentable_result_rolls_back_both_send_balances(self):
        """Undo a transfer whose resulting balance cannot be saved exactly."""
        self.bob.balance = "9007199254740992"
        storage.save_users(self.users)
        with self.assertRaises(ValueError):
            storage.send_and_save(self.alice, account_details(self.bob.mobile_number, "Bob", "0.01"), self.users)
        self.assert_balances(bob="9007199254740992")
        self.assertEqual(storage.load_transactions(), [])

    def test_failed_staging_never_writes_partial_data(self):
        """Preserve wallet data when staging a save fails."""
        original = self.users_path.read_bytes()
        with patch.object(storage.tempfile, "mkstemp", side_effect=OSError("disk full")):
            with self.assertRaises(storage.StorageError):
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assert_balances()
        self.assertEqual(self.users_path.read_bytes(), original)
        self.assertFalse(self.transactions_path.exists())

    def test_failed_second_stage_cleans_first_temp_file(self):
        """Remove the first staging file when the second cannot be created."""
        real_mkstemp = tempfile.mkstemp
        calls = 0

        def fail_second_stage(*args, **kwargs):
            """Fail only the second staging-file creation."""
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("disk full")
            return real_mkstemp(*args, **kwargs)

        with patch.object(storage.tempfile, "mkstemp", side_effect=fail_second_stage):
            with self.assertRaises(storage.StorageError):
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assert_balances()
        self.assertEqual(list(Path(self.directory.name).glob("*.tmp")), [])

    def test_failed_first_replace_rolls_back_memory_without_log(self):
        """Restore in-memory balances when the first replacement fails."""
        with patch.object(storage.os, "replace", side_effect=OSError("locked")):
            with self.assertRaises(storage.StorageError):
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assert_balances()
        self.assertEqual(storage.load_transactions(), [])

    def test_failed_log_replace_restores_exact_original_users_and_log(self):
        """Restore both original files after a history replacement failure."""
        storage.add_transaction(self.alice.mobile_number, "deposit", "1.00")
        original_users = self.users_path.read_bytes()
        original_transactions = self.transactions_path.read_bytes()
        real_replace = os.replace

        def fail_log(source, destination):
            """Fail history replacement while permitting other replacements."""
            if destination == str(self.transactions_path):
                raise OSError("log locked")
            return real_replace(source, destination)

        with patch.object(storage.os, "replace", side_effect=fail_log):
            with self.assertRaisesRegex(storage.StorageError, "balances were restored"):
                storage.send_and_save(
                    self.alice, account_details(self.bob.mobile_number, "Bob", 1), self.users)
        self.assert_balances()
        self.assertEqual(self.users_path.read_bytes(), original_users)
        self.assertEqual(self.transactions_path.read_bytes(), original_transactions)
        self.assertEqual(list(Path(self.directory.name).glob("*.tmp")), [])
        self.assertFalse(Path(storage._pending_file()).exists())

    def test_failed_log_replace_restores_missing_users_file(self):
        """Restore the absence of a users file after rollback."""
        self.users_path.unlink()
        real_replace = os.replace

        def fail_log(source, destination):
            """Fail history replacement while permitting other replacements."""
            if destination == str(self.transactions_path):
                raise OSError("log locked")
            return real_replace(source, destination)

        with patch.object(storage.os, "replace", side_effect=fail_log):
            with self.assertRaises(storage.StorageError):
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assertEqual(self.alice.balance, Decimal(100))
        self.assertFalse(self.users_path.exists())
        self.assertFalse(self.transactions_path.exists())

    def test_rollback_failure_is_explicit_and_not_success(self):
        """Retain recovery evidence and block reads when rollback fails."""
        real_replace = os.replace
        calls = 0

        def fail_log_and_rollback(source, destination):
            """Allow one replacement before failing both saving and rollback."""
            nonlocal calls
            calls += 1
            if calls > 1:
                raise OSError("disk unavailable")
            return real_replace(source, destination)

        with patch.object(storage.os, "replace", side_effect=fail_log_and_rollback):
            with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assertEqual(self.alice.balance, Decimal(100))
        marker = Path(storage._pending_file())
        self.assertTrue(marker.exists())
        backup = Path(json.loads(marker.read_text(encoding="utf-8"))["original_users_backup"])
        self.assertTrue(backup.exists())
        self.assertEqual(json.loads(backup.read_text(encoding="utf-8"))[0]["balance"], 100.0)
        with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
            storage.load_users()
        with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
            storage.load_transactions()

    def test_interrupted_save_marker_blocks_loads_and_registration_without_changes(self):
        """Block wallet access while an interrupted-save marker exists."""
        marker = Path(storage._pending_file())
        marker.write_text("interrupted", encoding="utf-8")
        original = self.users_path.read_bytes()
        for _ in range(2):
            for loader in (storage.load_users, storage.load_transactions):
                with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
                    loader()
        with self.assertRaises(storage.StorageError):
            storage.register_and_save("Carol", "09111111111", "1234", self.users)
        self.assertEqual(self.users, [self.alice, self.bob])
        self.assertEqual(self.users_path.read_bytes(), original)
        self.assertEqual(marker.read_text(encoding="utf-8"), "interrupted")

    def test_process_crash_between_replacements_blocks_next_launch(self):
        """Detect a process crash between the two wallet replacements."""
        script = """
import os
import sys
from backend import storage
from backend.transactions import deposit_details
storage.USERS_FILE, storage.TRANSACTIONS_FILE = sys.argv[1:]
users = storage.load_users()
real_replace = os.replace
def crash_after_users(source, destination):
    real_replace(source, destination)
    if destination == storage.USERS_FILE:
        os._exit(17)
storage.os.replace = crash_after_users
storage.deposit_and_save(users[0], deposit_details('Bank', 'Alice', '1.00'), users)
"""
        crashed = subprocess.run(
            [sys.executable, "-c", script, str(self.users_path), str(self.transactions_path)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        self.assertTrue(Path(storage._pending_file()).exists())
        for loader in (storage.load_users, storage.load_transactions):
            with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
                loader()
        self.assertEqual(json.loads(self.users_path.read_text(encoding="utf-8"))[0]["balance"], 101)
        self.assertFalse(self.transactions_path.exists())

    def test_marker_exists_before_first_wallet_replacement(self):
        """Create recovery information before replacing wallet data."""
        real_replace = os.replace

        def check_marker(source, destination):
            """Require a recovery marker before delegating file replacement."""
            self.assertTrue(Path(storage._pending_file()).exists())
            return real_replace(source, destination)

        with patch.object(storage.os, "replace", side_effect=check_marker):
            storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assertFalse(Path(storage._pending_file()).exists())
        self.assert_balances("101")

    def test_failed_marker_creation_never_changes_balances_or_data(self):
        """Leave wallet data unchanged when a recovery marker cannot be created."""
        real_open = open

        def fail_marker(filename, *args, **kwargs):
            """Fail recovery-marker creation without blocking other file access."""
            if filename == storage._pending_file():
                raise PermissionError("marker blocked")
            return real_open(filename, *args, **kwargs)

        with patch("builtins.open", side_effect=fail_marker):
            with self.assertRaises(storage.StorageError):
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assert_balances()
        self.assertEqual(storage.load_transactions(), [])

    def test_marker_cleanup_failure_reports_committed_data_and_locks_wallet(self):
        """Report committed data and block access when marker cleanup fails."""
        real_remove = os.remove

        def fail_marker_remove(filename):
            """Fail marker cleanup while permitting other removals."""
            if filename == storage._pending_file():
                raise PermissionError("marker locked")
            return real_remove(filename)

        with patch.object(storage.os, "remove", side_effect=fail_marker_remove):
            with self.assertRaisesRegex(storage.StorageError, "Transaction was saved") as failure:
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assertTrue(failure.exception.committed)
        self.assertEqual(self.alice.balance, Decimal(101))
        self.assertEqual(json.loads(self.users_path.read_text(encoding="utf-8"))[0]["balance"], 101)
        self.assertEqual(len(json.loads(self.transactions_path.read_text(encoding="utf-8"))), 1)
        with self.assertRaises(storage.StorageError):
            storage.load_users()
        with self.assertRaises(storage.StorageError):
            storage.load_transactions()

    def test_rollback_marker_cleanup_failure_keeps_original_balances_and_locks_wallet(self):
        """Keep restored balances locked if rollback marker cleanup fails."""
        real_replace = os.replace
        real_remove = os.remove
        original = self.users_path.read_bytes()

        def fail_log(source, destination):
            """Fail history replacement while permitting other replacements."""
            if destination == str(self.transactions_path):
                raise OSError("log locked")
            return real_replace(source, destination)

        def fail_marker_remove(filename):
            """Fail marker cleanup while permitting other removals."""
            if filename == storage._pending_file():
                raise PermissionError("marker locked")
            return real_remove(filename)

        with patch.object(storage.os, "replace", side_effect=fail_log):
            with patch.object(storage.os, "remove", side_effect=fail_marker_remove):
                with self.assertRaisesRegex(storage.StorageError, "Balances were restored"):
                    storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        self.assertEqual(self.alice.balance, Decimal(100))
        self.assertEqual(self.users_path.read_bytes(), original)
        self.assertTrue(Path(storage._pending_file()).exists())

    def test_corrupt_users_remain_in_place_and_block_repeated_launch_and_save(self):
        """Preserve corrupt user data and reject further wallet operations."""
        for content in (b"{bad json", b"\xff", b"{}", b"[{}]"):
            with self.subTest(content=content):
                self.users_path.write_bytes(content)
                for _ in range(2):
                    with self.assertRaises(storage.StorageError):
                        storage.load_users()
                with self.assertRaises(storage.StorageError):
                    storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
                self.assertEqual(self.users_path.read_bytes(), content)
                self.assertFalse(Path(str(self.users_path) + ".bak").exists())
                self.assertEqual(self.alice.balance, Decimal(100))

    def test_corrupt_log_blocks_transactions_without_debit(self):
        """Prevent debits when the existing transaction log is corrupt."""
        for content in (b"[", b"{}", b"[{}]"):
            with self.subTest(content=content):
                self.transactions_path.write_bytes(content)
                for _ in range(2):
                    with self.assertRaises(storage.StorageError):
                        storage.withdraw_and_save(
                            self.alice, withdraw_details("ATM", "Alice", "123", 1), self.users)
                self.assertEqual(self.transactions_path.read_bytes(), content)
                self.assert_balances()

    def test_malformed_balances_and_duplicate_users_fail_closed(self):
        """Reject malformed balances and duplicate saved accounts."""
        original = [user.toDict() for user in self.users]
        for value in (-1, True, float("nan"), float("inf"), 1.001, "9007199254740992.01"):
            data = [dict(original[0], balance=value), original[1]]
            self.users_path.write_text(json.dumps(data), encoding="utf-8")
            with self.subTest(value=value), self.assertRaises(storage.StorageError):
                storage.load_users()
        self.users_path.write_text(json.dumps([original[0], original[0]]), encoding="utf-8")
        with self.assertRaises(storage.StorageError):
            storage.load_users()

    def test_malformed_transaction_records_fail_closed(self):
        """Reject invalid or duplicate saved transaction records."""
        record = {"transaction_id": 1, "mobile_number": self.alice.mobile_number,
                  "type": "deposit", "amount": 1.0, "date": "2026-10-18"}
        for field, value in (("transaction_id", True), ("transaction_id", 0), ("amount", "NaN"),
                             ("amount", 1.001), ("type", " "), ("date", "bad"),
                             ("mobile_number", "123")):
            self.transactions_path.write_text(json.dumps([dict(record, **{field: value})]), encoding="utf-8")
            with self.subTest(field=field, value=value), self.assertRaises(storage.StorageError):
                storage.load_transactions()
        self.transactions_path.write_text(json.dumps([record, record]), encoding="utf-8")
        with self.assertRaises(storage.StorageError):
            storage.load_transactions()

    def test_read_oserror_is_wrapped(self):
        """Expose file-access failures as wallet storage errors."""
        with patch("builtins.open", side_effect=PermissionError("blocked")):
            with self.assertRaises(storage.StorageError):
                storage.load_users()
            with self.assertRaises(storage.StorageError):
                storage.get_transactions(self.alice.mobile_number)

    def test_missing_files_are_read_without_creating_wallet_data(self):
        """Read absent wallet files as empty without creating them."""
        self.users_path.unlink()
        self.assertEqual(storage.load_users(), [])
        self.assertEqual(storage.load_transactions(), [])
        self.assertFalse(self.users_path.exists())
        self.assertFalse(self.transactions_path.exists())

    def test_cli_passes_raw_amount_text_to_backend(self):
        """Preserve the exact amount text entered through the CLI."""
        cli = importlib.import_module("cli")
        with patch("builtins.input", side_effect=["Bank", "9007199254740992.01"]):
            with patch.object(storage, "deposit_and_save", return_value={}) as save:
                cli.do_deposit(self.alice, self.users)
        self.assertEqual(save.call_args.args[1].amount, "9007199254740992.01")

    def test_cli_transaction_menu_catches_storage_error(self):
        """Display storage failures in the CLI transaction menu."""
        cli = importlib.import_module("cli")
        action = unittest.mock.Mock(side_effect=storage.StorageError("disk unavailable"))
        with patch.dict(cli.ACTIONS, {"1": action}, clear=True):
            with patch("builtins.input", side_effect=["1", "0"]), patch("builtins.print") as printer:
                cli.user_menu(self.alice, self.users)
        self.assertTrue(any("Error: disk unavailable" in str(call) for call in printer.call_args_list))

    def test_cli_registration_and_login_use_hidden_pin_prompts(self):
        """Collect registration and login PINs through hidden prompts."""
        cli = importlib.import_module("cli")
        answers = ["1", "Carol", "09111111111", "2", "09111111111", "0"]
        with patch("builtins.input", side_effect=answers), patch("builtins.print"):
            with patch.object(cli.getpass, "getpass", side_effect=["1234", "1234"]) as hidden_pin:
                with patch.object(cli, "user_menu") as menu:
                    cli.main()
        self.assertEqual(hidden_pin.call_args_list, [call("4-digit PIN: "), call("PIN: ")])
        menu.assert_called_once()
        self.assertEqual(menu.call_args.args[0].mobile_number, "09111111111")
        self.assertEqual(storage.load_users()[-1].name, "Carol")


if __name__ == "__main__":
    unittest.main()
