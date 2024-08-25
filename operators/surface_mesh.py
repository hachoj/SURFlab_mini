import bpy
import bmesh
from bpy.app.handlers import persistent
from .polyhedral_splines import PolyhedralSplines

import numpy as np
from mathutils import Vector

class PersistentState():
    previous_mesh = None
    previous_mesh_verts = None
    previous_vertex_idx = None
    previous_location = None
    delta_location = (0, 0, 0)
    # delta_total = None
# persitent_data = {}

class SurfaceMesh(bpy.types.Operator):
    """fake net operator"""
    bl_label = "Surface Mesh"
    bl_idname = "object.create_surface_mesh"
    bl_description = "Creates a surface mesh"
    control_mesh_name = None
    control_mesh_obj = None
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
    def mesh_modification(vertex_index, delta_location):
        control_mesh = bpy.data.objects[SurfaceMesh.control_mesh_name]

        bpy.ops.object.mode_set(mode='OBJECT')

        bm = bmesh.new()
        bm.from_mesh(control_mesh.data)
        bm.verts.ensure_lookup_table()

        # undo the rotation from the original location
        # original_location[1], original_location[2] = original_location[2], -original_location[1]

        print("Before the locations are changed")
        print(bm.verts[vertex_index].co)

        bm.verts[vertex_index].co += delta_location

        print("After the locations are changed")
        print("---------------------------------------------")

        bm.to_mesh(control_mesh.data)
        bm.free()

        control_mesh.data.update()

        bpy.ops.object.mode_set(mode='EDIT')


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
                    # rotated_vertex = np.array([vert[0], vert[1], vert[2]])
                    # rotated_vertex = np.array([rotated_vertex[0], rotated_vertex[2], -rotated_vertex[1]])
                    # Add vertex and get its index
                    # rotated_vertex = np.array([vert[0], -vert[1], -vert[2]])
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

        sbm = bmesh.new()
        sbm.from_mesh(mesh)
        sbm.verts.ensure_lookup_table()
        sbm.faces.ensure_lookup_table()

        # using float_color to store control points because it can store 4 values

        SurfaceMesh.control_mesh_name = SurfaceMesh.control_mesh_obj.name
        # SurfaceMesh.control_mesh_obj.hide_viewport = True

        control_mesh = bpy.data.objects[SurfaceMesh.control_mesh_name]

        bpy.ops.object.mode_set(mode='OBJECT')

        cbm = bmesh.new()
        cbm.from_mesh(control_mesh.data)
        cbm.verts.ensure_lookup_table()

        # undo the rotation from the original location

        control_points_layer = sbm.verts.layers.float_color.new("control_points")
        
        for svert in sbm.verts:   
            closest_vert_indices = []
            # undo rotation from the original location
            sverttemp = Vector((svert.co[0], svert.co[2], -svert.co[1]))
            # sverttemp = Vector((svert.co[0], svert.co[1], svert.co[2]))
            for _ in range(4):
                min_distance = float('inf')
                closest_vert_index = None
                for i, cvert in enumerate(cbm.verts):
                    if i not in closest_vert_indices:
                        dist = (cvert.co - sverttemp).length
                        if dist < min_distance:
                            min_distance = dist
                            closest_vert_index = i
                if closest_vert_index is not None:
                    closest_vert_indices.append(closest_vert_index)
            svert[control_points_layer] = [closest_vert_index for closest_vert_index in closest_vert_indices]


        cmesh = bpy.context.active_object.data
        cbm.to_mesh(cmesh)
        cbm.free()

        # Create a new object with the mesh data
        sbm.to_mesh(mesh)
        sbm.free()
        obj = bpy.data.objects.new(name="SurfaceMesh", object_data=mesh)

        # Link object to the current collection
        bpy.context.collection.objects.link(obj)


        # Set the object as active and select it
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        obj.display_type = 'WIRE'
        SurfaceMesh.wireframe_mesh_created = True
        # Optionally, clear the list after creating the mesh
        # PolyhedralSplines.wireframe_vertices.clear()
        # SurfaceMesh.mesh_modification(300, Vector((2, 2, 2)))

# bpy.types.WindowManager.previous_vertex_idx = bpy.props.IntProperty(name="Previous Vertex Index", default=-1)
persistent_data = {"prev_idx":-1, "prev_loc": None, "delta_loc": Vector((0, 0, 0,)), "delta_sum": Vector((0, 0, 0)), "suppress_handler": False}

@persistent
def edit_object_change_handler(scene, context):
    if persistent_data["suppress_handler"]:
        return
    obj = bpy.context.active_object
    # wm = bpy.context.window_manager
    # if not hasattr(wm, "previous_vertex_idx"):
    #     wm.previous_vertex_idx = None

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

            control_points_layer = bm.verts.layers.float_color["control_points"]

            for v in bm.verts:
                if v.select:
                    if persistent_data["prev_loc"] is None:
                        persistent_data["prev_loc"] = v.co.copy()
                        persistent_data["prev_idx"] = v.index
                    elif persistent_data["prev_idx"] != v.index:
                        persistent_data["prev_loc"] = v.co.copy()
                        persistent_data["delta_loc"] = Vector((0, 0, 0))
                        persistent_data["prev_idx"] = v.index
                    elif persistent_data["prev_idx"] == v.index:
                        persistent_data["delta_loc"] = SurfaceMesh.delta_location(original_location=persistent_data["prev_loc"], new_location=v.co)
                        persistent_data["prev_loc"] = v.co.copy()
                        persistent_data["prev_idx"] = v.index
                    break
            delta_sum = sum(abs(coord) for coord in persistent_data["delta_loc"])
            if delta_sum != 0:
                persistent_data["delta_sum"] += persistent_data["delta_loc"]
            elif delta_sum == 0 and persistent_data["delta_sum"] != Vector((0, 0, 0)):
                control_points = v[control_points_layer]
                print(f"delta sum (total change being applied): {persistent_data['delta_sum']}")
                for control_point_index in control_points:
                    print(f"control point getting modified: {int(control_point_index)}")
                    persistent_data["suppress_handler"] = True
                    SurfaceMesh.mesh_modification(int(control_point_index), persistent_data["delta_sum"])
                    persistent_data["suppress_handler"] = False
                persistent_data["delta_loc"] = Vector((0, 0, 0))
                persistent_data["delta_sum"] = Vector((0, 0, 0))

bpy.app.handlers.depsgraph_update_post.append(edit_object_change_handler)