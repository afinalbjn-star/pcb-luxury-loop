"""Apply CI render overrides, read from environment variables.

Run before the animation render:

    ENGINE=cycles SAMPLES=256 START_FRAME=1 END_FRAME=720 FRAMES_DIR=render \
        blender -b scene.blend -P ci_settings.py -o //render/pcb_#### -a

Keeping this in a file rather than a `--python-expr` string avoids the shell
and YAML quoting that would otherwise mangle the code.
"""

import os

import bpy

FRAME_START = int(os.environ.get("START_FRAME", "1"))
FRAME_END = int(os.environ.get("END_FRAME", "720"))
SAMPLES = int(os.environ.get("SAMPLES", "256"))
ENGINE = os.environ.get("ENGINE", "cycles")
FRAMES_DIR = os.environ.get("FRAMES_DIR", "render")
RES_X = int(os.environ.get("RES_X", "3840"))
RES_Y = int(os.environ.get("RES_Y", "2160"))
FPS = int(os.environ.get("FPS", "60"))
THREADS = int(os.environ.get("CYCLES_THREADS", "0"))

scene = bpy.context.scene
render = scene.render

render.engine = "CYCLES" if ENGINE == "cycles" else "BLENDER_EEVEE"
render.resolution_x = RES_X
render.resolution_y = RES_Y
render.resolution_percentage = 100
render.fps = FPS
render.fps_base = 1.0

scene.frame_start = FRAME_START
scene.frame_end = FRAME_END

render.image_settings.file_format = "PNG"
render.image_settings.color_mode = "RGB"
render.image_settings.color_depth = "16"
render.image_settings.compression = 15
render.use_overwrite = True
render.use_file_extension = True
render.use_placeholder = False

render.filepath = os.path.join(FRAMES_DIR, "pcb_")

if render.engine == "CYCLES":
    cy = scene.cycles
    cy.device = "CPU"
    cy.samples = SAMPLES
    cy.preview_samples = 16
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.01
    cy.use_denoising = True
    cy.max_bounces = 8
    cy.diffuse_bounces = 4
    cy.glossy_bounces = 4
    cy.transmission_bounces = 6
    cy.transparent_max_bounces = 8
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    cy.volume_bounces = 2
    # GitHub runners have no GPU, so multi-tile keeps every core busy.
    cy.use_auto_tile = True
    cy.tile_size = 2048
    if THREADS > 0:
        cy.threads_mode = "FIXED"
        cy.threads = THREADS
else:
    ee = scene.eevee
    ee.taa_render_samples = max(SAMPLES, 16)
    if hasattr(ee, "use_raytracing"):
        ee.use_raytracing = True
    if hasattr(ee, "use_bloom"):
        ee.use_bloom = False

scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -0.42
scene.view_settings.gamma = 1.0

counts = {}
for ob in scene.objects:
    counts[ob.type] = counts.get(ob.type, 0) + 1

print("[ci_settings] engine=%s %dx%d @%dfps frames %d-%d samples=%d threads=%s"
      % (render.engine, RES_X, RES_Y, FPS, FRAME_START, FRAME_END,
         SAMPLES, THREADS or "auto"))
print("[ci_settings] objects=%d %s" % (len(scene.objects), counts))
print("[ci_settings] materials=%d meshes=%d curves=%d"
      % (len(bpy.data.materials), len(bpy.data.meshes), len(bpy.data.curves)))
print("[ci_settings] output=%s" % render.filepath)