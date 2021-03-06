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
import xml.etree.ElementTree #@UnresolvedImport
import os.path
import glob #@UnresolvedImport
import subprocess #@UnresolvedImport
import louie
import wogfile
import metaworld
import metawog
import metaworldui
import metatreeui
import metaelementui
import levelview
import wogeditor_rc #@UnusedImport
from shutil import copy2 #@UnresolvedImport
from PyQt4 import QtCore, QtGui #@UnresolvedImport
from PyQt4.QtCore import Qt #@UnresolvedImport
import qthelper
import editleveldialog
import newleveldialog_ui
import errors
from utils import * #@UnusedWildImport
from datetime import datetime

YAML_FORMAT = True
LOG_TO_FILE = False
APP_NAME_UPPER = 'DFG-AMY-EDITOR'
APP_NAME_LOWER = 'dfg-amy-editor'
APP_NAME_PROPER = 'Amy In Da Farm! Editor'
STR_DIR_STUB = 'levels'
CURRENT_VERSION = "v0.1"
CREATED_BY = 'Created by ' + APP_NAME_PROPER + ' ' + CURRENT_VERSION
ISSUE_LEVEL_NONE = 0
ISSUE_LEVEL_ADVICE = 1
ISSUE_LEVEL_WARNING = 2
ISSUE_LEVEL_CRITICAL = 4
MAXRECENTFILES = 4


#@DaB New actions for Add item toolbar
def _appendChildTag( parent_element, new_element_meta , mandatory_attributes, keepid = False ):
    """Adds the specified child tag to the specified element and update the tree view."""
    assert parent_element is not None
    # build the list of attributes with their initial values.
    for attribute_meta in new_element_meta.attributes:
        if attribute_meta.mandatory:
            if attribute_meta.type == metaworld.IDENTIFIER_TYPE:
                try:
                    given_id = mandatory_attributes[attribute_meta.name]
                except KeyError:
                    given_id = None
                if given_id is None or not keepid:
                    init_value = parent_element.world.generate_unique_identifier( attribute_meta )
                    mandatory_attributes[attribute_meta.name] = init_value
            else:
                init_value = attribute_meta.init
                if init_value is not None:
                    if attribute_meta.name not in mandatory_attributes:
                        mandatory_attributes[attribute_meta.name] = init_value

        if ( attribute_meta.default is not None and not attribute_meta.mandatory ):
            if attribute_meta.name not in mandatory_attributes:
                init_value = attribute_meta.default
                mandatory_attributes[attribute_meta.name] = init_value
    # Notes: when the element is added, the ElementAdded signal will cause the
    # corresponding item to be inserted into the tree.
    child_element = parent_element.make_child( new_element_meta,
                                               mandatory_attributes )
    # Select new item in tree view
    if not keepid:
        child_element.world.set_selection( child_element )
    return child_element

class AddItemFactory( object ):
    def __init__( self, window, parent, itemtag, attrib ):
        self.window = window
        self.itemtag = itemtag
        self.attrib = attrib
        self.parent = parent
        
    def _element_has_children(self, element):
        meta_element = metawog.TREE_LEVEL_SCENE.find_immediate_child_by_tag( self.parent )
        return meta_element.children_count > 0

    def __call__( self ):
        assert self.parent is not None
        model = self.window.getCurrentModel()
        if model:
            window = self.window.mdiArea.activeSubWindow()
            if window:
                cview = window.widget()
                cp = cview.mapToScene( cview.width()*0.5, cview.height()*0.5 )
                offsetx, offsety = 0, 0
                if self.parent == 'level':
                    root = model.level_root
                elif self.parent == 'scene':
                    root = model.scene_root
                elif self.parent == 'resource':
                    root = model.resource_root
                elif self._element_has_children( self.parent ):
                    thisworld = cview.world
                    selected_elements = thisworld.selected_elements
                    cgparent = None
                    for element in selected_elements:
                        meta_element = metawog.TREE_LEVEL_SCENE.find_immediate_child_by_tag( element.tag )
                        if meta_element.children_count > 0:
                            cgparent = element
                            break
                        else:
                            # check to see if they are part of a cg
                            pelement = element.parent
                            if pelement is not None:
                                if self._element_has_children( pelement.tag ):
                                    cgparent = pelement
                                    break
                    if cgparent is None:
                        QtGui.QMessageBox.warning( window, 'No composite geometry parent', 'You must select a CompositeGeom item to add this child to' )
                        return
                    root = cgparent
                    offsetx, offsety = root.get_native( 'center' )
                else:
                    print "Unknown Parent in AddItemFactory", self.parent
                    return
                rootmbt = root.meta.find_immediate_child_by_tag( self.itemtag )
                if rootmbt is not None:
                    for attribute_meta in rootmbt.attributes:
                        if attribute_meta.type == metaworld.XY_TYPE:
                            self.attrib[attribute_meta.name] = str( cp.x() - offsetx ) + "," + str( -( cp.y() + offsety ) )
                            break
                    _appendChildTag( root, rootmbt, self.attrib )

def tr( context, message ):
    return QtCore.QCoreApplication.translate( context, message )

def find_element_in_tree( root_element, element ):
    """Searchs the specified element in the root_element children and returns all its parent, and its index in its immediate parent.
       Returns None if the element is not found, otherwise returns a tuple ([parent_elements], child_index)
       root_element, element: must provides the interface xml.etree.ElementTree.
    """
    for index, child_element in enumerate( root_element ):
        if child_element is element:
            return ( [root_element], index )
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

class GameModelException( Exception ):
    pass

class PixmapCache( object ):
    """A global pixmap cache the cache the pixmap associated to each element.
       Maintains the cache up to date by listening for element events.
    """
    def __init__( self, amy_dir, universe ):
        self._amy_dir = amy_dir
        self._pixmaps_by_path = {}
        self._filedate_by_path = {}
        self.__event_synthetizer = metaworld.ElementEventsSynthetizer( universe,
            None,
            self._on_element_updated,
            self._on_element_about_to_be_removed )

    def get_pixmap( self, image_id ):
        """Returns a pixmap corresponding to the image id (actually image path).
           The pixmap is loaded if not present in the cache.
           None is returned on failure to load the pixmap.
        """
        image_path = image_id
        pixmap = self._pixmaps_by_path.get( image_path )
        if pixmap:
            return pixmap
        path = os.path.join( self._amy_dir, image_path + '.png' )
        if not os.path.isfile( path ):
            print 'Warning: invalid image path "%(path)s"' % { 'path': image_path }
        else:
            return self._addToCache( path, image_id )
        return None

    def _addToCache( self, path, image_id ):
            img = QtGui.QImage()
            image_path = image_id
            if not img.load( path ):
                data = file( path, 'rb' ).read()
                if not img.loadFromData( data ):
                    if image_path in self._pixmaps_by_path.keys():
                        del self._pixmaps_by_path[image_path]
                        del self._filedate_by_path[image_path]
                    print 'Warning: failed to load image "%(path)s"' % { 'path' : image_path }
                    return None

            # assume source image is in premultiplied alpha format
            # so, after converting image to ARGB32_Premultiplied
            # we need to restore its pixels to the pixels of original image
            img2 = img.convertToFormat( QtGui.QImage.Format_ARGB32_Premultiplied )
            if img.hasAlphaChannel():
                #img = img.convertToFormat( QtGui.QImage.Format_ARGB32 )
                w = img.width()
                for y in xrange( img.height() ):
                    pixels = img.scanLine( y )
                    pixels.setsize( 4 * w )
                    pixels_new = img2.scanLine( y )
                    pixels_new.setsize( 4 * w )
                    pixels_new[:] = pixels[:]

            self._pixmaps_by_path[image_path] = img2
            self._filedate_by_path[image_path] = os.path.getmtime( path )
            return img2

    def refresh( self ):
        # check each file in the cache...
        # if it's out of date then reload
        for image_path, filedate in self._filedate_by_path.items():
            path = os.path.normpath( os.path.join( self._amy_dir, image_path + '.png' ) )
            if not os.path.isfile( path ):
                if image_path in self._pixmaps_by_path.keys():
                    del self._pixmaps_by_path[image_path]
                    del self._filedate_by_path[image_path]
                print 'Warning: File is missing %s' % path
            elif os.path.getmtime( path ) > filedate:
                # refresh
                self._addToCache( path, {'id':path, 'path':image_path} )


    def _on_element_about_to_be_removed( self, element, index_in_parent ): #IGNORE:W0
        if element.tag == 'Image':
            if element.get( 'path', '' ) in self._pixmaps_by_element:
                del self._pixmaps_by_element[element.get( 'path', '' )]

    def _on_element_updated( self, element, name, new_value, old_value ): #IGNORE:W0613
        if element.tag == 'Image':
            if old_value in self._pixmaps_by_element:
                del self._pixmaps_by_element[old_value]

