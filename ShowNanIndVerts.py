bl_info = {
    "name": "ShowNanIndVerts",
    "blender": (3, 6, 0),
    "description": "Show all non(ind) verticies",
    "author": "Prostrelov",
    "category": "Edit"
}

import bpy, bmesh
import mathutils
from bpy.types import PropertyGroup
from bpy.props import (
    CollectionProperty,
    IntProperty,
    BoolProperty,
    StringProperty,
    PointerProperty,
)


class SearchNanindVerts(bpy.types.Operator):
    bl_idname = 'object.search_nanind_verts'
    bl_label = 'find all nan ind verts'

    def execute(self, context):
        
        # force obj mode
        if bpy.context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        # get verts coords
        obj = bpy.context.active_object
        if obj.mode == 'EDIT':
            # this works only in edit mode,
            bm = bmesh.from_edit_mesh(obj.data)
            verts = [vert.co for vert in bm.verts]
        else:
            # this works only in object mode,
            verts = [vert.co for vert in obj.data.vertices]
        #save Basis coordinates as tuples
        plain_verts = [vert.to_tuple() for vert in verts]

        # process shape keys
        nanind_list = []
        muted_nanind_list = []
        shapekeys = obj.data.shape_keys.key_blocks
        if(len(shapekeys))>0:
            # store Basis key coords
            #basis_verts = [vert.co for vert in shapekeys[0].data]
            basis_verts = shapekeys[0].data
            
            # PROCESS SHAPEKEY COORDS
            for key in shapekeys:
                if(key.mute == True):
                    muted_nanind_list.append(key.name)
                for idx, vert in enumerate(key.data):
                    if str(vert.co[0]) == 'nan':
                        #print("vert.co nanind: ", vert.co)
                        nanind_list.append(idx)
            
        #print("nanind_list: ", nanind_list)
        # exclude duplicates
        nanind_list = list(set(nanind_list))
        nanind_list_str = ""
        for vert_idx in nanind_list:
            nanind_list_str += str(vert_idx)+","
        #print("nanind_list_str: ", nanind_list_str)
        bpy.context.scene.SearchNanindVerts_Property = nanind_list_str
        
        #print warning for muted shape keys
        print("ShowNanindVerts :: Muted Shape Keys with nonind verticies (unmute shape keys to fix them): ")
        print(muted_nanind_list)
        return {'FINISHED'}

class JumpToNanindVert(bpy.types.Operator):
    bl_idname = 'object.jump_to_nanind_vert'
    bl_label = 'jump to nan ind verts'
    vert: bpy.props.IntProperty()
    
    def execute(self, context):
        # force deselect comps
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action = 'DESELECT')
            
        # switch to obj mode first
        if bpy.context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            # select vert
            obj = bpy.context.active_object
            vert = obj.data.vertices[self.vert]
            vert.select = True
        
        # force edit mode comps
        if bpy.context.active_object.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        
        # focus on vert
        areas  = [area for area in bpy.context.window.screen.areas if area.type == 'VIEW_3D']
        with bpy.context.temp_override(window=bpy.context.window, area=areas[0], region=[region for region in areas[0].regions if region.type == 'WINDOW'][0], screen=bpy.context.window.screen):
            bpy.ops.view3d.view_selected()
        
        
        return {'FINISHED'}
        
class RestoreNanindVert(bpy.types.Operator):
    bl_idname = 'object.restore_nanind_vert'
    bl_label = 'overwrite one nan ind verts with basis coords'
    vert: bpy.props.IntProperty()
        
    def execute(self, context):
        nanindstr = bpy.context.scene.SearchNanindVerts_Property
        nanindlist = [l for l in nanindstr.split(',') if l.strip()]
        #print("RestoreNanindVert::nanindlist: ", nanindlist)
        
        # force obj mode
        if bpy.context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        # get verts coords
        obj = bpy.context.active_object

        # process shape keys
        shapekeys = obj.data.shape_keys.key_blocks
        if(len(shapekeys))>0:
            # store Basis key coords
            basis_verts = shapekeys[0].data
            
            # process ShapeKey coords
            for key in shapekeys:
                if(key.mute == False):
                    print("restore key: ", key.name)
                    vert = key.data[self.vert]
                    if str(vert.co[0]) == 'nan':
                        # overwrite nonind vert coords with basis vert coords
                        vert.co = basis_verts[self.vert].co
        
        nanindstr = nanindstr.replace(str(self.vert), '')
        bpy.context.scene.SearchNanindVerts_Property = nanindstr
        
        return {'FINISHED'}

