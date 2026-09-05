"""Двухфакторная аутентификация: TOTP (Google Authenticator / Authy и т.п.)."""

import qrcode
import qrcode.constants
from qrcode.image.svg import SvgPathImage

import pyotp

ISSUER = "Conspectus"


def new_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, username: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER)


def verify(code: str, secret: str) -> bool:
    """Проверяет TOTP-код (допускается ±1 шаг синхронизации)."""
    if not secret:
        return False
    try:
        return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
    except Exception:
        return False


def qr_svg(secret: str, username: str) -> str:
    """SVG-картинка QR-кода для сканирования приложением-аутентификатором."""
    uri = totp_uri(secret, username)
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgPathImage)
    return img.to_string().decode("utf-8")