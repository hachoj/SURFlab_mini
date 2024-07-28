import bpy

class Fake_Net(bpy.types.Operator):
    """fake net operator"""
    bl_label = "Fake Mesh"
    bl_idname = "object.create_fake_mesh"
    bl_description = "Creates a fake net"

    def execute(self, context):
        # Perform some custom action
        self.report({'INFO'}, "Custom Button Pressed")
        print("Button Pressed")
        return {'FINISHED'}