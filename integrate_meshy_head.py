import bpy,math,json
from pathlib import Path
from mathutils import Vector
D=Path("/data/models/8be67f4c0dd512a4132993698146a687");SRC=D/"v001.glb";R=D/"renders_v002";R.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(SRC))
O=[o for o in bpy.context.scene.objects if o.type=="MESH"];B=max(O,key=lambda o:len(o.data.polygons))
P=[o.matrix_world@Vector(c) for o in O for c in o.bound_box];mn=Vector((min(q.x for q in P),min(q.y for q in P),min(q.z for q in P)));mx=Vector((max(q.x for q in P),max(q.y for q in P),max(q.z for q in P)));H=mx.z-mn.z;cy=(mn.y+mx.y)/2
orig=[v.co.copy() for v in B.data.vertices];inv=B.matrix_world.inverted();adj=[set() for _ in B.data.vertices]
for e in B.data.edges:a,b=e.vertices;adj[a].add(b);adj[b].add(a)
def W(i):return B.matrix_world@orig[i]
def sd(q):return q.z-(.540+.684*abs(q.x))
core=[v.index for v in B.data.vertices if (-.108<(q:=W(v.index)).x<-.006 and .532<q.z<.616 and q.y<cy and abs(sd(q))<.0065)]
T={}
for i in core:
 q=W(i);seen={i};fr={i};cand=[]
 for _ in range(3):
  nx=set()
  for u in fr:
   for j in adj[u]:
    if j not in seen:seen.add(j);nx.add(j);cand.append(j)
  fr=nx
 up=[];dn=[]
 for j in cand:
  p=W(j);d=sd(p)
  if not(-.125<p.x<.005 and p.y<cy and abs(p.x-q.x)<.026):continue
  if .010<d<.040:up.append((j,d))
  elif -.040<d<-.010:dn.append((j,-d))
 if not up or not dn:continue
 def av(a):
  a=sorted(a,key=lambda x:x[1])[:4];v=Vector((0,0,0));sw=0
  for j,d in a:wt=1/max(d,.002);v+=W(j)*wt;sw+=wt
  return v/sw
 t=(av(up)+av(dn))*.5;t.x=q.x*.92+t.x*.08;T[i]=t
# renderer
S=bpy.context.scene;S.render.engine="CYCLES";S.cycles.device="CPU";S.cycles.samples=3;S.render.resolution_x=S.render.resolution_y=700;S.render.resolution_percentage=100;S.render.image_settings.file_format="PNG"
if S.world is None:S.world=bpy.data.worlds.new("World")
S.world.use_nodes=True;S.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.06
try:S.view_settings.look="AgX - Medium High Contrast"
except:pass
S.view_settings.exposure=-.6
M=bpy.data.materials.new("C");M.use_nodes=True;bs=M.node_tree.nodes["Principled BSDF"];bs.inputs["Base Color"].default_value=(.28,.31,.36,1);bs.inputs["Roughness"].default_value=.78;S.view_layers["ViewLayer"].material_override=M
cd=bpy.data.cameras.new("Cam");C=bpy.data.objects.new("Cam",cd);S.collection.objects.link(C);S.camera=C;cd.type="ORTHO";cd.ortho_scale=H*.29;tar=Vector((0,cy,mn.z+H*.57))
def look(o):o.rotation_euler=(tar-o.location).to_track_quat("-Z","Y").to_euler()
for k,(loc,en) in enumerate([((-H*.20,mn.y-H*.28,tar.z+H*.15),32),((H*.18,mn.y-H*.14,tar.z+H*.01),12),((0,mx.y+H*.16,tar.z+H*.14),20)]):
 ld=bpy.data.lights.new(str(k),"AREA");ld.energy=en;ld.size=H*.16;lo=bpy.data.objects.new(str(k),ld);S.collection.objects.link(lo);lo.location=loc;look(lo)
def rend(p):
 for n,l in {"front":(0,mn.y-H*.48,tar.z),"threequarter":(H*.20,mn.y-H*.40,tar.z)}.items():C.location=l;look(C);S.render.filepath=str(R/(p+"_"+n+".png"));bpy.ops.render.render(write_still=True)
rend("pelvis_bridge_before")
res=[]
for tag,a in [("mid",.55),("high",.85)]:
 for v,c in zip(B.data.vertices,orig):v.co=c
 for i,t in T.items():B.data.vertices[i].co=inv@(W(i).lerp(t,a))
 B.data.update()
 vg=B.vertex_groups.get("BL") or B.vertex_groups.new(name="BL");ring=set(T)
 for i in list(T):ring.update(adj[i])
 for i in ring:vg.add([i],1 if i in T else .3,"REPLACE")
 m=B.modifiers.new("S","SMOOTH");m.vertex_group=vg.name;m.factor=.22;m.iterations=2;m.use_x=False;m.use_y=True;m.use_z=False;bpy.context.view_layer.objects.active=B;B.select_set(True);bpy.ops.object.modifier_apply(modifier=m.name)
 for p in B.data.polygons:p.use_smooth=True
 o=D/f"pelvis_bridge_left_{tag}.glb";bpy.ops.object.select_all(action="SELECT");bpy.ops.export_scene.gltf(filepath=str(o),export_format="GLB",export_apply=True);rend("pelvis_bridge_"+tag);res.append([tag,str(o)])
print("PELVIS_BRIDGE_RESULT "+json.dumps({"core":len(core),"targets":len(T),"res":res}),flush=True)