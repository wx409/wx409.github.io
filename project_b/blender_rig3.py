#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blender 绑定 v3：底图 + 双眼 + 嘴 + 前后发，真实包络驱动，随机眨眼，说话点头。

用法
  blender -b --factory-startup --python blender_rig3.py -- <env.json> <outdir> <frames>
env.json: {fps, frames, talk_start, talk_frames, values:[0..1 ...]}
"""
import json
import math
import random
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
ENVP, OUTDIR, FRAMES = Path(argv[0]), Path(argv[1]), int(argv[2])
BASE = Path(r"E:\wx\论文素材_王晰作传")
LAYERS = BASE / "layers"
W, H = 629, 820
FPS = 25


def plane(img: Path, name: str, w: float, h: float, cx=0.0, cy=0.0, z=0.0):
    im = bpy.data.images.load(str(img))
    m = bpy.data.materials.new(name + "_m")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = im
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mx.inputs["Fac"])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (w, h, 1)
    ob.location = (cx, cy, z)
    ob.data.materials.append(m)
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scn.render.engine = eng
            break
        except Exception:
            continue
    scn.render.resolution_x, scn.render.resolution_y = 1080, 1920
    scn.render.film_transparent = True
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    scn.render.fps = FPS

    cd = bpy.data.cameras.new("c")
    cd.type = "ORTHO"
    cd.ortho_scale = 1920
    cam = bpy.data.objects.new("c", cd)
    scn.collection.objects.link(cam)
    cam.location = (0, 0, 50)
    scn.camera = cam

    meta = json.loads((LAYERS / "meta.json").read_text(encoding="utf-8"))

    def box2xy(b):
        x0, y0, x1, y1 = b
        return ((x0 + x1) / 2 - W / 2, H / 2 - (y0 + y1) / 2, x1 - x0, y1 - y0)

    base = plane(LAYERS / "base.png", "base", W, H, 0, 0, 0)
    hair_back = plane(LAYERS / "hair_back.png", "hair_back", W, H, 0, 0, 0.05) if (LAYERS / "hair_back.png").exists() else None
    hair_front = plane(LAYERS / "hair_front.png", "hair_front", W, H, 0, 0, 0.06) if (LAYERS / "hair_front.png").exists() else None

    eyes = []
    eyes_w = eyes_h = 1.0
    for p in meta["parts"][:2]:
        cx, cy, w, h = box2xy(p["box"])
        eyes_w, eyes_h = w, h
        eyes.append(plane(LAYERS / p["file"], p["file"], w, h, cx, cy, 0.10))
    mcx, mcy, mw, mh = box2xy(meta["parts"][2]["box"])
    mouth = plane(LAYERS / "mouth.png", "mouth", mw, mh, mcx, mcy, 0.20)

    env = json.loads(ENVP.read_text(encoding="utf-8"))
    vals = env["values"]
    talk0 = env["talk_start"]
    ntalk = env["talk_frames"]

    random.seed(7)
    blinks, t = [], 1.2
    if env.get("blink", True) is False:
        blinks = []
    while (env.get("blink", True) is not False) and t < FRAMES / FPS:
        blinks.append(t)
        t += random.uniform(3.0, 5.0)

    for f in range(1, FRAMES + 1):
        tt = f / FPS
        v = 0.0
        k = f - talk0
        if 0 <= k < ntalk:
            v = vals[k]
        # 点头：说话时轻微前后点
        nod = math.radians(0.5 * math.sin(2 * math.pi * tt / 1.8) * (1.0 if v > 0.05 else 0.0))
        base.location.y = math.sin(2 * math.pi * tt / 3.4) * 4
        base.rotation_euler[1] = math.radians(math.sin(2 * math.pi * tt / 7.0) * 0.6)
        base.rotation_euler[0] = nod
        base.keyframe_insert("location", frame=f)
        base.keyframe_insert("rotation_euler", frame=f)

        # 头发摆动（前后反向，幅度随说话音量）
        sw = math.radians(1.2 + 0.8 * v) * math.sin(2 * math.pi * tt / 4.2)
        for ob, sgn in ((hair_front, 1.0), (hair_back, -0.8)):
            if ob:
                ob.rotation_euler[1] = sw * sgn
                ob.keyframe_insert("rotation_euler", frame=f)

        blink = any(abs(tt - b) < 0.08 for b in blinks)
        for ob in eyes:
            _, hh, _ = ob.scale
            ob.scale = (eyes_w, eyes_h * (0.04 if blink else 1.0), 1)
            ob.keyframe_insert("scale", frame=f)

        mouth.scale = (mw * (1 + 0.18 * v), mh * (1 + 1.5 * v), 1)
        mouth.keyframe_insert("scale", frame=f)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    scn.render.filepath = str(OUTDIR / "f_")
    scn.frame_end = FRAMES
    bpy.ops.render.render(animation=True)
    print("RIG3_DONE", FRAMES, OUTDIR)


if __name__ == "__main__":
    main()
