# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatVectorProperty
from mathutils import Vector
from sverchok.node_tree import SverchCustomTreeNode
from sverchok.data_structure import (updateNode, match_long_repeat, enum_item as e)


class SvMatrixBasisChangeNode(bpy.types.Node, SverchCustomTreeNode):
    ''' Construct a Matrix from arbitrary Track and Up vectors '''
    bl_idname = 'SvMatrixBasisChangeNode'
    bl_label = 'Matrix Basis Change'
    bl_icon = 'OUTLINER_OB_EMPTY'

    OO = ["X Y  Z", "X Z  Y", "Y X  Z", "Y Z  X", "Z X  Y", "Z Y  X"]
    orthogonalizing_order = EnumProperty(
        name="Orthogonalizing Order",
        description="The priority order in which the XYZ vectors are orthogonalized",
        items=e(OO), default=OO[0], update=updateNode)

    normalize = BoolProperty(
        name="Normalize Vectors", description="Normalize the output X,Y,Z vectors",
        default=True, update=updateNode)

    origin = FloatVectorProperty(
        name='Location', description="The location component of the output matrix",
        default=(0, 0, 0), update=updateNode)

    scale = FloatVectorProperty(
        name='Scale', description="The scale component of the output matrix",
        default=(1, 1, 1), update=updateNode)

    vA = FloatVectorProperty(
        name='A', description="A direction",
        default=(1, 0, 0), update=updateNode)

    vB = FloatVectorProperty(
        name='B', description='B direction',
        default=(0, 1, 0), update=updateNode)

    AB = ["A", "B", "-A", "-B"]
    T = EnumProperty(name="T", items=e(AB), default=AB[0], update=updateNode)
    U = EnumProperty(name="U", items=e(AB), default=AB[1], update=updateNode)

    def sv_init(self, context):
        self.width = 150
        self.inputs.new('VerticesSocket', "Location").prop_name = "origin"  # L
        self.inputs.new('VerticesSocket', "Scale").prop_name = "scale"  # S
        self.inputs.new('VerticesSocket', "A").prop_name = "vA"  # A
        self.inputs.new('VerticesSocket', "B").prop_name = "vB"  # B
        self.outputs.new('MatrixSocket', "Matrix")
        self.outputs.new('VerticesSocket', "X")
        self.outputs.new('VerticesSocket', "Y")
        self.outputs.new('VerticesSocket', "Z")

    def split_columns(self, panel, ratios, aligns):
        """
        Splits the given panel into columns based on the given set of ratios.
        e.g ratios = [1, 2, 1] or [.2, .3, .2] etc
        Note: The sum of all ratio numbers doesn't need to be normalized
        """
        col2 = panel
        cols = []
        ns = len(ratios) - 1  # number of splits
        for n in range(ns):
            n1 = ratios[n]  # size of the current column
            n2 = sum(ratios[n + 1:])  # size of all remaining columns
            p = n1 / (n1 + n2)  # percentage split of current vs remaning columns
            # print("n = ", n, " n1 = ", n1, " n2 = ", n2, " p = ", p)
            split = col2.split(percentage=p, align=aligns[n])
            col1 = split.column(align=True)
            col2 = split.column(align=True)
            cols.append(col1)
        cols.append(col2)

        return cols

    def draw_buttons(self, context, layout):
        layout.prop(self, "normalize")
        row = layout.column().row()
        cols = self.split_columns(row, [12, 7, 8], [True, True, True])

        cols[0].prop(self, "orthogonalizing_order", "")
        cols[1].prop(self, "T", "")
        cols[2].prop(self, "U", "")

    def orthogonalizeXYZ(self, X, Y):  # keep X, recalculate Z form X&Y then Y
        Z = X.cross(Y)
        Y = Z.cross(X)
        return X, Y, Z

    def orthogonalizeXZY(self, X, Z):  # keep X, recalculate Y form Z&X then Z
        Y = Z.cross(X)
        Z = X.cross(Y)
        return X, Y, Z

    def orthogonalizeYXZ(self, Y, X):  # keep Y, recalculate Z form X&Y then X
        Z = X.cross(Y)
        X = Y.cross(Z)
        return X, Y, Z

    def orthogonalizeYZX(self, Y, Z):  # keep Y, recalculate X form Y&Z then Z
        X = Y.cross(Z)
        Z = X.cross(Y)
        return X, Y, Z

    def orthogonalizeZXY(self, Z, X):  # keep Z, recalculate Y form Z&X then X
        Y = Z.cross(X)
        X = Y.cross(Z)
        return X, Y, Z

    def orthogonalizeZYX(self, Z, Y):  # keep Z, recalculate X form Y&Z then Y
        X = Y.cross(Z)
        Y = Z.cross(X)
        return X, Y, Z

    def orthogonalizer(self):
        order = self.orthogonalizing_order.replace(" ", "")
        orthogonalizer = eval("self.orthogonalize" + order)
        return lambda T, U: orthogonalizer(T, U)

    def process(self):
        outputs = self.outputs

        # return if no outputs are connected
        if not any(s.is_linked for s in outputs):
            return

        # input values lists
        inputs = self.inputs
        input_locations = inputs["Location"].sv_get()[0]
        input_scales = inputs["Scale"].sv_get()[0]
        input_vAs = inputs["A"].sv_get()[0]
        input_vBs = inputs["B"].sv_get()[0]

        locations = [Vector(i) for i in input_locations]
        scales = [Vector(i) for i in input_scales]
        vAs = [Vector(i) for i in input_vAs]
        vBs = [Vector(i) for i in input_vBs]

        params = match_long_repeat([locations, scales, vAs, vBs])

        orthogonalize = self.orthogonalizer()

        xList = []  # ortho-normal X vector list
        yList = []  # ortho-normal Y vector list
        zList = []  # ortho-normal Z vector list
        matrixList = []
        for L, S, A, B in zip(*params):
            T = eval(self.T)  # map T to one of A, B or its negative
            U = eval(self.U)  # map U to one of A, B or its negative

            X, Y, Z = orthogonalize(T, U)

            if self.normalize:
                X.normalize()
                Y.normalize()
                Z.normalize()

            # prepare the Ortho-Normalized outputs
            if outputs["X"].is_linked:
                xList.append([X.x, X.y, X.z])
            if outputs["Y"].is_linked:
                yList.append([Y.x, Y.y, Y.z])
            if outputs["Z"].is_linked:
                zList.append([Z.x, Z.y, Z.z])

            # composite matrix: M = T * R * S (Tanslation x Rotation x Scale)
            m = [[X.x * S.x, Y.x * S.y, Z.x * S.z, L.x],
                 [X.y * S.x, Y.y * S.y, Z.y * S.z, L.y],
                 [X.z * S.x, Y.z * S.y, Z.z * S.z, L.z],
                 [0, 0, 0, 1]]

            matrixList.append(m)

        outputs["Matrix"].sv_set(matrixList)
        outputs["X"].sv_set([xList])
        outputs["Y"].sv_set([yList])
        outputs["Z"].sv_set([zList])


def register():
    bpy.utils.register_class(SvMatrixBasisChangeNode)


def unregister():
    bpy.utils.unregister_class(SvMatrixBasisChangeNode)
