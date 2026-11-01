# DIGICASH theme: light and warm, using the logo's green and dark brown.
#   brown  #1c0a02   green  #7fdb5a   background  #f7f5f0
STYLE_SHEET = """
QWidget {
    background-color: #f7f5f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    color: #1c0a02;
}

QLabel#titleLabel {
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 20px;
    margin-top: 20px;
}

QLabel#balanceLabel {
    font-size: 32px;
    font-weight: bold;
    background-color: transparent;
    border: none;
}

QLabel#subtitleLabel {
    font-size: 16px;
    color: #5a4a40;
    margin-bottom: 10px;
}

QLabel#errorLabel {
    color: #c0392b;
}

QLineEdit, QComboBox {
    padding: 10px;
    border: 1px solid #d9d2c5;
    border-radius: 4px;
    background-color: #ffffff;
    font-size: 16px;
}

QLineEdit:focus, QComboBox:focus {
    border: 2px solid #3d9a20;
    padding: 9px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d9d2c5;
    selection-background-color: #eaf8e2;
    selection-color: #1c0a02;
    outline: 0;
}

QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {
    background-color: #eaf8e2;
    color: #1c0a02;
}

/* Arrow area: flat, no native dark border, small brown triangle. */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #1c0a02;
    margin-right: 10px;
}

QPushButton.primary {
    background-color: #7fdb5a;
    color: #1c0a02;
    border: none;
    border-radius: 4px;
    padding: 12px;
    font-size: 16px;
    font-weight: bold;
}

QPushButton.primary:hover {
    background-color: #6bc84a;
}

QPushButton.primary:pressed {
    background-color: #5ab83c;
}

QPushButton.primary:disabled {
    background-color: #d4eccb;
    color: #7a6e66;
}

QPushButton.secondary {
    background-color: #ffffff;
    color: #1c0a02;
    border: 1px solid #d9d2c5;
    border-radius: 4px;
    padding: 12px;
    font-size: 16px;
}

QPushButton.secondary:hover {
    background-color: #efeadf;
}

QPushButton.secondary:disabled {
    color: #7a6e66;
}

QPushButton.menuButton {
    background-color: #ffffff;
    color: #1c0a02;
    border: 1px solid #d9d2c5;
    border-radius: 4px;
    padding: 20px;
    font-size: 18px;
    font-weight: bold;
}

QPushButton.menuButton:hover {
    background-color: #eaf8e2;
    border: 1px solid #7fdb5a;
}

QFrame.card {
    background-color: #ffffff;
    border: 1px solid #e3ddd2;
    border-radius: 4px;
    padding: 20px;
}

QFrame.card QLabel {
    background-color: transparent;
    border: none;
}
"""
