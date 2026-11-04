import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
D=Path("/data/models/8be67f4c0dd512a4132993698146a687");SRC=D/"v001.glb";OUT=D/"pelvis_segment_B_patch_v1.glb";R=D/"renders_v002";R.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(SRC))
O=[o for o in bpy.context.scene.objects if o.type=="MESH"];B=max(O,key=lambda o:len(o.data.polygons))
P=[o.matrix_world@Vector(c) for o in O for c in o.bound_box];mn=Vector((min(q.x for q in P),min(q.y for q in P),min(q.z for q in P)));mx=Vector((max(q.x for q in P),max(q.y for q in P),max(q.z for q in P)));H=mx.z-mn.z;cy=(mn.y+mx.y)/2
bm=bmesh.new();bm.from_mesh(B.data);bm.faces.ensure_lookup_table();bm.edges.ensure_lookup_table()
# Interior third only: completely away from external silhouette.
cut=[]
for f in bm.faces:
 c=B.matrix_world@f.calc_center_median();curve=.540+.684*abs(c.x)
 if -.075<c.x<-.038 and .555<c.z<.603 and c.y<cy and abs(c.z-curve)<.016:cut.append(f)
before=(len(bm.verts),len(bm.edges),len(bm.faces));bmesh.ops.delete(bm,geom=cut,context="FACES")
# Boundary connected components.
bedges=[e for e in bm.edges if len(e.link_faces)==1];byv={}
for e in bedges:
 for v in e.verts:byv.setdefault(v,[]).append(e)
seen=set();comps=[]
for e0 in bedges:
 if e0 in seen:continue
 st=[e0];seen.add(e0);cc=[]
 while st:
  e=st.pop();cc.append(e)
  for v in e.verts:
   for ee in byv.get(v,[]):
    if ee not in seen:seen.add(ee);st.append(ee)
 comps.append(cc)
best=[];score=-1;closed=False
for cc in comps:
 hit=0;deg={}
 for e in cc:
  for v in e.verts:deg[v]=deg.get(v,0)+1
  c=B.matrix_world@((e.verts[0].co+e.verts[1].co)*.5);curve=.540+.684*abs(c.x)
  if -.085<c.x<-.028 and .545<c.z<.613 and c.y<cy and abs(c.z-curve)<.030:hit+=1
 isclosed=bool(cc) and all(v==2 for v in deg.values())
 # require closed loop and strongest overlap
 if isclosed and hit>score and len(cc)<220:score=hit;best=cc;closed=True
newfaces=[];newverts=[]
if best:
 res=bmesh.ops.triangle_fill(bm,edges=best,use_beauty=True,use_dissolve=False)
 newfaces=[g for g in res.get("geom",[]) if isinstance(g,bmesh.types.BMFace)]
 if newfaces:
  boundary_set=set(best)
  internal=list({e for f in newfaces for e in f.edges if e not in boundary_set})
  if internal:
   sub=bmesh.ops.subdivide_edges(bm,edges=internal,cuts=1,use_grid_fill=False)
   newverts=[g for g in sub.get("geom_inner",[]) if isinstance(g,bmesh.types.BMVert)]
   if newverts:
    for _ in range(4):
     bmesh.ops.smooth_vert(bm,verts=[v for v in newverts if v.is_valid],factor=.35,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bm.normal_update();after=(len(bm.verts),len(bm.edges),len(bm.faces));bm.to_mesh(B.data);bm.free();B.data.update()
for p in B.data.polygons:p.use_smooth=True
bpy.ops.object.select_all(action="SELECT");bpy.ops.export_scene.gltf(filepath=str(OUT),export_format="GLB",export_apply=True)
# Render
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
 C.location=loc;look(C);S.render.filepath=str(R/("pelvis_segB_patch_v1_"+view+".png"));bpy.ops.render.render(write_still=True)
print("PELVI_SEG_B_PATCH "+json.dumps({"cut_faces":len(cut),"chosen_edges":len(best),"closed":closed,"hit_score":score,"filled_faces":len(newfaces),"new_interior_vertices":len(newverts),"before":before,"after":after,"out":str(OUT)}),flush=True)