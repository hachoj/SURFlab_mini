import bpy
from .operators.polyhedral_splines import PolyhedralSplines
from .operators.highlighter import Highlighter
from .operators.main_ui import MainUI
from .operators.ui_helper import ToggleFaces, ToggleSurfPatchCollection
from .operators.ui_color import COLOR_OT_TemplateOperator
from .operators.moments import Moments
from .operators.subdivide_mesh import SubdivideMesh
from .operators.ui_exporter import IGSExporter
from .operators.surface_mesh import SurfaceMesh

bl_info = {
    "name": "polyhedral_splines",
    "description": "An interactive spline generation addon",
    "version": (1, 0, 1),
    "blender": (2, 80, 2),
    "category": "Modeling"
}

classes = (
    PolyhedralSplines,
    Highlighter,
    ToggleFaces,
    ToggleSurfPatchCollection,
    MainUI,
    COLOR_OT_TemplateOperator,
    IGSExporter,
    Moments,
    SubdivideMesh,
    SurfaceMesh
)

register, unregister = bpy.utils.register_classes_factory(classes)
bpy.types.TOPBAR_MT_file_export.append(IGSExporter.menu_func_export)