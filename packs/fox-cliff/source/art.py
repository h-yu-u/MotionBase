"""Small cut-paper mesh primitives shared by the bundled demo assets."""
import math
import bpy


class Artwork:
    def __init__(self, collection, rig=None):
        self.collection = collection
        self.rig = rig
        self.materials = {}

    def material(self, role, flat):
        key = role,flat
        if key not in self.materials:
            mat = bpy.data.materials.new(role)
            mat["motionbase_role"], mat["motionbase_flat"] = role,flat
            self.materials[key] = mat
        return self.materials[key]

    def shape(self, name, points, y, role, bone=None, depth=.012, flat=None):
        if flat is None:
            flat = self.rig is None
        points = list(points)
        area = sum(x*v-u*z for (x,z),(u,v) in zip(points,points[1:]+points[:1]))
        if area < 0:
            points.reverse()
        n = len(points)
        verts = [(x,y,z) for x,z in points]+[(x,y+depth,z) for x,z in points]
        faces = [tuple(range(n)),tuple(reversed(range(n,2*n)))]
        faces += [(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts,[],faces)
        mesh.update()
        obj = bpy.data.objects.new(name,mesh)
        self.collection.objects.link(obj)
        mesh.materials.append(self.material(role,flat))
        if bone:
            obj.parent = self.rig
            obj.vertex_groups.new(name=bone).add(range(2*n),1,"REPLACE")
            obj.modifiers.new("Character rig","ARMATURE").object = self.rig
        return obj

    def oval(self,name,x,z,rx,rz,y,role,bone=None,steps=32):
        return self.shape(name,[(x+rx*math.cos(i*math.tau/steps),z+rz*math.sin(i*math.tau/steps))
                                for i in range(steps)],y,role,bone)
