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
import aesfile
import xml.etree.ElementTree 
from PyQt4 import QtCore, QtGui
import qthelper
import editleveldialog_ui
import wogeditor_rc

def tr( context, message ):
    return QtCore.QCoreApplication.translate( message )

MODEL_TYPE_LEVEL = 'Level'
LEVEL_OBJECT_TYPE = 'LevelObject'
SCENE_OBJECT_TYPE = 'SceneObject'

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
        """
        QtCore.QObject.__init__( self )
        self._wog_dir = os.path.split( wog_path )[0]
        properties_dir = os.path.join( self._wog_dir, u'properties' )
        self._res_dir = os.path.join( self._wog_dir, u'res' )
        self._effects = self._loadPackedData( properties_dir, 'fx.xml.bin' )
        self._materials = self._loadPackedData( properties_dir, 'materials.xml.bin' )
        self._resources = self._loadPackedData( properties_dir, 'resources.xml.bin' )
        self._texts = self._loadPackedData( properties_dir, 'text.xml.bin' )
        self._levels = self._loadDirList( os.path.join( self._res_dir, 'levels' ) )
        self._balls = self._loadDirList( os.path.join( self._res_dir, 'balls' ) )
        self.level_models_by_name = {}
        self.current_model = None

    def getResourcePath( self, game_dir_relative_path ):
        return os.path.join( self._wog_dir, game_dir_relative_path )

    def _loadPackedData( self, dir, file_name ):
        path = os.path.join( dir, file_name )
        if not os.path.isfile( path ):
            raise GameModelException( tr( 'LoadData',
                'File "%1" does not exist. You likely provided an incorrect WOG directory.' ).arg( path ) )
        xml_data = aesfile.decrypt_file_data( path )
        xml_tree = xml.etree.ElementTree.fromstring( xml_data )
        return xml_tree

    def _loadDirList( self, dir ):
        if not os.path.isdir( dir ):
            raise GameModelException( tr('LoadLevelList',
                'Directory "%1" does not exist. You likely provided an incorrect WOG directory.' ).arg( dir ) )
        dirs = [ entry for entry in os.listdir( dir )
                 if os.path.isdir( os.path.join( dir, entry ) ) ]
        dirs.sort()
        return dirs

    @property
    def level_names( self ):
        return self._levels

    def getLevelModel( self, level_name ):
        return self.level_models_by_name.get( level_name )

    def selectLevel( self, level_name ):
        if level_name not in self.level_models_by_name:
            self.level_models_by_name[level_name] = LevelModel( self, level_name )
        level_model = self.level_models_by_name[level_name]
        
        old_model = level_model
        self.current_model = level_model
        self.emit( QtCore.SIGNAL('currentModelChanged(PyQt_PyObject,PyQt_PyObject)'),
                   old_model,
                   level_model )

    def objectSelected( self, level_name, object_type, element ):
        """Signal that the specified object has been selected."""
        self.emit( QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                   level_name, object_type, element )

class LevelModel(object):
    def __init__( self, game_model, level_name ):
        self.game_model = game_model
        self.level_name = level_name
        level_dir = os.path.join( game_model._res_dir, 'levels', level_name )
        self.level_tree = game_model._loadPackedData( level_dir, level_name + '.level.bin' )
        self.resource_tree = game_model._loadPackedData( level_dir, level_name + '.resrc.bin' )
        self.scene_tree = game_model._loadPackedData( level_dir, level_name + '.scene.bin' )
        self.selected_object = ('SCENE', 'TAG', 'scene')

        self.images_by_id = {}
        for image_element in self.resource_tree.findall( './/Image' ):
            id, path = image_element.get('id'), image_element.get('path')
            path = game_model.getResourcePath( path + '.png' )
            if os.path.isfile( path ):
                pixmap = QtGui.QPixmap()
                if pixmap.load( path ):
                    self.images_by_id[id] = pixmap
##                    print 'Loaded', id, path
                else:
                    print 'Failed to load image:', path

    def getImagePixmap( self, image_id ):
        return self.images_by_id.get(image_id)

    def objectSelected( self, object_type, element ):
        """Indicates that the specified object has been selected.
           object_type: one of LEVEL_OBJECT_TYPE, SCENE_OBJECT_TYPE
        """
        self.game_model.objectSelected( self.level_name, object_type, element )

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
                element = item.data(0).toPyObject()
                assert element is not None, "Hmmm, forgot to associate a data to that item..."
                if element in self.__scene_elements:
                    self.getLevelModel().objectSelected( SCENE_OBJECT_TYPE, element )
                elif element in self.__level_elements:
                    self.getLevelModel().objectSelected( LEVEL_OBJECT_TYPE, element )
                else: # Should never get there
                    assert False

    def _updateObjectSelection( self, level_name, object_type, selected_element ):
        """Ensures that the selected object is seleted in the graphic view.
           Called whenever an object is selected in the tree view or the graphic view.
        """
        for item in self.__scene.items():
            element = item.data(0).toPyObject()
            if element == selected_element:
                item.setSelected( True )
            elif item.isSelected():
                item.setSelected( False )

    def matchModel( self, model_type, level_name ):
        return model_type == MODEL_TYPE_LEVEL and level_name == self.__level_name

    def getLevelModel( self ):
        return self.__game_model.getLevelModel( self.__level_name )

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
           rotation is defaulted to 0 if not defined.
           scalex and scaley are defaulted to 1 if not defined.
        """
        return ( float(element.get('rotation',0.0)),
                 float(element.get('scalex',1.0)),
                 float(element.get('scaley',1.0)) )

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
        imagerot = float(element.get('imagerot', 0.0))
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
        item = scene.addText( element.get('name') )