class GameModel( QtCore.QObject ):
    def __init__( self, amy_path, window ):
        """Loads text and global resources.
           Loads Levels.

           The following signals are provided:
           QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)')
        """
        QtCore.QObject.__init__( self )
        self._window = window
        self._amy_path = amy_path

        if ON_PLATFORM == PLATFORM_MAC:
            # on Mac
            # amydir is Contents\resources\game\
            self._amy_dir = os.path.join( self._amy_path, u'Contents', u'Resources', u'game' )
        else:
            self._amy_dir = os.path.split( amy_path )[0]

        metaworld.AMY_PATH = self._amy_dir
        self._res_dir = os.path.join( self._amy_dir, u'Data' )

        # On MAC
        # enumerate all files in res folder
        # convert all .png.binltl to .png
        if ON_PLATFORM == PLATFORM_MAC:
            window.statusBar().showMessage( self.tr( "Checking graphics files..." ) )
            skipped, processed, found = 0, 0, 0
            lresdir = len( self._res_dir )
            toconvert = []
            for ( path, dirs, files ) in os.walk( self._res_dir ): #@UnusedVariable
                for name in files:
                    if name.endswith( '.png.binltl' ):
                        found += 1
                        output_path = os.path.join( path, name[:-11] ) + '.png'
                        if not os.path.isfile( output_path ):
                            toconvert.append( [os.path.join( path, name ), output_path, os.path.join( path, name )[lresdir:]] )
                            processed += 1
                        else:
                            skipped += 1

            #print "png.binltl found",found,'processed',processed,'skipped',skipped
            if processed > 0:
                progress = QtGui.QProgressDialog( "", QtCore.QString(), 0, processed, window );
                progress.setWindowTitle( window.tr( "Converting PNG.BINLTL files to PNG..." ) );
                progress.setWindowModality( Qt.WindowModal );
                progress.setMinimumWidth( 300 )
                progress.forceShow()
                for filepair in toconvert:
                    if progress.wasCanceled():
                        break
                    progress.setValue( progress.value() + 1 );
                    progress.setLabelText( filepair[2] )
                    wogfile.pngbinltl2png( filepair[0], filepair[1] )
                progress.setValue( progress.value() + 1 );

        window.statusBar().showMessage( self.tr( "Game Model : Initializing" ) )
        self._universe = metaworld.Universe()
        self.global_world = self._universe.make_world( metawog.WORLD_GLOBAL, 'game' )
        window.statusBar().showMessage( self.tr( "Game Model : Loading Properties XMLs" ) )

        self._readonly_resources = set()

        self._levels = self._loadDirList( os.path.join( self._res_dir, 'levels' ),
                                          filename_filter = '%s.scene' )

        self.models_by_name = {}
        self.__is_dirty = False

        self.modified_worlds_to_check = set()
        louie.connect( self._onElementAdded, metaworld.ElementAdded )
        louie.connect( self._onElementAboutToBeRemoved, metaworld.ElementAboutToBeRemoved )
        louie.connect( self._onElementUpdated, metaworld.AttributeUpdated )
        self.pixmap_cache = PixmapCache( self._amy_dir, self._universe )
        window.statusBar().showMessage( self.tr( "Game Model : Complete" ) )

    @property
    def is_dirty( self ):
        worlds = self.modified_worlds_to_check
        self.modified_worlds_to_check = set()
        for world in worlds:
            if world:
                self.__is_dirty = self.__is_dirty or world.is_dirty
        return self.__is_dirty

    def getResourcePath( self, game_dir_relative_path ):
        return os.path.join( self._amy_dir, game_dir_relative_path )

    def _loadTree( self, world, meta_tree, directory, file_name ):
        path = os.path.join( directory, file_name )
        if not os.path.isfile( path ):
            raise GameModelException( tr( 'LoadData',
                'File "%1" does not exist. You likely provided an incorrect Amy In Da Farm! directory.' ).arg( path ) )
        data = wogfile.decrypt_file_data( path )
        try:
            if YAML_FORMAT:
                new_tree = world.make_tree_from_yaml( meta_tree, data )
            else:
                new_tree = world.make_tree_from_xml( meta_tree, data )
        except IOError, e:
            raise GameModelException( unicode( e ) + u' in file ' + file_name )
        new_tree.setFilename( path )
        return new_tree

    def _loadUnPackedTree( self, world, meta_tree, directory, file_name ):
        input_path = os.path.join( directory, file_name )
        data = file( input_path, 'rb' ).read()
        try:
            if YAML_FORMAT:
                new_tree = world.make_tree_from_yaml( meta_tree, data )
            else:
                new_tree = world.make_tree_from_xml( meta_tree, data )
        except IOError, e:
            raise GameModelException( unicode( e ) + u' in file ' + file_name )
        new_tree.setFilename( input_path )
        return new_tree

    def _saveUnPackedTree( self, directory, file_name, tree ):
        if not os.path.isdir( directory ):
            os.makedirs( directory )
        output_path = os.path.join( directory, file_name )
        if YAML_FORMAT:
            data = '## ' + CREATED_BY + '\n' + tree.to_yaml()
        else:
            data = tree.to_xml()
            data = '<!-- ' + CREATED_BY + ' -->\n' + data.replace( '><', '>\n<' )
        file( output_path, 'wb' ).write( data )
        tree.setFilename( output_path )

    def _saveTree( self, directory, file_name, tree ):
        if not os.path.isdir( directory ):
            os.makedirs( directory )
        path = os.path.join( directory, file_name )
        if YAML_FORMAT:
            data = '## ' + CREATED_BY + '\n' + tree.to_yaml()
        else:
            data = tree.to_xml()
            data = '<!-- ' + CREATED_BY + ' -->\n' + data.replace( '><', '>\n<' )
        wogfile.encrypt_file_data( path, data )
        tree.setFilename( path )

    def _loadDirList( self, directory, filename_filter ):
        if not os.path.isdir( directory ):
            raise GameModelException( tr( 'LoadLevelList',
                'Directory "%1" does not exist. You likely provided an incorrect Amy In Da Farm! directory.' ).arg( directory ) )
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
        dirs.sort( key = unicode.lower )
        return dirs

    def _loadFileList( self, directory, filename_filter ):
        if not os.path.isdir( directory ):
            raise GameModelException( tr( 'LoadFileList',
                'Directory "%1" does not exist. You likely provided an incorrect Amy In Da Farm! directory.' ).arg( directory ) )
        def is_valid_file( entry ):
            """Accepts the directory only if it contains a specified file."""
            if entry.endswith( filename_filter ):
                file_path = os.path.join( directory, entry )
                return os.path.isfile( file_path )
            return False
        files = [ entry for entry in os.listdir( directory ) if is_valid_file( entry ) ]
        files.sort( key = unicode.lower )
        return files

    @property
    def names( self ):
        return self._levels

    def getModel( self, name ):
        if name not in self.models_by_name:
            folder = os.path.join( self._res_dir, STR_DIR_STUB, name )

            world = self.global_world.make_world( metawog.WORLD_LEVEL,
                                                        name,
                                                        LevelWorld,
                                                        self )

            self._loadUnPackedTree( world, metawog.TREE_LEVEL_GAME,
                            folder, name + '.level' )
            self._loadUnPackedTree( world, metawog.TREE_LEVEL_SCENE,
                            folder, name + '.scene' )
            self._loadUnPackedTree( world, metawog.TREE_LEVEL_RESOURCE,
                            folder, name + '.resrc' )

            if world.isReadOnly:
                world.clean_dirty_tracker()
            world.clear_undo_queue()
            self.models_by_name[name] = world

        return self.models_by_name[name]

    def selectLevel( self, name ):
        """Activate the specified level and load it if required.
           Returns the activated LevelWorld.
        """
        model = self.getModel( name )
        assert model is not None
        louie.send( metaworldui.ActiveWorldChanged, self._universe, model )
        return model

    def _onElementAdded( self, element, index_in_parent ): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )

    def _onElementUpdated( self, element, attribute_name, new_value, old_value ): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )

    def _onElementAboutToBeRemoved( self, element, index_in_parent ): #IGNORE:W0613
        self.modified_worlds_to_check.add( element.world )

    def hasModifiedReadOnly( self ):
        """Checks if the user has modified read-only """
        for model in self.models_by_name.itervalues():
            if model.is_dirty and model.isReadOnly:
                return True
        return False

    def playLevel( self, level_model ):
        """Starts Amy to test the specified level."""
        # remove PYTHONPATH from the environment of new process
        env = os.environ.copy()
        if 'PYTHONPATH' in env:
            del env['PYTHONPATH']
        if ON_PLATFORM == PLATFORM_MAC:
            #print "ON MAC - Save and Play"
            #Then run the program file itself with no command-line parameters
            #print "launch ",os.path.join(self._amy_path,u'Contents',u'MacOS',u'Amy In Da Farm')
            subprocess.Popen( 
                os.path.join( self._amy_path, u'Contents', u'MacOS', u'Amy In Da Farm' ),
                cwd = self._amy_dir, env = env )
        else:
            #pid = subprocess.Popen( self._amy_path, cwd = self._amy_dir ).pid
            try:
                subprocess.Popen( [self._amy_path, level_model.name], cwd = self._amy_dir, env = env )
            except:
                # debug build have executable in different place, try to use it
                exe_path = os.path.join( os.path.dirname( self._amy_dir ), '_Debug', 'Launcher.exe' )
                subprocess.Popen( [exe_path, level_model.name], cwd = self._amy_dir, env = env )
            # Don't wait for process end...
            # @Todo ? Monitor process so that only one can be launched ???

    def newLevel( self, name ):
        """Creates a new blank level with the specified name.
           May fails with an IOError or OSError."""
        return self._addNewLevel( name,
            self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_GAME,
                                                          metawog.LEVEL_GAME_TEMPLATE ),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_SCENE,
                                                          metawog.LEVEL_SCENE_TEMPLATE ),
            self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_RESOURCE,
                                                          metawog.LEVEL_RESOURCE_TEMPLATE ) )


    def cloneLevel( self, cloned_name, new_name ):
        #Clone an existing level and its resources.
        model = self.getModel( cloned_name )
        dir = os.path.join( self._res_dir, STR_DIR_STUB, new_name )
        if not os.path.isdir( dir ):
            os.mkdir( dir )
            os.mkdir( os.path.join( dir, 'animations' ) )
            os.mkdir( os.path.join( dir, 'fx' ) )
            os.mkdir( os.path.join( dir, 'scripts' ) )
            os.mkdir( os.path.join( dir, 'textures' ) )
            os.mkdir( os.path.join( dir, 'sounds' ) )

        #new cloning method... #2
        # worked for balls... might be going back to the old Nitrozark way..
        # which didn't work right... Hmmm.!

        #get xml from existing
        #make unattached trees from it
        new_level_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_GAME,
                                                                       model.level_root.tree.to_xml() )

        new_scene_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_SCENE,
                                                                    model.scene_root.tree.to_xml() )

        new_res_tree = self._universe.make_unattached_tree_from_xml( metawog.TREE_LEVEL_RESOURCE,
                                                                        model.resource_root.tree.to_xml() )
        #change stuff
        #TODO: copy level related resources to new folder and change their paths in scene
#        self._res_swap( new_level_tree.root, '_' + cloned_name.upper() + '_', '_' + new_name.upper() + '_' )
#        self._res_swap( new_scene_tree.root, '_' + cloned_name.upper() + '_', '_' + new_name.upper() + '_' )

        #save out new trees
        self._saveUnPackedTree( dir, new_name + '.level', new_level_tree )
        self._saveUnPackedTree( dir, new_name + '.scene', new_scene_tree )
        self._saveUnPackedTree( dir, new_name + '.resrc', new_res_tree )

        self._levels.append( unicode( new_name ) )
        self._levels.sort( key = unicode.lower )
        self.__is_dirty = True

#    def _res_swap( self, element, find, replace ):
#        for attribute in element.meta.attributes:
#            if attribute.type == metaworld.REFERENCE_TYPE:
#                if attribute.reference_family in ['image', 'sound', 'TEXT_LEVELNAME_STR']:
#                    value = element.get( attribute.name, None )
#                    if value is not None:
#                        rv = ','.join( [v.replace( find, replace, 1 ) for v in value.split( ',' )] )
#                        element.set( attribute.name, rv )
#        for child in element.getchildren():
#            self._res_swap( child, find, replace )

    def _isOriginalFile( self, filename, extension ):

        return False

        path_bits = filename.replace( '\\', '/' ).split( "/" )
        if len( path_bits ) == 1:
            print filename, path_bits
            return False
        path_bits.pop( 0 )
        file = path_bits.pop( len( path_bits ) - 1 )
        root_element = self._files_tree.root
        return self._seekFile( root_element, path_bits, file, extension )

    def _seekFile( self, element, path, file, ext ):

        if path == []:
            for fileitem in element.findall( 'file' ):
                if fileitem.get( 'name' ) == file:
                    if fileitem.get( 'type' ) == ext:
                        return True
            return False
        else:
            for folder in element.findall( 'folder' ):
                if folder.get( 'name' ) == path[0]:
                    path.pop( 0 )
                    return self._seekFile( folder, path, file, ext )
            return False

    def _addNewLevel( self, name, level_tree, scene_tree, resource_tree ):
        """Adds a new level using the specified level, scene and resource tree.
           The level directory is created, but the level xml files will not be saved immediately.
        """
        dir_path = os.path.join( self._res_dir, STR_DIR_STUB, name )
        if not os.path.isdir( dir_path ):
            os.mkdir( dir_path )
            os.mkdir( os.path.join( dir_path, 'animations' ) )
            os.mkdir( os.path.join( dir_path, 'fx' ) )
            os.mkdir( os.path.join( dir_path, 'scripts' ) )
            os.mkdir( os.path.join( dir_path, 'textures' ) )
            os.mkdir( os.path.join( dir_path, 'sounds' ) )

        # Creates and register the new level
        world = self.global_world.make_world( metawog.WORLD_LEVEL, name,
                                                    LevelWorld, self, is_dirty = True )
        treestoadd = [level_tree, scene_tree, resource_tree]

        world.add_tree( treestoadd )

        self.models_by_name[name] = world
        self._levels.append( unicode( name ) )
        self._levels.sort( key = unicode.lower )
        self.__is_dirty = True

