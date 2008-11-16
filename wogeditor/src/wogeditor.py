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
import subprocess
import louie
import wogfile
import metaworld
import metawog
import metaworldui
import metatreeui
import metaelementui
import levelview
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import qthelper
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
    """A global pixmap cache the cache the pixmap associated to each element.
       Maintains the cache up to date by listening for element events.
    """
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
        self.global_world = self._universe.make_world( metawog.WORLD_GLOBAL, 'game' )
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

    def _savePackedData( self, directory, file_name, tree ):
        path = os.path.join( directory, file_name )
        xml_data = tree.to_xml()
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
                                                        LevelWorld, 
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
        """Activate the specified level and load it if required.
           Returns the activated LevelWorld.
        """
        level_model = self.getLevelModel(level_name)
        assert level_model is not None
        louie.send( metaworldui.ActiveWorldChanged, self._universe, level_model )
        return level_model

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
                                                    LevelWorld, self, is_dirty = True )
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


class LevelWorld(metaworld.World,metaworldui.SelectedElementsTracker):
    def __init__( self, universe, world_meta, level_name, game_model, is_dirty = False ):
        metaworld.World.__init__( self, universe, world_meta, level_name )
        metaworldui.SelectedElementsTracker.__init__( self, self )
        self.game_model = game_model
        self.__dirty_tracker = metaworldui.DirtyWorldTracker( self, is_dirty )

    @property
    def level_name( self ):
        return self.key

    @property
    def level_root( self ):
        return self.find_tree( metawog.TREE_LEVEL_GAME ).root

    @property
    def scene_root( self ):
        return self.find_tree( metawog.TREE_LEVEL_SCENE ).root

    @property
    def resource_root( self ):
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
                self.game_model._savePackedData( level_dir, level_name + '.level.bin', 
                                                 self.level_root.tree )
            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_LEVEL_RESOURCE):
                self.game_model._savePackedData( level_dir, level_name + '.resrc.bin', 
                                                 self.resource_root.tree )
            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_LEVEL_SCENE):
                self.game_model._savePackedData( level_dir, level_name + '.scene.bin', 
                                                 self.scene_root.tree )
        self.__dirty_tracker.clean()

    def getImagePixmap( self, image_id ):
        image_element = self.resolve_reference( metawog.WORLD_LEVEL, 'image', image_id )
        pixmap = None
        if image_element is not None:
            pixmap = self.game_model.pixmap_cache.get_pixmap( image_element )
        else:
            print 'Warning: invalid image reference: "%(ref)s"' % {'ref':image_id}
        return pixmap or QtGui.QPixmap()

    def updateLevelResources( self ):
        """Ensures all image/sound resource present in the level directory 
           are in the resource tree.
           Adds new resource to the resource tree if required.
        """
        game_dir = os.path.normpath( self.game_model._wog_dir )
        level_dir = os.path.join( game_dir, 'res', 'levels', self.level_name )
        resource_element = self.resource_root.find( './/Resources' )
        if resource_element is None:
            print 'Warning: root element not found in resource tree'
            return []
        added_elements = []
        for tag, extension, id_prefix in ( ('Image','png', 'LEVEL_IMAGE_'), ('Sound','ogg', 'LEVEL_SOUND_') ):
            known_paths = set()
            for element in self.resource_root.findall( './/' + tag ):
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
                    level_world = self._game_model.selectLevel( level_name )
                except GameModelException, e:
                    QtGui.QMessageBox.warning(self, self.tr("Failed to load level!"),
                              unicode(e))
                else:
                    sub_window = self._findWorldMDIView( level_world )
                    if sub_window:
                        self.mdiArea.setActiveSubWindow( sub_window )
                    else:
                        self._addLevelGraphicView( level_world )

    def _addLevelGraphicView( self, level_world ):
        """Adds a new MDI LevelGraphicView window for the specified level."""
        level_view = levelview.LevelGraphicView( level_world )
        sub_window = self.mdiArea.addSubWindow( level_view )
        self.connect( level_view, QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'),
                      self._updateMouseScenePosInStatusBar )
        self.connect( sub_window, QtCore.SIGNAL('aboutToActivate()'),
                      level_view.selectLevelOnSubWindowActivation )
        level_view.show()

    def _updateMouseScenePosInStatusBar( self, x, y ):
        """Called whenever the mouse move in the LevelView."""
        y = -y # Reverse transformation done when mapping to scene (in Qt 0 = top, in WOG 0 = bottom)
        self._mousePositionLabel.setText( self.tr('x: %1 y: %2').arg(x).arg(y) )

    def _findWorldMDIView( self, world ):
        """Search for an existing MDI window for level level_name.
           Return the LevelGraphicView widget, or None if not found."""
        for window in self.mdiArea.subWindowList():
            sub_window = window.widget()
            if sub_window.world == world:
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
                level_world = self._game_model.selectLevel( new_level_name )
                self._addLevelGraphicView( level_world )
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
                    level_world = self._game_model.selectLevel( new_level_name )
                    self._addLevelGraphicView( level_world )
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


    def on_cut_action(self):
        elements = self.on_copy_action( is_cut_action=True )
        if elements:
            self.on_delete_action( is_cut_action=True )
            self.statusBar().showMessage( 
                self.tr('Element "%s" cut to clipboard' % 
                        elements[0].tag), 1000 )

    def on_copy_action(self, is_cut_action = False):
        level_world = self.getCurrentLevelModel()
        if level_world:
            elements = list(level_world.selected_elements)
            if len(elements) == 1:
                xml_data = elements[0].to_xml_with_meta()
                clipboard = QtGui.QApplication.clipboard()
                clipboard.setText( xml_data )
                if not is_cut_action:
                    self.statusBar().showMessage( 
                        self.tr('Element "%s" copied to clipboard' % 
                                elements[0].tag), 1000 )
                return elements

    def on_paste_action(self):
        clipboard = QtGui.QApplication.clipboard()
        xml_data = unicode(clipboard.text())
        level_world = self.getCurrentLevelModel()
        if level_world is None or not xml_data:
            return
        elements = list(level_world.selected_elements)
        if len(elements) == 0: # Allow pasting to root when no selection
            elements = [tree.root for tree in level_world.trees]
        # Try to paste in one of the selected elements. Stop when succeed
        for element in elements:
            while element is not None:
                child_elements = element.make_detached_child_from_xml( xml_data )
                if child_elements:
                    for child_element in child_elements:
                        element.safe_identifier_insert( len(element), child_element )
                    element.world.set_selection( child_elements[0] )
                    break
                element = element.parent

    def on_delete_action(self, is_cut_action = False):
        level_world = self.getCurrentLevelModel()
        if level_world is None:
            return
        deleted_elements = []
        for element in  list(level_world.selected_elements):
            if not element.is_root():
                deleted_elements.append( element.previous_element() )
                element.parent.remove( element )
                
        if is_cut_action:
            return len(deleted_elements)
        if deleted_elements:
            self.statusBar().showMessage( 
                self.tr('Deleted %d element(s)' % len(deleted_elements)), 1000 )
            level_world.set_selection( deleted_elements[0] )

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
        self.changeWOGDirAction = qthelper.action( self, handler = self.changeWOGDir,
            icon = ":/images/open.png",
            text = "&Change WOG directory...",
            shortcut = QtGui.QKeySequence.Open,
            status_tip = "Change World Of Goo top-directory" )
                                                   
        self.editLevelAction = qthelper.action( self, handler = self.editLevel,
            icon = ":/images/open-level.png",
            text = "&Edit existing level...",
            shortcut = "Ctrl+L", 
            status_tip = "Select a level to edit" )

        self.newLevelAction = qthelper.action(self, handler = self.newLevel,
            icon = ":/images/new-level.png",
            text = "&New level...",
            shortcut = QtGui.QKeySequence.New,
            status_tip = "Creates a new level" )

        self.cloneLevelAction = qthelper.action( self, handler = self.cloneLevel,
            icon = ":/images/clone-level.png",
            text = "&Clone selected level...",
            shortcut = "Ctrl+D",
            status_tip = "Clone the selected level" )
        
        self.saveAction = qthelper.action( self, handler = self.save,
            icon = ":/images/save.png",
            text = "&Save...",
            shortcut = QtGui.QKeySequence.Save,
            status_tip = "Save all changes made to the game" )
        
        self.playAction = qthelper.action( self, handler = self.saveAndPlayLevel,
            icon = ":/images/play.png",
            text = "&Save and play Level...",
            shortcut = "Ctrl+P",
            status_tip = "Save all changes and play the selected level" )
        
        self.updateLevelResourcesAction = qthelper.action( self,
            handler = self.updateLevelResources,
            icon = ":/images/update-level-resources.png",
            text = "&Update level resources...",
            shortcut = "Ctrl+U",
            status_tip = "Adds automatically all .png & .ogg files in the level directory to the level resources" )

        self.quitAct = qthelper.action( self, handler = self.close,
            text = "&Quit",
            shortcut = "Ctrl+Q",
            status_tip = "Quit the application" )
        
        self.aboutAct = qthelper.action( self, handler = self.about,
            text = "&About",
            status_tip = "Show the application's About box" )

        self.common_actions = {
            'cut': qthelper.action( self, handler = self.on_cut_action,
                    text = "Cu&t", 
                    shortcut = QtGui.QKeySequence.Cut ),
            'copy': qthelper.action( self, handler = self.on_copy_action,
                    text = "&Copy", 
                    shortcut = QtGui.QKeySequence.Copy ),
            'paste': qthelper.action( self, handler = self.on_paste_action,
                    text = "&Paste", 
                    shortcut = QtGui.QKeySequence.Paste ),
            'delete': qthelper.action( self, handler = self.on_delete_action,
                    text = "&Remove Element", 
                    shortcut = QtGui.QKeySequence.Delete )
            }

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
        self.editMenu.addAction( self.common_actions['cut'] )
        self.editMenu.addAction( self.common_actions['copy'] )
        self.editMenu.addAction( self.common_actions['paste'] )
        self.editMenu.addSeparator()
        self.editMenu.addAction( self.common_actions['delete'] )
        
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
        element_tree_view = metatreeui.MetaWorldTreeView( self.common_actions, dock )
        tree_model = metatreeui.MetaWorldTreeModel(tree_meta, element_tree_view)
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
