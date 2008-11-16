# The level editor GUI.

# The following workflow is expected:
# 1) User load a level
# 2) main windows display the scene layout
#    right-side-top-dock display:
#   - level scene tree
#   - level tree (a list in fact)
#   - level resources tree (a list in fact)
# 3) user select an element in one of the tree, related properties are displayed in
#    right-side-down-dock property list
# 4) user edit properties in property list
#
# Later on, provides property edition via scene layout display
# Add toolbar to create new element
#
# In memory, we keep track of two things:
# - updated level
# - specific text/fx resources 

import sys
import os
import os.path
import glob
import math
import subprocess
import louie
import wogfile
import metaworld
import metawog
import metaworldui
import metatreeui
import metaelementui
import xml.etree.ElementTree 
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import editleveldialog_ui
import newleveldialog_ui
import wogeditor_rc #IGNORE:W0611

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

class GameModelException(Exception):
    pass

class PixmapCache(object):
    def __init__(self, wog_dir, universe):
        self._wog_dir = wog_dir
        self._pixmaps_by_element = {}
        self.__event_synthetizer = metaworld.ElementEventsSynthetizer(universe,
            None,
            self._on_element_updated, 
            self._on_element_about_to_be_removed )
        
    def get_pixmap(self, image_element):
        """Returns a pixmap corresponding to the image_element.
           The pixmap is loaded if not present in the cache.
           None is returned on failure to load the pixmap.
        """
        assert image_element.tag == 'Image'
        pixmap = self._pixmaps_by_element.get( image_element )
        if pixmap:
            return pixmap
        path = os.path.join( self._wog_dir, image_element.get('path','') + '.png' )
        if not os.path.isfile(path):
            print 'Warning: invalid image path for "%(id)s": "%(path)s"' % \
                image_element.attributes
        else:
            pixmap = QtGui.QPixmap()
            if pixmap.load( path ):
                self._pixmaps_by_element[image_element] = pixmap
                return pixmap
            else:
                print 'Warning: failed to load image "%(id)s": "%(path)s"' % \
                    image_element.attributes
        return None

    def _on_element_about_to_be_removed(self, element, index_in_parent): #IGNORE:W0613
        if element in self._pixmaps_by_element:
            del self._pixmaps_by_element[element]

    def _on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        if element in self._pixmaps_by_element:
            del self._pixmaps_by_element[element]
    