class ThingWorld( metaworld.World,
                 metaworldui.SelectedElementsTracker,
                 metaworldui.ElementIssueTracker,
                 metaworldui.UndoWorldTracker ):
    def __init__( self, universe, world_meta, name, game_model, is_dirty = False ):
        metaworld.World.__init__( self, universe, world_meta, name )
        metaworldui.SelectedElementsTracker.__init__( self, self )
        metaworldui.ElementIssueTracker.__init__( self, self )
        metaworldui.UndoWorldTracker.__init__( self, self, 100 )
        self.game_model = game_model

    @property
    def name( self ):
        return self.key

class LevelWorld( ThingWorld ):
    def __init__( self, universe, world_meta, name, game_model, is_dirty = False ):
        ThingWorld.__init__( self, universe, world_meta, name, game_model, is_dirty = is_dirty )
        self.__dirty_tracker = metaworldui.DirtyWorldTracker( self, is_dirty )
        self._importError = None
        self._sceneissues = ''
        self._levelissues = ''
        self._resrcissues = ''
        self._globalissues = ''
        self._scene_issue_level = ISSUE_LEVEL_NONE
        self._level_issue_level = ISSUE_LEVEL_NONE
        self._resrc_issue_level = ISSUE_LEVEL_NONE
        self._global_issue_level = ISSUE_LEVEL_NONE
        self._view = None

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

    @property
    def isReadOnly( self ):
        return self.name.lower() in metawog.LEVELS_ORIGINAL_LOWER

    @property
    def view( self ):
        return self._view

    def setView ( self, newview ):
        self._view = newview

    #@DaB - Issue checking used when saving the level
    def hasIssues ( self ):
        #Checks all 3 element trees for outstanding issues
        # Returns True if there are any.
        tIssue = ISSUE_LEVEL_NONE
        if self.element_issue_level( self.scene_root ):
            tIssue |= ISSUE_LEVEL_CRITICAL
        if self.element_issue_level( self.level_root ):
            tIssue |= ISSUE_LEVEL_CRITICAL
        if self.element_issue_level( self.resource_root ):
            tIssue |= ISSUE_LEVEL_CRITICAL
        #If we have a tree Issue.. don't perform the extra checks
        #because that can cause rt errors (because of the tree issues)
        #and then we don't see a popup.
        if tIssue == ISSUE_LEVEL_CRITICAL:
            #ensure old issues don't get redisplayed is we do "bail" here
            self._sceneissues = ''
            self._levelissues = ''
            self._resrcissues = ''
            self._globalissues = ''
            return tIssue
        if self.haslevel_issue():
            tIssue |= self._level_issue_level
        if self.hasscene_issue():
            tIssue |= self._scene_issue_level
        if self.hasresrc_issue():
            tIssue |= self._resrc_issue_level
        if self.hasglobal_issue():
            tIssue |= self._global_issue_level

        return tIssue

    def getIssues ( self ):
        #Get a 'report' of outstanding Issues
        #Used for Popup Message
        txtIssue = ''
        if self.element_issue_level( self.scene_root ):
            txtIssue = txtIssue + '<p>Scene Tree:<br>' + self.element_issue_report( self.scene_root ) + '</p>'
        if self.scene_issue_report != '':
            txtIssue += '<p>Scene Checks:<br>' + self.scene_issue_report + '</p>'
        if self.element_issue_level( self.level_root ):
            txtIssue = txtIssue + '<p>Level Tree:<br>' + self.element_issue_report( self.level_root ) + '</p>'
        if self.level_issue_report != '':
            txtIssue += '<p>Level Checks:<br>' + self.level_issue_report + '</p>'
        if self.element_issue_level( self.resource_root ):
            txtIssue = txtIssue + '<p>Resource Tree:<br>' + self.element_issue_report( self.resource_root ) + '</p>'
        if self.resrc_issue_report != '':
            txtIssue += '<p>Resource Checks:<br>' + self.resrc_issue_report + '</p>'
        if self.global_issue_report != '':
            txtIssue += '<p>Global Checks:<br>' + self.global_issue_report + '</p>'

        return txtIssue

    #@DaB Additional Checking Level,Scene,Resource (at tree level)
    def hasglobal_issue( self ):
        # check for issues across trees
        #if there's a levelexit it must be within the scene bounds
        self._globalissues = ''
        self._global_issue_level = ISSUE_LEVEL_NONE
        levelexit = self.level_root.find( 'levelexit' )
        if levelexit is not None:
            exit_posx, exit_posy = levelexit.get_native( 'pos' )
            minx, maxx = self.scene_root.get_native( 'minx' ), self.scene_root.get_native( 'maxx' )
            miny, maxy = self.scene_root.get_native( 'miny' ), self.scene_root.get_native( 'maxy' )
            if exit_posx > maxx or exit_posx < minx or exit_posy > maxy or exit_posy < miny:
                # exit outside scene bounds warning
                self.addGlobalError( 401, None )

        return self._global_issue_level != ISSUE_LEVEL_NONE

    def haslevel_issue( self ):
        # rules for "DUMBASS" proofing (would normally use a much ruder word)

        root = self.level_root
        self._levelissues = ''
        self._level_issue_level = ISSUE_LEVEL_NONE
        normal_camera = False
        widescreen_camera = False

        #must have 1 normal camera and 1 widescreen camera
        for camera in root.findall( 'camera' ):
            c_aspect = camera.get( 'aspect' )
            if c_aspect == 'normal':
                normal_camera = True
            elif c_aspect == 'widescreen':
                widescreen_camera = True

            #only Single poi travel time check
            if len( camera._children ) == 1:
                if camera._children[0].get_native( 'traveltime', 0 ) > 1:
                    self.addLevelError( 101, c_aspect )

        if not normal_camera:
            self.addLevelError( 102, None )

        if not widescreen_camera:
            self.addLevelError( 103, None )

        end_conditions = []

        if len( end_conditions ) > 1:
            self.addLevelError( 111, ','.join( end_conditions ) )

        return self._level_issue_level != ISSUE_LEVEL_NONE

    def addSceneError( self, error_num, subst ):
        error = errors.ERROR_INFO[error_num]
        self._scene_issue_level, self._sceneissues = self.addError( self._scene_issue_level, self._sceneissues, error, error_num, subst )

    def addLevelError( self, error_num, subst ):
        error = errors.ERROR_INFO[error_num]
        self._level_issue_level, self._levelissues = self.addError( self._level_issue_level, self._levelissues, error, error_num, subst )

    def addResourceError( self, error_num, subst ):
        error = errors.ERROR_INFO[error_num]
        self._resrc_issue_level, self._resrcissues = self.addError( self._resrc_issue_level, self._resrcissues, error, error_num, subst )

    def addGlobalError( self, error_num, subst ):
        error = errors.ERROR_INFO[error_num]
        self._global_issue_level, self._globalissues = self.addError( self._global_issue_level, self._globalissues, error, error_num, subst )

    def addError( self, err_level, err_message, error, error_num, err_subst ):
        err_level |= error[0]
        err_message += errors.ERROR_FRONT[error[0]]
        if err_subst is not None:
            err_message += error[1] % err_subst
        else:
            err_message += error[1]
        err_message += errors.ERROR_MORE_INFO % error_num
        err_message += "<br>"
        return err_level, err_message



    def hasscene_issue( self ):
        # TODO: check SceneLayer tiling applied to only pow2 textures

        #rules
        root = self.scene_root
        self._scene_issue_level = ISSUE_LEVEL_NONE
        self._sceneissues = ''
        #motor attached to static body
        motorbodys = set()
        for motor in root.findall( 'motor' ):
            motorbodys.add( motor.get( 'body' ) )
        hingebodys = set()
        for hinge in root.findall( 'hinge' ):
            hingebodys.add( hinge.get( 'body1' ) )
            body2 = hinge.get( 'body2', '' )
            if body2 != '':
                hingebodys.add( hinge.get( 'body2' ) )

        rotspeedbodys = set()

        geomitems = []
        for geomitem in root.findall( 'rectangle' ):
            geomitems.append( geomitem )
        for geomitem in root.findall( 'circle' ):
            geomitems.append( geomitem )

#        # mass checks on rectangle and circles
#        for geomitem in geomitems:
#            geomstatic = geomitem.get_native( 'static', False )
#            #static / masscheck!
#            if not geomstatic:
#                if geomitem.get_native( 'mass', 0 ) <= 0:
#                    self.addSceneError( 1, geomitem.get( 'id', '' ) )
#        # check on composite geoms
        geomchildren = set()
        for geomitem in root.findall( 'compositegeom' ):
            geomitems.append( geomitem )
#            geomstatic = geomitem.get_native( 'static', False )
#            if not geomstatic:
#                if geomitem.get_native( 'rotation', 0 ) != 0:
#                    self.addSceneError( 2, geomitem.get( 'id', '' ) )
            nchildren = 0
            for geomchild in geomitem.getchildren():
                nchildren += 1
                geomchildren.add( geomchild.get( 'id', '' ) )
#                if not geomstatic:
#                    if geomchild.get_native( 'mass', 0.0 ) <= 0:
#                        self.addSceneError( 3, ( geomitem.get( 'id', '' ), geomchild.get( 'id', '' ) ) )
#                if geomchild.get( 'image' ):
#                    self.addSceneError( 4, geomchild.get( 'id', '' ) )
#            if nchildren == 0:
#                if not geomstatic:
#                    self.addSceneError( 5, geomitem.get( 'id', '' ) )
#                else:
#                    self.addSceneError( 6, geomitem.get( 'id', '' ) )

        # Get any radial forcefields.. ready for next check
        rfflist = {}
        for rff in root.findall( 'radialforcefield' ):
            rffid = rff.get( 'id', len( rfflist ) )
            rfflist[rffid] = rff.get_native( 'center' )

        # check on ALL geometry bodies
