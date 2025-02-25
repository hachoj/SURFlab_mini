import bpy
import bmesh
from bpy.app.handlers import persistent
from .polyhedral_splines import PolyhedralSplines
from .polyhedral_splines import update_surface

import numpy as np
import math
from mathutils import Vector, Matrix

#TODO: look at open mesh half edge thing to track iterator through the stuff and stuff

class SurfaceMesh(bpy.types.Operator):
    """Operator to create a surface mesh from the control mesh"""
    bl_label = "Surface Mesh"
    bl_idname = "object.create_surface_mesh"
    bl_description = "Creates a surface mesh"

    # Class variables
    control_mesh_name = None           # Name of the control mesh object
    control_mesh_obj = None            # Reference to the control mesh object
    patch_to_corners = None            # Mapping from patches to corner points
    verts = None                       # List of vertices
    full_verts = None                  # Complete list of vertices with additional information
    wireframe_mesh_created = False     # Flag indicating if the wireframe mesh has been created

    @classmethod
    def poll(cls, context):
        """Determine if the you can make a surface mesh with given conditions"""
        obj = context.active_object
        return (
            obj is not None and
            obj.type == 'MESH' and
            obj.mode == 'EDIT' and
            obj.name == "SurfaceMesh" and
            PolyhedralSplines.polyhedral_splines_finished
            or
            obj in context.selected_objects and
            obj.mode == "OBJECT" and
            obj.type == "MESH" and
            PolyhedralSplines.polyhedral_splines_finished
        )

    def execute(self, context):
        """Execute the operator to create the surface mesh"""
        obj = context.active_object

        if PolyhedralSplines.polyhedral_splines_finished:
            # Store references
            SurfaceMesh.control_mesh_obj = obj
            SurfaceMesh.control_mesh_name = obj.name
            SurfaceMesh.patch_to_corners = PolyhedralSplines.patch_to_corners
            SurfaceMesh.verts = PolyhedralSplines.verts
            SurfaceMesh.full_verts = PolyhedralSplines.full_verts

            # Create the surface mesh
            SurfaceMesh.create_wireframe_mesh(context)
            self.report({'INFO'}, "Surface mesh created")
            return {'FINISHED'}
        else:
            self.report({'INFO'}, "Surface mesh already created")
            return {'CANCELLED'}
    
    # @staticmethod
    # def create_wireframe_mesh(context):
    #     """Creates the wireframe mesh that users will interact with."""
    #     # Create new mesh
    #     mesh = bpy.data.meshes.new(name="WireframeMesh")
    #     vert_dict = {}
    #     verts = []
    #     edges = set()

    #     # Create a rotation matrix to fix the orientation
    #     rotation_matrix = Matrix.Rotation(math.radians(90), 4, 'X')

    #     def add_vertex(vertex):
    #         """Helper function to add a vertex to the mesh."""
    #         vertex_tuple = tuple(vertex)
    #         if vertex_tuple not in vert_dict:
    #             vert_dict[vertex_tuple] = len(verts)
    #             verts.append(vertex_tuple)
    #         return vert_dict[vertex_tuple]

    #     # Process all patches
    #     for face, face_type, parent in SurfaceMesh.full_verts:
    #         face_verts = []
    #         for vert in face:
    #             # Rotate the vertices
    #             rotated_vertex = rotation_matrix @ Vector(vert)
    #             vert_index = add_vertex(rotated_vertex)
    #             face_verts.append(vert_index)

    #         # Create edges based on the face structure
    #         num_verts = len(face_verts)
    #         if num_verts >= 3:
    #             # Create edges for n-gon faces
    #             for i in range(num_verts):
    #                 edge = (face_verts[i], face_verts[(i + 1) % num_verts])
    #                 edges.add(edge)

    #     # Create the mesh with the vertices and edges
    #     mesh.from_pydata(verts, list(edges), [])
    #     mesh.update()

    #     # Create attribute to hold the nearby control points
    #     cp_idx_layers = []
    #     for i in range(4):
    #         layer_name = f"cp_idx_{i}"
    #         if layer_name not in mesh.attributes:
    #             mesh.attributes.new(name=layer_name, type='INT', domain='POINT')
    #         cp_idx_layers.append(mesh.attributes[layer_name])

    #     # Get control mesh object
    #     SurfaceMesh.control_mesh_name = SurfaceMesh.control_mesh_obj.name
    #     control_mesh = bpy.data.objects[SurfaceMesh.control_mesh_name]

    #     bpy.ops.object.mode_set(mode='OBJECT')

    #     # Create a BMesh from the control mesh
    #     cbm = bmesh.new()
    #     cbm.from_mesh(control_mesh.data)
    #     cbm.verts.ensure_lookup_table()

    #     # Get the control points in world space and rotate them
    #     control_coords = [rotation_matrix @ cvert.co.copy() for cvert in cbm.verts]

    #     # Assign control point indices to each vertex in the surface mesh
    #     for svert_idx, svert_co in enumerate(mesh.vertices):
    #         svert_co = svert_co.co.copy()  # Pre-rotated

    #         # Find the closest control points
    #         distances = [(i, (svert_co - c_co).length) for i, c_co in enumerate(control_coords)]
    #         distances.sort(key=lambda x: x[1])
    #         closest_indices = [i for i, _ in distances[:4]]

    #         # Store the indices
    #         for i, cp_idx in enumerate(closest_indices):
    #             mesh.attributes[f"cp_idx_{i}"].data[svert_idx].value = cp_idx

    #     cbm.free()

    #     # Create and link the wireframe mesh object
    #     SurfaceMesh._link_mesh_to_scene(context, mesh)

    @staticmethod
    def create_wireframe_mesh(context):
        """Creates the wireframe mesh that users will interact with."""
        # Create new mesh
        mesh = bpy.data.meshes.new(name="WireframeMesh")
        vert_dict = {}
        verts = []
        edges = set()

        # Create a rotation matrix to fix the weird blender rotation with new mesh
        rotation_matrix = Matrix.Rotation(math.radians(90), 4, 'X')

        def add_vertex(vertex):
            """Helper function to add a vertex to the mesh."""
            vertex_tuple = tuple(vertex)
            if vertex_tuple not in vert_dict:
                vert_dict[vertex_tuple] = len(verts)
                verts.append(vertex_tuple)
            return vert_dict[vertex_tuple]

        face_verts = []
        for face, face_type, parent in SurfaceMesh.full_verts:
            if face_type == "Regular":
                for vert in face:
                    # Fixing the rotation of the vertices
                    rotated_vertex = rotation_matrix @ Vector(vert)
                    vert_index = add_vertex(rotated_vertex)
                    face_verts.append(vert_index)
                if len(face_verts) == 4:
                    edges.update({
                        (face_verts[0], face_verts[1]),
                        (face_verts[1], face_verts[3]),
                        (face_verts[3], face_verts[2]),
                        (face_verts[2], face_verts[0])
                    })
                    face_verts = []

        # Create the mesh with the vertices and edges
        mesh.from_pydata(verts, list(edges), [])
        mesh.update()

        # Create attribute to hold the near by control points
        cp_idx_layers = []
        for i in range(4):
            layer_name = f"cp_idx_{i}"
            if layer_name not in mesh.attributes:
                mesh.attributes.new(name=layer_name, type='INT', domain='POINT')
            cp_idx_layers.append(mesh.attributes[layer_name])

        # Get control mesh object
        SurfaceMesh.control_mesh_name = SurfaceMesh.control_mesh_obj.name
        control_mesh = bpy.data.objects[SurfaceMesh.control_mesh_name]

        bpy.ops.object.mode_set(mode='OBJECT')

        # Create a BMesh from the control mesh
        cbm = bmesh.new()
        cbm.from_mesh(control_mesh.data)
        cbm.verts.ensure_lookup_table()

        # Get the control points in world space and rotate them
        control_coords = [rotation_matrix @ cvert.co.copy() for cvert in cbm.verts]

        for svert_idx, svert_co in enumerate(mesh.vertices):
            svert_co = svert_co.co.copy() # pre rotated

            # Find the closest control points
            distances = [(i, (svert_co - c_co).length) for i, c_co in enumerate(control_coords)]
            distances.sort(key=lambda x: x[1])
            closest_indeces = [i for i, _ in distances[:4]]

            # Store the indeces
            for i, cp_idx in enumerate(closest_indeces):
                mesh.attributes[f"cp_idx_{i}"].data[svert_idx].value = cp_idx

        cbm.free()
        
        # Create and link the wireframe mesh object
        SurfaceMesh._link_mesh_to_scene(context, mesh)

    @staticmethod
    def _link_mesh_to_scene(context, mesh):
        """Link the created wireframe mesh to the current scene."""
        obj = bpy.data.objects.new(name="SurfaceMesh", object_data=mesh)
        context.collection.objects.link(obj)
        context.view_layer.objects.active = obj
        obj.select_set(True)
        obj.display_type = 'WIRE'
        SurfaceMesh.wireframe_mesh_created = True

