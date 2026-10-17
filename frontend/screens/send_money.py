# Import the shared transaction form layout and validation.
from frontend.screens.transaction_form import TransactionFormScreen
# Import transaction detail validation and formatting helpers.
from backend.transactions import account_details


# Configure the shared form for sending funds.
class SendMoneyScreen(TransactionFormScreen):
    # Identify this form transaction for confirmation and execution.
    kind = "send"
    # Set the heading displayed by the shared transaction form.
    title = "Send Money"
    # Set the label on the shared form submission button.
    action_text = "Send"
    # Declare field keys, labels, and example text for the shared form.
    fields = [
        ("number", "Mobile Number", "0917 000 0000"),
        ("name", "Name", "Juan Dela Cruz"),
    ]

    # Build validated transaction details and confirmation text.
    def build_details(self, values, amount):
        # Validate and assemble the transaction information.
        details = account_details(values["number"], values["name"], amount)
        # Prepare the transaction lines shown for confirmation.
        summary = [
            f"Send to: {values['name']}", f"Mobile Number: {values['number']}",
            f"Amount: PHP {amount:,.2f}",
        ]
        # Pass validated details and display text to confirmation.
        return details, summary
