"""Provides a way to describe a graph of objects, that may be linked together.

Objects live in a given scope. Scopes are organized as a hierarchy: scope children may see their parent objects,
but the parent scope can not see the child objects.

Typically, their is a global scope with resources common to all levels, and each level has its own scope.
This allows each level to define objects with identifiers that would conflict with object defined in other
levels if scope were not used.

While objects live in a scope, they are attached to a given "file" in that scope. A scope can contain multiple
files, but each file can only have one root object.

The structure of the graph of objects is defined statically:
- structure of the scope kind hierarchy
- kind of file attached to each kind of scope
- root object description attached to each file
- for each object description, its possible child object description, and its attribute description.

Object description can define constraint such as the minimum or maximum number of occurrences of the object in its parent.
Attribute description can indicate if the attribute is mandatory, its value domain, typical initial value, type...
"""
import xml.etree.ElementTree
# Publish/subscribe framework
# See http://louie.berlios.de/ and http://pydispatcher.sf.net/
import louie 


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
    def __init__( self, name, attribute_type, init = None, default = None, 
                  allow_empty = False, mandatory = False ):
        self.name = name
        self.type = attribute_type
        if init is not None:
            init = str(init)
        self.init = init
        self.default = default
        self.allow_empty = allow_empty
        self.mandatory = mandatory
        self.object_desc = None

    def attach_to_object_desc( self, object_desc ):
        self.object_desc = object_desc

    def get( self, element ):
        return element.get( self.name )

    def set( self, element, value ):
        return element.set( self.name, value )

    def __repr__( self ):
        return '%s(name=%s, type=%s, mandatory=%s)' % (self.__class__.__name__, self.name, self.type, self.mandatory)

class NumericAttributeDesc(AttributeDesc):
    def __init__( self, name, attribute_type, min_value = None, max_value = None, **kwargs ):
        AttributeDesc.__init__( self, name, attribute_type, **kwargs )
        self.min_value = min_value
        self.max_value = max_value

class ColorAttributeDesc(AttributeDesc):
    def __init__( self, name, attribute_type, components, **kwargs ):
        AttributeDesc.__init__( self, name, attribute_type, **kwargs )
        self.nb_components = components

class Vector2DAttributeDesc(AttributeDesc):
    def __init__( self, name, attribute_type, **kwargs ):
        AttributeDesc.__init__( self, name, attribute_type, **kwargs )

class EnumeratedAttributeDesc(AttributeDesc):
    def __init__( self, name, values, is_list = False, **kwargs ):
        AttributeDesc.__init__( self, name, ENUMERATED_TYPE, **kwargs )
        self.values = set( values )
        self.is_list = is_list

class BooleanAttributeDesc(EnumeratedAttributeDesc):
    def __init__( self, name, **kwargs ):
        EnumeratedAttributeDesc.__init__( self, name, ('true','false'), BOOLEAN_TYPE, **kwargs )

class ReferenceAttributeDesc(AttributeDesc):
    def __init__( self, name, reference_family, reference_scope, **kwargs ):
        AttributeDesc.__init__( self, name, REFERENCE_TYPE, **kwargs )
        self.reference_family = reference_family
        self.reference_scope = reference_scope

    def attach_to_object_desc( self, object_desc ):
        AttributeDesc.attach_to_object_desc( self, object_desc )
        object_desc._add_reference_attribute( self )

class IdentifierAttributeDesc(AttributeDesc):
    def __init__( self, name, reference_family, reference_scope, **kwargs ):
        AttributeDesc.__init__( self, name, IDENTIFIER_TYPE, **kwargs )
        self.reference_family = reference_family
        self.reference_scope = reference_scope

    def attach_to_object_desc( self, object_desc ):
        AttributeDesc.attach_to_object_desc( self, object_desc )
        object_desc._set_identifier_attribute( self )

class PathAttributeDesc(AttributeDesc):
    def __init__( self, name, strip_extension = None, **kwargs ):
        AttributeDesc.__init__( self, name, PATH_TYPE, **kwargs )
        self.strip_extension = strip_extension

def bool_attribute( name, **kwargs ):
    return BooleanAttributeDesc( name, **kwargs )

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

def reference_attribute( name, reference_family, reference_scope, **kwargs ):
    return ReferenceAttributeDesc( name, reference_family = reference_family, reference_scope = reference_scope, **kwargs )

def identifier_attribute( name, reference_family, reference_scope, **kwargs ):
    return IdentifierAttributeDesc( name, reference_family, reference_scope, **kwargs )

def path_attribute( name, **kwargs ):
    return PathAttributeDesc( name, **kwargs )

unknown_attribute = string_attribute # to help with generated model

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

    def find_object_desc_by_tag( self, tag ):
        """Returns the ObjectDesc corresponding to the specified tag if found in the owner or its descendant.
           None if not found.
        """
        found_object_desc = self.objects_by_tag.get( tag )
        if not found_object_desc:
            for object_desc in self.objects_by_tag.itervalues():
                found_object_desc = object_desc.find_object_desc_by_tag( tag )
                if found_object_desc:
                    break
        return found_object_desc

    def find_immediate_child_by_tag( self, tag ):
        """Returns the ObjectDesc corresponding to the specified tag if found, otherwise returns None.
           Notes: only direct child are inspected. Grand-children will not be examined.
        """
        return self.objects_by_tag.get( tag )

    def all_descendant_object_descs( self ):
        """Returns a dict of all object desc found in the owner and all its descendant keyed by tag."""
        object_descs_by_tag = self.objects_by_tag.copy()
        for object_desc in self.objects_by_tag.itervalues():
            object_descs_by_tag.update( object_desc.all_descendant_object_descs() )
        return object_descs_by_tag

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
    def __init__( self, tag, objects_desc = None, attributes = None,
                  min_occurrence = None, max_occurrence = None,
                  read_only = False ):
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
        self.max_occurrence = max_occurrence or 2**32
        assert self.min_occurrence <= self.max_occurrence
        self.read_only = read_only
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

    def attribute_by_name( self, attribute_name ):
        """Retrieves the attribute description for the specified attribute_name.
           @exception KeyError if the element has no attribute named attribute_name.
        """ 
        return self.attributes_by_name[attribute_name]


    def __repr__( self ):
        return '%s(tag=%s, attributes=[%s], objects=[%s])' % (
            self.__class__.__name__, self.tag, ','.join([a.name for a in self.attributes_order]),
            ','.join(self.objects_by_tag.keys()))

def describe_object( tag, attributes = None, objects = None,
                     min_occurrence = None, max_occurrence = None, exact_occurrence = None,
                     read_only = False ):
    if exact_occurrence is not None:
        min_occurrence = exact_occurrence
        max_occurrence = exact_occurrence
    return ObjectDesc( tag, attributes = attributes, objects_desc = objects,
                       min_occurrence = min_occurrence, max_occurrence = max_occurrence,
                       read_only = read_only )

