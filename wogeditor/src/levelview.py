"""Provides a visual representation of a LevelWorld using a QGraphicView.
"""

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import math
import louie
import metaworldui
import qthelper

Z_LEVEL_ITEMS = 10000.0
Z_PHYSIC_ITEMS = 9000.0

TOOL_SELECT = 'select'
TOOL_PAN = 'pan'
TOOL_MOVE = 'move'

# Workflow:
# left click: do whatever the current tool is selected to do.
#             for move tool, determine move/resize based on click location
# middle click or left+right click: start panning
# right click: context menu selection


class BasicTool(object):
    def __init__(self, view):
        self._view = view
        self._last_event = None
        self._press_event = None
        self.activated = False
        self.in_use = False
        self.override_tool = None
        
    def on_mouse_press_event(self, event):
        """Handles tool overriding with mouse button and dispatch press event.
           Middle click or left+right mouse button override the current tool
           with the PanTool.
        """
        if ( (event.buttons() == Qt.MidButton) or 
             (event.buttons() == (Qt.LeftButton|Qt.RightButton)) ):
            if self.override_tool is None:
                self.stop_using_tool()
                self.override_tool = PanTool(self._view)
                return self.override_tool._handle_press_event(event)
            return True
        elif self.override_tool is None and event.buttons() == Qt.LeftButton: 
            return self._handle_press_event(event)
        return False
    
    def _handle_press_event(self, event):
        """Handle press event for the tool."""
        if not self.in_use:
            self.start_using_tool()
        self._press_event = qthelper.clone_mouse_event(event)
        self._last_event = self._press_event 
        self.activated = True
        return True
    
    def on_mouse_release_event(self, event):
        if self.override_tool is not None:
            self.override_tool.on_mouse_release_event(event)
            self.override_tool.stop_using_tool()
            self.override_tool = None
        self.start_using_tool()
        self.activated = False
        return self._handle_release_event(event)
    
    def _handle_release_event(self, event):
        return True
    
    def on_mouse_move_event(self, event):
        if self.override_tool is not None:
            return self.override_tool.on_mouse_move_event(event)
        self.start_using_tool()
        accepted = self._handle_move_event(event)
        self._last_event = qthelper.clone_mouse_event(event)
        return accepted

    def _handle_move_event(self, event):
        return False

    def start_using_tool(self):
        if not self.in_use:
            self.in_use = True
            self._on_start_using_tool()

    def stop_using_tool(self):
        if self.in_use:
            self._on_stop_using_tool()
            self._last_event = None
            self.in_use = False

    def _on_start_using_tool(self):
        pass
    
    def _on_stop_using_tool(self):
        pass

class SelectTool(BasicTool):
    def _on_start_using_tool(self):
        self._view.setInteractive( True )
        self._view.viewport().setCursor( Qt.ArrowCursor )
        
    def _handle_press_event(self, event):
        BasicTool._handle_press_event( self, event )
        return False # always redirect to default implementation for selection
    
    def _handle_release_event(self, event):
        return False # always redirect to default implementation for selection

class PanTool(BasicTool):
    def _on_start_using_tool(self):
        self._view.setInteractive( False )
        self._view.viewport().setCursor( Qt.OpenHandCursor )

    def _handle_press_event(self, event):
        BasicTool._handle_press_event(self, event)
        self._view.viewport().setCursor( Qt.ClosedHandCursor )
        return True
    
    def _handle_release_event(self, event):
        self._view.viewport().setCursor( Qt.OpenHandCursor )
        return True
    
    def _handle_move_event(self, event):
        if self._last_event and self.activated:
            view = self._view
            h_bar = self._view.horizontalScrollBar()
            v_bar = self._view.verticalScrollBar()
            delta = event.pos() - self._last_event.pos()
            x_value = h_bar.value()
            if view.isRightToLeft():
                x_value += delta.x()
            else:
                x_value -= delta.x()
            h_bar.setValue( x_value )
            v_bar.setValue( v_bar.value() - delta.y() )
        return True


class MoveTool(BasicTool):
    pass

class ResizeTool(BasicTool):
    pass

class MoveOrResizeTool(BasicTool):
    def __init__(self, view):
        BasicTool.__init__( self, view )
        self._resize_tool = ResizeTool(view)
        self._move_tool = MoveTool(view)
        self._active_tool = None


