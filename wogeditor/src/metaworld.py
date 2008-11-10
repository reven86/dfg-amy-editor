"""Describes the structure and constraints of objects used in data file of WOG."""
import xml.etree.ElementTree


# Different type of attributes

BOOLEAN_TYPE = 'boolean'
INTEGER_TYPE = 'integer'
REAL_TYPE = 'real'
RGB_COLOR_TYPE = 'rgb_color'
ARGB_COLOR_TYPE = 'argb_color'
XY_TYPE = 'xy'
ENUMERATED_TYPE = 'enumerated'
STRING_TYPE = 'string'
ANGLE_DEGREES_TYPE = 'angle.degrees'
ANGLE_RADIANS_TYPE = 'angle.radians'
REFERENCE_TYPE = 'reference'
IDENTIFIER_TYPE = 'identifier'
PATH_TYPE = 'path'


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

class PathAttributeDesc(AttributeDesc):
    def __init__( self, name, strip_extension = None, **kwargs ):
        AttributeDesc.__init__( self, name, PATH_TYPE, **kwargs )
        self.strip_extension = strip_extension

def bool_attribute( name, **kwargs ):
    return AttributeDesc( name, BOOLEAN_TYPE, **kwargs )

def int_attribute( name, min_value = None, **kwargs ):
    return NumericAttributeDesc( name, INTEGER_TYPE, min_value = min_value, **kwargs )

def real_attribute( name, min_value = None, max_value = None, **kwargs ):
    return NumericAttributeDesc( name, REAL_TYPE, min_value = min_value, max_value = max_value, **kwargs )

def rgb_attribute( name, **kwargs ):
    return ColorAttributeDesc( name, RGB_COLOR_TYPE, components = 3, **kwargs )

def argb_attribute( name, **kwargs ):
    return ColorAttributeDesc( name, ARGB_COLOR_TYPE, components = 4, **kwargs )

def xy_attribute( name, **kwargs ):
    return Vector2DAttributeDesc( name, XY_TYPE, **kwargs )

def enum_attribute( name, values, **kwargs ):
    return EnumeratedAttributeDesc( name, values, **kwargs )

def string_attribute( name, **kwargs ):
    return AttributeDesc( name, STRING_TYPE, **kwargs )

def angle_degrees_attribute( name, min_value = None, max_value = None, **kwargs ):
    return NumericAttributeDesc( name, ANGLE_DEGREES_TYPE, min_value = min_value, max_value = max_value, **kwargs )

def angle_radians_attribute( name, min_value = None, max_value = None, **kwargs ):
    return NumericAttributeDesc( name, ANGLE_RADIANS_TYPE, min_value = min_value, max_value = max_value, **kwargs )

def reference_attribute( name, reference_familly, reference_scope, **kwargs ):
    return ReferenceAttributeDesc( name, reference_familly = reference_familly, reference_scope = reference_scope, **kwargs )

def identifier_attribute( name, reference_familly, reference_scope, **kwargs ):
    return IdentifierAttributeDesc( name, reference_familly, reference_scope, **kwargs )

def path_attribute( name, **kwargs ):
    return PathAttributeDesc( name, **kwargs )



class ObjectsDescOwner:
    def __init__( self, objects_desc = None ):
        objects_desc = objects_desc or []
        self.__scope = None
        self.objects_by_tag = {}
        self.add_objects( objects_desc )

    @property
    def scope( self ):
        return self.__scope

    def _set_scope( self, parent_scope ):
        if self.__scope is not parent_scope: # avoid cycle
            self.__scope = parent_scope
            for object_desc in self.objects_by_tag.itervalues():
                object_desc._set_scope( parent_scope )

    def add_objects( self, objects_desc ):
        for object_desc in objects_desc:
            assert object_desc.tag not in self.objects_by_tag, object_desc.tag
            self.objects_by_tag[object_desc.tag] = object_desc
            object_desc._set_scope( self.__scope )
            self._object_added( object_desc )

    def _object_added( self, object_desc ):
        raise NotImplemented()


class ObjectDesc(ObjectsDescOwner):
    """A object description represents a tag that belong in a given file. Its main features are:
       - a tag name
       - a list of attribute description
       - zero or more parent object description
       - a minimum number of occurrences when it occurs in a parent object
       - a conceptual file it may appears in
    """
    def __init__( self, tag, objects_desc = None, attributes = None, min_occurrence = None ):
        ObjectsDescOwner.__init__( self, objects_desc = objects_desc or [] )
        self.tag = tag
        attributes = attributes or []
        self.attributes_order = []
        self.attributes_by_name = {}
        self.parent_objects = set() # An object may be added as child of multiple objects if they are in the same file
        self.identifier_attribute = None
        self.reference_attributes = set()
        self.file = None # initialized when object or parent object is added to a file
        self.child_objects_by_tag = {}
        self.min_occurrence = min_occurrence or 0
        self.add_attributes( attributes )

    def add_attributes( self, attributes ):
        for attribute in attributes:
            assert attribute.name not in self.attributes_by_name, attribute.name
            self.attributes_by_name[attribute.name] = attribute
            attribute.attach_to_object_desc( self )
        self.attributes_order.extend( attributes )

    def _add_reference_attribute( self, attribute_desc ):
        assert attribute_desc not in self.reference_attributes
        self.reference_attributes.add( attribute_desc )

    def _set_identifier_attribute( self, attribute_desc ):
        assert self.identifier_attribute is None
        self.identifier_attribute = attribute_desc

    def _set_file( self, file_desc ):
        if self.file is not file_desc: # avoid cycle
            self.file = file_desc
            for object_desc in self.objects_by_tag.itervalues():
                object_desc._set_file( file_desc )

    def _object_added( self, object_desc ):
        object_desc.parent_objects.add( self )

    def __repr__( self ):
        return '%s(tag=%s, attributes=[%s], objects=[%s])' % (
            self.__class__.__name__, self.tag, ','.join([a.name for a in self.attributes_order]),
            ','.join(self.objects_by_tag.keys()))

