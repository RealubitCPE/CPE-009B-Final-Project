from PyQt6.QtWidgets import QComboBox

from backend.transactions import deposit_details
from frontend.screens.transaction_form import TransactionFormScreen

# Where money can come from. Edit this list to add or remove choices.
CASH_IN_SOURCES = ["Bank", "Cash-in outlet", "Convenience Store"]


class CashInScreen(TransactionFormScreen):
    kind = "cash_in"
    title = "Cash In"
    action_text = "Cash In"
    fields = [("source", "Source", "Select a source")]

    def __init__(self, app_main):
        """Build the form and start with no source selected."""
        super().__init__(app_main)
        self.source_combo = self.inputs["source"]
        self.source_combo.setCurrentIndex(-1)

    def create_input(self, key, placeholder):
        """Use a dropdown for the source and text fields for anything else."""
        if key == "source":
            combo = QComboBox()
            combo.addItems(CASH_IN_SOURCES)
            combo.setPlaceholderText(placeholder)
            return combo
        return super().create_input(key, placeholder)

    def reset(self):
        """Clear the form and leave the source unselected."""
        super().reset()
        self.source_combo.setCurrentIndex(-1)

    def build_details(self, values, amount):
        """Build cash-in details using the signed-in account name."""
        user = self.main_window.current_user
        if user is None:
            raise ValueError("Log in before making a transaction.")
        details = deposit_details(values["source"], user.name, amount)
        summary = [
            f"Source: {details.source}", f"Name: {details.account_name}",
            f"Amount: PHP {amount:,.2f}",
        ]
        return details, summary
