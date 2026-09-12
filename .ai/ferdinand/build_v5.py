"""V5: segmented skirts, seated turret, authored hierarchical exploded parts."""
import ast, bpy, bmesh, math, json, base64, sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'assets'/'3d'/'ferdinand_v5'
SOURCE=OUT.parent/'ferdinand_v4'/'ferdinand_technical.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
bpy.context.preferences.filepaths.save_version=0
root=bpy.data.objects['FERDINAND_ROOT'];root['variant']='FD-184R V5 / skirts and detailed assembly'
MATS=list(bpy.data.objects['HULL_LOWER'].data.materials);parts={};I=Matrix.Identity(3)
tree=ast.parse((HERE/'rebuild_v3.py').read_text(encoding='utf-8'))
selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'Mesh','empty','orient','bore'}]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(HERE/'rebuild_v3.py'),'exec'))
turret=bpy.data.objects['TURRET_YAW_PIVOT'];turret.location.z=1.96
pitch=bpy.data.objects['GUN_PITCH_PIVOT']

def offset(o,vec,layer):
    o['explode_offset_blender']=list(vec);o['explode_layer']=layer

# A broad raised mounting plinth carries the fixed bearing. A concentric rotating
# cover overlaps its vertical seam, with radial clearance between separate solids.
for name in ('TURRET_FIXED_BEARING','TURRET_ROTATING_BEARING'):
    bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
outline=[(1.64,-.98),(1.64,.98),(1.10,1.39),(-1.34,1.39),(-1.69,1.02),(-1.69,-1.02),(-1.34,-1.39),(1.10,-1.39)]
plinth=Mesh('HULL_TURRET_PLINTH')
plinth.add([(x-1.1,y,1.760) for x,y in outline]+[(x*.98-1.1,y*.97,1.878) for x,y in outline],
    [tuple(reversed(range(8))),tuple(range(8,16))]+[(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)])
po=plinth.finish(.006);bore(po,(-1.1,0,1.82),1.035,.5)
base=Mesh('TURRET_FIXED_BEARING');base.ring((-1.1,0,1.900),1.306,1.04,.044,1,N=96);base.finish()
spin=Mesh('TURRET_ROTATING_BEARING',turret);spin.ring((0,0,-.009),1.295,1.045,.050,2,N=96);spin.finish()
seal=Mesh('TURRET_SEAM_COVER',turret);seal.ring((0,0,-.021),1.39,1.335,.092,0,N=96)
seal.ring((0,0,.017),1.401,1.332,.014,1,N=96);seal.finish(.002)

# Seven removable upper-track skirt plates on each side; inset lower corners,
# individual hinges, wear strips and external fasteners keep the large faces legible.
skirts=[];skirt_solids=[]
for side in (-1,1):
    tag='L' if side<0 else 'R';group=empty('SIDE_SKIRTS_'+tag,root);skirts.append(group)
    offset(group,(0,side*3.7,1.10),1)
    rail=Mesh('SKIRT_MOUNT_RAIL_'+tag,group)
    rail.box((-.09,side*1.905,1.758),(6.50,.070,.055),1)
    for j in range(7):
        x=-2.90+j*.93
        rail.box((x,side*1.84,1.755),(.14,.25,.052),1)
        panel=empty('SKIRT_PANEL_%s_%02d'%(tag,j),group,(x,side*1.95,0))
        offset(panel,((x+.1)*.25,side*(.12+(j%2)*.15),.16*(j%2)),2)
        bottom=1.14 if j not in (0,6) else 1.24
        profile=[(-.447,1.755),(.447,1.755),(.447,bottom+.10),(.35,bottom),(-.35,bottom),(-.447,bottom+.10)]
        me=Mesh(panel.name+'_ARMOR',panel)
        me.add([(px,yy,z) for yy in (-.027,.027) for px,z in profile],
            [tuple(reversed(range(6))),tuple(range(6,12))]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)])
        armor=me.finish(.007);skirt_solids.append(armor)
        trim=Mesh(panel.name+'_WEAR_STRIP',panel);trim.box((0,side*.036,bottom+.061),(.685,.017,.061),1);offset(trim.finish(.003),(0,side*.22,-.12),3)
        for k,xx in enumerate((-.29,.29)):
            hinge=Mesh(panel.name+'_HINGE_%d'%k,panel)
            hinge.cyl((xx,0,1.781),.033,.16,1,(1,0,0),20)
            hinge.box((xx,side*.033,1.693),(.088,.035,.13),1)
            hinge.bolt((xx,side*.054,1.67),(0,side,0),.014)
            offset(hinge.finish(.002),(0,side*.42,.21),4)
    skirt_solids.append(rail.finish(.004))

