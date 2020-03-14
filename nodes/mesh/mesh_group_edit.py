# This file is part of project Sverchok. It's copyrighted by the contributors
# recorded in the version control history of the file, available from
# its original location https://github.com/nortikin/sverchok/commit/master
#
# SPDX-License-Identifier: GPL3
# License-Filename: LICENSE


from itertools import cycle, chain

import numpy as np

import bpy

from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import repeat_last, updateNode
from sverchok.core.mesh_structure import Mesh, MeshGroup, FacesGroup, EdgesGroup, VertsGroup, LoopsGroup
from sverchok.utils.mesh_structure.check_input import set_safe_attr


class SvMeshEditAttrs(bpy.types.Node, SverchCustomTreeNode):
    """
    Triggers: ...

    ...
    """
    bl_idname = 'SvMeshEditAttrs'
    bl_label = 'Mesh Edit Attributes'
    bl_icon = 'MOD_BOOLEAN'

    edit_group: bpy.props.BoolProperty(name="Edit mesh group", update=updateNode)
    group_name: bpy.props.StringProperty(default="Mesh group", update=updateNode)
    element: bpy.props.EnumProperty(items=[(i, i, '') for i in ['verts', 'edges', 'faces']])
    is_name_valid: bpy.props.BoolProperty(default=True)

    def draw_buttons(self, context, layout):
        layout.prop(self, 'edit_group')
        col = layout.column()
        col.active = self.edit_group
        col.alert = not self.is_name_valid and self.edit_group
        col.prop(self, 'group_name', text='')

    def draw_index_socket(self, socket, context, layout):
        layout.label(text='Indexes')
        layout.prop(self, 'element', text='')

    def sv_init(self, context):
        self.inputs.new('SvStringsSocket', 'Mesh')
        # self.inputs.new('SvStringsSocket', 'Indexes').custom_draw = 'draw_index_socket'
        self.inputs.new('SvDictionarySocket', 'Object')
        self.inputs.new('SvDictionarySocket', 'Faces')
        self.inputs.new('SvDictionarySocket', 'Edges')
        self.inputs.new('SvDictionarySocket', 'Verts')
        self.inputs.new('SvDictionarySocket', 'Loops')
        self.outputs.new('SvStringsSocket', 'Mesh')

    def process(self):
        if not self.inputs['Mesh'].is_linked:
            return

        if not self.validate_name(self.inputs['Mesh'].sv_get(deepcopy=False)[0]):
            return

        data = [chain(s.sv_get(default=(cycle([None])), deepcopy=False), cycle([None])) for s in self.inputs[1:]]
        out = []
        me: Mesh
        for me, layer in zip(self.inputs['Mesh'].sv_get(), zip(*data)):
            mg = me.groups.get(self.group_name)
            if mg:
                for element, attrs in zip([mg, mg.faces, mg.edges, mg.verts, mg.loops], layer):
                    if attrs:
                        [set_safe_attr(element, key, values) for key, values in attrs.items()]
            out.append(me)
        self.outputs['Mesh'].sv_set(out)

    def validate_name(self, mesh: Mesh):
        if self.group_name not in mesh.groups:
            self.is_name_valid = False
            return False
        else:
            self.is_name_valid = True
            return True


def register():
    bpy.utils.register_class(SvMeshEditAttrs)


def unregister():
    bpy.utils.unregister_class(SvMeshEditAttrs)