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
            return True
        return False

    def execute(self, context):
        # Perform some action
        obj = context.active_object
        self.report({'INFO'}, "Button Pressed")
        print("Button Pressed")
        print("Polyhedral Splines Finished:", PolyhedralSplines.polyhedral_splines_finished)
        if PolyhedralSplines.polyhedral_splines_finished:
            # fixed
            PolyhedralSplines.get_verts()
        self.create_wireframe_mesh(context)
        return {'FINISHED'}

    @staticmethod
    def create_wireframe_mesh(context):

        name = "WireframeObject"
        mesh = bpy.data.meshes.new(name=name)

        patch_to_corners = PolyhedralSplines.patch_to_corners

        vertices = []
        edges = []
        vert_index_map = {}

        # Iterate over each patch and its vertices
        for patch_name, (patch_type, corners) in patch_to_corners.items():
            start_index = len(vertices)
            # Add vertices for this patch
            for corner in corners:
                vertices.append(corner)
                vert_index_map[tuple(corner)] = len(vertices) - 1

            # Create edges for this patch
            for i in range(len(corners)):
                for j in range(i + 1, len(corners)):
                    # Add edge only if not already added
                    edge = (start_index + i, start_index + j)
                    if edge not in edges and (edge[1], edge[0]) not in edges:
                        edges.append(edge)

        # Create mesh data
        mesh.from_pydata(vertices, edges, [])
        mesh.update()

        obj = bpy.data.objects.new(name=name, object_data=mesh)

        # Link object to the scene
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        obj.rotation_euler = (0, 0, 0)  # Reset rotation
        bpy.ops.object.transform_apply(rotation=True)

        obj.display_type = 'WIRE'

        # Optionally, clear the list after creating the mesh
        # PolyhedralSplines.wireframe_vertices.clear()
        # PolyhedralSplines.wireframe_edges.clear()

        print("Wireframe mesh created and updated.")
