import math
import os

import bpy
from mathutils import Vector


PROJECT = r"X:\迅雷下载\godot-agent"
ASSET_DIR = os.path.join(PROJECT, "assets", "3d", "ferdinand")
BLEND_OUT = os.path.join(ASSET_DIR, "ferdinand_master.blend")
GLB_OUT = os.path.join(ASSET_DIR, "ferdinand_preview.glb")
PREVIEW_OUT = os.path.join(ASSET_DIR, "ferdinand_preview.png")
os.makedirs(ASSET_DIR, exist_ok=True)


def material(name, color, metallic=0.0, roughness=0.65):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return result


# Technical-illustration palette. Freestyle supplies the visible navy edge treatment.
ARMOR = material("MAT_Armor_Illustration", (0.80, 0.84, 0.83), 0.10, 0.70)
ARMOR_DARK = material("MAT_Armor_Recess", (0.35, 0.42, 0.43), 0.25, 0.68)
TRACK = material("MAT_Track_Steel", (0.15, 0.20, 0.22), 0.68, 0.42)
RUBBER = material("MAT_Rubber", (0.035, 0.055, 0.062), 0.0, 0.87)
OPTICS = material("MAT_Optics", (0.08, 0.28, 0.31), 0.30, 0.18)
MARKING = material("MAT_Marking", (0.035, 0.07, 0.10), 0.0, 0.60)
FLOOR = material("MAT_Drawing_Floor", (0.85, 0.89, 0.89), 0.0, 0.96)
GRID = material("MAT_Drawing_Grid", (0.20, 0.39, 0.45), 0.0, 0.78)


bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
    for item in list(block):
        if item.users == 0:
            block.remove(item)


root = bpy.data.objects.new("FERDINAND_ROOT", None)
bpy.context.collection.objects.link(root)
root["vehicle"] = "Sd.Kfz. 184 Ferdinand"
root["variant"] = "early production inspired"
root["coordinate_contract"] = "+X forward, +Z up, meters"
root["asset_status"] = "structured line-art preview and future game blockout"


def parent(obj, parent_node=root):
    obj.parent = parent_node
    return obj


def empty(name, location=(0, 0, 0), parent_node=root):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    return parent(obj, parent_node)