bpy.context.view_layer.update()
def worldtree(objects):
    verts=[];faces=[]
    for o in objects:
        e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();i=len(verts)
        verts.extend([e.matrix_world@v.co for v in me.vertices]);faces.extend([tuple(i+j for j in p.vertices) for p in me.polygons]);e.to_mesh_clear()
    return BVHTree.FromPolygons(verts,faces)

collisions=[]
new_static=skirts[0].children_recursive[:]+skirts[1].children_recursive[:]
new_static=[o for o in new_static if o.type=='MESH']
skirt_tree=worldtree(new_static)
track_objects=[o for o in root.children_recursive if '_LINK_' in o.name]
track_outer=max(abs((o.matrix_world@v.co).y) for o in track_objects for v in o.data.vertices)
for fr in (1,16,31,46,61):
    scene.frame_set(fr);bpy.context.view_layer.update()
    if skirt_tree.overlap(worldtree(track_objects)):collisions.append({'track_frame':fr})
scene.frame_set(1);bpy.context.view_layer.update()
fixed=worldtree([bpy.data.objects[n] for n in ('HULL_LOWER','HULL_SPONSONS','HULL_TURRET_PLINTH','HULL_TURRET_DECK','ENGINE_DECK','DRIVER_NOSE','FENDERS_AND_TOOLS','TURRET_FIXED_BEARING')]+new_static)
moving=[o for o in turret.children_recursive if o.type=='MESH']
for angle in range(0,360,5):
    turret.rotation_euler.z=math.radians(angle)
    for elev in (-4,14):
        pitch.rotation_euler.y=-math.radians(elev);bpy.context.view_layer.update()
        if fixed.overlap(worldtree(moving)):collisions.append({'yaw':angle,'elevation':elev})
