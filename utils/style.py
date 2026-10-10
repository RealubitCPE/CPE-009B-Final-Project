STYLE_SHEET = """
{
    background-color: #f0f0f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    color: #333333;
}

QLabel#titleLabel {
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 20px;
    margin-top: 20px;
    background: transparent;
}

QLabel#balanceLabel {
    font-size: 32px;
    font-weight: bold;
    background: transparent;
    border: none;
}

QLabel#subtitleLabel {
    font-size: 16px;
    color: #555555;
    margin-bottom: 10px;
    background: transparent;
    border: none;
}

QFrame.card QWidget, QFrame.card QFrame {
    background-color: transparent;
}

QLineEdit, QComboBox {
    padding: 10px;
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: #ffffff;
    font-size: 16px;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #195cbb;
}

QPushButton.primary {
    background-color: #195cbb;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 12px;
    font-size: 16px;
    font-weight: bold;
}

QPushButton.primary:hover {
    background-color: #134896;
}

QPushButton.secondary {
    background-color: #e1e1e1;
    color: #333333;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 12px;
    font-size: 16px;
}

QPushButton.secondary:hover {
    background-color: #d0d0d0;
}

QPushButton.menuButton {
    background-color: #e1e1e1;
    color: #000000;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 20px;
    font-size: 18px;
    font-weight: bold;
}

QPushButton.menuButton:hover {
    background-color: #d0d0d0;
}

QFrame.card {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 20px;
}
"""
