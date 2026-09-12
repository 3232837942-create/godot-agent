"""Reference-inspired rotating turret conversion; preserves the repaired V3 master."""
import ast, bpy, bmesh, math, json, base64, runpy, os
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'assets'/'3d'/'ferdinand_v4'
SOURCE=OUT.parent/'ferdinand_v3'/'ferdinand_technical.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.frame_set(1);scene.frame_end=540
bpy.context.preferences.filepaths.save_version=0
root=bpy.data.objects['FERDINAND_ROOT'];root['variant']='FD-184R / fictional rotating-turret conversion'
MATS=list(bpy.data.objects['HULL_LOWER'].data.materials)
parts={};I=Matrix.Identity(3)
# Reuse only the geometry helper definitions; do not run the V3 builder.
tree=ast.parse((HERE/'rebuild_v3.py').read_text(encoding='utf-8'))
selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'Mesh','empty','orient','bore','keyrot'}]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(HERE/'rebuild_v3.py'),'exec'))
def bore(obj,pos,r,depth,axis=(0,0,1)):
    cutter=Mesh('V4 aperture cutter',None).cyl(pos,r,depth,0,axis,64).finish()
    bpy.context.view_layer.update()
    cutter.matrix_world=obj.matrix_world@cutter.matrix_world
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Machined opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True);parts.pop('V4 aperture cutter',None)

fx=bpy.data.collections.get('PRESENTATION_FIRE_FX')
if fx:
    for o in list(fx.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(fx)
# The repaired hull, mudguards, suspension, track instances and gun stay intact.
for o in list(root.children_recursive):
    if o.name.startswith(('CASEMATE_','HATCH_')) or o.name=='REAR_DETAILS':bpy.data.objects.remove(o,do_unlink=True)
traverse=bpy.data.objects['GUN_TRAVERSE_PIVOT'];pitch=bpy.data.objects['GUN_PITCH_PIVOT'];recoil=bpy.data.objects['GUN_RECOIL_ROOT']
traverse.animation_data_clear();traverse.rotation_euler=(0,0,0)
turret=empty('TURRET_YAW_PIVOT',root,(-1.10,0,2.00));turret['rotation_range_deg']='360 continuous';turret['role']='Entire turret and all roof/side attachments'
traverse.parent=turret;traverse.location=(1.74,0,.57);traverse['limits_deg']='0; azimuth handled by TURRET_YAW_PIVOT'
# Shorten the exposed tube slightly to balance the lower turret.
bar=bpy.data.objects['GUN_BARREL'];bar.data=bar.data.copy()
for v in bar.data.vertices:
    if v.co.x>.68:v.co.x=.68+(v.co.x-.68)*.88
socket=bpy.data.objects['SOCKET_MUZZLE'];socket.location.x=.68+(4.884-.68)*.88
deck=Mesh('HULL_TURRET_DECK').box((-1.60,0,1.73),(2.90,2.75,.060)).finish(.012)
bore(deck,(-1.1,0,1.73),1.03,.4)
base=Mesh('TURRET_FIXED_BEARING');base.ring((-1.1,0,1.824),1.24,1.03,.12,1,N=96)
base.ring((-1.1,0,1.902),1.26,1.03,.032,0,N=96);base.bolt_circle((-1.1,0,1.92),1.18,32,size=.013);base.finish()
spin=Mesh('TURRET_ROTATING_BEARING',turret);spin.ring((0,0,-.046),1.15,1.045,.054,2,N=96);spin.ring((0,0,-.006),1.20,1.045,.024,1,N=96);spin.finish()

lower=[(1.60,-.90),(1.60,.90),(.98,1.36),(-1.30,1.36),(-1.62,1.02),(-1.62,-1.02),(-1.30,-1.36),(.98,-1.36)]
upper=[(1.18,-.75),(1.18,.75),(.80,1.16),(-1.27,1.16),(-1.48,.96),(-1.48,-.96),(-1.27,-1.16),(.80,-1.16)]
wallnames=['FRONT','CHEEK_R','SIDE_R','REAR_CORNER_R','REAR','REAR_CORNER_L','SIDE_L','CHEEK_L']
for i,name in enumerate(wallnames):
    j=(i+1)%8;outer=[(*lower[i],.02),(*lower[j],.02),(*upper[j],.94),(*upper[i],.94)]
    v0,v1,v2=map(Vector,outer[:3]);normal=(v1-v0).cross(v2-v0).normalized()
    inner=[tuple(Vector(v)-normal*.045) for v in outer]
    ob=Mesh('TURRET_'+name,turret).add(outer+inner,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]).finish(.009)
    if name=='FRONT':bore(ob,(1.40,0,.57),.316,1.3,(1,0,0))
