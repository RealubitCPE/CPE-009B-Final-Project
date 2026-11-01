from PyQt6.QtWidgets import QComboBox

from backend.transactions import withdraw_details
from frontend.screens.transaction_form import TransactionFormScreen

# Where money can go. Edit this list to add or remove choices.
CASH_OUT_DESTINATIONS = ["Bank", "Cash-out outlet", "Convenience Store"]


class CashOutScreen(TransactionFormScreen):
    kind = "cash_out"
    title = "Cash Out"
    action_text = "Cash Out"
    fields = [
        ("destination", "Destination", "Select a destination"),
        ("number", "Account Number", "000-000-000"),
    ]

    def __init__(self, app_main):
        """Build the form and start with no destination selected."""
        super().__init__(app_main)
        self.destination_combo = self.inputs["destination"]
        self.destination_combo.setCurrentIndex(-1)

    def create_input(self, key, placeholder):
        """Use a dropdown for the destination and text fields for anything else."""
        if key == "destination":
            combo = QComboBox()
            combo.addItems(CASH_OUT_DESTINATIONS)
            combo.setPlaceholderText(placeholder)
            return combo
        return super().create_input(key, placeholder)

    def reset(self):
        """Clear the form and leave the destination unselected."""
        super().reset()
        self.destination_combo.setCurrentIndex(-1)

    def build_details(self, values, amount):
        """Build withdrawal details using the signed-in account and destination."""
        user = self.main_window.current_user
        if user is None:
            raise ValueError("Log in before making a transaction.")
        details = withdraw_details(values["destination"], user.name, values["number"], amount)
        summary = [
            f"Destination: {details.destination}", f"Name: {details.account_name}",
            f"Account Number: {details.account_number}", f"Amount: PHP {amount:,.2f}",
        ]
        return details, summary