##            item = scene.addPixmap( pixmap )
        self._setLevelItemXYZ( item, x, y )
        return item

    def _levelPipeBuilder( self, scene, element ):
        vertexes = []
        for vertex_element in element:
            vertexes.append( self._elementXY(vertex_element) )
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
        pass
##        x, y = self._elementXY( element )
##        rotation = self._elementReal( element, 'rotation', 0.0 )
##        width = self._elementReal( element, 'width', 1.0 )
##        height = self._elementReal( element, 'height', 1.0 )
##        image, imagepos, imagescale, imagerot = self._elementImageWithPosScaleRot( element )
##        if image: # draw only the pixmap for now, but we should probably draw both the physic & pixmap
##            pixmap = self.getImagePixmap( image )
##            if pixmap:
##                item = scene.addPixmap( pixmap )
##                self._applyPixmapTransform( item, pixmap, imagepos[0], imagepos[1], imagerot,
##                                            imagescale[0], imagescale[1], 0.0 )
##                return item
##            else:
##                print 'Rectangle image not found:', image
##        else: # "physic" rectangle
##            pen = QtGui.QPen( QtGui.QColor( 0, 64, 255 ) )
##            pen.setWidth( 5 )
##            item = scene.addRect( -width/2.0, -height/2.0, width, height, pen )
##            self._applyTransform( item, width/2.0, height/2.0, x, y, rotation,
##                                  1.0, 1.0, Z_PHYSIC_ITEMS )
##        return item
        
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
        rotation = self._elementReal( element, 'rotation', 0.0 )
        image, imagepos, imagescale, imagerot = self._elementImageWithPosScaleRot( element )
        # Notes: we create an item group, but child element are NOT added to the group
        # (this would prevent selecting a specific element)
        item = scene.createItemGroup([])
        self._applyTransform( item, 0, 0, x, y, rotation, 1.0, 1.0, Z_PHYSIC_ITEMS )
        return item

    def _sceneLabelBuilder( self, scene, element ):
        pass

    def _sceneHingeBuilder( self, scene, element ):
        pass

    def _sceneLinearForceFieldBuidler( self, scene, element ):
        pass

    def _sceneRadialForceFieldBuilder( self, scene, element ):
        pass

    def _sceneMotorBuilder( self, scene, element ):
        pass

    def _sceneParticlesBuilder( self, scene, element ):
        pass