class FileDesc(ObjectsDescOwner):
    def __init__( self, conceptual_file_name, objects = None ):
        ObjectsDescOwner.__init__( self, objects_desc = objects or [] )
        self.name = conceptual_file_name
        assert len(self.objects_by_tag) <= 1

    def _object_added( self, object_desc ):
        assert len(self.objects_by_tag) <= 1
        object_desc._set_file( self )

    @property
    def root_object_desc( self ):
        """Returns the root object description of the file."""
        assert len(self.objects_by_tag) == 1
        return self.objects_by_tag.values()[0]

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
                self.__objects_by_tag.update( file_desc.all_descendant_object_descs() )
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
       It keeps track of all object identifiers per family and scope.
       It keeps track of all references on a given object family/identifier (to easily rename for example).
    """
    def __init__( self ):
        self.scopes_by_world = {} # (scope_desc, parent_scope_key) by scope_key
        self.ref_by_scope_and_family = {} # dict( (scope_key,family): dict(id: object_key) )
        self.back_references = {} # dict( (family,identifier) : set(scope_key,object_key,attribute_desc)] )

    # Mutators
    def scope_added( self, world ):
        assert world not in self.scopes_by_world
        self.scopes_by_world[world] = (world.meta, world.parent_world)
    
    def scope_about_to_be_removed( self, world ):
        del self.scopes_by_world[world]

    def object_added( self, element ):
        """Declares object identifier and track referenced objects."""
##        print 'REF: object_added', element
        world = element.world
        assert world is not None
        assert element is not None
        # Checks if the object has any identifier attribute
        identifier_desc = element.meta.identifier_attribute
        if identifier_desc:
            identifier_value = identifier_desc.get( element )
            self._register_object_identifier( world, element, identifier_desc, identifier_value )
        # Checks object for all reference attributes
        for attribute_desc in element.meta.reference_attributes:
            reference_value = attribute_desc.get( element )
            self._register_object_reference( world, element, attribute_desc, reference_value )

    def _register_object_identifier( self, scope_key, object_key, identifier_desc, identifier_value ):
##        print '=> registering "%s" with identifier: "%s"' % (object_key, repr(identifier_value))
        assert scope_key is not None
        assert object_key is not None
        if identifier_value is not None:
            # walk parents scopes until we find the right one.
            while self.scopes_by_world[scope_key][0] != identifier_desc.reference_scope:
                scope_key = self.scopes_by_world[scope_key][1]
            references = self.ref_by_scope_and_family.get( (scope_key,identifier_desc.reference_family) )
            if references is None:
                references = {}
                self.ref_by_scope_and_family[ (scope_key,identifier_desc.reference_family) ] = references
            references[identifier_value] = object_key

    def _register_object_reference( self, scope_key, object_key, attribute_desc, reference_value ):
        if reference_value is not None:
            back_reference_key = (attribute_desc.reference_family, reference_value)
            back_references = self.back_references.get( back_reference_key )
            if back_references is None:
                back_references = set()
                self.back_references[back_reference_key] = back_references
            back_references.add( (scope_key, object_key, attribute_desc) )

    def object_about_to_be_removed( self, element ):
##        print 'REF: object_about_to_be_removed', element
        scope_key = element.world
        assert scope_key is not None
        object_desc = element.meta
        # Checks if the object has any identifier attribute
        identifier_desc = object_desc.identifier_attribute
        if identifier_desc:
            identifier_value = identifier_desc.get( element )
            self._unregister_object_identifier( scope_key, element, identifier_desc, identifier_value )
        # Checks object for all reference attributes
        for attribute_desc in object_desc.reference_attributes:
            reference_value = attribute_desc.get( element )
            self._unregister_object_reference( scope_key, element, attribute_desc, reference_value )

    def _unregister_object_identifier( self, scope_key, object_key, identifier_desc, identifier_value ):
##        print '=> unregistering "%s" with identifier: "%s"' % (object_key, repr(identifier_value))
        if identifier_value is not None:
            references = self.ref_by_scope_and_family.get( (scope_key,identifier_desc.reference_family) )
            if references:
                try:
                    del references[identifier_value]
                except KeyError:    # May happens in case of multiple image with same identifier (usually blank)
                    pass            # since unicity is not validated yet

    def _unregister_object_reference( self, scope_key, object_key, attribute_desc, reference_value ):
        if reference_value is not None:
            back_reference_key = (attribute_desc.reference_family, reference_value)
            back_references = self.back_references.get( back_reference_key )
            if back_references:
                back_references.remove( (scope_key, object_key, attribute_desc) )

    def attribute_updated( self, object_key, attribute_desc, old_value, new_value ):
        scope_key = object_key.world
        assert scope_key is not None
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
        references = self.ref_by_scope_and_family.get( (scope_key,attribute_desc.reference_family) )
        if references is None or attribute_value not in references:
            scope_desc, parent_scope_key = self.scopes_by_world[scope_key]
            if parent_scope_key is not None:
                return self.is_valid_reference( parent_scope_key, attribute_desc, attribute_value )
            return False
        return True

    def list_identifiers( self, scope_key, family ):
        """Returns a list all identifiers for the specified family in the specified scope and its parent scopes."""
        identifiers = self.ref_by_scope_and_family.get( (scope_key, family), {} ).keys()
        scope_desc, parent_scope_key = self.scopes_by_world[scope_key]
        if parent_scope_key is not None:
            identifiers.extend( self.list_identifiers( parent_scope_key, family ) )
        return identifiers

    def list_references( self, family, identifier ):
        """Returns a list of (scope_key,object_key,attribute_desc) object attributes that reference the specified identifier."""
##        import pprint
##        pprint.pprint( self.back_references )
##        print 'Searching', family, identifier
        return list( self.back_references.get( (family, identifier), [] ) )
        

def print_scope( scope ):
    """Diagnostic function that print the full content of a Scope, including its files and objects."""
    print '* Scope:', scope.scope_name
    for child_scope in scope.child_scopes:
        print '  has child scope:', child_scope.scope_name
    for tree in scope.files_desc_by_name:
        print '  contained file:', tree
    print '  contains object:', ', '.join( sorted(scope.objects_by_tag) )
    for child_scope in scope.child_scopes:
        print_scope( child_scope )
        print
    for file_desc in scope.files_desc_by_name.itervalues():
        print_file_desc( file_desc )
        print

def print_file_desc( file_desc ):
    """Diagnostic function that print the full content of a FileDesc, including its objects."""
    print '* File:', file_desc.name
    print '  belong to scope:', file_desc.scope.scope_name
    print '  root object:', file_desc.root_object_desc.tag
    print '  contains object:', ', '.join( sorted(file_desc.all_descendant_object_descs()) )
    print '  object tree:'
    print_object_desc_tree( file_desc.root_object_desc, '        ' )

def print_object_desc_tree( element, indent ):
    """Diagnostic function that print the hierarchy of an ObjectDesc and its children."""
    suffix = ''
    if element.min_occurrence == element.max_occurrence:
        if element.min_occurrence > 1:
            suffix = '{%d}' % element.min_occurrence
    elif element.min_occurrence == 0:
        if element.max_occurrence == 1:
            suffix = '?'
        else:
            suffix = '*'
    elif element.min_occurrence == 1:
        suffix = '+'
    else:
        suffix = '{%d-%d}' % (element.min_occurrence, element.max_occurrence)
    print indent + element.tag + suffix
    for child_object in element.objects_by_tag.itervalues():
        print_object_desc_tree( child_object, indent + '    ' )




# SIGNALS
ELEMENT_ADDED = 'added'
ELEMENT_ABOUT_TO_BE_REMOVED = 'about_to_be_removed'
ELEMENT_ATTRIBUTE_UPDATED = 'updated'

class ElementAdded(louie.Signal):
    """Signal emitted when one element has been inserted into a tree or another element.
       The parent element/tree must be connected connected to a tree for
       the signal to be emitted.
       Signature: (parent_element, element, index_in_parent)
       parent_element: new parent Element of the element that has been added.
                       None if element is the root of the tree.
       element: Element that has been added.
       index_in_parent: zero-based index of insertion element in parent_element.
                        Always 0 if element is the root of the tree.
       Can retrieve the element tree via element.tree.   
    """

class ElementAboutToBeRemoved(louie.Signal):
    """Signal emitted when an element connected to a tree is about to be removed.
       Signature: (parent_element, element, index_in_parent)
       parent_element: parent Element of the element that will be removed.
                       None if element is the root of the tree.
       element: Element that will be removed.
       index_in_parent: zero-based index of insertion element in parent_element.
                        Always 0 if element is the root of the tree.  
    """

class AttributeUpdated(louie.Signal):
    """Signal emitted when an attribute of an element connected to a tree has been modified.
       Signature: (element, attribute_name, new_value, old_value )
       element: element that has been modified
       attribute_name: name of the attribute of the element that has been modified
       new_value: new value of the attribute. None if the attribute has been removed.
       old_value: old value of the attribute. None if the attribute has been added.
    """
    
class TreeAdded(louie.Signal):
    """Signal emitted when a tree has been added to a world connected to the universe.
       Signature: (tree)
       tree: tree that has been added to a world.
             Can retrieve the tree world & universe using tree.world and tree.universe.
    """
    
class TreeAboutToBeRemoved(louie.Signal):
    """Signal emitted when a tree is about to be removed from a world connected to the universe.
       Signature: (tree)
       tree: tree that is about to be removed from a world.
             Can retrieve the tree world & universe using tree.world and tree.universe.
    """

class WorldAdded(louie.Signal):
    """Signal emitted when a world is added to another world or the universe.
       Signature: (world)
       world: World that has been added. Can retrieve is parent world and universe from
              attributes.
    """
    
class WorldAboutToBeRemoved(louie.Signal):
    """Signal emitted when a world is about to be removed from another world or the universe.
       Signature: (world)
       world: World that is about to be removed. Can retrieve is parent world and universe from
              attributes.
    """
    

class WorldsOwner:
    def __init__( self ):
        self._worlds = {} # dict(desc: dict(key: world) )

    def all_child_worlds(self):
        worlds = []
        for world_data in self._worlds.itervalues():
            worlds.append( world_data.values() )
        return worlds
        
    def make_world( self, scope_desc, world_key = None, factory = None, *args, **kwargs ):
        """Creates a child World using the specified scoped_desc description and associating it with world_key.
           scope_desc: description of the world to instantiate.
           workd_key: a unique identifier for the world within the scope for worlds of the same kind.
           factory: Type to instantiate. Must be a subclass of World. Default is World.
                    Factory parameters are: (universe, scope_desc, key)
                    It will also be passed any extra parameters provided to the function.
        """
        #@todo check that scope_desc is an allowed child scope
        factory = factory or World
        world = factory( self.universe, scope_desc, world_key, #IGNORE:E1101 
                         *args, **kwargs ) 
        if scope_desc not in self._worlds:
            self._worlds[scope_desc] = {}
        assert world.key not in self._worlds[scope_desc]
        self._worlds[scope_desc][world.key] = world
        parent_world = self.universe != self and self or None #IGNORE:E1101
        world._attached_to_parent_world(parent_world)
        return world

    def remove_world(self, world):
        """Removes the specified child World from the World or Universe.
           exception: KeyError if the World does not belong.
        """
        # @todo
        assert world.key in self._worlds[world.meta]
        parent_world = self.universe != self and self or None #IGNORE:E1101
        world._about_to_be_detached_from_parent_world(parent_world)
        del self._worlds[world.meta][world.key]

    def find_world( self, scope_desc, world_key ):
        worlds_by_key = self._worlds.get( scope_desc, {} )
        return worlds_by_key.get( world_key )

    def list_worlds_of_type( self, scope_desc ):
        worlds_by_key = self._worlds.get( scope_desc, {} )
        return worlds_by_key.values()

    def list_world_keys( self, scope_desc ):
        worlds_by_key = self._worlds.get( scope_desc, {} )
        return worlds_by_key.keys()


class Universe(WorldsOwner):
    """Represents the universe where all elements, worlds and trees live in.
    """
    def __init__( self ):
        WorldsOwner.__init__( self )
        louie.connect( self._on_tree_added, TreeAdded )
        louie.connect( self._on_tree_about_to_be_removed, TreeAboutToBeRemoved )
        louie.connect( self._on_world_added, WorldAdded )
        louie.connect( self._on_world_about_to_be_removed, WorldAboutToBeRemoved )
        self.ref_by_world_and_family = {} # dict( (world,family): dict(id: element) )
        self.back_references = {} # dict( (family,identifier) : set(world,element,attribute_desc)] )

    @property
    def universe( self ):
        return self
            
    def _on_world_added(self, world):
        if world.universe == self:
            for tree in world.trees:
                self._on_tree_added(tree)
            for world in world.all_child_worlds():
                self._on_world_added(world)
    
    def _on_world_about_to_be_removed(self, world):
        if world.universe == self:
            for tree in world.trees:
                self._on_tree_about_to_be_removed(tree)
            for world in world.all_child_worlds():
                self._on_world_about_to_be_removed(world)

    def _on_tree_added(self, tree):
        if tree.universe == self:
            self._manage_tree_connections( tree, louie.connect )
            if tree.root is not None:
                self._on_element_added( tree.root, 0 )

    def _on_tree_about_to_be_removed(self, tree):
        if tree.universe == self:
            self._manage_tree_connections( tree, louie.disconnect )
            if tree.root is not None:
                self._on_element_about_to_be_removed( tree.root, 0 ) 
            
    def _manage_tree_connections(self, tree, connection_manager):
        connection_manager( self._on_element_added, ElementAdded, tree )
        connection_manager( self._on_element_about_to_be_removed, 
                            ElementAboutToBeRemoved, tree )
        connection_manager( self._on_element_updated, AttributeUpdated, tree )

    def _on_element_added(self, element, index_in_parent): #IGNORE:W0613
        assert isinstance(element,Element)
        assert index_in_parent >=0, index_in_parent
        
        # Checks if the object has any identifier attribute
        identifier_meta = element.meta.identifier_attribute
        if identifier_meta:
            identifier_value = identifier_meta.get( element )
            self._register_element_identifier( element, identifier_meta, identifier_value )

        # Checks object for all reference attributes
        for attribute_meta in element.meta.reference_attributes:
            reference_value = attribute_meta.get( element )
            self._register_element_reference( element, attribute_meta, reference_value )

        for index, child_element in enumerate( element ):
            self._on_element_added(child_element, index)

    def _register_element_identifier( self, element, id_meta, identifier_value ):
##        print '=> registering "%s" with identifier: "%s"' % (object_key, repr(identifier_value))
        assert element is not None
        if identifier_value is not None:
            # walk parents scopes until we find the right one.
            world = element.world
            while world.meta != id_meta.reference_scope:
                world = world.parent_world
            id_scope_key = (world,id_meta.reference_family)
            references = self.ref_by_world_and_family.get( id_scope_key )
            if references is None:
                references = {}
                self.ref_by_world_and_family[ id_scope_key ] = references
            references[identifier_value] = element

    def _register_element_reference( self, element, attribute_meta, reference_value ):
        if reference_value is not None:
            back_reference_key = (attribute_meta.reference_family, reference_value)
            back_references = self.back_references.get( back_reference_key )
            if back_references is None:
                back_references = set()
                self.back_references[back_reference_key] = back_references
            back_references.add( (element, attribute_meta) )

    def _on_element_about_to_be_removed(self, element, index_in_parent): #IGNORE:W0613
        assert isinstance(element,Element)
        assert index_in_parent >= 0, index_in_parent

        # Checks if the object has any identifier attribute
        id_meta = element.meta.identifier_attribute
        if id_meta:
            identifier_value = id_meta.get( element )
            self._unregister_element_identifier( element, id_meta, identifier_value )
            
        # Checks object for all reference attributes
        for attribute_meta in element.meta.reference_attributes:
            reference_value = attribute_meta.get( element )
            self._unregister_element_reference( element, attribute_meta, reference_value )

        for index, child_element in enumerate( element ):
            self._on_element_about_to_be_removed(child_element, index)

    def _unregister_element_identifier( self, element, id_meta, identifier_value ):
##        print '=> unregistering "%s" with identifier: "%s"' % (element, repr(identifier_value))
        if identifier_value is not None:
            # walk parents scopes until we find the right one.
            world = element.world
            while world.meta != id_meta.reference_scope:
                world = world.parent_world
            # unregister the reference
            id_scope_key = (world,id_meta.reference_family)
            references = self.ref_by_world_and_family.get( id_scope_key )
            if references:
                try:
                    del references[identifier_value]
                except KeyError:    # IGNORE:W0704 May happens in case of multiple image with same identifier (usually blank)
                    pass            # since unicity is not validated yet

    def _unregister_element_reference( self, element, attribute_meta, reference_value ):
        if reference_value is not None:
            back_reference_key = (attribute_meta.reference_family, reference_value)
            back_references = self.back_references.get( back_reference_key )
            if back_references:
                back_references.remove( (element, attribute_meta) )

    def _on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        assert isinstance(element,Element) 
#        print 'Element updated', element
        attribute_meta = element.meta.attribute_by_name( name )
        id_meta = element.meta.identifier_attribute
        if id_meta is attribute_meta:
            self._unregister_element_identifier( element, id_meta, old_value )
            self._register_element_identifier( element, id_meta, new_value )
        if attribute_meta in element.meta.reference_attributes:
            self._unregister_element_reference( element, attribute_meta, old_value )
            self._register_element_reference( element, attribute_meta, new_value )
    
    def _warning( self, message, **kwargs ):
        print message % kwargs

    # Identifier/Reference queries
    
    def is_valid_reference( self, world, attribute_meta, attribute_value ):
        """Checks if the specified attribute reference is valid in the world scope
           specified by attribute_meta.
           @exception ValueError if world has no world matching 
                      attribute_meta.reference_scope in its hierarchy. 
        """
        # walk parents scopes until we find the right one.
        assert world is not None
        initial_world = world
        while world.meta != attribute_meta.reference_scope:
            world = world.parent_world
            if world is None:
                raise ValueError( "World '%(world)s' as no meta world '%(scope)s' in its hiearchy" % 
                                  {'world':initial_world, 
                                   'scope':attribute_meta.reference_scope } )
        return self._is_valid_reference_in_world_or_parent( world, 
                                                            attribute_meta, 
                                                            attribute_value )

    def _is_valid_reference_in_world_or_parent(self, world, attribute_meta, attribute_value ):
        """Checks if the world or one of its parent as the specified identifier in
           the family specified by attribute_meta.
           Implementation detail of is_valid_reference.
        """
        id_scope_key = (world,attribute_meta.reference_family)
        references = self.ref_by_world_and_family.get( id_scope_key )
        if references is None or attribute_value not in references:
            world = world.parent_world
            if world is not None:
                return self._is_valid_reference_in_world_or_parent( world, 
                                                                    attribute_meta, 
                                                                    attribute_value )
            return False
        return True

    def list_identifiers( self, world, family ):
        """Returns a list all identifiers for the specified family in the specified scope and its parent scopes."""
        id_scope_key = (world, family)
        identifiers = set(self.ref_by_world_and_family.get( id_scope_key, {} ).keys())
        if world.parent_world is not None:
            identifiers |= self.list_identifiers( world.parent_world, family )
        return identifiers

    def list_references( self, family, identifier_value ):
        """Returns a list of (element,attribute_meta) element attributes 
           that reference the specified identifier.
        """
        back_reference_key = (family, identifier_value)
        return list( self.back_references.get( back_reference_key, [] ) )

    def make_unattached_tree_from_xml( self, file_desc, xml_data ):
        """Makes a tree from the provided xml data for the specified kind of tree.
           The tree is NOT attached to any world. Use World.add_tree to do so.
           Returns the created tree if successful (root was successfully parsed),
           otherwise raise the exception WorldException.
           Warning may be raised at the universe level.
           file_desc: description of the kind of tree to load. Used to associated xml tag to element description.
           xml_data: raw XML data.
        """
        xml_tree = xml.etree.ElementTree.fromstring( xml_data )
        if file_desc.root_object_desc.tag != xml_tree.tag:
            raise WorldException( u'Expected root tag "%(root)s", but got "%(actual)s" instead.' % {
                'root': file_desc.root_object_desc.tag, 'actual': xml_tree.tag } )
        def _make_element_tree_from_xml( object_desc, xml_tree ):
            # Map element attributes
            known_attributes = {}
            missing_attributes = set( xml_tree.keys() )
            for attribute_desc in object_desc.attributes_by_name.itervalues():
                attribute_value = xml_tree.get( attribute_desc.name )
                if attribute_value is not None:
                    # @todo Warning if attribute already in dict
                    known_attributes[ attribute_desc.name ] = attribute_value
                    missing_attributes.remove( attribute_desc.name )
            if missing_attributes:
                self._warning( u'Element %(tag)s, the following attributes are missing in the object description: %(attributes)s.',
                               tag = xml_tree.tag,
                               attributes = ', '.join( sorted( missing_attributes ) ) )
            # Map element children
            children = []
            for xml_tree_child in xml_tree:
                child_object_desc = object_desc.find_immediate_child_by_tag( xml_tree_child.tag )
                if child_object_desc:
                    children.append( _make_element_tree_from_xml( child_object_desc, xml_tree_child ) )
                else:
                    self._warning( u'Element %(tag)s, the following child tag missing in the object description: %(child)s.',
                                   tag = xml_tree.tag,
                                   child = xml_tree_child.tag )
            return Element( object_desc, attributes = known_attributes, children = children )
        root_element = _make_element_tree_from_xml( file_desc.root_object_desc, xml_tree )
        return Tree( self, file_desc, root_element = root_element )


class WorldException(Exception):
    pass

class World(WorldsOwner):
    """Represents a part of the universe unknown to other worlds, described by a ScopeDesc.

       The elements attached to a world are unknown to other World.    
    """
    def __init__( self, universe, scope_desc, key = None ):
        WorldsOwner.__init__( self )
        self._universe = universe
        self._scope_desc = scope_desc
        self._trees = {}
        self._key = key
        self._parent_world = None

    def __repr__( self ):
        trees = ', '.join( tree.meta.name for tree in self._trees.values() )
        return 'World(key="%s",meta="%s",trees=[%s])' % (self.key,self.meta,trees)

    @property
    def key( self ):
        return self._key 

    @property
    def parent_world( self ):
        return self._parent_world

    @property
    def universe( self ):
        return self._universe

    @property
    def meta( self ):
        return self._scope_desc

    @property
    def trees(self):
        return self._trees.values()

    def list_identifiers( self, family ):
        """Returns a list all identifiers for the specified family in the specified scope and its parent scopes."""
        return self.universe.list_identifiers(self, family)

    def is_valid_reference( self, attribute_meta, attribute_value ):
        """Checks if the specified attribute reference is valid in the world scope
           specified by attribute_meta.
           @exception ValueError if world has no world matching 
                      attribute_meta.reference_scope in its hierarchy. 
        """
        return self.universe.is_valid_reference( self, attribute_meta, attribute_value )

    def _attached_to_parent_world( self, parent_world ):
        """Called when a sub-world is attached to the world."""
        self._parent_world = parent_world
        louie.send( WorldAdded, parent_world, self )

    def _about_to_be_detached_from_parent_world(self, parent_world ):
        """Called when a world is removed from the owner."""
        louie.send( WorldAboutToBeRemoved, parent_world, self )
        self._parent_world = None

    def make_tree( self, file_desc, root_element = None ):
        tree = Tree( self.universe, file_desc, root_element = root_element )
        self.add_tree( tree )
        return tree

    def make_tree_from_xml( self, file_desc, xml_data ):
        """Makes a tree from the provided xml data for the specified kind of tree.
           The tree is automatically attached to the world.
           Returns the created tree if successful (root was successfully parsed),
           otherwise raise the exception WorldException.
           Warning may be raised at the universe level.
           file_desc: description of the kind of tree to load. Used to associated xml tag to element description.
           xml_data: raw XML data.
        """
        tree = self.universe.make_unattached_tree_from_xml( file_desc, xml_data )
        self.add_tree( tree )
        return tree

    def find_tree( self, file_desc ):
        return self._trees.get( file_desc )

    def add_tree( self, *trees ):
        for tree in trees:
            assert tree._world is None
            assert isinstance(tree, Tree)
            tree._world = self
            assert tree._file_desc not in self._trees 
            self._trees[ tree._file_desc ] = tree
            louie.send( TreeAdded, self, tree )

    def remove_tree( self, *trees ):
        for tree in trees:
            assert isinstance(tree, Tree)
            assert self._trees.get(tree._file_desc) == tree
            louie.send( TreeAboutToBeRemoved, self, tree )
            del self._trees[ tree._file_desc ]
            tree._world = None

    def _warning( self, message, **kwargs ):
        self._universe._warning( message, **kwargs )
        

class Tree:
    """Represents a part of the world elements live in, described by a FileDesc.
    """
    def __init__( self, universe, file_desc, root_element = None ):
        self._universe = universe
        self._file_desc = file_desc
        self._root_element = root_element
        self._world = None
        self.set_root( root_element )

    def set_root( self, root_element ):
        assert root_element is None or isinstance(root_element, Element), type(root_element)
        if self._root_element is not None:  # detach old root
            louie.send( ElementAboutToBeRemoved, self, self._root_element, 0 )
            self._root_element._tree = None
        if root_element is not None: # attach new root
            root_element._tree = self
            louie.send( ElementAdded, self, root_element, 0 )
        self._root_element = root_element

    def __repr__( self ):
        return 'Tree(meta="%s",id="%s",root="%s")' % (self.meta,id(self),self.root)

    @property
    def universe( self ):
        return self._universe

    @property
    def world( self ):
        return self._world

    @property
    def root( self ):
        return self._root_element

    @property
    def meta( self ):
        return self._file_desc

    def to_xml( self, encoding = None ):
        """Outputs a XML string representing the tree.
           The XML is encoded using the specified encoding, or UTF-8 if none is specified.
        """
        assert self.root is not None
        encoding = encoding or 'utf-8'
        return xml.etree.ElementTree.tostring( self.root )

    def clone( self ):
        """Makes a deep clone of the tree root element.
           The returned tree is not attached to a world.
        """
        cloned_root = self.root and self.root.clone() or None
        return Tree( self, self.meta, cloned_root )


# Provides support for attributes dict, children list and path look-up
_ElementBase = xml.etree.ElementTree._ElementInterface

class Element(_ElementBase):
    """Represents a tree that live in a World on a given Tree, described by an ObjectDesc.
       The Element's description associates it with a given kind of Tree and restricts
       the kind of parent and child elements it may have.
    """
    def __init__( self, object_desc, attributes = None, children = None ):
        """Initializes the element of type object_descwith the specified attributes.
           object_desc: an ObjectDesc instance
           attributes: a dictionary of (name, value) of attributes values
           children: an iterable (list) of child elements not attached to any tree to be attached as child of this element.
        """
        _ElementBase.__init__( self, object_desc.tag, attributes and attributes.copy() or {} )
        assert object_desc is not None
        self._object_desc = object_desc
        self._parent = None
        self._tree = None # only set for the root element
        for child in children or ():
            self.append( child )

    def is_root( self ):
        return self._parent is None

    @property
    def universe( self ):
        world = self.world
        if world is None:
            return None
        return world.universe

    @property
    def world( self ):
        tree = self.tree
        if tree is None:
            return None
        return tree.world

    @property
    def tree( self ):
        if self._parent is None:
            return self._tree
        return  self._parent.tree

    @property
    def parent( self ):
        """Returns the parent element. None if the element is a root."""
        return self._parent

    @property
    def meta( self ):
        return self._object_desc

    def make_child( self, element_meta, attributes = None, children = None ):
        """Makes a new child element and append it to the element."""
        child_element = Element( element_meta, attributes, children )
        self.append( child_element )
        return child_element

    def attribute_meta( self, attribute_name ):
        """Returns the AttributeDesc for the specified attribute.
           @exception KeyError if attribute not found.
        """
        return self._object_desc.attributes_by_name[attribute_name]

    def append( self, element ):
        """Adds a subelement to the end of this element.
           @param element The element to add.
           @exception AssertionError If a sequence member is not a valid object.
        """
        index = len(self)
        self._children.append( element )
        self._parent_element( element )
        tree = self.tree
        if tree:
            louie.send( ElementAdded, tree, element, index )

    def insert( self, index, element ):
        """Inserts a subelement at the given position in this element.
           @param index Where to insert the new subelement.
           @exception AssertionError If the element is not a valid object.
        """
        self._children.insert( index, element )
        self._parent_element( element )
        tree = self.tree
        if tree:
            louie.send( ElementAdded, tree, element, index )

    def __setitem__( self, index, element ):
        """Replaces the given subelement.
           @param index What subelement to replace.
           @param element The new element value.
           @exception IndexError If the given element does not exist.
           @exception AssertionError If element is not a valid object.
        """
        tree = self.tree
        old_element = self._children[index]
        if tree:
            louie.send( ElementAboutToBeRemoved, tree, old_element, index )
        self._children[index] = element
        old_element._parent = None
        self._parent_element( element )
        if tree:
            louie.send( ElementAdded, tree, element, index )

    def __delitem__( self, index ):
        """Deletes the given subelement.
           @param index What subelement to delete.
           @exception IndexError If the given element does not exist.
        """
        if index < 0:
            index += len(self)
        if index < 0 or index >= len(self):
            raise IndexError( "Index %(i)d is not in range[0,%(len)d[" % {'i':index,'len':len(self)} )
        tree = self.tree
        element = self._children[index]
        if tree:
            louie.send( ElementAboutToBeRemoved, tree, element, index )
        del self._children[index]
        element._parent = None

    def __setslice__( self, start, stop, elements ):
        """Replaces a number of subelements with elements from a sequence.
           @param start The first subelement to replace.
           @param stop The first subelement that shouldn't be replaced.
           @param elements A sequence object with zero or more elements.
           @exception AssertionError If a sequence member is not a valid object.
        """
        if start < 0:
            start += len(self)
        if start < 0 or start >= len(self):
            raise IndexError( "Start index %(i)d is not in range[0,%(len)d[" % {'i':start,'len':len(self)} )
        if stop < 0:
            stop += len(self)
        if stop < start:
            stop = start
        if stop > len(self):
            raise IndexError( "End index %(i)d is not in range[0,%(len)d]" % {'i':stop,'len':len(self)} )
        tree = self.tree
        for index in xrange(start,stop):
            element = self._children[start]
            if tree:
                louie.send( ElementAboutToBeRemoved, tree, element, start )
            element._parent = None
            del self._children[start]
        for offset, element in enumerate(elements):
            index = start + offset
            self._parent_element( element )
            self._children.insert( index, element )
            louie.send( ElementAdded, tree, element, index )

    def __delslice__( self, start, stop ):
        """Deletes a number of subelements.
           @param start The first subelement to delete.
           @param stop The first subelement to leave in there.
        """
        if start < 0:
            start += len(self)
        if start < 0 or start >= len(self):
            raise IndexError( "Start index %(i)d is not in range[0,%(len)d[" % {'i':start,'len':len(self)} )
        if stop < 0:
            stop += len(self)
        if stop < start:
            stop = start
        if stop > len(self):
            raise IndexError( "End index %(i)d is not in range[0,%(len)d]" % {'i':stop,'len':len(self)} )
        tree = self.tree
        for index in xrange(start,stop):
            element = self._children[start]
            if tree:
                louie.send( ElementAboutToBeRemoved, tree, element, start )
            element._parent = None
            del self._children[start]

    def index_in_parent( self ):
        """Returns the index of the element in its parent.
           Returns None if the element has no parent.
        """
        if self._parent is None:
            return None
        return self._parent._children.index( self )

    def remove( self, element ):
        """Removes a matching subelement.  Unlike the <b>find</b> methods,
           this method compares elements based on identity, not on tag
           value or contents.
           @param element What element to remove.
           @exception ValueError If a matching element could not be found.
           @exception AssertionError If the element is not a valid object.
        """
        index = self._children.index( element )
        tree = self.tree
        if tree:
            louie.send( ElementAboutToBeRemoved, tree, element, index )
        del self._children[index]
        element._parent = None

    def clear( self ):
        """Resets an element.  This function removes all subelements, clears
           all attributes, and sets the text and tail attributes to None.
        """
        tree = self.tree
        for index in xrange(0,len(self)):
            element = self._children[0]
            if tree:
                louie.send( ElementAboutToBeRemoved, tree, element, 0 )
            element._parent = None
            del self._children[0]
        _ElementBase.clear( self )

    def set(self, key, new_value):
        """Sets an element attribute.
           @param key What attribute to set.
           @param value The attribute value.
           @exception KeyError if the element has no attribute with the specified name in its description.
        """
        # @todo check that value is string-like
        assert new_value is not None
        if key not in self._object_desc.attributes_by_name:
            raise KeyError( 'element %(tag)s has no attribute %(name)s' % {
                'tag': self.meta.tag,
                'name': key } )
        tree = self.tree
        if tree:
            old_value = self.attrib.get(key)
            self.attrib[key] = new_value
            louie.send( AttributeUpdated, tree, self, key, new_value, old_value )
        else:
            self.attrib[key] = new_value

    def unset( self, attribute_name ):
        """Removes the specified attribute from the element.
        """
        tree = self.tree
        if tree:
            old_value = self.attrib[attribute_name]
            louie.send( AttributeUpdated, tree, self, attribute_name, None, old_value )
        del self.attrib[attribute_name]

    def _parent_element( self, element ):
        assert isinstance(element, Element)
        assert element._parent is None
        element._parent = self

    def clone( self ):
        """Makes a deep clone of the element.
           The returned element is not attached to a tree or parented.
        """
        element = Element( self.meta, attributes = self.attrib.copy() )
        for child in self:
            element.append( child.clone() )
        return element


if __name__ == "__main__":
    import unittest

    TEST_GLOBAL_FILE = describe_file( 'testglobal' )
    TEST_LEVEL_FILE = describe_file( 'testlevel' )

    TEST_LEVEL_SCOPE = describe_scope( 'testscope.level', files_desc = [TEST_LEVEL_FILE] )

    TEST_GLOBAL_SCOPE = describe_scope( 'testscope',
                                        files_desc = [TEST_GLOBAL_FILE],
                                        child_scopes = [TEST_LEVEL_SCOPE] )

    GLOBAL_TEXT = describe_object( 'text', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_family = 'text',
                              reference_scope = TEST_GLOBAL_SCOPE ),
        string_attribute( 'fr' )
        ] )


    TEST_GLOBAL_FILE.add_objects( [ GLOBAL_TEXT ] )

    LEVEL_TEXT = describe_object( 'text', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_family = 'text',
                              reference_scope = TEST_LEVEL_SCOPE ),
        string_attribute( 'fr' )
        ] )
    
    LEVEL_SIGN = describe_object( 'sign', attributes = [
        reference_attribute( 'text', reference_family = 'text',
                             reference_scope = TEST_LEVEL_SCOPE, init = '', mandatory = True ),
        reference_attribute( 'alt_text', reference_family = 'text',
                             reference_scope = TEST_LEVEL_SCOPE )
        ], objects = [ LEVEL_TEXT ] )

    LEVEL_INLINE = describe_object( 'inline', objects= [ LEVEL_SIGN, LEVEL_TEXT ] )

    TEST_LEVEL_FILE.add_objects( [ LEVEL_INLINE ] )


    class MetaTest(unittest.TestCase):

        def test_descriptions( self ):
            self.assertEqual( sorted(['text', 'sign', 'inline']), sorted(TEST_LEVEL_SCOPE.objects_by_tag.keys()) )
            for scope in (TEST_LEVEL_SCOPE, TEST_GLOBAL_SCOPE):
                for object_desc in scope.objects_by_tag.itervalues():
                    self.assertEqual( scope, object_desc.scope )
#                for file_desc in scope.files_desc_by_name.itervalues():
#                    self.assertEqual( scope, object_desc.scope )
            self.assertEqual( sorted([LEVEL_SIGN, LEVEL_INLINE]), sorted(LEVEL_TEXT.parent_objects) )
            for tree, objects in { TEST_GLOBAL_FILE: [GLOBAL_TEXT],
                                   TEST_LEVEL_FILE: [LEVEL_TEXT, LEVEL_SIGN] }.iteritems():
                for element in objects:
                    self.assertEqual( tree, element.file )
                    self.assert_( element in tree.all_descendant_object_descs().values() )
                    self.assert_( element.tag in tree.all_descendant_object_descs() )
                    self.assert_( element.tag in tree.scope.objects_by_tag )

    class UniverseTest(unittest.TestCase):


        def setUp( self ):
            self.universe = Universe()
            self.world = self.universe.make_world( TEST_GLOBAL_SCOPE, 'global' )
            self.world_level1 = self.world.make_world( TEST_LEVEL_SCOPE, 'level1' )
            self.level1 = self.world_level1.make_tree( TEST_LEVEL_FILE )
            self.world_level2 = self.world.make_world( TEST_LEVEL_SCOPE, 'level2' )
            self.level2 = self.world_level2.make_tree( TEST_LEVEL_FILE )

        def _make_element(self, object_desc, **attributes ):
            return Element( object_desc, attributes = attributes )

        def test_identifiers(self):
            universe = self.universe
            self.assertEqual( set([]), universe.list_identifiers(self.world, 'text') )
            self.failIf(universe.list_references('text', 'TEXT_HI'))
            # add objects
            gt1 = self._make_element( GLOBAL_TEXT, id = 'TEXT_HI', fr = 'Salut' )
            global_tree = self.world.make_tree( TEST_GLOBAL_FILE, gt1 )
            assert global_tree.universe == universe
            # check reference resolution to global world from global or level worlds
            def check_text_ids( world, *args ):
                self.assertEqual( set(args), 
                                  universe.list_identifiers(world, 'text') )
            check_text_ids( self.world, 'TEXT_HI' )
            check_text_ids( self.world_level1, 'TEXT_HI' )
            check_text_ids( self.world_level2, 'TEXT_HI' )
            def check_valid_sign_reference(world, value):
                attribute_meta = LEVEL_SIGN.attributes_by_name['text']
                assert world is not None
                self.assert_( world.is_valid_reference(attribute_meta, value) ) 
            def check_invalid_sign_reference(world, value):
                attribute_meta = LEVEL_SIGN.attributes_by_name['text']
                assert world is not None
                self.failIf( world.is_valid_reference(attribute_meta, value) ) 
            check_valid_sign_reference( self.world_level1, 'TEXT_HI')
            check_valid_sign_reference( self.world_level2, 'TEXT_HI')
            check_invalid_sign_reference( self.world_level1, 'TEXT_HO')
            check_invalid_sign_reference( self.world_level2, 'TEXT_HO')
            # add identifiers specific to level1 scope
            l1root = self._make_element( LEVEL_INLINE )
            l2root = self._make_element( LEVEL_INLINE )
            self.level1.set_root( l1root )
            self.level2.set_root( l2root )
            l1_ho = l1root.make_child(LEVEL_TEXT, {'id':'TEXT_HO', 'fr':'Oh'})
            # check that reference resolution keep level worlds identifiers independent
            check_valid_sign_reference( self.world_level1, 'TEXT_HO')
            check_invalid_sign_reference( self.world_level2, 'TEXT_HO')
            check_text_ids( self.world, 'TEXT_HI' )
            check_text_ids( self.world_level1, 'TEXT_HI', 'TEXT_HO' )
            check_text_ids( self.world_level2, 'TEXT_HI' )
            # add identifier specified to level2 scope
            l2_ho = l2root.make_child(LEVEL_TEXT, {'id':'TEXT_HO', 'fr':'Oooh'})
            check_valid_sign_reference( self.world_level2, 'TEXT_HO')
            check_text_ids( self.world_level1, 'TEXT_HI', 'TEXT_HO' )
            check_text_ids( self.world_level2, 'TEXT_HI', 'TEXT_HO' )
            #
            # check back references
            #
            def check_references( identifier_value, *args ):
                expected = set([ (element,element.meta.attribute_by_name(name))
                                 for element, name in args ] )
                actual = set( universe.list_references( 'text', identifier_value ) )
                self.assertEqual( expected, actual )
            check_references( 'TEXT_HI' )    
            l1s1 = l1root.make_child( LEVEL_SIGN, 
                                      {'text':'TEXT_HI', 'alt_text':'TEXT_HO'})
            check_references( 'TEXT_HI', (l1s1,'text') )    
            check_references( 'TEXT_HO', (l1s1,'alt_text') )
            # check after update    
            l1s1.set( 'text', 'TEXT_HO' )
            check_references( 'TEXT_HI' )    
            check_references( 'TEXT_HO', (l1s1,'text'), (l1s1,'alt_text') )
            # check after unset attribute
            l1s1.unset( 'alt_text' )
            check_references( 'TEXT_HI' )    
            check_references( 'TEXT_HO', (l1s1,'text') )
            # remove element with reference
            l1s1.parent.remove( l1s1 )
            check_references( 'TEXT_HI' )    
            check_references( 'TEXT_HO' )
            # remove element with identifier
            l1_ho.parent.remove( l1_ho )
            check_invalid_sign_reference( self.world_level1, 'TEXT_HO')

        def test_world( self ):
            self.assertEqual( self.universe, self.universe.universe )
            self.assertEqual( self.universe, self.world.universe )
            self.assertEqual( self.universe, self.world_level1.universe )
            self.assertEqual( self.universe, self.level1.universe )
            # Global
            self.assertEqual( sorted( ['global'] ),
                              sorted( self.universe.list_world_keys( TEST_GLOBAL_SCOPE ) ) )
            self.assertEqual( sorted( [self.world] ),
                              sorted( self.universe.list_worlds_of_type( TEST_GLOBAL_SCOPE ) ) )
            self.assertEqual( self.world, self.universe.find_world( TEST_GLOBAL_SCOPE, 'global' ) )
            # Levels
            self.assertEqual( sorted( ['level1', 'level2'] ),
                              sorted( self.world.list_world_keys( TEST_LEVEL_SCOPE ) ) )
            self.assertEqual( sorted( [self.world_level1, self.world_level2] ),
                              sorted( self.world.list_worlds_of_type( TEST_LEVEL_SCOPE ) ) )
            self.assertEqual( self.world_level1, self.world.find_world( TEST_LEVEL_SCOPE, 'level1' ) )
            self.assertEqual( self.world, self.world_level1.parent_world )
            # Missing
            self.assertEqual( sorted( [] ),
                              sorted( self.world.list_world_keys( TEST_GLOBAL_SCOPE ) ) )
            self.assertEqual( sorted( [] ),
                              sorted( self.world.list_worlds_of_type( TEST_GLOBAL_SCOPE ) ) )
            self.assertEqual( None, self.world.find_world( TEST_LEVEL_SCOPE, 'level_unknown' ) )
            self.assertEqual( None, self.world.find_world( TEST_GLOBAL_SCOPE, 'level_unknown' ) )
    
        def test_element(self):
            s1 = self._make_element( LEVEL_SIGN )
            class ChangeListener:
                def __init__(self,test):
                    self.test = test
                    self._events = []
                    self._expectations = []
                def expect_event(self, signal, parent_element, element, index ):
                    self._events.append( (signal,parent_element, element, index) )
                def on_event(self, element, index, signal=None):
                    expected = self._events.pop(0)  # if failure there, then unexpected extra events...
                    actual = (signal,element.parent, element, index)
                    self.test.assertEqual( expected, actual )
                def expect_attribute(self, element, name, value, old_value):
                    self._events.append( (AttributeUpdated, element, name, value, old_value) )
                def on_attribute_change(self, element, name, value, old_value,signal=None ):
                    expected = self._events.pop(0)  # if failure there, then unexpected extra events...
                    actual = (signal,element,name,value,old_value)
                    self.test.assertEqual( expected, actual )
                def check(self):
                    self.test.assertEqual( [], self._events )
            def check_list( *args ):
                elements = s1[:]
                self.assertEquals( list(args), list(elements) ) 
            t1 = self._make_element( LEVEL_TEXT )
            t2 = self._make_element( LEVEL_TEXT )
            t3 = self._make_element( LEVEL_TEXT )
            t4 = self._make_element( LEVEL_TEXT )
            t5 = self._make_element( LEVEL_TEXT )
            # Test: append() & insert()
            s1.append( t3 )    # t3
            s1.insert( 0, t1 ) # t1, t3
            s1.insert( 1, t2 ) # t1, t2, t3
            s1.append( t4 )    # t1, t2, t3, t4
            s1.insert( 4, t5 ) # t1, t2, t3, t4, t5
            # Checks that child are in s1 and correctly parent
            self.assertEqual( 5, len(s1) )
            self.assertEqual( LEVEL_SIGN, s1.meta  )
            self.assertEqual( LEVEL_TEXT, t2.meta  )
            self.assertEqual( None, t3.universe )
            self.assertEqual( None, s1.parent )
            self.assertEqual( s1, t2.parent )
            self.assertEqual( s1, t3.parent )
            self.assertEqual( None, s1.tree )
            self.assertEqual( None, s1.world )
            self.assertEqual( None, s1.universe )
            self.assertEqual( None, t2.tree )
            self.assertEqual( None, t2.world )
            self.assertEqual( None, t2.universe )
            check_list( t1, t2, t3, t4, t5 )

            # Attach s1 to a root
            events_checker = ChangeListener( self )
            louie.connect( events_checker.on_event, ElementAdded )
            louie.connect( events_checker.on_event, ElementAboutToBeRemoved )
            louie.connect( events_checker.on_attribute_change, AttributeUpdated )
            events_checker.expect_event(ElementAdded, None, s1, 0)
            self.level1.set_root( s1 )
            events_checker.check()
            events_checker.expect_event(ElementAboutToBeRemoved, None, s1, 0)
            self.level1.set_root( None )
            events_checker.expect_event(ElementAdded, None, s1, 0)
            self.level1.set_root( s1 )
            events_checker.check()

            # Checks that universe... is correctly propagated to all children
            self.assertEqual( self.level1, s1.tree )
            self.assertEqual( self.level1, t2.tree )
            self.assertEqual( self.world_level1, s1.world )
            self.assertEqual( self.world_level1, t2.world )
            self.assertEqual( self.universe, s1.universe )
            self.assertEqual( self.universe, t2.universe )
            check_list( t1, t2, t3, t4, t5 )
            # setitem
            t6 = self._make_element( LEVEL_TEXT )
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t1, 0)
            events_checker.expect_event(ElementAdded, s1, t6, 0)
            s1[0] = t6
            self.assertEqual( t6, s1[0] )
            self.assertEqual( s1, t6.parent )
            self.assertEqual( None, t1.parent )
            check_list( t6, t2, t3, t4, t5 )
            events_checker.check()
            # delitem
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t6, 0)
            del s1[0]
            self.assertEqual( t2, s1[0] )
            self.assertEqual( None, t6.parent )
            check_list( t2, t3, t4, t5 )
            events_checker.check()
            # setslice
            events_checker.expect_event(ElementAdded, s1, t1, 0)
            s1[0:0] = [t1]
            self.assertEqual( t1, s1[0] )
            check_list( t1, t2, t3, t4, t5 )
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t2, 1)
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t3, 1)
            s1[1:3] = []
            check_list( t1, t4, t5 )
            self.assertEqual( None, t2.parent )
            self.assertEqual( None, t3.parent )
            self.assertEqual( 5-2, len(s1) )
            events_checker.expect_event(ElementAdded, s1, t2, 1)
            events_checker.expect_event(ElementAdded, s1, t3, 2)
            s1[1:1] = [t2,t3]
            check_list( t1, t2, t3, t4, t5 )
            self.assertEqual( s1, t2.parent )
            self.assertEqual( s1, t3.parent )
            self.assertEqual( 5, len(s1) )
            events_checker.check()
            # delslice
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t2, 1)
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t3, 1)
            del s1[1:3]
            check_list( t1, t4, t5 )
            self.assertEqual( None, t2.parent )
            self.assertEqual( None, t3.parent )
            self.assertEqual( 5-2, len(s1) )
            events_checker.expect_event(ElementAdded, s1, t2, 1)
            events_checker.expect_event(ElementAdded, s1, t3, 2)
            s1[1:1] = [t2,t3]
            check_list( t1, t2, t3, t4, t5 )
            self.assertEqual( s1, t2.parent )
            self.assertEqual( s1, t3.parent )
            events_checker.check()
            # remove
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t2, 1)
            s1.remove(t2)
            check_list( t1, t3, t4, t5 )
            self.assertEqual( None, t2.parent )
            self.assertEqual( 5-1, len(s1) )
            events_checker.expect_event(ElementAdded, s1, t2, 1)
            s1[1:1] = [t2]
            check_list( t1, t2, t3, t4, t5 )
            events_checker.check()
            # clear
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t1, 0)
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t2, 0)
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t3, 0)
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t4, 0)
            events_checker.expect_event(ElementAboutToBeRemoved, s1, t5, 0)
            s1.clear()
            check_list()
            self.assertEqual( 0, len(s1) )
            self.assertEqual( None, t1.parent )
            self.assertEqual( None, t2.parent )
            self.assertEqual( None, t3.parent )
            self.assertEqual( None, t4.parent )
            self.assertEqual( None, t5.parent )
            self.assertEqual( 0, len(s1.keys()) )
            events_checker.check()
            # set attribute
            events_checker.expect_event(ElementAdded, s1, t1, 0)
            s1.append( t1 )
            events_checker.expect_attribute( t1, 'id', 'TEXT_HI', None )
            t1.set( 'id', 'TEXT_HI' )
            events_checker.expect_attribute( t1, 'id', 'TEXT_HO', 'TEXT_HI' )
            t1.set( 'id', 'TEXT_HO' )
            try:
                t1.set( '_bad_attribute', 'dummy')
                self.fail()
            except KeyError: #IGNORE:W0704 
                pass
            events_checker.check()

        def test_from_to_xml_clone( self ):
            xml_data = """<inline>
