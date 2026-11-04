import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector
D=Path("/data/models/8be67f4c0dd512a4132993698146a687");SRC=D/"v001.glb";OUT=D/"pelvis_segment_A_dissolve5.glb";R=D/"renders_v002";R.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(SRC))
O=[o for o in bpy.context.scene.objects if o.type=="MESH"];B=max(O,key=lambda o:len(o.data.polygons))
P=[o.matrix_world@Vector(c) for o in O for c in o.bound_box];mn=Vector((min(q.x for q in P),min(q.y for q in P),min(q.z for q in P)));mx=Vector((max(q.x for q in P),max(q.y for q in P),max(q.z for q in P)));H=mx.z-mn.z;cy=(mn.y+mx.y)/2
bm=bmesh.new();bm.from_mesh(B.data);bm.edges.ensure_lookup_table();bm.faces.ensure_lookup_table()
es=[];ang=[]
for e in bm.edges:
 if len(e.link_faces)!=2:continue
 c=(e.verts[0].co+e.verts[1].co)*.5;w=B.matrix_world@c;curve=.540+.684*abs(w.x)
 if -.112<w.x<-.072 and .584<w.z<.624 and w.y<cy and abs(w.z-curve)<.009:
  a=e.calc_face_angle(0.0)
  if a>math.radians(32):es.append(e);ang.append(math.degrees(a))
before=(len(bm.verts),len(bm.edges),len(bm.faces))
if es:bmesh.ops.dissolve_edges(bm,edges=es,use_verts=False,use_face_split=False)
# retriangulate only resulting local faces around segment A
local=[]
for f in bm.faces:
 c=B.matrix_world@f.calc_center_median();curve=.540+.684*abs(c.x)
 if -.120<c.x<-.064 and .574<c.z<.634 and c.y<cy and abs(c.z-curve)<.018:local.append(f)
if local:bmesh.ops.triangulate(bm,faces=local,quad_method="BEAUTY",ngon_method="BEAUTY")
bm.normal_update();after=(len(bm.verts),len(bm.edges),len(bm.faces));bm.to_mesh(B.data);bm.free();B.data.update()
for p in B.data.polygons:p.use_smooth=True
bpy.ops.object.select_all(action="SELECT");bpy.ops.export_scene.gltf(filepath=str(OUT),export_format="GLB",export_apply=True)
# render
S=bpy.context.scene;S.render.engine="CYCLES";S.cycles.device="CPU";S.cycles.samples=3;S.render.resolution_x=S.render.resolution_y=700;S.render.resolution_percentage=100;S.render.image_settings.file_format="PNG"
if S.world is None:S.world=bpy.data.worlds.new("World")
S.world.use_nodes=True;S.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.06
try:S.view_settings.look="AgX - Medium High Contrast"
except:pass
S.view_settings.exposure=-.6
M=bpy.data.materials.new("C");M.use_nodes=True;bs=M.node_tree.nodes["Principled BSDF"];bs.inputs["Base Color"].default_value=(.28,.31,.36,1);bs.inputs["Roughness"].default_value=.78;S.view_layers["ViewLayer"].material_override=M
cd=bpy.data.cameras.new("Cam");C=bpy.data.objects.new("Cam",cd);S.collection.objects.link(C);S.camera=C;cd.type="ORTHO";cd.ortho_scale=H*.25;tar=Vector((-.06,cy,mn.z+H*.575))
def look(o):o.rotation_euler=(tar-o.location).to_track_quat("-Z","Y").to_euler()
for k,(loc,en) in enumerate([((-H*.2,mn.y-H*.28,tar.z+H*.15),32),((H*.18,mn.y-H*.14,tar.z),12),((0,mx.y+H*.16,tar.z+H*.12),20)]):
 ld=bpy.data.lights.new(str(k),"AREA");ld.energy=en;ld.size=H*.16;lo=bpy.data.objects.new(str(k),ld);S.collection.objects.link(lo);lo.location=loc;look(lo)
for view,loc in {"front":(0,mn.y-H*.48,tar.z),"threequarter":(H*.20,mn.y-H*.40,tar.z)}.items():
 C.location=loc;look(C);S.render.filepath=str(R/("pelvis_segA_dissolve5_"+view+".png"));bpy.ops.render.render(write_still=True)
print("PELVI_SEG_A_DISSOLVE5 "+json.dumps({"edges":len(es),"angles":ang,"local_faces":len(local),"before":before,"after":after,"out":str(OUT)}),flush=True)