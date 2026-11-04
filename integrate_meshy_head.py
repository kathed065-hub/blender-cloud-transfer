import bpy,math,json
from pathlib import Path
from mathutils import Vector

MID="8be67f4c0dd512a4132993698146a687"
D=Path("/data/models")/MID
SRC=D/"pelvis_laplacian_left_firm.glb"
OUT=D/"pelvis_laplacian_left_firm2.glb"
R=D/"renders_v002"; R.mkdir(parents=True,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
objs=[o for o in bpy.context.scene.objects if o.type=="MESH"]
body=max(objs,key=lambda o:len(o.data.polygons))
pts=[o.matrix_world@Vector(c) for o in objs for c in o.bound_box]
mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
H=mx.z-mn.z; cy=(mn.y+mx.y)/2

vg=body.vertex_groups.new(name="UPPER_LEFT_SEAM")
count=0
for v in body.data.vertices:
    w=body.matrix_world@v.co
    curve=.540+.684*abs(w.x)
    d=abs(w.z-curve)
    if not (-.110<w.x<-.005 and .530<w.z<.617 and w.y<cy): continue
    front=max(0.0,min(1.0,(cy-w.y)/(H*.070)))
    weight=math.exp(-0.5*(d/.011)**2)*front
    if weight>.015:
        vg.add([v.index],min(1.0,weight),"REPLACE"); count+=1

mod=body.modifiers.new("UPPER_LEFT_LAP","LAPLACIANSMOOTH")
mod.vertex_group=vg.name
mod.lambda_factor=.30
mod.iterations=8
mod.use_volume_preserve=True
mod.use_x=True; mod.use_y=True; mod.use_z=True
bpy.context.view_layer.objects.active=body; body.select_set(True)
bpy.ops.object.modifier_apply(modifier=mod.name)
for p in body.data.polygons:p.use_smooth=True

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format="GLB",export_apply=True)

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
for view,loc in {"front":(0,mn.y-H*.48,target.z),"threequarter":(H*.20,mn.y-H*.40,target.z)}.items():
    cam.location=loc; look(cam,target); sc.render.filepath=str(R/("pelvis_lap_firm2_"+view+".png")); bpy.ops.render.render(write_still=True)

print("PELVIS_FIRM2 "+json.dumps({"weighted_vertices":count,"out":str(OUT)}),flush=True)