scene.frame_set(1);bpy.context.view_layer.update()
report={'version':'V5','turret_sweep_poses':144,'track_animation_poses':5,'intersections':collisions,'skirt_track_lateral_clearance_m':round(1.923-track_outer,4),'bearing_radial_clearance_m':.029,'seam_cover_to_plinth_vertical_clearance_m':.015,'scope':'Sampled new skirt and turret interfaces, not complete vehicle physics.'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert not collisions,json.dumps(collisions)
print('V5_CLEARANCES_OK',flush=True)

# Break combined display meshes into coherent physical pieces. Small fasteners
# stay with their closest plate/part. The original assembly node survives intact.
split_stats={}
def split_mesh(o,mode):
    me=o.data;parent=list(range(len(me.vertices)))
    def find(a):
        while a!=parent[a]:parent[a]=parent[parent[a]];a=parent[a]
        return a
    for e in me.edges:
        a,b=e.vertices;parent[find(a)]=find(b)
    components={}
    for p in me.polygons:components.setdefault(find(p.vertices[0]),[]).append(p)
    comps=[]
    for polys in components.values():
        ids=sorted({i for p in polys for i in p.vertices});vs=[me.vertices[i].co for i in ids]
        lo=Vector([min(v[i] for v in vs) for i in range(3)]);hi=Vector([max(v[i] for v in vs) for i in range(3)])
        comps.append({'polys':polys,'center':(lo+hi)/2,'extent':max(hi-lo),'lo':lo,'hi':hi})
    if mode=='wheel':
        # Separate each axial layer, with fasteners grouped on their matching face.
        side=-1 if '_L' in o.name else 1;buckets={}
        for c in comps:
            y=c['center'].y*side
            key=0 if y<-.1 else 1 if y<.20 else 2 if y<.28 else 3 if y<.315 else 4 if y<.35 else 5
            buckets.setdefault(key,[]).append(c)
        groups=list(buckets.values())
    else:
        seeds=[c for c in comps if c['extent']>=.155]
        if not seeds:seeds=[max(comps,key=lambda c:c['extent'])]
        groups=[[c] for c in seeds]
        for c in comps:
            if any(c is s for s in seeds):continue
            near=min(range(len(seeds)),key=lambda j:(seeds[j]['center']-c['center']).length)
            groups[near].append(c)
    if len(groups)<2:return
    name=o.name;assembly=empty(name+'_ASSEMBLY',o.parent);assembly.matrix_basis=o.matrix_basis.copy()
    bevel=next((m for m in o.modifiers if m.type=='BEVEL'),None)
    for idx,group in enumerate(groups):
        polys=[p for c in group for p in c['polys']];ids=sorted({i for p in polys for i in p.vertices});mapping={old:i for i,old in enumerate(ids)}
        center=sum((me.vertices[i].co for i in ids),Vector())/len(ids)
        piece=bpy.data.meshes.new(name+'_piece');piece.from_pydata([me.vertices[i].co-center for i in ids],[],[tuple(mapping[i] for i in p.vertices) for p in polys]);piece.update()
        for m in me.materials:piece.materials.append(m)
        for dst,src in zip(piece.polygons,polys):dst.material_index=src.material_index;dst.use_smooth=src.use_smooth
        part=bpy.data.objects.new(name+'__PART_%03d'%idx,piece);scene.collection.objects.link(part);part.parent=assembly;part.location=center
        if bevel:mod=part.modifiers.new('Machined edges','BEVEL');mod.width=bevel.width;mod.segments=bevel.segments
        side=-1 if (center.y<0 if mode!='wheel' else '_L' in name) else 1
        if mode=='wheel':delta=(0,side*(idx*.24),0);layer=2+idx*.3
        elif mode=='gun':delta=(max(0,center.x)*.34,0,.10*(idx%3));layer=3
        elif mode=='deck':delta=((center.x-1.0)*.22,center.y*.40,.60+(idx%3)*.16);layer=3
        elif mode=='fender':delta=(center.x*.20,side*.85,.48+(idx%3)*.15);layer=2
        elif mode=='bogie':delta=(center.x*.18,side*.32,.10*(idx%3));layer=2
        elif mode=='roof':delta=(center.x*.4,center.y*.75,2.9+(idx%3)*.18);layer=4
        elif mode=='side':delta=(center.x*.55,side*(1.7+(idx%3)*.20),1.1+(idx%3)*.20);layer=3
        elif mode=='mg':delta=(center.x*.7,center.y*.8,.40+(idx%3)*.22);layer=5
        else:delta=(0,0,.2*idx);layer=3
        offset(part,delta,layer)
    split_stats[name]=len(groups)
    bpy.data.objects.remove(o,do_unlink=True);assembly.name=name

for o in list(root.children_recursive):
    if o.type!='MESH':continue
    n=o.name;mode=None
    if n.endswith('_MESH') and ('WHEEL' in n or 'SPROCKET' in n or 'IDLER' in n):mode='wheel'
    elif n=='GUN_BARREL':mode='gun'
    elif n=='ENGINE_DECK':mode='deck'
    elif n=='FENDERS_AND_TOOLS':mode='fender'
    elif n.startswith('BOGIE_ARMS_'):mode='bogie'
    elif n=='TURRET_ROOF_FITTINGS':mode='roof'
    elif n.startswith('TURRET_SIDE_ACCESSORIES_'):mode='side'
    elif n=='MG_WEAPON':mode='mg'
    if mode:split_mesh(o,mode)

offset(turret,(0,0,3.0),1)
offset(bpy.data.objects['GUN_TRAVERSE_PIVOT'],(2.15,0,.60),2)
offset(bpy.data.objects['GUN_MANTLET'],(.40,0,0),3)
offset(bpy.data.objects['HULL_SPONSONS'],(0,0,.42),1)
offset(bpy.data.objects['HULL_TURRET_DECK'],(0,0,.83),2)
offset(bpy.data.objects['HULL_TURRET_PLINTH'],(0,0,1.08),2)
offset(bpy.data.objects['TURRET_FIXED_BEARING'],(0,0,1.65),2)
offset(bpy.data.objects['DRIVER_NOSE'],(1.35,0,.50),2)
offset(bpy.data.objects['TURRET_ROOF'],(0,0,2.10),3)
offset(bpy.data.objects['TURRET_FLOOR'],(0,0,-.10),1)
offset(bpy.data.objects['TURRET_ROTATING_BEARING'],(0,0,-.65),1)
offset(bpy.data.objects['TURRET_SEAM_COVER'],(0,0,-.37),2)
offset(bpy.data.objects['TURRET_GUN_SEAT'],(1.32,0,.3),3)
offset(bpy.data.objects['MG_MOUNT'],(.6,-.30,3.6),4)
offset(bpy.data.objects['TURRET_REAR_BASKET'],(-1.70,0,1.35),3)
for n in ('FRONT','CHEEK_R','SIDE_R','REAR_CORNER_R','REAR','REAR_CORNER_L','SIDE_L','CHEEK_L'):
    o=bpy.data.objects['TURRET_'+n];center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
    offset(o,(center.x*.72,center.y*.74,.75 if 'SIDE' in n else .95),2)
for side in (-1,1):
    tag='L' if side<0 else 'R'
    offset(bpy.data.objects['SUSPENSION_'+tag],(0,side*1.9,-.05),1)
    offset(bpy.data.objects['TRACKS_'+tag],(0,side*6.2,-.1),2)
    for i in range(6):
        o=bpy.data.objects['ROAD_WHEEL_%s_%02d'%(tag,i)];offset(o,(o.location.x*.25,side*.2,0),2)
    for name in ('FRONT_IDLER','REAR_SPROCKET'):
        o=bpy.data.objects[name+'_'+tag];offset(o,(.8 if name=='FRONT_IDLER' else -.8,side*2.15,.06),2)
    for end in ('FRONT','REAR'):offset(bpy.data.objects['FENDER_'+end+'_'+tag],(1 if end=='FRONT' else -1,side*.65,1.1),2)
    offset(bpy.data.objects['HATCH_'+tag+'_PIVOT'],(-.12,side*.62,3.18),4)
    offset(bpy.data.objects['HATCH_'+tag+'_RIM'],(-.12,side*.3,2.66),4)
for i in (0,1):offset(bpy.data.objects['TURRET_ANTENNA_%d'%i],(-.5,.3 if i==0 else -.3,2.7),4)
for o in track_objects:offset(o,(o.location.x*.95,0,(o.location.z-.78)*1.15),3)
report['split_assemblies']=split_stats
report['independent_mesh_parts']=sum(o.type=='MESH' for o in root.children_recursive)
report['exploding_nodes']=sum('explode_offset_blender' in o for o in root.children_recursive)
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('V5_PARTS',report['independent_mesh_parts'],flush=True)

# Save the assembled master and export real separate parts. Presentation offsets
# are extras, leaving normal movement clips and socket hierarchy unchanged.
scene.frame_set(1);bpy.context.view_layer.update()
points=[o.matrix_world@Vector(v) for o in root.children_recursive if o.type=='MESH' for v in o.bound_box]
lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)]);center=(lo+hi)/2
directions={'ISO':(10,-12,9),'SIDE':(0,-1,0),'TOP':(0,0,1),'FRONT':(1,0,0),'REAR':(-1,0,0),'REAR_ISO':(-10,-12,8)}
for name,d in directions.items():
    cam=bpy.data.objects['VIEW_'+name];d=Vector(d).normalized();cam.location=center+d*25;cam.rotation_euler=(-d).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    projected=[cam.matrix_world.inverted()@v for v in points];xmin,xmax=min(v.x for v in projected),max(v.x for v in projected);ymin,ymax=min(v.y for v in projected),max(v.y for v in projected)
    cam.location+=cam.matrix_world.to_3x3()@Vector(((xmin+xmax)/2,(ymin+ymax)/2,0));cam.data.ortho_scale=max(xmax-xmin,(ymax-ymin)*scene.render.resolution_x/scene.render.resolution_y)*1.14
