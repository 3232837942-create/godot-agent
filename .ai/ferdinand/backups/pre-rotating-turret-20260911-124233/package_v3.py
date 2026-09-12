from pathlib import Path
import base64,json,shutil,math
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageFilter
OUT=Path(__file__).resolve().parents[2]/'assets'/'3d'/'ferdinand_v3'
ROOT=Path(r'C:\Users\32328\Documents\Codex\2026-09-06\three-js-webgl-brig-html-sea\work')
shutil.copy2(ROOT/'three.min.js',OUT/'three.min.js')
(OUT/'vehicle_data.js').write_text('const VEHICLE_GLB="'+base64.b64encode((OUT/'ferdinand_vehicle.glb').read_bytes()).decode()+'";',encoding='utf-8')
INK='#203d5b'; MUTED='#7e93a8'; RULE='#9badc0'; PAPER='#eef3f9'
def font(size,bold=False):
    return ImageFont.truetype(str(Path('C:/Windows/Fonts')/('consolab.ttf' if bold else 'consola.ttf')),size)
def board(w,h):
    im=Image.new('RGB',(w,h),PAPER);d=ImageDraw.Draw(im)
    for x in range(20,w,22):d.line((x,20,x,h-20),fill='#dee6ef',width=1)
    for y in range(20,h,22):d.line((20,y,w-20,y),fill='#dee6ef',width=1)
    for x in range(20,w,110):d.line((x,20,x,h-20),fill='#c8d4e1',width=1)
    for y in range(20,h,110):d.line((20,y,w-20,y),fill='#c8d4e1',width=1)
    d.rectangle((20,20,w-21,h-21),outline=INK,width=2); d.rectangle((29,29,w-30,h-30),outline=RULE,width=1)
    for i,c in enumerate('ABCDEFGHJKLM'):
        x=75+i*(w-150)/11;d.text((x,32),c,font=font(12),fill=MUTED,anchor='mt')
    return im
def put_render(im,name,rect):
    img=Image.open(OUT/('render_'+name+'.png')).convert('RGBA');box=img.getbbox();img=img.crop(box);img.thumbnail((rect[2]-rect[0],rect[3]-rect[1]),Image.Resampling.LANCZOS)
    x=rect[0]+(rect[2]-rect[0]-img.width)//2;y=rect[1]+(rect[3]-rect[1]-img.height)//2
    im.paste(img,(x,y),img);return (x,y,img.width,img.height,box)
def top(im,subtitle):
    d=ImageDraw.Draw(im);w=im.width
    d.polygon([(75,76),(92,93),(75,110),(58,93)],outline=INK,width=2);d.polygon([(75,85),(83,93),(75,101),(67,93)],outline='#678d99',width=2)
    d.text((113,72),'ARMOUR / FORM STUDIES',font=font(22,True),fill=INK)
    d.text((113,103),'VEHICLE ENGINEERING  /  REFERENCE-LED DESIGN',font=font(13),fill=MUTED)
    d.text((w-65,73),'FERDINAND  /  SD.KFZ.184',font=font(27,True),anchor='ra',fill=INK)
    d.text((w-65,111),subtitle,font=font(13),anchor='ra',fill=MUTED)
def titleblock(im,x,y,w=430,h=160):
    d=ImageDraw.Draw(im);d.rectangle((x,y,x+w,y+h),fill=PAPER,outline=INK,width=2)
    d.text((x+15,y+11),'TITLE / DESIGN STUDY',font=font(11),fill=MUTED)
    d.text((x+15,y+36),'FERDINAND  -  WIDE CHASSIS',font=font(20,True),fill=INK)
    d.text((x+15,y+68),'GENERAL ARRANGEMENT',font=font(18,True),fill=INK)
    d.line((x,y+102,x+w,y+102),fill=RULE,width=1)
    for i,(k,v) in enumerate([('DRAWING','FD-184-03'),('SHEET','01 / V3'),('UNITS','METRES')]):
        xx=x+i*w/3;d.text((xx+13,y+113),k,font=font(10),fill=MUTED);d.text((xx+13,y+133),v,font=font(13,True),fill=INK)
        if i:d.line((xx,y+102,xx,y+h),fill=RULE,width=1)

