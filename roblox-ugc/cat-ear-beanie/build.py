"""고양이 귀 비니 - Roblox 단단한(rigid) 모자 액세서리 생성 스크립트.
실행: python3 build.py   (pip install bpy 필요)
단위: Blender 1 unit = 1 stud. 정면 = Blender -Y.
"""
import bpy, bmesh, math, os
from mathutils import Vector

OUT = os.path.dirname(os.path.abspath(__file__))
TEX = 256  # 단단한 액세서리 권장 텍스처 크기

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree.nodes, m.node_tree.links

def knit_mat(name, c1, c2, cols, rows, ribbed):
    m, n, l = new_mat(name)
    bsdf = n["Principled BSDF"]; bsdf.inputs["Roughness"].default_value = 0.9
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ")
    l.new(tc.outputs["Object"], sep.inputs[0])
    az = n.new("ShaderNodeMath"); az.operation = "ARCTAN2"
    l.new(sep.outputs["Y"], az.inputs[0]); l.new(sep.outputs["X"], az.inputs[1])
    a = n.new("ShaderNodeMath"); a.operation = "MULTIPLY"; a.inputs[1].default_value = cols
    l.new(az.outputs[0], a.inputs[0])
    sa = n.new("ShaderNodeMath"); sa.operation = "SINE"; l.new(a.outputs[0], sa.inputs[0])
    if ribbed:
        f = sa
    else:
        z = n.new("ShaderNodeMath"); z.operation = "MULTIPLY"; z.inputs[1].default_value = rows
        l.new(sep.outputs["Z"], z.inputs[0])
        # V자 니트 느낌: 행 방향에 열 위상을 섞음
        ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; l.new(sa.outputs[0], ab.inputs[0])
        ad = n.new("ShaderNodeMath"); ad.operation = "MULTIPLY_ADD"
        l.new(ab.outputs[0], ad.inputs[0]); ad.inputs[1].default_value = 2.0; l.new(z.outputs[0], ad.inputs[2])
        sz = n.new("ShaderNodeMath"); sz.operation = "SINE"; l.new(ad.outputs[0], sz.inputs[0])
        f = n.new("ShaderNodeMath"); f.operation = "MULTIPLY"
        l.new(sz.outputs[0], f.inputs[0]); l.new(ab.outputs[0], f.inputs[1])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = c1
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = c2
    mr = n.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -1
    l.new(f.outputs[0], mr.inputs["Value"]); l.new(mr.outputs[0], ramp.inputs[0])
    l.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    return m

def flat_mat(name, c):
    m, n, l = new_mat(name)
    b = n["Principled BSDF"]; b.inputs["Base Color"].default_value = c; b.inputs["Roughness"].default_value = 0.85
    return m

DARK  = (0.018, 0.018, 0.022, 1); DARK2 = (0.055, 0.055, 0.068, 1)
PINK  = (0.88, 0.36, 0.47, 1)
m_body = knit_mat("Knit", DARK, DARK2, 44, 70, False)
m_cuff = knit_mat("Cuff", (0.012, 0.012, 0.015, 1), (0.07, 0.07, 0.085, 1), 60, 0, True)
m_ear  = flat_mat("EarOuter", (0.03, 0.03, 0.036, 1))
m_pink = flat_mat("EarInner", PINK)

def finish(obj, mat):
    obj.data.materials.append(mat)
    for p in obj.data.polygons: p.use_smooth = True
    return obj

# 1) 돔 (머리 덮는 부분)
bpy.ops.mesh.primitive_uv_sphere_add(segments=36, ring_count=18, radius=0.70)
dome = bpy.context.object; dome.name = "Dome"
bm = bmesh.new(); bm.from_mesh(dome.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.02], context="VERTS")
bm.to_mesh(dome.data); bm.free()
dome.scale = (1.0, 1.04, 1.08)
sol = dome.modifiers.new("t", "SOLIDIFY"); sol.thickness = 0.03; sol.offset = 1
finish(dome, m_body)

# 2) 접힌 밴드(커프)
bpy.ops.mesh.primitive_torus_add(major_segments=40, minor_segments=8, major_radius=0.70, minor_radius=0.075)
cuff = bpy.context.object; cuff.name = "Cuff"
cuff.scale = (1.0, 1.04, 1.9); cuff.location.z = 0.02
finish(cuff, m_cuff)

# 3) 고양이 귀
def ear(side):
    objs = []
    for inner in (False, True):
        r, d = (0.24, 0.40) if not inner else (0.15, 0.27)
        bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=r, radius2=0.012, depth=d)
        e = bpy.context.object
        e.scale = (1.0, 0.42 if not inner else 0.18, 1.0)
        bpy.ops.object.transform_apply(scale=True)
        # 귀 끝을 살짝 바깥으로 휘게
        for v in e.data.vertices:
            t = (v.co.z + d / 2) / d
            v.co.x += side * 0.05 * t * t
        tilt = math.radians(28) * side
        base = Vector((side * 0.42, 0.0, 0.56))
        e.rotation_euler = (0, tilt, 0)
        e.location = base + Vector((side * 0.10, 0, 0.13)) if not inner else base + Vector((side * 0.085, -0.06, 0.10))
        finish(e, m_pink if inner else m_ear)
        objs.append(e)
    return objs

ears = ear(+1) + ear(-1)

