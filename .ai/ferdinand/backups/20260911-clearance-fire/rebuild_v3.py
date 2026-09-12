"""Reference-led Ferdinand study. Blender 5.2; local +X forward, +Z up, metres."""
import bpy, bmesh, math, json, os, bisect, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parents[2] / 'assets' / '3d' / 'ferdinand_v3'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.fps = 30
scene.frame_start, scene.frame_end = 1, 280
bpy.context.preferences.filepaths.save_version = 0

def ink_material(name, base, hatch=True):
    m = bpy.data.materials.new(name); m.diffuse_color = (*base,1); m.use_nodes = True
    ns, ls = m.node_tree.nodes, m.node_tree.links; ns.clear()
    def n(typ): return ns.new(typ)
    def mathn(op,a,b=None):
        q=n('ShaderNodeMath'); q.operation=op
        for i,v in enumerate((a,b)):
            if v is None: continue
            if isinstance(v,(int,float)): q.inputs[i].default_value=v
            else: ls.new(v,q.inputs[i])
        return q.outputs[0]
    geom=n('ShaderNodeNewGeometry'); dot=n('ShaderNodeVectorMath'); dot.operation='DOT_PRODUCT'
    ls.new(geom.outputs['Normal'],dot.inputs[0]); dot.inputs[1].default_value=(.28,-.43,.86)
    shade=mathn('MULTIPLY_ADD',dot.outputs['Value'],.15)
    shade.node.inputs[2].default_value=.83
    mix=n('ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=1
    mix.inputs[1].default_value=(*base,1); ls.new(shade,mix.inputs[2])
    color=mix.outputs[0]
    if hatch:
        tex=n('ShaderNodeTexCoord'); sep=n('ShaderNodeSeparateXYZ'); ls.new(tex.outputs['Window'],sep.inputs[0])
        f=mathn('ADD',mathn('MULTIPLY',sep.outputs['X'],1900),mathn('MULTIPLY',sep.outputs['Y'],1150))
        lines=mathn('LESS_THAN',mathn('ABSOLUTE',mathn('SINE',f)),.13)
        mask=mathn('MULTIPLY',lines,mathn('LESS_THAN',dot.outputs['Value'],.6))
        dark=n('ShaderNodeMixRGB'); ls.new(mathn('MULTIPLY',mask,.62),dark.inputs[0]); ls.new(color,dark.inputs[1]); dark.inputs[2].default_value=(.10,.18,.29,1)
        color=dark.outputs[0]
    em=n('ShaderNodeEmission'); ls.new(color,em.inputs[0]); em.inputs[1].default_value=1
    out=n('ShaderNodeOutputMaterial'); ls.new(em.outputs[0],out.inputs[0]); return m

MATS=[ink_material('Paper armor',(.91,.94,.97)),ink_material('Machined steel',(.72,.80,.88)),ink_material('Deep recess',(.12,.19,.28),False),ink_material('Fastener',(.81,.87,.94)),ink_material('Optical glass',(.26,.44,.56),False)]

def empty(name, p=None, loc=(0,0,0)):
    o=bpy.data.objects.new(name,None); scene.collection.objects.link(o); o.parent=p; o.location=loc; o.empty_display_size=.12; return o
root=empty('FERDINAND_ROOT'); root['variant']='Ferdinand-inspired wide chassis; artistic interpretation'
root['units']='meters'; root['forward_axis']='+X'; root['up_axis']='+Z'
root['design_width_m']=3.72; root['historical_status']='Reference-led proportions; not a certified restoration'
parts={}; animated=[]; track_links=[]; wheel_nodes=[]; hatch_nodes=[]
I=Matrix.Identity(3)
def orient(axis): return Vector((0,0,1)).rotation_difference(Vector(axis).normalized()).to_matrix()

class Mesh:
    def __init__(self,name,p=root,loc=(0,0,0)):
        self.name,self.parent,self.loc=name,p,loc; self.v=[]; self.f=[]; self.mat=[]; self.smooth=[]
    def add(self,verts,faces,mat=0,pos=(0,0,0),rot=None,smooth=False):
        idx=len(self.v); r=rot if rot is not None else I; p=Vector(pos)
        self.v.extend([tuple(r@Vector(v)+p) for v in verts]); self.f.extend([tuple(idx+i for i in f) for f in faces]); self.mat.extend([mat]*len(faces))
        self.smooth.extend(smooth if isinstance(smooth,list) else [smooth]*len(faces)); return self
    def box(self,pos,size,mat=0,rot=None):
        x,y,z=[s/2 for s in size]
        return self.add([(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)],[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat,pos,rot)
    def cyl(self,pos,r,d,mat=0,axis=(0,0,1),N=32,r2=None):
        r2=r if r2 is None else r2
        vs=[(rad*math.cos(i*math.tau/N),rad*math.sin(i*math.tau/N),zz) for zz,rad in ((-d/2,r),(d/2,r2)) for i in range(N)]
        fs=[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]+[tuple(reversed(range(N))),tuple(range(N,2*N))]
        return self.add(vs,fs,mat,pos,orient(axis),[True]*N+[False,False])
    def ring(self,pos,outer,inner,d,mat=0,axis=(0,0,1),N=40):
        vs=[(r*math.cos(i*math.tau/N),r*math.sin(i*math.tau/N),z) for z,r in ((-d/2,outer),(d/2,outer),(-d/2,inner),(d/2,inner)) for i in range(N)]
        fs=[]; sm=[]
        for a,b in ((0,1),(1,3),(3,2),(2,0)):
            for i in range(N): fs.append((a*N+i,a*N+(i+1)%N,b*N+(i+1)%N,b*N+i)); sm.append(a in (0,3))
        return self.add(vs,fs,mat,pos,orient(axis),sm)
    def rod(self,a,b,r=.012,mat=1,N=10):
        a,b=Vector(a),Vector(b); return self.cyl((a+b)/2,r,(b-a).length,mat,b-a,N)
    def path(self,ps,r=.012,mat=1):
        for a,b in zip(ps,ps[1:]): self.rod(a,b,r,mat)
        return self
    def bolt(self,p,axis=(0,0,1),r=.019):
        n=Vector(axis).normalized(); p=Vector(p)
        self.cyl(p+n*.006,r*1.36,.012,1,n,18); self.cyl(p+n*.019,r,.022,3,n,6); return self
    def bolt_circle(self,p,r,count,axis=(0,0,1),size=.017):
        rot=orient(axis)
        for i in range(count):
            a=math.tau*i/count; self.bolt(Vector(p)+rot@Vector((r*math.cos(a),r*math.sin(a),0)),axis,size)
        return self
    def finish(self,bevel=0):
        me=bpy.data.meshes.new(self.name); me.from_pydata(self.v,[],self.f); me.update()
        for m in MATS: me.materials.append(m)
        for po,mi,sm in zip(me.polygons,self.mat,self.smooth): po.material_index=mi; po.use_smooth=sm
        bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(me); bm.free()
        o=bpy.data.objects.new(self.name,me); scene.collection.objects.link(o); o.parent=self.parent; o.location=self.loc
        if bevel:
            mod=o.modifiers.new('Subtle edge machining','BEVEL'); mod.width=bevel; mod.segments=2
        parts[self.name]=o; return o

def shell_ring(x_front,x_rear,y,z): return [(x_front,-y,z),(x_front,y,z),(x_rear,y,z),(x_rear,-y,z)]
def loft(name,lower,upper,p=root,mat=0):
    return Mesh(name,p).add(lower+upper,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat).finish(.008)
def plate(name,ps,normal,thick=.035):
    n=Vector(normal).normalized(); vs=[tuple(Vector(p)+n*s) for s in (-thick/2,thick/2) for p in ps]
    return Mesh(name).add(vs,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]).finish(.005)

# Hull tapers below the wide sponsons; it clears the inner faces of both track belts.
loft('HULL_LOWER',shell_ring(2.88,-2.92,1.10,.48),shell_ring(3.15,-3.15,1.16,1.634))
loft('HULL_SPONSONS',shell_ring(3.15,-3.15,1.46,1.636),shell_ring(2.94,-3.13,1.54,1.68))
loft('DRIVER_NOSE',shell_ring(3.16,2.35,1.12,1.45),shell_ring(2.79,2.36,1.12,1.70))
deck=Mesh('ENGINE_DECK'); deck.box((1.30,0,1.70),(2.04,2.96,.05))
for side in (-1,1):
    yy=side*.99
    deck.box((1.24,yy,1.744),(1.48,.58,.035),1)
    deck.box((1.24,yy,1.764),(1.34,.46,.010),2)
    for i in range(17): deck.box((.59+i*.081,yy,1.80),(.026,.43,.042),0,Matrix.Rotation(.24,3,'Y'))
    for x in (.54,1.94):
        for y in (yy-.235,yy+.235): deck.bolt((x,y,1.77),r=.014)
    deck.box((2.49,side*.70,1.748),(.52,.49,.045)); deck.box((2.49,side*.70,1.777),(.44,.40,.020),1)
    deck.path([(2.50,side*.7-.10,1.80),(2.50,side*.7-.10,1.85),(2.50,side*.7+.10,1.85),(2.50,side*.7+.10,1.80)],.012)
    for xx in (2.30,2.68): deck.cyl((xx,side*.7,1.79),.024,.17,1,(0,1,0),16)
    deck.box((2.85,side*.75,1.71),(.14,.26,.06),1); deck.box((2.924,side*.75,1.722),(.004,.19,.023),4)
deck.box((1.29,0,1.738),(1.51,1.01,.037)); deck.box((1.29,0,1.762),(1.40,.90,.014),1)
for xx in (.66,1.92):
    for yy in (-.38,.38): deck.bolt((xx,yy,1.78),r=.017)
deck.cyl((1.34,0,1.802),.086,.042,1); deck.box((1.34,0,1.83),(.12,.021,.021),3)
deck.finish(.004)

# Casemate walls are separate plates with a real open roof beneath the moving covers.
bz,tz=1.70,2.79; bf,br=.28,-3.12; tf,tr=-.04,-2.94; by,ty=1.52,1.32
for side in (-1,1):
    plate('CASEMATE_'+('L' if side<0 else 'R'),[(bf,side*by,bz),(br,side*by,bz),(tr,side*ty,tz),(tf,side*ty,tz)],(0,side,.184))
front=plate('CASEMATE_FRONT',[(bf,-by,bz),(bf,by,bz),(tf,ty,tz),(tf,-ty,tz)],(1,0,.294))
rear=plate('CASEMATE_REAR',[(br,by,bz),(br,-by,bz),(tr,-ty,tz),(tr,ty,tz)],(-1,0,.165))
roof=Mesh('CASEMATE_ROOF').box((-1.49,0,2.803),(2.90,2.64,.040)).finish(.007)

def bore(obj,pos,r,depth,axis=(0,0,1)):
    cut=Mesh('Temporary cutter',None).cyl(pos,r,depth,0,axis,48).finish()
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Machined aperture','BOOLEAN'); mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cut
    bpy.ops.object.modifier_apply(modifier=mod.name); bpy.data.objects.remove(cut,do_unlink=True); parts.pop('Temporary cutter',None)
bore(front,(.12,0,2.27),.205,1,(1,0,0))
for side in (-1,1): bore(roof,(-1.52,side*.65,2.80),.315,.30)

trim=Mesh('CASEMATE_FITTINGS')
for side in (-1,1):
    n=Vector((0,side,.184)).normalized()
    for zz in (1.76,2.00):
        yy=by+(ty-by)*(zz-bz)/(tz-bz)
        for x in (-2.70,-2.18,-1.61,-.99,-.44): trim.bolt((x,side*yy,zz),n,.018)
    # Welds follow the actual sloped surfaces, not a detached vertical plane.
    trim.rod((br,side*by,bz),(bf,side*by,bz),.011)
    trim.rod((tr,side*ty,tz),(tf,side*ty,tz),.009)
    for x in (-2.68,-.34):
        yy=1.365; trim.path([(x-.07,side*yy,2.59),(x-.07,side*(yy+.055),2.66),(x+.07,side*(yy+.055),2.66),(x+.07,side*yy,2.59)],.016)
    for x in (-2.78,-.25):
        z=2.34; yy=by+(ty-by)*(z-bz)/(tz-bz)
        trim.ring((x,side*(yy+.009),z),.059,.042,.022,1,n,24)
    # Delicate weld stitches on the sloping front and rear plate joins.
    for xx0,xx1 in ((bf,tf),(br,tr)):
        for j in range(34):
            t=(j+.5)/34; xx=xx0+(xx1-xx0)*t; zz=bz+(tz-bz)*t; yy=by+(ty-by)*t
            trim.rod((xx-.012,side*(yy+.010),zz-.004),(xx+.012,side*(yy+.010),zz+.004),.006,1,6)
    trim.cyl((-2.48,side*.98,2.861),.125,.075,0); trim.ring((-2.48,side*.98,2.895),.144,.085,.02,1)
    trim.cyl((-2.48,side*.98,2.855),.097,.038,2)
    trim.box((-.45,side*.82,2.846),(.30,.19,.053),1); trim.box((-.45,side*.82,2.875),(.23,.12,.008),2)
    trim.box((-.45,side*.82,2.889),(.31,.21,.013))
    trim.box((-2.70,side*.3,2.84),(.24,.20,.026),1); trim.bolt((-2.7,side*.3,2.86))
trim.finish(.002)

# Rear escape cover and rear deck fittings.
rd=Mesh('REAR_DETAILS'); axis=Vector((-1,0,.165)).normalized(); rp=Vector((-3.019,0,2.25))
rd.ring(rp,.355,.299,.035,1,axis); rd.cyl(rp+axis*.03,.295,.042,0,axis); rd.bolt_circle(rp+axis*.055,.248,8,axis,.018)
rd.rod((-3.086,-.095,2.245),(-3.086,.095,2.245),.016)
for yy in (-.94,.94):
    rd.cyl((-3.155,yy,1.88),.090,.055,1,axis)
    rd.box((-3.211,yy,1.53),(.055,.24,.17),1)
    rd.path([(-3.23,yy,1.15),(-3.31,yy,1.25),(-3.31,yy,1.45)],.044)
rd.box((-3.24,0,1.27),(.12,1.12,.40),1)
for y in [i*.13 for i in range(-3,4)]: rd.box((-3.309,y,1.28),(.009,.04,.24),2)
rd.finish(.004)

# Two hinged roof lids. Local hinge axes lie on the rim, so no lid sweeps through the roof.
for side in (-1,1):
    tag='L' if side<0 else 'R'; hp=empty('HATCH_'+tag+'_PIVOT',root,(-1.185,side*.65,2.864)); hatch_nodes.append(hp)
    mm=Mesh('HATCH_'+tag,hp); mm.cyl((-.335,0,0),.326,.032); mm.ring((-.335,0,.022),.288,.265,.012,1)
    mm.box((-.335,0,.025),(.43,.055,.034),1)
    mm.path([(-.4,-.075,.033),(-.4,-.075,.100),(-.4,.075,.100),(-.4,.075,.033)],.014)
    for yy in (-.17,.17): mm.cyl((0,yy,0),.032,.12,1,(0,1,0),20)
    mm.finish(.002)
    rim=Mesh('HATCH_'+tag+'_RIM'); rim.ring((-1.52,side*.65,2.839),.346,.315,.044,1); rim.finish()

# Armored mantlet, tapered tube, hollow double-chamber muzzle brake.
traverse=empty('GUN_TRAVERSE_PIVOT',root,(.15,0,2.27)); traverse['limits_deg']='-7.5,7.5'
pitch=empty('GUN_PITCH_PIVOT',traverse); pitch['limits_deg']='-4,14'
recoil=empty('GUN_RECOIL_ROOT',pitch)
gun=Mesh('GUN_MANTLET',pitch); gun.ring((.03,0,0),.335,.202,.14,0,(1,0,0)); gun.cyl((.15,0,0),.252,.21,0,(1,0,0),48,.189); gun.ring((.267,0,0),.198,.136,.035,1,(1,0,0)); gun.bolt_circle((.106,0,0),.289,10,(1,0,0),.019); gun.finish()
bar=Mesh('GUN_BARREL',recoil)
bar.cyl((.47,0,0),.140,.42,1,(1,0,0),48,.124)
bar.cyl((2.40,0,0),.124,3.44,0,(1,0,0),48,.075)
for xx,rr in ((.68,.129),(1.28,.119),(3.94,.081)):
    bar.ring((xx,0,0),rr+.012,rr,.049,1,(1,0,0))
bar.ring((4.22,0,0),.081,.046,.20,1,(1,0,0))
for xx in (4.35,4.57,4.82): bar.ring((xx,0,0),.151,.080,.063,0,(1,0,0),8)
for zz in (-.117,.117): bar.box((4.585,0,zz),(.45,.135,.045),0)
bar.ring((4.86,0,0),.121,.052,.025,1,(1,0,0),32)
bar.finish()
empty('SOCKET_MUZZLE',recoil,(4.884,0,0))

# Running gear: paired wheel discs leave a central channel for the guide teeth.
wheel_x=[-2.225,-1.335,-.445,.445,1.335,2.225]
for side in (-1,1):
    tag='L' if side<0 else 'R'
    suspension=empty('SUSPENSION_'+tag,root)
    for idx,x in enumerate(wheel_x):
        wp=empty('ROAD_WHEEL_'+tag+'_%02d'%idx,suspension,(x,side*1.5,.56)); wheel_nodes.append((wp,.425))
        w=Mesh(wp.name+'_MESH',wp)
        for dy in (-.157,.157):
            w.cyl((0,dy,0),.425,.184,1,(0,1,0),48)
            w.ring((0,dy+side*.096,0),.404,.358,.022,0,(0,1,0),48)
        y=side*.262
        w.cyl((0,y,0),.339,.026,0,(0,side,0),48)
        w.ring((0,y+side*.017,0),.305,.275,.019,1,(0,side,0),48)
        w.cyl((0,y+side*.042,0),.122,.071,1,(0,side,0),24)
        w.cyl((0,y+side*.082,0),.077,.021,0,(0,side,0),12)
        w.bolt_circle((0,y+side*.023,0),.22,10,(0,side,0),.020)
        w.bolt_circle((0,y+side*.095,0),.063,6,(0,side,0),.010)
        w.finish()
    arms=Mesh('BOGIE_ARMS_'+tag,suspension)
    for x in (-1.78,0,1.78):
        arms.cyl((x,side*1.25,.95),.145,.22,1,(0,side,0),24)
        for delta in (-.445,.445): arms.rod((x,side*1.27,.95),(x+delta,side*1.27,.56),.052)
        arms.box((x,side*1.28,1.08),(.60,.14,.13),1)
    arms.finish(.003)
    for x,name in ((3.0,'FRONT_IDLER'),(-3.0,'REAR_SPROCKET')):
        wp=empty(name+'_'+tag,root,(x,side*1.5,1.0)); wheel_nodes.append((wp,.45)); w=Mesh(wp.name+'_MESH',wp)
        for dy in (-.16,.16):
            w.ring((0,dy,0),.45,.31,.16,1,(0,1,0),48)
            for i in range(10):
                a=i*math.tau/10; w.rod((.1*math.cos(a),dy,.1*math.sin(a)),(.335*math.cos(a),dy,.335*math.sin(a)),.033,0)
        w.cyl((0,side*.267,0),.17,.10,0,(0,side,0)); w.cyl((0,side*.33,0),.10,.045,1,(0,side,0),12)
        w.bolt_circle((0,side*.322,0),.137,8,(0,side,0),.018)
        if x<0:
            for i in range(18):
                a=i*math.tau/18
                for dy in (-.205,.205): w.box((.451*math.cos(a),dy,.451*math.sin(a)),(.054,.071,.051),0,Matrix.Rotation(-a,3,'Y'))
        w.finish()

def convex_hull(ps):
    ps=sorted(set(ps))
    def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[]; hi=[]
    for p in ps:
        while len(lo)>=2 and cross(lo[-2],lo[-1],p)<=0: lo.pop()
        lo.append(p)
    for p in reversed(ps):
        while len(hi)>=2 and cross(hi[-2],hi[-1],p)<=0: hi.pop()
        hi.append(p)
    return lo[:-1]+hi[:-1]
points=[]
for x,z,r in [(x,.56,.490) for x in wheel_x]+[(-3,1,.535),(3,1,.535)]:
    points.extend([(x+r*math.cos(a*math.tau/160),z+r*math.sin(a*math.tau/160)) for a in range(160)])
path=convex_hull(points); lengths=[0]
for a,b in zip(path,path[1:]+path[:1]): lengths.append(lengths[-1]+math.dist(a,b))
perimeter=lengths[-1]; count=round(perimeter/.147); step=perimeter/count
def sample(s):
    s=s%perimeter; i=min(len(path)-1,bisect.bisect_right(lengths,s)-1)
    a,b=path[i],path[(i+1)%len(path)]; t=(s-lengths[i])/(lengths[i+1]-lengths[i])
    return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,math.atan2(b[1]-a[1],b[0]-a[0]))