def cube(name, location, size, mat, parent_node=root, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    parent(obj, parent_node)
    if bevel:
        modifier = obj.modifiers.new("Edge_Radius", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def cylinder(name, location, radius, depth, mat, parent_node=root, rotation=(0, 0, 0), vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return parent(obj, parent_node)


def torus(name, location, major_radius, minor_radius, mat, parent_node=root, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=20,
        minor_segments=8,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return parent(obj, parent_node)


def prism(name, vertices, faces, mat, parent_node=root):
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return parent(obj, parent_node)


def tapered_box(name, front_x, rear_x, bottom_z, top_z, bottom_half_width, top_half_width, mat, parent_node=root):
    # +X is vehicle front. The front and rear faces are both deliberately sloped.
    vertices = [
        (front_x, -bottom_half_width, bottom_z), (front_x, bottom_half_width, bottom_z),
        (rear_x, -bottom_half_width, bottom_z), (rear_x, bottom_half_width, bottom_z),
        (front_x - 0.24, -top_half_width, top_z), (front_x - 0.24, top_half_width, top_z),
        (rear_x + 0.24, -top_half_width, top_z), (rear_x + 0.24, top_half_width, top_z),
    ]
    faces = [(0, 2, 3, 1), (0, 4, 6, 2), (1, 3, 7, 5), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3)]
    return prism(name, vertices, faces, mat, parent_node)


def add_rivet(name, location, parent_node=root, radius=0.045):
    return cylinder(name, location, radius, 0.025, MARKING, parent_node, (math.pi * 0.5, 0, 0), 12)


def animate_rotation(obj, axis, start, end, frame_start, frame_end):
    obj.rotation_mode = "XYZ"
    obj.rotation_euler[axis] = start
    obj.keyframe_insert(data_path="rotation_euler", index=axis, frame=frame_start)
    obj.rotation_euler[axis] = end
    obj.keyframe_insert(data_path="rotation_euler", index=axis, frame=frame_end)


def animate_location_x(obj, values):
    for frame, value in values:
        obj.location.x = value
        obj.keyframe_insert(data_path="location", index=0, frame=frame)


def wheel(side, index, x):
    side_name = "L" if side < 0 else "R"
    y = side * 1.62
    parent_node = empty("BOGIE_%s_%02d" % (side_name, index), (0, 0, 0))
    parent_node["damage_group"] = "suspension_%s_%02d" % (side_name.lower(), index)
    cylinder("ROAD_WHEEL_%s_%02d" % (side_name, index), (x, y, 0.76), 0.54, 0.22, TRACK, parent_node, (math.pi * 0.5, 0, 0), 20)
    torus("ROAD_WHEEL_RIM_%s_%02d" % (side_name, index), (x, side * 1.755, 0.76), 0.38, 0.055, RUBBER, parent_node, (math.pi * 0.5, 0, 0))
    cylinder("ROAD_WHEEL_HUB_%s_%02d" % (side_name, index), (x, side * 1.79, 0.76), 0.13, 0.055, ARMOR_DARK, parent_node, (math.pi * 0.5, 0, 0), 12)
    for spoke in range(8):
        angle = spoke * math.tau / 8.0
        cylinder(
            "ROAD_WHEEL_BOLT_%s_%02d_%02d" % (side_name, index, spoke),
            (x + math.cos(angle) * 0.25, side * 1.805, 0.76 + math.sin(angle) * 0.25),
            0.026,
            0.035,
            ARMOR_DARK,
            parent_node,
            (math.pi * 0.5, 0, 0),
            10,
        )
    return parent_node


def add_track(side):
    side_name = "L" if side < 0 else "R"
    track_root = empty("TRACKS_" + side_name)
    track_root["runtime_control"] = "track_roll"
    y = side * 1.82
    link_index = 0
    for x in [(-2.68 + 0.19 * i) for i in range(30)]:
        cube("TRACK_%s_TOP_%02d" % (side_name, link_index), (x, y, 1.56), (0.105, 0.105, 0.075), TRACK, track_root, 0.022)
        link_index += 1
    for x in [(2.83 - 0.19 * i) for i in range(30)]:
        cube("TRACK_%s_BOTTOM_%02d" % (side_name, link_index), (x, y, 0.15), (0.105, 0.105, 0.075), TRACK, track_root, 0.022)
        link_index += 1
    for direction, center_x in ((1, 2.90), (-1, -2.90)):
        for step in range(10):
            angle = -math.pi * 0.5 + math.pi * (step + 0.5) / 10.0
            x = center_x + direction * math.cos(angle) * 0.70
            z = 0.855 + math.sin(angle) * 0.705
            link = cube("TRACK_%s_END_%02d" % (side_name, link_index), (x, y, z), (0.10, 0.105, 0.075), TRACK, track_root, 0.022)
            link.rotation_euler.y = direction * -angle
            link_index += 1
    animate_rotation(track_root, 1, 0.0, math.tau, 1, 64)


# Low hull, six Porsche-style road wheels per side, front sprocket and rear idler.
cube("HULL_LOWER", (0.0, 0.0, 1.02), (3.18, 1.45, 0.60), ARMOR, bevel=0.07)
tapered_box("FRONT_ENGINE_HOOD", 3.20, 0.36, 1.42, 2.12, 1.42, 1.30, ARMOR)
cube("FRONT_GLACIS", (3.24, 0.0, 1.35), (0.10, 1.42, 0.33), ARMOR_DARK, bevel=0.025)
cube("REAR_HULL_PLATE", (-3.18, 0.0, 1.36), (0.10, 1.45, 0.40), ARMOR_DARK, bevel=0.025)

for side in (-1, 1):
    side_name = "L" if side < 0 else "R"
    cube("SIDE_SUSPENSION_PLATE_" + side_name, (0.0, side * 1.52, 1.02), (3.07, 0.055, 0.52), ARMOR_DARK, bevel=0.015)
    cylinder("DRIVE_SPROCKET_" + side_name, (3.07, side * 1.66, 0.87), 0.66, 0.20, TRACK, rotation=(math.pi * 0.5, 0, 0), vertices=18)
    torus("DRIVE_SPROCKET_RIM_" + side_name, (3.07, side * 1.78, 0.87), 0.54, 0.070, RUBBER, rotation=(math.pi * 0.5, 0, 0))
    cylinder("IDLER_" + side_name, (-3.10, side * 1.66, 0.87), 0.60, 0.18, TRACK, rotation=(math.pi * 0.5, 0, 0), vertices=18)
    torus("IDLER_RIM_" + side_name, (-3.10, side * 1.77, 0.87), 0.47, 0.055, RUBBER, rotation=(math.pi * 0.5, 0, 0))
    for index, x in enumerate((2.18, 1.32, 0.46, -0.40, -1.26, -2.12), 1):
        wheel(side, index, x)
    cube("FENDER_FRONT_" + side_name, (2.30, side * 1.76, 1.72), (0.92, 0.10, 0.055), TRACK, bevel=0.012)
    cube("FENDER_REAR_" + side_name, (-2.46, side * 1.76, 1.68), (0.56, 0.10, 0.055), TRACK, bevel=0.012)
    add_track(side)

# Early Ferdinand fixed casemate: it sits aft of the engine hood and has no turret.
tapered_box("FIXED_CASEMATE", 0.30, -3.04, 1.48, 3.23, 1.39, 1.18, ARMOR)
cube("CASEMATE_ROOF", (-1.42, 0.0, 3.25), (1.48, 1.17, 0.065), ARMOR, bevel=0.035)
cube("CASEMATE_REAR_LIP", (-2.88, 0.0, 2.96), (0.10, 1.23, 0.17), ARMOR_DARK, bevel=0.025)

# Front deck sits beneath the long 8.8 cm gun and carries two symmetrical radiator grilles.
cube("ENGINE_DECK", (1.36, 0.0, 2.08), (0.92, 1.28, 0.06), ARMOR, bevel=0.025)
for side in (-1, 1):
    side_name = "L" if side < 0 else "R"
    cube("RADIATOR_GRILLE_" + side_name, (1.30, side * 0.72, 2.16), (0.42, 0.35, 0.025), ARMOR_DARK, bevel=0.018)
    for line in range(7):
        cube("GRILLE_SLAT_%s_%02d" % (side_name, line), (1.30, side * (0.48 + line * 0.08), 2.20), (0.35, 0.013, 0.035), MARKING, bevel=0.004)

# Gun: only limited traverse and elevation; its root is exactly on the casemate front face.
gun_traverse = empty("GUN_TRAVERSE_PIVOT", (0.31, 0.0, 2.50))
gun_traverse["runtime_control"] = "gun_traverse_limited"
gun_pitch = empty("GUN_PITCH_PIVOT", (0.0, 0.0, 0.0), gun_traverse)
gun_pitch["runtime_control"] = "gun_elevation"
recoil_root = empty("GUN_RECOIL_ROOT", (0.0, 0.0, 0.0), gun_pitch)
recoil_root["runtime_control"] = "gun_recoil"
cylinder("GUN_MANTLET", (0.0, 0.0, 0.0), 0.43, 0.42, ARMOR_DARK, gun_pitch, (0.0, math.pi * 0.5, 0.0), 20)
cylinder("PAK_43_BARREL", (2.31, 0.0, 0.0), 0.145, 4.25, TRACK, recoil_root, (0.0, math.pi * 0.5, 0.0), 20)
cylinder("PAK_43_MUZZLE", (4.60, 0.0, 0.0), 0.22, 0.52, TRACK, recoil_root, (0.0, math.pi * 0.5, 0.0), 20)
cylinder("PAK_43_BREECH_COLLAR", (0.32, 0.0, 0.0), 0.24, 0.46, TRACK, recoil_root, (0.0, math.pi * 0.5, 0.0), 18)
animate_rotation(gun_traverse, 2, math.radians(-8.0), math.radians(8.0), 1, 80)
animate_rotation(gun_pitch, 1, math.radians(-6.0), math.radians(10.0), 1, 64)
animate_location_x(recoil_root, ((1, 0.0), (9, -0.20), (23, 0.0)))

# Roof hatches, vents, lifting hooks and side fasteners are all separate gameplay-ready objects.
for index, (x, y, radius) in enumerate(((-1.82, -0.56, 0.34), (-1.82, 0.56, 0.34), (-0.68, -0.52, 0.28), (-0.68, 0.52, 0.28))):
    pivot = empty("HATCH_%02d_PIVOT" % index, (x, y, 3.36))
    pivot["runtime_control"] = "hatch"
    cylinder("HATCH_%02d" % index, (0.0, 0.0, 0.0), radius, 0.055, ARMOR_DARK, pivot, vertices=16)
    animate_rotation(pivot, 1, 0.0, math.radians(70.0), 1, 44)

for x in (-2.56, -2.15, -1.74):
    cube("REAR_VENT_" + str(x).replace("-", "n").replace(".", "_"), (x, 0.0, 3.34), (0.14, 0.52, 0.030), ARMOR_DARK, bevel=0.008)

for side in (-1, 1):
    side_name = "L" if side < 0 else "R"
    for index, x in enumerate((-2.65, -2.12, -1.58, -1.05, -0.48, 0.06)):
        add_rivet("CASEMATE_RIVET_%s_%02d" % (side_name, index), (x, side * 1.42, 2.02))
    for index, x in enumerate((2.75, 1.95, 1.12, 0.30)):
        add_rivet("HULL_RIVET_%s_%02d" % (side_name, index), (x, side * 1.47, 1.45))
    cube("TOW_CABLE_" + side_name, (2.32, side * 1.50, 1.90), (0.70, 0.025, 0.025), TRACK, bevel=0.008)

# Balkenkreuz is simplified as separate shapes, so it can be hidden in game camouflage variants.
cross_parent = empty("MARKING_BALKENKREUZ_L", (-1.20, -1.425, 2.36))
cross_parent["variant_component"] = "marking"
cube("MARKING_VERTICAL", (0.0, 0.0, 0.0), (0.055, 0.018, 0.29), MARKING, cross_parent)
cube("MARKING_HORIZONTAL", (0.0, 0.0, 0.0), (0.29, 0.018, 0.055), MARKING, cross_parent)

for name, location in {
    "SOCKET_MUZZLE": (5.18, 0.0, 2.50),
    "SOCKET_SMOKE": (-2.84, 0.0, 3.16),
    "SOCKET_ENGINE_DAMAGE": (1.55, 0.0, 2.15),
    "SOCKET_AMMO_DAMAGE": (-1.48, 0.0, 2.45),
    "SOCKET_CREW": (-1.82, 0.0, 3.42),
    "SOCKET_CAMERA_THIRD": (-8.5, -8.5, 5.5),
}.items():
    socket = empty(name, location)
    socket["socket"] = True

# A light technical grid gives the render the drafting language of the supplied reference.
bpy.ops.mesh.primitive_plane_add(size=32, location=(0, 0, -0.04))
floor = bpy.context.object
floor.name = "PREVIEW_DRAWING_FLOOR"
floor.data.materials.append(FLOOR)
for index in range(-16, 17):
    thickness = 0.010 if index % 4 else 0.018
    cube("GRID_X_%02d" % (index + 16), (index, 0, -0.018), (thickness, 16, 0.004), GRID)
    cube("GRID_Y_%02d" % (index + 16), (0, index, -0.017), (16, thickness, 0.004), GRID)


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, location, target, focal_length=58):
    bpy.ops.object.camera_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.lens = focal_length
    look_at(obj, target)
    return obj


camera_iso = camera("PREVIEW_CAMERA_ISO", (11.3, -12.8, 7.3), (-0.20, 0.0, 1.55), 58)
camera_side = camera("PREVIEW_CAMERA_SIDE", (0.0, -17.0, 2.0), (0.0, 0.0, 1.65), 66)
camera_top = camera("PREVIEW_CAMERA_TOP", (0.0, 0.0, 17.0), (0.0, 0.0, 1.35), 58)
camera_front = camera("PREVIEW_CAMERA_FRONT", (15.0, 0.0, 2.55), (0.0, 0.0, 1.7), 66)
camera_rear = camera("PREVIEW_CAMERA_REAR", (-14.0, 0.0, 2.55), (0.0, 0.0, 1.7), 66)
for view_camera, scale in ((camera_side, 8.8), (camera_top, 8.4), (camera_front, 6.6), (camera_rear, 6.6)):
    view_camera.data.type = "ORTHO"
    view_camera.data.ortho_scale = scale
bpy.context.scene.camera = camera_iso

for name, location, energy, size in (
    ("KEY", (4.0, -7.0, 10.0), 1200, 7.0),
    ("FILL", (-6.0, -2.0, 6.0), 750, 8.0),
    ("RIM", (-4.0, 7.0, 8.0), 950, 6.0),
):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = "PREVIEW_LIGHT_" + name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.data.color = (0.83, 0.93, 1.0)
    look_at(light, (0.0, 0.0, 1.5))

world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.86, 0.90, 0.91, 1.0)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.32

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1400
scene.render.resolution_y = 920
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.film_transparent = False
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 80
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "METERS"
scene.render.use_freestyle = True
lineset = scene.view_layers["ViewLayer"].freestyle_settings.linesets[0]
lineset.linestyle.color = (0.018, 0.060, 0.095)
lineset.linestyle.thickness = 1.15

# Save source first, then render the isometric technical-illustration baseline.
bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT)
scene.render.filepath = PREVIEW_OUT
bpy.ops.render.render(write_still=True)
for view_name, view_camera in {
    "side": camera_side,
    "top": camera_top,
    "front": camera_front,
    "rear": camera_rear,
}.items():
    scene.camera = view_camera
    scene.render.filepath = os.path.join(ASSET_DIR, "ferdinand_%s.png" % view_name)
    bpy.ops.render.render(write_still=True)
scene.camera = camera_iso

# Game export excludes cameras, lights, drawing grid, and floor; only the authored vehicle hierarchy goes to Godot.
bpy.ops.object.select_all(action="DESELECT")
for obj in (root, *list(root.children_recursive)):
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
try:
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_animations=True,
        export_extras=True,
        export_apply=True,
    )
except TypeError:
    bpy.ops.export_scene.gltf(
        filepath=GLB_OUT,
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_animations=True,
        export_extras=True,
    )

print("FERDINAND_BUILD_OK", BLEND_OUT, GLB_OUT, PREVIEW_OUT)