class GameModel(QtCore.QObject):
    def __init__( self, wog_path ):
        """Loads FX, material, text and global resources.
           Loads Balls
           Loads Levels

           The following signals are provided:
           QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)')
        """
        QtCore.QObject.__init__( self )
        self._wog_path = wog_path
        self._wog_dir = os.path.split( wog_path )[0]
        properties_dir = os.path.join( self._wog_dir, u'properties' )
        self._res_dir = os.path.join( self._wog_dir, u'res' )
        self._universe = metaworld.Universe()
        self.global_world = self._universe.make_world( metawog.WORLD_GLOBAL, 'global' )
        self._effects_tree = self._loadTree( self.global_world, metawog.TREE_GLOBAL_FX,
                                             properties_dir, 'fx.xml.bin' )
        self._materials_tree = self._loadTree( self.global_world, metawog.TREE_GLOBAL_MATERIALS,
                                               properties_dir, 'materials.xml.bin' )
        self._resources_tree = self._loadTree( self.global_world, metawog.TREE_GLOBAL_RESOURCE,
                                               properties_dir, 'resources.xml.bin' )
        self._readonly_resources = set()    # resources in resources.xml that have expanded defaults idprefix & path
        self._texts_tree = self._loadTree( self.global_world, metawog.TREE_GLOBAL_TEXT,
                                           properties_dir, 'text.xml.bin' )
        self._levels = self._loadDirList( os.path.join( self._res_dir, 'levels' ), 
                                          filename_filter = '%s.scene.bin' )
        self.level_models_by_name = {}
        self.__is_dirty = False
        self._initializeGlobalReferences()
        self._loadBalls()
        self.modified_worlds_to_check = set()
        louie.connect( self._onElementAdded, metaworld.ElementAdded )
        louie.connect( self._onElementAboutToBeRemoved, metaworld.ElementAboutToBeRemoved )
        louie.connect( self._onElementUpdated, metaworld.AttributeUpdated )
        self.pixmap_cache = PixmapCache( self._wog_dir, self._universe )

    @property
    def is_dirty(self):
        worlds = self.modified_worlds_to_check
        self.modified_worlds_to_check = set()
        for world in worlds:
            if world:
                self.__is_dirty = self.__is_dirty or world.is_dirty
        return self.__is_dirty

    def getResourcePath( self, game_dir_relative_path ):
        return os.path.join( self._wog_dir, game_dir_relative_path )

    def _loadTree( self, world, meta_tree, directory, file_name ):
        path = os.path.join( directory, file_name )
        if not os.path.isfile( path ):
            raise GameModelException( tr( 'LoadData',
                'File "%1" does not exist. You likely provided an incorrect WOG directory.' ).arg( path ) )
        xml_data = wogfile.decrypt_file_data( path )
        return world.make_tree_from_xml( meta_tree, xml_data )

    def _savePackedData( self, directory, file_name, element_tree ):
        path = os.path.join( directory, file_name )
        xml_data = xml.etree.ElementTree.tostring( element_tree )
        wogfile.encrypt_file_data( path, xml_data )

    def _loadDirList( self, directory, filename_filter ):
        if not os.path.isdir( directory ):
            raise GameModelException( tr('LoadLevelList',
                'Directory "%1" does not exist. You likely provided an incorrect WOG directory.' ).arg( directory ) )
        def is_valid_dir( entry ):
            """Accepts the directory only if it contains a specified file."""
            dir_path = os.path.join( directory, entry )
            if os.path.isdir( dir_path ):
                try:
                    filter_file_path = filename_filter % entry
                except TypeError:
                    filter_file_path = filename_filter
                if os.path.isfile( os.path.join( dir_path, filter_file_path ) ):
                    return True
            return False
        dirs = [ entry for entry in os.listdir( directory ) if is_valid_dir( entry ) ]
        dirs.sort()
        return dirs

    def _loadBalls( self ):
        """Loads all ball models and initialize related identifiers/references."""
        ball_names = self._loadDirList( os.path.join( self._res_dir, 'balls' ),
                                        filename_filter = 'balls.xml.bin' )
        ball_dir = os.path.join( self._res_dir, 'balls' )
        for ball_name in ball_names:
            ball_world = self.global_world.make_world( metawog.WORLD_BALL, ball_name, BallModel, self )
            ball_tree = self._loadTree( ball_world, metawog.TREE_BALL_MAIN,
                                        os.path.join(ball_dir, ball_name), 'balls.xml.bin' )
            self._loadTree( ball_world, metawog.TREE_BALL_RESOURCE,
                            os.path.join(ball_dir, ball_name), 'resources.xml.bin' )
            assert ball_tree.world == ball_world
            assert ball_tree.root.world == ball_world, ball_tree.root.world

    def _initializeGlobalReferences( self ):
        """Initialize global effects, materials, resources and texts references."""
        self._expandResourceDefaultsIdPrefixAndPath()

    def _expandResourceDefaultsIdPrefixAndPath( self ):
        """Expands the default idprefix and path that are used as short-cut in the XML file."""
        # Notes: there is an invalid global resource:
        # IMAGE_GLOBAL_ISLAND_6_ICON res/images/islandicon_6
        resource_manifest = self._resources_tree.root
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
        if level_name not in self.level_models_by_name:
            level_dir = os.path.join( self._res_dir, 'levels', level_name )

            level_world = self.global_world.make_world( metawog.WORLD_LEVEL, 
                                                        level_name, 
                                                        LevelModel, 
                                                        self )
            self._loadTree( level_world, metawog.TREE_LEVEL_GAME,
                            level_dir, level_name + '.level.bin' )
            self._loadTree( level_world, metawog.TREE_LEVEL_SCENE,
                            level_dir, level_name + '.scene.bin' )
            self._loadTree( level_world, metawog.TREE_LEVEL_RESOURCE,
                            level_dir, level_name + '.resrc.bin' )
            
            self.level_models_by_name[level_name] = level_world
        return self.level_models_by_name[level_name]

    def selectLevel( self, level_name ):
        level_model = self.getLevelModel(level_name)
        louie.send( metaworldui.ActiveWorldChanged, self._universe, level_model )

    def _onElementAdded(self, element, index_in_parent): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )

    def _onElementUpdated(self, element, attribute_name, new_value, old_value): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )
        
    def _onElementAboutToBeRemoved(self, element, index_in_parent): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )

    def hasModifiedReadOnlyLevels( self ):
        """Checks if the user has modified read-only level."""
        for level_model in self.level_models_by_name.itervalues():
            if level_model.is_dirty and level_model.isReadOnlyLevel():
                return True
        return False

    def save( self ):
        """Save all changes.
           Raise exception IOError on failure.
        """
        for level_model in self.level_models_by_name.itervalues():
            level_model.saveModifiedElements()
        self.__is_dirty = False

    def playLevel( self, level_name ):
        """Starts WOG to test the specified level."""
        pid = subprocess.Popen( [self._wog_path, level_name], cwd = self._wog_dir ).pid
        # Don't wait for process end...
        # @Todo ? Monitor process so that only one can be launched ???

    def newLevel( self, level_name ):
        """Creates a new blank level with the specified name.
           May fails with an IOError."""
        return self._addNewLevel( level_name,
            self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_GAME,
                                                          metawog.LEVEL_GAME_TEMPLATE ),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_SCENE,
                                                          metawog.LEVEL_SCENE_TEMPLATE ),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_RESOURCE,
                                                          metawog.LEVEL_RESOURCE_TEMPLATE ) )

    def cloneLevel( self, cloned_level_name, new_level_name ):
        """Clone an existing level and its resources."""
        level_model = self.getLevelModel( cloned_level_name )
        def clone_level_tree( element_type ):
            return level_model.find_tree( element_type ).clone()
        return self._addNewLevel( new_level_name,
                                  clone_level_tree( metawog.TREE_LEVEL_GAME ),
                                  clone_level_tree( metawog.TREE_LEVEL_SCENE ),
                                  clone_level_tree( metawog.TREE_LEVEL_RESOURCE ) )

    def _addNewLevel( self, level_name, level_tree, scene_tree, resource_tree ):
        """Adds a new level using the specified level, scene and resource tree.
           The level directory is created, but the level xml files will not be saved immediately.
        """
        level_dir_path = os.path.join( self._res_dir, 'levels', level_name )
        if not os.path.isdir( level_dir_path ):
            os.mkdir( level_dir_path )
        # Fix the hard-coded level name in resource tree: <Resources id="scene_NewTemplate" >
        for resource_element in resource_tree.root.findall( './/Resources' ):
            resource_element.set( 'id', 'scene_%s' % level_name )
        # Creates and register the new level
        level_world = self.global_world.make_world( metawog.WORLD_LEVEL, level_name,
                                                    LevelModel, self, is_dirty = True )
        level_world.add_tree( level_tree, scene_tree, resource_tree )
        self.level_models_by_name[level_name] = level_world
        self._levels.append( level_name )
        self._levels.sort()
        self.__is_dirty = True

