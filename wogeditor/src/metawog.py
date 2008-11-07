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
IDENTIFIER_TYPE = 'identifier'


class AttributeDesc(object):
    def __init__( self, name, type, init = None, default = None, allow_empty = False, mandatory = False ):
        self.name = name
        self.type = type
        self.init = init
        self.default = default
        self.allow_empty = allow_empty
        self.mandatory = mandatory
        self.object_desc = None

    def attach_to_object_desc( self, object_desc ):
        self.object_desc = object_desc

    def __repr__( self ):
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
    def __init__( self, name, reference_familly, reference_scope, **kwargs ):
        AttributeDesc.__init__( self, name, REFERENCE_TYPE, **kwargs )
        self.reference_familly = reference_familly
        self.reference_scope = reference_scope

    def attach_to_object_desc( self, object_desc ):
        AttributeDesc.attach_to_object_desc( self, object_desc )
        object_desc._add_reference_attribute( self )

class IdentifierAttributeDesc(AttributeDesc):
    def __init__( self, name, reference_familly, reference_scope, **kwargs ):
        AttributeDesc.__init__( self, name, IDENTIFIER_TYPE, **kwargs )
        self.reference_familly = reference_familly
        self.reference_scope = reference_scope

    def attach_to_object_desc( self, object_desc ):
        AttributeDesc.attach_to_object_desc( self, object_desc )
        object_desc._set_identifier_attribute( self )

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

def reference_attribute( name, reference_familly, reference_scope, **kwargs ):
    return ReferenceAttributeDesc( name, reference_familly = reference_familly, reference_scope = reference_scope, **kwargs )

def identifier_attribute( name, reference_familly, reference_scope, **kwargs ):
    return IdentifierAttributeDesc( name, reference_familly, reference_scope, **kwargs )


class ObjectDesc(object):
    def __init__( self, tag, attributes = None ):
        self.tag = tag
        attributes = attributes or []
        self.attributes_order = [ attribute.name for attribute in attributes ]
        self.attributes_by_name = {}
        self.identifier_attribute = None
        self.reference_attributes = set()
        self.add_attributes( attributes )

    def add_attributes( self, attributes ):
        for attribute in attributes:
            assert attribute.name not in self.attributes_by_name, attribute.name
            self.attributes_by_name[attribute.name] = attribute
            attribute.attach_to_object_desc( self )

    def get_attribute_desc( self, attribute_name ):
        return self.attributes_by_name.get( attribute_name )

    def _add_reference_attribute( self, attribute_desc ):
        assert attribute_desc not in self.reference_attributes
        self.reference_attributes.add( attribute_desc )

    def _set_identifier_attribute( self, attribute_desc ):
        assert self.identifier_attribute is None
        self.identifier_attribute = attribute_desc

    def __repr__( self ):
        return '%s(tag=%s, attributes=[%s])' % (self.__class__.__name__, self.tag, ','.join(self.attributes_order))

def describe_object( tag, attributes = None ):
    return ObjectDesc( tag, attributes )

class ScopeDesc(object):
    def __init__( self, scope_name, objects_desc = None, child_scopes = None ):
        objects_desc = objects_desc or []
        child_scopes = child_scopes or []
        self.parent_scope = None
        self.child_scopes = []
        self.add_child_scopes( child_scopes )
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
        for scope in child_scopes:
            scope.parent_scope = self

    def get_attribute_desc( self, tag, attribute_name ):
        """Returns the attribute desc declared for the specified tag."""
        object_desc = self.objects_by_tag.get( tag )
        if object_desc:
            return object_desc.get_attribute_desc( attribute_name )
        return None

    def __repr__( self ):
        return '%s(name=%s, attributes=[%s])' % (self.__class__.__name__, self.scope_name, ','.join(self.objects_by_tag.keys()))

def describe_scope( scope_name, objects_desc = None, child_scopes = None ):
    return ScopeDesc( scope_name, objects_desc )

