"""Backend checks use only temporary wallet files, never project data."""

# Use replace to vary one field in transaction details.
from dataclasses import replace
# Use Decimal to compare money without floating-point rounding.
from decimal import Decimal
# Load compatibility modules and the CLI by module name.
import importlib
# Read and write JSON fixtures for storage checks.
import json
# Access file operations so tests can simulate storage failures.
import os
# Build paths and inspect temporary test files.
from pathlib import Path
# Run the intentional crash test in a separate process.
import subprocess
# Use the same Python executable for the crash test.
import sys
# Keep test wallet files in disposable temporary directories.
import tempfile
# Use the standard test runner and assertion helpers.
import unittest
# Temporarily replace dependencies and inspect recorded calls.
from unittest.mock import call, patch

# Exercise wallet persistence through the storage module.
from backend import storage
# Use the transaction detail types and confirmation helpers under test.
from backend.transactions import (
    PAYMENT_STRUCTURE, account_details, confirm_deposit, confirm_payment,
    confirm_transaction, confirm_withdraw, deposit_details, payment_details,
    withdraw_details,
)
# Use account operations and their expected validation exceptions.
from backend.user import AuthenticationError, InsufficientFundsError, User, find_user, login, register


# Group the backend regression checks in a unittest test case.
class BackendTests(unittest.TestCase):
    # Prepare shared resources once before this test class runs.
    @classmethod
    def setUpClass(cls):
        # Compute one reusable PIN hash for the test accounts.
        cls.pin_hash = User.hashPin("0123", b"0123456789abcdef")

    # Create fresh accounts, storage paths, or widgets for each test.
    def setUp(self):
        # Create an isolated directory for this test.
        self.directory = tempfile.TemporaryDirectory()
        # Register cleanup even if the test fails.
        self.addCleanup(self.directory.cleanup)
        # Choose the temporary users JSON path.
        self.users_path = Path(self.directory.name, "users.json")
        # Choose the temporary transaction JSON path.
        self.transactions_path = Path(self.directory.name, "transactions.json")
        # Exercise each name and value in this case set.
        for name, value in (("USERS_FILE", str(self.users_path)),
                            ("TRANSACTIONS_FILE", str(self.transactions_path))):
            # Prepare a temporary override for a storage-file path.
            patcher = patch.object(storage, name, value)
            # Activate the temporary override.
            patcher.start()
            # Register cleanup even if the test fails.
            self.addCleanup(patcher.stop)
        # Create Alice with a known opening balance.
        self.alice = User("Alice", "09123456789", self.pin_hash, "100.00")
        # Create Bob with a known opening balance.
        self.bob = User("Bob", "09987654321", self.pin_hash, "25.00")
        # Keep both test accounts in the working user list.
        self.users = [self.alice, self.bob]
        # Persist the current test accounts.
        storage.save_users(self.users)

    # Compare expected balances in memory and on disk.
    def assert_balances(self, alice="100.00", bob="25.00"):
        # Check the two in-memory balances against exact decimal amounts.
        self.assertEqual([user.balance for user in self.users], [Decimal(alice), Decimal(bob)])
        # Check the saved balances against the same exact decimal amounts.
        self.assertEqual([user.balance for user in storage.load_users()], [Decimal(alice), Decimal(bob)])

    # Provide one valid detail object for each transaction type.
    def samples(self):
        # Return the sample transaction cases to the calling test.
        return [
            (confirm_deposit, deposit_details("Bank", "Alice", "1.25")),
            (confirm_withdraw, withdraw_details("Bank", "Alice", "123", "1.25")),
            (confirm_transaction, account_details(self.bob.mobile_number, "Bob", "1.25")),
            (confirm_payment, payment_details("Bills", "water", "Water Co", "123", "1.25")),
        ]

    # Verify that compatibility imports share canonical classes and storage state.
    def test_compatibility_imports_share_canonical_classes_and_storage_state(self):
        # Check that the legacy import exposes the canonical User class.
        self.assertIs(importlib.import_module("user").User, User)
        # Check that legacy and canonical storage imports share one module.
        self.assertIs(importlib.import_module("storage"), storage)
        # Exercise each module in this case set.
        for module in ("Transaction", "utils.transactions"):
            # Check that account details is the expected object.
            self.assertIs(importlib.import_module(module).account_details, account_details)
            # Check that payment structure is the expected object.
            self.assertIs(importlib.import_module(module).PAYMENT_STRUCTURE, PAYMENT_STRUCTURE)

    # Verify that default storage paths stay at project root.
    def test_default_storage_paths_stay_at_project_root(self):
        # Check that default storage is rooted in the project directory.
        self.assertEqual(Path(storage.BASE_DIR), Path(__file__).resolve().parents[1])

    # Check salted PIN hashes, authentication, and serialization together.
    def test_salted_pin_hash_login_and_round_trip(self):
        # Create the account used by this scenario.
        user = User.createNew(" Carol ", "09111-111-111", "0123")
        # Create a second instance for this comparison or startup check.
        other = User.createNew("Carol", "09111111111", "0123")
        # Check that independent salts produce different hashes for the same PIN.
        self.assertNotEqual(user.pin_hash, other.pin_hash)
        # Check the encoded salted PIN hash has the expected length.
        self.assertEqual(len(user.pin_hash), 97)
        # Check that the correct PIN verifies successfully.
        self.assertTrue(user.checkPin("0123"))
        # Check that an incorrect PIN is rejected.
        self.assertFalse(user.checkPin("9999"))
        # Check that a boolean cannot serve as a PIN.
        self.assertFalse(user.checkPin(True))
        # Rebuild the user from its serialized account data.
        loaded = User.fromDict(user.toDict())
        # Check that the authenticated user is the expected object.
        self.assertIs(login("09111-111-111", "0123", [loaded]), loaded)
        # Check that the matching user is the expected object.
        self.assertIs(find_user("09111-111-111", [loaded]), loaded)
        # Exercise each mobile and pin in this case set.
        for mobile, pin in ((user.mobile_number, "9999"), ("09000000000", "0123")):
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(AuthenticationError):
                # Attempt authentication with these credentials.
                login(mobile, pin, [loaded])

    # Verify that registration validation and duplicates leave list unchanged.
    def test_registration_validation_and_duplicates_leave_list_unchanged(self):
        # List invalid registration inputs, including a duplicate account.
        invalid = [(" ", "09111111111", "1234"), ("Carol", "123", "1234"),
                   ("Carol", "09111111111", "12"), ("Carol", "09111111111", "abcd"),
                   ("Carol", "09111111111", "１２３４"),
                   ("Alice", self.alice.mobile_number, "1234")]
        # Exercise each name and mobile and pin in this case set.
        for name, mobile, pin in invalid:
            # Expect the invalid or failed operation to raise this exception.
            with self.subTest(name=name, mobile=mobile, pin=pin), self.assertRaises(ValueError):
                # Attempt registration with this set of inputs.
                register(name, mobile, pin, self.users)
            # Check that the in-memory user list matches the expected list.
            self.assertEqual(self.users, [self.alice, self.bob])

    # Verify that five failed pins lock correct and incorrect attempts without hashing.
    def test_five_failed_pins_lock_correct_and_incorrect_attempts_without_hashing(self):
        # Freeze the clock so PIN cooldown timing is deterministic.
        with patch("backend.user.time.monotonic", return_value=100):
            # Repeat the operation the required number of times.
            for _ in range(4):
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin("9999"))
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("9999")
            # Replace this dependency temporarily to control the test scenario.
            with patch.object(User, "hashPin") as hasher:
                # Exercise each pin in this case set.
                for pin in ("0123", "9999"):
                    # Expect the operation to raise the specified error and matching message.
                    with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                        # Attempt a PIN check under the current retry state.
                        self.alice.checkPin(pin)
                # Check that the mocked operation was never attempted.
                hasher.assert_not_called()

    # Verify that pin cooldown expires without extending on blocked attempts.
    def test_pin_cooldown_expires_without_extending_on_blocked_attempts(self):
        # Freeze the clock so PIN cooldown timing is deterministic.
        with patch("backend.user.time.monotonic", return_value=100) as clock:
            # Repeat the operation the required number of times.
            for _ in range(4):
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin("9999"))
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(AuthenticationError):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("9999")
            # Advance the mocked monotonic clock to this test time.
            clock.return_value = 129.1
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(AuthenticationError, "1 second\\."):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("0123")
            # Advance the mocked monotonic clock to this test time.
            clock.return_value = 130
            # Check that the PIN check result is true.
            self.assertTrue(self.alice.checkPin("0123"))

    # Verify that cooldown expiry resets failed attempt count even for wrong pin.
    def test_cooldown_expiry_resets_failed_attempt_count_even_for_wrong_pin(self):
        # Freeze the clock so PIN cooldown timing is deterministic.
        with patch("backend.user.time.monotonic", return_value=100) as clock:
            # Repeat the operation the required number of times.
            for _ in range(4):
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin("9999"))
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(AuthenticationError):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("9999")
            # Advance the mocked monotonic clock to this test time.
            clock.return_value = 130
            # Repeat the operation the required number of times.
            for _ in range(4):
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin("9999"))
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("9999")

    # Verify that login and confirmation share failed pin attempts.
    def test_login_and_confirmation_share_failed_pin_attempts(self):
        # Freeze the clock so PIN cooldown timing is deterministic.
        with patch("backend.user.time.monotonic", return_value=100):
            # Repeat the operation the required number of times.
            for _ in range(2):
                # Expect the operation to raise the specified error and matching message.
                with self.assertRaisesRegex(AuthenticationError, "Invalid mobile number or PIN"):
                    # Attempt authentication with these credentials.
                    login(self.alice.mobile_number, "9999", self.users)
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin("9999"))
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                # Attempt authentication with these credentials.
                login(self.alice.mobile_number, "9999", self.users)
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("0123")
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                # Attempt authentication with these credentials.
                login(self.alice.mobile_number, "0123", self.users)
            # Check that the authenticated user is the expected object.
            self.assertIs(login(self.bob.mobile_number, "0123", self.users), self.bob)

    # Verify that successful pin check resets previous failures.
    def test_successful_pin_check_resets_previous_failures(self):
        # Freeze the clock so PIN cooldown timing is deterministic.
        with patch("backend.user.time.monotonic", return_value=100):
            # Repeat the operation the required number of times.
            for _ in range(4):
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin("9999"))
            # Check that the authenticated user is the expected object.
            self.assertIs(login(self.alice.mobile_number, "0123", self.users), self.alice)
            # Repeat the operation the required number of times.
            for _ in range(4):
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin("9999"))
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(AuthenticationError):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("9999")

    # Verify that malformed pin attempts count towards cooldown.
    def test_malformed_pin_attempts_count_towards_cooldown(self):
        # Freeze the clock so PIN cooldown timing is deterministic.
        with patch("backend.user.time.monotonic", return_value=100):
            # Exercise each pin in this case set.
            for pin in (True, None, "", "12345"):
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin(pin))
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(AuthenticationError, "30 seconds"):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("abcd")

    # Verify that retry guard is object local and not serialized.
    def test_retry_guard_is_object_local_and_not_serialized(self):
        # Freeze the clock so PIN cooldown timing is deterministic.
        with patch("backend.user.time.monotonic", return_value=100):
            # Repeat the operation the required number of times.
            for _ in range(4):
                # Check that the PIN check result is false.
                self.assertFalse(self.alice.checkPin("9999"))
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(AuthenticationError):
                # Attempt a PIN check under the current retry state.
                self.alice.checkPin("9999")
            # Check that the serialized field names matches the result.
            self.assertEqual(set(self.alice.toDict()), {"name", "mobile_number", "pin_hash", "balance"})
            # Reconstruct the user without transient retry state.
            reloaded = User.fromDict(self.alice.toDict())
            # Check that the PIN check result is true.
            self.assertTrue(reloaded.checkPin("0123"))

    # Verify that registration persists authentication.
    def test_registration_persists_authentication(self):
        # Register Carol and retain the newly saved user.
        user = storage.register_and_save("Carol", "09111111111", "1234", self.users)
        # Check that balance matches the exact decimal value.
        self.assertEqual(user.balance, Decimal(0))
        # Reload the saved accounts to check persistence.
        loaded = storage.load_users()
        # Check that name matches 'Carol'.
        self.assertEqual(login(user.mobile_number, "1234", loaded).name, "Carol")

    # Verify that registration rolls back when save fails.
    def test_registration_rolls_back_when_save_fails(self):
        # Keep the original data for preservation checks.
        original = self.users_path.read_bytes()
        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.os, "replace", side_effect=OSError("blocked")):
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(storage.StorageError):
                # Register the test account and persist it.
                storage.register_and_save("Carol", "09111111111", "1234", self.users)
        # Check that the in-memory user list matches the expected list.
        self.assertEqual(self.users, [self.alice, self.bob])
        # Check that the exact user-file contents matches original.
        self.assertEqual(self.users_path.read_bytes(), original)

    # Verify that decimal arithmetic has no fractional cent drift.
    def test_decimal_arithmetic_has_no_fractional_cent_drift(self):
        # Create the account used by this scenario.
        user = User("Alice", self.alice.mobile_number, self.pin_hash)
        # Deposit the test amount into the user balance.
        user.deposit(0.1)
        # Deposit the test amount into the user balance.
        user.deposit(0.2)
        # Check that balance matches the exact decimal value.
        self.assertEqual(user.balance, Decimal("0.3"))
        # Withdraw the test amount from the user balance.
        user.withdraw("0.30")
        # Check that balance matches the exact decimal value.
        self.assertEqual(user.balance, Decimal(0))
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(InsufficientFundsError):
            # Withdraw the test amount from the user balance.
            user.withdraw("0.01")
        # Check that balance matches the exact decimal value.
        self.assertEqual(user.balance, Decimal(0))

    # Verify that confirmations accept explicit sequence and optional sequence.
    def test_confirmations_accept_explicit_sequence_and_optional_sequence(self):
        # Exercise each confirm and details in this case set.
        for confirm, details in self.samples():
            # Report failures separately for this combination of inputs.
            with self.subTest(confirm=confirm.__name__):
                # Confirm the sample transaction with a predictable sequence number.
                receipt = confirm(details, sequence_value=42)
                # Check that the status value matches 'Success'.
                self.assertEqual(receipt["Status"], "Success")
                # Check that the transaction-number suffix is true.
                self.assertTrue(receipt["Transaction Number"].endswith("000000042"))
                # Check that the amount value matches 1.25.
                self.assertEqual(receipt["Amount"], 1.25)
                # Check that the transaction  number value differs from the transaction  number value.
                self.assertNotEqual(confirm(details)["Transaction Number"], confirm(details)["Transaction Number"])

    # Verify that all payment categories and case normalization.
    def test_all_payment_categories_and_case_normalization(self):
        # Exercise each category and subcategories in this case set.
        for category, subcategories in PAYMENT_STRUCTURE.items():
            # Exercise each subcategory in this case set.
            for subcategory in subcategories:
                # Report failures separately for this combination of inputs.
                with self.subTest(category=category, subcategory=subcategory):
                    # Prepare the receipt data or capture the confirmed receipt.
                    receipt = confirm_payment(payment_details(
                        category.upper(), subcategory.upper(), "Biller", "Ref", "2.00"))
                    # Check that the status value matches 'Success'.
                    self.assertEqual(receipt["Status"], "Success")
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(ValueError):
            # Validate and confirm the payment details.
            confirm_payment(payment_details("Bank", "water", "Biller", "Ref", 2))

    # Verify that all confirmations reject invalid amounts.
    def test_all_confirmations_reject_invalid_amounts(self):
        # Cover invalid, non-finite, and unsafe-precision amounts.
        amounts = [True, False, None, 0, -1, "", " ", "NaN", float("nan"),
                   "Infinity", float("inf"), float("-inf"), "1.001", Decimal("0.001"),
                   "1.000", "9007199254740992.01", Decimal("1e1000")]
        # Exercise each confirm and details in this case set.
        for confirm, details in self.samples():
            # Exercise each amount in this case set.
            for amount in amounts:
                # Report failures separately for this combination of inputs.
                with self.subTest(confirm=confirm.__name__, amount=repr(amount)):
                    # Expect the invalid or failed operation to raise this exception.
                    with self.assertRaises(ValueError):
                        # Validate and confirm the transaction details.
                        confirm(replace(details, amount=amount))

    # Verify that required fields reject whitespace and none.
    def test_required_fields_reject_whitespace_and_none(self):
        # Exercise each confirm and details in this case set.
        for confirm, details in self.samples():
            # Exercise each field in this case set.
            for field in details.__dataclass_fields__:
                # Leave amount validation to the separate amount tests.
                if field == "amount":
                    # Skip the amount field in this required-text-field check.
                    continue
                # Exercise each value in this case set.
                for value in ("  ", None):
                    # Report failures separately for this combination of inputs.
                    with self.subTest(confirm=confirm.__name__, field=field, value=value):
                        # Expect the invalid or failed operation to raise this exception.
                        with self.assertRaises(ValueError):
                            # Validate and confirm the transaction details.
                            confirm(replace(details, **{field: value}))

    # Verify that deposit withdraw payment persist receipts and history.
    def test_deposit_withdraw_payment_persist_receipts_and_history(self):
        # Deposit money and capture the saved receipt.
        deposit = storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", "0.10"), self.users)
        # Capture the saved withdrawal receipt.
        withdrawal = storage.withdraw_and_save(
            self.alice, withdraw_details("ATM", "Alice", "123", "0.20"), self.users)
        # Capture the saved payment receipt.
        payment = storage.pay_and_save(
            self.alice, payment_details("Bills", "water", "Water Co", "123", "1.25"), self.users)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances("98.65")
        # Load this account's saved transaction history.
        history = storage.get_transactions(self.alice.mobile_number)
        # Check that the collected values equal the expected list.
        self.assertEqual([record["type"] for record in history], ["deposit", "withdrawal", "payment"])
        # Exercise each index and receipt in this case set.
        for index, receipt in enumerate((deposit, withdrawal, payment), 1):
            # Check that the status value matches 'Success'.
            self.assertEqual(receipt["Status"], "Success")
            # Check that the transaction-number suffix is true.
            self.assertTrue(receipt["Transaction Number"].endswith(f"{index:09d}"))
        # Check that the account history matches an empty list.
        self.assertEqual(storage.get_transactions(self.bob.mobile_number), [])

    # Verify that send updates both accounts and both histories.
    def test_send_updates_both_accounts_and_both_histories(self):
        # Send money and capture the transfer receipt.
        receipt = storage.send_and_save(
            self.alice, account_details("09987-654-321", " bob ", "12.34"), self.users)
        # Check that the status value matches 'Success'.
        self.assertEqual(receipt["Status"], "Success")
        # Check both the in-memory balances and the saved balances.
        self.assert_balances("87.66", "37.34")
        # Load the sender's saved history.
        sent = storage.get_transactions(self.alice.mobile_number)
        # Load the recipient's saved history.
        received = storage.get_transactions(self.bob.mobile_number)
        # Check that the type value matches 'send'.
        self.assertEqual(sent[0]["type"], "send")
        # Check that the type value matches 'receive'.
        self.assertEqual(received[0]["type"], "receive")
        # Check that the related transaction id value matches the transaction id value.
        self.assertEqual(received[0]["related_transaction_id"], sent[0]["transaction_id"])
        # Check that sending and receiving consumed two transaction IDs.
        self.assertEqual(storage.next_transaction_id(), 3)

    # Verify that send rejects unknown self mismatched or blank recipient.
    def test_send_rejects_unknown_self_mismatched_or_blank_recipient(self):
        # Define the inputs and expected targets for each case.
        cases = [("09000000000", "Nobody"), (self.alice.mobile_number, "Alice"),
                 (self.bob.mobile_number, "Not Bob"), (self.bob.mobile_number, " ")]
        # Exercise each number and name in this case set.
        for number, name in cases:
            # Expect the invalid or failed operation to raise this exception.
            with self.subTest(number=number, name=name), self.assertRaises(ValueError):
                # Attempt the transfer and both account updates.
                storage.send_and_save(self.alice, account_details(number, name, "1.00"), self.users)
            # Check both the in-memory balances and the saved balances.
            self.assert_balances()
            # Check that the saved transaction history matches an empty list.
            self.assertEqual(storage.load_transactions(), [])

    # Verify that insufficient funds never changes balances or log.
    def test_insufficient_funds_never_changes_balances_or_log(self):
        # Pair each debit operation with an amount above the balance.
        actions = [
            (storage.withdraw_and_save, withdraw_details("ATM", "Alice", "123", "100.01")),
            (storage.pay_and_save, payment_details("Bills", "water", "Water Co", "123", "100.01")),
            (storage.send_and_save, account_details(self.bob.mobile_number, "Bob", "100.01")),
        ]
        # Exercise each action and details in this case set.
        for action, details in actions:
            # Expect the invalid or failed operation to raise this exception.
            with self.subTest(action=action.__name__), self.assertRaises(InsufficientFundsError):
                # Run the selected debit operation.
                action(self.alice, details, self.users)
            # Check both the in-memory balances and the saved balances.
            self.assert_balances()
            # Check that the saved transaction history matches an empty list.
            self.assertEqual(storage.load_transactions(), [])

    # Verify that unregistered active user is rejected.
    def test_unregistered_active_user_is_rejected(self):
        # Copy Alice into an object outside the registered user list.
        detached = User.fromDict(self.alice.toDict())
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(ValueError):
            # Attempt the deposit and its persistent wallet update.
            storage.deposit_and_save(detached, deposit_details("Bank", "Alice", 1), self.users)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances()

    # Verify that invalid transaction leaves existing files untouched.
    def test_invalid_transaction_leaves_existing_files_untouched(self):
        # Seed a transaction so history preservation can be checked.
        storage.add_transaction(self.alice.mobile_number, "deposit", "1.00")
        # Save the original user-file bytes for exact comparison.
        original_users = self.users_path.read_bytes()
        # Save the original history bytes for exact comparison.
        original_transactions = self.transactions_path.read_bytes()
        # Exercise each amount in this case set.
        for amount in (True, "NaN", "0.001", "9007199254740992.01"):
            # Expect the invalid or failed operation to raise this exception.
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                # Attempt the deposit and its persistent wallet update.
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", amount), self.users)
        # Check that the exact user-file contents matches original users.
        self.assertEqual(self.users_path.read_bytes(), original_users)
        # Check that the exact transaction-file contents matches original transactions.
        self.assertEqual(self.transactions_path.read_bytes(), original_transactions)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances()

    # Verify that unrepresentable result rolls back both send balances.
    def test_unrepresentable_result_rolls_back_both_send_balances(self):
        # Put the recipient balance at a precision-sensitive boundary.
        self.bob.balance = "9007199254740992"
        # Persist the current test accounts.
        storage.save_users(self.users)
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(ValueError):
            # Attempt the transfer and both account updates.
            storage.send_and_save(self.alice, account_details(self.bob.mobile_number, "Bob", "0.01"), self.users)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances(bob="9007199254740992")
        # Check that the saved transaction history matches an empty list.
        self.assertEqual(storage.load_transactions(), [])

    # Verify that failed staging never writes partial data.
    def test_failed_staging_never_writes_partial_data(self):
        # Keep the original data for preservation checks.
        original = self.users_path.read_bytes()
        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.tempfile, "mkstemp", side_effect=OSError("disk full")):
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(storage.StorageError):
                # Attempt the deposit and its persistent wallet update.
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances()
        # Check that the exact user-file contents matches original.
        self.assertEqual(self.users_path.read_bytes(), original)
        # Check that this file was not created or was removed.
        self.assertFalse(self.transactions_path.exists())

    # Verify that failed second stage cleans first temp file.
    def test_failed_second_stage_cleans_first_temp_file(self):
        # Keep the real temporary-file creator for the mock.
        real_mkstemp = tempfile.mkstemp
        # Start the mock call counter at zero.
        calls = 0

        # Simulate failure only while creating the second staging file.
        def fail_second_stage(*args, **kwargs):
            # Update the counter owned by the enclosing test.
            nonlocal calls
            # Count this call to the mocked function.
            calls += 1
            # Apply this failure or special case only when the condition matches.
            if calls == 2:
                # Simulate the storage failure expected by this test.
                raise OSError("disk full")
            # Delegate unaffected calls to the real implementation.
            return real_mkstemp(*args, **kwargs)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.tempfile, "mkstemp", side_effect=fail_second_stage):
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(storage.StorageError):
                # Attempt the deposit and its persistent wallet update.
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances()
        # Check that staging cleanup left no temporary files behind.
        self.assertEqual(list(Path(self.directory.name).glob("*.tmp")), [])

    # Verify that failed first replace rolls back memory without log.
    def test_failed_first_replace_rolls_back_memory_without_log(self):
        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.os, "replace", side_effect=OSError("locked")):
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(storage.StorageError):
                # Attempt the deposit and its persistent wallet update.
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances()
        # Check that the saved transaction history matches an empty list.
        self.assertEqual(storage.load_transactions(), [])

    # Verify that failed log replace restores exact original users and log.
    def test_failed_log_replace_restores_exact_original_users_and_log(self):
        # Seed a transaction so history preservation can be checked.
        storage.add_transaction(self.alice.mobile_number, "deposit", "1.00")
        # Save the original user-file bytes for exact comparison.
        original_users = self.users_path.read_bytes()
        # Save the original history bytes for exact comparison.
        original_transactions = self.transactions_path.read_bytes()
        # Keep the real file replacement function for the mock.
        real_replace = os.replace

        # Fail history replacement while allowing other replacements.
        def fail_log(source, destination):
            # Apply this failure or special case only when the condition matches.
            if destination == str(self.transactions_path):
                # Simulate the storage failure expected by this test.
                raise OSError("log locked")
            # Delegate unaffected calls to the real implementation.
            return real_replace(source, destination)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.os, "replace", side_effect=fail_log):
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(storage.StorageError, "balances were restored"):
                # Attempt the transfer and both account updates.
                storage.send_and_save(
                    self.alice, account_details(self.bob.mobile_number, "Bob", 1), self.users)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances()
        # Check that the exact user-file contents matches original users.
        self.assertEqual(self.users_path.read_bytes(), original_users)
        # Check that the exact transaction-file contents matches original transactions.
        self.assertEqual(self.transactions_path.read_bytes(), original_transactions)
        # Check that staging cleanup left no temporary files behind.
        self.assertEqual(list(Path(self.directory.name).glob("*.tmp")), [])
        # Check that this file was not created or was removed.
        self.assertFalse(Path(storage._pending_file()).exists())

    # Verify that failed log replace restores missing users file.
    def test_failed_log_replace_restores_missing_users_file(self):
        # Remove the temporary users file to test missing-file behavior.
        self.users_path.unlink()
        # Keep the real file replacement function for the mock.
        real_replace = os.replace

        # Fail history replacement while allowing other replacements.
        def fail_log(source, destination):
            # Apply this failure or special case only when the condition matches.
            if destination == str(self.transactions_path):
                # Simulate the storage failure expected by this test.
                raise OSError("log locked")
            # Delegate unaffected calls to the real implementation.
            return real_replace(source, destination)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.os, "replace", side_effect=fail_log):
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(storage.StorageError):
                # Attempt the deposit and its persistent wallet update.
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check that Alice's balance matches the exact decimal value.
        self.assertEqual(self.alice.balance, Decimal(100))
        # Check that this file was not created or was removed.
        self.assertFalse(self.users_path.exists())
        # Check that this file was not created or was removed.
        self.assertFalse(self.transactions_path.exists())

    # Verify that rollback failure is explicit and not success.
    def test_rollback_failure_is_explicit_and_not_success(self):
        # Keep the real file replacement function for the mock.
        real_replace = os.replace
        # Start the mock call counter at zero.
        calls = 0

        # Allow the first replacement, then fail saving and recovery.
        def fail_log_and_rollback(source, destination):
            # Update the counter owned by the enclosing test.
            nonlocal calls
            # Count this call to the mocked function.
            calls += 1
            # Apply this failure or special case only when the condition matches.
            if calls > 1:
                # Simulate the storage failure expected by this test.
                raise OSError("disk unavailable")
            # Delegate unaffected calls to the real implementation.
            return real_replace(source, destination)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.os, "replace", side_effect=fail_log_and_rollback):
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
                # Attempt the deposit and its persistent wallet update.
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check that Alice's balance matches the exact decimal value.
        self.assertEqual(self.alice.balance, Decimal(100))
        # Locate the marker that signals an unfinished save.
        marker = Path(storage._pending_file())
        # Check that the expected recovery file still exists.
        self.assertTrue(marker.exists())
        # Locate the recovery backup named by the marker.
        backup = Path(json.loads(marker.read_text(encoding="utf-8"))["original_users_backup"])
        # Check that the expected recovery file still exists.
        self.assertTrue(backup.exists())
        # Check that the balance value matches 100.0.
        self.assertEqual(json.loads(backup.read_text(encoding="utf-8"))[0]["balance"], 100.0)
        # Expect the operation to raise the specified error and matching message.
        with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
            # Attempt to load users from the temporary storage.
            storage.load_users()
        # Expect the operation to raise the specified error and matching message.
        with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
            # Attempt to load transaction history.
            storage.load_transactions()

    # Verify that interrupted save marker blocks loads and registration without changes.
    def test_interrupted_save_marker_blocks_loads_and_registration_without_changes(self):
        # Locate the marker that signals an unfinished save.
        marker = Path(storage._pending_file())
        # Write this test fixture into the temporary file.
        marker.write_text("interrupted", encoding="utf-8")
        # Keep the original data for preservation checks.
        original = self.users_path.read_bytes()
        # Repeat the operation the required number of times.
        for _ in range(2):
            # Exercise each loader in this case set.
            for loader in (storage.load_users, storage.load_transactions):
                # Expect the operation to raise the specified error and matching message.
                with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
                    # Try the current wallet loader.
                    loader()
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(storage.StorageError):
            # Register the test account and persist it.
            storage.register_and_save("Carol", "09111111111", "1234", self.users)
        # Check that the in-memory user list matches the expected list.
        self.assertEqual(self.users, [self.alice, self.bob])
        # Check that the exact user-file contents matches original.
        self.assertEqual(self.users_path.read_bytes(), original)
        # Check that the interrupted-save marker remains unchanged.
        self.assertEqual(marker.read_text(encoding="utf-8"), "interrupted")

    # Verify that process crash between replacements blocks next launch.
    def test_process_crash_between_replacements_blocks_next_launch(self):
        # Prepare a child process that stops during a wallet save.
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
        # Run the crash scenario in a separate Python process.
        crashed = subprocess.run(
            [sys.executable, "-c", script, str(self.users_path), str(self.transactions_path)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10,
        )
        # Check that the child process's exit code matches 17.
        self.assertEqual(crashed.returncode, 17, crashed.stderr)
        # Check that the expected recovery file still exists.
        self.assertTrue(Path(storage._pending_file()).exists())
        # Exercise each loader in this case set.
        for loader in (storage.load_users, storage.load_transactions):
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(storage.StorageError, "manual reconciliation"):
                # Try the current wallet loader.
                loader()
        # Check that the balance value matches 101.
        self.assertEqual(json.loads(self.users_path.read_text(encoding="utf-8"))[0]["balance"], 101)
        # Check that this file was not created or was removed.
        self.assertFalse(self.transactions_path.exists())

    # Verify that marker exists before first wallet replacement.
    def test_marker_exists_before_first_wallet_replacement(self):
        # Keep the real file replacement function for the mock.
        real_replace = os.replace

        # Check that recovery information exists before replacing a file.
        def check_marker(source, destination):
            # Check that the expected recovery file still exists.
            self.assertTrue(Path(storage._pending_file()).exists())
            # Delegate unaffected calls to the real implementation.
            return real_replace(source, destination)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.os, "replace", side_effect=check_marker):
            # Attempt the deposit and its persistent wallet update.
            storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check that this file was not created or was removed.
        self.assertFalse(Path(storage._pending_file()).exists())
        # Check both the in-memory balances and the saved balances.
        self.assert_balances("101")

    # Verify that failed marker creation never changes balances or data.
    def test_failed_marker_creation_never_changes_balances_or_data(self):
        # Keep the real file opener for unaffected paths.
        real_open = open

        # Block marker creation while allowing unrelated file access.
        def fail_marker(filename, *args, **kwargs):
            # Apply this failure or special case only when the condition matches.
            if filename == storage._pending_file():
                # Simulate the storage failure expected by this test.
                raise PermissionError("marker blocked")
            # Delegate unaffected calls to the real implementation.
            return real_open(filename, *args, **kwargs)

        # Replace this dependency temporarily to control the test scenario.
        with patch("builtins.open", side_effect=fail_marker):
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(storage.StorageError):
                # Attempt the deposit and its persistent wallet update.
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check both the in-memory balances and the saved balances.
        self.assert_balances()
        # Check that the saved transaction history matches an empty list.
        self.assertEqual(storage.load_transactions(), [])

    # Verify that marker cleanup failure reports committed data and locks wallet.
    def test_marker_cleanup_failure_reports_committed_data_and_locks_wallet(self):
        # Keep the real file remover for unaffected paths.
        real_remove = os.remove

        # Block marker removal while allowing other cleanup.
        def fail_marker_remove(filename):
            # Apply this failure or special case only when the condition matches.
            if filename == storage._pending_file():
                # Simulate the storage failure expected by this test.
                raise PermissionError("marker locked")
            # Delegate unaffected calls to the real implementation.
            return real_remove(filename)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.os, "remove", side_effect=fail_marker_remove):
            # Expect the operation to raise the specified error and matching message.
            with self.assertRaisesRegex(storage.StorageError, "Transaction was saved") as failure:
                # Attempt the deposit and its persistent wallet update.
                storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check that the committed-data flag is true.
        self.assertTrue(failure.exception.committed)
        # Check that Alice's balance matches the exact decimal value.
        self.assertEqual(self.alice.balance, Decimal(101))
        # Check that the balance value matches 101.
        self.assertEqual(json.loads(self.users_path.read_text(encoding="utf-8"))[0]["balance"], 101)
        # Check that the number of items matches 1.
        self.assertEqual(len(json.loads(self.transactions_path.read_text(encoding="utf-8"))), 1)
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(storage.StorageError):
            # Attempt to load users from the temporary storage.
            storage.load_users()
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(storage.StorageError):
            # Attempt to load transaction history.
            storage.load_transactions()

    # Verify that rollback marker cleanup failure keeps original balances and locks wallet.
    def test_rollback_marker_cleanup_failure_keeps_original_balances_and_locks_wallet(self):
        # Keep the real file replacement function for the mock.
        real_replace = os.replace
        # Keep the real file remover for unaffected paths.
        real_remove = os.remove
        # Keep the original data for preservation checks.
        original = self.users_path.read_bytes()

        # Fail history replacement while allowing other replacements.
        def fail_log(source, destination):
            # Apply this failure or special case only when the condition matches.
            if destination == str(self.transactions_path):
                # Simulate the storage failure expected by this test.
                raise OSError("log locked")
            # Delegate unaffected calls to the real implementation.
            return real_replace(source, destination)

        # Block marker removal while allowing other cleanup.
        def fail_marker_remove(filename):
            # Apply this failure or special case only when the condition matches.
            if filename == storage._pending_file():
                # Simulate the storage failure expected by this test.
                raise PermissionError("marker locked")
            # Delegate unaffected calls to the real implementation.
            return real_remove(filename)

        # Replace this dependency temporarily to control the test scenario.
        with patch.object(storage.os, "replace", side_effect=fail_log):
            # Replace this dependency temporarily to control the test scenario.
            with patch.object(storage.os, "remove", side_effect=fail_marker_remove):
                # Expect the operation to raise the specified error and matching message.
                with self.assertRaisesRegex(storage.StorageError, "Balances were restored"):
                    # Attempt the deposit and its persistent wallet update.
                    storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
        # Check that Alice's balance matches the exact decimal value.
        self.assertEqual(self.alice.balance, Decimal(100))
        # Check that the exact user-file contents matches original.
        self.assertEqual(self.users_path.read_bytes(), original)
        # Check that the expected recovery file still exists.
        self.assertTrue(Path(storage._pending_file()).exists())

    # Verify that corrupt users remain in place and block repeated launch and save.
    def test_corrupt_users_remain_in_place_and_block_repeated_launch_and_save(self):
        # Exercise each content in this case set.
        for content in (b"{bad json", b"\xff", b"{}", b"[{}]"):
            # Report failures separately for this combination of inputs.
            with self.subTest(content=content):
                # Write deliberately invalid bytes into the temporary file.
                self.users_path.write_bytes(content)
                # Repeat the operation the required number of times.
                for _ in range(2):
                    # Expect the invalid or failed operation to raise this exception.
                    with self.assertRaises(storage.StorageError):
                        # Attempt to load users from the temporary storage.
                        storage.load_users()
                # Expect the invalid or failed operation to raise this exception.
                with self.assertRaises(storage.StorageError):
                    # Attempt the deposit and its persistent wallet update.
                    storage.deposit_and_save(self.alice, deposit_details("Bank", "Alice", 1), self.users)
                # Check that the exact user-file contents matches content.
                self.assertEqual(self.users_path.read_bytes(), content)
                # Check that this file was not created or was removed.
                self.assertFalse(Path(str(self.users_path) + ".bak").exists())
                # Check that Alice's balance matches the exact decimal value.
                self.assertEqual(self.alice.balance, Decimal(100))

    # Verify that corrupt log blocks transactions without debit.
    def test_corrupt_log_blocks_transactions_without_debit(self):
        # Exercise each content in this case set.
        for content in (b"[", b"{}", b"[{}]"):
            # Report failures separately for this combination of inputs.
            with self.subTest(content=content):
                # Write deliberately invalid bytes into the temporary file.
                self.transactions_path.write_bytes(content)
                # Repeat the operation the required number of times.
                for _ in range(2):
                    # Expect the invalid or failed operation to raise this exception.
                    with self.assertRaises(storage.StorageError):
                        # Attempt the withdrawal and its persistent wallet update.
                        storage.withdraw_and_save(
                            self.alice, withdraw_details("ATM", "Alice", "123", 1), self.users)
                # Check that the exact transaction-file contents matches content.
                self.assertEqual(self.transactions_path.read_bytes(), content)
                # Check both the in-memory balances and the saved balances.
                self.assert_balances()

    # Verify that malformed balances and duplicate users fail closed.
    def test_malformed_balances_and_duplicate_users_fail_closed(self):
        # Keep the original data for preservation checks.
        original = [user.toDict() for user in self.users]
        # Exercise each value in this case set.
        for value in (-1, True, float("nan"), float("inf"), 1.001, "9007199254740992.01"):
            # Replace one stored balance with the current invalid value.
            data = [dict(original[0], balance=value), original[1]]
            # Write this test fixture into the temporary file.
            self.users_path.write_text(json.dumps(data), encoding="utf-8")
            # Expect the invalid or failed operation to raise this exception.
            with self.subTest(value=value), self.assertRaises(storage.StorageError):
                # Attempt to load users from the temporary storage.
                storage.load_users()
        # Write this test fixture into the temporary file.
        self.users_path.write_text(json.dumps([original[0], original[0]]), encoding="utf-8")
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(storage.StorageError):
            # Attempt to load users from the temporary storage.
            storage.load_users()

    # Verify that malformed transaction records fail closed.
    def test_malformed_transaction_records_fail_closed(self):
        # Start with a valid transaction record to corrupt one field at a time.
        record = {"transaction_id": 1, "mobile_number": self.alice.mobile_number,
                  "type": "deposit", "amount": 1.0, "date": "2026-10-18"}
        # Exercise each field and value in this case set.
        for field, value in (("transaction_id", True), ("transaction_id", 0), ("amount", "NaN"),
                             ("amount", 1.001), ("type", " "), ("date", "bad"),
                             ("mobile_number", "123")):
            # Write this test fixture into the temporary file.
            self.transactions_path.write_text(json.dumps([dict(record, **{field: value})]), encoding="utf-8")
            # Expect the invalid or failed operation to raise this exception.
            with self.subTest(field=field, value=value), self.assertRaises(storage.StorageError):
                # Attempt to load transaction history.
                storage.load_transactions()
        # Write this test fixture into the temporary file.
        self.transactions_path.write_text(json.dumps([record, record]), encoding="utf-8")
        # Expect the invalid or failed operation to raise this exception.
        with self.assertRaises(storage.StorageError):
            # Attempt to load transaction history.
            storage.load_transactions()

    # Verify that read oserror is wrapped.
    def test_read_oserror_is_wrapped(self):
        # Replace this dependency temporarily to control the test scenario.
        with patch("builtins.open", side_effect=PermissionError("blocked")):
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(storage.StorageError):
                # Attempt to load users from the temporary storage.
                storage.load_users()
            # Expect the invalid or failed operation to raise this exception.
            with self.assertRaises(storage.StorageError):
                # Attempt to read the account history.
                storage.get_transactions(self.alice.mobile_number)

    # Verify that missing files are read without creating wallet data.
    def test_missing_files_are_read_without_creating_wallet_data(self):
        # Remove the temporary users file to test missing-file behavior.
        self.users_path.unlink()
        # Check that the saved users matches an empty list.
        self.assertEqual(storage.load_users(), [])
        # Check that the saved transaction history matches an empty list.
        self.assertEqual(storage.load_transactions(), [])
        # Check that this file was not created or was removed.
        self.assertFalse(self.users_path.exists())
        # Check that this file was not created or was removed.
        self.assertFalse(self.transactions_path.exists())

    # Verify that cli passes raw amount text to backend.
    def test_cli_passes_raw_amount_text_to_backend(self):
        # Load the command-line interface module under test.
        cli = importlib.import_module("cli")
        # Replace this dependency temporarily to control the test scenario.
        with patch("builtins.input", side_effect=["Bank", "9007199254740992.01"]):
            # Replace this dependency temporarily to control the test scenario.
            with patch.object(storage, "deposit_and_save", return_value={}) as save:
                # Run the CLI deposit prompt with mocked input.
                cli.do_deposit(self.alice, self.users)
        # Check that amount matches '9007199254740992.01'.
        self.assertEqual(save.call_args.args[1].amount, "9007199254740992.01")

    # Verify that cli transaction menu catches storage error.
    def test_cli_transaction_menu_catches_storage_error(self):
        # Load the command-line interface module under test.
        cli = importlib.import_module("cli")
        # Create a failing action for the CLI error-handling check.
        action = unittest.mock.Mock(side_effect=storage.StorageError("disk unavailable"))
        # Replace this dependency temporarily to control the test scenario.
        with patch.dict(cli.ACTIONS, {"1": action}, clear=True):
            # Replace this dependency temporarily to control the test scenario.
            with patch("builtins.input", side_effect=["1", "0"]), patch("builtins.print") as printer:
                # Run the CLI transaction menu with scripted input.
                cli.user_menu(self.alice, self.users)
        # Check that whether any captured message matches is true.
        self.assertTrue(any("Error: disk unavailable" in str(call) for call in printer.call_args_list))

    # Verify that cli registration and login use hidden pin prompts.
    def test_cli_registration_and_login_use_hidden_pin_prompts(self):
        # Load the command-line interface module under test.
        cli = importlib.import_module("cli")
        # Provide scripted answers for registration, login, and exit.
        answers = ["1", "Carol", "09111111111", "2", "09111111111", "0"]
        # Replace this dependency temporarily to control the test scenario.
        with patch("builtins.input", side_effect=answers), patch("builtins.print"):
            # Replace this dependency temporarily to control the test scenario.
            with patch.object(cli.getpass, "getpass", side_effect=["1234", "1234"]) as hidden_pin:
                # Replace this dependency temporarily to control the test scenario.
                with patch.object(cli, "user_menu") as menu:
                    # Run the test suite or CLI entry point.
                    cli.main()
        # Check that registration and login both used hidden PIN prompts.
        self.assertEqual(hidden_pin.call_args_list, [call("4-digit PIN: "), call("PIN: ")])
        # Check that the mocked operation ran exactly once.
        menu.assert_called_once()
        # Check that mobile number matches '09111111111'.
        self.assertEqual(menu.call_args.args[0].mobile_number, "09111111111")
        # Check that name matches 'Carol'.
        self.assertEqual(storage.load_users()[-1].name, "Carol")


# Run the tests when this file is executed directly.
if __name__ == "__main__":
    # Run the test suite or CLI entry point.
    unittest.main()
