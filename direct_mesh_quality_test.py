import bpy, bmesh, math, json, time, hashlib
from pathlib import Path
from mathutils import Vector

MID="8be67f4c0dd512a4132993698146a687"
D=Path("/data/models")/MID
BODY=D/"v001.glb"
TARGET=Path("/tmp/meshy_head.glb")
OUT=D/"v003_direct_mesh_test.glb"
R=D/"renders_v002"; R.mkdir(parents=True,exist_ok=True)

def world_bbox(objs):
    pts=[o.matrix_world@Vector(c) for o in objs if o.type=="MESH" for c in o.bound_box]
    return Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts)))

def mesh_world_vertices(o):
    return [o.matrix_world@v.co for v in o.data.vertices]

def pct(a,q):
    a=sorted(a); return a[int((len(a)-1)*q)]

def setup_render(sc, H, center):
    sc.render.engine="CYCLES"; sc.cycles.device="CPU"; sc.cycles.samples=4
    sc.render.resolution_x=520; sc.render.resolution_y=520; sc.render.resolution_percentage=100
    sc.render.image_settings.file_format="PNG"; sc.render.film_transparent=False
    if sc.world is None: sc.world=bpy.data.worlds.new("World")
    sc.world.use_nodes=True
    bg=sc.world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(0.025,0.03,0.04,1); bg.inputs["Strength"].default_value=.12
    try: sc.view_settings.look="AgX - Medium High Contrast"
    except: pass
    camd=bpy.data.cameras.new("AuditCam"); cam=bpy.data.objects.new("AuditCam",camd); sc.collection.objects.link(cam); sc.camera=cam
    camd.type="ORTHO"; camd.ortho_scale=H*.31
    target=Vector((center.x,center.y,center.z+H*.006))
    lights=[
      ((center.x+H*.18,center.y-H*.28,center.z+H*.17),110,H*.17),
      ((center.x-H*.20,center.y-H*.12,center.z+H*.05),55,H*.14),
      ((center.x,center.y+H*.18,center.z+H*.19),85,H*.15)]
    for i,(loc,energy,size) in enumerate(lights):
        ld=bpy.data.lights.new(f"AuditL{i}","AREA"); ld.energy=energy; ld.size=size
        lo=bpy.data.objects.new(f"AuditL{i}",ld); sc.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(target-lo.location).to_track_quat("-Z","Y").to_euler()
    return cam,target

def make_clay(name="AuditClay"):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(0.34,0.37,0.41,1)
    bs.inputs["Roughness"].default_value=.72
    bs.inputs["Metallic"].default_value=0
    return m

def make_wire():
    m=bpy.data.materials.new("AuditWire"); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    bs=nt.nodes.new("ShaderNodeBsdfPrincipled")
    wire=nt.nodes.new("ShaderNodeWireframe"); wire.use_pixel_size=True; wire.inputs["Size"].default_value=1.2
    mix=nt.nodes.new("ShaderNodeMixRGB"); mix.blend_type="MIX"
    mix.inputs[1].default_value=(0.42,0.45,0.49,1); mix.inputs[2].default_value=(0.025,0.03,0.035,1)
    nt.links.new(wire.outputs["Fac"],mix.inputs["Fac"]); nt.links.new(mix.outputs["Color"],bs.inputs["Base Color"]); nt.links.new(bs.outputs["BSDF"],out.inputs["Surface"])
    bs.inputs["Roughness"].default_value=.78
    return m

def render_views(sc,cam,target,H,prefix,mat,views=("front","threequarter","profile")):
    sc.view_layers["ViewLayer"].material_override=mat
    locs={
      "front":(target.x,target.y-H*.52,target.z),
      "threequarter":(target.x+H*.235,target.y-H*.42,target.z),
      "profile":(target.x+H*.49,target.y,target.z)}
    for name in views:
        cam.location=locs[name]; cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
        sc.render.filepath=str(R/f"{prefix}_{name}.png"); bpy.ops.render.render(write_still=True)

# Load original body only
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(BODY))
body_objs=[o for o in bpy.context.scene.objects if o.type=="MESH"]
body=max(body_objs,key=lambda o:len(o.data.vertices))
mn,mx=world_bbox(body_objs); H=mx.z-mn.z; cx=(mn.x+mx.x)/2
neck_z=mn.z+H*.835
head_pts=[w for w in mesh_world_vertices(body) if w.z>=neck_z and abs(w.x-cx)<H*.16]
if len(head_pts)<100: raise RuntimeError("head region not found")
hx=[p.x for p in head_pts]; hy=[p.y for p in head_pts]; hz=[p.z for p in head_pts]
head_top=pct(hz,.995); head_h=head_top-neck_z
hc=Vector(((pct(hx,.04)+pct(hx,.96))/2,(pct(hy,.04)+pct(hy,.96))/2,neck_z+head_h*.54))
head_front=pct(hy,.025)

sc=bpy.context.scene; cam,aim=setup_render(sc,H,hc); clay=make_clay(); wire=make_wire()
render_views(sc,cam,aim,H,"direct_before_clay",clay)

# Save exact original coordinates for proof
orig=[v.co.copy() for v in body.data.vertices]
vcount=len(body.data.vertices); pcount=len(body.data.polygons)

