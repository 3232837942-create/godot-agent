"""Compose paper plates from V4's actual Blender renders."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).resolve().parents[2]/'assets'/'3d'/'ferdinand_v4'
PAPER='#eef3f9';INK='#203d5b';RULE='#b3c3d4'
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/consolab.ttf' if bold else 'C:/Windows/Fonts/consola.ttf',n)
def board(w,h):
    im=Image.new('RGB',(w,h),PAPER);d=ImageDraw.Draw(im)
    for x in range(20,w,24):d.line((x,20,x,h-20),fill='#dce5ef')
    for y in range(20,h,24):d.line((20,y,w-20,y),fill='#dce5ef')
    d.rectangle((22,22,w-23,h-23),outline=INK,width=2);d.rectangle((30,30,w-31,h-31),outline=RULE)
    d.text((65,57),'ARMOUR / FORM STUDIES',font=font(24,True),fill=INK)
    d.text((w-65,57),'FD-184R  /  ROTATING TURRET',font=font(29,True),anchor='ra',fill=INK)
    d.text((65,98),'REFERENCE-INSPIRED CONVERSION / DRAFTING SERIES / V4',font=font(14),fill='#758ca2')
    return im
def place(im,name,box):
    src=Image.open(OUT/('render_'+name+'.png')).convert('RGBA');src=src.crop(src.getbbox());src.thumbnail((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
    x=box[0]+(box[2]-box[0]-src.width)//2;y=box[1]+(box[3]-box[1]-src.height)//2;im.paste(src,(x,y),src)
hero=board(2400,1750);place(hero,'iso',(130,165,2260,1580));d=ImageDraw.Draw(hero)
d.rectangle((65,1555,825,1685),fill=PAPER,outline=INK,width=2)
for i,txt in enumerate(['360 DEG ROTATING TURRET / LOW FACETED ARMOR','ROOF MACHINE GUN / TWIN ANTENNAS','SIDE STOWAGE / REAR BASKET / MOVING HATCHES']):d.text((88,1574+i*33),txt,font=font(18,i==0),fill=INK)
d.text((2320,1650),'FD-184R / V4\nFICTIONAL CONVERSION',font=font(20,True),anchor='rd',fill=INK)
hero.save(OUT/'ferdinand_drawing.png')
sheet=board(2400,1900);d=ImageDraw.Draw(sheet)
for name,box,label in [('side',(70,185,1390,945),'01 / SIDE ELEVATION'),('top',(70,1000,1390,1750),'02 / PLAN'),('front',(1450,185,2330,945),'03 / FRONT'),('rear',(1450,1000,2330,1750),'04 / REAR')]:
    place(sheet,name,(box[0],box[1]+40,box[2],box[3]));d.text((box[0]+10,box[1]),label,font=font(20,True),fill=INK)
d.line((1420,160,1420,1790),fill=RULE);d.line((65,973,2335,973),fill=RULE)
d.text((65,1820),'SAME VEHICLE / FOUR ORTHOGRAPHIC VIEWS / METRES / BLENDER MASTER',font=font(18),fill=INK);sheet.save(OUT/'ferdinand_four_views.png')
for path in OUT.glob('render_*.png'):
    src=Image.open(path).convert('RGBA');im=Image.new('RGB',src.size,PAPER);im.paste(src,(0,0),src);im.save(OUT/path.name.replace('render_','view_'))
print('V4_PLATES_OK')