def describe_object( tag, attributes = None, objects = None, min_occurrence = None ):
    return ObjectDesc( tag, attributes = attributes, objects_desc = objects, min_occurrence = min_occurrence )

class FileDesc(ObjectsDescOwner):
    def __init__( self, conceptual_file_name, objects = None ):
        ObjectsDescOwner.__init__( self, objects_desc = objects or [] )
        self.name = conceptual_file_name

    def _object_added( self, object_desc ):
        object_desc._set_file( self )

    def __repr__( self ):
        return '%s(name=%s, objects=[%s])' % (self.__class__.__name__, self.name, ','.join(self.objects_by_tag.keys()))

def describe_file( conceptual_file_name, objects = None ):
    return FileDesc( conceptual_file_name, objects = objects )

class ScopeDesc(object):
    def __init__( self, scope_name, files_desc = None, child_scopes = None ):
        child_scopes = child_scopes or []
        self.scope_name = scope_name
        self.parent_scope = None
        self.child_scopes = []
        self.files_desc_by_name = {}
        self.__objects_by_tag = None
        self.add_child_scopes( child_scopes )
        self.add_files_desc( files_desc )

    @property
    def objects_by_tag( self ):
        if self.__objects_by_tag is None:
            self.__objects_by_tag = {}
            for file_desc in self.files_desc_by_name.itervalues():
                self.__objects_by_tag.update( file_desc.objects_by_tag )
        return self.__objects_by_tag

    def add_child_scopes( self, child_scopes ):
        self.child_scopes.extend( child_scopes )
        for scope in child_scopes:
            scope.parent_scope = self

    def add_files_desc( self, files_desc ):
        for file_desc in files_desc:
            assert file_desc.name not in self.files_desc_by_name
            self.files_desc_by_name[file_desc.name] = file_desc
            file_desc._set_scope( self )

    def __repr__( self ):
        return '%s(name=%s, files=[%s])' % (self.__class__.__name__, self.scope_name, ','.join(self.files_desc_by_name.keys()))

def describe_scope( scope_name, files_desc = None, child_scopes = None ):
    return ScopeDesc( scope_name, files_desc = files_desc, child_scopes = child_scopes )

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
##        print 'REF: object_added', object_key
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
##        print '=> registering "%s" with identifier: "%s"' % (object_key, repr(identifier_value))
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
##        print 'REF: object_about_to_be_removed', object_key
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
##        print '=> unregistering "%s" with identifier: "%s"' % (object_key, repr(identifier_value))
        if identifier_value is not None:
            references = self.ref_by_scope_and_familly.get( (scope_key,identifier_desc.reference_familly) )
            if references:
                try:
                    del references[identifier_value]
                except KeyError:    # May happens in case of multiple image with same identifier (usually blank)
                    pass            # since unicity is not validated yet

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
        



if __name__ == "__main__":
    import unittest

    TEST_GLOBAL_FILE = describe_file( 'testglobal' )
    TEST_LEVEL_FILE = describe_file( 'testlevel', objects = [
        describe_object( 'inline' )
        ] )

    TEST_GLOBAL_SCOPE = describe_scope( 'testscope', files_desc = [TEST_GLOBAL_FILE] )

    TEST_LEVEL_SCOPE = describe_scope( 'testscope.level', files_desc = [TEST_LEVEL_FILE] )

    GLOBAL_TEXT = describe_object( 'text', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'text',
                              reference_scope = TEST_GLOBAL_SCOPE ),
        string_attribute( 'fr' )
        ] )


    TEST_GLOBAL_FILE.add_objects( [ GLOBAL_TEXT ] )

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
        ], objects = [ LEVEL_TEXT ] )

    TEST_LEVEL_FILE.add_objects( [ LEVEL_TEXT, LEVEL_SIGN ] )

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

        def test_descriptions( self ):
            self.assertEqual( sorted(['text', 'sign', 'inline']), sorted(TEST_LEVEL_SCOPE.objects_by_tag.keys()) )
            for scope in (TEST_LEVEL_SCOPE, TEST_GLOBAL_SCOPE):
                for object_desc in scope.objects_by_tag.itervalues():
                    self.assertEqual( scope, object_desc.scope )
                for file_desc in scope.files_desc_by_name.itervalues():
                    self.assertEqual( scope, object_desc.scope )
            self.assertEqual( sorted([LEVEL_SIGN]), sorted(LEVEL_TEXT.parent_objects) )
            for file, objects in { TEST_GLOBAL_FILE: [GLOBAL_TEXT],
                                   TEST_LEVEL_FILE: [LEVEL_TEXT, LEVEL_SIGN] }.iteritems():
                for object in objects:
                    self.assertEqual( file, object.file )
                    self.assert_( object in file.objects_by_tag.values() )
                    self.assert_( object.tag in file.objects_by_tag )
                    self.assert_( object.tag in file.scope.objects_by_tag )

    unittest.main()
