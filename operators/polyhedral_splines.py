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


class PolyhedralSplines(bpy.types.Operator):
    bl_label = "Interactive Modeling"
    bl_idname = "object.polyhedral_splines"
    bl_description = "Generates polyhedral spline mesh. Some mesh configurations are not supported, subdivide the mesh beforehand if this is the case"

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
        # Check if all submeshes are supported by algorithms.
        # Subdivide the mesh if not.
        if Highlighter.is_subdivision_required(context):
            bpy.ops.object.subdivide_mesh()

        self.__init_patch_obj__(context)
        bpy.ops.ui.reloadtranslation()
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
        
        bpy.app.handlers.depsgraph_update_post.append(edit_object_change_handler)
        while input("Do you want to add control cubes to a patch? (y/n): ") != 'n':
            control_cube_test()

def control_cube_test():
    patch_index_str = input("Enter the patch index to test (e.g., 536): ")
    try:
        patch_index = int(patch_index_str)
        patch_name = "SurfPatch." + str(patch_index)
        patch = bpy.context.scene.objects[patch_name]
        add_control_cubes(patch)
        print("Control cubes added to patch", patch_index)
    except ValueError:
        print("Invalid patch index. Please enter a number.")

def create_control_cube(location, parent_obj):
    bpy.ops.mesh.primitive_cube_add(size=0.01, enter_editmode=False, align='WORLD', location=location, scale=(1, 1, 1))
    cube = bpy.context.active_object
    cube.name = "ControlCube"
    cube.parent = parent_obj

def add_control_cubes(obj):
    if obj.type != 'SURFACE':
        print("Selected object is not a spline patch")
        return
    spline = obj.data.splines[0]
    corners = [list(pt.co)[:3] for pt in list(spline.points)]
    create_control_cube((1,1,1), obj)
    cns = []
    corner_1_x = (corners[0][0] + corners[1][0] + corners [3][0] + corners[4][0]) / 4
    corner_1_y = (corners[0][1] + corners[1][1] + corners [3][1] + corners[4][1]) / 4
    corner_1_z = (corners[0][2] + corners[1][2] + corners [3][2] + corners[4][2]) / 4
    cns.append((corner_1_x, corner_1_y, corner_1_z))
    corner_2_x = (corners[1][0] + corners[2][0] + corners [4][0] + corners[5][0]) / 4
    corner_2_y = (corners[1][1] + corners[2][1] + corners [4][1] + corners[5][1]) / 4
    corner_2_z = (corners[1][2] + corners[2][2] + corners [4][2] + corners[5][2]) / 4
    cns.append((corner_2_x, corner_2_y, corner_2_z))
    corner_3_x = (corners[3][0] + corners[4][0] + corners [6][0] + corners[7][0]) / 4
    corner_3_y = (corners[3][1] + corners[4][1] + corners [6][1] + corners[7][1]) / 4
    corner_3_z = (corners[3][2] + corners[4][2] + corners [6][2] + corners[7][2]) / 4
    cns.append((corner_3_x, corner_3_y, corner_3_z))
    corner_4_x = (corners[4][0] + corners[5][0] + corners [7][0] + corners[8][0]) / 4
    corner_4_y = (corners[4][1] + corners[5][1] + corners [7][1] + corners[8][1]) / 4
    corner_4_z = (corners[4][2] + corners[5][2] + corners [7][2] + corners[8][2]) / 4
    cns.append((corner_4_x, corner_4_y, corner_4_z))
    for corner_x, corner_y, corner_z in cns:
        create_control_cube((corner_x, corner_y, corner_z), obj)

# if previous mode is not edit, switching to edit has no need to update surface
class Mode:
    prev = "OBJECT"


# can't put it in the class
# please see https://developer.blender.org/T73638
prev_mode = 'OBJECT'


@persistent
def edit_object_change_handler(context):
    obj = bpy.context.active_object

    if obj is None:
        return None

    if obj.mode == 'EDIT' and Mode.prev == 'EDIT' and obj.type == 'MESH':
        update_surface(context, obj)

    Mode.prev = obj.mode

    return None


def update_surface(context, obj):
    bm = bmesh.from_edit_mesh(obj.data)
    selected_verts = [v for v in bm.verts if v.select]

    for sv in selected_verts:
        bmesh.update_edit_mesh(obj.data)

        # Get the centrol vert that needed to be updated
        central_vert_IDs = PatchTracker.get_central_vert_ID(sv)
        vpatch_names = PatchTracker.get_vert_based_patch_obj_name(sv)
        central_face_IDs = PatchTracker.get_central_face_ID(sv)
        fpatch_names = PatchTracker.get_face_based_patch_obj_name(sv)

        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        if central_face_IDs is not False and fpatch_names is not False:
            i = 0
            while i < len(central_face_IDs):
                for pc in Algorithms.face_patch_constructors:
                    if i >= len(central_face_IDs):
                        break
                    if not pc.is_same_type(bm.faces[central_face_IDs[i]]):
                        continue
                    bspline_patches = pc.get_patch(bm.faces[central_face_IDs[i]])
                    for bc in bspline_patches.bspline_coefs:
                        PatchOperator.update_patch_obj(fpatch_names[i], bc)
                        i = i + 1

        if central_vert_IDs is not False and vpatch_names is not False:
            i = 0
            while i < len(central_vert_IDs):
                for pc in Algorithms.vert_patch_constructors:
                    if i >= len(central_vert_IDs):
                        break
                    if not pc.is_same_type(bm.verts[central_vert_IDs[i]]):
                        continue
                    bspline_patches = pc.get_patch(bm.verts[central_vert_IDs[i]])
                    for bc in bspline_patches.bspline_coefs:
                        PatchOperator.update_patch_obj(vpatch_names[i], bc)
                        i = i + 1

    facePatchList = list(PatchTracker.fpatch_LUT)
    vertexPatchList = list(PatchTracker.vpatch_LUT)

bpy.app.handlers.depsgraph_update_post.append(edit_object_change_handler)