prototype=Mesh('TRACK_LINK_PROTOTYPE',None)
prototype.box((0,0,0),(step*.80,.64,.063),0)
for yy in (-.217,.217): prototype.box((0,yy,-.045),(.042,.198,.032),1)
prototype.box((0,0,.070),(.066,.047,.09),1)
prototype.cyl((step*.40,0,.0),.025,.681,1,(0,1,0),12)
for yy in (-.25,.25): prototype.box((0,yy,.037),(.071,.092,.012),3)
proto=prototype.finish(); mesh=proto.data
for side in (-1,1):
    group=empty('TRACKS_'+('L' if side<0 else 'R'),root); group['link_count']=count; group['pitch_m']=step; group['width_m']=.64
    for i in range(count):
        o=bpy.data.objects.new(group.name+'_LINK_%03d'%i,mesh); scene.collection.objects.link(o); o.parent=group
        x,z,t=sample(i*step); o.location=(x,side*1.5,z); o.rotation_euler.y=-t; o['path_offset_m']=i*step
        track_links.append((o,i*step,side))
bpy.data.objects.remove(proto,do_unlink=True); parts.pop('TRACK_LINK_PROTOTYPE',None)

# Fender decks, braces, towing eyes, lights, tool clamps and cable runs.
f=Mesh('FENDERS_AND_TOOLS')
for side in (-1,1):
    for xx,ll in ((-2.80,1.12),(-1.41,1.58),(.30,1.79),(2.06,1.63)):
        f.box((xx,side*1.52,1.687),(ll,.67,.044))
        f.box((xx,side*1.85,1.716),(ll,.025,.095),1)
        for bx in (xx-ll*.35,xx+ll*.35): f.bolt((bx,side*1.75,1.715),r=.014)
    f.path([(2.86,side*1.85,1.71),(3.35,side*1.85,1.46),(3.49,side*1.85,1.42)],.019)
    f.box((3.11,side*1.51,1.57),(.57,.68,.045),0,Matrix.Rotation(.47,3,'Y'))
    f.box((-3.30,side*1.52,1.53),(.45,.68,.045),0,Matrix.Rotation(-.59,3,'Y'))
    for xx in (-2.65,1.95):
        f.path([(xx-.22,side*1.67,1.73),(xx-.22,side*1.74,1.81),(xx+.22,side*1.74,1.81),(xx+.22,side*1.67,1.73)],.016)
    # Cable is a bent metal curve resting on brackets, clear of the track.
    ps=[(-2.4,side*1.68,1.77),(-2.65,side*1.63,1.80),(-2.3,side*1.62,1.81),(-.6,side*1.63,1.81),(.65,side*1.65,1.77)]
    f.path(ps,.024)
    f.rod((.67,side*1.68,1.755),(2.08,side*1.68,1.755),.027,0)
    f.box((2.2,side*1.68,1.751),(.28,.23,.018),1)
    for xx in (.83,1.73): f.box((xx,side*1.68,1.79),(.046,.115,.065),1)
    for xx in (3.06,-3.12):
        f.box((xx,side*.96,1.20),(.13,.15,.14),1)
        f.ring((xx+( .09 if xx>0 else -.09),side*.96,1.13),.103,.060,.06,0,(0,1,0),24)
    f.cyl((2.99,side*1.09,1.69),.088,.12,1,(1,0,0),32)
    f.cyl((3.055,side*1.09,1.69),.072,.012,4,(1,0,0),32)
    f.box((3.064,side*1.09,1.69),(.01,.13,.022),0)