scene.camera=bpy.data.objects['VIEW_ISO']
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ferdinand_technical.blend'))
game=[]
for m in MATS:
    mat=bpy.data.materials.new('V5 game '+m.name);mat.diffuse_color=m.diffuse_color;mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=m.diffuse_color;bs.inputs['Roughness'].default_value=.68;game.append(mat)
meshes={o.data.name:o.data for o in root.children_recursive if o.type=='MESH'};saved_mats={n:list(me.materials) for n,me in meshes.items()}
for me in meshes.values():
    for i in range(len(me.materials)):me.materials[i]=game[i]
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for o in root.children_recursive:o.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(OUT/'ferdinand_vehicle.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True,export_animation_mode='SCENE',export_animations=True,export_cameras=False,export_lights=False)
for name,me in meshes.items():
    for i,m in enumerate(saved_mats[name]):me.materials[i]=m
(OUT/'vehicle_data.js').write_text('const VEHICLE_GLB="'+base64.b64encode((OUT/'ferdinand_vehicle.glb').read_bytes()).decode()+'";',encoding='utf-8')
print('V5_EXPORT_OK',flush=True)
if '--no-render' not in sys.argv:
    for name in directions:
        scene.camera=bpy.data.objects['VIEW_'+name];scene.render.filepath=str(OUT/('render_'+name.lower()+'.png'));bpy.ops.render.render(write_still=True)
scene.camera=bpy.data.objects['VIEW_ISO'];scene.render.filepath=str(OUT/'render_iso.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ferdinand_technical.blend'))
print('FD184R_V5_BUILD_OK',json.dumps(report),flush=True)