#        for geomitem in geomitems:
#            id = geomitem.get( 'id', '' )
#            if geomitem.get_native( 'rotspeed', 0 ) != 0:
#                rotspeedbodys.add( id )
#            geomstatic = geomitem.get_native( 'static', False )
#            #static vs motor check
#            if geomstatic and id in motorbodys:
#                self.addSceneError( 7, id )
#
#            if not geomstatic:
#                gx, gy = geomitem.get_native( 'center', ( 0, 0 ) )
#                for rffid, rffpos in rfflist.items():
#                    if abs( gx - rffpos[0] + gy - rffpos[1] ) < 0.001:
#                        self.addSceneError( 8, ( id, rffid ) )

        # finally some checks on unfixed spinning things
        spinning = motorbodys | rotspeedbodys
        spinningnohinge = spinning - hingebodys
        for body in spinningnohinge:
            self.addSceneError( 9, body )

        hingedchildren = hingebodys & geomchildren
        for hingedchild in hingedchildren:
            self.addSceneError( 10, hingedchild )

        #linearforcefield can have center but no size
        #but CANNOT have size, but no center
        for lff in root.findall( 'linearforcefield' ):
            if lff.get( 'size' ) is not None:
                if lff.get( 'center', '' ) == '':
                    self.addSceneError( 11, lff.get( 'id', '' ) )

        return self._scene_issue_level != ISSUE_LEVEL_NONE

    def _get_all_resource_ids( self, root, tag ):
        resource_ids = set()
        for resource in root.findall( './/' + tag ):
            resource_ids.add( resource.get( 'path' ) + resource.attribute_meta( 'path' ).strip_extension )
        return resource_ids

    def _get_unused_resources( self ):
        used = self._get_used_resources()
        resources = self._get_all_resource_ids( self.resource_root, "Image" ) | self._get_all_resource_ids( self.resource_root, "Sound" )
        unused = resources - used
        return unused

    def _remove_unused_resources( self, element, unused ):
        self.suspend_undo()
        to_remove = []

        def _recursive_remove( element ):
            for attribute_meta in element.meta.attributes:
                if attribute_meta.type == metaworld.PATH_TYPE:
                    if element.get( attribute_meta.name ) + attribute_meta.strip_extension in unused:
                        to_remove.append( element )
            for child in element:
                _recursive_remove( child )

        _recursive_remove( element )
        for element in to_remove:
            element.parent.remove( element )
        self.activate_undo()

    def _get_used_resources( self ):
        used = set()

        #go through scene and level root
        #store the resource id of any that do
        for root in ( self.scene_root, self.level_root ):
            for element in root:
                for attribute_meta in element.meta.attributes:
                    if attribute_meta.type == metaworld.PATH_TYPE:
                        if element.get( attribute_meta.name ):
                            used.add( element.get( attribute_meta.name ) + attribute_meta.strip_extension )
        return used

    def hasresrc_issue( self ):
        root = self.resource_root
        self._resrcissues = ''
        self._resrc_issue_level = ISSUE_LEVEL_NONE
        # confirm every file referenced exists
        used_resources = self._get_used_resources()
        image_resources = set()
        for resource in root.findall( './/Image' ):
            image_resources.add( resource.get( 'path' ) )
            full_filename = os.path.join( self.game_model._amy_dir, resource.get( 'path' ) + resource.attribute_meta( 'path' ).strip_extension )
            if ON_PLATFORM == PLATFORM_WIN:
                #confirm extension on drive is lower case
                real_filename = getRealFilename( full_filename )
                real_ext = os.path.splitext( real_filename )[1]
                if real_ext != ".png":
                    self.addResourceError( 201, resource.get( 'path' ) + real_ext )

        unused_images = image_resources.difference( used_resources )
        if len( unused_images ) != 0:
            for unused in unused_images:
                self.addResourceError( 202, unused )

        sound_resources = set()
        for resource in root.findall( './/Sound' ):
            sound_resources.add( resource.get( 'path' ) )
            full_filename = os.path.join( self.game_model._amy_dir, resource.get( 'path' ) + ".ogg" )

            if ON_PLATFORM == PLATFORM_WIN:
                #confirm extension on drive is lower case
                real_filename = getRealFilename( full_filename )
                real_ext = os.path.splitext( real_filename )[1]
                if real_ext != ".ogg":
                    self.addResourceError( 203, resource.get( 'path' ) + real_ext )

        unused_sounds = sound_resources.difference( used_resources )
        if len( unused_sounds ) != 0:
            for unused in unused_sounds:
                self.addResourceError( 204, unused )

        return self._resrc_issue_level != ISSUE_LEVEL_NONE

    @property
    def scene_issue_report( self ):
        return self._sceneissues
    @property
    def level_issue_report( self ):
        return self._levelissues
    @property
    def resrc_issue_report( self ):
        return self._resrcissues
    @property
    def global_issue_report( self ):
        return self._globalissues

    def _isNumber( self, input ):
        try:
            f = float( input ) #@UnusedVariable
            return True
        except ValueError:
            return False

    def _cleanleveltree( self ):
        pass

    def _cleanscenetree( self ):
        self.suspend_undo()
        for hinge in self.scene_root.findall( 'hinge' ):
            self.scene_root.remove( hinge )
            self.scene_root.append( hinge )
        for motor in self.scene_root.findall( 'motor' ):
            self.scene_root.remove( motor )
            self.scene_root.append( motor )
        self.activate_undo()

    def _cleanresourcetree( self ):
        #removes any unused resources from the resource and text resource trees
        self.suspend_undo()
        root = self.resource_root

        #ensure cAsE sensitive path is stored in resource file
        #Only required on windows...
        #If path was not CaSe SenSitivE match on Linux / Mac would be File not found earlier
        if ON_PLATFORM == PLATFORM_WIN:
            for resource in root.findall( './/Image' ):
                full_filename = os.path.normpath( os.path.join( self.game_model._amy_dir, resource.get( 'path' ) + ".png" ) )
                if os.path.exists( full_filename ):
                    #confirm extension on drive is lower case
                    len_wogdir = len( os.path.normpath( self.game_model._amy_dir ) ) + 1
                    real_filename = os.path.normpath( getRealFilename( full_filename ) )
                    real_file = os.path.splitext( real_filename )[0][len_wogdir:]
                    full_file = os.path.splitext( full_filename )[0][len_wogdir:]
                    if real_file != full_file:
                        print "Correcting Path", resource.get( 'id' ), full_file, "-->", real_file
                        resource.attribute_meta( 'path' ).set( resource, real_file )

            for resource in root.findall( './/Sound' ):
                full_filename = os.path.normpath( os.path.join( self.game_model._amy_dir, resource.get( 'path' ) + ".ogg" ) )
                if os.path.exists( full_filename ):
                    #confirm extension on drive is lower case
                    len_wogdir = len( os.path.normpath( self.game_model._amy_dir ) )
                    real_filename = os.path.normpath( getRealFilename( full_filename ) )
                    real_file = os.path.splitext( real_filename )[0][len_wogdir:]
                    full_file = os.path.splitext( full_filename )[0][len_wogdir:]
                    if real_file != full_file:
                        print "Correcting Path", resource.get( 'id' ), full_file, "-->", real_file
                        resource.attribute_meta( 'path' ).set( resource, real_file )

        self.activate_undo()
    def saveModifiedElements( self ):
        """Save the modified scene, level, resource tree."""
        if not self.isReadOnly:  # Discards change made on read-only level
            name = self.name
            dir = os.path.join( self.game_model._res_dir, STR_DIR_STUB, name )
            if not os.path.isdir( dir ):
                os.mkdir( dir )
                os.mkdir( os.path.join( dir, 'animations' ) )
                os.mkdir( os.path.join( dir, 'fx' ) )
                os.mkdir( os.path.join( dir, 'scripts' ) )
                os.mkdir( os.path.join( dir, 'textures' ) )
                os.mkdir( os.path.join( dir, 'sounds' ) )

            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_LEVEL_GAME ):
                if not self.element_issue_level( self.level_root ):
                    #clean tree caused an infinite loop when there was a missing ball
                    # so only clean trees with no issues
                    self._cleanleveltree()
                self.game_model._saveUnPackedTree( dir, name + '.level', self.level_root.tree )

            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_LEVEL_RESOURCE ):
                self.game_model._saveUnPackedTree( dir, name + '.resrc', self.resource_root.tree )

            # ON Mac
            # Convert all "custom" png to .png.binltl
            # Only works with REAL PNG
            if ON_PLATFORM == PLATFORM_MAC:
                for image in self.resource_root.findall( './/Image' ):
                    if not self.game_model._isOriginalFile( image.get( 'path' ), 'png' ):
                        in_path = os.path.join( self.game_model._amy_dir, image.get( 'path' ) )
                        out_path = in_path + '.png.binltl'
                        in_path += '.png'
                        wogfile.png2pngbinltl( in_path, out_path )

            if self.__dirty_tracker.is_dirty_tree( metawog.TREE_LEVEL_SCENE ):
                if not self.element_issue_level( self.scene_root ):
                    # so only clean trees with no issues
                    self._cleanscenetree()
                self.game_model._saveUnPackedTree( dir, name + '.scene', self.scene_root.tree )

        self.__dirty_tracker.clean()

    def clean_dirty_tracker( self ):
        self.__dirty_tracker.clean()

    def getImagePixmap( self, image_id ):
        pixmap = self.game_model.pixmap_cache.get_pixmap( image_id )
        if pixmap is None:
            print 'Warning: invalid image reference:|', image_id, '|'
        return pixmap

    def updateResources( self ):
        """Ensures all image/sound resource present in the level directory 
           are in the resource tree.
           Adds new resource to the resource tree if required.
        """
        game_dir = os.path.normpath( self.game_model._amy_dir )
        dir = os.path.join( game_dir, 'Data', STR_DIR_STUB, self.name )
        if not os.path.isdir( dir ):
            print 'Warning: level directory does not exist'
            return []

        resource_element = self.resource_root.find( './/Resources' )
        if resource_element is None:
            print 'Warning: root element not found in resource tree'
            return []
        added_elements = []
        for tag, extension, subfolder in ( ( 'Image', 'png', 'textures' ), ( 'Sound', 'ogg', 'sounds' ) ):
            known_paths = set()
            for element in self.resource_root.findall( './/' + tag ):
                path = os.path.normpath( os.path.splitext( element.get( 'path', '' ).lower() )[0] )
                # known path are related to wog top dir in unix format & lower case without the file extension
                known_paths.add( path )
            existing_paths = glob.glob( os.path.join( dir, subfolder, '*.' + extension ) )
            for existing_path in existing_paths:
                existing_path = existing_path[len( game_dir ) + 1:] # makes path relative to top dir
                existing_path = os.path.splitext( existing_path )[0] # strip file extension
                path = os.path.normpath( existing_path ).lower()
                if path not in known_paths:
                    resource_path = existing_path.replace( "\\", "/" )
                    meta_element = metawog.TREE_LEVEL_RESOURCE.find_element_meta_by_tag( tag )
                    new_resource = metaworld.Element( meta_element, {'path':resource_path} )
                    resource_element.append( new_resource )
                    added_elements.append( new_resource )
        return added_elements

    #@DaB New Functionality - Import resources direct from files
    def importError( self ):
        return self._importError

    def importResources( self, importedfiles, res_dir ):
        """Import Resources direct from files into the level
           If files are located outside the Wog/res folder it copies them
           png -> Data/levels/{name}/textures
           ogg -> Data/levels/{name}/sounds
        """
        self._importError = None
        res_dir = os.path.normpath( res_dir )
        game_dir = os.path.split( res_dir )[0]

        resource_element = self.resource_root.find( './/Resources' )
        if resource_element is None:
            print 'Warning: root element not found in resource tree'
            return []

        all_local = True
        includesogg = False
        for file in importedfiles:
            file = os.path.normpath( file )
            # "Are you Local?"
            # Check if the files were imported from outside the Res folder
            fileext = os.path.splitext( file )[1][1:4]
            if fileext.lower() == "ogg":
                includesogg = True
            if file[:len( res_dir )] != res_dir:
                all_local = False

        if not all_local and self.isReadOnly:
            self._importError = ["Cannot import external files...!", "You cannot import external files into the original levels.\nIf you really want to do this... Clone the level first!"]
            return []

        if not all_local:
            level_path = os.path.join( res_dir, STR_DIR_STUB, self.name )
            if not os.path.isdir( level_path ):
                os.mkdir( level_path )
                os.mkdir( os.path.join( level_path, 'animations' ) )
                os.mkdir( os.path.join( level_path, 'fx' ) )
                os.mkdir( os.path.join( level_path, 'scripts' ) )
                os.mkdir( os.path.join( level_path, 'textures' ) )
                os.mkdir( os.path.join( level_path, 'sounds' ) )

            if includesogg:
                #' confirm / create import folder'
                music_path = os.path.join( res_dir, STR_DIR_STUB, 'sounds', self.name )
                if not os.path.isdir( music_path ):
                    os.mkdir( music_path )

        localfiles = []
        resmap = {'png':( 'Image', 'textures' ), 'ogg':( 'Sound', 'sounds' )}
        for file in importedfiles:
            # "Are you Local?"
            fileext = os.path.splitext( file )[1][1:4]
            if file[:len( res_dir )] != res_dir:
                #@DaB - Ensure if the file is copied that it's new extension is always lower case
                fname = os.path.splitext( os.path.split( file )[1] )[0]
                fileext = fileext.lower()
                newfile = os.path.join( res_dir, STR_DIR_STUB, self.name, resmap[fileext][1], fname + "." + fileext )
                copy2( file, newfile )
                localfiles.append( newfile )
            else:
                #@DaB - File Extension Capitalization Check
                if fileext != fileext.lower():
                    #Must be png or ogg to be compatible with LINUX and MAC
                    self._importError = ["File Extension CAPITALIZATION Warning!", "To be compatible with Linux and Mac - All file extensions must be lower case.\nYou should rename the file below, and then import it again.\n\n" + file + " skipped!"]
                else:
                    localfiles.append( file )

        added_elements = []

        known_paths = {'Image':set(), 'Sound':set()}
        for ext in resmap:
            for element in self.resource_root.findall( './/' + resmap[ext][0] ):
                path = os.path.normpath( os.path.splitext( element.get( 'path', '' ).lower() )[0] )
                # known path are related to wog top dir in unix format & lower case without the file extension
                known_paths[resmap[ext][0]].add( path )
        for file in localfiles:
            file = file[len( game_dir ) + 1:] # makes path relative to top dir
            filei = os.path.splitext( file )
            path = os.path.normpath( filei[0] ).lower()
            ext = filei[1][1:4]
            if path not in known_paths[resmap[ext][0]]:
                resource_path = filei[0].replace( "\\", "/" )
                meta_element = metawog.TREE_LEVEL_RESOURCE.find_element_meta_by_tag( resmap[ext][0] )
                new_resource = metaworld.Element( meta_element, {'path':resource_path} )
                resource_element.append( new_resource )
                added_elements.append( new_resource )
        return added_elements


