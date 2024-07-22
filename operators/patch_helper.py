from dataclasses import dataclass

from .bezier_bspline_converter import BezierBsplineConverter
import numpy as np
from .helper import Helper
from .csv_reader import Reader
from .patch_tracker import PatchTracker
import time

from .patch import BezierPatch, BsplinePatch
from .extraordinary_patch_constructor import ExtraordinaryPatchConstructor
from .n_gon_patch_constructor import NGonPatchConstructor
from .polar_patch_constructor import PolarPatchConstructor
from .reg_patch_constructor import RegPatchConstructor
from .t0_patch_constructor import T0PatchConstructor
from .t1_patch_constructor import T1PatchConstructor
from .t2_patch_constructor import T2PatchConstructor
from .two_triangles_two_quads_patch_constructor import TwoTrianglesTwoQuadsPatchConstructor

@dataclass
class PatchWrapper:
    patch: BsplinePatch | BezierPatch = None
    isBSpline = False
    source = None   #The source vert/face the patch is based on
    neighbors = []

    def __init__(self, patch, isBSpline, source, neighbors):
        self.patch = patch
        self.isBSpline = isBSpline
        self.source = source
        self.neighbors = neighbors

class PatchHelper:
    # The algorithm using vert as center
    vert_based_patch_constructors: list = [
        RegPatchConstructor,
        ExtraordinaryPatchConstructor,
        PolarPatchConstructor,
        TwoTrianglesTwoQuadsPatchConstructor
    ]
    # The algorithm using face as center
    face_based_patch_constructors: list = [
        T0PatchConstructor,
        T1PatchConstructor,
        T2PatchConstructor,
        NGonPatchConstructor
    ]

    @staticmethod
    def getPatches(bMesh, isBSpline = True) -> list[PatchWrapper]:
        patchWrappers = []

        vertPatches = PatchHelper.getVertPatches(bMesh, isBSpline)
        facePatches = PatchHelper.getFacePatches(bMesh, isBSpline)

        patchWrappers.extend(vertPatches)
        patchWrappers.extend(facePatches)

        # harry addition
        for patchWrapper in patchWrappers:
            # patchWrapper.patch.corner_coords = (1, 1, 1)
            patchWrapper.patch.corner_coords = PatchHelper.calculate_corner_coords(PatchHelper, patchWrapper)


        return patchWrappers

    #     return patchWrappers
    @staticmethod
    def getVertPatches(bMesh, isBSpline = True) -> list[PatchWrapper]:
        bsplinePatches = []
        # Iterate through each vert of the mesh
        for v in bMesh.verts:
            # Iterate throgh different type of patch constructors
            for pc in PatchHelper.vert_based_patch_constructors:
                if pc.is_same_type(v):
                    patch: BsplinePatch = pc.get_patch(v, isBSpline)
                    neighborVerts: list = pc.get_neighbor_verts(v)
                    patchWrapper = PatchWrapper(patch, isBSpline, v, neighborVerts)
                    bsplinePatches.append(patchWrapper)
        return bsplinePatches

    @staticmethod
    def getFacePatches(bMesh, isBSpline = True) -> list[PatchWrapper]:
        bsplinePatches = []
        # Iterate through each face of the mesh
        for f in bMesh.faces:
            # Iterate throgh different type of patch constructors
            for pc in PatchHelper.face_based_patch_constructors:
                if pc.is_same_type(f):
                    patch: BsplinePatch = pc.get_patch(f, isBSpline)
                    neighborVerts: list = pc.get_neighbor_verts(f)
                    patchWrapper = PatchWrapper(patch, isBSpline, f, neighborVerts)
                    bsplinePatches.append(patchWrapper)
        return bsplinePatches

    # harry addition
    @staticmethod
    def calculate_corner_coords(cls, patchWrapper: PatchWrapper) -> list:
        """
        Calculate the corner coordinates of a patch using the mask
        """
        corner_coords = []
        if(patchWrapper.patch.struct_name == "Regular"):
            # THIeS ONE WORKS
            nb_verts = patchWrapper.neighbors
            corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[0], nb_verts[1], nb_verts[3], nb_verts[4]]), axis=0))   #Corner 0
            corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[1], nb_verts[2], nb_verts[4], nb_verts[5]]), axis=0))   #Corner 1
            corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[3], nb_verts[4], nb_verts[6], nb_verts[7]]), axis=0))   #Corner 2
            corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[4], nb_verts[5], nb_verts[7], nb_verts[8]]), axis=0))   #Corner 3
            # pass
        elif (patchWrapper.patch.struct_name == "EOP"):
            nb_verts = patchWrapper.neighbors
            valence = len(patchWrapper.source.link_edges)
            mask = Reader.csv_to_masks(["eopSct{}".format(valence)])["eopSct{}".format(valence)]
            bezier_coefs = Helper.apply_mask_on_neighbor_verts(mask, nb_verts)
            if(valence == 3):
                # THIS ONE WORKS
                for i in range(0, 32, 16):
                    corner_coords.append(bezier_coefs[i])
                    corner_coords.append(bezier_coefs[i+3])
                    corner_coords.append(bezier_coefs[i+12])
                    corner_coords.append(bezier_coefs[i+15])
                # pass
            elif(valence == 5):
                # THIS ONE WORKS
                for i in range(0, 64, 16):
                    corner_coords.append(bezier_coefs[i])
                    corner_coords.append(bezier_coefs[i+3])
                    corner_coords.append(bezier_coefs[i+12])
                    corner_coords.append(bezier_coefs[i+15])
                # pass
            elif(valence == 6):
                # THIS ONE WORKS
                for i in range(0, 368, 16):
                    corner_coords.append(bezier_coefs[i])
                    corner_coords.append(bezier_coefs[i+3])
                    corner_coords.append(bezier_coefs[i+12])
                    corner_coords.append(bezier_coefs[i+15])
                # pass
            elif(valence == 7):
                # THIS ONE WORKS
                for i in range(0, 432, 16):
                    corner_coords.append(bezier_coefs[i])
                    corner_coords.append(bezier_coefs[i+3])
                    corner_coords.append(bezier_coefs[i+12])
                    corner_coords.append(bezier_coefs[i+15])
                # pass
            elif(valence == 8):
                # THIS ONE WORKS
                for i in range(0, 496, 16):
                    corner_coords.append(bezier_coefs[i])
                    corner_coords.append(bezier_coefs[i+3])
                    corner_coords.append(bezier_coefs[i+12])
                    corner_coords.append(bezier_coefs[i+15])
                # pass
        elif(patchWrapper.patch.struct_name == "Polar"):
            nb_verts = patchWrapper.neighbors
            valence = len(nb_verts) - 1   #Dont include central vert
            mask = Reader.csv_to_masks(["polarSct{}".format(valence)])["polarSct{}".format(valence)]
            bezier_coefs = Helper.apply_mask_on_neighbor_verts(mask, nb_verts)
            if(valence == 3):
                # THIS ONE WORKS
                # center
                corner_coords.append(bezier_coefs[0])
                # outside
                for i in range(9, 48, 12):
                    corner_coords.append(bezier_coefs[i])
                # pass
            elif(valence == 5):
                # THIS ONE WORKS
                # center
                corner_coords.append(bezier_coefs[0])
                # outside
                for i in range(9, 96, 12):
                    corner_coords.append(bezier_coefs[i])
                # pass
            elif(valence == 6):
                # THIS ONE WORKS
                # center
                corner_coords.append(bezier_coefs[0])
                # outside
                for i in range(9, 96, 12):
                    corner_coords.append(bezier_coefs[i])
                # pass
            elif(valence == 7):
                # THIS ONE WORKS
                # center
                corner_coords.append(bezier_coefs[0])
                # outside
                for i in range(9, 96, 12):
                    corner_coords.append(bezier_coefs[i])
                # pass
            elif(valence == 8):
                # THIS ONE WORKS
                # center
                corner_coords.append(bezier_coefs[0])
                # outside
                for i in range(9, 96, 12):
                    corner_coords.append(bezier_coefs[i])
                # pass
        # elif(patchWrapper.patch.struct_name == "T0"):
        #     print("T0")
        #     nb_verts = patchWrapper.neighbors
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[0], nb_verts[1], nb_verts[3], nb_verts[4]]), axis=0))   #Corner 0
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[2], nb_verts[3], nb_verts[5], nb_verts[6]]), axis=0))   #Corner 1
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[6], nb_verts[7], nb_verts[9], nb_verts[10]]), axis=0))   #Corner 2
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[8], nb_verts[9], nb_verts[11], nb_verts[12]]), axis=0))   #Corner 3
        # elif(patchWrapper.patch.struct_name == "T1"):
        #     print("T1")
        #     nb_verts = patchWrapper.neighbors
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[0], nb_verts[1], nb_verts[3], nb_verts[4]]), axis=0))   #Corner 0
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[2], nb_verts[3], nb_verts[5], nb_verts[6]]), axis=0))   #Corner 1
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[8], nb_verts[9], nb_verts[11], nb_verts[12]]), axis=0))   #Corner 2
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[10], nb_verts[11], nb_verts[13], nb_verts[14]]), axis=0))   #Corner 3
        # elif(patchWrapper.patch.struct_name == "T2"):
        #     print("T2")
        #     nb_verts = patchWrapper.neighbors
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[0], nb_verts[1], nb_verts[3], nb_verts[4]]), axis=0))   #Corner 0
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[2], nb_verts[3], nb_verts[5], nb_verts[6]]), axis=0))   #Corner 1
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[10], nb_verts[11], nb_verts[13], nb_verts[14]]), axis=0))   #Corner 2
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[12], nb_verts[13], nb_verts[15], nb_verts[16]]), axis=0))   #Corner 3
        # elif(patchWrapper.patch.struct_name == "n-gon"):
        #     nb_verts = patchWrapper.neighbors
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[0], nb_verts[1], nb_verts[3], nb_verts[4]]), axis=0))   #Corner 0
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[2], nb_verts[3], nb_verts[5], nb_verts[6]]), axis=0))   #Corner 1
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[8], nb_verts[9], nb_verts[11], nb_verts[12]]), axis=0))   #Corner 2
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[10], nb_verts[11], nb_verts[13], nb_verts[14]]), axis=0))   #Corner 3
        # elif(patchWrapper.patch.struct_name == "2T2Q"):
        #     print("2T2Q")
        #     nb_verts = patchWrapper.neighbors
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[0], nb_verts[1], nb_verts[3], nb_verts[4]]), axis=0))   #Corner 0
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[2], nb_verts[3], nb_verts[5], nb_verts[6]]), axis=0))   #Corner 1
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[6], nb_verts[7], nb_verts[8], nb_verts[4]]), axis=0))   #Corner 2
        #     corner_coords.append(np.mean(Helper.convert_verts_from_list_to_matrix([nb_verts[0], nb_verts[1], nb_verts[4], nb_verts[7]]), axis=0))   #Corner 3
        return corner_coords 