#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blender 绑定 v4：眼睛完全不动（不再分层、不再眨眼），只做呼吸/点头/嘴型。

这样从结构上杜绝“白眼”——眼睛是底图的一部分，没有任何东西能把它压没。
"""
import json
import math
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
ENVP, OUTDIR, FRAMES = Path(argv[0]), Path(argv[1]), int(argv[2])
BASE = Path(r"E:\wx\论文素材_王晰作传")
LAY = BASE / "layers"
W, H = 629, 820
FPS = 25


def plane(img, name, w, h, cx=0.0, cy=0.0, z=0.0):
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

    cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 1920
    cam = bpy.data.objects.new("c", cd)
    scn.collection.objects.link(cam); cam.location = (0, 0, 50); scn.camera = cam

    base = plane(LAY / "base_eyes.png", "base", W, H, 0, 0, 0)
    meta = json.loads((LAY / "meta.json").read_text(encoding="utf-8"))
    m = meta["parts"][2]["box"]
    cx = (m[0] + m[2]) / 2 - W / 2
    cy = H / 2 - (m[1] + m[3]) / 2
    mw, mh = m[2] - m[0], m[3] - m[1]
    mouth = plane(LAY / "mouth.png", "mouth", mw, mh, cx, cy, 0.1)

    env = json.loads(ENVP.read_text(encoding="utf-8"))
    vals = env["values"]; t0 = env["talk_start"]; nt = env["talk_frames"]

    for f in range(1, FRAMES + 1):
        tt = f / FPS
        v = 0.0
        k = f - t0
        if 0 <= k < nt:
            v = vals[k]
        nod = math.radians(0.4 * math.sin(2 * math.pi * tt / 1.9) * (1.0 if v > 0.05 else 0.0))
        base.location.y = math.sin(2 * math.pi * tt / 3.4) * 4
        base.rotation_euler[1] = math.radians(math.sin(2 * math.pi * tt / 7.0) * 0.6)
        base.rotation_euler[0] = nod
        base.keyframe_insert("location", frame=f)
        base.keyframe_insert("rotation_euler", frame=f)
        mouth.scale = (mw * (1 + 0.16 * v), mh * (1 + 1.4 * v), 1)
        mouth.keyframe_insert("scale", frame=f)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    scn.render.filepath = str(OUTDIR / "f_")
    scn.frame_end = FRAMES
    bpy.ops.render.render(animation=True)
    print("RIG4_DONE", FRAMES, OUTDIR)


if __name__ == "__main__":
    main()
