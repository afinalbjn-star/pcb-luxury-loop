"""Set deterministic render settings for the PCB luxury loop.

Run headless on a render farm or CI runner:

    blender -b pcb_luxury_loop.blend -P render_settings.py -a

Every animated quantity in the scene is driven by
sin((frame - 1) * 2*pi / 720), so frame 721 reproduces frame 1 exactly.
720 frames at 60 fps is therefore a 12.000 s clip whose last frame flows
straight back into its first.
"""

import bpy

LOOP_FRAMES = 720
FPS = 60

scene = bpy.context.scene
render = scene.render

# --- delivery spec ---
render.resolution_x = 3840
render.resolution_y = 2160
render.resolution_percentage = 100
render.fps = FPS
render.fps_base = 1.0
render.engine = "CYCLES"

scene.frame_start = 1
scene.frame_end = LOOP_FRAMES

# --- image output ---
render.image_settings.file_format = "PNG"
render.image_settings.color_mode = "RGB"
render.image_settings.color_depth = "16"
render.image_settings.compression = 15
render.use_overwrite = True
render.use_file_extension = True
render.use_placeholder = False
render.film_transparent = False

# --- sampling ---
cycles = scene.cycles
cycles.samples = 256
cycles.preview_samples = 16
cycles.use_adaptive_sampling = True
cycles.adaptive_threshold = 0.01
cycles.use_denoising = True
cycles.max_bounces = 8
cycles.diffuse_bounces = 4
cycles.glossy_bounces = 4
cycles.transmission_bounces = 6
cycles.transparent_max_bounces = 8
cycles.caustics_reflective = False
cycles.caustics_refractive = False
cycles.blur_glossy = 1.0
cycles.volume_bounces = 2

# tile size matters for the 4K volume scatter on CPU-only runners
cycles.use_auto_tile = True
cycles.tile_size = 2048

# --- colour management ---
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -0.42
scene.view_settings.gamma = 1.0

print(
    "[render_settings] %dx%d @ %d fps, frames %d-%d (%0.3f s), samples %d"
    % (
        render.resolution_x,
        render.resolution_y,
        render.fps,
        scene.frame_start,
        scene.frame_end,
        LOOP_FRAMES / FPS,
        cycles.samples,
    )
)