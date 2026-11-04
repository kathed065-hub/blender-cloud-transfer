import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector

MID="8be67f4c0dd512a4132993698146a687"
D=Path("/data/models")/MID
SRC=D/"v001.glb"
OUT=D/"pelvis_bmesh_left_v1.glb"
RDIR=D/"renders_v002"; RDIR.mkdir(parents=True,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
mesh_objs=[o for o in bpy.context.scene.objects if o.type=="MESH"]
if not mesh_objs: raise RuntimeError("no mesh objects")
body=max(mesh_objs,key=lambda o: len(o.data.polygons))

# Bounds in Blender world (glTF import => Z-up, front roughly -Y)
pts=[o.matrix_world@Vector(c) for o in mesh_objs for c in o.bound_box]
mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
H=mx.z-mn.z
cy=(mn.y+mx.y)/2

bm=bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
selected=[]
angles=[]
for e in bm.edges:
    if len(e.link_faces)!=2: continue
    co=(e.verts[0].co+e.verts[1].co)*0.5
    w=body.matrix_world@co
    curve=0.540 + 0.684*abs(w.x)
    if not (-0.110 < w.x < -0.003): continue
    if not (0.525 < w.z < 0.620): continue
    if abs(w.z-curve) > 0.010: continue
    if w.y >= cy: continue
    try: ang=e.calc_face_angle(0.0)
    except: ang=0.0
    if ang < math.radians(8): continue
    selected.append(e); angles.append(math.degrees(ang))

before_v=len(bm.verts); before_e=len(bm.edges); before_f=len(bm.faces)
if selected:
    bmesh.ops.dissolve_edges(bm, edges=selected, use_verts=True, use_face_split=False)

bm.normal_update()
after_v=len(bm.verts); after_e=len(bm.edges); after_f=len(bm.faces)
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons: p.use_smooth=True

# Export copy only
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format="GLB",export_apply=True)

# Clay render
sc=bpy.context.scene
sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=4
sc.render.resolution_x=720; sc.render.resolution_y=720; sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"
sc.render.film_transparent=False
if sc.world is None: sc.world=bpy.data.worlds.new("World")
sc.world.use_nodes=True
bg=sc.world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value=(0.02,0.025,0.035,1); bg.inputs["Strength"].default_value=0.15
mat=bpy.data.materials.new("Clay"); mat.use_nodes=True
bs=mat.node_tree.nodes.get("Principled BSDF")
bs.inputs["Base Color"].default_value=(0.42,0.45,0.50,1)
bs.inputs["Roughness"].default_value=0.72
sc.view_layers["ViewLayer"].material_override=mat

camd=bpy.data.cameras.new("PelvisCam"); cam=bpy.data.objects.new("PelvisCam",camd)
sc.collection.objects.link(cam); sc.camera=cam
camd.type="ORTHO"; camd.ortho_scale=H*0.31
target=Vector((0.0,cy,mn.z+H*0.57))

def look(o,t):
    o.rotation_euler=(t-o.location).to_track_quat("-Z","Y").to_euler()

lights=[
    ((-H*.20,mn.y-H*.28,target.z+H*.14),160,H*.18),
    (( H*.18,mn.y-H*.16,target.z+H*.02),90,H*.16),
    ((0, mx.y+H*.16,target.z+H*.15),120,H*.18)]
for i,(loc,en,size) in enumerate(lights):
    ld=bpy.data.lights.new(f"L{i}","AREA"); ld.energy=en; ld.shape="DISK"; ld.size=size
    lo=bpy.data.objects.new(f"L{i}",ld); sc.collection.objects.link(lo); lo.location=loc; look(lo,target)

for name,loc in {
    "pelvis_bmesh_left_front":(0,mn.y-H*.48,target.z),
    "pelvis_bmesh_left_threequarter":(H*.20,mn.y-H*.40,target.z)
}.items():
    cam.location=loc; look(cam,target)
    sc.render.filepath=str(RDIR/(name+".png"))
    bpy.ops.render.render(write_still=True)

print("PELVIS_BMESH_RESULT "+json.dumps({
    "selected_edges":len(selected),
    "angle_min":min(angles) if angles else None,
    "angle_max":max(angles) if angles else None,
    "before":[before_v,before_e,before_f],
    "after":[after_v,after_e,after_f],
    "out":str(OUT)
}),flush=True)
