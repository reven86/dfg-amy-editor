"""Describes the structure and constraints of objects used in data file of WOG."""

# Different type of attributes

BOOLEAN_TYPE = 'boolean'
INTEGER_TYPE = 'integer'
REAL_TYPE = 'real'
RGB_COLOR_TYPE = 'rgb_color'
XY_TYPE = 'xy'
ENUMERATED_TYPE = 'enumerated'
STRING_TYPE = 'string'
ANGLE_DEGREES_TYPE = 'angle.degrees'
REFERENCE_TYPE = 'reference'


class AttributeDesc(object):
    def __init__( self, name, type, init = None, default = None, allow_empty = False, mandatory = False ):
        self.name = name
        self.type = type
        self.init = init
        self.default = default
        self.allow_empty = allow_empty
        self.mandatory = mandatory

    def __str__( self ):
        return '%s(name=%s, type=%s, mandatory=%s)' % (self.__class__.__name__, self.name, self.type, self.mandatory)

class NumericAttributeDesc(AttributeDesc):
    def __init__( self, name, type, min_value = None, max_value = None, **kwargs ):
        AttributeDesc.__init__( self, name, type, **kwargs )
        self.min_value = min_value
        self.max_value = max_value

class ColorAttributeDesc(AttributeDesc):
    def __init__( self, name, type, components, **kwargs ):
        AttributeDesc.__init__( self, name, type, **kwargs )
        self.nb_components = components

class Vector2DAttributeDesc(AttributeDesc):
    def __init__( self, name, type, **kwargs ):
        AttributeDesc.__init__( self, name, type, **kwargs )

class EnumeratedAttributeDesc(AttributeDesc):
    def __init__( self, name, values, is_list = False, **kwargs ):
        AttributeDesc.__init__( self, name, ENUMERATED_TYPE, **kwargs )
        self.values = set( values )
        self.is_list = is_list

class ReferenceAttributeDesc(AttributeDesc):
    def __init__( self, name, referenced_familly, reference_scope, **kwargs ):
        AttributeDesc.__init__( self, name, REFERENCE_TYPE, **kwargs )
        self.referenced_familly = referenced_familly
        self.reference_scope = reference_scope

def bool_attribute( name, **kwargs ):
    return AttributeDesc( name, BOOLEAN_TYPE, **kwargs )

def int_attribute( name, min_value = None, **kwargs ):
    return NumericAttributeDesc( name, INTEGER_TYPE, min_value = min_value, **kwargs )

def real_attribute( name, min_value = None, max_value = None, **kwargs ):
    return NumericAttributeDesc( name, REAL_TYPE, min_value = min_value, max_value = max_value, **kwargs )

def rgb_attribute( name, **kwargs ):
    return ColorAttributeDesc( name, RGB_COLOR_TYPE, components = 3, **kwargs )

def xy_attribute( name, **kwargs ):
    return Vector2DAttributeDesc( name, XY_TYPE, **kwargs )

def enum_attribute( name, values, **kwargs ):
    return EnumeratedAttributeDesc( name, values, **kwargs )

def string_attribute( name, **kwargs ):
    return AttributeDesc( name, STRING_TYPE, **kwargs )

def angle_degrees_attribute( name, min_value = None, max_value = None, **kwargs ):
    return NumericAttributeDesc( name, ANGLE_DEGREES_TYPE, min_value = min_value, max_value = max_value, **kwargs )

def reference_attribute( name, referenced_familly, reference_scope, **kwargs ):
    return ReferenceAttributeDesc( name, referenced_familly = referenced_familly, reference_scope = reference_scope, **kwargs )

class ObjectDesc(object):
    def __init__( self, tag, attributes = None ):
        self.tag = tag
        attributes = attributes or []
        self.attributes_order = [ attribute.name for attribute in attributes ]
        self.attributes_by_name = {}
        self.add_attributes( attributes )

    def add_attributes( self, attributes ):
        for attribute in attributes:
            assert attribute.name not in self.attributes_by_name, attribute.name
            self.attributes_by_name[attribute.name] = attribute
            attribute.object = self

    def get_attribute_desc( self, attribute_name ):
        return self.attributes_by_name.get( attribute_name )

    def __str__( self ):
        return '%s(tag=%s, attributes=[%s])' % (self.__class__.__name__, self.tag, ','.join(self.attributes_order))

def describe_object( tag, attributes = None ):
    return ObjectDesc( tag, attributes )