# Import Meshy only as hidden deformation target
before=set(bpy.context.scene.objects)
bpy.ops.import_scene.gltf(filepath=str(TARGET))
target_objs=[o for o in bpy.context.scene.objects if o not in before and o.type=="MESH"]
if not target_objs: raise RuntimeError("target mesh not found")
bpy.ops.object.select_all(action="DESELECT")
for o in target_objs: o.select_set(True)
bpy.context.view_layer.objects.active=target_objs[0]
if len(target_objs)>1: bpy.ops.object.join()
t=bpy.context.view_layer.objects.active
tmn,tmx=world_bbox([t]); TH=tmx.z-tmn.z
tw=mesh_world_vertices(t)
# Upper 60% = head/hair, excluding shoulders and chest
tneck=tmn.z+TH*.39
thp=[p for p in tw if p.z>=tneck]
tx=[p.x for p in thp]; ty=[p.y for p in thp]; tz=[p.z for p in thp]
t_head_h=pct(tz,.995)-pct(tz,.02)
scale=(head_h*1.03)/max(t_head_h,1e-6)
t.scale*=scale; bpy.context.view_layer.update()
# Recompute, align x/top/front
tw=mesh_world_vertices(t); tmn,tmx=world_bbox([t]); TH2=tmx.z-tmn.z
tneck2=tmn.z+TH2*.39
thp=[p for p in tw if p.z>=tneck2]
tx=[p.x for p in thp]; ty=[p.y for p in thp]; tz=[p.z for p in thp]
tcx=(pct(tx,.10)+pct(tx,.90))/2
tfront=pct(ty,.025); ttop=pct(tz,.995)
t.location += Vector((hc.x-tcx,head_front-tfront,head_top-ttop))
bpy.context.view_layer.update()
t.hide_render=True

# FACE_TRANSFER vertex group: direct manipulation of original mesh only
vg=body.vertex_groups.get("FACE_TRANSFER") or body.vertex_groups.new(name="FACE_TRANSFER")
weighted=[]; masked=set()
inv=body.matrix_world.inverted()
for v in body.data.vertices:
    w=body.matrix_world@v.co
    nz=(w.z-neck_z)/max(head_h,1e-6)
    nx=abs(w.x-hc.x)/(H*.125)
    # Only face/front half; preserve rear cranium, body and neck
    front=(hc.y+H*.012-w.y)/(H*.095)
    if .045<nz<.90 and nx<1.0 and front>-0.05:
        vz=min(1,(nz-.045)/.12)*min(1,(.90-nz)/.16)
        vx=max(0,1-nx**4)
        vf=max(0,min(1,(front+.05)/.40))
        weight=max(0,min(1,vz*vx*vf*.72))
        if weight>.02:
            vg.add([v.index],weight,"REPLACE"); weighted.append(weight); masked.add(v.index)

bpy.context.view_layer.objects.active=body; body.select_set(True)
sw=body.modifiers.new("DIRECT_FACE_TRANSFER","SHRINKWRAP")
sw.target=t; sw.vertex_group=vg.name; sw.wrap_method="PROJECT"; sw.wrap_mode="ON_SURFACE"
sw.use_project_y=True; sw.use_positive_direction=True; sw.use_negative_direction=True
sw.project_limit=H*.055; sw.offset=0
bpy.ops.object.modifier_apply(modifier=sw.name)

# Gentle smoothing in same mask, still same vertices/topology
sm=body.modifiers.new("DIRECT_FACE_SMOOTH","SMOOTH"); sm.vertex_group=vg.name; sm.factor=.16; sm.iterations=2
bpy.ops.object.modifier_apply(modifier=sm.name)

# Verify topology + displacement + zero movement outside mask
if len(body.data.vertices)!=vcount or len(body.data.polygons)!=pcount: raise RuntimeError("topology changed")
moves=[]; outside=[]
for i,v in enumerate(body.data.vertices):
    d=(v.co-orig[i]).length
    (moves if i in masked else outside).append(d)
max_move=max(moves) if moves else 0
max_out=max(outside) if outside else 0
mean_move=sum(moves)/max(1,len(moves))
if max_out>1e-7: raise RuntimeError(f"outside mask changed {max_out}")

# Hide reference completely
t.hide_viewport=True; t.hide_render=True

# Export only original scene body objects, not Meshy target
bpy.ops.object.select_all(action="DESELECT")
for o in body_objs: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT),export_format="GLB",use_selection=True,export_apply=True)

render_views(sc,cam,aim,H,"direct_after_clay",clay)
render_views(sc,cam,aim,H,"direct_after_wire",wire,views=("front","threequarter"))

report={
 "method":"direct deformation of original vertices; Meshy only hidden shrinkwrap target",
 "topology_preserved":True,
 "vertices":vcount,"polygons":pcount,
 "masked_vertices":len(masked),
 "max_displacement_local":max_move,
 "mean_displacement_local":mean_move,
 "max_displacement_outside_mask":max_out,
 "output":str(OUT),
 "renders":[p.name for p in sorted(R.glob("direct_*png"))]
}
(D/"direct_mesh_test_report.json").write_text(json.dumps(report,indent=2),"utf-8")
print("DIRECT_MESH_TEST_OK "+json.dumps(report),flush=True)