class ReferenceTracker(object):
    """The reference trackers keep that of all object identifiers to check for reference validity and identifier unicity.
       It keeps track of all object identifiers per familly and scope.
       It keeps track of all references on a given object familly/identifier (to easily rename for example).
    """
    def __init__( self ):
        self.scopes_by_key = {} # (scope_desc, parent_scope_key) by scope_key
        self.ref_by_scope_and_familly = {} # dict( (scope_key,familly): dict(id: object_key) )
        self.back_references = {} # dict( (familly,identifier) : set(scope_key,object_key,attribute_desc)] )

    # Mutators
    def scope_added( self, scope_key, scope_desc, parent_scope_key ):
        assert scope_key not in self.scopes_by_key
        self.scopes_by_key[scope_key] = (scope_desc, parent_scope_key)
    
    def scope_about_to_be_removed( self, scope_key ):
        del self.scopes_by_key[scope_key]

    def object_added( self, scope_key, object_key, object_desc, attribute_retriever ):
        """Declares object identifier and track referenced objects."""
        # Checks if the object has any identifier attribute
        identifier_desc = object_desc.identifier_attribute
        if identifier_desc:
            identifier_value = attribute_retriever( scope_key, object_key, identifier_desc )
            self._register_object_identifier( scope_key, object_key, identifier_desc, identifier_value )
        # Checks object for all reference attributes
        for attribute_desc in object_desc.reference_attributes:
            reference_value = attribute_retriever( scope_key, object_key, attribute_desc )
            self._register_object_reference( scope_key, object_key, attribute_desc, reference_value )

    def _register_object_identifier( self, scope_key, object_key, identifier_desc, identifier_value ):
        if identifier_value is not None:
            references = self.ref_by_scope_and_familly.get( (scope_key,identifier_desc.reference_familly) )
            if references is None:
                references = {}
                self.ref_by_scope_and_familly[ (scope_key,identifier_desc.reference_familly) ] = references
            references[identifier_value] = object_key

    def _register_object_reference( self, scope_key, object_key, attribute_desc, reference_value ):
        if reference_value is not None:
            back_reference_key = (attribute_desc.reference_familly, reference_value)
            back_references = self.back_references.get( back_reference_key )
            if back_references is None:
                back_references = set()
                self.back_references[back_reference_key] = back_references
            back_references.add( (scope_key, object_key, attribute_desc) )

    def object_about_to_be_removed( self, scope_key, object_key, object_desc, attribute_retriever ):
        # Checks if the object has any identifier attribute
        identifier_desc = object_desc.identifier_attribute
        if identifier_desc:
            identifier_value = attribute_retriever( scope_key, object_key, identifier_desc )
            self._unregister_object_identifier( scope_key, object_key, identifier_desc, identifier_value )
        # Checks object for all reference attributes
        for attribute_desc in object_desc.reference_attributes:
            reference_value = attribute_retriever( scope_key, object_key, attribute_desc )
            self._unregister_object_reference( scope_key, object_key, attribute_desc, reference_value )

    def _unregister_object_identifier( self, scope_key, object_key, identifier_desc, identifier_value ):
        if identifier_value is not None:
            references = self.ref_by_scope_and_familly.get( (scope_key,identifier_desc.reference_familly) )
            if references:
                del references[identifier_value]

    def _unregister_object_reference( self, scope_key, object_key, attribute_desc, reference_value ):
        if reference_value is not None:
            back_reference_key = (attribute_desc.reference_familly, reference_value)
            back_references = self.back_references.get( back_reference_key )
            if back_references:
                back_references.remove( (scope_key, object_key, attribute_desc) )

    def attribute_updated( self, scope_key, object_key, attribute_desc, old_value, new_value ):
        object_desc = attribute_desc.object_desc
        identifier_desc = object_desc.identifier_attribute
        if identifier_desc is attribute_desc:
            self._unregister_object_identifier( scope_key, object_key, identifier_desc, old_value )
            self._register_object_identifier( scope_key, object_key, identifier_desc, new_value )
        if attribute_desc in object_desc.reference_attributes:
            self._unregister_object_reference( scope_key, object_key, attribute_desc, old_value )
            self._register_object_reference( scope_key, object_key, attribute_desc, new_value )

    # Queries
    def is_valid_reference( self, scope_key, attribute_desc, attribute_value ):
        references = self.ref_by_scope_and_familly.get( (scope_key,attribute_desc.reference_familly) )
        if references is None or attribute_value not in references:
            scope_desc, parent_scope_key = self.scopes_by_key[scope_key]
            if parent_scope_key is not None:
                return self.is_valid_reference( parent_scope_key, attribute_desc, attribute_value )
            return False
        return True

    def list_identifiers( self, scope_key, familly ):
        """Returns a list all identifiers for the specified familly in the specified scope and its parent scopes."""
        identifiers = self.ref_by_scope_and_familly.get( (scope_key, familly), {} ).keys()
        scope_desc, parent_scope_key = self.scopes_by_key[scope_key]
        if parent_scope_key is not None:
            identifiers.extend( self.list_identifiers( parent_scope_key, familly ) )
        return identifiers

    def list_references( self, familly, identifier ):
        """Returns a list of (scope_key,object_key,attribute_desc) object attributes that reference the specified identifier."""