<text id ="TEXT_HI" fr="Salut" />
<text id ="TEXT_HO" fr="Oh" />
<sign text="TEXT_HI" alt_text="TEXT_HO">
  <text id="TEXT_CHILD" fr="Enfant" />
</sign>
</inline>
"""
            def check( xml_data ):
                world_level = self.world.make_world( TEST_LEVEL_SCOPE, 'levelxml' )
                level_tree = world_level.make_tree_from_xml( TEST_LEVEL_FILE, xml_data )
                self.assertEqual( TEST_LEVEL_FILE, level_tree.meta )
                self.assertEqual( self.universe, level_tree.universe )
                self.assertEqual( world_level, level_tree.world )
                self.assertEqual( level_tree, world_level.find_tree( TEST_LEVEL_FILE ) )
                self.assertEqual( world_level, level_tree.root.world )
                # content            
                inline = level_tree.root
                self.assertEqual( LEVEL_INLINE, inline.meta )
                self.assertEqual( 3, len(inline) )
                self.assertEqual( LEVEL_TEXT, inline[0].meta )
                self.assertEqual( LEVEL_TEXT, inline[1].meta )
                self.assertEqual( LEVEL_SIGN, inline[2].meta )
                self.assertEqual( LEVEL_TEXT, inline[2][0].meta )
                self.assertEqual( 1, len(inline[2]) )
                self.assertEqual( sorted( [('fr','Salut'),('id','TEXT_HI')] ), sorted(inline[0].items()) )
                self.assertEqual( sorted( [('fr','Oh'),('id','TEXT_HO')] ), sorted(inline[1].items()) )
                self.assertEqual( sorted( [('alt_text','TEXT_HO'),('text','TEXT_HI')] ), sorted(inline[2].items()) )
                self.assertEqual( sorted( [('fr','Enfant'),('id','TEXT_CHILD')] ), sorted(inline[2][0].items()) )
                self.world.remove_world( world_level )
                return level_tree

            level_tree = check( xml_data )
            xml_data = level_tree.to_xml()
            check( xml_data )
            level_tree = check( xml_data )
            xml_data = level_tree.to_xml()
            check( xml_data )
            # clone
            cloned_tree = level_tree.clone()
            xml_data = cloned_tree.to_xml()
            check( xml_data )

        def test_from_xml2( self ):
            xml_data = """<inline></inline>"""
            world_level = self.world.make_world( TEST_LEVEL_SCOPE, 'levelxml' )
            level_tree = world_level.make_tree_from_xml( TEST_LEVEL_FILE, xml_data )
            self.assertEqual( world_level, level_tree.world )
            self.assertEqual( world_level, level_tree.root.world )
            

# to test:
# clone

    unittest.main()
