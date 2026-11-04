import bpy,math,json
from pathlib import Path
from mathutils import Vector

MID="8be67f4c0dd512a4132993698146a687"
D=Path("/data/models")/MID
SRC=D/"v001.glb"; R=D/"renders_v002"; R.mkdir(parents=True,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
objs=[o for o in bpy.context.scene.objects if o.type=="MESH"]
body=max(objs,key=lambda o:len(o.data.polygons))
pts=[o.matrix_world@Vector(c) for o in objs for c in o.bound_box]
mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
H=mx.z-mn.z; cy=(mn.y+mx.y)/2
orig=[v.co.copy() for v in body.data.vertices]

# Left seam mask in Blender coordinates: X horizontal, Z vertical, Y depth/front.
weights=[]
for v in body.data.vertices:
    w=body.matrix_world@v.co
    curve=.540+.684*abs(w.x)
    d=abs(w.z-curve)
    front=max(0.0,min(1.0,(cy-w.y)/(H*.075)))
    side=1.0 if (-.115<w.x<-.004 and .525<w.z<.620 and w.y<cy) else 0.0
    # broad enough to include both sides of the crease, smooth Gaussian falloff
    ww=math.exp(-0.5*(d/.018)**2)*front*side
    weights.append(ww)

# diagnostic render setup
sc=bpy.context.scene; sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=3
sc.render.resolution_x=700; sc.render.resolution_y=700; sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"; sc.render.film_transparent=False
if sc.world is None: sc.world=bpy.data.worlds.new("World")
sc.world.use_nodes=True
bg=sc.world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(.018,.022,.030,1); bg.inputs["Strength"].default_value=.06
try: sc.view_settings.look="AgX - Medium High Contrast"
except: pass
sc.view_settings.exposure=-.6
mat=bpy.data.materials.new("DiagClay"); mat.use_nodes=True
bs=mat.node_tree.nodes.get("Principled BSDF"); bs.inputs["Base Color"].default_value=(.28,.31,.36,1); bs.inputs["Roughness"].default_value=.78
sc.view_layers["ViewLayer"].material_override=mat
camd=bpy.data.cameras.new("Cam"); cam=bpy.data.objects.new("Cam",camd); sc.collection.objects.link(cam); sc.camera=cam
camd.type="ORTHO"; camd.ortho_scale=H*.29
target=Vector((0,cy,mn.z+H*.57))
def look(o,t): o.rotation_euler=(t-o.location).to_track_quat("-Z","Y").to_euler()
for i,(loc,en,size) in enumerate([
 ((-H*.20,mn.y-H*.28,target.z+H*.15),32,H*.17),
 (( H*.18,mn.y-H*.14,target.z+H*.01),12,H*.14),
 ((0,mx.y+H*.16,target.z+H*.14),20,H*.16)]):
    ld=bpy.data.lights.new(f"L{i}","AREA"); ld.energy=en; ld.shape="DISK"; ld.size=size
    lo=bpy.data.objects.new(f"L{i}",ld); sc.collection.objects.link(lo); lo.location=loc; look(lo,target)

def render(prefix):
    for view,loc in {"front":(0,mn.y-H*.48,target.z),"threequarter":(H*.20,mn.y-H*.40,target.z)}.items():
        cam.location=loc; look(cam,target); sc.render.filepath=str(R/(prefix+"_"+view+".png")); bpy.ops.render.render(write_still=True)

render("pelvis_lap_before")
results=[]
for tag,lamb,iters in [("gentle",.12,5),("firm",.22,8)]:
    for v,c in zip(body.data.vertices,orig): v.co=c
    body.data.update()
    vg=body.vertex_groups.get("PELVI_LEFT") or body.vertex_groups.new(name="PELVI_LEFT")
    for v in body.data.vertices:
        try: vg.remove([v.index])
        except: pass
    for i,w in enumerate(weights):
        if w>.005: vg.add([i],min(1.0,w),"REPLACE")
    mod=body.modifiers.new("PELVI_LAPLACIAN","LAPLACIANSMOOTH")
    mod.vertex_group=vg.name
    mod.lambda_factor=lamb
    mod.iterations=iters
    mod.use_volume_preserve=True
    mod.use_x=True; mod.use_y=True; mod.use_z=True
    bpy.context.view_layer.objects.active=body; body.select_set(True)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # smooth shading only; no topology changes
    for p in body.data.polygons:p.use_smooth=True
    out=D/f"pelvis_laplacian_left_{tag}.glb"
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.export_scene.gltf(filepath=str(out),export_format="GLB",export_apply=True)
    render("pelvis_lap_"+tag)
    results.append({"tag":tag,"lambda":lamb,"iters":iters,"out":str(out)})

print("PELVIS_LAPLACIAN_RESULT "+json.dumps(results),flush=True)
