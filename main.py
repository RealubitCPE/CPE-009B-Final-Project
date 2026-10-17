# Keep the application class available to existing callers and tests.
from frontend.app import EWalletApp, launch


# Start the desktop interface when this launcher runs directly.
if __name__ == "__main__":
    # Create one Qt application and run the wallet window.
    launch()