class MainWindow( QtGui.QMainWindow ):
    def __init__( self, parent = None ):
        QtGui.QMainWindow.__init__( self, parent )
        self.setWindowIcon( QtGui.QIcon( ":/images/icon.png" ) )
        self.setAttribute( Qt.WA_DeleteOnClose )
        self.actionTimer = None
        self.statusTimer = None
        self._amy_path = None # Path to 'amy' executable
        self.recentfiles = None
        self.createMDIArea()
        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.createStatusBar()
        self.createDockWindows()
        self.setWindowTitle( self.tr( "Amy In Da Farm! Editor" ) )

        self._readSettings()

        self._game_model = None
        if self._amy_path:
            #Check that the stored path is still valid
            if not os.path.exists( self._amy_path ):
                self.changeAmyDir()
            else:
                self._reloadGameModel()
        else:
            # if amy_path is missing, prompt for it.
            self.changeAmyDir()

    def changeAmyDir( self ):
        amy_path = QtGui.QFileDialog.getOpenFileName( self,
             self.tr( 'Select Amy In Da Farm! program in the folder you want to edit' ),
             r'',
             self.tr( 'Amy In Da Farm! (Amy*)' ) )
        if amy_path.isEmpty(): # user canceled action
            return
        self._amy_path = os.path.normpath( unicode( amy_path ) )
        #print "_amy_path=",self._amy_path

        self._reloadGameModel()

    def _reloadGameModel( self ):
        try:
            self._game_model = GameModel( self._amy_path, self )
        except GameModelException, e:
            QtGui.QMessageBox.warning( self, self.tr( "Loading Amy In Da Farm! levels (" + APP_NAME_PROPER + " " + CURRENT_VERSION + ")" ),
                                      unicode( e ) )
    def _updateRecentFiles( self ):
        if self.recentFiles is None:
            numRecentFiles = 0
        else:
            numRecentFiles = min( len( self.recentFiles ), MAXRECENTFILES )
        for i in range( 0, numRecentFiles ):
            self.recentfile_actions[i].setText( self.recentFiles[i] )
            self.recentfile_actions[i].setVisible( True )
        for i in range( numRecentFiles, MAXRECENTFILES ):
            self.recentfile_actions[i].setVisible( False )
        self.separatorRecent.setVisible( numRecentFiles > 0 );

    def _setRecentFile( self, filename ):
        self.recentFiles.removeAll( filename )
        self.recentFiles.prepend( filename )
        if len( self.recentFiles ) > MAXRECENTFILES:
            self.recentFiles = self.recentFiles[:MAXRECENTFILES]
        self._updateRecentFiles()

    def on_recentfile_action( self ):
        action = self.sender()
        name = unicode( action.text() )
        if self.open_level_view_by_name( name ):
            self._setRecentFile( name )

    def editLevel( self ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = editleveldialog.Ui_EditLevelDialog()
            ui.setupUi( dialog , set( self._game_model.names ), metawog.LEVELS_ORIGINAL )
            if dialog.exec_() and ui.levelList.currentItem:
                settings = QtCore.QSettings()
                settings.beginGroup( "MainWindow" )
                settings.setValue( "level_filter", ui.comboBox.currentIndex() )
                settings.endGroup()
                name = unicode( ui.levelList.currentItem().text() )
                if self.open_level_view_by_name( name ):
                    self._setRecentFile( name )

    def open_level_view_by_name( self, name ):
        try:
            world = self._game_model.selectLevel( name )
        except GameModelException, e:
            QtGui.QMessageBox.warning( self, self.tr( "Failed to load level! (" + APP_NAME_PROPER + " " + CURRENT_VERSION + ")" ),
                      unicode( e ) )
        else:
            sub_window = self._findWorldMDIView( world )
            if sub_window:
                self.mdiArea.setActiveSubWindow( sub_window )
            else:
                self._addGraphicView( world )
            return True
        return False

    def _addGraphicView( self, world ):
        """Adds a new MDI GraphicView window for the specified level."""
        level_view = levelview.LevelGraphicView( world, self.view_actions, self.common_actions )
        sub_window = self.mdiArea.addSubWindow( level_view )
        self.connect( level_view, QtCore.SIGNAL( 'mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)' ),
                      self._updateMouseScenePosInStatusBar )
        self.connect( sub_window, QtCore.SIGNAL( 'aboutToActivate()' ),
                      level_view.selectLevelOnSubWindowActivation )
        world.set_selection( world.scene_root )
        world.setView( level_view )
        level_view.show()

    def _updateMouseScenePosInStatusBar( self, x, y ):
        """Called whenever the mouse move in the LevelView."""
        # Round displayed coordinate to 2dp (0.01)
        x = round( x, 2 )
        y = -round( y, 2 ) # Reverse transformation done when mapping to scene (in Qt 0 = top, in WOG 0 = bottom)
        self._mousePositionLabel.setText( self.tr( 'x: %1 y: %2' ).arg( x ).arg( y ) )

    def _findWorldMDIView( self, world ):
        """Search for an existing MDI window for level name.
           Return the LevelGraphicView widget, or None if not found."""
        for window in self.mdiArea.subWindowList():
            sub_window = window.widget()
            if sub_window.world == world:
                return window
        return None

    def get_active_view( self ):
        """Returns the view of the active MDI window. 
           Returns None if no view is active.
        """
        window = self.mdiArea.activeSubWindow()
        if window:
            return window.widget()
        return None

    def getCurrentModel( self ):
        """Returns the level model of the active MDI window."""
        window = self.mdiArea.activeSubWindow()
        if window:
            return window.widget().getModel()
        return None

    #@DaB - New save routines to save ONLY the current Level
    def saveCurrent( self ):
        if self._game_model:
            model = self.getCurrentModel()
            if model is not None:
                if model.isReadOnly:
                    if model.is_dirty:
                        QtGui.QMessageBox.warning( self, self.tr( "Can not save Amy In Da Farm! standard levels!" ),
                              self.tr( 'You can not save changes made to levels that come with Amy In Da Farm!.\n'
                                      'Instead, clone the level using the "Clone selected level" tool.\n'
                                      'Do so now, or your change will be lost once you quit the editor' ) )
                        return False
                    return True
                else:
                    #Check for issues
                    try:
                        model.saveModifiedElements()
                        self.statusBar().showMessage( self.tr( "Saved " + model.name ), 2000 )
                        return True
                    except ( IOError, OSError ), e:
                        QtGui.QMessageBox.warning( self, self.tr( "Failed saving levels (" + APP_NAME_PROPER + " " + CURRENT_VERSION + ")" ), unicode( e ) )

        return False

    def saveIT( self ):
        if self.saveCurrent():
            QtGui.QApplication.setOverrideCursor( Qt.WaitCursor )
            model = self.getCurrentModel()
            issue_level = model.hasIssues()
            QtGui.QApplication.restoreOverrideCursor()
            if issue_level >= ISSUE_LEVEL_WARNING:
                txtIssue = self.tr( """<p>There are unresolved issues with this level that may cause problems.<br>
                                        You should fix these before you try to play or make a goomod.</p>""" )
                txtIssue = txtIssue + self.tr( model.getIssues() )
                txtIssue = txtIssue + self.tr( '<br>The level has been saved!' )
                QtGui.QMessageBox.warning( self, self.tr( "This level has issues!" ),
                      txtIssue )

    def saveAndPlayLevel( self ):
        #@DaB only save current level, and don't "play" if it has "Issues"
        if self.saveCurrent():
            model = self.getCurrentModel()
            if model:
                issue_level = model.hasIssues()
                if issue_level >= ISSUE_LEVEL_CRITICAL:
                    txtIssue = self.tr( """<p>There are CRITICAL issues with this level that will cause World of Goo to crash.<br>
                                       You must fix these before you try to play the level.</p>""" )
                    txtIssue = txtIssue + self.tr( model.getIssues() )
                    txtIssue = txtIssue + self.tr( '<br>The level has been saved!' )
                    QtGui.QMessageBox.warning( self, self.tr( "This level has CRITICAL issues!" ),
                          txtIssue )
                elif issue_level > ISSUE_LEVEL_NONE:
                    txtIssue = self.tr( """<p>There are Advice/Warnings for this level that may cause problems.<br>
                                        You should fix these before you try to play the level.</p>""" )
                    txtIssue = txtIssue + self.tr( model.getIssues() )
                    txtIssue = txtIssue + self.tr( '<br>Click OK to Play anyway, or click Cancel to go back.' )
                    ret = QtGui.QMessageBox.warning( self, self.tr( "This level has warnings!" ),
                        txtIssue, QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                    if ret == QtGui.QMessageBox.Ok:
                        self._game_model.playLevel( model )
                else:
                    self._game_model.playLevel( model )
            else:
                self.statusBar().showMessage( self.tr( "You must select a level to play" ), 2000 )

    def newLevel( self ):
        """Creates a new blank level."""
        new_name = self._pickNewName( is_cloning = False )
        if new_name:
            try:
                self._game_model.newLevel( new_name )
                world = self._game_model.selectLevel( new_name )
                self._addGraphicView( world )
            except ( IOError, OSError ), e:
                QtGui.QMessageBox.warning( self, self.tr( "Failed to create the new level! (" + APP_NAME_PROPER + " " + CURRENT_VERSION + ")" ),
                                          unicode( e ) )

    def _pickNewName( self, is_cloning = False ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = newleveldialog_ui.Ui_NewLevelDialog()
            ui.setupUi( dialog )
            reg_ex = QtCore.QRegExp( '[A-Za-z][0-9A-Za-z_][0-9A-Za-z_]+' )
            validator = QtGui.QRegExpValidator( reg_ex, dialog )
            ui.levelName.setValidator( validator )
            if is_cloning:
                dialog.setWindowTitle( tr( "NewLevelDialog", "Cloning Level" ) )

            if dialog.exec_():
                new_name = str( ui.levelName.text() )
                existing_names = [name.lower() for name in self._game_model.names]
                if new_name.lower() not in existing_names:
                    return new_name
                QtGui.QMessageBox.warning( self, self.tr( "Can not create level!" ),
                    self.tr( "There is already a level named '%1'" ).arg( new_name ) )
        return None

    def cloneLevel( self ):
        """Clone the selected level."""
        current_model = self.getCurrentModel()
        if current_model:
            new_name = self._pickNewName( is_cloning = True )
            if new_name:
                try:
                    self._game_model.cloneLevel( current_model.name, new_name )
                    world = self._game_model.selectLevel( new_name )
                    self._addGraphicView( world )
                    self._setRecentFile( new_name )
                except ( IOError, OSError ), e:
                    QtGui.QMessageBox.warning( self, self.tr( "Failed to create the new cloned level! (" + APP_NAME_PROPER + " " + CURRENT_VERSION + ")" ), unicode( e ) )

    def updateResources( self ):
        """Adds the required resource in the level based on existing file."""
        model = self.getCurrentModel()
        if model:
            model.game_model.pixmap_cache.refresh()
            added_resource_elements = model.updateResources()
            if added_resource_elements:
                model.set_selection( added_resource_elements )
            model._view.refreshFromModel()

    def cleanResources( self ):
        model = self.getCurrentModel()
        if model:
            unused = model._get_unused_resources()
            unusedlist = ''
            for id in unused:
                unusedlist += id + '\n'
            if unusedlist != '':
                unusedlist = "The following resources are unused\n" + unusedlist + "\nAre you sure you want to remove them?"
                ret = QtGui.QMessageBox.warning( self, self.tr( "Remove unused resources" ),
                        unusedlist, QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel )
                if ret == QtGui.QMessageBox.Ok:
                    model._remove_unused_resources( model.resource_root, unused )
            else:
                QtGui.QMessageBox.warning( self, self.tr( "Remove unused resources" ),
                        self.tr( "There are no unused resources\n" ) )

    def importResources( self ):
        """Adds the required resource in the level based on existing file."""
        model = self.getCurrentModel()
        if model:
            #game_dir = os.path.normpath( os.path.split( self._amy_path )[0] )
            #res_dir =  os.path.join( game_dir, 'res' )
            dir = os.path.join( self._game_model._res_dir, STR_DIR_STUB )
            files = QtGui.QFileDialog.getOpenFileNames( self,
                        self.tr( 'Select the Images to import...' ),
                        dir,
                        self.tr( 'Images (*.png)' ) )

            if files.isEmpty(): # user canceled action
                return
            safefiles = []
            for file in files:
                safefiles.append( os.path.normpath( str( file ) ) )

            added_resource_elements = model.importResources( safefiles, self._game_model._res_dir )
            if added_resource_elements:
                model.set_selection( added_resource_elements )
            else:
                ie = model.importError()
                if ie is not None:
                    QtGui.QMessageBox.warning( self, self.tr( ie[0] ),
                              self.tr( ie[1] ) )

    def about( self ):
        QtGui.QMessageBox.about( self, self.tr( "About Amy In Da Farm! Level Editor " + CURRENT_VERSION ),
            self.tr( """<p>Amy In Da Farm! Level Editor helps you create new levels for Amy In Da Farm!.<p>
            <p>Developer Page, Sources and Reference Guide:<br>
            <a href="http://github.com/reven86/dfg-amy-editor">http://github.com/reven86/dfg-amy-editor</a></p>
            <p>Copyright 2010, Andrew Karpushin &lt;andrew.karpushin at dreamfarmgames.com&gt;</p>
            <p>&nbsp;<br>Original based on World Of Goo Level Editor (WooGLE) by DaftasBrush: (v0.77)</p>
            <p>Copyright 2010, DaftasBrush<br>
            <a href="http://goofans.com/download/utility/world-of-goo-level-editor">http://goofans.com/download/utility/world-of-goo-level-editor</a></p>
            <p>&nbsp;<br>Original Sourceforge project: (v0.5)
            <a href="http://www.sourceforge.net/projects/wogedit">http://www.sourceforge.net/projects/wogedit</a><br>
            Copyright 2008-2009, NitroZark &lt;nitrozark at users.sourceforget.net&gt;</p>""" ) )

    def on_cut_action( self ):
        elements = self.on_copy_action( is_cut_action = True )
        if elements:
            for element in elements:
                if element.meta.read_only:
                    #Messagebox
                    QtGui.QMessageBox.warning( self, self.tr( "Cannot Cut read only element!" ),
                              self.tr( 'This element is read only.\n'
                                      'It cannot be cut' ) )
                    return
            self.on_delete_action( is_cut_action = True )
            self.statusBar().showMessage( 
                self.tr( 'Element "%s" cut to clipboard' %
                        elements[0].tag ), 1000 )

    def on_copy_action( self, is_cut_action = False ):
        world = self.getCurrentModel()
        if world:
            elements = list( world.selected_elements )
            on_clipboard = set()
            clipboard_element = xml.etree.ElementTree._ElementInterface( 'WooGLEClipboard', {} )
            for element in elements:
                on_clipboard.add( element.tag )
                xml_data = element.to_xml_with_meta()
                clipboard_element.append( xml.etree.ElementTree.fromstring( xml_data ) )
            clipboard = QtGui.QApplication.clipboard()
            if len( on_clipboard ) == 1:
                clipboard_element.set( 'type', list( on_clipboard )[0] )
            else:
                clipboard_element.set( 'type', "Various" )
            scene = self.get_active_view().scene()
            # bounding rect of selected items
            i = 0
            for item in scene.selectedItems():
                if i == 0:
                    brect = item.mapToScene( item.boundingRect() ).boundingRect()
                    mybrect = [brect.left(), brect.right(), brect.bottom(), brect.top()]
                else:
                    brect = item.mapToScene( item.boundingRect() ).boundingRect()
                    if brect.left() < mybrect[0]:
                        mybrect[0] = brect.left()
                    if brect.right() > mybrect[1]:
                        mybrect[1] = brect.right()
                    if brect.bottom() < mybrect[2]:
                        mybrect[2] = brect.bottom()
                    if brect.top() > mybrect[3]:
                        mybrect[3] = brect.top()
                i += 1

            clipboard_element.set( 'posx', str( ( mybrect[0] + mybrect[1] ) * 0.5 ) )
            clipboard_element.set( 'posy', str( -( mybrect[2] + mybrect[3] ) * 0.5 ) )
            xml_data = xml.etree.ElementTree.tostring( clipboard_element, 'utf-8' )
            clipboard.setText( xml_data )
            if not is_cut_action:
                self.statusBar().showMessage( 
                    self.tr( '%d Element "%s" copied to clipboard' %
                            ( len( elements ), clipboard_element.get( 'type' ) ) ), 1000 )
            self.common_actions['paste'].setText( "Paste In Place (" + clipboard_element.get( 'type' ) + ")" )
            self.common_actions['pastehere'].setText( "Paste Here (" + clipboard_element.get( 'type' ) + ")" )
            return elements


    def on_pasteto_action( self ):
        clipboard = QtGui.QApplication.clipboard()
        xml_data = unicode( clipboard.text() )
        world = self.getCurrentModel()
        if world is None or not xml_data:
            return
        clipboard_element = xml.etree.ElementTree.fromstring( xml_data )
        view = self.get_active_view()
        paste_posx, paste_posy = view._last_pos.x(), -view._last_pos.y()
        copy_posx, copy_posy = float( clipboard_element.get( 'posx', 0 ) ), float( clipboard_element.get( 'posy', 0 ) )
        pasted_elements = []
        for clip_child in clipboard_element.getchildren():
            xml_data = xml.etree.ElementTree.tostring( clip_child, 'utf-8' )
            for element in [tree.root for tree in world.trees]:
                child_elements = element.make_detached_child_from_xml( xml_data )
                if child_elements:
                    pasted_elements.extend( child_elements )
                    for child_element in child_elements:
                        # find the pos attribute in the meta
                        # set it to view._last_release_at
                        pos_attribute = self._getPositionAttribute( child_element )
                        if pos_attribute is not None:
                            old_pos = pos_attribute.get_native( child_element, ( 0, 0 ) )
                            if clipboard_element.__len__() == 1:
                                pos_attribute.set_native( child_element, [view._last_pos.x(), -view._last_pos.y()] )
                            else:
                                pos_attribute.set_native( child_element, [old_pos[0] + paste_posx - copy_posx, old_pos[1] + paste_posy - copy_posy] )

                        element.safe_identifier_insert( len( element ), child_element )
                    break
        if len( pasted_elements ) >= 1:
            world.set_selection( pasted_elements )


    def _getPositionAttribute( self, element ):
        for attribute_meta in element.meta.attributes:
            if attribute_meta.type == metaworld.XY_TYPE:
                if attribute_meta.position:
                    return attribute_meta
        return None

    def on_paste_action( self ):
        clipboard = QtGui.QApplication.clipboard()
        xml_data = unicode( clipboard.text() )
        world = self.getCurrentModel()
        if world is None or not xml_data:
            return
        elements = list( world.selected_elements )
        if len( elements ) == 0: # Allow pasting to root when no selection
            elements = [tree.root for tree in world.trees]
        # Try to paste in one of the selected elements. Stop when succeed
        clipboard_element = xml.etree.ElementTree.fromstring( xml_data )
        pasted_elements = []
        for clip_child in clipboard_element.getchildren():
            xml_data = xml.etree.ElementTree.tostring( clip_child, 'utf-8' )
            for element in elements:
                while element is not None:
                    child_elements = element.make_detached_child_from_xml( xml_data )
                    if child_elements:
                        for child_element in child_elements:
                            element.safe_identifier_insert( len( element ), child_element )
                        pasted_elements.extend( child_elements )
                        break
                    element = element.parent
        if len( pasted_elements ) >= 1:
            element.world.set_selection( pasted_elements )

    def on_undo_action( self ):
        world = self.getCurrentModel()
        if world is None:
            return
        world.undo()

    def on_redo_action( self ):
        world = self.getCurrentModel()
        if world is None:
            return
        world.redo()

    def on_delete_action( self, is_cut_action = False ):
        world = self.getCurrentModel()
        if world is None:
            return
        deleted_elements = []
        previous_element = None
        for element in list( world.selected_elements ):
            if element.meta.read_only:
                #messagebox
                QtGui.QMessageBox.warning( self, self.tr( "Cannot delete read only element!" ),
                              self.tr( 'This element is read only.\n'
                                      'It cannot be deleted' ) )

                return 0
            elif not element.is_root():
                if element.previous_element() not in list( world.selected_elements ):
                    previous_element = element.previous_element()

                deleted_elements.append( element.tag )
                element.parent.remove( element )

        if is_cut_action:
            return len( deleted_elements )
        if deleted_elements:
            self.statusBar().showMessage( 
                self.tr( 'Deleted %d element(s)' % len( deleted_elements ) ), 1000 )
            world.set_selection( previous_element )

    def _on_view_tool_actived( self, tool_name ):
        active_view = self.get_active_view()
        if active_view is not None:
            active_view.tool_activated( tool_name )

    def on_pan_tool_action( self ):
        self._on_view_tool_actived( levelview.TOOL_PAN )

    def on_move_tool_action( self ):
        self._on_view_tool_actived( levelview.TOOL_MOVE )

    def onRefreshAction( self ):
        """Called multiple time per second. Used to refresh enabled flags of actions."""
        has_amy_dir = self._game_model is not None
        #@DaB - Now that save and "save and play" only act on the
        # current level it's better if that toolbars buttons
        # change state based on the current level, rather than all levels
        currentModel = self.getCurrentModel()
        is_selected = currentModel is not None
        can_select = is_selected and self.view_actions[levelview.TOOL_MOVE].isChecked()

        if is_selected:
            can_save = has_amy_dir and currentModel.is_dirty
            element_is_selected = can_select and len( currentModel.selected_elements ) > 0
            can_import = is_selected and not currentModel.isReadOnly
            can_undo = currentModel.can_undo
            can_redo = currentModel.can_redo
            if currentModel.is_dirty:
                if currentModel.isReadOnly:
                    self.mdiArea.activeSubWindow().setWindowIcon( QtGui.QIcon ( ':/images/nosave.png' ) )
                else:
                    self.mdiArea.activeSubWindow().setWindowIcon( QtGui.QIcon ( ':/images/dirty.png' ) )
            else:
                self.mdiArea.activeSubWindow().setWindowIcon( QtGui.QIcon ( ':/images/clean.png' ) )
        else:
            can_save = False
            element_is_selected = False
            can_import = False
            can_undo = False
            can_redo = False


        self.editLevelAction.setEnabled( has_amy_dir )
        self.newLevelAction.setEnabled( has_amy_dir )
        self.cloneLevelAction.setEnabled( is_selected )
        self.saveAction.setEnabled( can_save and True or False )
        self.playAction.setEnabled( is_selected )

        #Edit Menu / ToolBar

        self.common_actions['cut'].setEnabled ( element_is_selected )
        self.common_actions['copy'].setEnabled ( element_is_selected )
        self.common_actions['paste'].setEnabled ( is_selected )
        self.common_actions['delete'].setEnabled ( element_is_selected )
        self.undoAction.setEnabled ( can_undo )
        self.redoAction.setEnabled ( can_redo )

        #Resources
        self.importResourcesAction.setEnabled ( can_import )
        self.cleanResourcesAction.setEnabled ( can_import )
        self.updateResourcesAction.setEnabled( can_import )

        self.addItemToolBar.setEnabled( can_select )
        self.showhideToolBar.setEnabled( is_selected )

        active_view = self.get_active_view()
        enabled_view_tools = set()
        if active_view:
            enabled_view_tools = active_view.get_enabled_view_tools()
        for name, action in self.view_actions.iteritems():
            is_enabled = name in enabled_view_tools
            action.setEnabled( is_enabled )
        if self.view_action_group.checkedAction() is None:
            self.view_actions[levelview.TOOL_MOVE].setChecked( True )

    def _on_refresh_element_status( self ):
        # broadcast the event to all ElementIssueTracker
        louie.send_minimal( metaworldui.RefreshElementIssues )

    def createMDIArea( self ):
        self.mdiArea = QtGui.QMdiArea()
        self.mdiArea.setViewMode( QtGui.QMdiArea.TabbedView )
        for thing in self.mdiArea.findChildren( QtGui.QTabBar ):
            thing.setTabsClosable( True )
            self.connect ( thing, QtCore.SIGNAL( "tabCloseRequested(int)" ), self.on_closeTab )
        self.setCentralWidget( self.mdiArea )

    def on_closeTab( self, index ):
        sub = self.mdiArea.subWindowList()[index]
        sub.close()

    def createActions( self ):
        self.changeAmyDirAction = qthelper.action( self, handler = self.changeAmyDir,
            icon = ":/images/open.png",
            text = "&Change Amy In Da Farm! directory...",
            shortcut = QtGui.QKeySequence.Open,
            status_tip = "Change Amy In Da Farm! top-directory" )

        self.editLevelAction = qthelper.action( self, handler = self.editLevel,
            icon = ":/images/icon-amy-level.png",
            text = "&Edit existing level...",
            shortcut = "Ctrl+L",
            status_tip = "Select a level to edit" )

        self.newLevelAction = qthelper.action( self, handler = self.newLevel,
            icon = ":/images/icon-amy-new-level2.png",
            text = "&New level...",
            shortcut = QtGui.QKeySequence.New,
            status_tip = "Creates a new level" )

        self.cloneLevelAction = qthelper.action( self, handler = self.cloneLevel,
            icon = ":/images/icon-amy-clone-level.png",
            text = "&Clone selected level...",
            shortcut = "Ctrl+D",
            status_tip = "Clone the selected level" )

        self.saveAction = qthelper.action( self, handler = self.saveIT,
            icon = ":/images/save.png",
            text = "&Save...",
            shortcut = QtGui.QKeySequence.Save,
            status_tip = "Saves the Level" )

        self.playAction = qthelper.action( self, handler = self.saveAndPlayLevel,
            icon = ":/images/play.png",
            text = "&Save and play Level...",
            shortcut = "Ctrl+P",
            status_tip = "Save and play the selected level" )

        self.updateResourcesAction = qthelper.action( self,
            handler = self.updateResources,
            icon = ":/images/update-level-resources.png",
            text = "&Update level resources...",
            shortcut = "Ctrl+U",
            status_tip = "Adds automatically all .png & .ogg files in the level directory to the level resources" )

        self.cleanResourcesAction = qthelper.action( self,
            handler = self.cleanResources,
            icon = ":/images/cleanres.png",
            text = "&Clean Resources",
            status_tip = "Removes any unused resource from the level." )

        self.importResourcesAction = qthelper.action( self,
            handler = self.importResources,
            icon = ":/images/importres.png",
            text = "&Import images...",
            shortcut = "Ctrl+I",
            status_tip = "Adds images (png) to the level resources" )

        self.quitAct = qthelper.action( self, handler = self.close,
            text = "&Quit",
            shortcut = "Ctrl+Q",
            status_tip = "Quit the application" )

        self.aboutAct = qthelper.action( self, handler = self.about,
            icon = ":/images/icon.png",
            text = "&About",
            status_tip = "Show the application's About box" )

        self.recentfile_actions = [qthelper.action( self, handler = self.on_recentfile_action, visible = False )
                                    for i in range( 0, MAXRECENTFILES )] #@UnusedVariable

        self.common_actions = {
            'cut': qthelper.action( self, handler = self.on_cut_action,
                    icon = ":/images/cut.png",
                    text = "Cu&t",
                    shortcut = QtGui.QKeySequence.Cut ),
            'copy': qthelper.action( self, handler = self.on_copy_action,
                    icon = ":/images/copy.png",
                    text = "&Copy",
                    shortcut = QtGui.QKeySequence.Copy ),
            'paste': qthelper.action( self, handler = self.on_paste_action,
                    icon = ":/images/paste.png",
                    text = "Paste &In Place",
                    shortcut = "Ctrl+Shift+V" ),
            'pastehere': qthelper.action( self, handler = self.on_pasteto_action,
                    icon = ":/images/paste.png",
                    text = "&Paste Here", shortcut = QtGui.QKeySequence.Paste ),

            'delete': qthelper.action( self, handler = self.on_delete_action,
                    icon = ":/images/delete.png",
                    text = "&Delete",
                    shortcut = QtGui.QKeySequence.Delete )

        }
        self.undoAction = qthelper.action( self, handler = self.on_undo_action,
                    icon = ":/images/undo.png",
                    text = "&Undo",
                    shortcut = QtGui.QKeySequence.Undo )

        self.redoAction = qthelper.action( self, handler = self.on_redo_action,
                    icon = ":/images/redo.png",
                    text = "&Redo",
                    shortcut = QtGui.QKeySequence.Redo )

        class ShowHideFactory( object ):
                def __init__( self, window, elements ):
                    self.window = window
                    self.elements = elements
                def __call__( self ):
                    lv = self.window.get_active_view()
                    if lv is not None:
                        for elementtype in self.elements:
                            currentstate = lv.get_element_state( elementtype )
                            newstate = 2 - currentstate
                            lv.set_element_state( elementtype, newstate )
                        lv.refreshFromModel()

        self.showhide_actions = {
            'camera': qthelper.action( self, handler = ShowHideFactory( self , ['camera', 'poi'] ),
                    text = "Show/Hide Camera" , icon = ":/images/show-camera.png" ),
            'fields': qthelper.action( self, handler = ShowHideFactory( self , ['linearforcefield', 'radialforcefield'] ),
                    text = "Show/Hide Forcefields", icon = ":/images/show-physic.png" ),
            'geom': qthelper.action( self, handler = ShowHideFactory( self , ['rectangle', 'circle', 'compositegeom', 'levelexit', 'line', 'hinge'] ),
                    text = "Show/Hide Geometry" , icon = ":/images/show-geom.png" ),
            'gfx': qthelper.action( self, handler = ShowHideFactory( self , ['scenelayer', 'pixmap'] ),
                    text = "Show/Hide Graphics" , icon = ":/images/show-gfx.png" ),
            'labels': qthelper.action( self, handler = ShowHideFactory( self , ['label'] ),
                    text = "Show/Hide Labels" , icon = ":/images/show-label.png" )
        }

        self.view_action_group = QtGui.QActionGroup( self )
        self.view_actions = {
            levelview.TOOL_PAN: qthelper.action( self,
                    handler = self.on_pan_tool_action,
                    icon = ":/images/zoom.png",
                    text = "&Zoom and Pan view (F)",
                    shortcut = 'F',
                    checkable = True ),
            levelview.TOOL_MOVE: qthelper.action( self,
                    handler = self.on_move_tool_action,
                    icon = ":/images/tool-move.png",
                    text = "&Select, Move and Resize",
                    shortcut = 'T',
                    checked = True,
                    checkable = True )
            }

        for action in self.view_actions.itervalues():
            self.view_action_group.addAction( action )

        self.additem_actions = {
        'line':qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'line', {} ),
                    icon = ":/images/addline.png",
                    text = "&Add a Line" ),

        'rectangle':qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'rectangle', {} ),
                    icon = ":/images/addrect.png",
                    text = "&Add Rectangle" ),

        'circle':   qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'circle', {} ),
                    icon = ":/images/addcircle.png",
                    text = "&Add Circle" ),

        'image':    qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'scenelayer', {} ),
                    icon = ":/images/group-image.png",
                    text = "&Add Image (SceneLayer)" ),

        'compgeom': qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'compositegeom', {} ),
                    icon = ":/images/compgeom.png",
                    text = "&Add Composite Geometry (Parent)" ),

        'childrect':qthelper.action( self,
                    handler = AddItemFactory( self, 'compositegeom', 'rectangle', {} ),
                    icon = ":/images/childrect.png",
                    text = "&Add Child Rectangle" ),

        'childcircle':qthelper.action( self,
                    handler = AddItemFactory( self, 'compositegeom', 'circle', {} ),
                    icon = ":/images/childcircle.png",
                    text = "&Add Child Circle" ),

        'hinge':    qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'hinge', {} ),
                    icon = ":/images/hinge.png",
                    text = "&Add Hinge" ),

        'lff':      qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'linearforcefield', {'size':'100,100'} ),
                    icon = ":/images/lff.png",
                    text = "&Add Linear force Field" ),

        'rff':      qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'radialforcefield', {} ),
                    icon = ":/images/rff.png",
                    text = "&Add Radial force Field" ),

        'label':    qthelper.action( self,
                    handler = AddItemFactory( self, 'scene', 'label', {} ),
                    icon = ":/images/label.png",
                    text = "&Add Label" )

        }

        self.actionTimer = QtCore.QTimer( self )
        self.connect( self.actionTimer, QtCore.SIGNAL( "timeout()" ), self.onRefreshAction )
        self.actionTimer.start( 250 )    # Refresh action enabled flag every 250ms.

        self.statusTimer = QtCore.QTimer( self )
        self.connect( self.statusTimer, QtCore.SIGNAL( "timeout()" ),
                      self._on_refresh_element_status )
        self.statusTimer.start( 300 )    # Refresh element status every 300ms.

    def createMenus( self ):
        self.fileMenu = self.menuBar().addMenu( self.tr( "&File" ) )
        self.fileMenu.addAction( self.newLevelAction )
        self.fileMenu.addAction( self.editLevelAction )
        self.fileMenu.addAction( self.cloneLevelAction )
        self.fileMenu.addAction( self.saveAction )
        self.fileMenu.addAction( self.playAction )
        self.fileMenu.addSeparator()
        self.fileMenu.addAction( self.changeAmyDirAction )
        self.separatorRecent = self.fileMenu.addSeparator()
        for recentaction in self.recentfile_actions:
            self.fileMenu.addAction( recentaction )
        self.fileMenu.addSeparator()
        self.fileMenu.addAction( self.quitAct )

        self.editMenu = self.menuBar().addMenu( self.tr( "&Edit" ) )
        self.editMenu.addAction( self.undoAction )
        self.editMenu.addAction( self.redoAction )
        self.editMenu.addSeparator()
        self.editMenu.addAction( self.common_actions['cut'] )
        self.editMenu.addAction( self.common_actions['copy'] )
        self.editMenu.addAction( self.common_actions['paste'] )
        self.editMenu.addAction( self.common_actions['pastehere'] )
        self.editMenu.addSeparator()
        self.editMenu.addAction( self.common_actions['delete'] )

        self.menuBar().addSeparator()
        self.resourceMenu = self.menuBar().addMenu( self.tr( "&Resources" ) )
        self.resourceMenu.addAction( self.updateResourcesAction )
        self.resourceMenu.addAction( self.importResourcesAction )
        self.resourceMenu.addSeparator()
        self.resourceMenu.addAction( self.cleanResourcesAction )
        self.resourceMenu.addSeparator()

        self.menuBar().addSeparator()

        # @todo add Windows menu. Take MDI example as model.        

        self.helpMenu = self.menuBar().addMenu( self.tr( "&Help" ) )
        self.helpMenu.addAction( self.aboutAct )

    def createToolBars( self ):
        self.fileToolBar = self.addToolBar( self.tr( "File" ) )
        self.fileToolBar.setObjectName( "fileToolbar" )
        # self.fileToolBar.addAction(self.changeAmyDirAction)
        self.fileToolBar.addAction( self.newLevelAction )
        self.fileToolBar.addAction( self.editLevelAction )
        self.fileToolBar.addAction( self.cloneLevelAction )
        self.fileToolBar.addSeparator()
        self.fileToolBar.addAction( self.saveAction )
        self.fileToolBar.addAction( self.playAction )
        self.fileToolBar.addSeparator()

        self.editToolbar = self.addToolBar( self.tr( "Edit" ) )
        self.editToolbar.setObjectName( "editToolbar" )
        self.editToolbar.addAction( self.undoAction )
        self.editToolbar.addAction( self.redoAction )
        self.editToolbar.addSeparator()
        self.editToolbar.addAction( self.common_actions['cut'] )
        self.editToolbar.addAction( self.common_actions['copy'] )
        self.editToolbar.addAction( self.common_actions['paste'] )
        self.editToolbar.addSeparator()
        self.editToolbar.addAction( self.common_actions['delete'] )

        self.resourceToolBar = self.addToolBar( self.tr( "Resources" ) )
        self.resourceToolBar.setObjectName( "resourceToolbar" )
        self.resourceToolBar.addAction( self.updateResourcesAction )
        self.resourceToolBar.addAction( self.importResourcesAction )
        self.resourceToolBar.addSeparator()
        self.resourceToolBar.addAction( self.cleanResourcesAction )
        self.resourceToolBar.addSeparator()

        self.levelViewToolBar = self.addToolBar( self.tr( "Level View" ) )
        self.levelViewToolBar.setObjectName( "levelViewToolbar" )

        for name in ( 'move', 'pan' ):
            action = self.view_actions[name]
            self.levelViewToolBar.addAction( action )

        self.addItemToolBar = QtGui.QToolBar( self.tr( "Add Item" ) )
        self.addItemToolBar.setObjectName( "addItemToolbar" )
        self.addToolBar( Qt.LeftToolBarArea, self.addItemToolBar )

        additem_action_list = ['line', 'rectangle', 'circle', 'image', 'compgeom', 'childrect', 'childcircle', 'hinge',
                            'sep1',
                            'lff', 'rff',
                            'sep2',
                            'label'
                            ]

        for name in additem_action_list:
            if name not in self.additem_actions:
                self.addItemToolBar.addSeparator()
            else:
                self.addItemToolBar.addAction( self.additem_actions[name] )

        self.showhideToolBar = self.addToolBar( self.tr( "Show/Hide" ) )
        self.showhideToolBar.setObjectName( "showhideToolbar" )

        for elementtype in ( 'camera', 'fields', 'geom', 'gfx', 'labels' ):
            self.showhideToolBar.addAction( self.showhide_actions[elementtype] )

    def createStatusBar( self ):
        self.statusBar().showMessage( self.tr( "Ready" ) )
        self._mousePositionLabel = QtGui.QLabel()
        self.statusBar().addPermanentWidget( self._mousePositionLabel )

    def createElementTreeView( self, name, tree_meta, sibling_tabbed_dock = None ):
        dock = QtGui.QDockWidget( self.tr( name ), self )
        dock.setObjectName( name + '_tab' )
        dock.setAllowedAreas( Qt.RightDockWidgetArea )
        element_tree_view = metatreeui.MetaWorldTreeView( self.common_actions, self.group_icons, dock )
        tree_model = metatreeui.MetaWorldTreeModel( tree_meta, self.group_icons,
                                                    element_tree_view )
        element_tree_view.setModel( tree_model )
        dock.setWidget( element_tree_view )
        self.addDockWidget( Qt.RightDockWidgetArea, dock )
        if sibling_tabbed_dock: # Stacks the dock widget together
            self.tabifyDockWidget( sibling_tabbed_dock, dock )
        dock.setFeatures( QtGui.QDockWidget.NoDockWidgetFeatures )
        self.tree_view_by_element_world[tree_meta] = element_tree_view
        return dock, element_tree_view

    def createDockWindows( self ):
        self.group_icons = {}
        for group in 'camera game image physic resource shape text info material rect circle compgeom line anim'.split():
            self.group_icons[group] = QtGui.QIcon( ":/images/group-%s.png" % group )
        self.tree_view_by_element_world = {} # map of all tree views
        scene_dock, self.sceneTree = self.createElementTreeView( 'Scene', metawog.TREE_LEVEL_SCENE )
        level_dock, self.levelTree = self.createElementTreeView( 'Level', metawog.TREE_LEVEL_GAME, scene_dock )
        resource_dock, self.levelResourceTree = self.createElementTreeView( 'Resource', #@UnusedVariable
                                                                            metawog.TREE_LEVEL_RESOURCE,
                                                                            level_dock )

        scene_dock.raise_() # Makes the scene the default active tab

        dock = QtGui.QDockWidget( self.tr( "Properties" ), self )
        dock.setAllowedAreas( Qt.RightDockWidgetArea )
        dock.setFeatures( QtGui.QDockWidget.NoDockWidgetFeatures )
        dock.setObjectName( 'properties' )

        self.propertiesList = metaelementui.MetaWorldPropertyListView( self.statusBar(),
                                                                       dock )

        self.propertiesListModel = metaelementui.MetaWorldPropertyListModel( 0, 2,
            self.propertiesList )  # nb rows, nb cols
        self.propertiesList.setModel( self.propertiesListModel )
        dock.setWidget( self.propertiesList )
        self.addDockWidget( Qt.RightDockWidgetArea, dock )

    def _readSettings( self ):
        """Reads setting from previous session & restore window state."""
        settings = QtCore.QSettings()
        settings.beginGroup( "MainWindow" )

        self._amy_path = unicode( settings.value( "amy_path", QtCore.QVariant( u'' ) ).toString() )
        if self._amy_path == u'.':
            self._amy_path = u''
        elif self._amy_path != u'':
            self._amy_path = os.path.normpath( self._amy_path )

        if settings.value( "wasMaximized", False ).toBool():
            self.showMaximized()
        else:
            self.resize( settings.value( "size", QtCore.QVariant( QtCore.QSize( 640, 480 ) ) ).toSize() )
            self.move( settings.value( "pos", QtCore.QVariant( QtCore.QPoint( 200, 200 ) ) ).toPoint() )
        windowstate = settings.value( "windowState", None );
        if windowstate is not None:
            self.restoreState( windowstate.toByteArray() )

        self.recentFiles = settings.value( "recent_files" ).toStringList()
        self._updateRecentFiles()
        settings.endGroup()

    def _writeSettings( self ):
        """Persists the session window state for future restoration."""
        # Settings should be stored in HKEY_CURRENT_USER\Software\WOGCorp\WOG Editor
        settings = QtCore.QSettings() #@todo makes helper to avoid QVariant conversions
        settings.beginGroup( "MainWindow" )
        settings.setValue( "amy_path", QtCore.QVariant( QtCore.QString( self._amy_path or u'' ) ) )
        settings.setValue( "wasMaximized", QtCore.QVariant( self.isMaximized() ) )
        settings.setValue( "size", QtCore.QVariant( self.size() ) )
        settings.setValue( "pos", QtCore.QVariant( self.pos() ) )
        settings.setValue( "windowState", self.saveState() )
        settings.setValue( "recent_files", self.recentFiles )
        settings.endGroup()

    def closeEvent( self, event ):
        """Called when user close the main window."""
        #@todo check if user really want to quit

        for subwin in self.mdiArea.subWindowList():
            if not subwin.close():
                event.ignore()
                return

        self._writeSettings()
        self.actionTimer.stop
        self.statusTimer.stop
        QtGui.QMainWindow.closeEvent( self, event )
        event.accept()

if __name__ == "__main__":
    app = QtGui.QApplication( sys.argv )
    # Set keys for settings
    app.setOrganizationName( "DreamFarmGames" )
    app.setOrganizationDomain( "dreamfarmgames.com" )
    app.setApplicationName( "Amy In Da Farm! Editor" )

    if LOG_TO_FILE:
        saveout = sys.stdout
        saveerr = sys.stderr
        fout = open( APP_NAME_LOWER + '.log', 'a' )
        sys.stdout = fout
        sys.stderr = fout
        print ""
        print "------------------------------------------------------"
        print APP_NAME_PROPER + " started ", datetime.now(), "File Logging Enabled"


    mainwindow = MainWindow()
    mainwindow.show()
    appex = app.exec_()

    if LOG_TO_FILE:
        sys.stdout = saveout
        sys.stderr = saveerr
        fout.close()

    sys.exit( appex )
