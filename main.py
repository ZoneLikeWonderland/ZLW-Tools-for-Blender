bl_info = {
    "name": "ZLW Add-on",
    "description": "",
    "author": "ZoneLikeWonderland",
    "version": (0, 0, 1),
    "blender": (2, 93, 0),
    "location": "3D View > Tools",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Development"
}


import bpy
import os
import json
import itertools
import glob
import numpy as np
import datetime


from bpy.props import (
    StringProperty,
    PointerProperty,
)

from bpy.types import (
    Panel,
    Operator,
    AddonPreferences,
    PropertyGroup,
)

# ------------------------------------------------------------------------
#    Functions
# ------------------------------------------------------------------------


def import_keys(key_folder, append=False):

    face_model_name = os.path.basename(key_folder)

    expression_names = []
    expression_models = []

    for filepath in sorted(glob.glob(os.path.join(key_folder, "*.obj"))):
        print(filepath)
        expression_name = os.path.basename(filepath)[:-4]
        print("Reading expression morph target: " + expression_name)
        filename = expression_name + '.obj'
        bpy.ops.import_scene.obj(filepath=filepath, use_split_objects=False)
        imported_object = bpy.context.selected_objects[0]
        imported_object.name = expression_name

        expression_names.append(expression_name)
        expression_models.append(imported_object)

    # Select all shape models
    for expression_model in expression_models[1:]:
        expression_model.select_set(True)

    face_model_neutral_object = expression_models[0]
    face_model_neutral_object.name = face_model_name

    if append:
        bpy.ops.object.join_shapes()

        face_model_neutral_object.select_set(True)
        bpy.ops.object.delete()

    else:
        bpy.context.view_layer.objects.active = face_model_neutral_object

        bpy.ops.object.join_shapes()
        bpy.ops.object.delete()

        face_model_neutral_object.select_set(True)
        bpy.context.view_layer.objects.active = face_model_neutral_object
        # bpy.ops.object.shade_smooth()

        bpy.ops.export_scene.fbx(filepath=os.path.join(os.path.dirname(os.path.abspath(key_folder)), f"{os.path.basename(key_folder)}.fbx"), use_selection=True, object_types={"MESH"}, mesh_smooth_type="FACE")


def export_keys(output_folder):

    model = bpy.context.object

    names = []
    for key in model.data.shape_keys.key_blocks:
        key.value = 0
        names.append(key.name)

    os.makedirs(output_folder, exist_ok=True)

    for i, name in enumerate(sorted(names)):
        key = model.data.shape_keys.key_blocks[name]
        key.value = 1

        bpy.ops.export_scene.obj(
            filepath=os.path.join(output_folder, rf"{i:04d}_{name}.obj"),
            check_existing=True,
            use_selection=True,
            use_normals=False,
            use_uvs=True,
            use_materials=False,
            keep_vertex_order=True,
        )
        key.value = 0


def apply_npy_weight_to_blendshapes(npy_path):

    bsws = np.load(bpy.path.abspath(npy_path))
    obj = bpy.context.object
    for i in range(bsws.shape[0]):
        bs = bsws[i]
        for j in range(len(bs)):
            frame_shape = obj.data.shape_keys.key_blocks[j + 1]
            frame_shape.value = bs[j]
            frame_shape.keyframe_insert(data_path="value", frame=i)


# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class ZLWProperties(PropertyGroup):

    path_import_keys: StringProperty(
        name="",
        description="Path to keys directory",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    path_export_keys: StringProperty(
        name="",
        description="Path to keys directory",
        default="",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    path_bsweight_npy: StringProperty(
        name="",
        description="Path to bs weight.npy",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )


# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------

class ZLWOperator(Operator):
    bl_options = {'REGISTER', 'UNDO'}


class WM_OT_ImportKeys(ZLWOperator):
    bl_label = "Import keys from folder"
    bl_idname = "wm.import_keys"

    def execute(self, context):
        scene = context.scene
        zlw_properties = scene.zlw_properties

        import_keys(zlw_properties.path_import_keys)

        return {'FINISHED'}


class WM_OT_AppendKeys(ZLWOperator):
    bl_label = "Append keys from folder"
    bl_idname = "wm.append_keys"

    def execute(self, context):
        scene = context.scene
        zlw_properties = scene.zlw_properties

        import_keys(zlw_properties.path_import_keys, append=True)

        return {'FINISHED'}


class WM_OT_ExportKeys(ZLWOperator):
    bl_label = "Export keys to folder"
    bl_idname = "wm.export_keys"

    def execute(self, context):
        scene = context.scene
        zlw_properties = scene.zlw_properties

        export_keys(zlw_properties.path_export_keys)

        return {'FINISHED'}


class WM_OT_ApplyBsw(ZLWOperator):
    bl_label = "Apply blendshape weight"
    bl_idname = "wm.apply_bsw"

    def execute(self, context):
        scene = context.scene
        zlw_properties = scene.zlw_properties

        apply_npy_weight_to_blendshapes(zlw_properties.path_bsweight_npy)

        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------


class ZLWPanel(Panel):
    bl_idname = "OBJECT_PT_ZLW_panel"
    bl_label = "ZLW Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ZLW Tools"
    # bl_context = "objectmode"

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        zlw_properties = scene.zlw_properties

        sublayout = layout.box()
        sublayout.prop(zlw_properties, "path_import_keys", text="keys folder")
        subsublayout = sublayout.row()
        subsublayout.operator("wm.import_keys")
        subsublayout.operator("wm.append_keys")

        sublayout = layout.box()
        sublayout.prop(zlw_properties, "path_export_keys", text="keys folder")
        sublayout.operator("wm.export_keys")

        sublayout = layout.box()
        sublayout.prop(zlw_properties, "path_bsweight_npy", text="bsw path")
        sublayout.operator("wm.apply_bsw")


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    ZLWProperties,
    WM_OT_ImportKeys,
    WM_OT_AppendKeys,
    WM_OT_ExportKeys,
    WM_OT_ApplyBsw,
    ZLWPanel,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.zlw_properties = PointerProperty(type=ZLWProperties)

    print("ZLW tools loaded")


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.zlw_properties


if __name__ == "__main__":
    register()