class BallModel(metaworld.World):
    def __init__( self, universe, world_meta, ball_name, game_model ):
        metaworld.World.__init__( self, universe, world_meta, ball_name )
        self.game_model = game_model
        self.is_dirty = False


class LevelModel(metaworld.World,metaworldui.SelectedElementsTracker):
    def __init__( self, universe, world_meta, level_name, game_model, is_dirty = False ):
        metaworld.World.__init__( self, universe, world_meta, level_name )
        metaworldui.SelectedElementsTracker.__init__( self, self )
        self.game_model = game_model
        self.__dirty_tracker = metaworldui.DirtyWorldTracker( self, is_dirty )

    @property
    def level_name( self ):
        return self.key

    @property
    def level_tree( self ):
        return self.find_tree( metawog.TREE_LEVEL_GAME ).root

    @property
    def scene_tree( self ):
        return self.find_tree( metawog.TREE_LEVEL_SCENE ).root

    @property
    def resource_tree( self ):
        return self.find_tree( metawog.TREE_LEVEL_RESOURCE ).root

    @property
    def is_dirty( self ):
        return self.__dirty_tracker.is_dirty

    def isReadOnlyLevel( self ):
        return self.level_name.lower() in 'ab3 beautyandthetentacle beautyschool blusteryday bulletinboardsystem burningman chain deliverance drool economicdivide fistyreachesout flyawaylittleones flyingmachine geneticsortingmachine goingup gracefulfailure grapevinevirus graphicprocessingunit hanglow helloworld htinnovationcommittee immigrationnaturalizationunit impalesticky incinerationdestination infestytheworm ivytower leaphole mapworldview mistyslongbonyroad mom observatoryobservationstation odetobridgebuilder productlauncher redcarpet regurgitationpumpingstation roadblocks secondhandsmoke superfusechallengetime theserver thirdwheel thrustertest towerofgoo tumbler uppershaft volcanicpercolatordayspa waterlock weathervane whistler youhavetoexplodethehead'.split()

    def saveModifiedElements( self ):
        """Save the modified scene, level, resource tree."""
        if not self.isReadOnlyLevel():  # Discards change made on read-only level
            level_name = self.level_name
            level_dir = os.path.join( self.game_model._res_dir, 'levels', level_name )
            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_LEVEL_GAME):
                self.game_model._savePackedData( level_dir, level_name + '.level.bin', self.level_tree )
            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_LEVEL_RESOURCE):
                self.game_model._savePackedData( level_dir, level_name + '.resrc.bin', self.resource_tree )
            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_LEVEL_SCENE):
                self.game_model._savePackedData( level_dir, level_name + '.scene.bin', self.scene_tree )
        self.__dirty_tracker.clean()

    def updateObjectPropertyValue( self, tree_meta, element, property_name, new_value ):
        """Changes the property value of an element (scene, level or resource)."""
        element.set( property_name, new_value )

    def getObjectFileRootElement( self, tree_meta ):
        root_by_world = { metawog.TREE_LEVEL_GAME: self.level_tree,
                          metawog.TREE_LEVEL_SCENE: self.scene_tree,
                          metawog.TREE_LEVEL_RESOURCE: self.resource_tree }
        return root_by_world[tree_meta]

    def getImagePixmap( self, image_id ):
        image_element = self.resolve_reference( metawog.WORLD_LEVEL, 'image', image_id )
        pixmap = None
        if image_element is not None:
            pixmap = self.game_model.pixmap_cache.get_pixmap( image_element )
        else:
            print 'Warning: invalid image reference: %(ref)s' % {'ref':image_id}
        return pixmap or QtGui.QPixmap()

    def updateLevelResources( self ):
        """Ensures all image/sound resource present in the level directory 
           are in the resource tree.
           Adds new resource to the resource tree if required.
        """
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
                    ALLOWED_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
                    resource_id = id_prefix + ''.join( c for c in existing_path 
                                                       if c.upper() in ALLOWED_CHARS )
                    resource_path = 'res/levels/%s/%s' % (self.level_name,existing_path)
                    meta_element = metawog.TREE_LEVEL_RESOURCE.find_element_meta_by_tag( tag )
                    new_resource = metaworld.Element( meta_element, {'id':resource_id.upper(),
                                                                     'path':resource_path} )
                    resource_element.append( new_resource )
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
        self.setAttribute( Qt.WA_DeleteOnClose )
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
        self.setRenderHints( QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform )
        # Subscribes to level element change to refresh the view
        for tree in self.getLevelModel().trees:
            tree.connect_to_element_events( self.__on_element_added,
                                            self.__on_element_updated,
                                            self.__on_element_about_to_be_removed )
        level_model = game_model.getLevelModel(level_name)
        louie.connect( self._on_active_world_change, metaworldui.ActiveWorldChanged, 
                       level_model.universe )
        louie.connect( self._on_selection_change, metaworldui.WorldSelectionChanged, level_model )

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
                element.world.set_selection( element )

    def _on_selection_change(self, selected_elements, deselected_elements): #IGNORE:W0613
        """Ensures that the selected element is seleted in the graphic view.
           Called whenever an element is selected in the tree view or the graphic view.
        """
        # Notes: we do not change selection if the item belong to an item group.
        # All selection events send to an item belonging to a group are forwarded
        # to the item group, which caused infinite recursion (unselect child,
        # then unselect parent, selection parent...)
        for item in self.__scene.items():
            element = item.data(0).toPyObject()
            if element in selected_elements:
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

    def __on_element_added(self, element, index_in_parent): #IGNORE:W0613
        self.refreshFromModel( element.tree.world )

    def __on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        self.refreshFromModel( element.tree.world )

    def __on_element_about_to_be_removed(self, element, index_in_parent): #IGNORE:W0613
        self.refreshFromModel( element.tree.world, set([element]) )

    def _on_active_world_change(self, active_world):
        """Called when a new world becomes active (may be another one).
        """
        if active_world.key == self.__level_name:
            self.refreshFromModel( active_world )

    def refreshFromModel( self, game_level_model, elements_to_skip = None ):
        elements_to_skip = elements_to_skip or set()
        scene = self.__scene
        scene.clear()
        self.__balls_by_id = {}
        self.__strands = []
        self.__lines = []
        level_element = game_level_model.level_tree
        self._addElements( scene, level_element, self.__level_elements, elements_to_skip )
        self._addStrands( scene )

        scene_element = game_level_model.scene_tree
        self._addElements( scene, scene_element, self.__scene_elements, elements_to_skip )

        for element in self.__lines:
            self._sceneLineBuilder( scene, element )
        
