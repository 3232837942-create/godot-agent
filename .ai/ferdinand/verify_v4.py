import bpy,json,struct,hashlib,math
from pathlib import Path
from mathutils import Vector
out=Path(__file__).resolve().parents[2]/'assets'/'3d'/'ferdinand_v4'
bpy.ops.wm.open_mainfile(filepath=str(out/'ferdinand_technical.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
root=bpy.data.objects['FERDINAND_ROOT'];turret=bpy.data.objects['TURRET_YAW_PIVOT']
for name in ('MG_MOUNT','TURRET_ANTENNA_0','TURRET_ANTENNA_1','TURRET_SIDE_ACCESSORIES_L','TURRET_SIDE_ACCESSORIES_R','TURRET_REAR_BASKET','HATCH_L_PIVOT','HATCH_R_PIVOT','GUN_TRAVERSE_PIVOT'):
    o=bpy.data.objects[name];assert o.parent==turret,name
assert bpy.data.objects['TURRET_FIXED_BEARING'].parent==root
roof=bpy.data.objects['TURRET_ROOF'].evaluated_get(bpy.context.evaluated_depsgraph_get())
for side in (-1,1):assert not roof.ray_cast(Vector((-.42,side*.61,1.4)),Vector((0,0,-1)),distance=1)[0],'Roof opening blocked'
assert len([o for o in root.children_recursive if '_LINK_' in o.name])==212
track=bpy.data.objects['TRACKS_L_LINK_000'];track_rest=track.matrix_world.copy()
mount=bpy.data.objects['MG_MOUNT'];mount_rest=mount.matrix_world.translation.copy()
scene.frame_set(431);bpy.context.view_layer.update();assert abs(math.degrees(turret.rotation_euler.z)-90)<.01
assert (mount.matrix_world.translation-mount_rest).length>.5
scene.frame_set(521);assert abs(math.degrees(turret.rotation_euler.z)-360)<.01
scene.frame_set(250);assert abs(math.degrees(bpy.data.objects['HATCH_L_PIVOT'].rotation_euler.y)-80)<.01
scene.frame_set(301);bpy.context.view_layer.update();s=bpy.data.objects['SOCKET_MUZZLE'];m0=s.matrix_world.translation.copy()
scene.frame_set(303);bpy.context.view_layer.update();assert abs((s.matrix_world.translation-m0).length-.23)<.001
assert len(bpy.data.collections['PRESENTATION_FIRE_FX'].objects)==18
scene.frame_set(1);bpy.context.view_layer.update()
v=[];tri=0
for o in root.children_recursive:
    if o.type!='MESH':continue
    e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();me.calc_loop_triangles();tri+=len(me.loop_triangles);v.extend([e.matrix_world@a.co for a in me.vertices]);e.to_mesh_clear()
data=(out/'ferdinand_vehicle.glb').read_bytes();assert data[:4]==b'glTF' and struct.unpack_from('<I',data,4)[0]==2
n=struct.unpack_from('<I',data,12)[0];g=json.loads(data[20:20+n]);assert any(a['name']=='TURRET_YAW_PIVOT' for a in g['nodes'])
assert max(g['accessors'][s['input']]['max'][0] for a in g['animations'] for s in a['samplers'])>=540/30-.001
base=out.parent/'ferdinand_v3';backup=Path(__file__).resolve().parent/'backups'/'pre-rotating-turret-20260911-124233'/'ferdinand_v3'
for name in ('ferdinand_technical.blend','ferdinand_vehicle.glb','viewer.js','fire_effects.js'):
    assert hashlib.sha256((base/name).read_bytes()).digest()==hashlib.sha256((backup/name).read_bytes()).digest(),name+' original changed'
report={'result':'PASS','vehicle_nodes':len(list(root.children_recursive))+1,'triangles_with_track_instances':tri,'dimensions_m':[max(p[i] for p in v)-min(p[i] for p in v) for i in range(3)],'glb_nodes':len(g['nodes']),'glb_meshes':len(g['meshes']),'glb_animation_clips':len(g['animations']),'turret_rotation_deg':360,'roof_apertures_open':True,'attachments_follow_turret':True,'recoil_m':.23,'original_v3_unchanged':True,'presentation_fx_objects':18}
(out/'asset_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('V4_ASSET_OK',json.dumps(report))
