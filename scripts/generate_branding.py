"""
Generates high-resolution Cover (1280x720) and Thumbnail (600x600) assets
for CareerPilot AI with glassmorphic styling, glowing cyan accents, and clear typography.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path("assets")
ASSETS_DIR.mkdir(exist_ok=True)

def get_font(size: int, bold: bool = False):
    """Attempts to load a standard system font, falling back to default."""
    font_names = [
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\calibrib.ttf" if bold else "C:\\Windows\\Fonts\\calibri.ttf"
    ]
    for fn in font_names:
        if Path(fn).exists():
            try:
                return ImageFont.truetype(fn, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_cover():
    """Generates 1280x720 Brand Cover Image."""
    width, height = 1280, 720
    img = Image.new("RGBA", (width, height), (11, 15, 25, 255))
    draw = ImageDraw.Draw(img)

    # 1. Subtle Background Gradients & Glows
    for i in range(height):
        # Vertical dark gradient from #0B0F19 to #111827
        ratio = i / height
        r = int(11 * (1 - ratio) + 17 * ratio)
        g = int(15 * (1 - ratio) + 24 * ratio)
        b = int(25 * (1 - ratio) + 39 * ratio)
        draw.line([(0, i), (width, i)], fill=(r, g, b, 255))

    # Cyan Ambient Glow at Top Right
    for radius in range(350, 0, -10):
        alpha = int(18 * (1 - radius / 350))
        draw.ellipse([900 - radius, 150 - radius, 900 + radius, 150 + radius], fill=(6, 182, 212, alpha))

    # Blue Ambient Glow at Bottom Left
    for radius in range(400, 0, -10):
        alpha = int(15 * (1 - radius / 400))
        draw.ellipse([200 - radius, 600 - radius, 200 + radius, 600 + radius], fill=(37, 99, 235, alpha))

    # 2. Main Glass Card Container
    card_x1, card_y1, card_x2, card_y2 = 80, 70, 1200, 650
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=28, fill=(17, 24, 39, 210), outline=(56, 189, 248, 70), width=2)

    # 3. Top Tag / Badge
    tag_x, tag_y = 130, 125
    draw.rounded_rectangle([tag_x, tag_y, tag_x + 320, tag_y + 40], radius=20, fill=(6, 182, 212, 35), outline=(6, 182, 212, 100), width=1)
    tag_font = get_font(16, bold=True)
    draw.text((tag_x + 22, tag_y + 9), "⚡ AUTONOMOUS CAREER COPILOT", font=tag_font, fill=(56, 189, 248, 255))

    # 4. Main Headline
    title_font = get_font(56, bold=True)
    draw.text((130, 185), "CareerPilot AI Pro", font=title_font, fill=(255, 255, 255, 255))

    # 5. Subtitle
    sub_font = get_font(24, bold=False)
    draw.text((130, 260), "The AI Agent that Scores Job Fit & Applies on LinkedIn, Naukri & ATS", font=sub_font, fill=(148, 163, 184, 255))

    # 6. Feature Pills Grid
    features = [
        ("🎯 LLM Match Gate", "Gemini 2.5 Flash scores JD fit (0-100%) against resume"),
        ("⚡ True External Apply", "Autofills Workday, Greenhouse & Lever portals"),
        ("🛡️ Zero-Ban Chrome CDP", "Reuses active browser sessions with zero bot detection"),
        ("🔒 100% Private & Local", "Runs on your laptop - passwords & data never leave")
    ]

    pill_y = 330
    for idx, (title, desc) in enumerate(features):
        px = 130 if idx % 2 == 0 else 660
        py = pill_y if idx < 2 else pill_y + 95

        draw.rounded_rectangle([px, py, px + 500, py + 75], radius=16, fill=(30, 41, 59, 180), outline=(71, 85, 105, 80), width=1)
        draw.text((px + 20, py + 14), title, font=get_font(20, bold=True), fill=(241, 245, 249, 255))
        draw.text((px + 20, py + 42), desc, font=get_font(14, bold=False), fill=(148, 163, 184, 255))

    # 7. Bottom Callout / Pricing
    bottom_y = 550
    draw.rounded_rectangle([130, bottom_y, 450, bottom_y + 55], radius=16, fill=(6, 182, 212, 230))
    draw.text((155, bottom_y + 14), "Instant License Key Included 🚀", font=get_font(18, bold=True), fill=(11, 15, 25, 255))

    badge_font = get_font(16, bold=True)
    draw.text((480, bottom_y + 18), "Works on Windows & Mac | Unlimited Applications", font=badge_font, fill=(148, 163, 184, 255))

    output_path = ASSETS_DIR / "careerpilot_cover.png"
    img.convert("RGB").save(output_path, "PNG", quality=95)
    print(f"Cover saved: {output_path.resolve()}")
    return output_path

def create_thumbnail():
    """Generates 600x600 Brand Square Thumbnail."""
    width, height = 600, 600
    img = Image.new("RGBA", (width, height), (11, 15, 25, 255))
    draw = ImageDraw.Draw(img)

    # Ambient radial gradient
    for radius in range(300, 0, -8):
        alpha = int(22 * (1 - radius / 300))
        draw.ellipse([300 - radius, 250 - radius, 300 + radius, 250 + radius], fill=(6, 182, 212, alpha))

    # Card outline
    draw.rounded_rectangle([30, 30, 570, 570], radius=32, fill=(17, 24, 39, 220), outline=(56, 189, 248, 90), width=2)

    # Center Icon Badge
    draw.rounded_rectangle([210, 110, 390, 290], radius=28, fill=(30, 41, 59, 255), outline=(6, 182, 212, 180), width=3)
    
    # Large ⚡ symbol
    bolt_font = get_font(90, bold=True)
    draw.text((255, 140), "⚡", font=bolt_font, fill=(56, 189, 248, 255))

    # Title
    t_font = get_font(34, bold=True)
    draw.text((170, 330), "CareerPilot AI", font=t_font, fill=(255, 255, 255, 255))

    # Pro Pill
    draw.rounded_rectangle([240, 385, 360, 425], radius=12, fill=(245, 158, 11, 230))
    pro_font = get_font(18, bold=True)
    draw.text((275, 394), "PRO", font=pro_font, fill=(15, 23, 42, 255))

    # Subtext
    sub_font = get_font(16, bold=False)
    draw.text((120, 460), "Autonomous Job Application Agent", font=sub_font, fill=(148, 163, 184, 255))
    
    pill_font = get_font(13, bold=True)
    draw.text((160, 495), "LinkedIn • Naukri • Workday • ATS", font=pill_font, fill=(56, 189, 248, 255))

    output_path = ASSETS_DIR / "careerpilot_thumbnail.png"
    img.convert("RGB").save(output_path, "PNG", quality=95)
    print(f"Thumbnail saved: {output_path.resolve()}")
    return output_path

if __name__ == "__main__":
    create_cover()
    create_thumbnail()