roof=Mesh('TURRET_ROOF',turret).add([(*p,.939) for p in upper]+[(*p,.973) for p in upper],[tuple(reversed(range(8))),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]).finish(.008)
floor=Mesh('TURRET_FLOOR',turret).add([(*p,.018) for p in lower]+[(*p,.051) for p in lower],[tuple(reversed(range(8))),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]).finish(.006)
bore(floor,(0,0,.03),1.02,.3)

# Beveled rectangular mounting collar, with a true open passage for the ball.
seat=Mesh('TURRET_GUN_SEAT',turret);verts=[];N=64
for kind,inner in [('rear',False),('front',False),('front',True),('rear',True)]:
    for i in range(N):
        a=i*math.tau/N;c,s=math.cos(a),math.sin(a)
        r=.310 if inner else min((.40 if kind=='rear' else .365)/max(abs(c),abs(s)),.49 if kind=='rear' else .452)
        y,z=r*c,.57+r*s;x=(1.60+(1.18-1.60)*(z-.02)/.92+.025) if kind=='rear' else 1.685
        verts.append((x,y,z))
seat.add(verts,[(j*N+i,j*N+(i+1)%N,((j+1)%4)*N+(i+1)%N,((j+1)%4)*N+i) for j in range(4) for i in range(N)])
seat.ring((1.696,0,.57),.335,.310,.022,1,(1,0,0),64)
for y in (-.32,.32):
    for z in (.25,.89):seat.bolt((1.69,y,z),(1,0,0),.018)
seat.finish(.003)

hatches=[]
for side in (-1,1):
    tag='L' if side<0 else 'R';cx=-.42;cy=side*.61
    bore(roof,(cx,cy,.96),.302,.3)
    rim=Mesh('HATCH_'+tag+'_RIM',turret);rim.ring((cx,cy,.992),.332,.300,.039,1);rim.finish()
    hp=empty('HATCH_'+tag+'_PIVOT',turret,(cx+.32,cy,1.027));hatches.append(hp)
    lid=Mesh('HATCH_'+tag,hp);lid.cyl((-.32,0,0),.313,.03);lid.ring((-.32,0,.025),.279,.260,.014,1)
    lid.box((-.32,0,.028),(.43,.044,.025),1);lid.path([(-.40,-.075,.042),(-.40,-.075,.10),(-.40,.075,.10),(-.40,.075,.042)],.014)
    for yy in (-.17,.17):lid.cyl((0,yy,0),.033,.11,1,(0,1,0),20)
    lid.finish(.002);keyrot(hp,1,[(1,0),(221,0),(250,80),(280,0),(540,0)])

details=Mesh('TURRET_ROOF_FITTINGS',turret)
for side in (-1,1):
    details.cyl((.69,side*.57,1.008),.115,.07,0);details.ring((.69,side*.57,1.053),.135,.072,.019,1)
    for xx in (-.84,-.52,-.20):
        details.box((xx,side*.97,.99),(.20,.115,.035),1);details.box((xx,side*.97,1.017),(.146,.08,.016),4)
    details.path([(-1.15,side*.96,1.00),(-1.15,side*.96,1.09),(-.92,side*.96,1.09),(-.92,side*.96,1.00)],.013)
for i in range(8):
    j=(i+1)%8;details.rod((*upper[i],.978),(*upper[j],.978),.008,1)
details.finish(.002)

