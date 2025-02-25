# import bpy
# import bmesh
# from bpy.app.handlers import persistent
# from .polyhedral_splines import PolyhedralSplines

# import numpy as np
# import math
# from mathutils import Vector, Matrix

# class SurfaceMesh(bpy.types.Operator):
#     """surface mesh operator"""
#     bl_label = "Surface Mesh"
#     bl_idname = "object.create_surface_mesh"
#     bl_description = "Creates a surface mesh"
#     control_mesh_name = None
#     control_mesh_obj = None
#     patch_to_corners = None
#     verts = None
#     full_verts = None
#     wireframe_mesh_created = False

#     @classmethod
#     def poll(cls, context):
#         obj = context.active_object
#         return (
#             obj is not None and
#             obj.type == 'MESH' and
#             obj.mode == 'EDIT' and
#             obj.name == "SurfaceMesh" and
#             PolyhedralSplines.polyhedral_splines_finished
#             or
#             obj in context.selected_objects and
#             obj.mode == "OBJECT" and
#             obj.type == "MESH" and
#             PolyhedralSplines.polyhedral_splines_finished
#         )

#     def execute(self, context):
#         obj = context.active_object

#         if PolyhedralSplines.polyhedral_splines_finished:
#             SurfaceMesh.control_mesh_obj = obj
#             SurfaceMesh.control_mesh_name = obj.name
#             SurfaceMesh.patch_to_corners = PolyhedralSplines.patch_to_corners
#             SurfaceMesh.verts = PolyhedralSplines.verts
#             SurfaceMesh.full_verts = PolyhedralSplines.full_verts

#             # Create the surface mesh
#             SurfaceMesh.create_wireframe_mesh(context)
#             self.report({'INFO'}, "Surface mesh created")
#             return {'FINISHED'}
#         else:
#             self.report({'INFO'}, "Surface mesh already created")
#             return {'CANCELLED'}

#     @staticmethod
#     def create_wireframe_mesh(context):
#         """Creates the wireframe mesh that users will interact with."""
#         mesh = bpy.data.meshes.new(name="WireframeMesh")
#         vert_dict = {}
#         verts = []
#         edges = set()

#         # Create a rotation matrix to fix the orientation of the vertices
#         # The vertices are rotated 90 degrees around the x-axis 
#         rotation_matrix = Matrix.Rotation(math.radians(90), 4, 'X')

#         def add_vertex(vertex):
#             vertex_tuple = tuple(vertex)
#             if vertex_tuple not in vert_dict:
#                 vert_dict[vertex_tuple] = len(verts)
#                 verts.append(vertex_tuple)
#             return vert_dict[vertex_tuple]

#         face_verts = []
#         for face, face_type, parent in SurfaceMesh.full_verts:
#             if face_type == "Regular":
#                 for vert in face:
#                     # fixing the rotation of the vertices
#                     rotated_vertex = rotation_matrix @ Vector(vert)
#                     vert_index = add_vertex(rotated_vertex)
#                     face_verts.append(vert_index)
#                 if len(face_verts) == 4:
#                     edges.update({
#                         # (face_verts[0], face_verts[1]),
#                         # (face_verts[0], face_verts[2]),
#                         # (face_verts[1], face_verts[3]),
#                         # (face_verts[2], face_verts[3])
#                         (face_verts[0], face_verts[1]),
#                         (face_verts[1], face_verts[3]),
#                         (face_verts[3], face_verts[2]),
#                         (face_verts[2], face_verts[0])
#                     })
#                     face_verts = []

#         # Create the mesh with the vertices and edges
#         mesh.from_pydata(verts, list(edges), [])
#         mesh.update()

#         # Create integer attributes on the mesh
#         for i in range(4):
#             if f"cp_idx_{i}" not in mesh.attributes:
#                 mesh.attributes.new(f"cp_idx_{i}", type='INT', domain='POINT')

#         # Now we handle the control points using BMesh
#         sbm = bmesh.new()
#         sbm.from_mesh(mesh)
#         sbm.verts.ensure_lookup_table()

#         # Get the interger layers
#         cp_idx_layers = [sbm.verts.layers.int.get(f"cp_idx_{i}") for i in range(4)]
#         if None in cp_idx_layers:
#             cp_idx_layers = [sbm.verts.layers.int.new(f"cp_idx_{i}") for i in range(4)]

#         # Set control mesh from the current object
#         SurfaceMesh.control_mesh_name = SurfaceMesh.control_mesh_obj.name
#         control_mesh = bpy.data.objects[SurfaceMesh.control_mesh_name]

#         bpy.ops.object.mode_set(mode='OBJECT')

#         cbm = bmesh.new()
#         cbm.from_mesh(control_mesh.data)
#         cbm.verts.ensure_lookup_table()

#         # for mapping purposes, rotate the control coords
#         control_coords = [rotation_matrix @ cvert.co.copy() for cvert in cbm.verts]

#         for svert in sbm.verts:
#             svert_co = svert.co.copy() # pre rotated

#             distances = [(i, (svert_co - c_co).length) for i, c_co in enumerate(control_coords)]
#             distances.sort(key=lambda x: x[1])
#             closest_indeces = [i for i, _ in distances[:4]]

#             # Store the indeces
#             for i, cp_idx in enumerate(closest_indeces):
#                 svert[cp_idx_layers[i]] = cp_idx

#             # closest_vert_indices = []
#             # sverttemp = Vector((svert.co[0], svert.co[2], -svert.co[1]))  # Undo rotation

