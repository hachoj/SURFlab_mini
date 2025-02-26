import numpy
import bpy
import bmesh
from bpy.app.handlers import persistent
from .algorithms import Algorithms
from .patch_helper import PatchHelper
from .helper import Helper
from .highlighter import Highlighter
from .patch_tracker import PatchTracker
from .patch import PatchOperator
from .bivariateBBFunctions import bbFunctions
from .moments import Moments

import math

# Debug
import time

tups = []

class PolyhedralSplines(bpy.types.Operator):
    bl_label = "Interactive Modeling"
    bl_idname = "object.polyhedral_splines"
    bl_description = "Generates polyhedral spline mesh. Some mesh configurations are not supported, subdivide the mesh beforehand if this is the case"
    polyhedral_splines_finished = False
    patch_to_corners = {}
    verts = []
    full_verts = []

    def __init__(self):
        print("Start")

    def __del__(self):
        print("End")

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        selected = context.selected_objects

        if obj in selected and obj.mode == "OBJECT" and obj.type == "MESH":
            return True
        return False

    def execute(self, context):
        # # Check if all submeshes are supported by algorithms.
        # # Subdivide the mesh if not.
        # if Highlighter.is_subdivision_required(context):
        #     bpy.ops.object.subdivide_mesh()

        # self.__init_patch_obj__(context)
        # bpy.ops.ui.reloadtranslation()
        # return {'FINISHED'}
        
        # DIFF: Richard had different code here

        # Check if all submeshes are supported by algorithms.
        # Subdivide the mesh if not.
        if Highlighter.is_subdivision_required(context):
            bpy.ops.object.subdivide_mesh()

        self.__init_patch_obj__(context)
        bpy.ops.ui.reloadtranslation()

        bpy.context.scene.polyhedral_splines_finished = True
        PolyhedralSplines.polyhedral_splines_finished = True
        return {'FINISHED'}

    def __init_patch_obj__(self, context):
        context.object.display_type = 'WIRE'

        # control_mesh is the input obj file
        obj = context.view_layer.objects.active
        control_mesh = obj.data

        bm = bmesh.new()
        bm.from_mesh(control_mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table() 

        patchWrappers = PatchHelper.getPatches(bm)
        for patchWrapper in patchWrappers:
            start = time.process_time()

            patchNames = PatchOperator.generate_multiple_patch_obj(patchWrapper.patch)
            PatchTracker.register_multiple_patches(patchWrapper.source, patchWrapper.neighbors, patchNames)
            for patch_name in patchNames:
                bpy.context.scene.objects[patch_name].parent = obj
                # save the corner coordinates of the patch
                # bpy.context.scene.objects[patch_name].corner_coords = patchWrapper.patch.corner_coords
                PolyhedralSplines.patch_to_corners.update({patch_name : (patchWrapper.patch.struct_name, patchWrapper.patch.corner_coords)})

            print("Generate patch obj time usage (sec): ", time.process_time() - start)

        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        Moments.execute(self, context)
        # Finish up, write the bmesh back to the mesh
        if control_mesh.is_editmode:
            bmesh.update_edit_mesh(control_mesh)
        else:
            bm.to_mesh(control_mesh)
            control_mesh.update()
        
        PolyhedralSplines.full_verts, PolyhedralSplines.verts = PolyhedralSplines.get_verts()
        bpy.app.handlers.depsgraph_update_post.append(edit_object_change_handler)
                
    def get_verts(): 
        # if input("full test? (y/n): ") != 'n':
        for parent, val in PolyhedralSplines.patch_to_corners.items():
            # corner[1] is the corner coordinates because
            # corner[0] is the type of contructed patch
            coords = tuple(val[1])
            patch_type = val[0]
            tups.append((coords, patch_type, parent))
        no_dupes_tups = []
        seen_coords = set()
        for coords, patch_type, parent in tups:

            # -----------------------------------
            # this block of code converts the coordinates into a tuple
            # from a numpy array so it can be hashed and checked for duplicates
            check_coords = []
            for cord in coords:
                check_coords.extend(list(cord))
            check_coords = tuple(check_coords)
            # -----------------------------------

            if check_coords not in seen_coords:
                no_dupes_tups.append((coords, patch_type, parent))
                seen_coords.add(check_coords)
            
        # -----------------------------------
        # just to find the amount of control points
        total_control_points = 0
        unique_control_points = 0
        for corners, constructor, parent in tups:
            for corner in corners:
                total_control_points += 1
        for corners, constructor, parent in no_dupes_tups:
            for corner in corners:
                unique_control_points += 1
        print(f"Number of total control points: {total_control_points}")
        print(f"Number of unique control points: {unique_control_points}")
        return tups, no_dupes_tups
            # -----------------------------------
        #     i = 0
        #     for tup in no_dupes_tups:
        #         for corner in tup[0]:
        #             i += 1
        #             if i % 50 == 0:
        #                 print(f"Patch {i}/{unique_control_points}")
        #             PolyhedralSplines.create_control_cube(corner, bpy.context.scene.objects[tup[1]])
        # else:
        #     for key, item in PolyhedralSplines.patch_to_corners.items():
        #         if item != []:
        #             print(key, end=', ')
        #     patch_index = 'y'
        #     while patch_index != 'n':
        #         patch_index = input("Enter patch index: ")
        #         patch_name = "SurfPatch." + str(patch_index)
        #         for corner in PolyhedralSplines.patch_to_corners[patch_name]:
        #             coords = tuple(corner)
        #             create_control_cube(coords, bpy.context.scene.objects[patch_name])

    def control_cube_test(patch_index_str):
        try:
            patch_index = int(patch_index_str)
            patch_name = "SurfPatch." + str(patch_index)
            # patch = bpy.context.scene.objects[patch_name]
            # add_control_cubes(patch) #TODO:
            corners = PolyhedralSplines.patch_to_corners[patch_name]
            if corners != []:
                for corner in corners:
                    coords = tuple(corner)
                    create_control_cube(coords, bpy.context.scene.objects[patch_name])
                print("Control cubes added to patch", patch_index)
            else:
                print("No corner coordinates found for patch", patch_index)
            # print("Control cubes added to patch", patch_index)
        except ValueError:
            print("Invalid patch index. Please enter a number.") 

    def create_control_cube(location, parent_obj=None):
        bpy.ops.mesh.primitive_cube_add(size=0.01, enter_editmode=False, align='WORLD', location=location, scale=(1, 1, 1))
        cube = bpy.context.active_object
        if parent_obj is not None:
            name = "ControlCube." + str(parent_obj.name)
            cube.name = name
            cube.parent = parent_obj 
        else:
            name = "ControlCube."
            cube.name = name

# if previous mode is not edit, switching to edit has no need to update surface
class Mode:
    prev = "OBJECT"


# can't put it in the class
# please see https://developer.blender.org/T73638
prev_mode = 'OBJECT'

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


    if obj.mode == 'EDIT' and Mode.prev == 'EDIT' and obj.type == 'MESH' and obj.name != "SurfaceMesh":
        update_surface(context, obj)


    '''
    if obj.type == 'SURFACE':
        print("You selected a surface")
    if obj.type == 'MESH':
        print("You selected a mesh")
    print(obj.type, "inbetween")
    print("in function")
    '''

    Mode.prev = obj.mode

    return None

def update_surface(context, obj, updated_control_verts=None):
    """Update the spline patches based on the control mesh."""
    # Ensure we're working with the correct object
    if obj is None or obj.type != 'MESH':
        return

    # Create a BMesh from the control mesh data
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    if updated_control_verts is not None:
        # Process only the updated vertices
        vertices_to_process = [bm.verts[i] for i in updated_control_verts]
    else:
        # Get selected vertices
        vertices_to_process = [v for v in bm.verts if v.select]

    # For each vertex to process
    for sv in vertices_to_process:
        # Get central verts and faces
        central_vert_IDs = PatchTracker.get_central_vert_ID(sv)
        vpatch_names = PatchTracker.get_vert_based_patch_obj_name(sv)
        central_face_IDs = PatchTracker.get_central_face_ID(sv)
        fpatch_names = PatchTracker.get_face_based_patch_obj_name(sv)

        # Update vert-based patches
        if central_vert_IDs and vpatch_names:
            for i, vert_id in enumerate(central_vert_IDs):
                vert = bm.verts[vert_id]
                for pc in Algorithms.vert_patch_constructors:
                    if pc.is_same_type(vert):
                        bspline_patches = pc.get_patch(vert)
                        for bc in bspline_patches.bspline_coefs:
                            PatchOperator.update_patch_obj(vpatch_names[i], bc)

        # Update face-based patches
        if central_face_IDs and fpatch_names:
            for i, face_id in enumerate(central_face_IDs):
                face = bm.faces[face_id]
                for pc in Algorithms.face_patch_constructors:
                    if pc.is_same_type(face):
                        bspline_patches = pc.get_patch(face)
                        for bc in bspline_patches.bspline_coefs:
                            PatchOperator.update_patch_obj(fpatch_names[i], bc)

    bm.free()

# def update_surface(context, obj):
#     bm = bmesh.from_edit_mesh(obj.data)
#     selected_verts = [v for v in bm.verts if v.select]

#     for sv in selected_verts:
#         bmesh.update_edit_mesh(obj.data)

#         # Get the centrol vert that needed to be updated
#         central_vert_IDs = PatchTracker.get_central_vert_ID(sv)
#         vpatch_names = PatchTracker.get_vert_based_patch_obj_name(sv)
#         central_face_IDs = PatchTracker.get_central_face_ID(sv)
#         fpatch_names = PatchTracker.get_face_based_patch_obj_name(sv)

#         bm.verts.ensure_lookup_table()
#         bm.faces.ensure_lookup_table()

#         if central_face_IDs is not False and fpatch_names is not False:
#             i = 0
#             while i < len(central_face_IDs):
#                 for pc in Algorithms.face_patch_constructors:
#                     if i >= len(central_face_IDs):
#                         break
#                     if not pc.is_same_type(bm.faces[central_face_IDs[i]]):
#                         continue
#                     bspline_patches = pc.get_patch(bm.faces[central_face_IDs[i]])
#                     for bc in bspline_patches.bspline_coefs:
#                         PatchOperator.update_patch_obj(fpatch_names[i], bc)
#                         i = i + 1

#         if central_vert_IDs is not False and vpatch_names is not False:
#             i = 0
#             while i < len(central_vert_IDs):
#                 for pc in Algorithms.vert_patch_constructors:
#                     if i >= len(central_vert_IDs):
#                         break
#                     if not pc.is_same_type(bm.verts[central_vert_IDs[i]]):
#                         continue
#                     bspline_patches = pc.get_patch(bm.verts[central_vert_IDs[i]])
#                     for bc in bspline_patches.bspline_coefs:
#                         PatchOperator.update_patch_obj(vpatch_names[i], bc)
#                         i = i + 1

#     facePatchList = list(PatchTracker.fpatch_LUT)
#     vertexPatchList = list(PatchTracker.vpatch_LUT)


bpy.app.handlers.depsgraph_update_post.append(edit_object_change_handler)
bpy.types.Scene.polyhedral_splines_finished = bpy.props.BoolProperty(default=False)
bpy.types.Scene.previous_object = bpy.props.PointerProperty(type=bpy.types.Object)
# old
# @persistent
# def edit_object_change_handler(context):
#     obj = bpy.context.active_object

#     if obj is None:
#         return None

#     if obj.mode == 'EDIT' and Mode.prev == 'EDIT' and obj.type == 'MESH':
#         update_surface(context, obj)

#     Mode.prev = obj.mode

#     return None


# def update_surface(context, obj):
#     bm = bmesh.from_edit_mesh(obj.data)
#     selected_verts = [v for v in bm.verts if v.select]

#     for sv in selected_verts:
#         bmesh.update_edit_mesh(obj.data)

#         # Get the centrol vert that needed to be updated
#         central_vert_IDs = PatchTracker.get_central_vert_ID(sv)
#         vpatch_names = PatchTracker.get_vert_based_patch_obj_name(sv)
#         central_face_IDs = PatchTracker.get_central_face_ID(sv)
#         fpatch_names = PatchTracker.get_face_based_patch_obj_name(sv)

#         bm.verts.ensure_lookup_table()
#         bm.faces.ensure_lookup_table()

#         if central_face_IDs is not False and fpatch_names is not False:
#             i = 0
#             while i < len(central_face_IDs):
#                 for pc in Algorithms.face_patch_constructors:
#                     if i >= len(central_face_IDs):
#                         break
#                     if not pc.is_same_type(bm.faces[central_face_IDs[i]]):
#                         continue
#                     bspline_patches = pc.get_patch(bm.faces[central_face_IDs[i]])
#                     for bc in bspline_patches.bspline_coefs:
#                         PatchOperator.update_patch_obj(fpatch_names[i], bc)
#                         i = i + 1

#         if central_vert_IDs is not False and vpatch_names is not False:
#             i = 0
#             while i < len(central_vert_IDs):
#                 for pc in Algorithms.vert_patch_constructors:
#                     if i >= len(central_vert_IDs):
#                         break
#                     if not pc.is_same_type(bm.verts[central_vert_IDs[i]]):
#                         continue
#                     bspline_patches = pc.get_patch(bm.verts[central_vert_IDs[i]])
#                     for bc in bspline_patches.bspline_coefs:
#                         PatchOperator.update_patch_obj(vpatch_names[i], bc)
#                         i = i + 1

#     facePatchList = list(PatchTracker.fpatch_LUT)
#     vertexPatchList = list(PatchTracker.vpatch_LUT)

# bpy.app.handlers.depsgraph_update_post.append(edit_object_change_handler)