class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self._wog_path = None # Path to worl of goo executable
        
        self.mdiArea = QtGui.QMdiArea()
        self.setCentralWidget(self.mdiArea)
        
        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.createStatusBar()
        self.createDockWindows()
        self.setWindowTitle(self.tr("WOG Editor"))
        
        self._readSettings()

        self.__sceneTreeIndexByItem = {}

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
                          self._refreshPropertyList )
        except GameModelException, e:
            QtGui.QMessageBox.warning(self, self.tr("Loading WOG levels"),
                                      unicode(e))

    def _refreshLevel( self, old_model, new_game_level_model ):
        self._refreshSceneTree( new_game_level_model )
        self._refreshGraphicsView( new_game_level_model )

    def _refreshSceneTree( self, game_level_model ):
        self.sceneTree.clear()
        self.__sceneTreeIndexByItem = {}
        
        root_element = game_level_model.scene_tree
        root_item = None
        item_parent = self.sceneTree
        items_to_process = [ (item_parent, root_element) ]
        while items_to_process:
            item_parent, element = items_to_process.pop(0)
            
            item = QtGui.QTreeWidgetItem( item_parent )
            item.setText( 0, element.tag )
            item.setData( 0, QtCore.Qt.UserRole, QtCore.QVariant( element ) )
            if element == root_element:
                root_item = item
            
            for child_element in element:
                items_to_process.append( (item, child_element) )
        self.sceneTree.expandItem( root_item )  

    def _refreshGraphicsView( self, game_level_model ):
        level_view = self._findLevelGraphicView( game_level_model.level_name )
        if level_view:
            level_view.refreshFromModel( game_level_model )
        
    def _onSceneTreeSelectionChange( self ):
        """Called whenever the scene tree selection change."""
        selected_items = self.sceneTree.selectedItems()
        if len( selected_items ) == 1:
            item = selected_items[0]
            element = item.data( 0, QtCore.Qt.UserRole ).toPyObject()
            game_level_model = self.getCurrentLevelModel()
            if game_level_model:
                game_level_model.objectSelected( SCENE_OBJECT_TYPE, element )
