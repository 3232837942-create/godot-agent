# Ferdinand Asset Contract

This directory contains the first playable-asset blockout for the Sd.Kfz. 184 Ferdinand.
It establishes the scene hierarchy, animation pivots, export sockets, and Blender-to-Godot
handoff. It is not yet a historically exhaustive production model.

## Files

- `ferdinand_master.blend`: Blender source of truth.
- `ferdinand_preview.glb`: Godot import target for the viewer and future game prototype.
- `ferdinand_preview.png`: visual baseline for review.
- `../../../.ai/ferdinand/build_ferdinand.py`: repeatable Blender 5.2 build script.

## Coordinate and Scale Contract

- Blender unit: meter.
- Vehicle forward: positive X.
- Vehicle up: positive Z.
- Root node: `FERDINAND_ROOT`.
- The prototype is laid out against Ferdinand's published overall dimensions of roughly
  8.14 m x 3.38 m x 2.97 m. Individual armor plates and fittings still require reference
  drawing verification before it is called historically accurate.

## Required Runtime Nodes

- `TRACKS_L`, `TRACKS_R`: track animation parents.
- `GUN_TRAVERSE_PIVOT`: limited left/right weapon traverse. It is not a turret node.
- `GUN_PITCH_PIVOT`: gun elevation.
- `GUN_RECOIL_ROOT`: recoil animation parent.
- `HATCH_L_PIVOT`, `HATCH_R_PIVOT`: hatch animation parents.
- `SOCKET_MUZZLE`, `SOCKET_SMOKE`, `SOCKET_ENGINE_DAMAGE`, `SOCKET_AMMO_DAMAGE`,
  `SOCKET_CREW`, `SOCKET_CAMERA_THIRD`: gameplay and effects attachment points.

## Animation Scope

Current source contains animation keys for tracks, gun elevation, gun recoil, and hatches.
The Godot viewer must expose only historically plausible controls: camera views, vehicle
drive state, gun elevation, limited gun traverse, recoil/fire, hatch state, smoke, and a
non-gameplay exploded inspection view. Do not add turret rotation because Ferdinand has a
fixed superstructure.

## Production Stages

1. Replace the blockout plates, running gear, exhausts, tools, welds, and fittings from a
   selected 1943 Ferdinand reference set. Keep all required runtime node names unchanged.
2. Make LOD0 through LOD3 and collision meshes. Keep road wheels, tracks, gun, hatches,
   and damage modules separate at LOD0 and LOD1.
3. Bake PBR materials: Dunkelgelb base paint, oxidized track steel, rubber, wood, glass,
   dust, and mud masks.
4. Add the Godot inspection scene and input controller. Run it only after a Godot 4.6
   executable is available locally; the repository alone is not the engine runtime.
5. Add gameplay-specific collision, hit zones, particle effects, audio, and damaged-track
   states only after the viewer validates the imported GLB hierarchy.
