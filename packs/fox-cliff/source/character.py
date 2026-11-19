"""An original fox-mask performer, assembled entirely from rigged cutout meshes."""
import bpy
from mathutils import Vector
from art import Artwork

HIP=1.02
SHOULDER=1.62
ARM=.39
FOREARM=.39
THIGH=.58
SHIN=.56
BLADE_Z=1.43


def build():
    coll = bpy.data.collections.new("Performer")
    bpy.context.scene.collection.children.link(coll)
    arm = bpy.data.armatures.new("Biped")
    rig = bpy.data.objects.new("PerformerRig",arm)
    rig["motionbase_id"] = "PerformerRig"
    coll.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    def bone(name,h,t,parent=None):
        b = arm.edit_bones.new(name)
        b.head=(h[0],0,h[1]); b.tail=(t[0],0,t[1])
        if parent:
            b.parent=arm.edit_bones[parent]
    bone("root",(0,HIP),(0,HIP+.13))
    bone("torso",(0,HIP),(0,SHOULDER),"root")
    bone("head",(0,SHOULDER),(0,2.05),"torso")
    bone("cape",(0,1.56),(-.64,1.49),"torso")
    bone("ribbon",(-.64,1.49),(-1.07,1.44),"cape")
    for side in ("far","near"):
        bone("arm."+side,(0,SHOULDER),(0,SHOULDER-ARM),"torso")
        bone("forearm."+side,(0,SHOULDER-ARM),(0,SHOULDER-ARM-FOREARM),"arm."+side)
        bone("thigh."+side,(0,HIP),(0,HIP-THIGH),"root")
        bone("shin."+side,(0,HIP-THIGH),(0,HIP-THIGH-SHIN),"thigh."+side)
        bone("foot."+side,(0,HIP-THIGH-SHIN),(.23,HIP-THIGH-SHIN),"shin."+side)
    bone("prop",(0,BLADE_Z),(1.58,BLADE_Z))
    bpy.ops.object.mode_set(mode="OBJECT")
    art=Artwork(coll,rig)
    S=art.shape
    for side,layer in (("far",.14),("near",-.025)):
        b="thigh."+side
        pants="shade" if side=="far" else "cloth"
        S("Hakama "+side,[(-.13,1.11),(.16,1.08),(.21,.77),(.115,.42),(.02,.38),(-.16,.43),(-.21,.65)],layer,pants,b)
        S("Pleat "+side,[(-.065,1.01),(.072,.86),(.115,.52),(.02,.69)],layer-.009,"shade",b)
        b="shin."+side
        S("Greave "+side,[(-.105,.48),(.11,.48),(.067,-.12),(-.06,-.14),(-.102,.18)],layer-.008,"trim",b)
        for j in range(4):
            h=-.03+j*.105
            S("Greave binding", [(-.075,h+.042),(.066,h+.006),(.071,h-.016),(-.072,h+.018)],layer-.017,"shade",b)
        b="foot."+side
        S("Tabi "+side,[(-.065,-.081),(.07,-.097),(.182,-.158),(.247,-.153),(.255,-.207),(-.068,-.207)],layer-.020,"ink",b)
        S("Sandal sole",[(-.073,-.184),(.249,-.178),(.256,-.207),(-.068,-.218)],layer-.028,"metal",b)
    S("Back scarf",[(-.09,1.67),(.09,1.53),(-.35,1.43),(-.73,1.43),(-.66,1.51),(-.42,1.59)],.12,"accent","cape")
    S("Silk end",[(-.61,1.54),(-.67,1.43),(-.88,1.39),(-1.16,1.26),(-1.06,1.41),(-1.21,1.44),(-.95,1.51)],.115,"accent","ribbon")
    S("Haori silhouette",[(-.20,1.63),(.06,1.72),(.21,1.59),(.16,1.20),(.26,.96),(.13,.86),(-.02,.94),(-.26,.85),(-.20,1.14),(-.28,1.42)],.010,"coat","torso")
    S("Haori shadow",[(-.19,1.6),(-.10,1.4),(-.055,1.08),(-.26,.85),(-.20,1.16),(-.27,1.39)],-.004,"coat_dark","torso")
    S("Lapel",[(-.095,1.67),(.02,1.65),(.17,1.55),(.052,1.27),(-.018,1.11),(-.085,1.15),(.051,1.5)],-.018,"trim","torso")
    S("Obi",[(-.213,1.16),(.169,1.19),(.159,1.097),(-.216,1.066)],-.026,"accent","torso")
    for x,z in [(-.14,1.39),(-.16,1.27),(-.06,.991),(.105,.995)]:
        S("Woven diamond",[(x-.039,z),(x,z+.052),(x+.038,z),(x,z-.051)],-.028,"trim","torso")
    for side,y in (("far",.095),("near",-.064)):
        b="arm."+side
        S("Kimono sleeve", [(-.11,1.62),(.08,1.66),(.145,1.57),(.158,1.28),(.06,1.16),(-.16,1.22),(-.19,1.47)],y,"coat" if side=="near" else "coat_dark",b)
        S("Cuff trim",[(-.158,1.245),(.149,1.297),(.151,1.258),(.05,1.175),(-.157,1.22)],y-.012,"coat_dark",b)
        S("Sleeve crest",[(-.08,1.47),(-.004,1.55),(.075,1.47),(-.004,1.39)],y-.014,"trim",b)
        b="forearm."+side
        S("Bracer", [(-.084,1.27),(.08,1.27),(.051,.89),(-.055,.875),(-.094,1.09)],y-.028,"shade",b)
        S("Bracer line",[(-.06,1.17),(.066,1.133),(.06,1.104),(-.063,1.143)],y-.04,"trim",b)
        art.oval("Glove",0,.849,.074,.080,y-.05,"glove",b,12)
    b="head"
    S("Hair",[(-.12,1.67),(-.255,1.72),(-.207,1.78),(-.382,1.78),(-.273,1.89),(-.374,1.93),(-.244,2.014),(-.251,2.12),(-.098,2.103),(-.024,2.219),(.106,2.155),(.203,2.10),(.20,1.85),(.04,1.66)],-.08,"hair",b)
    S("Fox mask outline",[(-.155,1.75),(-.199,1.94),(-.238,2.254),(-.06,2.122),(.08,2.144),(.196,2.277),(.188,2.072),(.246,1.984),(.232,1.93),(.323,1.877),(.217,1.84),(.158,1.745),(.016,1.70)],-.135,"ink",b)
    S("Fox mask",[(-.138,1.772),(-.174,1.943),(-.213,2.215),(-.062,2.099),(.086,2.124),(.178,2.237),(.167,2.061),(.221,1.98),(.210,1.931),(.293,1.879),(.202,1.857),(.145,1.767),(.019,1.725)],-.153,"mask",b)
    S("Ear lacquer",[(-.188,2.16),(-.085,2.082),(-.142,2.035)],-.164,"accent",b)
    S("Ear glaze",[(.107,2.103),(.161,2.19),(.146,2.072)],-.164,"accent",b)
    S("Mask shadow",[(-.139,1.921),(-.034,1.843),(.190,1.858),(.131,1.775),(.02,1.739),(-.095,1.785)],-.167,"mask_shadow",b)
    S("Eye enamel",[(-.079,2.016),(.032,1.983),(.193,2.014),(.144,1.958),(.019,1.951)],-.178,"accent",b)
    S("Eye slit",[(-.045,1.99),(.037,1.967),(.172,1.992),(.092,1.953),(.03,1.95)],-.185,"ink",b)
    S("Cheek enamel",[(-.11,1.928),(-.016,1.901),(.10,1.913),(.027,1.879),(-.057,1.872)],-.18,"accent",b)
    S("Mask nose",[(.22,1.904),(.29,1.878),(.235,1.863)],-.181,"ink",b)
    b="prop";z=BLADE_Z
    def prop(name,points,role,y=-.235):
        S(name,[(x,z+v) for x,v in points],y,role,b)
    prop("Hilt",[(-.26,-.035),(.12,-.037),(.12,.037),(-.26,.036)],"ink")
    for j in range(5):
        x=-.24+j*.07
        prop("Hilt cord",[(x,-.03),(x+.017,-.03),(x+.048,.03),(x+.031,.03)],"trim",-.242)
    prop("Guard",[(.082,-.102),(.144,-.083),(.151,.085),(.089,.099)],"accent",-.245)
    prop("Blade",[(.136,-.029),(.62,-.025),(1.18,.003),(1.63,.109),(1.475,.012),(1.16,-.044),(.64,-.077),(.136,-.067)],"metal")
    prop("Cutting edge",[(.139,-.065),(.75,-.064),(1.195,-.029),(1.62,.106),(1.476,.009),(1.16,-.05),(.64,-.082),(.139,-.073)],"glint",-.244)
    return coll,rig
