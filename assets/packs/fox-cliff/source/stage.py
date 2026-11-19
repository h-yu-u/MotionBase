import math
import random
import bpy
from art import Artwork


def build():
    coll=bpy.data.collections.new("Cliff")
    bpy.context.scene.collection.children.link(coll)
    a=Artwork(coll)
    rng=random.Random(81)
    a.shape("Sky",[(-9,-4),(9,-4),(9,7),(-9,7)],5.5,"sky")
    a.oval("Moon",1.75,2.61,.72,.72,5.0,"sun",steps=96)
    def ridge(name,y,z,rough,role,frequency):
        peaks=[(x*.19-5.7,z+rough*(.45*math.sin(x*frequency)+.72*math.sin(x*frequency*.59+2)+rng.uniform(-.1,.1))) for x in range(61)]
        return a.shape(name,peaks+[(5.7,-2),(-5.7,-2)],y,role)
    ridge("Distant range",4.5,1.54,.49,"far",.23)
    ridge("Middle range",3.8,1.05,.33,"mid",.31)
    for i in range(32):
        x,z=rng.uniform(-4.9,4.9),rng.uniform(.79,2.76)
        length=rng.uniform(.10,.68)
        a.shape("Mist wisp",[(x,z),(x+length*.28,z+.009),(x+length,z+.008),(x+.64*length,z-.005)],3.5,"mist")
    # A distant shrine gives the performer a scale reference.
    for x in (-2.86,-2.23):
        a.shape("Gate pillar",[(x-.035,.22),(x+.044,.22),(x+.035,1.82),(x-.027,1.82)],2.85,"mid")
    a.shape("Gate lintel",[(-3.05,1.86),(-2.87,1.82),(-2.24,1.82),(-2.04,1.86),(-2.10,1.78),(-2.99,1.78)],2.83,"mid")
    a.shape("Gate crossbar",[(-2.98,1.63),(-2.10,1.63),(-2.10,1.59),(-2.98,1.59)],2.83,"mid")
    for i in range(34):
        x=rng.uniform(-4.75,4.75);z=rng.uniform(.1,.55)
        h=rng.uniform(.22,.53);r=h*.29
        outline=[(x,z+h),(x+r*.47,z+h*.69),(x+r*.25,z+h*.72),(x+r*.81,z+h*.39),
                 (x+r*.53,z+h*.43),(x+r,z+.05),(x+.02,z+.09),(x+.02,z-.13),
                 (x-.02,z-.13),(x-.02,z+.09),(x-r,z+.04),(x-r*.61,z+h*.44),
                 (x-r*.83,z+h*.39),(x-r*.34,z+h*.72),(x-r*.49,z+h*.68)]
        a.shape("Cypress",outline,2.5,"mid")
    ridge("Low bank",2.28,.23,.16,"bank",.37)
    ground=[(-6,.005),(-3.9,.007),(-3,.01),(-2.4,-.012),(-1.6,.009),(-.9,-.007),(-.2,.002),
            (.43,-.008),(1.02,.009),(1.83,0),(2.4,-.015),(3.21,.01),(4.8,-.002),(6,.008),(6,-2),(-6,-2)]
    a.shape("Rock shelf",ground,.68,"earth")
    for i in range(45):
        x,z=rng.uniform(-4.7,4.5),rng.uniform(-.59,-.035)
        w=rng.uniform(.05,.55)
        a.shape("Basalt grain",[(x,z),(x+w*.32,z+.012),(x+w,z+.019),(x+w*.53,z-.008)],.46,"stone")
    for side in (-1,1):
        for i in range(25):
            x=side*(2.9+rng.random()*1.9); b=rng.uniform(-.18,-.01)
            h=rng.uniform(.1,.63);d=rng.uniform(.035,.17)*side
            a.shape("Reed",[(x-.017,b),(x+d*.27,b+h*.55),(x+d,b+h),(x+d*.38,b+h*.38),(x+.014,b)],-.72,"grass")
    cam=bpy.data.objects.new("ShotCamera",bpy.data.cameras.new("ShotCamera"))
    coll.objects.link(cam)
    cam["motionbase_id"]="ShotCamera"
    cam.data.type="ORTHO"
    cam.data.ortho_scale=7.4
    cam.rotation_euler=(math.pi/2,0,0)
    for f,x,z in [(1,-.08,1.46),(41,-.12,1.44),(80,.08,2.06),(102,.25,1.57),(150,.32,1.46)]:
        cam.location=(x,-9,z)
        cam.keyframe_insert("location",frame=f)
    light=bpy.data.lights.new("Key","AREA")
    light.energy=380
    light.shape="DISK"
    light.size=4.0
    lamp=bpy.data.objects.new("Key",light)
    lamp.location=(-3,-4,5)
    from mathutils import Vector
    lamp.rotation_euler=(Vector((0,0,1))-lamp.location).to_track_quat("-Z","Y").to_euler()
    coll.objects.link(lamp)
    return coll