# Stowage, handrails, angled side tubes and an open basket echo the reference.
for side in (-1,1):
    tag='L' if side<0 else 'R';d=Mesh('TURRET_SIDE_ACCESSORIES_'+tag,turret)
    d.box((-.69,side*1.366,.43),(.92,.17,.29),1)
    d.box((-.69,side*1.463,.43),(.86,.028,.255),0)
    for x in (-1.04,-.34):d.box((x,side*1.486,.47),(.054,.020,.16),1);d.bolt((x,side*1.5,.39),(0,side,0),.014)
    d.path([(-1.10,side*1.34,.70),(-1.10,side*1.47,.72),(-.35,side*1.47,.72),(-.35,side*1.34,.70)],.019)
    d.box((.32,side*1.37,.53),(.30,.030,.175),1);d.box((.32,side*1.391,.53),(.237,.017,.12),2)
    for j in range(3):
        axis=Vector((.42,side*.74,.53)).normalized();p=Vector((.64-j*.19,side*1.33,.26+j*.017))
        d.cyl(p+axis*.13,.056,.26,1,axis,24);d.ring(p+axis*.27,.060,.043,.027,0,axis,24)
        d.rod((p.x,side*1.30,.20),(p.x,side*1.36,.29),.025,1)
    d.finish(.004)
basket=Mesh('TURRET_REAR_BASKET',turret)
for z in (.18,.42,.68):basket.path([(-1.49,-.91,z),(-1.85,-.91,z),(-1.85,.91,z),(-1.49,.91,z)],.024,1)
for y in (-.91,-.46,0,.46,.91):basket.rod((-1.85,y,.18),(-1.85,y,.68),.022,1)
for y in (-.70,-.35,0,.35,.70):basket.rod((-1.51,y,.19),(-1.86,y,.19),.014,1)
basket.box((-1.66,-.39,.36),(.26,.67,.30),0)
for yy in (-.65,-.13):basket.box((-1.80,yy,.36),(.015,.054,.31),1)
basket.finish(.003)

# Roof-mounted machine gun with a pedestal, cradle, ammo box and ventilated barrel.
mg=empty('MG_MOUNT',turret,(.32,-.77,1.00))
stand=Mesh('MG_PEDESTAL',mg);stand.cyl((0,0,.035),.10,.07,1);stand.bolt_circle((0,0,.075),.075,6,size=.009)
stand.cyl((0,0,.23),.037,.33,1);stand.ring((0,0,.33),.056,.038,.065,0)
for yy in (-.073,.073):stand.box((0,yy,.40),(.13,.025,.20),1)
stand.finish(.002)
mgpitch=empty('MG_ELEVATION_PIVOT',mg,(0,0,.48));mgpitch.rotation_euler.y=math.radians(-18)
mgbody=Mesh('MG_WEAPON',mgpitch);mgbody.box((.01,0,0),(.38,.135,.145),1);mgbody.box((-.03,0,.087),(.24,.118,.03),0)
mgbody.box((-.28,0,-.035),(.21,.09,.10),0);mgbody.box((-.40,0,-.035),(.045,.13,.18),1)
mgbody.cyl((.59,0,.0),.022,.82,1,(1,0,0),24);mgbody.cyl((1.04,0,0),.032,.085,1,(1,0,0),24)
for x in (.22,.31,.40,.49,.58,.67):mgbody.ring((x,0,0),.047,.035,.018,0,(1,0,0),16)
for i in range(6):
    a=i*math.tau/6;mgbody.rod((.22,.041*math.cos(a),.041*math.sin(a)),(.68,.041*math.cos(a),.041*math.sin(a)),.007,1,6)
mgbody.box((.82,0,.063),(.035,.027,.106),1);mgbody.ring((.20,0,.125),.050,.040,.012,1,(1,0,0),24)
mgbody.path([(-.11,0,-.06),(-.11,0,-.20),(-.03,0,-.20),(-.01,0,-.07)],.017,1)
mgbody.box((-.04,-.17,-.013),(.23,.18,.25),0);mgbody.box((-.04,-.17,.119),(.25,.20,.019),1)
for xx in (-.11,.03):mgbody.box((xx,-.269,-.01),(.018,.014,.20),1)
mgbody.finish(.002)
empty('SOCKET_MG_MUZZLE',mgpitch,(1.084,0,0))