f.finish(.002)
for name,loc in [('SOCKET_ENGINE_DAMAGE',(1.3,0,1.6)),('SOCKET_AMMO_DAMAGE',(-1.4,0,2.0)),('SOCKET_SMOKE',(-3.24,0,1.48)),('SOCKET_CAMERA_THIRD',(-7,-7,4.8))]: empty(name,root,loc)

# Local clips: track links circulate on a closed path; neither entire track assembly spins.
for frame in range(1,62,2):
    distance=(frame-1)/60*step*8
    for o,s,side in track_links:
        x,z,a=sample(s+distance); o.location=(x,side*1.5,z); o.rotation_euler.y=-a
        o.keyframe_insert(data_path='location',frame=frame); o.keyframe_insert(data_path='rotation_euler',index=1,frame=frame)
    for o,r in wheel_nodes:
        o.rotation_euler.y=distance/r; o.keyframe_insert(data_path='rotation_euler',index=1,frame=frame)
def keyrot(o,axis,keys):
    for fr,ang in keys: o.rotation_euler[axis]=math.radians(ang); o.keyframe_insert(data_path='rotation_euler',index=axis,frame=fr)
keyrot(traverse,2,[(1,0),(81,0),(110,7.5),(145,-7.5),(170,0)])
keyrot(pitch,1,[(1,0),(81,0),(110,4),(145,-14),(170,0)])
for fr,x in [(1,0),(181,0),(186,-.23),(208,0)]: recoil.location.x=x; recoil.keyframe_insert(data_path='location',index=0,frame=fr)
for h in hatch_nodes: keyrot(h,1,[(1,0),(221,0),(250,80),(280,0)])
for name,fr in [('DRIVE / track circulation',1),('AIM / limited traverse',81),('FIRE / recoil',181),('HATCHES / inspection',221)]: scene.timeline_markers.new(name,frame=fr)
for act in bpy.data.actions:
    for layer in act.layers:
        for strip in layer.strips:
            if hasattr(strip,'channelbags'):
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for k in fc.keyframe_points: k.interpolation='LINEAR'
scene.frame_set(1); bpy.context.view_layer.update()