#             # for _ in range(4):
#             #     min_distance = float('inf')
#             #     closest_vert_index = None
#             #     for i, cvert in enumerate(cbm.verts):
#             #         if i not in closest_vert_indices:
#             #             dist = (cvert.co - sverttemp).length
#             #             if dist < min_distance:
#             #                 min_distance = dist
#             #                 closest_vert_index = i
#             #     if closest_vert_index is not None:
#             #         closest_vert_indices.append(closest_vert_index)

#             # for i, cp_idx in enumerate(closest_vert_indices):
#             #     svert[cp_idx_layers[i]] = cp_idx

#         # Apply the BMesh changes to the surface mesh
#         sbm.to_mesh(mesh)
#         mesh.update()
#         sbm.free()
#         cbm.free()

#         # Create and link the wireframe mesh object
#         SurfaceMesh._link_mesh_to_scene(context, mesh)

#     @staticmethod
#     def _link_mesh_to_scene(context, mesh):
#         """Link the created wireframe mesh to the current scene."""
#         obj = bpy.data.objects.new(name="SurfaceMesh", object_data=mesh)
#         context.collection.objects.link(obj)
#         context.view_layer.objects.active = obj
#         obj.select_set(True)
#         obj.display_type = 'WIRE'
#         SurfaceMesh.wireframe_mesh_created = True

# class SurfaceMeshUpdater:
#     prev_vertex_positions = {}
#     is_processing = False

#     @staticmethod
#     @persistent
#     def mode_change_handler(scene):
#         if SurfaceMeshUpdater.is_processing:
#             # prevent re-entrant calls
#             return 
        
#         obj = bpy.context.active_object
#         if obj and obj.type == 'MESH' and obj.name == 'SurfaceMesh':
#             mode = obj.mode
#             if mode == 'EDIT' and not SurfaceMeshUpdater.prev_vertex_positions:  # Corrected here
#                 # Entering Edit Mode: Store the initial vertex positions
#                 bm = bmesh.from_edit_mesh(obj.data)
#                 bm.verts.ensure_lookup_table()
#                 obj_matrix = obj.matrix_world
#                 SurfaceMeshUpdater.prev_vertex_positions = {v.index: obj_matrix @ v.co.copy() for v in bm.verts}  # Corrected here
#             elif mode == 'OBJECT' and SurfaceMeshUpdater.prev_vertex_positions:  # Corrected here
#                 # Exiting Edit Mode: Apply Deltas
#                 print("Getting Here at ALL?")
#                 SurfaceMeshUpdater.is_processing = True
#                 try: 
#                     mesh = obj.data
#                     bm = bmesh.new()
#                     bm.from_mesh(mesh)
#                     bm.verts.ensure_lookup_table()
#                     obj_matrix = obj.matrix_world
#                     moved_verts = []
#                     for v in bm.verts:
#                         prev_pos = SurfaceMeshUpdater.prev_vertex_positions.get(v.index)  # Corrected here
#                         current_pos = obj_matrix @ v.co.copy()
#                         print(f"Curr: {current_pos}")
#                         print(f"Prev: {prev_pos}")
#                         if prev_pos and (current_pos - prev_pos).length > 1e-6:
#                             delta = current_pos - prev_pos
                            
#                             # DEBUG
#                             print(f"Surface Vertex {v.index} moved by {delta}")

#                             moved_verts.append((v.index, delta))
#                     if moved_verts:
#                         SurfaceMeshUpdater.apply_deltas_to_control_mesh(obj, moved_verts)
#                     SurfaceMeshUpdater.prev_vertex_positions = {}  # Corrected here
#                     bm.free()
#                 finally:
#                     SurfaceMeshUpdater.is_processing = False

#     @staticmethod
#     def apply_deltas_to_control_mesh(surface_obj, moved_verts):
#         """Apply the deltas from the surface mesh to the control mesh."""
#         cp_idx_layers = [surface_obj.data.attributes.get(f"cp_idx_{i}") for i in range(4)]
#         if None in cp_idx_layers:
#             print("Error: Control point index layers not found")
#             return
        
#         control_mesh_obj = bpy.data.objects.get(SurfaceMesh.control_mesh_name)
#         if not control_mesh_obj:
#             print("Error: Control mesh not found")
#             return

#         control_mesh = control_mesh_obj.data
#         bm_control = bmesh.new()
#         bm_control.from_mesh(control_mesh_obj.data)
#         bm_control.verts.ensure_lookup_table()

#         control_vertex_deltas = {}

#         control_matrix_inv = control_mesh_obj.matrix_world.inverted()

#         for vert_idx, delta in moved_verts:
#             cp_indices = []
#             for attr in cp_idx_layers:
#                 cp_idx = attr.data[vert_idx].value
#                 cp_indices.append(cp_idx)

#             delta_local = control_matrix_inv.to_3x3() @ delta 

#             for cp_idx in cp_indices:

#                 if cp_idx not in control_vertex_deltas:
#                     control_vertex_deltas[cp_idx] = delta_local.copy()
#                 else:
#                     control_vertex_deltas[cp_idx] += delta_local 
        
#         for cp_dix, delta in control_vertex_deltas.items():
#             control_vert = bm_control.verts[cp_dix]
#             before_pos = control_vert.co.copy()
#             control_vert.co += delta
#             after_pos = control_vert.co.copy()
 
#         bm_control.to_mesh(control_mesh_obj.data)
#         control_mesh_obj.data.update()
#         bm_control.free()

# # Register the handler if it's not already registered
# if SurfaceMeshUpdater.mode_change_handler not in bpy.app.handlers.depsgraph_update_post:
#     bpy.app.handlers.depsgraph_update_post.append(SurfaceMeshUpdater.mode_change_handler)