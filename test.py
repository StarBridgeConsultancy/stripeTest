from fpdf import FPDF
from fpdf.enums import XPos, YPos  # new in fpdf2

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)

pdf.cell(200, 10, text="Hello World", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.output("test.pdf")