for idx,(x,y,height) in enumerate(((-1.18,.91,1.12),(-1.24,-.83,.76))):
    antenna=Mesh('TURRET_ANTENNA_%d'%idx,turret)
    antenna.cyl((x,y,1.008),.065,.07,1);antenna.cyl((x,y,1.063),.035,.06,2)
    spring=[(x+.024*math.cos(i*math.tau/10),y+.024*math.sin(i*math.tau/10),1.09+i*.0019) for i in range(70)]
    antenna.path(spring,.005,1);antenna.cyl((x,y,1.23+height/2),.008,height,1,N=12,r2=.0035)
    antenna.cyl((x,y,1.23+height),.011,.027,1,N=12);antenna.finish()

# All moving fittings inherit this single pivot, including the roof machine gun.
keyrot(turret,2,[(1,0),(81,0),(110,45),(145,-55),(170,0),(385,0),(401,0),(431,90),(461,180),(491,270),(521,360),(540,360)])
for label in list(scene.timeline_markers):
    if label.frame>=401:scene.timeline_markers.remove(label)
scene.timeline_markers.new('TURRET / full rotation',frame=401)
for act in bpy.data.actions:
    for layer in act.layers:
        for strip in layer.strips:
            if hasattr(strip,'channelbags'):
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for k in fc.keyframe_points:k.interpolation='LINEAR'
scene.frame_set(1);bpy.context.view_layer.update()

def worldtree(o):
    e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh()
    tree=BVHTree.FromPolygons([e.matrix_world@v.co for v in me.vertices],[tuple(p.vertices) for p in me.polygons]);e.to_mesh_clear();return tree

# Verify the complete rotating assembly over the original deck and mudguards.
fixed_names=['HULL_LOWER','HULL_SPONSONS','HULL_TURRET_DECK','ENGINE_DECK','DRIVER_NOSE','FENDERS_AND_TOOLS','FENDER_FRONT_L','FENDER_FRONT_R','FENDER_REAR_L','FENDER_REAR_R']
fixed={n:worldtree(bpy.data.objects[n]) for n in fixed_names}
rotating=[o for o in turret.children_recursive if o.type=='MESH']
collisions=[]
for angle in range(0,360,5):
    turret.rotation_euler.z=math.radians(angle)
    for elev in (-4,14):
        pitch.rotation_euler.y=math.radians(-elev);bpy.context.view_layer.update()
        for o in rotating:
            mt=worldtree(o)
            for name,ft in fixed.items():
                if mt.overlap(ft):collisions.append({'angle':angle,'elevation':elev,'moving':o.name,'fixed':name})
scene.frame_set(1);bpy.context.view_layer.update()
attachment_names=['TURRET_ROOF','TURRET_ROOF_FITTINGS','MG_PEDESTAL','MG_WEAPON','TURRET_ANTENNA_0','TURRET_ANTENNA_1']
attachments={n:worldtree(bpy.data.objects[n]) for n in attachment_names}
for angle in range(0,81,4):
    for h in hatches:h.rotation_euler.y=math.radians(angle)
    bpy.context.view_layer.update()
    for name in ('HATCH_L','HATCH_R'):
        ht=worldtree(bpy.data.objects[name])
        for other,tree in attachments.items():
            if ht.overlap(tree):collisions.append({'hatch_deg':angle,'moving':name,'fixed':other})
scene.frame_set(1);bpy.context.view_layer.update()
fixed_gun={n:worldtree(bpy.data.objects[n]) for n in ('TURRET_FRONT','TURRET_GUN_SEAT','TURRET_ROOF')}
for elev in (-4,0,7,14):
    for stroke in (0,-.115,-.23):
        pitch.rotation_euler.y=-math.radians(elev);recoil.location.x=stroke;bpy.context.view_layer.update()
        for name in ('GUN_MANTLET','GUN_BARREL'):
            for other,tree in fixed_gun.items():
                if worldtree(bpy.data.objects[name]).overlap(tree):collisions.append({'elevation':elev,'stroke':stroke,'moving':name,'fixed':other})
