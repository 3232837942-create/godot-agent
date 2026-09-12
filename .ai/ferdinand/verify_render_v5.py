"""Reopen the delivered V5 master, validate preservation and render actual views."""
import bpy,json,struct,math,hashlib,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;OUT=HERE.parents[1]/'assets'/'3d'/'ferdinand_v5'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'ferdinand_technical.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
root=bpy.data.objects['FERDINAND_ROOT'];turret=bpy.data.objects['TURRET_YAW_PIVOT']
assert abs(turret.location.z-1.96)<.0001
assert len([o for o in root.children_recursive if o.type=='MESH'])==575
assert len([o for o in root.children_recursive if o.name.endswith('_ARMOR')])==14
assert len([o for o in root.children_recursive if '_LINK_' in o.name])==212
track=bpy.data.objects['TRACKS_L_LINK_000'];track_start=track.location.copy()
scene.frame_set(16);assert (track.location-track_start).length>.025,'Track animation did not advance'
scene.frame_set(1)
assert bpy.data.objects['TURRET_SEAM_COVER'].parent==turret
for name in ('MG_MOUNT','TURRET_ANTENNA_0','TURRET_SIDE_ACCESSORIES_L','HATCH_L_PIVOT'):
    assert bpy.data.objects[name].parent==turret
roof=bpy.data.objects['TURRET_ROOF'].evaluated_get(bpy.context.evaluated_depsgraph_get())
for side in (-1,1):assert not roof.ray_cast(Vector((-.42,side*.61,1.4)),Vector((0,0,-1)),distance=1)[0]
scene.frame_set(431);assert abs(math.degrees(turret.rotation_euler.z)-90)<.01
scene.frame_set(521);assert abs(math.degrees(turret.rotation_euler.z)-360)<.01
scene.frame_set(250);assert abs(math.degrees(bpy.data.objects['HATCH_L_PIVOT'].rotation_euler.y)-80)<.01
scene.frame_set(303);assert abs(bpy.data.objects['GUN_RECOIL_ROOT'].location.x+.23)<.0001
base=OUT.parent/'ferdinand_v4';backup=HERE/'backups'/'pre-skirts-parts-20260911-164838'/'ferdinand_v4'
for p in base.iterdir():
    if p.is_file():assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256((backup/p.name).read_bytes()).digest(),p.name
data=(OUT/'ferdinand_vehicle.glb').read_bytes();assert data[:4]==b'glTF' and struct.unpack_from('<I',data,4)[0]==2
g=json.loads(data[20:20+struct.unpack_from('<I',data,12)[0]])
assert sum('mesh' in n for n in g['nodes'])==575
assert sum('explode_offset_blender' in n.get('extras',{}) for n in g['nodes'])==596
assert all(len(n['extras']['explode_offset_blender'])==3 for n in g['nodes'] if 'explode_offset_blender' in n.get('extras',{}))
for n in g['nodes']:
    if 'explode_offset_blender' in n.get('extras',{}):
        actual=list(bpy.data.objects[n['name']]['explode_offset_blender'])
        assert all(abs(a-b)<1e-6 for a,b in zip(actual,n['extras']['explode_offset_blender'])),n['name']
report={'result':'PASS','mesh_parts':575,'track_links':212,'track_animation_advances':True,'skirt_panels':14,'source_nodes':len(root.children_recursive)+1,'glb_nodes':len(g['nodes']),'glb_meshes':len(g['meshes']),'preserved_v4_files':sum(p.is_file() for p in base.iterdir()),'v4_backup_hashes_match':True,'turret_360':True,'hatches_open':True,'recoil_m':.23,'roof_apertures_open':True,'explosion':'575 real mesh parts, authored staged offsets; interactive presentation in viewer, not a glTF physics rig'}
(OUT/'asset_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('V5_ASSET_OK',json.dumps(report),flush=True)
scene.frame_set(1)
if '--no-render' not in sys.argv:
    for name in ('ISO','SIDE','FRONT','REAR','TOP','REAR_ISO'):
        scene.camera=bpy.data.objects['VIEW_'+name];scene.render.filepath=str(OUT/('render_'+name.lower()+'.png'));bpy.ops.render.render(write_still=True);print('V5_VIEW_DONE',name,flush=True)
    print('V5_VIEWS_OK',flush=True)
