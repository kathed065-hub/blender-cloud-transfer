import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
D=Path("/data/models/8be67f4c0dd512a4132993698146a687");SRC=D/"v001.glb";OUT=D/"pelvis_segment_B_patch_v2.glb";R=D/"renders_v002";R.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(SRC))
O=[o for o in bpy.context.scene.objects if o.type=="MESH"];B=max(O,key=lambda o:len(o.data.polygons))
P=[o.matrix_world@Vector(c) for o in O for c in o.bound_box];mn=Vector((min(q.x for q in P),min(q.y for q in P),min(q.z for q in P)));mx=Vector((max(q.x for q in P),max(q.y for q in P),max(q.z for q in P)));H=mx.z-mn.z;cy=(mn.y+mx.y)/2
bm=bmesh.new();bm.from_mesh(B.data);bm.faces.ensure_lookup_table();bm.edges.ensure_lookup_table()
N=B.matrix_world.to_3x3()
cut=[]
for f in bm.faces:
 c=B.matrix_world@f.calc_center_median();curve=.540+.684*abs(c.x);wn=N@f.normal
 if -.075<c.x<-.038 and .555<c.z<.603 and c.y<cy and abs(c.z-curve)<.016 and wn.y<-.15:cut.append(f)
cutset=set(cut)
# Exact cut boundary BEFORE deletion: edge has cut face + kept face.
boundary=set()
for f in cut:
 for e in f.edges:
  if any(lf not in cutset for lf in e.link_faces):boundary.add(e)
# Group exact boundary into connected loops before deleting.
byv={}
for e in boundary:
 for v in e.verts:byv.setdefault(v,[]).append(e)
seen=set();loops=[]
for e0 in boundary:
 if e0 in seen:continue
 st=[e0];seen.add(e0);cc=[]
 while st:
  e=st.pop();cc.append(e)
  for v in e.verts:
   for ee in byv.get(v,[]):
    if ee not in seen:seen.add(ee);st.append(ee)
 loops.append(cc)
loop_info=[]
for cc in loops:
 deg={}
 for e in cc:
  for v in e.verts:deg[v]=deg.get(v,0)+1
 loop_info.append({"edges":len(cc),"closed":all(v==2 for v in deg.values())})
before=(len(bm.verts),len(bm.edges),len(bm.faces))
bmesh.ops.delete(bm,geom=cut,context="FACES")
filled_faces=[];newverts=[]
for cc,info in zip(loops,loop_info):
 live=[e for e in cc if e.is_valid and len(e.link_faces)==1]
 if info["closed"] and len(live)>=3:
  res=bmesh.ops.triangle_fill(bm,edges=live,use_beauty=True,use_dissolve=False)
  nf=[g for g in res.get("geom",[]) if isinstance(g,bmesh.types.BMFace)]
  filled_faces.extend(nf)
  if nf:
   bset=set(live);internal=list({e for f in nf for e in f.edges if e not in bset})
   if internal:
    sub=bmesh.ops.subdivide_edges(bm,edges=internal,cuts=1,use_grid_fill=False)
    nv=[g for g in sub.get("geom_inner",[]) if isinstance(g,bmesh.types.BMVert)]
    newverts.extend(nv)
# Smooth only newly generated interior verts; exact cut boundary stays fixed.
if newverts:
 valid=list({v for v in newverts if v.is_valid})
 for _ in range(5):bmesh.ops.smooth_vert(bm,verts=valid,factor=.30,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bm.normal_update();after=(len(bm.verts),len(bm.edges),len(bm.faces));bm.to_mesh(B.data);bm.free();B.data.update()
for p in B.data.polygons:p.use_smooth=True
bpy.ops.object.select_all(action="SELECT");bpy.ops.export_scene.gltf(filepath=str(OUT),export_format="GLB",export_apply=True)

S=bpy.context.scene;S.render.engine="CYCLES";S.cycles.device="CPU";S.cycles.samples=3;S.render.resolution_x=S.render.resolution_y=700;S.render.resolution_percentage=100;S.render.image_settings.file_format="PNG"
if S.world is None:S.world=bpy.data.worlds.new("World")
S.world.use_nodes=True;S.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.06
try:S.view_settings.look="AgX - Medium High Contrast"
except:pass
S.view_settings.exposure=-.6
M=bpy.data.materials.new("C");M.use_nodes=True;bs=M.node_tree.nodes["Principled BSDF"];bs.inputs["Base Color"].default_value=(.28,.31,.36,1);bs.inputs["Roughness"].default_value=.78;S.view_layers["ViewLayer"].material_override=M
cd=bpy.data.cameras.new("Cam");C=bpy.data.objects.new("Cam",cd);S.collection.objects.link(C);S.camera=C;cd.type="ORTHO";cd.ortho_scale=H*.22;tar=Vector((-.055,cy,mn.z+H*.575))
def look(o):o.rotation_euler=(tar-o.location).to_track_quat("-Z","Y").to_euler()
for k,(loc,en) in enumerate([((-H*.2,mn.y-H*.28,tar.z+H*.15),32),((H*.18,mn.y-H*.14,tar.z),12),((0,mx.y+H*.16,tar.z+H*.12),20)]):
 ld=bpy.data.lights.new(str(k),"AREA");ld.energy=en;ld.size=H*.16;lo=bpy.data.objects.new(str(k),ld);S.collection.objects.link(lo);lo.location=loc;look(lo)
for view,loc in {"front":(0,mn.y-H*.48,tar.z),"threequarter":(H*.20,mn.y-H*.40,tar.z)}.items():
 C.location=loc;look(C);S.render.filepath=str(R/("pelvis_segB_patch_v2_"+view+".png"));bpy.ops.render.render(write_still=True)
print("PELVI_SEG_B_PATCH2 "+json.dumps({"cut_faces":len(cut),"exact_boundary_edges":len(boundary),"loops":loop_info,"filled_faces":len(filled_faces),"new_interior_vertices":len(newverts),"before":before,"after":after,"out":str(OUT)}),flush=True)