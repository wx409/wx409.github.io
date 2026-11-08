# -*- coding: utf-8 -*-
"""Blender headless：把大肥鱼立绘建成 2.5D 场景并渲出 PNG 序列（alpha）。

最小可行版
  · 正交相机，画布 1080×1920，1 单位 = 1 像素（用 ortho_scale=1920）
  · 三层：身体（整张立绘）/ 嘴（小图，缩放随音量）/ 眼睑（眨眼横条）
  · 动画：呼吸起伏、头部轻微倾斜、嘴开合、眨眼
  · 输出：透明背景 PNG 序列，交给 ffmpeg 合成

用法
  "D:\\Blender 5.1\\blender.exe" -b --factory-startup --python project_b\\blender_rig.py -- <env.json> <outdir>
"""
import json
import math
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ENV_JSON = Path(argv[0]) if argv else None
OUTDIR = Path(argv[1]) if len(argv) > 1 else Path(r"E:\wx\论文素材_王晰作传\blender_out")
BASE = Path(r"E:\wx\论文素材_王晰作传")
CHAR = BASE / "_char_front_v3.png"

FPS = 25


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_plane(img_path: Path, name: str, width: float, height: float, z: float):
    img = bpy.data.images.load(str(img_path))
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    emis = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Color"], emis.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(emis.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])

    bpy.ops.mesh.primitive_plane_add(size=1)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (width, height, 1)
    ob.location = (0, 0, z)
    ob.data.materials.append(mat)
    return ob


def main():
    clear()
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

    # 相机：正交，1 单位 = 1 像素
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 1920
    cam = bpy.data.objects.new("cam", cam_data)
    scn.collection.objects.link(cam)
    cam.location = (0, 0, 100)
    scn.camera = cam

    # 立绘：按像素尺寸建平面（629×820）
    body = add_plane(CHAR, "body", 629, 820, 0)

    # 嘴（单独小图，若没有就跳过）
    mouth_png = BASE / "_mouth.png"
    mouth = add_plane(mouth_png, "mouth", 40, 24, 0.1) if mouth_png.exists() else None

    # 读包络
    env = []
    if ENV_JSON and ENV_JSON.exists():
        env = json.loads(ENV_JSON.read_text(encoding="utf-8"))
    n = int(env[-1]["t"] * FPS) if env else 50

    # 动画：呼吸 + 倾斜 + 嘴开合
    for f in range(1, n + 1):
        t = f / FPS
        z = math.sin(2 * math.pi * t / 3.4) * 4
        body.location.z = 0
        body.location.y = z
        body.rotation_euler[1] = math.radians(math.sin(2 * math.pi * t / 7.2) * 0.6)
        body.keyframe_insert("location", frame=f)
        body.keyframe_insert("rotation_euler", frame=f)
        if mouth:
            v = 0.2
            for e in env:
                if abs(e["t"] - t) < 0.5 / FPS:
                    v = e["v"]
                    break
            mouth.scale = (40, 8 + 16 * v, 1)
            mouth.keyframe_insert("scale", frame=f)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    scn.render.filepath = str(OUTDIR / "f_")
    scn.frame_end = n
    bpy.ops.render.render(animation=True)
    print("BLENDER_DONE", n, OUTDIR)


if __name__ == "__main__":
    main()