##        print 'SceneRect:', self.sceneRect()
##        print 'ItemsBoundingRect:', scene.itemsBoundingRect()
##        for item in self.items():
##            print 'Item:', item.boundingRect()

    def _addElements( self, scene, element, element_set, elements_to_skip ):
        """Adds graphic item for 'element' to the scene, and add the element to element_set.
           Recurses for child element.
           Return the graphic item created for the element if any (None otherwise).
        """
        if element in elements_to_skip:
            return None
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
            item = self._addElements( scene, child_element, element_set, elements_to_skip )
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
#        image = element.get('image')
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
    ##        brush = QtGui.QBrush( Qt.SolidPattern )
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

    def _addlevelStrand( self, scene, element ): #IGNORE:W0613
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

    def _levelStrandBuilder( self, scene, element ): #IGNORE:W0613
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
#        alpha = self._elementReal( element, 'alpha', 1.0 )
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
        except GameModelException, e:
            QtGui.QMessageBox.warning(self, self.tr("Loading WOG levels"),
                                      unicode(e))
                    
    def _refreshGraphicsView( self, game_level_model ):
        level_mdi = self._findLevelGraphicView( game_level_model.level_name )
        if level_mdi:
            level_view = level_mdi.widget()
            level_view.refreshFromModel( game_level_model )

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
        new_value = top_left_index.data( Qt.DisplayRole ).toString()
        data = top_left_index.data( Qt.UserRole ).toPyObject()
        if data:
            world, tree_meta, element_meta, element, property_name = data
            element.set( property_name, str(new_value) )
        else:
            print 'Warning: no data on edited item!'

    def save(self):
        """Saving all modified elements.
        """
        if self._game_model:
            had_modified_readonly_level = self._game_model.hasModifiedReadOnlyLevels()
            try:
                try:
                    QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)
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
                level_model.set_selection( added_resource_elements )

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

    def createElementTreeView(self, name, tree_meta, sibling_tabbed_dock = None ):
        dock = QtGui.QDockWidget( self.tr( name ), self )
        dock.setAllowedAreas( Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea )
        element_tree_view = metatreeui.MetaWorldTreeView( dock )
        tree_model = metatreeui.MetaWorldTreeModel(tree_meta, 0, 1, 
                                                   element_tree_view)  # nb rows, nb cols
        element_tree_view.setModel( tree_model )
        dock.setWidget( element_tree_view )
        self.addDockWidget( Qt.RightDockWidgetArea, dock )
        if sibling_tabbed_dock: # Stacks the dock widget together
            self.tabifyDockWidget( sibling_tabbed_dock, dock )
        self.tree_view_by_element_world[tree_meta] = element_tree_view
        return dock, element_tree_view
        
    def createDockWindows(self):
        self.tree_view_by_element_world = {} # map of all tree views
        scene_dock, self.sceneTree = self.createElementTreeView( 'Scene', metawog.TREE_LEVEL_SCENE )
        level_dock, self.levelTree = self.createElementTreeView( 'Level', metawog.TREE_LEVEL_GAME, scene_dock )
        resource_dock, self.levelResourceTree = self.createElementTreeView( 'Resource',
                                                                            metawog.TREE_LEVEL_RESOURCE,
                                                                            level_dock )
        scene_dock.raise_() # Makes the scene the default active tab
        
        dock = QtGui.QDockWidget(self.tr("Properties"), self)
        self.propertiesList = metaelementui.MetaWorldPropertyListView( self.statusBar(),
                                                                       dock )

        self.propertiesListModel = metaelementui.MetaWorldPropertyListModel(0, 2, 
            self.propertiesList)  # nb rows, nb cols
        self.propertiesList.setModel( self.propertiesListModel )
        dock.setWidget(self.propertiesList)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.connect(self.propertiesListModel, QtCore.SIGNAL("dataChanged(const QModelIndex&,const QModelIndex&)"),
                     self._onPropertyListValueChanged)

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
