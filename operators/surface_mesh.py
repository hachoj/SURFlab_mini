import bpy
import bmesh
from .polyhedral_splines import PolyhedralSplines


class SurfaceMesh(bpy.types.Operator):
    """fake net operator"""
    bl_label = "Surface Mesh"
    bl_idname = "object.create_surface_mesh"
    bl_description = "Creates a surface mesh"
    control_mesh_obj = None
    control_mesh = None
    patch_to_corners = None
    vertices = []


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
            SurfaceMesh.vertices = PolyhedralSplines.get_verts()
            return True
        return False

    def distance(p1, p2):
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2) ** 0.5

    # Harry addition to test modifying mesh
    def mesh_modification():
        bm = bmesh.new()
        bm.from_mesh(SurfaceMesh.control_mesh)
        bm.verts.ensure_lookup_table()
        # testing two ways to select a vertex
        # ok editing a vert worked
        # -----------------------------------
        patch_to_corners = SurfaceMesh.patch_to_corners
        patch_index = input("Enter patch index: ")
        patch_index = str(patch_index) if len(str(patch_index)) == 3 else "0" + str(patch_index)
        patch_name = "SurfPatch." + patch_index
        # just taking the first cube coords for ease
        cube_coord = patch_to_corners[patch_name][1][0]
        # finding the closest vert to the cube coord
        closest_vert_index = 0
        min_distance = float('inf')
        for i, vert in enumerate(bm.verts):
            dist = SurfaceMesh.distance(vert.co, cube_coord)
            if dist < min_distance:
                min_distance = dist
                closest_vert_index = i
        bm.verts[closest_vert_index].co.x += 1
        bm.verts[closest_vert_index].co.y += 1
        bm.verts[closest_vert_index].co.z += 1
        bm.to_mesh(SurfaceMesh.control_mesh)
        SurfaceMesh.control_mesh.update()
        # -----------------------------------

    def execute(self, context):
        # Perform some action
        obj = context.active_object
        self.report({'INFO'}, "Button Pressed")
        print("Button Pressed")
        print("Polyhedral Splines Finished:", PolyhedralSplines.polyhedral_splines_finished)
        if PolyhedralSplines.polyhedral_splines_finished:
            # fixed
            SurfaceMesh.mesh_modification()
            # PolyhedralSplines.coverage_test()
        # self.create_wireframe_mesh(context)
        return {'FINISHED'}

    @staticmethod
    def create_wireframe_mesh(context):
        mesh = bpy.data.meshes.new(name="WireframeMesh")

        # Create vertices and edges for the wireframe
        vertices = PolyhedralSplines.wireframe_vertices
        print(vertices)
        #edges = [(i, (i + 1) % len(vertices)) for i in range(len(vertices))]  # Create edges between consecutive vertices
        vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]  # Replace with your vertices
        edges = [(0, 1), (1, 2), (2, 0)]  # Replace with your edges


        # Create mesh data
        mesh.from_pydata(vertices, edges, [])

        # Update mesh
        mesh.update()

        # Create a new object with the mesh data
        obj = bpy.data.objects.new(name="WireframeObject", data=mesh)

        # Link object to the current collection
        bpy.context.collection.objects.link(obj)

        # Set the object as active and select it
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        obj.display_type = 'WIRE'

        # Optionally, clear the list after creating the mesh
        # PolyhedralSplines.wireframe_vertices.clear()