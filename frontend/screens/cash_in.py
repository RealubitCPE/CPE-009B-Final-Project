# Import transaction detail validation and formatting helpers.
from backend.transactions import deposit_details
# Import the shared transaction form layout and validation.
from frontend.screens.transaction_form import TransactionFormScreen


# Configure the shared form for incoming funds.
class CashInScreen(TransactionFormScreen):
    # Identify this form transaction for confirmation and execution.
    kind = "cash_in"
    # Set the heading displayed by the shared transaction form.
    title = "Cash In"
    # Set the label on the shared form submission button.
    action_text = "Cash In"
    # Declare field keys, labels, and example text for the shared form.
    fields = [("source", "Source", "Bank or cash-in outlet")]

    # Build validated transaction details and confirmation text.
    def build_details(self, values, amount):
        # Read the account currently signed in.
        user = self.main_window.current_user
        # Require a signed-in account for these transaction details.
        if user is None:
            # Report why the requested wallet operation cannot proceed.
            raise ValueError("Log in before making a transaction.")
        # Validate and assemble the transaction information.
        details = deposit_details(values["source"], user.name, amount)
        # Prepare the transaction lines shown for confirmation.
        summary = [
            f"Source: {details.source}", f"Name: {details.account_name}",
            f"Amount: PHP {amount:,.2f}",
        ]
        # Pass validated details and display text to confirmation.
        return details, summary
