import bpy
import bmesh
from bpy.app.handlers import persistent
from .polyhedral_splines import PolyhedralSplines


class SurfaceMesh(bpy.types.Operator):
    """fake net operator"""
    bl_label = "Surface Mesh"
    bl_idname = "object.create_surface_mesh"
    bl_description = "Creates a surface mesh"
    control_mesh_obj = None
    control_mesh = None
    patch_to_corners = None
    verts = None
    full_verts = None
    wireframe_mesh_created = False


    # poll function makes it so that you cannot select button function unless certain requirements are met
    # such as having an object selected
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        selected = context.selected_objects

        if obj in selected and obj.mode == "OBJECT" and obj.type == "MESH" and PolyhedralSplines.polyhedral_splines_finished:
            SurfaceMesh.control_mesh_obj = obj
            SurfaceMesh.control_mesh = obj.data
            SurfaceMesh.patch_to_corners = PolyhedralSplines.patch_to_corners
            SurfaceMesh.verts = PolyhedralSplines.verts
            SurfaceMesh.full_verts = PolyhedralSplines.full_verts
            return True
        return False

    def distance(p1, p2):
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2) ** 0.5
    
    def delta_location(original_location, new_location):
        return new_location - original_location

    # Harry addition to test modifying mesh
    def mesh_modification(original_location, delta_location):
        bm = bmesh.new()
        bm.from_mesh(SurfaceMesh.control_mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()



        closest_vert_indices = []
        min_distance = float('inf')
        while len(closest_vert_indices) < 4:
            for i, vert in enumerate(bm.verts):
                dist = SurfaceMesh.distance(vert.co, original_location)
                if dist < min_distance and i not in closest_vert_indices:
                    min_distance = dist
                    closest_vert_index = i
            closest_vert_indices.append(closest_vert_index)
            min_distance = float('inf')
        for i in closest_vert_indices:
            bm.verts[i].co += delta_location
        # to mesh isn't working because
        # SurfaceMesh.control_mesh is in edit mode
        bpy.context.view_layer.objects.active = SurfaceMesh.control_mesh_obj
        bpy.ops.object.mode_set(mode='OBJECT')
        bm.to_mesh(SurfaceMesh.control_mesh)
        SurfaceMesh.control_mesh.update()
        bpy.ops.object.mode_set(mode='EDIT')
        # -----------------------------------

    def execute(self, context):
        # Perform some action
        obj = context.active_object
        self.report({'INFO'}, "Button Pressed")
        print("Button Pressed")
        print("Polyhedral Splines Finished:", PolyhedralSplines.polyhedral_splines_finished)
        if PolyhedralSplines.polyhedral_splines_finished:
            # fixed
            # SurfaceMesh.mesh_modification()
            # PolyhedralSplines.coverage_test()
            self.create_wireframe_mesh(context)
        return {'FINISHED'}

    @staticmethod
    def create_wireframe_mesh(context):
        import numpy as np
        mesh = bpy.data.meshes.new(name="WireframeMesh")

        # Dictionary to store unique vertices
        vert_dict = {}
        verts = []
        edges = set()

        # Function to add a vertex and return its index
        def add_vertex(vertex):
            vertex_tuple = tuple(vertex)
            if vertex_tuple not in vert_dict:
                vert_dict[vertex_tuple] = len(verts)
                verts.append(vertex_tuple)
            return vert_dict[vertex_tuple]

        # Process regular faces first
        face_verts = []
        for face, face_type, parent in SurfaceMesh.full_verts:
            if face_type == "Regular":
                # Rotate vertex: [x, y, z] -> [x, -z, y]
                for vert in face:
                    rotated_vertex = np.array([vert[0], -vert[2], vert[1]])
                    # Add vertex and get its index
                    vert_index = add_vertex(rotated_vertex)
                    face_verts.append(vert_index)
                
                # If we have collected 4 vertices for a face
                if len(face_verts) == 4:
                    # Add edges for the face
                    edges.add((face_verts[0], face_verts[1]))
                    edges.add((face_verts[0], face_verts[2]))
                    edges.add((face_verts[1], face_verts[3]))
                    edges.add((face_verts[2], face_verts[3]))
                    # Reset face_verts for the next face
                    face_verts = [] 
        
        edges_list = list(edges)

        # Create mesh data
        mesh.from_pydata(verts, edges_list, [])

        # Update mesh
        mesh.update()

        # Create a new object with the mesh data
        obj = bpy.data.objects.new(name="SurfaceMesh", object_data=mesh)

        # Link object to the current collection
        bpy.context.collection.objects.link(obj)

        SurfaceMesh.control_mesh_obj.hide_viewport = True

        # Set the object as active and select it
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        obj.display_type = 'WIRE'
        SurfaceMesh.wireframe_mesh_created = True
        # Optionally, clear the list after creating the mesh
        # PolyhedralSplines.wireframe_vertices.clear()

class PersistentState:
    previous_vertex_idx = None
    previous_location = None
    delta_location = (0, 0, 0)
    delta_total = None

ps = PersistentState()

@persistent
def edit_object_change_handler(scene, context):
    obj = bpy.context.active_object

    if scene.previous_object:
        prev_obj = scene.previous_object
    else:
        prev_obj = None

    # Update the previously selected object
    scene.previous_object = obj

    if obj is None:
        return None

    # if obj.mode == 'OBJECT' and Mode.prev == 'EDIT' and obj.type == 'MESH':
    if bpy.context.scene.polyhedral_splines_finished and SurfaceMesh.wireframe_mesh_created and obj.type == 'MESH' and obj.name == "SurfaceMesh":
        if obj.mode == 'EDIT':
            surface_mesh_obj = bpy.context.active_object
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            # bm.select_set(False)
            for v in bm.verts:
                if v.select:
                    if ps.previous_location is None:
                        ps.previous_location = v.co.copy()
                        ps.previous_vertex_idx = v.index
                    elif ps.previous_vertex_idx != v.index:
                        ps.previous_location = v.co.copy()
                        ps.delta_location = (0, 0, 0)
                        ps.previous_vertex_idx = v.index
                    elif ps.previous_vertex_idx == v.index:
                        ps.delta_location = SurfaceMesh.delta_location(original_location=ps.previous_location, new_location=v.co)
                        ps.previous_location = v.co.copy()
                        ps.previous_vertex_idx = v.index
                    break
            delta_sum = 0
            for coord in ps.delta_location:
                delta_sum += abs(coord)
            if delta_sum != 0:
                if ps.delta_total is None:
                    ps.delta_total = ps.delta_location
                else:
                    ps.delta_total += ps.delta_location
            elif delta_sum == 0 and ps.delta_total is not None:
                print("delta total:", ps.delta_total)
                SurfaceMesh.mesh_modification(ps.previous_location, delta_location=ps.delta_total)
                bpy.context.active_object = surface_mesh_obj
                ps.delta_total = None
                ps.previous_location = None
                ps.previous_vertex_idx = None 
                import sys; sys.exit(0)

bpy.app.handlers.depsgraph_update_post.append(edit_object_change_handler)