##        import pprint
##        pprint.pprint( self.back_references )
##        print 'Searching', familly, identifier
        return list( self.back_references.get( (familly, identifier), [] ) )
        

# Declares the scope hierarchy
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
            reference_attribute( 'text', reference_familly = 'text', reference_scope = LEVEL_SCOPE, init = '', mandatory = True ),
            reference_attribute( 'particles', reference_familly = 'effect', reference_scope = GLOBAL_SCOPE )
            ] ),
        describe_object( 'pipe', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'pipe',
                                  reference_scope = LEVEL_SCOPE, init ='exitPipe' ),
            real_attribute( 'depth', init = 0, mandatory = True ),
            enum_attribute( 'type', values = ('', 'BEAUTY', 'BLACK', 'ISH'), init = '', mandatory = True )
            ] ),
        describe_object( 'Vertex', attributes = [   # @todo restrict parent tag
            # @todo makes x,y a composite attribute
            real_attribute( 'x', init = 0, mandatory = True ),
            real_attribute( 'y', init = 0, mandatory = True ),
            ] ),
        describe_object( 'BallInstance', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'BallInstance',
                                  reference_scope = LEVEL_SCOPE, init ='1' ),
            string_attribute( 'type', mandatory = True, init = 'common' ),  # @todo makes this a reference
            # @todo makes x,y a composite attribute
            real_attribute( 'x', init = 0, mandatory = True ),
            real_attribute( 'y', init = 0, mandatory = True ),
            angle_degrees_attribute( 'angle', init = 0, mandatory = True ),
            real_attribute( 'depth', init = 0, mandatory = True ),
            bool_attribute( 'discovered', init = 'true', mandatory = True )
            ] ),
        describe_object( 'Strand', attributes = [
            reference_attribute( 'gb1', reference_familly = 'BallInstance', reference_scope = LEVEL_SCOPE,
                                 init = '', mandatory = True ),
            reference_attribute( 'gb2', reference_familly = 'BallInstance', reference_scope = LEVEL_SCOPE,
                                 init = '', mandatory = True )
            ] )
        ] )




