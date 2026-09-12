"""Add separately organized presentation FX to the Blender master, after game export."""
import bpy, math
from pathlib import Path
from mathutils import Vector

out=Path(globals().get('ASSET_OUT',Path(__file__).resolve().parents[2]/'assets'/'3d'/'ferdinand_v3'))
bpy.ops.wm.open_mainfile(filepath=str(out/'ferdinand_technical.blend'))
scene=bpy.context.scene; scene.frame_set(301); bpy.context.view_layer.update()
old=bpy.data.collections.get('PRESENTATION_FIRE_FX')
if old:
    for o in list(old.objects): bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(old)
collection=bpy.data.collections.new('PRESENTATION_FIRE_FX');scene.collection.children.link(collection)
socket=bpy.data.objects['SOCKET_MUZZLE'];origin=socket.matrix_world.translation.copy()

def move_to_fx(o):
    for c in list(o.users_collection):c.objects.unlink(o)
    collection.objects.link(o);o['purpose']='Presentation-only firing effect; excluded from vehicle GLB'
    return o
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    n=m.node_tree.nodes;n.clear();tr=n.new('ShaderNodeBsdfTransparent');em=n.new('ShaderNodeEmission');em.inputs[0].default_value=(*color,1)
    mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=0
    m.node_tree.links.new(tr.outputs[0],mix.inputs[1]);m.node_tree.links.new(em.outputs[0],mix.inputs[2]);o=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(mix.outputs[0],o.inputs[0]);return m,mix.inputs[0]
def alpha_keys(inp,values):
    for fr,v in values:inp.default_value=v;inp.keyframe_insert('default_value',frame=fr)
def key_pose(o,fr,loc,scale):
    o.location=loc;o.scale=scale;o.keyframe_insert('location',frame=fr);o.keyframe_insert('scale',frame=fr)

flash=move_to_fx(bpy.data.objects.new('FX_MUZZLE_FLASH_ROOT',None))
constraint=flash.constraints.new('COPY_TRANSFORMS');constraint.target=socket
for idx,(angle,size) in enumerate(((0,1),(1.25,.57),(-1.25,.57))):
    bpy.ops.mesh.primitive_cone_add(vertices=9,radius1=.25,radius2=0,depth=1.0)
    o=move_to_fx(bpy.context.object);o.name='FX_FLASH_LOBE_%02d'%idx;o.parent=flash
    direction=Vector((math.cos(angle),math.sin(angle),0));o.rotation_euler=direction.to_track_quat('Z','Y').to_euler()
    m,a=material(o.name+' material',(.96,.60,.25));o.data.materials.append(m)
    alpha_keys(a,[(1,0),(301,0),(302,.85),(305,.6),(308,0),(385,0)])
    for fr,s in ((1,.0001),(301,.0001),(303,size),(305,size*.72),(308,.0001),(385,.0001)):key_pose(o,fr,direction*.48*size,(s,s,s))

for i in range(14):
    side=1 if i%2 else -1;seed=(math.sin(i*78.233+4)*43758.5453)%1
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1)
    o=move_to_fx(bpy.context.object);o.name='FX_MUZZLE_SMOKE_%02d'%i
    for p in o.data.polygons:p.use_smooth=True
    m,a=material(o.name+' material',(.43,.52,.61));o.data.materials.append(m)
    start=306+i%5;end=370+i%5
    alpha_keys(a,[(1,0),(start,0),(start+4,.13),(start+18,.10),(end,0),(385,0)])
    for fr,t in ((1,0),(start,0),(start+6,.2),(start+23,.8),(end,2.3),(385,2.8)):
        loc=origin+Vector((.1+seed*.24+t*(.4 if i<6 else 1.0),side*(.12+t*(.5 if i<6 else .13)),t*(.20+seed*.18)))
        r=.025+(t**.5)*.24+seed*.05 if fr>start else .0001
        key_pose(o,fr,loc,(r*(1+seed*.3),r,r*.9))
for act in bpy.data.actions:
    if not act.name.startswith('FX_'):continue
    for layer in act.layers:
        for strip in layer.strips:
            if hasattr(strip,'channelbags'):
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:key.interpolation='LINEAR'
for ls in scene.view_layers[0].freestyle_settings.linesets:
    ls.select_by_collection=True;ls.collection=collection;ls.collection_negation='EXCLUSIVE'
scene.frame_set(304);scene.camera=bpy.data.objects['VIEW_ISO'];scene.render.filepath=str(out/'render_fire.png')
bpy.ops.render.render(write_still=True)
scene.frame_set(1);scene.render.filepath=str(out/'render_iso.png');bpy.ops.wm.save_as_mainfile(filepath=str(out/'ferdinand_technical.blend'))
print('BLENDER_FIRE_FX_OK',len(collection.objects))