hero=board(2400,1600);top(hero,'ISOMETRIC STUDY / EARLY TYPE INSPIRED / REV.03')
place=put_render(hero,'iso',(140,185,2310,1445));d=ImageDraw.Draw(hero)
x,y,ww,hh,crop=place
anchors=json.loads((OUT/'drawing_anchors.json').read_text())
def point(k):
    p=anchors[k];px=p[0]*2000-crop[0];py=(1-p[1])*1400-crop[1];return (x+px*ww/(crop[2]-crop[0]),y+py*hh/(crop[3]-crop[1]))
def callout(key,num,end):
    p=point(key);elbow=(end[0]+(65 if end[0]<p[0] else -65),end[1]);d.line([p,elbow,end],fill='#657f98',width=2)
    d.ellipse((p[0]-3,p[1]-3,p[0]+3,p[1]+3),fill=INK)
    d.ellipse((end[0]-15,end[1]-15,end[0]+15,end[1]+15),fill=PAPER,outline=INK,width=2);d.text(end,str(num),font=font(14,True),anchor='mm',fill=INK)
for args in [('casemate',1,(420,420)),('hatch',2,(975,195)),('grille',3,(2020,380)),('mantlet',4,(2120,530)),('wheel',5,(470,1260)),('track',6,(1040,1450)),('rear_drive',7,(160,740)),('muzzle',8,(2230,890))]:callout(*args)
d.rectangle((64,175,525,334),fill=PAPER,outline=INK,width=2);d.text((82,191),'KEY TO ASSEMBLIES',font=font(14,True),fill=INK);d.line((64,220,525,220),fill=RULE)
for i,txt in enumerate(['1  Fixed casemate','2  Hinged crew hatch','3  Engine louvres','4  Armored mantlet','5  Paired road wheels','6  640 mm track shoes','7  Rear drive sprocket','8  Double muzzle brake']):
    d.text((82+(i%2)*225,237+(i//2)*22),txt,font=font(12),fill=INK)
titleblock(hero,1890,1390,440,160)
d.text((65,1510),'ORTHOGRAPHIC PROJECTION   /   6 ROAD WHEELS PER SIDE   /   106 TRACK LINKS PER SIDE',font=font(14),fill=INK)
d.text((65,1540),'ARTISTIC INTERPRETATION FROM SUPPLIED REFERENCES - NOT A MEASURED RESTORATION',font=font(11),fill=MUTED)
hero.save(OUT/'ferdinand_drawing.png')

sheet=board(2400,1800);top(sheet,'ORTHOGRAPHIC PLATES / SAME MODEL / REV.03');d=ImageDraw.Draw(sheet)
rects=[('side',(60,180,1370,860),'01 / SIDE ELEVATION'),('top',(60,900,1370,1640),'02 / PLAN'),('front',(1420,200,2330,895),'03 / FRONT'),('rear',(1420,950,2330,1640),'04 / REAR')]
for name,rect,label in rects:
    put_render(sheet,name,rect);d.text((rect[0]+18,rect[1]+7),label,font=font(17,True),fill=INK)
d.line((1395,170,1395,1660),fill=RULE);d.line((60,880,2330,880),fill=RULE)
d.text((65,1725),'FD-184-03    /    WIDE CHASSIS + 640 mm TRACK SHOES    /    SOURCE: BLENDER MASTER',font=font(17),fill=INK)
sheet.save(OUT/'ferdinand_four_views.png')

# Neutral-background close views are useful outside the annotated drawing.
for name in ('iso','rear_iso','side','top','front','rear','hatches','fire'):
    if not (OUT/('render_'+name+'.png')).exists(): continue
    img=Image.open(OUT/('render_'+name+'.png')).convert('RGBA');im=Image.new('RGB',img.size,PAPER);im.paste(img,(0,0),img);im.save(OUT/('view_'+name+'.png'))
print('PACKAGE_COMPLETE',OUT)