report={'variant':'FD-184R V4','source_preserved':str(SOURCE),'turret_sweep_samples':144,'hatch_pose_samples':21,'gun_pose_samples':12,'intersection_results':collisions,'limits':'Sampled mesh intersections; no vehicle physics or engine runtime validation.'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert not collisions,json.dumps(collisions[:30])
scene.frame_set(1);bpy.context.view_layer.update()

# Reframe the six original orthographic cameras around the converted body.
points=[o.matrix_world@Vector(v) for o in root.children_recursive if o.type=='MESH' for v in o.bound_box]
lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)]);center=(lo+hi)/2
directions={'ISO':(10,-12,9),'SIDE':(0,-1,0),'TOP':(0,0,1),'FRONT':(1,0,0),'REAR':(-1,0,0),'REAR_ISO':(-10,-12,8)}
for name,d in directions.items():
    cam=bpy.data.objects['VIEW_'+name];d=Vector(d).normalized();cam.location=center+d*25;cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    projected=[cam.matrix_world.inverted()@v for v in points];xmin,xmax=min(v.x for v in projected),max(v.x for v in projected);ymin,ymax=min(v.y for v in projected),max(v.y for v in projected)
    cam.location+=cam.matrix_world.to_3x3()@Vector(((xmin+xmax)/2,(ymin+ymax)/2,0));cam.data.ortho_scale=max(xmax-xmin,(ymax-ymin)*scene.render.resolution_x/scene.render.resolution_y)*1.14
scene.camera=bpy.data.objects['VIEW_ISO']
for ls in scene.view_layers[0].freestyle_settings.linesets:ls.select_by_collection=False
from bpy_extras.object_utils import world_to_camera_view
anchors={'casemate':(-1.5,-1.44,2.50),'hatch':(-1.52,-.61,3.04),'grille':(1.24,-.99,1.8),'mantlet':(.61,0,2.57),'muzzle':tuple(socket.matrix_world.translation),'wheel':(.445,-1.82,.56),'track':(-1.4,-1.5,.07),'rear_drive':(-3,-1.8,1)}
(OUT/'drawing_anchors.json').write_text(json.dumps({k:list(world_to_camera_view(scene,scene.camera,Vector(v))) for k,v in anchors.items()}),encoding='utf-8')

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ferdinand_technical.blend'))
game=[]
for m in MATS:
    mat=bpy.data.materials.new('V4 game '+m.name);mat.diffuse_color=m.diffuse_color;mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.68;game.append(mat)
meshes={o.data.name:o.data for o in root.children_recursive if o.type=='MESH'}
saved_mats={name:list(me.materials) for name,me in meshes.items()}
for me in meshes.values():
    for i in range(len(me.materials)):me.materials[i]=game[i]
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for o in root.children_recursive:o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(OUT/'ferdinand_vehicle.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True,export_animation_mode='SCENE',export_animations=True,export_cameras=False,export_lights=False)
for name,me in meshes.items():
    for i,m in enumerate(saved_mats[name]):me.materials[i]=m
(OUT/'vehicle_data.js').write_text('const VEHICLE_GLB="'+base64.b64encode((OUT/'ferdinand_vehicle.glb').read_bytes()).decode()+'";',encoding='utf-8')
for name in directions:
    scene.camera=bpy.data.objects['VIEW_'+name];scene.render.filepath=str(OUT/('render_'+name.lower()+'.png'));bpy.ops.render.render(write_still=True)
scene.frame_set(250);scene.camera=bpy.data.objects['VIEW_ISO'];scene.render.filepath=str(OUT/'render_hatches.png');bpy.ops.render.render(write_still=True)
scene.frame_set(431);scene.render.filepath=str(OUT/'render_turret_90.png');bpy.ops.render.render(write_still=True)
scene.frame_set(1);scene.camera=bpy.data.objects['VIEW_ISO'];scene.render.filepath=str(OUT/'render_iso.png');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ferdinand_technical.blend'))
runpy.run_path(str(HERE/'add_shot_fx.py'),init_globals={'ASSET_OUT':OUT},run_name='__main__')
print('FD184R_BUILD_OK',json.dumps(report))
