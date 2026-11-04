import bpy,sys,os,math
from mathutils import Vector
from pathlib import Path

body=Path("/data/models/8be67f4c0dd512a4132993698146a687/v001.glb")
head=Path("/tmp/meshy_head.glb")
out=Path("/data/models/8be67f4c0dd512a4132993698146a687/v002.glb")
rdir=Path("/data/models/8be67f4c0dd512a4132993698146a687/renders_v002"); rdir.mkdir(parents=True,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(body))
body_objs=[o for o in bpy.context.scene.objects if o.type=="MESH"]

pts=[]
for o in body_objs:
    pts += [o.matrix_world@Vector(c) for c in o.bound_box]
mn=Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts)))
mx=Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))
H=mx.z-mn.z
neck_z=mn.z+H*.835
top_z=mx.z

hv=[]
for o in body_objs:
    for v in o.data.vertices:
        w=o.matrix_world@v.co
        if w.z>neck_z and abs(w.x-(mn.x+mx.x)/2)<H*.16: hv.append(w)
xs=sorted(v.x for v in hv); ys=sorted(v.y for v in hv); zs=sorted(v.z for v in hv)
def pct(a,q): return a[int((len(a)-1)*q)]
hc=Vector(((pct(xs,.05)+pct(xs,.95))/2,(pct(ys,.05)+pct(ys,.95))/2,neck_z+(pct(zs,.98)-neck_z)*.54))
target_w=max(pct(xs,.95)-pct(xs,.05),H*.095)

before=set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(head))
new=[o for o in bpy.context.scene.objects if o not in before]
mesh_new=[o for o in new if o.type=="MESH"]

hpts=[]
for o in mesh_new:
    hpts += [o.matrix_world@Vector(c) for c in o.bound_box]
hmn=Vector((min(p.x for p in hpts),min(p.y for p in hpts),min(p.z for p in hpts)))
hmx=Vector((max(p.x for p in hpts),max(p.y for p in hpts),max(p.z for p in hpts)))
hh=hmx.z-hmn.z
upper=[]
for o in mesh_new:
    for v in o.data.vertices:
        w=o.matrix_world@v.co
        if w.z>hmn.z+hh*.28: upper.append(w)
ux=sorted(v.x for v in upper); uy=sorted(v.y for v in upper); uz=sorted(v.z for v in upper)
uw=pct(ux,.95)-pct(ux,.05)
uc=Vector(((pct(ux,.05)+pct(ux,.95))/2,(pct(uy,.05)+pct(uy,.95))/2,(pct(uz,.02)+pct(uz,.98))/2))
scale=(target_w*1.20)/max(uw,1e-6)

for o in new:
    o.scale*=scale
bpy.context.view_layer.update()

# recompute transformed generated center
hpts=[]
for o in mesh_new:
    hpts += [o.matrix_world@Vector(c) for c in o.bound_box]
hmn2=Vector((min(p.x for p in hpts),min(p.y for p in hpts),min(p.z for p in hpts)))
hmx2=Vector((max(p.x for p in hpts),max(p.y for p in hpts),max(p.z for p in hpts)))
cur=(hmn2+hmx2)/2
desired=Vector((hc.x,hc.y,top_z-H*.015))
delta=desired-cur
for o in new: o.location += delta
bpy.context.view_layer.update()

# crop generated shoulders/bust below neck
for o in mesh_new:
    inv=o.matrix_world.inverted()
    kill=[]
    for v in o.data.vertices:
        if (o.matrix_world@v.co).z < neck_z-H*.005: kill.append(v.index)
    if kill:
        bm=__import__("bmesh").new(); bm.from_mesh(o.data)
        verts=[bm.verts[i] for i in kill if i < len(bm.verts)]
        __import__("bmesh").ops.delete(bm,geom=verts,context="VERTS")
        bm.to_mesh(o.data); bm.free(); o.data.update()

# compress old head so it doesn't poke through
for o in body_objs:
    inv=o.matrix_world.inverted()
    changed=False
    for v in o.data.vertices:
        w=o.matrix_world@v.co
        if w.z>neck_z+H*.01 and abs(w.x-hc.x)<H*.16:
            f=min(1,max(0,(w.z-neck_z)/(H*.04)))
            w.x=hc.x+(w.x-hc.x)*(1-.78*f)
            w.y=hc.y+(w.y-hc.y)*(1-.72*f)
            v.co=inv@w; changed=True
    if changed: o.data.update()

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=str(out),export_format="GLB",export_apply=True)

# render closeups
sc=bpy.context.scene; sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=6
sc.render.resolution_x=640; sc.render.resolution_y=640; sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"
if sc.world is None: sc.world=bpy.data.worlds.new("World")
sc.world.color=(.035,.045,.065)
camd=bpy.data.cameras.new("FaceCam"); cam=bpy.data.objects.new("FaceCam",camd); sc.collection.objects.link(cam); sc.camera=cam
camd.type="ORTHO"; camd.ortho_scale=H*.40
target=Vector((hc.x,hc.y,hc.z+H*.01))
for i,(loc,e) in enumerate([((hc.x+H*.22,hc.y-H*.34,hc.z+H*.17),750),((hc.x-H*.18,hc.y-H*.20,hc.z+H*.06),420),((hc.x,hc.y+H*.24,hc.z+H*.20),600)]):
    ld=bpy.data.lights.new(f"L{i}","AREA"); ld.energy=e; ld.size=H*.22
    lo=bpy.data.objects.new(f"L{i}",ld); sc.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(target-lo.location).to_track_quat("-Z","Y").to_euler()
for name,loc in {"face_front":(hc.x,hc.y-H*.58,hc.z+H*.02),"face_threequarter":(hc.x+H*.28,hc.y-H*.50,hc.z+H*.02)}.items():
    cam.location=loc; cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    sc.render.filepath=str(rdir/(name+".png")); bpy.ops.render.render(write_still=True)
print("INTEGRATION_OK",out,flush=True)