class LevelGraphicView(QtGui.QGraphicsView):
    """A graphics view that display scene and level elements.
       Signals:
       QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)')
         => when the mouse mouse in the map. parameters: x,y in scene coordinate.
    """
    def __init__( self, level_world, tools_actions ):
        QtGui.QGraphicsView.__init__( self )
        self.__world = level_world 
        self.setWindowTitle( self.tr( u'Level - %1' ).arg( self.__world.key ) )
        self.setAttribute( Qt.WA_DeleteOnClose )
        self.__scene = QtGui.QGraphicsScene()
        self.__balls_by_id = {}
        self.__strands = []
        self.__lines = []
        self.__scene_elements = set()
        self.__level_elements = set()
        self.__tools_by_actions = {}
        self.__tools_group = None 
        for name, action in tools_actions.iteritems():
            self.__tools_by_actions[action] = name
            self.__tools_group = self.__tools_group or action.actionGroup()
        self._tools_by_name = {
            TOOL_SELECT: SelectTool(self),
            TOOL_PAN: PanTool(self),
            TOOL_MOVE: MoveOrResizeTool(self)
            }
        self._active_tool = None 
        self.setScene( self.__scene )
        self.refreshFromModel()
        self.scale( 1.0, 1.0 )
        self.connect( self.__scene, QtCore.SIGNAL('selectionChanged()'),
                      self._sceneSelectionChanged )
        self.setRenderHints( QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform )
        # Subscribes to level element change to refresh the view
        for tree in self.__world.trees:
            tree.connect_to_element_events( self.__on_element_added,
                                            self.__on_element_updated,
                                            self.__on_element_about_to_be_removed )
        louie.connect( self._on_active_world_change, metaworldui.ActiveWorldChanged, 
                       self.__world.universe )
        louie.connect( self._on_selection_change, metaworldui.WorldSelectionChanged, 
                       self.__world )

    @property
    def world(self):
        return self.__world

    def get_enabled_view_tools(self):
        return set( [TOOL_PAN, TOOL_SELECT, TOOL_MOVE] )

    def tool_activated( self, tool_name ):
        """Activates the corresponding tool in the view and commit any pending change.
        """
        if self._active_tool:
            self._active_tool.stop_using_tool()
        self._get_active_tool().start_using_tool()
#        if tool_name == TOOL_SELECT:
#            self.setDragMode( QtGui.QGraphicsView.NoDrag )
#        elif tool_name == TOOL_PAN:
#            self.setDragMode( QtGui.QGraphicsView.ScrollHandDrag )

    def selectLevelOnSubWindowActivation( self ):
        """Called when the user switched MDI window."""
        self.__world.game_model.selectLevel( self.__world.key )

    def _get_active_tool(self):
        name = self.__tools_by_actions.get( self.__tools_group.checkedAction() )
        tool = self._tools_by_name.get(name)
        if tool is None:
            tool =  self._tools_by_name[TOOL_SELECT]
        self._active_tool = tool
        return tool

    def mousePressEvent(self, event):
        accepted = self._get_active_tool().on_mouse_press_event( event )
        assert accepted is not None  
        if not accepted:
            QtGui.QGraphicsView.mousePressEvent( self, event )
        else:
            event.accept()

    def mouseReleaseEvent(self, event):
        accepted = self._get_active_tool().on_mouse_release_event( event )
        assert accepted is not None  
        if not accepted:
            QtGui.QGraphicsView.mouseReleaseEvent( self, event )
        else:
            event.accept()

    def mouseMoveEvent( self, event):
        pos = self.mapToScene( event.pos() ) 
        self.emit( QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'), pos.x(), pos.y() )

        accepted = self._get_active_tool().on_mouse_move_event( event )
        assert accepted is not None  
        if not accepted:
            QtGui.QGraphicsView.mouseMoveEvent( self, event )
        else:
            event.accept()

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

    def _on_selection_change(self, selection, #IGNORE:W0613
                             selected_elements, deselected_elements): 
        """Ensures that the selected element is seleted in the graphic view.
           Called whenever an element is selected in the tree view or the graphic view.
        """
        # Notes: we do not change selection if the item belong to an item group.
        # All selection events send to an item belonging to a group are forwarded
        # to the item group, which caused infinite recursion (unselect child,
        # then unselect parent, selection parent...)
        for item in self.__scene.items():
            element = item.data(0).toPyObject()
            if element in selection:
##                print 'Selecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
                if not item.isSelected() and item.group() is None:
                    item.setSelected( True )
            elif item.isSelected() and item.group() is None:
##                print 'Unselecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
                item.setSelected( False )

    def getLevelModel( self ):
        return self.__world

    def __on_element_added(self, element, index_in_parent): #IGNORE:W0613
        self.refreshFromModel()

    def __on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        self.refreshFromModel()

    def __on_element_about_to_be_removed(self, element, index_in_parent): #IGNORE:W0613
        self.refreshFromModel( set([element]) )

    def _on_active_world_change(self, active_world):
        """Called when a new world becomes active (may be another one).
        """
        if active_world == self.__world:
            self.refreshFromModel()

    def refreshFromModel( self, elements_to_skip = None ):
        elements_to_skip = elements_to_skip or set()
        scene = self.__scene
        scene.clear()
        self.__balls_by_id = {}
        self.__strands = []
        self.__lines = []
        level_element = self.__world.level_root
        self._addElements( scene, level_element, self.__level_elements, elements_to_skip )
        self._addStrands( scene )

        scene_element = self.__world.scene_root
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
        if image_id is not None:
            return self.__world.getImagePixmap( image_id )
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
