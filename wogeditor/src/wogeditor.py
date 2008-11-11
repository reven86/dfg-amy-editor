# The level editor GUI.

# The following workflow is expected:
# 1) User load a level
# 2) main windows display the scene layout
#    right-side-top-dock display:
#   - level scene tree
#   - level tree (a list in fact)
#   - level resources tree (a list in fact)
# 3) user select an object in one of the tree, related properties are displayed in
#    right-side-down-dock property list
# 4) user edit properties in property list
#
# Later on, provides property edition via scene layout display
# Add toolbar to create new object
#
# In memory, we keep track of two things:
# - updated level
# - specific text/fx resources 

import sys
import os
import os.path
import glob
import math
import itertools
import subprocess
import wogfile
import metaworld
import metawog
import xml.etree.ElementTree 
from PyQt4 import QtCore, QtGui
import qthelper
import editleveldialog_ui
import newleveldialog_ui
import wogeditor_rc

def tr( context, message ):
    return QtCore.QCoreApplication.translate( context, message )

MODEL_TYPE_LEVEL = 'Level'

def find_element_in_tree( root_element, element ):
    """Searchs the specified element in the root_element children and returns all its parent, and its index in its immediate parent.
       Returns None if the element is not found, otherwise returns a tuple ([parent_elements], child_index)
       root_element, element: must provides the interface xml.etree.ElementTree.
    """
    for index, child_element in enumerate(root_element):
        if child_element is element:
            return ([root_element], index)
        found = find_element_in_tree( child_element, element )
        if found is not None:
            found_parents, found_index = found
            found_parents.insert( 0, root_element )
            return found_parents, found_index
    return None

def flattened_element_children( element ):
    """Returns a list of all the element children, including its grand-children..."""
    children = []
    for child_element in element:
        children.append( child_element )
        children.extend( flattened_element_children( child_element ) )
    return children

class ElementReferenceTracker(metaworld.ReferenceTracker):
    """Specialized version of the ReferenceTracker that provides helper for element tree based objects.
    """
    def element_object_added( self, scope_key, object, object_desc ):
        """Registers the specified element and all its children that are declared in the scope description.
        """
        metaworld.ReferenceTracker.object_added( self, scope_key, object, object_desc, self._retrieve_element_attribute )
        scope_desc = object_desc.scope
        for child_element in object:    # recurse to add all child elements
            child_object_desc = object_desc.find_immediate_child_by_tag( child_element.tag )
            if child_object_desc:
                self.element_object_added( scope_key, child_element, child_object_desc )
            else:
                print 'Warning: unknown element "%s", child of "%s" in metaworld:' % (
                    child_element.tag, object.tag)

    def element_object_about_to_be_removed( self, scope_key, element, object_desc ):
        """Unregisters the specified element and all its children that are declared in the scope description.
        """
        if object_desc is None:
            return
        metaworld.ReferenceTracker.object_about_to_be_removed( self, scope_key, element, object_desc,
                                                             self._retrieve_element_attribute )
        scope_desc = object_desc.scope
        for child_element in element:    # recurse to add all child elements
            child_object_desc = object_desc.find_immediate_child_by_tag( child_element.tag )
            if child_object_desc:
                self.element_object_about_to_be_removed( scope_key, child_element, child_object_desc )
            else:
                print 'Warning: unknown element "%s", child of "%s" in metaworld:' % (
                    child_element.tag, object.tag)

    def update_element_attribute( self, scope_key, scope_desc, element, attribute_name, new_value ):
        """Updates an element attribute value and automatically updates related identifier/back-references.
        """
        old_value = element.get( attribute_name )
        element.set( attribute_name, new_value )
        object_desc = scope_desc.objects_by_tag.get( element.tag )
        if object_desc:
            attribute_desc = object_desc.attributes_by_name.get( attribute_name )
            if attribute_desc:
                self.attribute_updated( scope_key, element, attribute_desc, old_value, new_value )

    def _retrieve_element_attribute( self, scope_key, object_key, attribute_desc ):
        return object_key.get( attribute_desc.name )

class GameModelException(Exception):
    pass

class GameModel(QtCore.QObject):
    def __init__( self, wog_path ):
        """Loads FX, material, text and global resources.
           Loads Balls
           Loads Levels

           The following signals are provided:
           QtCore.SIGNAL('currentModelChanged(PyQt_PyObject,PyQt_PyObject)')
           QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)')
           QtCore.SIGNAL('objectAdded(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)')
           QtCore.SIGNAL('objectPropertyValueChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)')
           QtCore.SIGNAL('objectRemoved(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)')
        """
        QtCore.QObject.__init__( self )
        self._wog_path = wog_path
        self._wog_dir = os.path.split( wog_path )[0]
        properties_dir = os.path.join( self._wog_dir, u'properties' )
        self._res_dir = os.path.join( self._wog_dir, u'res' )
        self._effects = self._loadPackedData( properties_dir, 'fx.xml.bin' )
        self._materials = self._loadPackedData( properties_dir, 'materials.xml.bin' )
        self._resources = self._loadPackedData( properties_dir, 'resources.xml.bin' )
        self._readonly_resources = set()    # resources in resources.xml that have expanded defaults idprefix & path
        self._texts = self._loadPackedData( properties_dir, 'text.xml.bin' )
        self._levels = self._loadDirList( os.path.join( self._res_dir, 'levels' ), filter = '%s.scene.bin' )
        self.level_models_by_name = {}
        self._balls_by_name = {}
        self.current_model = None
        self.is_dirty = False
        self.tracker = ElementReferenceTracker()
        self._initializeGlobalReferences()
        self._loadBalls()

    def getResourcePath( self, game_dir_relative_path ):
        return os.path.join( self._wog_dir, game_dir_relative_path )

    def _loadPackedData( self, dir, file_name ):
        path = os.path.join( dir, file_name )
        if not os.path.isfile( path ):
            raise GameModelException( tr( 'LoadData',
                'File "%1" does not exist. You likely provided an incorrect WOG directory.' ).arg( path ) )
        xml_data = wogfile.decrypt_file_data( path )
        xml_tree = xml.etree.ElementTree.fromstring( xml_data )
        return xml_tree

    def _savePackedData( self, dir, file_name, element_tree ):
        path = os.path.join( dir, file_name )
        xml_data = xml.etree.ElementTree.tostring( element_tree )
        wogfile.encrypt_file_data( path, xml_data )

    def _loadDirList( self, dir, filter ):
        if not os.path.isdir( dir ):
            raise GameModelException( tr('LoadLevelList',
                'Directory "%1" does not exist. You likely provided an incorrect WOG directory.' ).arg( dir ) )
        def is_valid_dir( entry ):
            """Accepts the directory only if it contains a specified file."""
            dir_path = os.path.join( dir, entry )
            if os.path.isdir( dir_path ):
                try:
                    filter_file_path = filter % entry
                except TypeError:
                    filter_file_path = filter
                if os.path.isfile( os.path.join( dir_path, filter_file_path ) ):
                    return True
            return False
        dirs = [ entry for entry in os.listdir( dir ) if is_valid_dir( entry ) ]
        dirs.sort()
        return dirs

    def _loadBalls( self ):
        """Loads all ball models and initialize related identifiers/references."""
        ball_names = self._loadDirList( os.path.join( self._res_dir, 'balls' ),
                                        filter = 'balls.xml.bin' )
        ball_dir = os.path.join( self._res_dir, 'balls' )
        for ball_name in ball_names:
            ball_tree = self._loadPackedData( os.path.join(ball_dir, ball_name), 'balls.xml.bin' )
            resource_tree = self._loadPackedData( os.path.join(ball_dir, ball_name), 'resources.xml.bin' )
            ball_model = BallModel( self, ball_name, ball_tree, resource_tree )
            self._balls_by_name[ball_model.ball_name] = ball_model

    def _initializeGlobalReferences( self ):
        """Initialize global effects, materials, resources and texts references."""
        global_scope = self
        self.tracker.scope_added( self, metawog.GLOBAL_SCOPE, None )
        self.tracker.element_object_added( global_scope, self._effects,
                                           metawog.GLOBAL_FX_FILE.root_object_desc )
        self.tracker.element_object_added( global_scope, self._materials,
                                           metawog.GLOBAL_MATERIALS_FILE.root_object_desc )
        self.tracker.element_object_added( global_scope, self._texts,
                                           metawog.GLOBAL_TEXT_FILE.root_object_desc )
        self._expandResourceDefaultsIdPrefixAndPath()
        self.tracker.element_object_added( global_scope, self._resources,
                                           metawog.GLOBAL_RESOURCE_FILE.root_object_desc )

    def _expandResourceDefaultsIdPrefixAndPath( self ):
        """Expands the default idprefix and path that are used as short-cut in the XML file."""
        # Notes: there is an invalid global resource:
        # IMAGE_GLOBAL_ISLAND_6_ICON res/images/islandicon_6
        resource_manifest = self._resources
        default_idprefix = ''
        default_path = ''
        for resources in resource_manifest:
            for element in resources:
                if element.tag == 'SetDefaults':
                    default_path = element.get('path')
                    if not default_path.endswith('/'):
                        default_path += '/'
                    default_idprefix = element.get('idprefix')
                elif element.tag in ('Image', 'Sound', 'font'):
                    new_id = default_idprefix + element.get('id')
                    new_path = default_path + element.get('path')