##            self._refreshPropertyListFromElement( element )
        else:
            for item in self.sceneTree.selectedItems():
                pass # need to get an handle on the element

    def _refreshPropertyList( self, level_name, object_type, element ):
        self._refreshPropertyListFromElement( element )
        self._refreshSceneTreeSelection( object_type, element )

    def _refreshSceneTreeSelection( self, object_type, element ):
        for item in qthelper.iterQTreeWidget( self.sceneTree ):
            if item.data( 0, QtCore.Qt.UserRole ).toPyObject() == element:
                item.setSelected( True )
                item.setExpanded( True )
                index = self.sceneTree.indexFromItem( item ) # Why is this method protected ???
                self.sceneTree.scrollTo( index )
            elif item.isSelected():
                item.setSelected( False )

    def _refreshPropertyListFromElement( self, element ):
        self.propertiesList.clear()
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
        for name, value in ordered_attributes:
            item = QtGui.QTreeWidgetItem( self.propertiesList )
            item.setText( 0, name )
            item.setText( 1, value )

    def editLevel( self ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = editleveldialog_ui.Ui_Dialog()
            ui.setupUi( dialog )
            for level_name in self._game_model.level_names:
                ui.levelList.addItem( level_name )
            if dialog.exec_() and ui.levelList.currentItem:
                level_name = unicode( ui.levelList.currentItem().text() )
                self._game_model.selectLevel( level_name )
                sub_window = self._findLevelGraphicView( level_name )
                if sub_window:
                    self.mdiArea.setActiveSubWindow( sub_window )
                else:
                    sub_window = LevelGraphicView( level_name, self._game_model )
                    self.mdiArea.addSubWindow( sub_window )
                    self.connect( sub_window, QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'),
                                  self._updateMouseScenePosInStatusBar )
                    sub_window.show()

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

    def save(self):
        pass   
##        filename = QtGui.QFileDialog.getSaveFileName(self,
##                    self.tr("Choose a file name"), ".",
##                    self.tr("HTML (*.html *.htm)"))
##        if filename.isEmpty():
##            return
##
##        file = QtCore.QFile(filename)
##        if not file.open(QtCore.QFile.WriteOnly | QtCore.QFile.Text):
##            QtGui.QMessageBox.warning(self, self.tr("Dock Widgets"),
##                                      self.tr("Cannot write file %1:\n%2.")
##                                      .arg(filename)
##                                      .arg(file.errorString()))
##            return
##
##        out = QtCore.QTextStream(file)
##        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
##        out << self.textEdit.toHtml()
##        QtGui.QApplication.restoreOverrideCursor()
##        
##        self.statusBar().showMessage(self.tr("Saved '%1'").arg(filename), 2000)

    def undo( self ):
        pass
        
##    def undo(self):
##        document = self.textEdit.document()
##        document.undo()
        
    def about(self):
        QtGui.QMessageBox.about(self, self.tr("About WOG Editor"),
            self.tr("The <b>WOG editor</b> helps you create new level in WOG"))
    
    def createActions(self):
        self.changeWOGDirAction = QtGui.QAction(QtGui.QIcon(":/images/open.png"), self.tr("&Change WOG directory..."), self)
        self.changeWOGDirAction.setShortcut(self.tr("Ctrl+O"))
        self.changeWOGDirAction.setStatusTip(self.tr("Change World Of Goo top-directory"))
        self.connect(self.changeWOGDirAction, QtCore.SIGNAL("triggered()"), self.changeWOGDir)

        self.editLevelAction = QtGui.QAction(QtGui.QIcon(":/images/open-level.png"), self.tr("&Edit level..."), self)
        self.editLevelAction.setShortcut(self.tr("Ctrl+L"))
        self.editLevelAction.setStatusTip(self.tr("Select a level to edit"))
        self.connect(self.editLevelAction, QtCore.SIGNAL("triggered()"), self.editLevel)
        
        self.saveAct = QtGui.QAction(QtGui.QIcon(":/images/save.png"), self.tr("&Save..."), self)
        self.saveAct.setShortcut(self.tr("Ctrl+S"))
        self.saveAct.setStatusTip(self.tr("Save all changes made to the game"))
        self.connect(self.saveAct, QtCore.SIGNAL("triggered()"), self.save)

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

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.changeWOGDirAction)
        self.fileMenu.addAction(self.editLevelAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAct)
        
        self.editMenu = self.menuBar().addMenu(self.tr("&Edit"))
##        self.editMenu.addAction(self.editLevelAction)
        
        self.menuBar().addSeparator()

        # @todo add Windows menu. Take MDI example as model.        
        
        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.addAction(self.aboutAct)

    def createToolBars(self):
        self.fileToolBar = self.addToolBar(self.tr("File"))
        self.fileToolBar.addAction(self.changeWOGDirAction)
        self.fileToolBar.addAction(self.editLevelAction)
        
##        self.editToolBar = self.addToolBar(self.tr("Edit"))
##        self.editToolBar.addAction(self.undoAct)
        
    def createStatusBar(self):
        self.statusBar().showMessage(self.tr("Ready"))
        self._mousePositionLabel = QtGui.QLabel()
        self.statusBar().addPermanentWidget( self._mousePositionLabel )
        
    def createDockWindows(self):
        dock = QtGui.QDockWidget(self.tr("Scene"), self)
        dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
    
        self.sceneTree = QtGui.QTreeWidget(dock)
        self.sceneTree.headerItem().setText( 0, self.tr( 'Element' ) )
        dock.setWidget(self.sceneTree)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        
        dock = QtGui.QDockWidget(self.tr("Properties"), self)
        self.propertiesList = QtGui.QTreeWidget(dock)
        self.propertiesList.setRootIsDecorated( False )
        self.propertiesList.setAlternatingRowColors( True )
        self.propertiesList.headerItem().setText( 0, self.tr( 'Name' ) )
        self.propertiesList.headerItem().setText( 1, self.tr( 'Value' ) )
        dock.setWidget(self.propertiesList)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        self.connect(self.sceneTree, QtCore.SIGNAL("itemSelectionChanged()"),
                     self._onSceneTreeSelectionChange)


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
