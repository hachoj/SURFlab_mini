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

        bpy.context.scene.polyhedral_splines_finished = True
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


def control_cube_test(patch_index_str):
    # patch_index_str = input("Enter the patch index to test (e.g., 536): ")
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
    four_corners = get_control_points(spline)
    # TODO: some of these patches are calculate with more than 9 control points
    # for example, patch 100 has 16 control points but in the calculation, only 9 control points are used
    # need to find a way to automatically compute the correct averages with a function
    # that takes in the number of control points to get the correct averages for the corners
    # back into 4 corners no matter the amount of control points
    for corner in four_corners:
        create_control_cube(corner, obj)


def get_control_points(spline):
    control_points = [list(pt.co)[:] for pt in list(spline.points)]
    four_corners = []
    sub_control_points = []
    square_length = math.sqrt(len(control_points))
    subgrids = find_subgrids(int(square_length))
    for subgrid in subgrids:
        x, y, z = 0, 0, 0
        for row in subgrid:
            for point in row:
                x += control_points[point][0] * control_points[point][3]
                y += control_points[point][1] * control_points[point][3]
                z += control_points[point][2] * control_points[point][3]
        num_sub_points = (square_length - 1) ** 2
        x /= num_sub_points
        y /= num_sub_points
        z /= num_sub_points
        four_corners.append((x, y, z))
    return four_corners


def find_subgrids(n):
    subgrids = []

    # Helper function to get the node label at a given row and column
    def get_node(row, col):
        return row + col * n

    # Top-left subgrid
    top_left = [[get_node(row, col) for col in range(n - 1)] for row in range(1, n)]
    subgrids.append(top_left)

    # Top-right subgrid
    top_right = [[get_node(row, col) for col in range(1, n)] for row in range(1, n)]
    subgrids.append(top_right)

    # Bottom-left subgrid
    bottom_left = [[get_node(row, col) for col in range(n - 1)] for row in range(n - 1)]
    subgrids.append(bottom_left)

    # Bottom-right subgrid
    bottom_right = [[get_node(row, col) for col in range(1, n)] for row in range(n - 1)]
    subgrids.append(bottom_right)

    return subgrids


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

    if bpy.context.scene.polyhedral_splines_finished:
        if obj.type == 'SURFACE':
            # print("PolyhedralSplines has finished, and a surface is selected")
            if prev_obj != obj:
                print("PolyhedralSplines has finished, and a new surface is selected")
                #print("new")
                #while input("Do you want to add control cubes to a patch? (y/n): ") != 'n':
                    # print(obj.name)
                    # Split the string by '.' and take the second part
                patch_index_str = obj.name.split('.')[1]
                control_cube_test(patch_index_str)


    if obj.mode == 'EDIT' and Mode.prev == 'EDIT' and obj.type == 'MESH':
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
bpy.types.Scene.polyhedral_splines_finished = bpy.props.BoolProperty(default=False)
bpy.types.Scene.previous_object = bpy.props.PointerProperty(type=bpy.types.Object)