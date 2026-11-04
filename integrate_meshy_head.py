import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector

MID="8be67f4c0dd512a4132993698146a687"
D=Path("/data/models")/MID
SRC=D/"v001.glb"
OUT=D/"pelvis_bmesh_left_v2.glb"
R=D/"renders_v002"; R.mkdir(parents=True,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
objs=[o for o in bpy.context.scene.objects if o.type=="MESH"]
body=max(objs,key=lambda o:len(o.data.polygons))
pts=[o.matrix_world@Vector(c) for o in objs for c in o.bound_box]
mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
H=mx.z-mn.z; cy=(mn.y+mx.y)/2

sc=bpy.context.scene
sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=4
sc.render.resolution_x=720; sc.render.resolution_y=720; sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"; sc.render.film_transparent=False
if sc.world is None: sc.world=bpy.data.worlds.new("World")
sc.world.use_nodes=True
bg=sc.world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(.018,.022,.030,1); bg.inputs["Strength"].default_value=.08
try: sc.view_settings.look="AgX - Medium High Contrast"
except: pass
mat=bpy.data.materials.new("ClayDark"); mat.use_nodes=True
bs=mat.node_tree.nodes.get("Principled BSDF"); bs.inputs["Base Color"].default_value=(.24,.27,.31,1); bs.inputs["Roughness"].default_value=.76
sc.view_layers["ViewLayer"].material_override=mat
camd=bpy.data.cameras.new("PelvisCam"); cam=bpy.data.objects.new("PelvisCam",camd); sc.collection.objects.link(cam); sc.camera=cam
camd.type="ORTHO"; camd.ortho_scale=H*.29
target=Vector((0,cy,mn.z+H*.57))
def look(o,t): o.rotation_euler=(t-o.location).to_track_quat("-Z","Y").to_euler()
for i,(loc,en,size) in enumerate([
    ((-H*.20,mn.y-H*.30,target.z+H*.15),48,H*.17),
    (( H*.20,mn.y-H*.15,target.z+H*.01),22,H*.14),
    ((0,mx.y+H*.16,target.z+H*.14),34,H*.16)]):
    ld=bpy.data.lights.new(f"L{i}","AREA"); ld.energy=en; ld.shape="DISK"; ld.size=size
    lo=bpy.data.objects.new(f"L{i}",ld); sc.collection.objects.link(lo); lo.location=loc; look(lo,target)

def render_pair(prefix):
    for name,loc in {
        "front":(0,mn.y-H*.48,target.z),
        "threequarter":(H*.20,mn.y-H*.40,target.z)
    }.items():
        cam.location=loc; look(cam,target)
        sc.render.filepath=str(R/(prefix+"_"+name+".png")); bpy.ops.render.render(write_still=True)

render_pair("pelvis_bmesh_v2_before")

bm=bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
edges=[]; angles=[]
for e in bm.edges:
    if len(e.link_faces)!=2: continue
    co=(e.verts[0].co+e.verts[1].co)*.5
    w=body.matrix_world@co
    curve=.540+.684*abs(w.x)
    if not (-.103 < w.x < -.006): continue
    if not (.535 < w.z < .615): continue
    if abs(w.z-curve)>.0048: continue
    if w.y>=cy: continue
    ang=e.calc_face_angle(0.0)
    if ang<math.radians(10): continue
    edges.append(e); angles.append(math.degrees(ang))
verts=set(v for e in edges for v in e.verts)
# one-ring verts, depth-only smoothing
for v in list(verts):
    for e in v.link_edges:
        for vv in e.verts: verts.add(vv)

before=(len(bm.verts),len(bm.edges),len(bm.faces))
if edges:
    bmesh.ops.dissolve_edges(bm,edges=edges,use_verts=False,use_face_split=False)
    bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    live=[v for v in verts if v.is_valid]
    for _ in range(5):
        bmesh.ops.smooth_vert(bm,verts=live,factor=.24,use_axis_x=False,use_axis_y=True,use_axis_z=False)
    # Triangulate only local n-gons/quads near target with BEAUTY to avoid long shading diagonals
    local=[]
    for f in bm.faces:
        c=body.matrix_world@f.calc_center_median()
        curve=.540+.684*abs(c.x)
        if (-.112<c.x<.002 and .525<c.z<.625 and abs(c.z-curve)<.018 and c.y<cy):
            local.append(f)
    if local:
        bmesh.ops.triangulate(bm,faces=local,quad_method="BEAUTY",ngon_method="BEAUTY")

bm.normal_update(); after=(len(bm.verts),len(bm.edges),len(bm.faces))
bm.to_mesh(body.data); bm.free(); body.data.update()
for p in body.data.polygons:p.use_smooth=True

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format="GLB",export_apply=True)
render_pair("pelvis_bmesh_v2_after")

print("PELVIS_BMESH_V2 "+json.dumps({
 "selected_edges":len(edges),"angles":[min(angles) if angles else None,max(angles) if angles else None],
 "before":before,"after":after,"out":str(OUT)
}),flush=True)