class FixNanindVert(bpy.types.Operator):
    bl_idname = 'object.fix_nanind_vert'
    bl_label = 'overwrite one nan ind verts with closest verts coords'
    vert: bpy.props.IntProperty()
        
    def execute(self, context):
        nanindstr = bpy.context.scene.SearchNanindVerts_Property
        nanindlist = [l for l in nanindstr.split(',') if l.strip()]
        #print("FixNanindVert::nanindlist: ", nanindlist)
        
        # force obj mode
        if bpy.context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        # get verts coords
        obj = bpy.context.active_object

        # process shape keys
        shapekeys = obj.data.shape_keys.key_blocks
        if(len(shapekeys))>0:
            # store Basis key coords
            #basis_verts = shapekeys[0].data
            
            # process ShapeKey coords
            for key in shapekeys:
                if(key.mute == False):
                    print("fix key: ", key.name)
                    shapekey_vert = key.data[self.vert]
                    #mesh_vert = obj.data.vertices[self.vert]
                    fmesh = bmesh.new()
                    fmesh.from_mesh(obj.data)
                    # ensure bmesh internal index tables are fresh
                    fmesh.verts.ensure_lookup_table()
                    fmesh.edges.ensure_lookup_table()
                    fmesh.faces.ensure_lookup_table()
                    # reconstruct vertex instance
                    mesh_vert = fmesh.verts[self.vert]
                    #get closest verts
                    #start_sel = [v.index for v in obj.data.vertices if v.select]
                    nb_verts_coord_list = []
                    vert_edges = mesh_vert.link_edges
                    #print("vert_edges: ", vert_edges)
                    for e in vert_edges:
                        for v in e.verts:
                            if v.index != mesh_vert.index:
                                if str(v.co[0]) != 'nan':
                                    # get shapekey vertex coord (not mesh vertex coord)
                                    key_vert = key.data[v.index]
                                    nb_verts_coord_list.append(key_vert.co)
                    # calculate center coord between neighbor verts
                    #print("nb_verts_coord_list: ", nb_verts_coord_list)
                    x, y, z = [ sum( [v[i] for v in nb_verts_coord_list] ) for i in range(3)]
                    #print("x,y,z: ", x,y,z)
                    center = mathutils.Vector( (x, y, z ) ) / len(nb_verts_coord_list)
                    #print("center: ", center)
                    # overwrite nonind vert coords with basis vert coords
                    shapekey_vert.co = center
        nanindstr = nanindstr.replace(str(self.vert), '')
        bpy.context.scene.SearchNanindVerts_Property = nanindstr
        
        return {'FINISHED'}

class RestoreAllNanindVert(bpy.types.Operator):
    bl_idname = 'object.restore_all_nanind_vert'
    bl_label = 'overwrite all nan ind verts with basis coords'
        
    def execute(self, context):
        nanindstr = bpy.context.scene.SearchNanindVerts_Property
        nanindlist = [int(l) for l in nanindstr.split(',') if l.strip()]
        #print("RestoreNanindVert::nanindlist: ", nanindlist)
        
        # force obj mode
        if bpy.context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        # get verts coords
        obj = bpy.context.active_object

        # process shape keys
        shapekeys = obj.data.shape_keys.key_blocks
        if(len(shapekeys))>0:
            # store Basis key coords
            basis_verts = shapekeys[0].data
            
            # process ShapeKey coords
            for key in shapekeys:
                if(key.mute == False):
                    print("restore key: ", key.name)
                    for v in nanindlist:
                        vert = key.data[v]
                        if str(vert.co[0]) == 'nan':
                            # overwrite nonind vert coords with basis vert coords
                            vert.co = basis_verts[v].co
                    
        bpy.context.scene.SearchNanindVerts_Property = ""
        
        return {'FINISHED'}

