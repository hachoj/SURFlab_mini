import bpy
from .polyhedral_splines import PolyhedralSplines


class Fake_Net(bpy.types.Operator):
    """fake net operator"""
    bl_label = "Fake Mesh"
    bl_idname = "object.create_fake_mesh"
    bl_description = "Creates a fake net"


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
            # tried to import function from polyhedral_splines.py, didnt work at first so just moved everything here, might fix later
            # fixed
            PolyhedralSplines.coverage_test()
        return {'FINISHED'}