# Actual drawing cameras: orthographic, automatic framing from model bounds.
scene.render.engine='CYCLES'; scene.cycles.samples=24; scene.cycles.use_denoising=False
scene.render.resolution_x=2000; scene.render.resolution_y=1400; scene.render.resolution_percentage=100
scene.render.film_transparent=True; scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='Standard'
scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1)
scene.render.use_freestyle=True; scene.render.line_thickness=1
fs=scene.view_layers[0].freestyle_settings; fs.crease_angle=math.radians(135)
ls=fs.linesets[0]; ls.select_silhouette=True; ls.select_border=True; ls.select_crease=True; ls.select_external_contour=True
ls.linestyle.color=(.034,.075,.135); ls.linestyle.thickness=1.6
ls.linestyle.use_chaining=True
def bounds():
    return [o.matrix_world@Vector(v) for o in root.children_recursive if o.type=='MESH' for v in o.bound_box]
vs=bounds(); lo=Vector(tuple(min(v[i] for v in vs) for i in range(3))); hi=Vector(tuple(max(v[i] for v in vs) for i in range(3))); center=(lo+hi)/2
cams={}
def camera(name,direction,margin=1.14):
    d=Vector(direction).normalized(); data=bpy.data.cameras.new(name); data.type='ORTHO'; o=bpy.data.objects.new('VIEW_'+name,data); scene.collection.objects.link(o)
    o.location=center+d*25; o.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler(); bpy.context.view_layer.update()
    inv=o.matrix_world.inverted(); pts=[inv@v for v in vs]
    xmin,xmax=min(v.x for v in pts),max(v.x for v in pts); ymin,ymax=min(v.y for v in pts),max(v.y for v in pts)
    o.location+=o.matrix_world.to_3x3()@Vector(((xmin+xmax)/2,(ymin+ymax)/2,0))
    data.ortho_scale=max(xmax-xmin,(ymax-ymin)*scene.render.resolution_x/scene.render.resolution_y)*margin
    cams[name]=o; return o