class FixAllNanindVert(bpy.types.Operator):
    bl_idname = 'object.fixall_nanind_vert'
    bl_label = 'overwrite all nan ind verts with closest verts coords'
    
    
    def execute(self, context):
        nanindstr = bpy.context.scene.SearchNanindVerts_Property
        nanindlist = [int(l) for l in nanindstr.split(',') if l.strip()]
        #print("RestoreNanindVert::nanindlist: ", nanindlist)
        
        # force obj mode
        if bpy.context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        
        # get verts coords
        obj = bpy.context.active_object

        # process shape keys
        shapekeys = obj.data.shape_keys.key_blocks
        if(len(shapekeys))>0:
            # store Basis key coords
            #basis_verts = shapekeys[0].data
            
            # process ShapeKey coords
            for key in shapekeys:
                if(key.mute == False):
                    print("fix key: ", key.name)
                    for vx in nanindlist:
                        shapekey_vert = key.data[vx]
                        #mesh_vert = obj.data.vertices[self.vert]
                        fmesh = bmesh.new()
                        fmesh.from_mesh(obj.data)
                        # ensure bmesh internal index tables are fresh
                        fmesh.verts.ensure_lookup_table()
                        fmesh.edges.ensure_lookup_table()
                        fmesh.faces.ensure_lookup_table()
                        # reconstruct vertex instance
                        mesh_vert = fmesh.verts[vx]
                        #get closest verts
                        #start_sel = [v.index for v in obj.data.vertices if v.select]
                        nb_verts_coord_list = []
                        vert_edges = mesh_vert.link_edges
                        #print("vert_edges: ", vert_edges)
                        for e in vert_edges:
                            for v in e.verts:
                                if v.index != mesh_vert.index:
                                    if str(v.co[0]) != 'nan':
                                        # get shapekey vertex coord (not mesh vertex coord)
                                        key_vert = key.data[v.index]
                                        nb_verts_coord_list.append(key_vert.co)
                        # calculate center coord between neighbor verts
                        #print("nb_verts_coord_list: ", nb_verts_coord_list)
                        x, y, z = [ sum( [v[i] for v in nb_verts_coord_list] ) for i in range(3)]
                        #print("x,y,z: ", x,y,z)
                        center = mathutils.Vector( (x, y, z ) ) / len(nb_verts_coord_list)
                        #print("center: ", center)
                        # overwrite nonind vert coords with basis vert coords
                        shapekey_vert.co = center
                    
        bpy.context.scene.SearchNanindVerts_Property = ""
        
        return {'FINISHED'}
    
class ShowNanIndVerts(bpy.types.Panel):
    """Creates a Panel in the 3DView properties region"""
    bl_label = "Show NanInd Verts"
    bl_idname = "MESH_PT_show_nanind_verts"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Edit'
    #bl_space_type = 'PROPERTIES'
    #bl_region_type = 'WINDOW'
    #bl_context = 'data'
    #bl_options = {'DEFAULT_CLOSED'}
    bl_description = "search for verts with -nan(ind) broken coordinates"
    
    @classmethod
    def poll(self, context):
        return context.active_object is not None
        
    def draw(self, context):
        # UI
        layout = self.layout
        
        # OPERATOR BOX
        row = layout.row()
        col = row.column()
        row.label(text=context.active_object.name, text_ctxt='', translate=False, icon='OBJECT_DATA')
        row.operator(SearchNanindVerts.bl_idname, text='search',text_ctxt='',translate=False,icon='VIEWZOOM')
        col = row.column()
        row.operator(RestoreAllNanindVert.bl_idname, text='restore all',text_ctxt='',translate=False,icon='BACK')
        col = row.column()
        row.operator(FixAllNanindVert.bl_idname, text='fix all',text_ctxt='',translate=False,icon='MODIFIER')
        nanindstr = bpy.context.scene.SearchNanindVerts_Property
        nanindlist = [l for l in nanindstr.split(',') if l.strip()]
        #print("nanindlist_splited: ", nanindlist)
        for v in nanindlist:
            row = layout.row()
            row.label(text=v, text_ctxt='', translate=False, icon='GROUP_VERTEX')
            # JUMP OPERATOR
            col = row.column()
            op = col.operator(JumpToNanindVert.bl_idname, icon='VIEWZOOM', text='')
            op.vert = int(v)
            col = row.column()
            rop = col.operator(RestoreNanindVert.bl_idname, icon='BACK', text='')
            rop.vert = int(v)
            col = row.column()
            rop = col.operator(FixNanindVert.bl_idname, icon='MODIFIER', text='')
            rop.vert = int(v)


def register():
    bpy.utils.register_class(ShowNanIndVerts)
    bpy.utils.register_class(SearchNanindVerts)
    bpy.utils.register_class(RestoreNanindVert)
    bpy.utils.register_class(RestoreAllNanindVert)
    bpy.utils.register_class(JumpToNanindVert)
    bpy.utils.register_class(FixNanindVert)
    bpy.utils.register_class(FixAllNanindVert)
    bpy.types.Scene.SearchNanindVerts_Property = StringProperty(name="nanind", description="nanInd verts list", default="")

def unregister():
    bpy.utils.unregister_class(ShowNanIndVerts)
    bpy.utils.unregister_class(SearchNanindVerts)
    bpy.utils.unregister_class(RestoreNanindVert)
    bpy.utils.unregister_class(RestoreAllNanindVert)
    bpy.utils.unregister_class(JumpToNanindVert)
    bpy.utils.unregister_class(FixNanindVert)
    bpy.utils.unregister_class(FixAllNanindVert)
    del bpy.types.Scene.SearchNanindVerts_Property

if __name__ == "__main__":
    register()
