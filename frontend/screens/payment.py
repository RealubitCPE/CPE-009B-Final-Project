# Import the Qt widgets and layout controls used here.
from PyQt6.QtWidgets import QComboBox

# Import transaction detail validation and formatting helpers.
from backend.transactions import PAYMENT_STRUCTURE, payment_details
# Import the shared transaction form layout and validation.
from frontend.screens.transaction_form import TransactionFormScreen


# Collect bill-payment details with linked category choices.
class PaymentScreen(TransactionFormScreen):
    # Identify this form transaction for confirmation and execution.
    kind = "payment"
    # Set the heading displayed by the shared transaction form.
    title = "Payment"
    # Set the label on the shared form submission button.
    action_text = "Pay"
    # Declare field keys, labels, and example text for the shared form.
    fields = [
        ("category", "Category", ""),
        ("subcategory", "Type", ""),
        ("biller", "Pay To", "Biller name"),
        ("reference", "Account Number", "000-000-000"),
    ]

    # Initialize the screen and its shared application reference.
    def __init__(self, app_main):
        # Initialize the inherited Qt widget or shared form.
        super().__init__(app_main)
        # Keep a named reference to the shared form control.
        self.category_combo = self.inputs["category"]
        # Keep a named reference to the shared form control.
        self.subcategory_combo = self.inputs["subcategory"]
        # Keep a named reference to the shared form control.
        self.biller_input = self.inputs["biller"]
        # Keep a named reference to the shared form control.
        self.account_input = self.inputs["reference"]
        # Keep a named reference to the shared form control.
        self.pay_btn = self.action_btn
        # Refresh payment types when the category changes.
        self.category_combo.currentTextChanged.connect(self.update_subcategories)
        # Initialize payment types for the current category.
        self.update_subcategories(self.category_combo.currentText())

    # Create the control required for this form field.
    def create_input(self, key, placeholder):
        # Use dropdowns for payment category and type.
        if key in ("category", "subcategory"):
            # Create a dropdown for the payment classification.
            combo = QComboBox()
            # Populate category choices from the supported payment structure.
            if key == "category":
                # Populate the dropdown with its available choices.
                combo.addItems(list(PAYMENT_STRUCTURE))
            # Return the control created for this field.
            return combo
        # Use the shared text field for other payment details.
        return super().create_input(key, placeholder)

    # Replace payment types for the selected category.
    def update_subcategories(self, category):
        # Remove payment types from the previous category.
        self.subcategory_combo.clear()
        # Populate the dropdown with its available choices.
        self.subcategory_combo.addItems(PAYMENT_STRUCTURE.get(category, []))

    # Build validated transaction details and confirmation text.
    def build_details(self, values, amount):
        # Validate and assemble the transaction information.
        details = payment_details(
            values["category"], values["subcategory"], values["biller"],
            values["reference"], amount,
        )
        # Prepare the transaction lines shown for confirmation.
        summary = [
            f"Pay to: {details.biller}",
            f"Category: {details.category} / Type: {details.subcategory}",
            f"Account Number: {details.account_reference}",
            f"Amount: PHP {amount:,.2f}",
        ]
        # Pass validated details and display text to confirmation.
        return details, summary