if __name__ == "__main__":
    import unittest

    TEST_GLOBAL_SCOPE = describe_scope( 'global' )

    TEST_LEVEL_SCOPE = describe_scope( 'global.level' )

    GLOBAL_TEXT = describe_object( 'text', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'text',
                              reference_scope = TEST_GLOBAL_SCOPE ),
        string_attribute( 'fr' )
        ] )


    TEST_GLOBAL_SCOPE.add_objects( [ GLOBAL_TEXT ] )

    LEVEL_TEXT = describe_object( 'text', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'text',
                              reference_scope = TEST_GLOBAL_SCOPE ),
        string_attribute( 'fr' )
        ] )
    
    LEVEL_SIGN = describe_object( 'sign', attributes = [
        reference_attribute( 'text', reference_familly = 'text',
                             reference_scope = TEST_LEVEL_SCOPE, init = '', mandatory = True ),
        reference_attribute( 'alt_text', reference_familly = 'text',
                             reference_scope = TEST_LEVEL_SCOPE )
        ] )

    TEST_LEVEL_SCOPE.add_objects( [ LEVEL_TEXT, LEVEL_SIGN ] )

    class TestScope(object):
        data = {}
        objects_desc = {}

        def __init__( self, tracker, name ):
            self.tracker = tracker
            self.name = name

        def add_object( self, key, object_desc, **attributes ):
            self.data[key] = attributes
            self.objects_desc[key] = object_desc
            self.tracker.object_added( self, key, object_desc, self._retrieve_attribute )

        def remove_object( self, key ):
            self.tracker.object_about_to_be_removed( self, key, self.objects_desc[key], self._retrieve_attribute )
            del self.data[key]
            del self.objects_desc[key]

        def update_attribute( self, key, **attributes ):
            object_desc = self.objects_desc[key]
            for name, new_value in attributes.iteritems():
                old_value = self.data[key].get( name )
                self.data[key][name] = new_value
                self.tracker.attribute_updated( self, key, object_desc.attributes_by_name[name],
                                                old_value, new_value )

        def _retrieve_attribute( self, scope_key, object_key, attribute_desc ):
            object = scope_key.data.get(object_key)
            if object:
                return object.get(attribute_desc.name)
            return None

        def __repr__( self ):
            return 'TestScope<%s>' % self.name


    class Test(unittest.TestCase):

        def test_identifiers(self):
            tracker = ReferenceTracker()
            global_scope = TestScope(tracker,'global')
            tracker.scope_added( global_scope, TEST_GLOBAL_SCOPE, None )
            level1_scope = TestScope(tracker,'level1')
            tracker.scope_added( level1_scope, TEST_LEVEL_SCOPE, global_scope )
            # add objects
            global_scope.add_object( 'hello', GLOBAL_TEXT, id = 'TEXT_HELLO', fr = 'bonjour' )
            level1_scope.add_object( 'hi', LEVEL_TEXT, id = 'TEXT_HI', fr = 'salut' )
            # check
            self.assert_( tracker.is_valid_reference( global_scope,
                                                      LEVEL_SIGN.attributes_by_name['text'],
                                                      'TEXT_HELLO' ) )
            self.assert_( tracker.is_valid_reference( level1_scope,
                                                      LEVEL_SIGN.attributes_by_name['text'],
                                                      'TEXT_HELLO' ) )
            self.assert_( tracker.is_valid_reference( level1_scope,
                                                      LEVEL_SIGN.attributes_by_name['text'],
                                                      'TEXT_HI' ) )
            self.failIf( tracker.is_valid_reference( global_scope,
                                                     LEVEL_SIGN.attributes_by_name['text'],
                                                     'TEXT_HI' ) )
            self.assertEqual( ['TEXT_HELLO'], tracker.list_identifiers( global_scope, 'text' ) )
            self.assertEqual( sorted(['TEXT_HELLO','TEXT_HI']),
                              sorted(tracker.list_identifiers( level1_scope, 'text' )) )
            # update global hello object attribute
            global_scope.update_attribute( 'hello', id='TEXT_HELLO_NEW', fr='bonjour new' )
            # check
            self.failIf( tracker.is_valid_reference( global_scope,
                                                     LEVEL_SIGN.attributes_by_name['text'],
                                                     'TEXT_HELLO' ) )
            self.failIf( tracker.is_valid_reference( level1_scope,
                                                     LEVEL_SIGN.attributes_by_name['text'],
                                                     'TEXT_HELLO' ) )
            self.assert_( tracker.is_valid_reference( global_scope,
                                                      LEVEL_SIGN.attributes_by_name['text'],
                                                      'TEXT_HELLO_NEW' ) )
            self.assert_( tracker.is_valid_reference( level1_scope,
                                                      LEVEL_SIGN.attributes_by_name['text'],
                                                      'TEXT_HELLO_NEW' ) )
            self.assertEqual( ['TEXT_HELLO_NEW'], tracker.list_identifiers( global_scope, 'text' ) )
            self.assertEqual( sorted(['TEXT_HELLO_NEW','TEXT_HI']),
                              sorted(tracker.list_identifiers( level1_scope, 'text' )) )
            # remove object
            global_scope.remove_object( 'hello' )
            # check
            self.failIf( tracker.is_valid_reference( level1_scope,
                                                     LEVEL_SIGN.attributes_by_name['text'],
                                                     'TEXT_HELLO_NEW' ) )
            self.assertEqual( sorted(['TEXT_HI']),
                              sorted(tracker.list_identifiers( level1_scope, 'text' )) )

        def test_back_references(self):
            tracker = ReferenceTracker()
            global_scope = TestScope(tracker,'global')
            tracker.scope_added( global_scope, TEST_GLOBAL_SCOPE, None )
            level1_scope = TestScope(tracker,'level1')
            tracker.scope_added( level1_scope, TEST_LEVEL_SCOPE, global_scope )
            level2_scope = TestScope(tracker,'level2')
            tracker.scope_added( level2_scope, TEST_LEVEL_SCOPE, global_scope )
            # add objects
            global_scope.add_object( 'hello', GLOBAL_TEXT, id = 'TEXT_HELLO', fr = 'bonjour' )
            level1_scope.add_object( 'hi', LEVEL_TEXT, id = 'TEXT_HI', fr = 'salut' )
            for level_scope in (level1_scope, level2_scope):
                level_scope.add_object( 'sign1', LEVEL_SIGN, text = 'TEXT_HI' )
                level_scope.add_object( 'sign2', LEVEL_SIGN, text = 'TEXT_HELLO' )
            level1_scope.add_object( 'sign3', LEVEL_SIGN, text = 'TEXT_HI' )
            level2_scope.add_object( 'sign4', LEVEL_SIGN, text = 'TEXT_HELLO', alt_text = 'TEXT_HELLO' )
            # check
            level_text_attribute = LEVEL_SIGN.attributes_by_name['text']
            level_alt_text_attribute = LEVEL_SIGN.attributes_by_name['alt_text']
            self.assertEqual( sorted([ (level1_scope, 'sign2', level_text_attribute),
                                       (level2_scope, 'sign2', level_text_attribute),
                                       (level2_scope, 'sign4', level_text_attribute),
                                       (level2_scope, 'sign4', level_alt_text_attribute) ]),
                              sorted(tracker.list_references( 'text', 'TEXT_HELLO' )) )
            self.assertEqual( sorted([ (level1_scope, 'sign1', level_text_attribute),
                                       (level2_scope, 'sign1', level_text_attribute),
                                       (level1_scope, 'sign3', level_text_attribute) ]),
                              sorted(tracker.list_references( 'text', 'TEXT_HI' )) )
            # remove object
            level2_scope.remove_object( 'sign4' )
            self.assertEqual( sorted([ (level1_scope, 'sign2', level_text_attribute),
                                       (level2_scope, 'sign2', level_text_attribute) ]),
                              sorted(tracker.list_references( 'text', 'TEXT_HELLO' )) )
            # update objects
            level1_scope.update_attribute( 'sign2', text='TEXT_HI' )
            level1_scope.update_attribute( 'sign3', text='TEXT_HELLO' )
            # check
            self.assertEqual( sorted([ (level2_scope, 'sign2', level_text_attribute),
                                       (level1_scope, 'sign3', level_text_attribute) ]),
                              sorted(tracker.list_references( 'text', 'TEXT_HELLO' )) )
            self.assertEqual( sorted([ (level1_scope, 'sign1', level_text_attribute),
                                       (level2_scope, 'sign1', level_text_attribute),
                                       (level1_scope, 'sign2', level_text_attribute) ]),
                              sorted(tracker.list_references( 'text', 'TEXT_HI' )) )

    unittest.main()
