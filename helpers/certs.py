from datetime import datetime
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


def generate_certificate(username, register_date: datetime, level):
    img = Image.open('certs/template.jpg')

    I1 = ImageDraw.Draw(img)

    # Load a font
    font_title = ImageFont.truetype("Amiri-Regular.ttf", 80)
    font_names = ImageFont.truetype("Amiri-Regular.ttf", 20)
    font_2 = ImageFont.truetype("Amiri-Regular.ttf", 22)
    font_2_bold = ImageFont.truetype("NotoSerif-Italic.ttf", 18)

    # Add NX level
    I1.text((378, 70), level, fill=(0, 0, 0), font=font_title)

    # Add user name
    I1.text((202, 370), username, fill=(0, 0, 0), font=font_names)

    # Add register date in ajr
    complete_register_date = register_date.strftime("%Y-%m-%d")
    I1.text((202, 440), complete_register_date,
            fill=(0, 0, 0), font=font_names)

    # Add current year
    current_year = datetime.now().year
    I1.text((268, 563), str(current_year), fill=(0, 0, 0), font=font_names)

    # Add current month always with 2 digits
    current_month = datetime.now().month
    I1.text((330, 563), f"{current_month:02d}",
            fill=(0, 0, 0), font=font_names)

    # Add NX level
    I1.text((171, 630), level, fill=(0, 0, 0), font=font_2)

    # Add NX level
    I1.text((222, 742), level, fill=(0, 0, 0), font=font_2_bold)

    # Add date
    short_month_year = datetime.now().strftime("%b %Y")
    I1.text((173, 772), short_month_year, fill=(0, 0, 0), font=font_2_bold)

    # Add date 500 pixels from the right
    complete_date = datetime.now().strftime("%B %d, %Y")
    # Calculate x coordinate taking text width into account
    w = I1.textlength(complete_date, font=font_2_bold)
    x = 679 - w
    I1.text((x, 827), complete_date, fill=(0, 0, 0), font=font_2_bold)

    img.save('temp/certificate.jpg')
