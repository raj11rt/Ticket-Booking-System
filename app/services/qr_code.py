import io
import qrcode
import base64

def generate_qr_base64(data: str) -> str:
    """
    Generates a QR code for the given data and returns it as a base64-encoded PNG string.
    This can be easily embedded in HTML emails as <img src="data:image/png;base64,..." />.
    """
    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str