class SurfaceMeshUpdaterModal(bpy.types.Operator):
    """Modal operator to update control mesh in real-time"""
    bl_idname = "object.surface_mesh_updater_modal"
    bl_label = "Surface Mesh Updater Modal"

    _timer = None
    _surface_obj = None
    _control_obj = None
    _prev_positions = {}

    def execute(self, context):
        """Initialize the modal operator"""
        print(f"Surface Mesh Updater Modal Started")
        self._surface_obj = bpy.data.objects.get("SurfaceMesh")
        if not self._surface_obj:
            print("SurfaceMesh object not found")
            return {'CANCELLED'}

        self._control_obj = bpy.data.objects.get(SurfaceMesh.control_mesh_name)
        if not self._control_obj:
            self.reoprt({'ERROR'}, "Control mesh not found")
            print("Control mesh not found")
            return {'CANCELLED'}

        # Store initial positions
        bm = bmesh.from_edit_mesh(self._surface_obj.data)
        bm.verts.ensure_lookup_table()
        self._prev_positions = {v.index: v.co.copy() for v in bm.verts}

        # Add a timer (think of like tick rate in a game loop so we have 100 ticks per second)
        wm = context.window_manager
        self._timer = wm.event_timer_add((1/60), window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Handles modal events"""
        if event.type == 'TIMER':
            # Check if still in Edit Mode
            if self._surface_obj.mode != 'EDIT':
                self.cancel(context)
                return {'CANCELLED'}

            # Access the BMesh in Edit Mode
            bm = bmesh.from_edit_mesh(self._surface_obj.data)
            bm.verts.ensure_lookup_table()
            current_positions = {v.index: v.co.copy() for v in bm.verts}

            moved_verts = []
            for idx, curr_pos in current_positions.items():
                prev_pos = self._prev_positions.get(idx)
                if prev_pos and (curr_pos - prev_pos).length > 1e-6:
                    delta = curr_pos - prev_pos
                    moved_verts.append((idx, delta))
                    self._prev_positions[idx] = curr_pos.copy()

            if moved_verts:
                # Apply deltas to control mesh
                self.apply_deltas_to_control_mesh(moved_verts)

        return {'PASS_THROUGH'}

    def apply_deltas_to_control_mesh(self, moved_verts):
        """Apply surface mesh vertex deltas to its related control mesh vertices"""
        surface_obj = self._surface_obj

        # Get the BMesh in Edit Mode
        bm = bmesh.from_edit_mesh(surface_obj.data)
        bm.verts.ensure_lookup_table()

        # Get the integer layers (custom attributes) from the BMesh
        cp_idx_layers = []
        for i in range(4):
            layer_name = f"cp_idx_{i}"
            layer = bm.verts.layers.int.get(layer_name)
            if layer is None:
                layer = bm.verts.layers.int.new(layer_name)
                attr_data = surface_obj.data.attributes[layer_name].data
                for j, vert in enumerate(bm.verts):
                    vert[layer] = attr_data[j].value
            cp_idx_layers.append(layer)

        control_mesh_obj = self._control_obj
        if not control_mesh_obj:
            print("Error: Control mesh not found")
            return

        control_mesh = control_mesh_obj.data
        bm_control = bmesh.new()
        bm_control.from_mesh(control_mesh)
        bm_control.verts.ensure_lookup_table()

        control_vertex_deltas = {}
        updated_control_verts = set()

        control_matrix_inv = control_mesh_obj.matrix_world.inverted()

        # For each moved vertex in the surface mesh, apply the delta to the control mesh
        for bm_vert_idx, delta in moved_verts:
            bm_vert = bm.verts[bm_vert_idx]

            # Get control mesh vertices from the custom layer
            cp_indices = []
            for layer in cp_idx_layers:
                cp_idx = bm_vert[layer]
                cp_indices.append(cp_idx)

            # Apply the delta in local space
            delta_local = control_matrix_inv.to_3x3() @ delta

            # Accumulate the delta for each control vertex
            for cp_idx in cp_indices:
                updated_control_verts.add(cp_idx)
                if cp_idx not in control_vertex_deltas:
                    control_vertex_deltas[cp_idx] = delta_local.copy()
                else:
                    control_vertex_deltas[cp_idx] += delta_local

        # Apply the accumulated deltas to the control mesh
        for cp_idx, delta in control_vertex_deltas.items():
            control_vert = bm_control.verts[cp_idx]
            control_vert.co += delta

        # Update the control mesh
        bm_control.to_mesh(control_mesh)
        control_mesh.update()
        bm_control.free()

        # After updating the control mesh, trigger spline reevaluation for updated control vertices
        self.update_spline_surface(updated_control_verts)

    def update_spline_surface(self, updated_control_verts):
        """Update the spline surface to reflect changes in the control mesh."""
        control_mesh_obj = self._control_obj

        # Ensure the control mesh object exists
        if not control_mesh_obj:
            print("Error: Control mesh not found")
            return

        # Call the update_surface function with the updated control vertices
        update_surface(bpy.context, control_mesh_obj, updated_control_verts)

    def cancel(self, context):
        """Cancel the modal operator"""
        print(f"Surface Mesh Updater Modal Cancelled")
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
        return {'CANCELLED'}

class StartSurfaceMeshUpdater(bpy.types.Operator):
    """Start the Surface Mesh Updater Modal"""
    bl_idname = "object.start_surface_mesh_updater"
    bl_label = "Start Surface Mesh Updater"
    bl_description = "Starts the updater to synchronize the surface mesh with the control mesh in real-time"

    @classmethod
    def poll(cls, context):
        """Make sure the operator can be run"""
        obj = context.active_object
        return (
            obj is not None and
            obj.type == 'MESH' and
            obj.mode == 'EDIT' and
            obj.name == "SurfaceMesh" and
            PolyhedralSplines.polyhedral_splines_finished and
            SurfaceMesh.wireframe_mesh_created
        )

    def execute(self, context):
        """Start the modal operator"""
        bpy.ops.object.surface_mesh_updater_modal()
        return {'FINISHED'}