# 합치기 (Roblox: 메시 1개)
for o in bpy.context.scene.objects: o.select_set(False)
for o in [dome, cuff] + ears:
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    for md in o.modifiers: bpy.ops.object.modifier_apply(modifier=md.name)
bpy.context.view_layer.objects.active = dome
bpy.ops.object.join()
hat = bpy.context.object; hat.name = "CatEarBeanie"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
hat.location = (0, 0, 0)

# 삼각형화 + 개수 확인
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.quads_convert_to_tris()
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
bpy.ops.object.mode_set(mode="OBJECT")
tris = len(hat.data.polygons)
dims = hat.dimensions
print(f"TRIS={tris} SIZE(studs)={dims.x:.2f} x {dims.y:.2f} x {dims.z:.2f}")
assert tris <= 4000, "Roblox 액세서리 제한 4000 삼각형 초과"

# 텍스처 베이크 (색 + AO)
scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 64
def bake(kind, size):
    img = bpy.data.images.new(kind, size, size, alpha=False)
    for m in hat.data.materials:
        nd = m.node_tree.nodes.new("ShaderNodeTexImage"); nd.image = img
        m.node_tree.nodes.active = nd
    if kind == "DIFFUSE":
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
    scene.render.bake.margin = 8
    bpy.ops.object.bake(type=kind)
    for m in hat.data.materials:
        m.node_tree.nodes.remove(m.node_tree.nodes.active)
    return img

hi = 1024
col = bake("DIFFUSE", hi); ao = bake("AO", hi)
import numpy as np
c = np.array(col.pixels[:]).reshape(hi, hi, 4); a = np.array(ao.pixels[:]).reshape(hi, hi, 4)
out = c.copy(); out[..., :3] = c[..., :3] * (0.45 + 0.55 * a[..., :3])
final = bpy.data.images.new("CatEarBeanie_tex", hi, hi, alpha=False)
final.pixels = out.ravel().tolist()
final.scale(TEX, TEX)
tex_path = os.path.join(OUT, "CatEarBeanie_texture.png")
final.filepath_raw = tex_path; final.file_format = "PNG"; final.save()

# 최종 재질: 텍스처 1장만 사용
hat.data.materials.clear()
fm, n, l = new_mat("CatEarBeanie")
t = n.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex_path)
l.new(t.outputs["Color"], n["Principled BSDF"].inputs["Base Color"])
n["Principled BSDF"].inputs["Roughness"].default_value = 0.9
hat.data.materials.append(fm)

for o in bpy.context.scene.objects: o.select_set(o == hat)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "CatEarBeanie.fbx"), use_selection=True,
                         path_mode="COPY", embed_textures=True, apply_unit_scale=True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "CatEarBeanie.glb"), use_selection=True)

# ---- 미리보기 렌더 (머리는 참고용, 내보내지 않음) ----
def add(o, mat): o.data.materials.append(mat); [setattr(p, "use_smooth", True) for p in o.data.polygons]; return o
skin = flat_mat("Skin", (0.45, 0.45, 0.47, 1)); black = flat_mat("Eye", (0.01, 0.01, 0.01, 1))
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.62, depth=1.15, location=(0, 0, -0.60))
head = bpy.context.object; bv = head.modifiers.new("b", "BEVEL"); bv.width = 0.28; bv.segments = 8
add(head, skin)
for x in (-0.2, 0.2):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.065, location=(x, -0.6, -0.68)); e = bpy.context.object
    e.scale = (0.8, 0.4, 1.3); add(e, black)
bpy.ops.mesh.primitive_torus_add(major_radius=0.16, minor_radius=0.025, location=(0, -0.6, -0.86), rotation=(math.radians(90), 0, 0))
sm = bpy.context.object; add(sm, black)
bm = bmesh.new(); bm.from_mesh(sm.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > -0.03], context="VERTS"); bm.to_mesh(sm.data); bm.free()

world = bpy.data.worlds.new("w"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.92, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
bpy.ops.object.light_add(type="AREA", location=(-2.5, -3, 3)); k = bpy.context.object; k.data.energy = 260; k.data.size = 3
k.rotation_euler = (math.radians(50), 0, math.radians(-40))
bpy.ops.object.light_add(type="AREA", location=(3, -1, 2)); r = bpy.context.object; r.data.energy = 120; r.data.size = 3
r.rotation_euler = (math.radians(60), 0, math.radians(70))
bpy.ops.object.camera_add(); cam = bpy.context.object; scene.camera = cam; cam.data.lens = 70
scene.render.resolution_x = scene.render.resolution_y = 720
scene.cycles.samples = 48; scene.view_settings.view_transform = "AgX"

def shoot(name, az, el, dist=5.8, head_on=True):
    for o in [head, sm] + [o for o in scene.objects if o.name.startswith("Sphere")]:
        o.hide_render = not head_on
    tgt = Vector((0, 0, 0.0 if not head_on else -0.45))
    cam.location = tgt + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(OUT, f"preview_{name}.png")
    bpy.ops.render.render(write_still=True)

shoot("front", 0, math.radians(8))
shoot("three_quarter", math.radians(35), math.radians(18))
shoot("side", math.radians(90), math.radians(5))
shoot("hat_only", math.radians(-30), math.radians(25), dist=4.2, head_on=False)
print("DONE")
