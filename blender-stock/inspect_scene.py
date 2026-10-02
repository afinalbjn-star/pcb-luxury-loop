"""Print a scene inventory so CI logs show what was actually loaded."""

import bpy

scene = bpy.context.scene
counts = {}
for ob in scene.objects:
    counts[ob.type] = counts.get(ob.type, 0) + 1

print("[inventory] objects=%d %s" % (len(scene.objects), counts))
print("[inventory] materials=%d meshes=%d curves=%d lights=%d"
      % (len(bpy.data.materials), len(bpy.data.meshes), len(bpy.data.curves),
         len(bpy.data.lights)))
print("[inventory] engine=%s %dx%d @%dfps frames %d-%d"
      % (scene.render.engine, scene.render.resolution_x,
         scene.render.resolution_y, scene.render.fps,
         scene.frame_start, scene.frame_end))
print("[inventory] compositor=%s"
      % (scene.compositing_node_group.name if scene.compositing_node_group else "none"))

drivers = 0
for ob in scene.objects:
    if ob.animation_data and ob.animation_data.drivers:
        drivers += len(ob.animation_data.drivers)
print("[inventory] object drivers=%d (all periodic over the loop)" % drivers)

camera = scene.camera
print("[inventory] camera=%s lens=%.1fmm dof=%s f/%.1f"
      % (camera.name, camera.data.lens, camera.data.dof.use_dof,
         camera.data.dof.aperture_fstop))