camera('ISO',(10,-12,9)); camera('SIDE',(0,-1,0)); camera('TOP',(0,0,1)); camera('FRONT',(1,0,0)); camera('REAR',(-1,0,0)); camera('REAR_ISO',(-10,-12,8))
scene.camera=cams['ISO']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.overlay.show_overlays=False

# Clearances: independent wheel geometry, moving gun vs hood, roof vs rotating lids.
checks={}
checks['roadwheel_gap_m']=min(b-a for a,b in zip(wheel_x,wheel_x[1:]))-.850
checks['lower_hull_to_track_inner_gap_m']=1.5-.32-1.16
checks['track_to_fender_vertical_gap_m']=1.665-(1+.535+.061)
checks['track_nominal_wheel_radial_clearance_m']=.490-.0315-.425
checks['wheel_pairs_end_clearance_m']=math.hypot(3-2.225,1-.56)-(.450+.425)
checks['minimum_gun_to_engine_deck_gap_m']=2.27-(2.85-.15)*math.tan(math.radians(4))-.145-1.848
assert min(checks.values())>0,checks
def bvh(o,deps): return BVHTree.FromObject(o,deps)
collision=[]
for fr in (1,19,61,110,145,186,250):
    scene.frame_set(fr); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get()
    # FromObject returns local coordinates; explicitly build world-space BVHs.
    def worldtree(o):
        e=o.evaluated_get(deps); me=e.to_mesh(); vv=[e.matrix_world@v.co for v in me.vertices]; ff=[tuple(p.vertices) for p in me.polygons]
        tree=BVHTree.FromPolygons(vv,ff); e.to_mesh_clear(); return tree
    tests=[('GUN_BARREL','ENGINE_DECK'),('GUN_BARREL','DRIVER_NOSE'),('HATCH_L','CASEMATE_ROOF'),('HATCH_R','CASEMATE_ROOF')]
    for a,b in tests:
        if worldtree(parts[a]).overlap(worldtree(parts[b])): collision.append({'frame':fr,'a':a,'b':b})