##                    if element.tag == 'Sound':
##                        full_path = os.path.join( self._wog_dir, new_path + '.ogg' )
##                    else:
##                        full_path = os.path.join( self._wog_dir, new_path + '.png' )
##                    if not os.path.isfile( full_path ):
##                        print 'Invalid resource:', element.get('id'), element.get('path'), new_id, full_path
                    element.set( 'id', new_id )
                    element.set( 'path', new_path )
                self._readonly_resources.add( element )


    @property
    def level_names( self ):
        return self._levels

    def getLevelModel( self, level_name ):
        return self.level_models_by_name.get( level_name )

    def selectLevel( self, level_name ):
        if level_name not in self.level_models_by_name:
            level_dir = os.path.join( self._res_dir, 'levels', level_name )
            level_tree = self._loadPackedData( level_dir, level_name + '.level.bin' )
            scene_tree = self._loadPackedData( level_dir, level_name + '.scene.bin' )
            resource_tree = self._loadPackedData( level_dir, level_name + '.resrc.bin' )
            self.level_models_by_name[level_name] = LevelModel( self, level_name,
                                                                level_tree,
                                                                scene_tree,
                                                                resource_tree )
        level_model = self.level_models_by_name[level_name]
        
        old_model = level_model
        self.current_model = level_model
        self.emit( QtCore.SIGNAL('currentModelChanged(PyQt_PyObject,PyQt_PyObject)'),
                   old_model,
                   level_model )

    def objectSelected( self, level_name, object_file, element ):
        """Signal that the specified object has been selected."""
        self.emit( QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                   level_name, object_file, element )

    def objectAdded( self, level_name, object_file, parent_element, element, index_in_parent ):
        """Signal that an element tree was inserted into another element."""
        self.is_dirty = True
        self.emit( QtCore.SIGNAL('objectAdded(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                   level_name, object_file, parent_element, element, index_in_parent )

    def objectRemoved( self, level_name, object_file, parent_elements, element, index_in_parent ):
        """Signal that an element has been removed from its tree."""
        self.is_dirty = True
        self.emit( QtCore.SIGNAL('objectRemoved(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                   level_name, object_file, parent_elements, element, index_in_parent )

    def objectPropertyValueChanged( self, level_name, object_file, element, property_name, value ):
        """Signal that an element attribute value has changed."""
        self.is_dirty = True
        self.emit( QtCore.SIGNAL('objectPropertyValueChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                   level_name, object_file, element, property_name, value )

    def hasModifiedReadOnlyLevels( self ):
        """Checks if the user has modified read-only level."""
        for level_model in self.level_models_by_name.itervalues():
            if level_model.isDirty() and level_model.isReadOnlyLevel():
                return True
        return False

    def save( self ):
        """Save all changes.
           Raise exception IOError on failure.
        """
        for level_model in self.level_models_by_name.itervalues():
            level_model.saveModifiedElements()
        self.is_dirty = False

    def playLevel( self, level_name ):
        """Starts WOG to test the specified level."""
        pid = subprocess.Popen( [self._wog_path, level_name], cwd = self._wog_dir ).pid
        # Don't wait for process end...
        # @Todo ? Monitor process so that only one can be launched ???

    def newLevel( self, level_name ):
        """Creates a new blank level with the specified name.
           May fails with an IOError."""
        return self._addNewLevel( level_name,
                                  xml.etree.ElementTree.fromstring( metawog.LEVEL_GAME_TEMPLATE ),
                                  xml.etree.ElementTree.fromstring( metawog.LEVEL_SCENE_TEMPLATE ),
                                  xml.etree.ElementTree.fromstring( metawog.LEVEL_RESOURCE_TEMPLATE ) )

    def cloneLevel( self, cloned_level_name, new_level_name ):
        """Clone an existing level and its resources."""
        level_model = self.getLevelModel( cloned_level_name )
        def clone_element_tree( element_tree ):
            xml_data = xml.etree.ElementTree.tostring( element_tree )
            return xml.etree.ElementTree.fromstring( xml_data )
        return self._addNewLevel( new_level_name,
                                  clone_element_tree( level_model.level_tree ),
                                  clone_element_tree( level_model.scene_tree ),
                                  clone_element_tree( level_model.resource_tree ) )

    def _addNewLevel( self, level_name, level_tree, scene_tree, resource_tree ):
        """Adds a new level using the specified level, scene and resource tree.
           The level directory is created, but the level xml files will not be saved immediately.
        """
        level_dir_path = os.path.join( self._res_dir, 'levels', level_name )
        if not os.path.isdir( level_dir_path ):
            os.mkdir( level_dir_path )
        # Fix the hard-coded level name in resource tree: <Resources id="scene_NewTemplate" >
        for resource_element in resource_tree.findall( './/Resources' ):
            resource_element.set( 'id', 'scene_%s' % level_name )
        # Creates and register the new level
        self.level_models_by_name[level_name] = LevelModel(
            self, level_name, level_tree, scene_tree, resource_tree, is_dirty = True )
        self._levels.append( level_name )
        self._levels.sort()
        self.is_dirty = True

class BallModel(object):
    def __init__( self, game_model, ball_name, ball_tree, resource_tree ):
        self.game_model = game_model
        self.ball_name = ball_name
        self.ball_tree = ball_tree
        self.resource_tree = resource_tree
        self._initializeBallReferences()

    @property
    def tracker( self ):
        return self.game_model.tracker

    def _initializeBallReferences( self ):
        ball_scope = self
        parent_scope = self.game_model
        self.tracker.scope_added( ball_scope, metawog.BALL_SCOPE, parent_scope )
        self.tracker.element_object_added( ball_scope, self.ball_tree,
                                           metawog.BALL_MAIN_FILE.root_object_desc )
        self.tracker.element_object_added( ball_scope, self.resource_tree,
                                           metawog.BALL_RESOURCE_FILE.root_object_desc )

class LevelModel(object):
    def __init__( self, game_model, level_name, level_tree, scene_tree, resource_tree, is_dirty = False ):
        self.game_model = game_model
        self.level_name = level_name
        self.level_tree = level_tree
        self.scene_tree = scene_tree
        self.resource_tree = resource_tree
        self._initializeLevelReferences()
        self.dirty_object_types = set()
        if is_dirty:
            self.dirty_object_types |= set( (metawog.LEVEL_GAME_FILE,
                                             metawog.LEVEL_RESOURCE_FILE,
                                             metawog.LEVEL_SCENE_FILE) )

        self.images_by_id = {}
        for image_element in self.resource_tree.findall( './/Image' ):
            self._loadImageFromElement( image_element )

    @property
    def tracker( self ):
        return self.game_model.tracker

    def isDirty( self ):
        return len(self.dirty_object_types) != 0

    def isReadOnlyLevel( self ):
        return self.level_name.lower() in 'ab3 beautyandthetentacle beautyschool blusteryday bulletinboardsystem burningman chain deliverance drool economicdivide fistyreachesout flyawaylittleones flyingmachine geneticsortingmachine goingup gracefulfailure grapevinevirus graphicprocessingunit hanglow helloworld htinnovationcommittee immigrationnaturalizationunit impalesticky incinerationdestination infestytheworm ivytower leaphole mapworldview mistyslongbonyroad mom observatoryobservationstation odetobridgebuilder productlauncher redcarpet regurgitationpumpingstation roadblocks secondhandsmoke superfusechallengetime theserver thirdwheel thrustertest towerofgoo tumbler uppershaft volcanicpercolatordayspa waterlock weathervane whistler youhavetoexplodethehead'.split()

    def _loadImageFromElement( self, image_element ):
        id, path = image_element.get('id'), image_element.get('path')
        path = self.game_model.getResourcePath( path + '.png' )
        if os.path.isfile( path ):
            pixmap = QtGui.QPixmap()
            if pixmap.load( path ):
                self.images_by_id[id] = pixmap
##                print 'Loaded', id, path
            else:
                print 'Failed to load image:', path
        else:
            print 'Invalid image path for "%s": "%s"' % (id,path)

    def _initializeLevelReferences( self ):
        level_scope = self
        parent_scope = self.game_model
        self.tracker.scope_added( level_scope, metawog.LEVEL_SCOPE, parent_scope )
        self.tracker.element_object_added( level_scope, self.level_tree,
                                           metawog.LEVEL_GAME_FILE.root_object_desc )
        self.tracker.element_object_added( level_scope, self.scene_tree,
                                           metawog.LEVEL_SCENE_FILE.root_object_desc )
        self.tracker.element_object_added( level_scope, self.resource_tree,
                                           metawog.LEVEL_RESOURCE_FILE.root_object_desc )

    def saveModifiedElements( self ):
        """Save the modified scene, level, resource tree."""
        if self.isReadOnlyLevel():  # Discards change made on read-only level
            self.dirty_object_types = set()
            return
        level_name = self.level_name
        level_dir = os.path.join( self.game_model._res_dir, 'levels', level_name )
        if metawog.LEVEL_GAME_FILE in self.dirty_object_types:
            self.game_model._savePackedData( level_dir, level_name + '.level.bin', self.level_tree )
            self.dirty_object_types.remove( metawog.LEVEL_GAME_FILE )
        if metawog.LEVEL_RESOURCE_FILE in self.dirty_object_types:
            self.game_model._savePackedData( level_dir, level_name + '.resrc.bin', self.resource_tree )
            self.dirty_object_types.remove( metawog.LEVEL_RESOURCE_FILE )
        if metawog.LEVEL_SCENE_FILE in self.dirty_object_types:
            self.game_model._savePackedData( level_dir, level_name + '.scene.bin', self.scene_tree )
            self.dirty_object_types.remove( metawog.LEVEL_SCENE_FILE )

    def updateObjectPropertyValue( self, object_file, element, property_name, new_value ):
        """Changes the property value of an object (scene, level or resource)."""
        reload_image = False
        if element.tag == 'Image':
            reload_image = True # reload image if path changed or image was not in cache
            if property_name == 'id': # update pixmap cache
                old_id = element.get('id')
                old_pixmap = self.images_by_id.get(old_id)
                if old_pixmap:
                    self.images_by_id[new_value] = old_pixmap
                    del self.images_by_id[old_id]
                    reload_image = False
        self.game_model.tracker.update_element_attribute( self, metawog.LEVEL_SCOPE, element,
                                                          property_name, new_value )
        if reload_image:
            self._loadImageFromElement( element )
        self.dirty_object_types.add( object_file )
        self.game_model.objectPropertyValueChanged( self.level_name,
                                                    object_file, element,
                                                    property_name, new_value )

    def getObjectFileRootElement( self, object_file ):
        root_by_scope = { metawog.LEVEL_GAME_FILE: self.level_tree,
                          metawog.LEVEL_SCENE_FILE: self.scene_tree,
                          metawog.LEVEL_RESOURCE_FILE: self.resource_tree }
        return root_by_scope[object_file]

    def addElement( self, object_file, parent_element, element, index = None ):
        """Adds the specified element (tree) at the specified position in the parent element.
           If index is None, then the element is added after all the parent children.
           The element is inserted with all its children.
           """
        # Update identifiers & reference related to element
        self.tracker.element_object_added( self, element, object_file.find_object_desc_by_tag(element.tag) )
        # Adds the element
        if index is None:
            index = len(parent_element)
        parent_element.insert( index, element )
        # Broadcast the insertion event
        self.dirty_object_types.add( object_file )
        if element.tag == 'Image':  # @todo dirty hack, need to be cleaner
            self._loadImageFromElement( element )
        self.game_model.objectAdded( self.level_name, object_file, parent_element, element, index )

    def removeElement( self, object_file, element ):
        """Removes the specified element and all its children from the level."""
        # Update element reference & identifiers in tracker
        if element in (self.scene_tree, self.level_tree, self.resource_tree):
            print 'Warning: attempted to remove root element, GUI should not allow that'
            return False # can not remove those elements
        # @todo makes tag look-up fails once model is complete
        self.tracker.element_object_about_to_be_removed( self, element, object_file.find_object_desc_by_tag(element.tag) )
        found = find_element_in_tree( self.getObjectFileRootElement(object_file), element )
        if found is None:
            print 'Warning: inconsistency, element to remove in not in the specified object_file', element
            return False
        parent_elements, index_in_parent = found
        # Remove the element from its parent
        del parent_elements[-1][index_in_parent]
        # broadcast element removal event...
        self.game_model.objectRemoved( self.level_name, object_file, parent_elements, element, index_in_parent )
        self.dirty_object_types.add( object_file )
        return True

    def getImagePixmap( self, image_id ):
        return self.images_by_id.get(image_id)

    def objectSelected( self, object_file, element ):
        """Indicates that the specified object has been selected.
           object_file: one of metawog.LEVEL_GAME_FILE, metawog.LEVEL_SCENE_FILE, metawog.LEVEL_RESOURCE_FILE
        """
        self.game_model.objectSelected( self.level_name, object_file, element )

    def updateLevelResources( self ):
        """Ensures all image/sound resource present in the level directory are in the resource tree."""
        game_dir = os.path.normpath( self.game_model._wog_dir )
        level_dir = os.path.join( game_dir, 'res', 'levels', self.level_name )
        resource_element = self.resource_tree.find( './/Resources' )
        if resource_element is None:
            print 'Warning: root element not found in resource tree'
            return []
        added_elements = []
        for tag, extension, id_prefix in ( ('Image','png', 'LEVEL_IMAGE_'), ('Sound','ogg', 'LEVEL_SOUND_') ):
            known_paths = set()
            for element in self.resource_tree.findall( './/' + tag ):
                path = os.path.normpath( os.path.splitext( element.get('path','').lower() )[0] )
                # known path are related to wog top dir in unix format & lower case without the file extension
                known_paths.add( path )
            existing_paths = glob.glob( os.path.join( level_dir, '*.' + extension ) )
            for existing_path in existing_paths:
                existing_path = existing_path[len(game_dir)+1:] # makes path relative to wog top dir
                existing_path = os.path.splitext(existing_path)[0] # strip file extension
                path = os.path.normpath( existing_path ).lower()
                if path not in known_paths:
                    existing_path = os.path.split( existing_path )[1]
                    id = id_prefix + ''.join( c for c in existing_path if c.upper() in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789' )
                    resource_path = 'res/levels/%s/%s' % (self.level_name,existing_path)
                    new_resource = xml.etree.ElementTree.Element( tag, {'id':id.upper(),
                                                                        'path':resource_path} )
                    self.addElement( metawog.LEVEL_RESOURCE_FILE, resource_element, new_resource )
                    added_elements.append( new_resource )
        return added_elements
            
        

Z_LEVEL_ITEMS = 10000.0
Z_PHYSIC_ITEMS = 9000.0

class LevelGraphicView(QtGui.QGraphicsView):
    """A graphics view that display scene and level elements.
       Signals:
       QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)')
         => when the mouse mouse in the map. parameters: x,y in scene coordinate.
    """
    def __init__( self, level_name, game_model ):
        QtGui.QGraphicsView.__init__( self )
        self.__level_name = level_name
        self.__game_model = game_model
        self.setWindowTitle( self.tr( u'Level - %1' ).arg( level_name ) )
        self.setAttribute( QtCore.Qt.WA_DeleteOnClose )
        self.__scene = QtGui.QGraphicsScene()
        self.__balls_by_id = {}
        self.__strands = []
        self.__lines = []
        self.__scene_elements = set()
        self.__level_elements = set()
        self.setScene( self.__scene )
        self.refreshFromModel( self.getLevelModel() )
        self.scale( 1.0, 1.0 )
        self.connect( self.__scene, QtCore.SIGNAL('selectionChanged()'),
                      self._sceneSelectionChanged )
        self.connect( self.__game_model, QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                      self._updateObjectSelection )
        self.setRenderHints( QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform )
        self.connect( self.__game_model,
                      QtCore.SIGNAL('objectPropertyValueChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                      self._refreshOnObjectPropertyValueChange )
        self.connect( self.__game_model,
                      QtCore.SIGNAL('objectRemoved(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                      self._refreshOnObjectRemoval )
        self.connect( self.__game_model,
                      QtCore.SIGNAL('objectAdded(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                      self._refreshOnObjectInsertion )

    def selectLevelOnSubWindowActivation( self ):
        """Called when the user switched MDI window."""
        self.__game_model.selectLevel( self.__level_name )

    def mouseMoveEvent( self, event):
        pos = self.mapToScene( event.pos() ) 
        self.emit( QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'), pos.x(), pos.y() )
        return QtGui.QGraphicsView.mouseMoveEvent( self, event )

    def wheelEvent(self, event):
        """Handle zoom when wheel is rotated."""
        delta = event.delta()
        if delta != 0:
            small_delta = delta / 500.0
            factor = abs(small_delta)
            if small_delta < 0:
                factor = 1/(1+factor)
            else:
                factor = 1 + small_delta
            self.scaleView( factor ) 

    def scaleView(self, scaleFactor):
        """Scales the view by a given factor."""
        factor = self.matrix().scale(scaleFactor, scaleFactor).mapRect(QtCore.QRectF(0, 0, 1, 1)).width()

        if factor < 0.07 or factor > 100:
            return

        self.scale(scaleFactor, scaleFactor)

    def _sceneSelectionChanged( self ):
        """Called whenever the selection change in the scene (e.g. user click on an item)."""
        items = self.__scene.selectedItems()
        if len(items) == 1: # do not handle multiple selection for now
            for item in items:
##                print 'selection changed', item
                element = item.data(0).toPyObject()
                assert element is not None, "Hmmm, forgot to associate a data to that item..."
                if element in self.__scene_elements:
                    self.getLevelModel().objectSelected( metawog.LEVEL_SCENE_FILE, element )
                elif element in self.__level_elements:
                    self.getLevelModel().objectSelected( metawog.LEVEL_GAME_FILE, element )
                else: # Should never get there
                    assert False

    def _updateObjectSelection( self, level_name, object_file, selected_element ):
        """Ensures that the selected object is seleted in the graphic view.
           Called whenever an object is selected in the tree view or the graphic view.
        """
        # Notes: we do not change selection if the item belong to an item group.
        # All selection events send to an item belonging to a group are forwarded
        # to the item group, which caused infinite recursion (unselect child,
        # then unselect parent, selection parent...)
        for item in self.__scene.items():
            element = item.data(0).toPyObject()
            if element == selected_element:
##                print 'Selecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
                if not item.isSelected() and item.group() is None:
                    item.setSelected( True )
            elif item.isSelected() and item.group() is None:
##                print 'Unselecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
                item.setSelected( False )

    def matchModel( self, model_type, level_name ):
        return model_type == MODEL_TYPE_LEVEL and level_name == self.__level_name

    def getLevelModel( self ):
        return self.__game_model.getLevelModel( self.__level_name )

    def _refreshOnObjectPropertyValueChange( self, level_name, object_file, element, property_name, value ):
        """Refresh the view when an object property change (usually via the property list edition)."""
        if level_name == self.__level_name:
            # @todo be a bit smarter than this (e.g. refresh just the item)
            # @todo avoid losing selection (should store selected object in level model)
            self.refreshFromModel( self.getLevelModel() )

    def _refreshOnObjectRemoval( self, level_name, object_file, parent_elements, element, index_in_parent ):
        if level_name == self.__level_name:
            # @todo be a bit smarter than this (e.g. refresh just the item)
            # @todo avoid losing selection (should store selected object in level model)
            self.refreshFromModel( self.getLevelModel() )

    _refreshOnObjectInsertion = _refreshOnObjectRemoval

    def refreshFromModel( self, game_level_model ):
        scene = self.__scene
        scene.clear()
        self.__balls_by_id = {}
        self.__strands = []
        self.__lines = []
        level_element = game_level_model.level_tree
        self._addElements( scene, level_element, self.__level_elements )
        self._addStrands( scene )

        scene_element = game_level_model.scene_tree
        self._addElements( scene, scene_element, self.__scene_elements )

        for element in self.__lines:
            self._sceneLineBuilder( scene, element )
        
##        print 'SceneRect:', self.sceneRect()
##        print 'ItemsBoundingRect:', scene.itemsBoundingRect()
##        for item in self.items():
##            print 'Item:', item.boundingRect()

    def _addElements( self, scene, element, element_set ):
        """Adds graphic item for 'element' to the scene, and add the element to element_set.
           Recurses for child element.
           Return the graphic item created for the element if any (None otherwise).
        """
        builders = {
            # .level.xml builders
            'signpost': self._levelSignPostBuilder,
            'pipe': self._levelPipeBuilder,
            'BallInstance': self._levelBallInstanceBuilder,
            'Strand': self._addlevelStrand,
            'fire': self._levelFireBuilder,
            # .scene.xml builders
            'SceneLayer': self._sceneSceneLayerBuilder,
            'button': self._sceneButtonBuilder,
            'buttongroup': self._sceneButtonGroupBuilder,
            'circle': self._sceneCircleBuilder,
            'compositegeom': self._sceneCompositeGeometryBuilder,
            'rectangle': self._sceneRectangleBuilder,
            'hinge': self._sceneHingeBuilder,
            'label': self._sceneLabelBuilder,
            'line': self._addSceneLine,
            'linearforcefield': self._sceneLinearForceFieldBuidler,
            'motor': self._sceneMotorBuilder,
            'particles': self._sceneParticlesBuilder,
            'radialforcefield': self._sceneRadialForceFieldBuilder
            }
        builder = builders.get( element.tag )
        composite_item = None
        item = None
        if builder:
            item = builder( scene, element )
            if item:
                item.setData( 0, QtCore.QVariant( element ) )
                item.setFlag( QtGui.QGraphicsItem.ItemIsSelectable, True )
                if element.tag == 'compositegeom':
                    composite_item = item
            
        for child_element in element:
            item = self._addElements( scene, child_element, element_set )
            if composite_item and item:
                item.setParentItem( composite_item )
        element_set.add( element )
        return item

    @staticmethod
    def _elementReal( element, attribute, default_value = 0.0 ):
        """Returns the specified element attribute as a float, defaulting to default_value if it does not exist."""
        return float( element.get(attribute, default_value) )

    @staticmethod
    def _elementXY( element ):
        """Returns 'x' & 'y' attribute. y is negated (0 is bottom of the screen)."""
        return (float(element.get('x')), -float(element.get('y')))

    @staticmethod
    def _elementXYR( element ):
        """Returns 'x' & 'y' & 'radius' attribute. y is negated (0 is bottom of the screen)."""
        return LevelGraphicView._elementXY(element) + (float(element.get('radius')),)

    @staticmethod
    def _elementXYDepth( element ):
        """Returns 'x' & 'y' & 'depth' attribute. y is negated (0 is bottom of the screen)."""
        return LevelGraphicView._elementXY(element) + (float(element.get('depth')),)

    @staticmethod
    def _elementRotationScaleXY( element ):
        """Returns 'rotation', 'scalex' and 'scaley' element's attribute converted to float.
           rotation is defaulted to 0 if not defined, and is in degrees.
           scalex and scaley are defaulted to 1 if not defined.
        """
        return ( float(element.get('rotation',0.0)),
                 float(element.get('scalex',1.0)),
                 float(element.get('scaley',1.0)) )

    @staticmethod
    def _elementRotationInRadians( element, attribute = 'rotation', default_value = 0.0 ):
        return math.degrees( LevelGraphicView._elementReal( element, attribute, default_value ) )

    @staticmethod
    def _elementV2( element, attribute, default_value = (0.0,0.0) ):
        value = element.get(attribute)
        if value is None:
            return default_value
        v1, v2 = [ float(v) for v in value.split(',') ]
        return (v1, v2)

    @staticmethod
    def _elementV2Pos( element, attribute, default_value = (0.0,0.0) ): # y=0 is bottom => Negate y
        x, y = LevelGraphicView._elementV2( element, attribute, default_value )
        return x, -y

    @staticmethod
    def _elementImageWithPosScaleRot( element ):
        image = element.get('image')
        imagepos = LevelGraphicView._elementV2Pos( element, 'imagepos' )
        imagescale = LevelGraphicView._elementV2( element, 'imagescale', (1.0,1.0) )
        imagerot = LevelGraphicView._elementRotationInRadians( element, 'imagerot' )
        return image, imagepos, imagescale, imagerot

    @staticmethod
    def _setLevelItemZ( item ):
        item.setZValue( Z_LEVEL_ITEMS )

    @staticmethod
    def _setLevelItemXYZ( item, x, y ):
        item.setZValue( Z_LEVEL_ITEMS )
        item.setPos( x, y )

    @staticmethod
    def _setSceneItemXYZ( item, x, y ):
        item.setZValue( Z_PHYSIC_ITEMS )
        item.setPos( x, y )

    def getImagePixmap( self, image_id ):
        """Returns the image pixmap for the specified image id."""
        if image_id:
            return self.getLevelModel().getImagePixmap( image_id )
        return None

    def _levelSignPostBuilder( self, scene, element ):
        image = element.get('image')
##        pixmap = self.getImagePixmap( image )
##        if pixmap:
        x, y = self._elementXY( element )
        font = QtGui.QFont()
        font.setPointSize( 24.0 )
        font.setBold( True )
        item = scene.addText( element.get('text'), font )
        item.setDefaultTextColor( QtGui.QColor( 64, 224, 255 ) )
##            item = scene.addPixmap( pixmap )
        self._setLevelItemXYZ( item, x, y )
        return item

    def _levelPipeBuilder( self, scene, element ):
        vertexes = []
        for vertex_element in element:
            vertexes.append( self._elementXY(vertex_element) )
        if vertexes:
            path = QtGui.QPainterPath()
            path.moveTo( *vertexes[0] )
            for vertex in vertexes[1:]:
                path.lineTo( *vertex )
                    
            pen = QtGui.QPen()
            pen.setWidth( 10 )
    ##        brush = QtGui.QBrush( QtCore.Qt.SolidPattern )
    ##        item = scene.addPath( path, pen, brush )
            item = scene.addPath( path, pen )
            return item

    def _levelBallInstanceBuilder( self, scene, element ):
        x, y = self._elementXY( element )
        r = 10
        item = scene.addEllipse( -r/2, -r/2, r, r )
        self._setLevelItemXYZ( item, x, y )
        ball_id = element.get('id')
        self.__balls_by_id[ ball_id ] = item
        return item

    def _addlevelStrand( self, scene, element ):
        """Strands are rendered once everything has been rendered because they refer other items (balls)."""
        id1, id2 = element.get('gb1'), element.get('gb2')
        self.__strands.append( (id1, id2, element) )

    def _addStrands( self, scene ):
        """Render all the strands."""
        pen = QtGui.QPen()
        pen.setWidth( 3 )
        for id1, id2, element in self.__strands:
            item1, item2 = self.__balls_by_id.get(id1), self.__balls_by_id.get(id2)
            if item1 and item2:
                p1, p2 = item1.pos(), item2.pos()
                strand_item = scene.addLine( p1.x(), p1.y(), p2.x(), p2.y(), pen )
                strand_item.setData( 0, QtCore.QVariant( element ) )

    def _levelStrandBuilder( self, scene, element ):
        pen = QtGui.QPen()
        pen.setWidth( 10 )

    def _levelFireBuilder( self, scene, element ):
        x, y, r = self._elementXYR( element )
        pen = QtGui.QPen( QtGui.QColor( 255, 64, 0 ) )
        pen.setWidth( 3 )
        item = scene.addEllipse( -r/2, -r/2, r, r, pen )
        self._setLevelItemXYZ( item, x, y )
        return item

    def _sceneSceneLayerBuilder( self, scene, element ):
        x, y, depth = self._elementXYDepth( element )
        image = element.get('image')
        alpha = self._elementReal( element, 'alpha', 1.0 )
        pixmap = self.getImagePixmap( image )
        rotation, scalex, scaley = self._elementRotationScaleXY( element )
##        tilex = self._elementBool( element, 'tilex', False )
##        tiley = self._elementBool( element, 'tiley', False )
        if pixmap:
            item = scene.addPixmap( pixmap )
            self._applyPixmapTransform( item, pixmap, x, y, rotation, scalex, scaley, depth )
            return item
        else:
            print 'Scene layer image not found', image

    @staticmethod
    def _applyPixmapTransform( item, pixmap, x, y, rotation, scalex, scaley, depth ):
        LevelGraphicView._applyTransform( item, pixmap.width()/2.0, pixmap.height()/2.0,
                                          x, y, rotation, scalex, scaley, depth )

    @staticmethod
    def _applyTransform( item, xcenter, ycenter, x, y, rotation, scalex, scaley, depth ):
        """Rotate, scale and translate the item. xcenter, ycenter indicates the center of rotation.
        """
        # Notes: x, y coordinate are based on the center of the image, but Qt are based on top-left.
        # Hence, we adjust the x, y coordinate by half width/height.
        # But rotation is done around the center of the image, that is half width/height
        transform = QtGui.QTransform()
        xcenter, ycenter = xcenter * scalex, ycenter * scaley
        transform.translate( xcenter, ycenter )
        transform.rotate( -rotation )
        transform.translate( -xcenter, -ycenter )
        item.setTransform( transform )
        x -= xcenter
        y -= ycenter
        item.setPos( x, y )
        item.scale( scalex, scaley )
        item.setZValue( depth )
            
    def _sceneButtonBuilder( self, scene, element ):
        x, y, depth = self._elementXYDepth( element )
        rotation, scalex, scaley = self._elementRotationScaleXY( element )
        pixmap = self.getImagePixmap( element.get('up') )
        if pixmap:
            item = scene.addPixmap( pixmap )
            self._applyPixmapTransform( item, pixmap, x, y, rotation, scalex, scaley, depth )
            return item
        else:
            print 'Button image not found:', element.get('up')
        

    def _sceneButtonGroupBuilder( self, scene, element ):
        pass

    def _sceneLabelBuilder( self, scene, element ):
        x, y = self._elementXY( element )
        rotation = self._elementReal( element, 'rotation', 0.0 )
        scale = self._elementReal( element, 'scale', 1.0 )
        font = QtGui.QFont()
        font.setPointSize( 24.0 )
        font.setBold( True )
        item = scene.addText( element.get('text'), font )
        item.setDefaultTextColor( QtGui.QColor( 64, 255, 0 ) )
        self._applyTransform( item, 0, 0, x, y, rotation, scale, scale, Z_PHYSIC_ITEMS )
        return item

    def _sceneCircleBuilder( self, scene, element ):
        # Still buggy: when in composite, likely position is likely relative to composite geometry
        x, y, r = self._elementXYR( element )
        image, imagepos, imagescale, imagerot = self._elementImageWithPosScaleRot( element )
        if image: # draw only the pixmap for now, but we should probably draw both the physic & pixmap
            pixmap = self.getImagePixmap( image )
            if pixmap:
                item = scene.addPixmap( pixmap )
                self._applyPixmapTransform( item, pixmap, imagepos[0], imagepos[1], imagerot,
                                            imagescale[0], imagescale[1], 0.0 )
                return item
            else:
                print 'Circle image not found:', image
        else: # "physic" circle
            pen = QtGui.QPen( QtGui.QColor( 0, 64, 255 ) )
            pen.setWidth( 5 )
            item = scene.addEllipse( -r, -r, r*2, r*2, pen )
            self._setSceneItemXYZ( item, x, y )
        return item
            

    def _sceneRectangleBuilder( self, scene, element ):
        x, y = self._elementXY( element )
        rotation = self._elementRotationInRadians( element )
        width = self._elementReal( element, 'width', 1.0 )
        height = self._elementReal( element, 'height', 1.0 )
        image, imagepos, imagescale, imagerot = self._elementImageWithPosScaleRot( element )
        if image: # draw only the pixmap for now, but we should probably draw both the physic & pixmap
            pixmap = self.getImagePixmap( image )
            if pixmap:
                item = scene.addPixmap( pixmap )
                self._applyPixmapTransform( item, pixmap, imagepos[0], imagepos[1], imagerot,
                                            imagescale[0], imagescale[1], 0.0 )
                return item
            else:
                print 'Rectangle image not found:', image
        else: # "physic" rectangle
            pen = QtGui.QPen( QtGui.QColor( 0, 64, 255 ) )
            pen.setWidth( 5 )
            item = scene.addRect( 0, 0, width, height, pen )
            self._applyTransform( item, width/2.0, height/2.0, x, y, rotation,
                                  1.0, 1.0, Z_PHYSIC_ITEMS )
        return item
        
    def _addSceneLine( self, scene, element ):
        """Delay line rendering after everything (line are unbounded, we limit them to the scene extend)."""
        self.__lines.append( element )

    def _sceneLineBuilder( self, scene, element ):
        """An unbounded physic line. We bound it to the scene bounding rectangle."""
        anchor = self._elementV2Pos( element, 'anchor' )
        normal = self._elementV2Pos( element, 'normal' )
        pen = QtGui.QPen( QtGui.QColor( 0, 64, 255 ) )
        pen.setWidth( 5 )
        direction = normal[1], -normal[0]
        scene_rect = scene.sceneRect()
        # The line is defined by: anchor + direction * t
        if abs(direction[0]) > abs(direction[1]):   # mostly horizontal, bound it min/max x scene
            # xl = anchor.x + direction.x * t => (xl - anchor.x)/direction.x
            # yl = anchor.y + direction.y * t => yl = anchor.y + direction.y * (xl - anchor.x)/direction.x
            minx, maxx = scene_rect.left(), scene_rect.right()
            ys = [ anchor[1] + direction[1] * ( xl - anchor[0] ) / direction[0]
                   for xl in (minx, maxx) ]
            item = scene.addLine( minx, ys[0], maxx, ys[1], pen )
        else:
            miny, maxy = scene_rect.top(), scene_rect.bottom()
            xs = [ anchor[0] + direction[0] * ( yl - anchor[1] ) / direction[1]
                   for yl in (miny, maxy) ]
            item = scene.addLine( xs[0], miny, xs[1], maxy, pen )
        item.setZValue( Z_PHYSIC_ITEMS )
        return item

    def _sceneCompositeGeometryBuilder( self, scene, element ):
        x, y = self._elementXY( element )
        rotation = self._elementRotationInRadians( element )
        image, imagepos, imagescale, imagerot = self._elementImageWithPosScaleRot( element )
        sub_items = []
        if image:
            pixmap = self.getImagePixmap( image )
            if pixmap:
                item = scene.addPixmap( pixmap )
                self._applyPixmapTransform( item, pixmap, imagepos[0]-x, imagepos[1]-y,
                                            imagerot-rotation,
                                            imagescale[0], imagescale[1], 0 )
                sub_items.append( item )
        item = scene.createItemGroup( sub_items )
        self._applyTransform( item, 0, 0, x, y, rotation, 1.0, 1.0, Z_PHYSIC_ITEMS )
        return item

    def _sceneLinearForceFieldBuidler( self, scene, element ):
        # @todo ? Should we bother: gravity field usually does not have center, width & height
        x, y = self._elementV2Pos( element, 'center', (0, 0) )
        width = self._elementReal( element, 'width', 1.0 )
        height = self._elementReal( element, 'height', 1.0 )
        forcex, forcey = self._elementV2Pos( element, 'force', (0, 0.1) )
        depth = self._elementReal( element, 'height', Z_PHYSIC_ITEMS )
        # force zone item
        pen = QtGui.QPen( QtGui.QColor( 255, 224, 0 ) )
        pen.setWidth( 5 )
        sub_item1 = scene.addRect( 0, 0, width, height, pen )
        # force direction item
        sub_item2 = self._makeForceDirectionItem( scene, width/2.0, height/2.0, forcex, forcey )
        # item group with both force direction & force zone
        item = scene.createItemGroup( [sub_item1, sub_item2] )
        self._applyTransform( item, width/2.0, height/2.0, x, y, 0.0,
                              1.0, 1.0, depth )
        return item

    def _sceneRadialForceFieldBuilder( self, scene, element ):
        x, y = self._elementV2Pos( element, 'center', (0, 0) )
        r = self._elementReal( element, 'radius', 1.0 )
        force_at_edge = self._elementReal( element, 'forceatedge', 0.0 )
        force_at_center = self._elementReal( element, 'forceatcenter', 0.0 )
        # circular zone item
        pen = QtGui.QPen( QtGui.QColor( 255, 224, 0 ) )
        pen.setWidth( 5 )
        sub_item1 = scene.addEllipse( -r, -r, r*2, r*2, pen )
        # force at center item (from the center to down)
        sub_item2 = self._makeForceDirectionItem( scene, 0, 0, 0, force_at_center )
        # force at edge item (from ledge side of the circle to down)
        sub_item3 = self._makeForceDirectionItem( scene, -r, 0, 0, force_at_edge )
        # item group with both force direction & force zone
        item = scene.createItemGroup( [sub_item1, sub_item2, sub_item3] )
        self._setSceneItemXYZ( item, x, y )
        return item        

    def _makeForceDirectionItem( self, scene, x, y, forcex, forcey, force_factor = 20.0 ):
        forcex, forcey = forcex * force_factor, forcey * force_factor # to make direction more visible
        force_gradient = QtGui.QLinearGradient( x,y, x+forcex, y+forcey )
        force_gradient.setColorAt( 0.0, QtGui.QColor( 192, 64, 0 ) )
        force_gradient.setColorAt( 1.0, QtGui.QColor( 255, 160, 0 ) )
        force_pen = QtGui.QPen( QtGui.QBrush( force_gradient ), 4 )
        return scene.addLine( x, y, x+forcex, y+forcey, force_pen )

    def _sceneMotorBuilder( self, scene, element ):
        # Nothing to render...
        pass

    def _sceneHingeBuilder( self, scene, element ):
        # Similar to strand. Worth bothering rendering ?
        pass

    def _sceneParticlesBuilder( self, scene, element ):
        x, y = self._elementV2Pos( element, 'pos', (150,30) )
        font = QtGui.QFont()
        font.setPointSize( 24.0 )
        font.setBold( True )
        item = scene.addText( element.get('effect'), font )
        item.setDefaultTextColor( QtGui.QColor( 168, 28, 255 ) )
        self._setSceneItemXYZ( item, x,y )
        return item





def validate_enumerated_property( scope_key, attribute_desc, input ):
    type_name = attribute_desc.name
    is_list = attribute_desc.is_list
    input = unicode( input )
    input_values = input.split(',')
    if len(input_values) == 0:
        if is_list:
            return QtGui.QValidator.Acceptable
        return QtGui.QValidator.Intermediate, 'One %s value is required' % type_name
    elif len(input_values) != 1 and not is_list:
        return QtGui.QValidator.Intermediate, 'Only one %s value is allowed' % type_name
    for input_value in input_values:
        if input_value not in attribute_desc.values:
            return ( QtGui.QValidator.Intermediate, 'Invalid %s value: "%%1". Valid values: %%2' % type_name,
                     input_value, ','.join(attribute_desc.values) )
    return QtGui.QValidator.Acceptable

def complete_enumerated_property( scope_key, attribute_desc ):
    return sorted(attribute_desc.values)

def do_validate_numeric_property( attribute_desc, input, value_type, error_message ):
    try:
        value = value_type(str(input))
        if attribute_desc.min_value is not None and value < attribute_desc.min_value:
            return QtGui.QValidator.Intermediate, 'Value must be >= %1', str(attribute_desc.min_value)
        if attribute_desc.max_value is not None and value > attribute_desc.max_value:
            return QtGui.QValidator.Intermediate, 'Value must be < %1', str(attribute_desc.max_value)
        return QtGui.QValidator.Acceptable
    except ValueError:
        return QtGui.QValidator.Intermediate, error_message

def validate_integer_property( scope_key, attribute_desc, input ):
    return do_validate_numeric_property( attribute_desc, input, int, 'Value must be an integer' )

def validate_real_property( scope_key, attribute_desc, input ):
    return do_validate_numeric_property( attribute_desc, input, float, 'Value must be a real number' )

def validate_rgb_property( scope_key, attribute_desc, input ):
    input = unicode(input)
    values = input.split(',')
    if len(values) != 3:
        return QtGui.QValidator.Intermediate, 'RGB color must be of the form "R,G,B" were R,G,B are integer in range [0-255].'
    for name, value in zip('RGB', values):
        try:
            value = int(value)
            if value <0 or value >255:
                return QtGui.QValidator.Intermediate, 'RGB color component "%s" must be in range [0-255].' % name
        except ValueError:
            return QtGui.QValidator.Intermediate, 'RGB color must be of the form "R,G,B" were R,G,B are integer in range [0-255].'
    return QtGui.QValidator.Acceptable

def validate_xy_property( scope_key, attribute_desc, input ):
    input = unicode(input)
    values = input.split(',')
    if len(values) != 2:
        return QtGui.QValidator.Intermediate, 'Position must be of the form "X,Y" were X and Y are real number'
    for name, value in zip('XY', values):
        try:
            value = float(value)
        except ValueError:
            return QtGui.QValidator.Intermediate, 'Position must be of the form "X,Y" were X and Y are real number'
    return QtGui.QValidator.Acceptable

def validate_reference_property( scope_key, attribute_desc, input ):
    input = unicode(input)
    if scope_key.tracker.is_valid_reference( scope_key, attribute_desc, input ):
        return QtGui.QValidator.Acceptable
    return QtGui.QValidator.Intermediate, '"%%1" is not a valid reference to an object of type %s' % attribute_desc.reference_familly, input

def complete_reference_property( scope_key, attribute_desc ):
    return scope_key.tracker.list_identifiers( scope_key, attribute_desc.reference_familly )

# For later
##def editor_rgb_property( parent, option, index, element, attribute_desc, default_editor_factory ):
##    widget = QtGui.QWidget( parent )
##    hbox = QtGui.QHBoxLayout()
##    hbox.addWidget( default_editor_factory )
##    push_button = QtGui.QPushButton( 
##    hbox.addWidget( push_button )
    

# A dictionnary of specific handler for metawog attribute types.
# validator: called whenever the user change the input.
#           a callable(attribute_desc, input) returning either QtGui.QValidator.Acceptable if input is a valid value,
#           or a tuple (QtGui.QValidator.Intermediate, message, arg1, arg2...) if the input is invalid. Message must be
#           in QString format (e.g. %1 for arg 1...). The message is displayed in the status bar.
# converter: called when the user valid the input (enter key usualy) to store the edited value into the model.
#            a callable(editor, model, index, attribute_desc).
ATTRIBUTE_TYPE_EDITOR_HANDLERS = {
    metaworld.BOOLEAN_TYPE: { 'validator': validate_enumerated_property,
                              'converter': complete_enumerated_property },
    metaworld.ENUMERATED_TYPE: { 'validator': validate_enumerated_property,
                                 'completer': complete_enumerated_property },
    metaworld.INTEGER_TYPE: { 'validator': validate_integer_property },
    metaworld.REAL_TYPE: { 'validator': validate_real_property },
    metaworld.RGB_COLOR_TYPE: { 'validator': validate_rgb_property },
    metaworld.XY_TYPE: { 'validator': validate_xy_property },
    metaworld.ANGLE_DEGREES_TYPE:  { 'validator': validate_real_property },
    metaworld.REFERENCE_TYPE: { 'validator': validate_reference_property,
                                'completer': complete_reference_property }
    }

class PropertyValidator(QtGui.QValidator):
    def __init__( self, parent, main_window, scope_key, attribute_desc, validator ):
        QtGui.QValidator.__init__( self, parent )
        self.main_window = main_window
        self.attribute_desc = attribute_desc
        self.validator = validator
        self.scope_key = scope_key

    def validate( self, input, pos ):
        """Returns state & pos.
           Valid values for state are: QtGui.QValidator.Invalid, QtGui.QValidator.Acceptable, QtGui.QValidator.Intermediate.
           Returning Invalid actually prevent the user from inputing that a value that would make the input invalid. It is
           better to avoid returning this at it prevent temporary invalid value (when using cut'n'paste for example)."""
        status = self.validator( self.scope_key, self.attribute_desc, input )
        if type(status) == tuple:
            message = status[1]
            args = status[2:]
            status = status[0]
            message = self.tr(message)
            for arg in args:
                message = message.arg(arg)
            self.main_window.statusBar().showMessage(message, 1000)
        return ( status, pos )

class PropertyListItemDelegate(QtGui.QStyledItemDelegate):
    def __init__( self, parent, main_window ):
        QtGui.QStyledItemDelegate.__init__( self, parent )
        self.main_window = main_window

    def createEditor( self, parent, option, index ):
        """Returns the widget used to edit the item specified by index for editing. The parent widget and style option are used to control how the editor widget appears."""
        # see QDefaultItemEditorFactory::createEditor for example of implementations
        scope_key, object_file, element, property_name, attribute_desc, handler_data = self._getHandlerData( index )
        need_specific_editor = handler_data and handler_data.get('editor')
        if need_specific_editor:
            class DefaultEditorFactory(object):
                def __init__( self, *args ):
                    self.args = args
                def __call_( self, parent ):
                    return QtGui.QStyledItemDelegate.createEditor( args[0], parent, *(args[1:]) )
            editor = handler_data['editor']( parent, option, index, element, attribute_desc, DefaultEditorFactory() )
        else: # No specific, use default QLineEditor
            editor = QtGui.QStyledItemDelegate.createEditor( self, parent, option, index )
        if handler_data and handler_data.get('validator'):
            validator = PropertyValidator( editor, self.main_window, scope_key, attribute_desc, handler_data['validator'] )
            editor.setValidator( validator )
        if handler_data and handler_data.get('completer'):
            word_list = QtCore.QStringList()
            for word in sorted(handler_data.get('completer')( scope_key, attribute_desc )):
                word_list.append( word )
            completer = QtGui.QCompleter( word_list, editor )
            completer.setCaseSensitivity( QtCore.Qt.CaseInsensitive )
            completer.setCompletionMode( QtGui.QCompleter.UnfilteredPopupCompletion )
            editor.setCompleter( completer )
        return editor

    def _getHandlerData( self, index ):
        """Returns data related to item at the specified index.
           Returns: tuple (scope_key, object_file, element, property_name, attribute_desc, handler_data). 
           handler_data may be None if no specific handler is defined for the attribute_desc.
           attribute_desc may be None if metawog is missing some attribute declaration.
           """
        data =  index.data( QtCore.Qt.UserRole ).toPyObject()
        # if this fails, then we are trying to edit the property name or item was added incorrectly.
        assert data is not None
        scope_key, object_file, object_desc, element, property_name = data
        if object_desc is None:
            handler_data = None
            attribute_desc = None
            print 'Warning: metawog is incomplet, no attribute description for', object_file, element.tag, property_name
        else:
            attribute_desc = object_desc.attributes_by_name.get( property_name )
            if attribute_desc is None:
                print 'Warning: metawog is incomplet, no attribute description for', object_file, element.tag, property_name
                handler_data = None
            else:
                handler_data = ATTRIBUTE_TYPE_EDITOR_HANDLERS.get( attribute_desc.type )
        return (scope_key, object_file, element, property_name, attribute_desc, handler_data)

    def setEditorData( self, editor, index ):
        """Sets the data to be displayed and edited by the editor from the data model item specified by the model index."""
        scope_key, object_file, element, property_name, attribute_desc, handler_data = self._getHandlerData( index )
        editor.setText( element.get( property_name, u'' ) )
#        QtGui.QStyledItemDelegate.setEditorData( self, editor, index )


    def setModelData( self, editor, model, index ):
        """Gets data drom the editor widget and stores it in the specified model at the item index.
           setModelData() is called by either.
           - QAbstractItemView::commitData, which itself may be called by the signal QAbstractItemDelegate::commitData
             which can be emitted by:
             - QItemDelegatePrivate::_q_commitDataAndCloseEditor
             - QItemDelegate::eventFilter, on Tab, BackTab, FocusOut
             - QStyledItemDelegate::eventFilter (looks like a big copy/paste of the above one)
           - or QAbstractItemView::currentChanged, when the current item change
           Conclusion: we set the data into the model, only if they are valid as QLineEdit validation may have
           been by-passed on focus change or current item change.
        """
        scope_key, object_file, element, property_name, attribute_desc, handler_data = self._getHandlerData( index )
        if not editor.hasAcceptableInput(): # input is invalid, discard it
            return
        need_specific_converter = handler_data and handler_data.get('converter')
        if need_specific_converter:
            handler_data['converter']( editor, model, index, attribute_desc )
        else:
##            value = editor.text()
##            model.setData(index, QtCore.QVariant( value ), QtCore.Qt.EditRole)
            QtGui.QStyledItemDelegate.setModelData( self, editor, model, index )


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self._wog_path = None # Path to worl of goo executable

        self.createMDIArea()
        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.createStatusBar()
        self.createDockWindows()
        self.setWindowTitle(self.tr("WOG Editor"))
        
        self._readSettings()


        self._game_model = None
        if self._wog_path:
            self._reloadGameModel()
        else:
            print self._wog_path

    def changeWOGDir(self):
        wog_path =  QtGui.QFileDialog.getOpenFileName( self,
             self.tr( 'Select the file WorldOfGoo.exe to locate WOG top directory' ),
             r'e:\jeux\WorldOfGoo-mod',
             self.tr( 'WorldOfGoo.exe (WorldOfGoo.exe)' ) )
        if wog_path.isEmpty(): # user canceled action
            return
        self._wog_path = unicode(wog_path)
        self._reloadGameModel()

    def _reloadGameModel( self ):
        try:
            self._game_model = GameModel( self._wog_path )
            self.connect( self._game_model, QtCore.SIGNAL('currentModelChanged(PyQt_PyObject,PyQt_PyObject)'),
                          self._refreshLevel )
            self.connect( self._game_model, QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                          self._refreshOnSelectedObjectChange )
            self.connect( self._game_model, QtCore.SIGNAL('objectAdded(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                          self._refreshOnObjectInsertion )
            self.connect( self._game_model, QtCore.SIGNAL('objectRemoved(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                          self._refreshOnObjectRemoval )
        except GameModelException, e:
            QtGui.QMessageBox.warning(self, self.tr("Loading WOG levels"),
                                      unicode(e))

    def _refreshOnObjectInsertion( self, level_name, object_file, parent_element, element, index ):
        """Called when an object is added to the tree.
        """
        tree_view = self.tree_view_by_object_scope[object_file]
        parent_item = self._findItemInTreeViewByElement( tree_view, parent_element )
        if parent_item:
            self._insertElementNodeInTree( parent_item, element, index )
        else:
            print 'Warning: parent_element not found in tree view', parent_element

    def _refreshOnObjectRemoval( self, level_name, object_file, parent_elements, element, index_in_parent ):
        """Called when an object is removed from its tree.
        """
        tree_view = self.tree_view_by_object_scope[object_file]
        item = self._findItemInTreeViewByElement( tree_view, element )
        if item:
            item_row = item.row()
            item.parent().removeRow( item_row )
        # Notes: selection will be automatically switched to the previous row in the tree view.

    def _refreshLevel( self, old_model, new_game_level_model ):
        """Refresh the tree views and property list on level switch."""
        self._refreshElementTree( self.sceneTree, new_game_level_model.scene_tree )
        self._refreshElementTree( self.levelTree, new_game_level_model.level_tree )
        self._refreshElementTree( self.levelResourceTree, new_game_level_model.resource_tree )
        self._refreshGraphicsView( new_game_level_model )

    def _refreshElementTree( self, element_tree_view, root_element ):
        """Refresh a tree view using its root element."""
        element_tree_view.model().clear()
        root_item = self._insertElementTreeInTree( element_tree_view.model(), root_element )
        element_tree_view.setExpanded( root_item.index(), True )

    def _insertElementTreeInTree( self, item_parent, element, index = None ):
        """Inserts a sub-tree of item in item_parent at the specified index corresponding to the tree of the specified element.
           Returns the new root item of the sub-tree.
           index: if None, append the new sub-tree after all the parent chidlren.
        """
        items_to_process = [ (item_parent, element, index) ]
        root_item = None
        while items_to_process:
            item_parent, element, index = items_to_process.pop(0)
            item = self._insertElementNodeInTree( item_parent, element, index )
            if root_item is None:
                root_item = item
            for child_element in element:
                items_to_process.append( (item, child_element, None) )
        return root_item

    def _insertElementNodeInTree( self, item_parent, element, index = None ):
        """Inserts a single child node in item_parent at the specified index corresponding to the specified element and returns item.
           index: if None, append the new child item after all the parent chidlren.
        """
        if index is None:
            index = item_parent.rowCount()
        item = QtGui.QStandardItem( element.tag )
        item.setData( QtCore.QVariant( element ), QtCore.Qt.UserRole )
        item.setFlags( item.flags() & ~QtCore.Qt.ItemIsEditable )
        item_parent.insertRow( index, item )
        return item
                    
    def _refreshGraphicsView( self, game_level_model ):
        level_mdi = self._findLevelGraphicView( game_level_model.level_name )
        if level_mdi:
            level_view = level_mdi.widget()
            level_view.refreshFromModel( game_level_model )
        
    def _onElementTreeSelectionChange( self, tree_view, object_file, selected, deselected ):
        """Called whenever the scene tree selection change."""
        selected_indexes = selected.indexes()
        if len( selected_indexes ) == 1: # Do not handle multiple selection yet
            item = tree_view.model().itemFromIndex( selected_indexes[0] )
            element = item.data( QtCore.Qt.UserRole ).toPyObject()
            game_level_model = self.getCurrentLevelModel()
            if game_level_model:
                game_level_model.objectSelected( object_file, element )

    def _refreshOnSelectedObjectChange( self, level_name, object_file, element ):
        self._refreshPropertyListFromElement( object_file, element )
        self._refreshSceneTreeSelection( object_file, element )

    def _findItemInTreeViewByElement( self, tree_view, element ):
        for item in qthelper.standardModelTreeItems( tree_view.model() ):
            if item.data( QtCore.Qt.UserRole ).toPyObject() is element:
                return item
        return None

    def _refreshSceneTreeSelection( self, object_file, element ):
        """Select the item corresponding to element in the tree view.
        """
        tree_view = self.tree_view_by_object_scope[object_file]
        for other_tree_view in self.tree_view_by_object_scope.itervalues():  
            if other_tree_view != tree_view: # unselect objects on all other tree views
                other_tree_view.selectionModel().clear()
        selected_item = self._findItemInTreeViewByElement( tree_view, element )
        if selected_item:
            selected_index = selected_item.index()
            selection_model = tree_view.selectionModel()
            selection_model.select( selected_index, QtGui.QItemSelectionModel.ClearAndSelect )
            tree_view.setExpanded( selected_index, True )
            tree_view.parent().raise_() # Raise the dock windows associated to the tree view
            tree_view.scrollTo( selected_index )
        else:
            print 'Warning: selected item not found in tree view.', tree_view, object_file, element

    def _refreshPropertyListFromElement( self, object_file, element ):
        # Order the properties so that main attributes are at the beginning
        object_desc = object_file.find_object_desc_by_tag(element.tag)
        if object_desc is None:  # path for data without meta-model (to be removed)
            attribute_names = element.keys()
            attribute_order = ( 'id', 'name', 'x', 'y', 'depth', 'radius',
                                'rotation', 'scalex', 'scaley', 'image', 'alpha' )
            ordered_attributes = []
            for name in attribute_order:
                try:
                    index = attribute_names.index( name )
                except ValueError: # name not found
                    pass
                else: # name found
                    del attribute_names[index]
                    ordered_attributes.append( (name, element.get(name)) )
            ordered_attributes.extend( [ (name, element.get(name)) for name in attribute_names ] )
            # Update the property list model
            self._resetPropertyListModel()
            for name, value in ordered_attributes:
                item_name = QtGui.QStandardItem( name )
                item_name.setEditable( False )
                item_value = QtGui.QStandardItem( value )
                # @todo object_desc & scope_key should be parameters...
                object_desc = object_file.find_object_desc_by_tag(element.tag)
                scope_key = self.getCurrentLevelModel()
                item_value.setData( QtCore.QVariant( (scope_key, object_file, object_desc, element, name) ), QtCore.Qt.UserRole )
                self.propertiesListModel.appendRow( [ item_name, item_value ] )
        else: # Update the property list using the model
            self._resetPropertyListModel()
            scope_key = self.getCurrentLevelModel()
            missing_attributes = set( element.keys() )
            for attribute_desc in object_desc.attributes_order:
                attribute_name = attribute_desc.name
                if attribute_name in missing_attributes:
                    missing_attributes.remove( attribute_name )
                attribute_value = element.get( attribute_name )
                item_name = QtGui.QStandardItem( attribute_name )
                item_name.setEditable( False )
                if attribute_value is not None: # bold property name for defined property
                    font = item_name.font()
                    font.setBold( True )
                    if attribute_value is None and attribute_desc.mandatory:
                        # @todo Also put name in red if value is not valid.
                        brush = QtGui.QBrush( QtGui.QColor( 255, 0, 0 ) )
                        font.setForeground( brush )
                    item_name.setFont( font )
                item_value = QtGui.QStandardItem( attribute_value or '' )
                item_value.setData( QtCore.QVariant( (scope_key, object_file, object_desc, element, attribute_name) ),
                                    QtCore.Qt.UserRole )
                self.propertiesListModel.appendRow( [ item_name, item_value ] )
            if missing_attributes:
                print 'Warning: The following attributes of "%s" are missing in metaworld:' % element.tag, ', '.join( missing_attributes )

    def editLevel( self ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = editleveldialog_ui.Ui_EditLevelDialog()
            ui.setupUi( dialog )
            for level_name in self._game_model.level_names:
                ui.levelList.addItem( level_name )
            if dialog.exec_() and ui.levelList.currentItem:
                level_name = unicode( ui.levelList.currentItem().text() )
                try:
                    self._game_model.selectLevel( level_name )
                except GameModelException, e:
                    QtGui.QMessageBox.warning(self, self.tr("Failed to load level!"),
                              unicode(e))
                else:
                    sub_window = self._findLevelGraphicView( level_name )
                    if sub_window:
                        self.mdiArea.setActiveSubWindow( sub_window )
                    else:
                        self._addLevelGraphicView( level_name )

    def _addLevelGraphicView( self, level_name ):
        """Adds a new MDI LevelGraphicView window for the specified level."""
        view = LevelGraphicView( level_name, self._game_model )
        sub_window = self.mdiArea.addSubWindow( view )
        self.connect( view, QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'),
                      self._updateMouseScenePosInStatusBar )
        self.connect( sub_window, QtCore.SIGNAL('aboutToActivate()'),
                      view.selectLevelOnSubWindowActivation )
        view.show()

    def _updateMouseScenePosInStatusBar( self, x, y ):
        """Called whenever the mouse move in the scene view."""
        y = -y # Reverse transformation done when mapping to scene (in Qt 0 = top, in WOG 0 = bottom)
        self._mousePositionLabel.setText( self.tr('x: %1 y: %2').arg(x).arg(y) )

    def _findLevelGraphicView( self, level_name ):
        """Search for an existing MDI window for level level_name.
           Return the LevelGraphicView widget, or None if not found."""
        for window in self.mdiArea.subWindowList():
            sub_window = window.widget()
            if sub_window.matchModel( MODEL_TYPE_LEVEL, level_name ):
                return window
        return None
        
    def getCurrentLevelModel( self ):
        """Returns the level model of the active MDI window."""
        window = self.mdiArea.activeSubWindow()
        if window:
            return window.widget().getLevelModel()
        return None

    def _onPropertyListValueChanged( self, top_left_index, bottom_right_index ):
        """Called the data of a property list item changed.
           Update the corresponding value in the level model and broadcast the event to refresh the scene view.
           """
        if top_left_index.row() != bottom_right_index.row():
            print 'Warning: edited non editable row!!!'
            return # not the result of an edit
        new_value = top_left_index.data( QtCore.Qt.DisplayRole ).toString()
        data = top_left_index.data( QtCore.Qt.UserRole ).toPyObject()
        if data:
            scope_key, object_file, object_desc, element, property_name = data
            self.getCurrentLevelModel().updateObjectPropertyValue( object_file, element, property_name, str(new_value) )
        else:
            print 'Warning: no data on edited item!'

    def _onTreeViewCustomContextMenu( self, tree_view, object_file, menu_pos ):
        # Select the right clicked item
        index = tree_view.indexAt(menu_pos)
        if index.isValid():
            element = index.data( QtCore.Qt.UserRole ).toPyObject()
            if element is None:
                print 'Warning: somehow managed to activate context menu on non item???'
            else:
                selection_model = tree_view.selectionModel()
                selection_model.select( index, QtGui.QItemSelectionModel.ClearAndSelect )
                # Notes: a selectionChanged signal may have been emitted due to selection change.
                # Check out FormWindow::initializePopupMenu in designer, it does plenty of interesting stuff...
                menu = QtGui.QMenu( tree_view )
                remove_action = menu.addAction( self.tr("Remove element") )
                menu.addSeparator()
                if index.parent() is None:
                    remove_action.setEnable( False )
                tag_by_actions = {}
                object_desc = object_file.find_object_desc_by_tag(element.tag)
                for tag in sorted(object_desc.objects_by_tag.iterkeys()):
                    if not object_desc.find_immediate_child_by_tag(tag).read_only:
                        action = menu.addAction( self.tr("Add child %1").arg(tag) )
                        tag_by_actions[action] = tag
                selected_action = menu.exec_( tree_view.viewport().mapToGlobal(menu_pos) )
                selected_tag = tag_by_actions.get( selected_action )
                if selected_tag:
                    self._appendChildTag( tree_view, object_file, index, selected_tag )
                elif selected_action is remove_action:
                    element_to_remove = tree_view.model().itemFromIndex( index ).data( QtCore.Qt.UserRole ).toPyObject()
                    self.getCurrentLevelModel().removeElement( object_file, element_to_remove )

    def _appendChildTag( self, tree_view, object_file, parent_element_index, new_tag ):
        """Adds the specified child tag to the specified element and update the tree view."""
        parent_element = parent_element_index.data( QtCore.Qt.UserRole ).toPyObject()
        if parent_element is not None:
            # build the list of attributes with their initial values.
            object_desc = object_file.find_object_desc_by_tag(new_tag)
            mandatory_attributes = {}
            for attribute_name, attribute_desc in object_desc.attributes_by_name.iteritems():
                if attribute_desc.mandatory:
                    init_value = attribute_desc.init
                    if init_value is None:
                        init_value = ''
                    mandatory_attributes[attribute_name] = init_value
            # Creates and append to parent the new child element
            child_element = xml.etree.ElementTree.Element( new_tag, mandatory_attributes )
            # Notes: when the element is added, the objectAdded() signal will cause the
            # corresponding item to be inserted into the tree.
            self.getCurrentLevelModel().addElement( object_file, parent_element, child_element )
            # Select new item in tree view
            item_child = self._findItemInTreeViewByElement( tree_view, child_element )
            selection_model = tree_view.selectionModel()
            selection_model.select( item_child.index(), QtGui.QItemSelectionModel.ClearAndSelect )
            tree_view.scrollTo( item_child.index() )
        else:
            print 'Warning: attempting to add an element to an item without associated elements!', parent_element, parent_element_index

    def save(self):
        """Saving all modified elements.
        """
        if self._game_model:
            had_modified_readonly_level = self._game_model.hasModifiedReadOnlyLevels()
            try:
                try:
                    QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                    self._game_model.save()
                finally:
                    QtGui.QApplication.restoreOverrideCursor()
                self.statusBar().showMessage(self.tr("Saved all modified levels"), 2000)
                if had_modified_readonly_level:
                    QtGui.QMessageBox.warning(self, self.tr("Can not save save World Of Goo standard level!"),
                              self.tr('You can not save change made to levels that comes with World Of Goo.\n'
                                      'Instead, clone the standard level using the clone selected level tool.\n'
                                      'Do so now, or your change will be lost once you quit the editor' ) )
                else:
                    return True
            except IOError, e:
                QtGui.QMessageBox.warning(self, self.tr("Failed saving levels"),
                          unicode(e))
        return False

    def saveAndPlayLevel(self):
        if self.save():
            level_model = self.getCurrentLevelModel()
            if level_model:
                self._game_model.playLevel( level_model.level_name )
            else:
                self.statusBar().showMessage(self.tr("You must select a level to play"), 2000)

    def newLevel( self ):
        """Creates a new blank level."""
        new_level_name = self._pickNewLevelName( is_cloning = False )
        if new_level_name:
            try:
                self._game_model.newLevel( new_level_name )
                self._game_model.selectLevel( new_level_name )
                self._addLevelGraphicView( new_level_name )
            except IOError, e:
                QtGui.QMessageBox.warning(self, self.tr("Failed to create the new level!"),
                                          unicode(e))

    def _pickNewLevelName( self, is_cloning = False ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = newleveldialog_ui.Ui_NewLevelDialog()
            ui.setupUi( dialog )
            reg_ex = QtCore.QRegExp( '[0-9A-Za-z]+' )
            validator = QtGui.QRegExpValidator( reg_ex, dialog )
            ui.levelName.setValidator( validator )
            if is_cloning:
                dialog.setWindowTitle(tr("NewLevelDialog", "Cloning Level"))
     
            if dialog.exec_():
                new_level_name = str(ui.levelName.text())
                existing_names = [name.lower() for name in self._game_model.level_names]
                if new_level_name.lower() not in existing_names:
                    return new_level_name
                QtGui.QMessageBox.warning(self, self.tr("Can not create level!"),
                    self.tr("There is already a level named '%1'").arg(new_level_name))
        return None

    def cloneLevel( self ):
        """Clone the selected level."""
        current_level_model = self.getCurrentLevelModel()
        if current_level_model:
            new_level_name = self._pickNewLevelName( is_cloning = False )
            if new_level_name:
                try:
                    self._game_model.cloneLevel( current_level_model.level_name, new_level_name )
                    self._game_model.selectLevel( new_level_name )
                    self._addLevelGraphicView( new_level_name )
                except IOError, e:
                    QtGui.QMessageBox.warning(self, self.tr("Failed to create the new cloned level!"),
                                              unicode(e))

    def updateLevelResources( self ):
        """Adds the required resource in the level based on existing file."""
        level_model = self.getCurrentLevelModel()
        if level_model:
            added_resource_elements = level_model.updateLevelResources()
            if added_resource_elements:
                level_model.objectSelected( metawog.LEVEL_RESOURCE_FILE, added_resource_elements[0] )

    def undo( self ):
        pass
        
    def about(self):
        QtGui.QMessageBox.about(self, self.tr("About WOG Editor"),
            self.tr("""<p>The <b>WOG editor</b> helps you create new level in WOG.<p>
            <p>Link to Sourceforge project:
            <a href="http://www.sourceforge.net/projects/wogedit">http://www.sourceforge.net/projects/wogedit</a></p>
            <p>Copyright 2008, NitroZark &lt;nitrozark at users.sourceforget.net&gt;</p>"""))

    def onRefreshAction( self ):
        """Called multiple time per second. Used to refresh enabled flags of actions."""
        has_wog_dir = self._game_model is not None
        is_level_selected = self.getCurrentLevelModel() is not None

        self.editLevelAction.setEnabled( has_wog_dir )
        self.newLevelAction.setEnabled( has_wog_dir )
        self.cloneLevelAction.setEnabled( is_level_selected )
        can_save = has_wog_dir and self._game_model.is_dirty
        self.saveAction.setEnabled( can_save and True or False )
        self.playAction.setEnabled( is_level_selected )
        self.updateLevelResourcesAction.setEnabled( is_level_selected )

    def createMDIArea( self ):
        self.mdiArea = QtGui.QMdiArea()
        self.setCentralWidget(self.mdiArea)
    
    def createActions(self):
        self.changeWOGDirAction = QtGui.QAction(QtGui.QIcon(":/images/open.png"), self.tr("&Change WOG directory..."), self)
        self.changeWOGDirAction.setShortcut(self.tr("Ctrl+O"))
        self.changeWOGDirAction.setStatusTip(self.tr("Change World Of Goo top-directory"))
        self.connect(self.changeWOGDirAction, QtCore.SIGNAL("triggered()"), self.changeWOGDir)

        self.editLevelAction = QtGui.QAction(QtGui.QIcon(":/images/open-level.png"), self.tr("&Edit existing level..."), self)
        self.editLevelAction.setShortcut(self.tr("Ctrl+L"))
        self.editLevelAction.setStatusTip(self.tr("Select a level to edit"))
        self.connect(self.editLevelAction, QtCore.SIGNAL("triggered()"), self.editLevel)

        self.newLevelAction = QtGui.QAction(QtGui.QIcon(":/images/new-level.png"), self.tr("&New level..."), self)
        self.newLevelAction.setShortcut(self.tr("Ctrl+N"))
        self.newLevelAction.setStatusTip(self.tr("Creates a new level"))
        self.connect(self.newLevelAction, QtCore.SIGNAL("triggered()"), self.newLevel)

        self.cloneLevelAction = QtGui.QAction(QtGui.QIcon(":/images/clone-level.png"), self.tr("&Clone selected level..."), self)
        self.cloneLevelAction.setShortcut(self.tr("Ctrl+D"))
        self.cloneLevelAction.setStatusTip(self.tr("Clone the selected level"))
        self.connect(self.cloneLevelAction, QtCore.SIGNAL("triggered()"), self.cloneLevel)
        
        self.saveAction = QtGui.QAction(QtGui.QIcon(":/images/save.png"), self.tr("&Save..."), self)
        self.saveAction.setShortcut(self.tr("Ctrl+S"))
        self.saveAction.setStatusTip(self.tr("Save all changes made to the game"))
        self.connect(self.saveAction, QtCore.SIGNAL("triggered()"), self.save)
        
        self.playAction = QtGui.QAction(QtGui.QIcon(":/images/play.png"), self.tr("&Save and play Level..."), self)
        self.playAction.setShortcut(self.tr("Ctrl+P"))
        self.playAction.setStatusTip(self.tr("Save all changes and play the selected level"))
        self.connect(self.playAction, QtCore.SIGNAL("triggered()"), self.saveAndPlayLevel)
        
        self.updateLevelResourcesAction = QtGui.QAction(QtGui.QIcon(":/images/update-level-resources.png"),
                                                        self.tr("&Update level resources..."), self)
        self.updateLevelResourcesAction.setShortcut(self.tr("Ctrl+U"))
        self.updateLevelResourcesAction.setStatusTip(self.tr("Adds automatically all .png & .ogg files in the level directory to the level resources"))
        self.connect(self.updateLevelResourcesAction, QtCore.SIGNAL("triggered()"), self.updateLevelResources)

##        self.undoAct = QtGui.QAction(QtGui.QIcon(":/images/undo.png"), self.tr("&Undo"), self)
##        self.undoAct.setShortcut(self.tr("Ctrl+Z"))
##        self.undoAct.setStatusTip(self.tr("Undo the last action"))
##        self.connect(self.undoAct, QtCore.SIGNAL("triggered()"), self.undo)

        self.quitAct = QtGui.QAction(self.tr("&Quit"), self)
        self.quitAct.setShortcut(self.tr("Ctrl+Q"))
        self.quitAct.setStatusTip(self.tr("Quit the application"))
        self.connect(self.quitAct, QtCore.SIGNAL("triggered()"), self.close)
        
        self.aboutAct = QtGui.QAction(self.tr("&About"), self)
        self.aboutAct.setStatusTip(self.tr("Show the application's About box"))
        self.connect(self.aboutAct, QtCore.SIGNAL("triggered()"), self.about)

        actionTimer = QtCore.QTimer( self )
        self.connect( actionTimer, QtCore.SIGNAL("timeout()"), self.onRefreshAction )
        actionTimer.start( 250 )    # Refresh action enabled flag every 250ms.

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.changeWOGDirAction)
        self.fileMenu.addAction(self.editLevelAction)
        self.fileMenu.addAction(self.newLevelAction)
        self.fileMenu.addAction(self.cloneLevelAction)
        self.fileMenu.addAction(self.saveAction)
        self.fileMenu.addAction(self.playAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAct)
        
        self.editMenu = self.menuBar().addMenu(self.tr("&Edit"))
        self.editMenu.addAction( self.updateLevelResourcesAction )
##        self.editMenu.addAction(self.editLevelAction)
        
        self.menuBar().addSeparator()

        # @todo add Windows menu. Take MDI example as model.        
        
        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.addAction(self.aboutAct)

    def createToolBars(self):
        self.fileToolBar = self.addToolBar(self.tr("File"))
        self.fileToolBar.addAction(self.changeWOGDirAction)
        self.fileToolBar.addAction(self.editLevelAction)
        self.fileToolBar.addAction(self.newLevelAction)
        self.fileToolBar.addAction(self.cloneLevelAction)
        self.fileToolBar.addAction(self.saveAction)
        self.fileToolBar.addAction(self.playAction)
        
        self.editToolBar = self.addToolBar(self.tr("Edit"))
        self.editToolBar.addAction( self.updateLevelResourcesAction )
##        self.editToolBar.addAction(self.undoAct)
        
    def createStatusBar(self):
        self.statusBar().showMessage(self.tr("Ready"))
        self._mousePositionLabel = QtGui.QLabel()
        self.statusBar().addPermanentWidget( self._mousePositionLabel )

    def createElementTreeView(self, name, object_file, sibling_tabbed_dock = None ):
        dock = QtGui.QDockWidget( self.tr( name ), self )
        dock.setAllowedAreas( QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea )
        element_tree_view = QtGui.QTreeView( dock )
        tree_model = QtGui.QStandardItemModel(0, 1, element_tree_view)  # nb rows, nb cols
        tree_model.setHorizontalHeaderLabels( [self.tr('Element')] )
        element_tree_view.setModel( tree_model )
        dock.setWidget( element_tree_view )
        self.addDockWidget( QtCore.Qt.RightDockWidgetArea, dock )
        if sibling_tabbed_dock: # Stacks the dock widget together
            self.tabifyDockWidget( sibling_tabbed_dock, dock )
        class TreeBinder(object):
            def __init__( self, tree_view, object_file, handler ):
                self.__tree_view = tree_view
                self.__object_type = object_file
                self.__handler = handler

            def __call__( self, *args ):
                self.__handler( self.__tree_view, self.__object_type, *args )
        # On tree node selection change
        selection_model = element_tree_view.selectionModel()
        self.connect( selection_model, QtCore.SIGNAL("selectionChanged(QItemSelection,QItemSelection)"),
                      TreeBinder( element_tree_view, object_file, self._onElementTreeSelectionChange) )
        # Hook context menu popup signal
        element_tree_view.setContextMenuPolicy( QtCore.Qt.CustomContextMenu )
        self.connect( element_tree_view, QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                      TreeBinder( element_tree_view, object_file, self._onTreeViewCustomContextMenu) )
        self.tree_view_by_object_scope[object_file] = element_tree_view
        return dock, element_tree_view
        
    def createDockWindows(self):
        self.tree_view_by_object_scope = {} # map of all tree views
        scene_dock, self.sceneTree = self.createElementTreeView( 'Scene', metawog.LEVEL_SCENE_FILE )
        level_dock, self.levelTree = self.createElementTreeView( 'Level', metawog.LEVEL_GAME_FILE, scene_dock )
        resource_dock, self.levelResourceTree = self.createElementTreeView( 'Resource',
                                                                            metawog.LEVEL_RESOURCE_FILE,
                                                                            level_dock )
        scene_dock.raise_() # Makes the scene the default active tab
        
        dock = QtGui.QDockWidget(self.tr("Properties"), self)
        self.propertiesList = QtGui.QTreeView(dock)
        self.propertiesList.setRootIsDecorated( False )
        self.propertiesList.setAlternatingRowColors( True )

        self.propertiesListModel = QtGui.QStandardItemModel(0, 2, self.propertiesList)  # nb rows, nb cols
        self._resetPropertyListModel()
        self.propertiesList.setModel( self.propertiesListModel )
        delegate = PropertyListItemDelegate( self.propertiesList, self )
        self.propertiesList.setItemDelegate( delegate )
        dock.setWidget(self.propertiesList)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        self.connect(self.propertiesListModel, QtCore.SIGNAL("dataChanged(const QModelIndex&,const QModelIndex&)"),
                     self._onPropertyListValueChanged)

    def _resetPropertyListModel( self ):
        self.propertiesListModel.clear()
        self.propertiesListModel.setHorizontalHeaderLabels( [self.tr('Name'), self.tr('Value')] )

    def _readSettings( self ):
        """Reads setting from previous session & restore window state."""
        settings = QtCore.QSettings()
        settings.beginGroup( "MainWindow" )
        self._wog_path = unicode( settings.value( "wog_path", QtCore.QVariant(u'') ).toString() )
        self.resize( settings.value( "size", QtCore.QVariant( QtCore.QSize(640,480) ) ).toSize() )
        self.move( settings.value( "pos", QtCore.QVariant( QtCore.QPoint(200,200) ) ).toPoint() )
        settings.endGroup()

    def _writeSettings( self ):
        """Persists the session window state for future restoration."""
        # Settings should be stored in HKEY_CURRENT_USER\Software\WOGCorp\WOG Editor
        settings = QtCore.QSettings() #@todo makes helper to avoid QVariant conversions
        settings.beginGroup( "MainWindow" )
        settings.setValue( "wog_path", QtCore.QVariant( QtCore.QString(self._wog_path or u'') ) )
        settings.setValue( "size", QtCore.QVariant( self.size() ) )
        settings.setValue( "pos", QtCore.QVariant( self.pos() ) )
        settings.endGroup()

    def closeEvent( self, event ):
        """Called when user close the main window."""
        #@todo check if user really want to quit
        if True:
            self._writeSettings()
            event.accept()
        else:
            event.ignore()

        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    # Set keys for settings
    app.setOrganizationName( "WOGCorp" )
    app.setOrganizationDomain( "wogedit.sourceforge.net" )
    app.setApplicationName( "Wog Editor" )
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())
