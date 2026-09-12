import bpy,json,struct,math
from pathlib import Path
from mathutils import Vector
out=Path(__file__).resolve().parents[2]/'assets'/'3d'/'ferdinand_v3'
bpy.ops.wm.open_mainfile(filepath=str(out/'ferdinand_technical.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
root=bpy.data.objects['FERDINAND_ROOT'];deps=bpy.context.evaluated_depsgraph_get()
v=[];triangles=0
for obj in root.children_recursive:
 if obj.type!='MESH':continue
 e=obj.evaluated_get(deps);me=e.to_mesh();v.extend([e.matrix_world@a.co for a in me.vertices]);me.calc_loop_triangles();triangles+=len(me.loop_triangles);e.to_mesh_clear()
actual=[max(p[i] for p in v)-min(p[i] for p in v) for i in range(3)]
required=['FERDINAND_ROOT','GUN_TRAVERSE_PIVOT','GUN_PITCH_PIVOT','GUN_RECOIL_ROOT','SOCKET_MUZZLE','HATCH_L_PIVOT','HATCH_R_PIVOT','TRACKS_L','TRACKS_R']
assert all(n in bpy.data.objects for n in required)
assert len([o for o in root.children_recursive if '_LINK_' in o.name])==212
scene.frame_set(1);muzzle0=bpy.data.objects['SOCKET_MUZZLE'].matrix_world.translation.copy()
scene.frame_set(186);bpy.context.view_layer.update();muzzle1=bpy.data.objects['SOCKET_MUZZLE'].matrix_world.translation.copy()
assert .22<(muzzle1-muzzle0).length<.24
scene.frame_set(250);assert abs(math.degrees(bpy.data.objects['HATCH_L_PIVOT'].rotation_euler.y)-80)<.01
glb=(out/'ferdinand_vehicle.glb').read_bytes();assert glb[:4]==b'glTF';assert struct.unpack_from('<I',glb,4)[0]==2
n=struct.unpack_from('<I',glb,12)[0];doc=json.loads(glb[20:20+n]);assert not doc.get('cameras');assert len(doc.get('animations',[]))>=1
report={'actual_mesh_size_m':actual,'triangles_with_all_track_instances':triangles,'blender_object_count':len(list(root.children_recursive))+1,'glb_node_count':len(doc['nodes']),'glb_mesh_count':len(doc['meshes']),'animation_clips':len(doc.get('animations',[])),'muzzle_follows_recoil_m':(muzzle1-muzzle0).length,'hatch_open_deg':80,'result':'PASS'}
assert scene.frame_end==385
fx=bpy.data.collections.get('PRESENTATION_FIRE_FX');assert fx and len(fx.objects)==18
scene.frame_set(303);bpy.context.view_layer.update();assert abs(bpy.data.objects['GUN_RECOIL_ROOT'].location.x+.23)<.001
flash=bpy.data.objects['FX_FLASH_LOBE_00'];assert flash.scale.x>.9
scene.frame_set(331);assert abs(bpy.data.objects['GUN_RECOIL_ROOT'].location.x)<.001
scene.frame_set(385);assert flash.scale.x<.001
max_animation_time=max(doc['accessors'][s['input']]['max'][0] for a in doc['animations'] for s in a['samplers'])
assert max_animation_time>=385/30-.001
report.update({'shot_frames':[301,385],'shot_recoil_peak_m':.23,'presentation_fx_objects':len(fx.objects),'glb_contains_shot_recoil':True})
(out/'asset_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ASSET_QA_OK',json.dumps(report))
