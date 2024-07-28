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
    polyhedral_splines_finished = False
    verts = {}

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

        PolyhedralSplines.polyhedral_splines_finished = True
        #bpy.context.scene.polyhedral_splines_finished = True
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
                PolyhedralSplines.verts.update({patch_name : patchWrapper.patch.corner_coords})

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
        # print(len(PatchTracker.patch_names))
        '''
        if input("Coverage Test? (y/n): ") != 'n':
            PolyhedralSplines.coverage_test()
        '''

# def coverage_test(): 
#     i = 0
#     for key, val in verts.items():
#         i += 1
#         if i % 50 == 0:
#             print(f"Patch {i}")
#         if val != []:
#             for corner in val:
#                 coords = tuple(corner)
#                 create_control_cube(coords, bpy.context.scene.objects[key])

    @staticmethod
    def coverage_test():
        tups = []

        if input("full test? (y/n): ") != 'n':
            for key, val in PolyhedralSplines.verts.items():
                if val != []:
                    for corner in val:
                        coords = tuple(corner)
                        tups.append((coords, key))
            new_tups = []
            for tup in tups:
                if tup[0] not in [t[0] for t in new_tups]:
                    new_tups.append((tup[0], tup[1]))
            print(f"Number of total patches: {len(tups)}")
            print(f"Number of unique patches: {len(new_tups)}")
            i = 0
            for tup in new_tups:
                i += 1
                if i % 50 == 0:
                    print(f"Patch {i}/{len(new_tups)}")
                PolyhedralSplines.create_control_cube(tup[0], bpy.context.scene.objects[tup[1]])
        else:
            for key, item in PolyhedralSplines.verts.items():
                if item != []:
                    print(key, end=', ')
            patch_index = 'y'
            while patch_index != 'n':
                patch_index = input("Enter patch index: ")
                patch_name = "SurfPatch." + str(patch_index)
                for corner in PolyhedralSplines.verts[patch_name]:
                    coords = tuple(corner)
                    PolyhedralSplines.create_control_cube(coords, bpy.context.scene.objects[patch_name])

    @staticmethod
    def control_cube_test(patch_index_str):
        try:
            patch_index = int(patch_index_str)
            patch_name = "SurfPatch." + str(patch_index)
            # patch = bpy.context.scene.objects[patch_name]
            # add_control_cubes(patch) #TODO:
            corners = PolyhedralSplines.verts[patch_name]
            if corners != []:
                for corner in corners:
                    coords = tuple(corner)
                    PolyhedralSplines.create_control_cube(coords, bpy.context.scene.objects[patch_name])
                print("Control cubes added to patch", patch_index)
            else:
                print("No corner coordinates found for patch", patch_index)
            # print("Control cubes added to patch", patch_index)
        except ValueError:
            print("Invalid patch index. Please enter a number.")

    @staticmethod
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
                PolyhedralSplines.control_cube_test(patch_index_str)


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