class ScopeDesc(object):
    def __init__( self, scope_name, objects_desc = None, child_scopes = None ):
        objects_desc = objects_desc or []
        child_scopes = child_scopes or []
        self.child_scopes = child_scopes
        self.scope_name = scope_name
        self.objects_by_tag = {}
        self.add_objects( objects_desc )

    def add_objects( self, objects_desc ):
        for object_desc in objects_desc:
            assert object_desc.tag not in self.objects_by_tag, object_desc.tag
            self.objects_by_tag[object_desc.tag] = object_desc
            object_desc.scope = self

    def add_child_scopes( self, child_scopes ):
        self.child_scopes.extend( child_scopes )

    def get_attribute_desc( self, tag, attribute_name ):
        """Returns the attribute desc declared for the specified tag."""
        object_desc = self.objects_by_tag.get( tag )
        if object_desc:
            return object_desc.get_attribute_desc( attribute_name )
        return None

    def __str__( self ):
        return '%s(name=%s, attributes=[%s])' % (self.__class__.__name__, self.scope_name, ','.join(self.objects_by_tag.keys()))

def describe_scope( scope_name, objects_desc = None, child_scopes = None ):
    return ScopeDesc( scope_name, objects_desc )

# Declares the scope hierachy
LEVEL_GAME_SCOPE = describe_scope( 'global.island.level.game' )

LEVEL_SCENE_SCOPE = describe_scope( 'global.island.level.scene' )

LEVEL_RESOURCE_SCOPE = describe_scope( 'global.island.level.resource' )

LEVEL_SCOPE = describe_scope( 'global.island.level',
                               child_scopes = [ LEVEL_GAME_SCOPE, LEVEL_SCENE_SCOPE, LEVEL_RESOURCE_SCOPE ] )
ISLAND_SCOPE = describe_scope( 'global.island',
                               child_scopes = [ LEVEL_SCOPE ] )
GLOBAL_SCOPE = describe_scope( 'global',
                               child_scopes = [ ISLAND_SCOPE ] )


LEVEL_GAME_SCOPE.add_objects( [
        describe_object( 'level', attributes = [
            int_attribute( 'ballsrequired', default = 0, allow_empty = True, mandatory = True, min_value = 0 ),
            bool_attribute( 'letterboxed', init = False, mandatory = True ),
            bool_attribute( 'visualdebug', init = False, mandatory = True ),
            bool_attribute( 'autobounds', init = True, mandatory = True ),
            rgb_attribute( 'textcolor', init = (255,255,255), mandatory = True ),
            real_attribute( 'timebugprobability', init = 0, min_value = 0, mandatory = True ),
            bool_attribute( 'strandgeom', default = False ),
            bool_attribute( 'allowskip', default = True, allow_empty = True ),
            bool_attribute( 'texteffects', default = False ),
            rgb_attribute( 'cursor1color', default = (255,255,255) ),
            rgb_attribute( 'cursor2color', default = (255,255,255) ),
            rgb_attribute( 'cursor3color', default = (255,255,255) ),
            rgb_attribute( 'cursor4color', default = (255,255,255) ),
            ] ),
        describe_object( 'camera', attributes = [
            enum_attribute( 'aspect', values = ('widescreen', 'normal'), default = 'normal' ),
            xy_attribute( 'endpos' ),
            real_attribute( 'endzoom', min_value = 0.00001 ),
            ] ),
        describe_object( 'poi', attributes = [
            real_attribute( 'pause', min_value = 0, init = 0 ),
            xy_attribute( 'pos', init = (0,0) ),
            real_attribute( 'traveltime', min_value = 0, init = 0 ),
            real_attribute( 'zoom', min_value = 0.00001, init = 0.408 )
            ] ),
        describe_object( 'signpost', attributes = [
            real_attribute( 'alpha', min_value = 0, max_value = 1, init = 1, mandatory = True ),
            rgb_attribute( 'colorize', init = (255,255,255), mandatory = True ),
            real_attribute( 'depth', init = 0, mandatory = True ),
            string_attribute( 'name', init = 'SIGN_POST_', mandatory = 'True' ),
            # @todo makes x,y a composite attribute
            real_attribute( 'x', init = 0, mandatory = True ),
            real_attribute( 'y', init = 0, mandatory = True ),
            angle_degrees_attribute( 'rotation', init = 0, mandatory = True ),
            # @todo makes scalex,scaley a composite attribute
            real_attribute( 'scalex', init = 1, min_value = 0.0000001, mandatory = True ),
            real_attribute( 'scaley', init = 1, min_value = 0.0000001, mandatory = True ),
            reference_attribute( 'text', referenced_familly = 'text', reference_scope = LEVEL_SCOPE, init = '', mandatory = True ),
            reference_attribute( 'particles', referenced_familly = 'effect', reference_scope = GLOBAL_SCOPE )
            ] )
        ] )