checks['sampled_intersections']=collision
scene.frame_set(1); bpy.context.view_layer.update()
# Check the entire belt against hull panels and rotating wheel meshes at representative drive poses.
for fr in (1,19,61):
    scene.frame_set(fr); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get()
    solids=[parts[n] for n in ('HULL_LOWER','HULL_SPONSONS','DRIVER_NOSE','CASEMATE_L','CASEMATE_R')]
    solids += [parts[o.name+'_MESH'] for o,r in wheel_nodes]
    cache={o.name:worldtree(o) for o in solids}
    for o,s,side in track_links:
        lt=worldtree(o)
        for solid in solids:
            if lt.overlap(cache[solid.name]): collision.append({'frame':fr,'a':o.name,'b':solid.name})
scene.frame_set(1); bpy.context.view_layer.update()
report={'design':'Ferdinand inspired V3','measured_mesh_bounds_m':list(hi-lo),'track_width_m':.64,'track_links_per_side':count,'road_wheels_per_side':6,'clearance_checks':checks,'validated_frames':[1,19,61,110,145,186,250],'limitations':'Selected moving-part checks only; assembly joints intentionally meet. No engine runtime or battle physics validation.'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(OUT/'track_path.json').write_text(json.dumps({'path_xz':path,'perimeter_m':perimeter,'pitch_m':step,'count_per_side':count,'y_centers':[-1.5,1.5]},indent=2),encoding='utf-8')
assert not collision,collision

# Model-local annotations for the composed drawing and optional future viewer.
from bpy_extras.object_utils import world_to_camera_view
anchors={'casemate':(-1.40,-1.43,2.25),'hatch':(-1.52,-.65,2.88),'grille':(1.24,-.99,1.8),'mantlet':(.20,0,2.27),'muzzle':(4.92,0,2.27),'wheel':(.445,-1.82,.56),'track':(-1.4,-1.5,.07),'rear_drive':(-3,-1.80,1),'width_left':(3.5,-1.85,.03),'width_right':(3.5,1.85,.03)}
projected={k:list(world_to_camera_view(scene,cams['ISO'],Vector(v))) for k,v in anchors.items()}
(OUT/'drawing_anchors.json').write_text(json.dumps(projected,indent=2),encoding='utf-8')

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ferdinand_technical.blend'))
# GLB receives conventional PBR materials. Drafting nodes stay in the authoring source.
plain=[]
for m in MATS:
    p=bpy.data.materials.new('Game '+m.name); p.diffuse_color=m.diffuse_color; p.use_nodes=True
    bs=p.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=m.diffuse_color; bs.inputs['Roughness'].default_value=.68
    plain.append(p)
seen=set()
for o in root.children_recursive:
    if o.type=='MESH' and o.data.name not in seen:
        seen.add(o.data.name)
        for i in range(len(o.data.materials)): o.data.materials[i]=plain[i]
bpy.ops.object.select_all(action='DESELECT'); root.select_set(True)
for o in root.children_recursive: o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(OUT/'ferdinand_vehicle.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True,export_animation_mode='SCENE',export_animations=True,export_cameras=False,export_lights=False)
seen=set()
for o in root.children_recursive:
    if o.type=='MESH' and o.data.name not in seen:
        seen.add(o.data.name)
        for i in range(len(o.data.materials)): o.data.materials[i]=MATS[i]
for name in ('ISO','SIDE','TOP','FRONT','REAR','REAR_ISO'):
    scene.camera=cams[name]; scene.render.filepath=str(OUT/('render_'+name.lower()+'.png')); bpy.ops.render.render(write_still=True)
scene.frame_set(250); scene.camera=cams['ISO']; scene.render.filepath=str(OUT/'render_hatches.png'); bpy.ops.render.render(write_still=True)
scene.frame_set(1); scene.camera=cams['ISO']; scene.render.filepath=str(OUT/'render_iso.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ferdinand_technical.blend'))
print('FERDINAND_V3_COMPLETE',json.dumps(report))
