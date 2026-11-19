"""Authoring fixture. The runtime itself plays ordinary Blender Actions."""
import bisect
import math
from mathutils import Quaternion, Vector
from character import ARM, FOREARM, THIGH, SHIN, HIP, SHOULDER, BLADE_Z

# frame, hip x/z, torso lean, grip offset from shoulder, prop angle,
# far ankle x/z, near ankle x/z, cape rotation.
POSES = [
 (1, -1.33,.99, 7, .29,-.23, 127, -1.71,.095, -.98,.095, 6),
 (16,-1.35,.97, 10,.30,-.20, 135, -1.71,.095, -.98,.095, 11),
 (32,-1.46,.80, 29,.13,-.31, 171, -1.71,.095, -.98,.095, 21),
 (43,-1.32,.72, 39,.04,-.24, 204, -1.71,.095, -.98,.095, 33),
 (52,-.99, .98, 28,.07,.05, 174, -1.55,.16, -.76,.27, 18),
 (65,-.46,1.52, 22,.04,.33, 146, -.92,.70, -.06,.88, 13),
 (75,-.02,1.63, 18,.15,.39, 126, -.55,.91, .47,.98, 2),
 (82,.23, 1.52, 30,.36,.29,  87, -.26,.71, .64,.74, -8),
 (88,.48, 1.31, 47,.50,.08,  28, .03,.47, .91,.44, -19),
 (95,.78, 1.02, 54,.54,-.17,-17, .24,.24, 1.30,.10, -27),
 (106,.95,.79, 44,.44,-.31,-35, .49,.095,1.30,.095,-10),
 (119,.92,.86, 29,.38,-.23,-24, .49,.095,1.30,.095, 10),
 (137,.94,.97, 13,.29,-.16, 13, .49,.095,1.30,.095, 4),
 (150,.94,.98, 11,.28,-.15, 17, .49,.095,1.30,.095, 7),
]


def sample(keys, t):
    """Monotone cubic Hermite; no overshoot on planted feet or held poses."""
    times = [row[0] for row in keys]
    i = min(len(keys)-2,max(0,bisect.bisect_right(times,t)-1))
    h = times[i+1]-times[i]
    u = min(1,max(0,(t-times[i])/h))
    def slope(j,col):
        if j==0 or j==len(keys)-1:
            return 0
        h0,h1=times[j]-times[j-1],times[j+1]-times[j]
        a=(keys[j][col]-keys[j-1][col])/h0
        b=(keys[j+1][col]-keys[j][col])/h1
        if a*b<=0:
            return 0
        w1,w2=2*h1+h0,h1+2*h0
        return (w1+w2)/(w1/a+w2/b)
    return [(2*u**3-3*u*u+1)*keys[i][n]+(u**3-2*u*u+u)*h*slope(i,n)
           +(-2*u**3+3*u*u)*keys[i+1][n]+(u**3-u*u)*h*slope(i+1,n)
           for n in range(1,len(keys[0]))]


def ik(a, b, length_a, length_b, bend):
    dx,dz=b[0]-a[0], b[1]-a[1]
    dist=max(.001,min(math.hypot(dx,dz), length_a+length_b-.00001))
    base=math.atan2(dz,dx)
    cosine=(length_a**2+dist**2-length_b**2)/(2*length_a*dist)
    upper=base+bend*math.acos(max(-1,min(1,cosine)))
    elbow=(a[0]+length_a*math.cos(upper),a[1]+length_a*math.sin(upper))
    return math.degrees(upper),math.degrees(math.atan2(b[1]-elbow[1],b[0]-elbow[0]))


def build(rig):
    import bpy
    action=bpy.data.actions.new("Leap and sweep")
    rig.animation_data_create().action=action
    previous={}
    for frame in range(1,151):
        hx,hz,lean,gx,gz,angle,fx,fz,nx,nz,cape=sample(POSES,frame)
        rx=math.radians(lean)
        shoulder=(hx+(SHOULDER-HIP)*math.sin(rx),hz+(SHOULDER-HIP)*math.cos(rx))
        grip=(shoulder[0]+gx,shoulder[1]+gz)
        axis=(math.cos(math.radians(angle)),math.sin(math.radians(angle)))
        rotations={"root":0.0,"torso":lean,"head":.48*lean+2*math.sin(frame*.053),
                   "cape":lean+cape,"ribbon":lean+cape+8*math.sin(.087*frame),"prop":-angle}
        for side,foot,g in [("far",(fx,fz),-.16),("near",(nx,nz),.025)]:
            wrist=(grip[0]+g*axis[0],grip[1]+g*axis[1])
            u,l=ik(shoulder,wrist,ARM,FOREARM,-1)
            rotations["arm."+side],rotations["forearm."+side]=-90-u,-90-l
            u,l=ik((hx,hz),foot,THIGH,SHIN,1)
            rotations["thigh."+side],rotations["shin."+side]=-90-u,-90-l
            rotations["foot."+side]=max(0,foot[1]-.095)*20
        for name,degrees in rotations.items():
            pb=rig.pose.bones[name]
            parent=rotations[pb.parent.name] if pb.parent else 0
            basis=pb.bone.matrix_local.to_quaternion()
            q=basis.inverted() @ Quaternion((0,1,0),math.radians(degrees-parent)) @ basis
            if name in previous:
                q.make_compatible(previous[name])
            previous[name]=q.copy()
            pb.rotation_mode="QUATERNION"
            pb.rotation_quaternion=q
            pb.keyframe_insert("rotation_quaternion",frame=frame,group=name)
        for name,dx,dz in [("root",hx,hz-HIP),("prop",grip[0],grip[1]-BLADE_Z)]:
            pb=rig.pose.bones[name]
            pb.location=pb.bone.matrix_local.to_quaternion().inverted() @ Vector((dx,0,dz))
            pb.keyframe_insert("location",frame=frame,group=name)
    return action
