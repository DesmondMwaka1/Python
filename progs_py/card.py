#Source Code:
from PIL import Image, ImageDraw, ImageFont

# Canvas size
W, H = 900, 1100
img = Image.new("RGB", (W, H), "#fdfcff")  # soft white background
d = ImageDraw.Draw(img)

# Safe font loader
def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()

title_f = font(46)
text_f  = font(32)

# Title (brighter gradient-style color)
d.text((200, 32), "Valentine's Week List 2026", fill="#6c1ce7", font=title_f)

# Card data with BRIGHT pastel colors
cards = [
    ("Rose Day", "Feb 7",       "#ffe6ea"),
    ("Propose Day", "Feb 8",     "#e6f0ff"),
    ("Chocolate Day", "Feb 9",   "#ffe9f3"),
    ("Teddy Day", "Feb 10",     "#e6fff7"),
    ("Promise Day", "Feb 11",   "#fff0e6"),
    ("Hug Day", "Feb 12",        "#fff6dd"),
    ("Kiss Day", "Feb 13",       "#f0e9ff"),
    ("Valentine Day", "Feb 14", "#e6ffe6")
]

y = 120
for name, date,  color in cards:
    # Soft shadow (lighter + realistic)
    d.rounded_rectangle(
        (90, y+8, 830, y+100),
        radius=32,
        fill="#dcdcdc"
    )

    # Card (bright pastel)
    d.rounded_rectangle(
        (80, y, 840, y+92),
        radius=32,
        fill=color
    )

    # Emoji
    # emoji = Image.open(emoji_file).convert("RGBA").resize((52, 52))
    # img.paste(emoji, (115, y+20), emoji)

    # Text
    d.text((190, y+32), name, fill="#222222", font=text_f)
    d.text((680, y+32), date, fill="#444444", font=text_f)

    y += 115

# Watermark (clean & subtle)
d.text((400, 1055), "Source Code : clcoding.com", fill="#999999", font=text_f)

# Save & show
img.save("valentine_week_BRIGHT.png")
img.show()