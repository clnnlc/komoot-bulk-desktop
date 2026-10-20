"""Reproducible geometric app icon; Pillow needed only to rebuild assets."""
from pathlib import Path
from PIL import Image, ImageDraw

assets = Path(__file__).parent / 'assets'
assets.mkdir(exist_ok=True)
image = Image.new('RGBA', (1024, 1024))
d = ImageDraw.Draw(image)
d.rounded_rectangle((24, 24, 1000, 1000), radius=228, fill='#174C43')
d.polygon([(160, 642), (390, 260), (620, 642)], fill='#F4F8F5')
d.polygon([(390, 260), (310, 393), (388, 364), (455, 369)], fill='#A5CDC1')
d.rounded_rectangle((620, 306, 720, 650), radius=30, fill='#E7BA65')
d.polygon([(536, 550), (804, 550), (670, 716)], fill='#E7BA65')
d.rounded_rectangle((190, 752, 820, 820), radius=34, fill='#A5CDC1')
image.resize((256, 256), Image.Resampling.LANCZOS).save(assets / 'app.png')
image.resize((256, 256), Image.Resampling.LANCZOS).save(assets / 'app.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
image.resize((64, 64), Image.Resampling.LANCZOS).save(assets / 'brand.png')
