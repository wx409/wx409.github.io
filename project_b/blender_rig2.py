#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blender 2.5D 绑定：底图 + 两只眼 + 嘴，按配音包络驱动。

与上一版的区别
  · 不是一张整图，而是 4 个平面：base / eye_l / eye_r / mouth
  · 眨眼 = 眼睛平面 scale.y → 0.05（皮肤色底图托底，不会露白）
  · 说话 = 嘴平面 scale.y 随包络（1 → 2.2）+ scale.x（1 → 1.15）
  · 身体 = 呼吸起伏 + 头部倾斜

用法
  blender -b --factory-startup --python blender_rig2.py -- <env.json> <outdir> <frames>
env.json: [{"t":0.0,"v":0.0}, ...] 每帧一个音量值 0..1
"""
import json
import math
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENV = Path(argv[0])
OUTDIR = Path(argv[1])
FRAMES = int(argv[2]) if len(argv) > 2 else 120
BASE = Path(r"E:\wx\论文素材_王晰作传")
LAYERS = BASE / "layers"
CANVAS = (629, 820)
FPS = 25


def add_plane(img: Path, name: str, w: float, h: float, cx: float, cy: float, z: float):
    image = bpy.data.images.load(str(img))
    mat = bpy.data.materials.new(name + "_m")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    emis = nt.nodes.new("ShaderNodeEmission")
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], emis.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(emis.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (w, h, 1)
    ob.location = (cx, cy, z)
    ob.data.materials.append(mat)
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

    cam_d = bpy.data.cameras.new("c")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = 1920
    cam = bpy.data.objects.new("c", cam_d)
    scn.collection.objects.link(cam)
    cam.location = (0, 0, 50)
    scn.camera = cam

    W, H = CANVAS
    meta = json.loads((LAYERS / "meta.json").read_text(encoding="utf-8"))
    # 平面坐标：左下原点 → 以画布中心为原点（1 单位 = 1 像素）
    def to_xy(box):
        x0, y0, x1, y1 = box
        cx = (x0 + x1) / 2 - W / 2
        cy = H / 2 - (y0 + y1) / 2
        return cx, cy, (x1 - x0), (y1 - y0)

    base = add_plane(LAYERS / "base.png", "base", W, H, 0, 0, 0)
    parts = {}
    for i, p in enumerate(meta["parts"]):
        cx, cy, w, h = to_xy(p["box"])
        parts[p["file"]] = add_plane(LAYERS / p["file"], p["file"], w, h, cx, cy, 0.1 + i * 0.1)

    env = json.loads(ENV.read_text(encoding="utf-8")) if ENV.exists() else []
    vals = [e["v"] for e in env] or [0.0]

    # 眨眼时刻
    blinks = []
    t = 1.6
    while t < FRAMES / FPS:
        blinks.append(t)
        t += 2.8 + (len(blinks) % 2) * 0.7

    for f in range(1, FRAMES + 1):
        tt = f / FPS
        v = vals[min(int(tt * FPS), len(vals) - 1)]
        # 身体
        base.location.y = math.sin(2 * math.pi * tt / 3.4) * 5
        base.rotation_euler[1] = math.radians(math.sin(2 * math.pi * tt / 7.0) * 0.7)
        base.keyframe_insert("location", frame=f)
        base.keyframe_insert("rotation_euler", frame=f)
        # 眨眼
        blink = any(abs(tt - b) < 0.06 for b in blinks)
        for name in ("eye_l.png", "eye_r.png"):
            ob = parts[name]
            sx, sy, sz = ob.scale
            ob.scale = (sx, 0.06 if blink else 1.0, sz)
            ob.keyframe_insert("scale", frame=f)
        # 嘴
        m = parts["mouth.png"]
        m.scale = ((meta["parts"][2]["w"]) * (1 + 0.15 * v),
                   (meta["parts"][2]["h"]) * (1 + 1.2 * v), 1)
        m.keyframe_insert("scale", frame=f)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    scn.render.filepath = str(OUTDIR / "f_")
    scn.frame_end = FRAMES
    bpy.ops.render.render(animation=True)
    print("RIG_DONE", FRAMES, OUTDIR)


if __name__ == "__main__":
    main()
