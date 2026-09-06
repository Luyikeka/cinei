import io
import qrcode
from qrcode.constants import ERROR_CORRECT_Q
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

URL = "https://luyikeka.github.io/cinei/poster/"
SRC = "/mnt/user-data/uploads/1788732260016_CINEI_ICON_poster_A0_portrait.pdf"
OUT = "/mnt/user-data/outputs"

qr = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, box_size=40, border=2)
qr.add_data(URL); qr.make(fit=True)
qr.make_image(fill_color="#0F3A45", back_color="white").convert("RGB").save(f"{OUT}/CINEI_poster_QR.png")

reader = PdfReader(SRC); page = reader.pages[0]
PW, PH = float(page.mediabox.width), float(page.mediabox.height)
buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(PW, PH))

# --- patch the poster number: Poster 1-42 -> Poster S1_P165 ---
HEADER = Color(15/255, 58/255, 69/255)
LABEL  = Color(0.624, 0.780, 0.824)          # exact colour of the original line
c.setFillColor(HEADER); c.rect(1120, 2988, 145, 28, stroke=0, fill=1)
c.setFillColor(LABEL); c.setFont("Helvetica", 18)
c.drawCentredString(PW/2, 2995.24, "Poster S1_P165")   # original baseline

# --- QR panel in the header, under the DKRZ logo ---
PANEL_R, PANEL_T, PANEL, PAD = 2330.0, 3175.0, 165.0, 9.0
x0, y0 = PANEL_R - PANEL, PANEL_T - PANEL
c.setFillColor(white); c.roundRect(x0, y0, PANEL, PANEL, 10, stroke=0, fill=1)
c.drawImage(ImageReader(f"{OUT}/CINEI_poster_QR.png"), x0+PAD, y0+PAD, PANEL-2*PAD, PANEL-2*PAD)
c.setFillColor(Color(1, 1, 1, alpha=0.85)); c.setFont("Helvetica", 21)
c.drawRightString(PANEL_R, y0-28, "Scan for the full poster PDF")
c.save()

page.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])
w = PdfWriter(); w.add_page(page)
with open(f"{OUT}/CINEI_ICON_poster_A0_portrait_QR.pdf", "wb") as f: w.write(f)
print("ok")
