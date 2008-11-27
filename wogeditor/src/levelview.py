"""Provides a visual representation of a LevelWorld using a QGraphicView.
"""

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import math
import louie
import metaworld
import metaworldui
import qthelper

Z_TOOL_ITEMS = 1000000 # makes sure always on top
Z_LEVEL_ITEMS = 10000.0
Z_PHYSIC_ITEMS = 9000.0

TOOL_SELECT = 'select'
TOOL_PAN = 'pan'
TOOL_MOVE = 'move'

# x coordinate of the unit vector of length = 1
UNIT_VECTOR_COORDINATE = math.sqrt(0.5)

KEY_ELEMENT = 0
KEY_TOOL = 1

global traced_level
traced_level = 0

TRACED_ACTIVE = False

def traced(f):
    """A decorator that print the method name when it is entered and exited."""
    if not TRACED_ACTIVE:
        return f
    if hasattr(f,'im_class'):
        name = '%s.%s' % (f.im_class.__name__,f.__name__)
    else:
        name = '%s' % (f.__name__)
    def traced_call( *args, **kwargs ):
        global traced_level
        print '%sEnter %s' % (traced_level*'  ', name)
        traced_level += 1
        result = f(*args, **kwargs)
        traced_level -= 1
        print '%sExit %s' % (traced_level*'  ', name)
        return result
    return traced_call

def vector2d_length(x, y):
    """Computes the magnitude of vector (x,y)."""
    return math.sqrt(x*x + y*y)

def vector2d_angle(u, v):
    """Computes the angle required to rotate 'u' around the Z axis counter-clockwise
       to be in the direction as 'v'.
       @param u tuple (x,y) representing vector U
       @param v tuple (x,y) representing vector V
       @exception ValueError is raise if either u or v is the null vector.
       @returns Angle between vector 'u' and 'v' in degrees, in range ]-180,180]
    """
    # We have: cos_uv = U.V / (|U|*|V|), where U.V is the scalar product of U and V, 
    # and |U| the magnitude of U.
    # and we have: sin_uv = |U*V| / (|U|*|V|), where U*V is the cross product of U and V
    # U.V = Ux * Vx + Uy * Vy
    # U*V = (0,0,Ux * Vy - Uy * Vx)
    # |U*V| = Ux * Vy - Uy * Vx
    length_uv = vector2d_length(*u) * vector2d_length(*v)
    if length_uv == 0.0:
        raise ValueError( "Can not computed angle between a null vector and another vector." )
    cos_uv = (u[0] * v[0] + u[1] * v[1]) / length_uv
    sign_sin_uv = u[0] * v[1] - u[1] * v[0]
    angle = math.acos( cos_uv )
    if sign_sin_uv < 0:
        angle = -angle
    return math.degrees( angle )  


# Actions:
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
                self.override_tool._handle_press_event(event)
        elif self.override_tool is None and event.buttons() == Qt.LeftButton: 
            self._handle_press_event(event)
    
    def _handle_press_event(self, event):
        """Handle press event for the tool."""
        if not self.in_use:
            self.start_using_tool()
        self._press_event = qthelper.clone_mouse_event(event)
        self._last_event = self._press_event 
        self.activated = True
    
    def on_mouse_release_event(self, event):
        if self.override_tool is not None:
            self.override_tool.on_mouse_release_event(event)
            self.override_tool.stop_using_tool()
            self.override_tool = None
        self.start_using_tool()
        self.activated = False
        self._handle_release_event(event)
    
    def _handle_release_event(self, event):
        pass
    
    def on_mouse_move_event(self, event):
        if self.override_tool is not None:
            self.override_tool.on_mouse_move_event(event)
        self.start_using_tool()
        self._handle_move_event(event)
        self._last_event = qthelper.clone_mouse_event(event)
        

    def _handle_move_event(self, event):
        pass

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
        self._view.viewport().setCursor( Qt.ArrowCursor )
        
    def _handle_press_event(self, event):
        BasicTool._handle_press_event( self, event )
        clicked_item = self._view.itemAt( event.pos() )
        if clicked_item is not None:
            self._view.select_item_element( clicked_item )


class PanTool(BasicTool):
    def _on_start_using_tool(self):
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


class MoveOrResizeTool(BasicTool):
    """
Need to get current selected item to:
- apply transformation to
- detect tool to activate on click (translate, rotate, resize)
    """
    def __init__(self, view):
        BasicTool.__init__( self, view )
        self._active_tool = None

    def _get_tool_for_event_location(self,event):
        item_at_pos = self._view.itemAt( event.pos() )
        if item_at_pos is not None:
            data = item_at_pos.data( KEY_TOOL )
            activated_tool = None
            if data.isValid():
                activated_tool = data.toPyObject()
            elif self._view.is_selected_item(item_at_pos):
                activated_tool = self._view.get_current_inner_tool()
            return activated_tool
        return None

    def _handle_press_event(self, event):
        BasicTool._handle_press_event(self, event)
        # Commit previous tool if any
        if self._active_tool:
            self._active_tool.cancel()
            self._active_tool = None
        if event.buttons() != Qt.LeftButton:
            return
        # Find if any tool handle was clicked by user
        activated_tool = self._get_tool_for_event_location( event )
        if activated_tool is not None:
            self._active_tool = activated_tool 
            print 'Selected tool:', self._active_tool
            scene_pos = self._view.mapToScene( event.pos() )
            self._active_tool.activated( scene_pos.x(), scene_pos.y() )
    
    def _handle_release_event(self, event):
        if self._active_tool is not None:
            scene_pos = self._view.mapToScene( event.pos() )
            self._active_tool.commit( scene_pos.x(), scene_pos.y() )
            self._active_tool = None
        else:
            self._handle_move_event(event)

    def _handle_move_event(self, event):
        # If a tool delegate has been activated, then forward all events
        if self._active_tool is not None:
            scene_pos = self._view.mapToScene( event.pos() )
            self._active_tool.on_mouse_move( scene_pos.x(), scene_pos.y() )
        else:
            # Otherwise try to find if one would be activated and change mouse cursor
            tool = self._get_tool_for_event_location( event )
            if tool is None: # If None, then go back to selection
                self._view.viewport().setCursor( Qt.ArrowCursor )
            else:
                tool.set_activable_mouse_cursor()

# ###################################################################
# ###################################################################
# Tool Delegates
# ###################################################################
# ###################################################################

class ToolDelegate(object):
    """A tool delegate operate on a single attribute of the object. 
       It provides the following features:
       - set mouse icon corresponding to the tool when mouse is hovering over 
         the tool activation location
       - set mouse icon to activated icon when the user press the left mouse button
       - modify the item to match user action when the mouse is moved
       - cancel or commit change to the underlying element attribute.
    """
    def __init__(self, view, element, item, attribute_meta, state_handler,
                 activable_cursor = None, activated_cursor = None):
        self.view = view
        self.element = element
        self.item = item
        self.attribute_meta = attribute_meta
        self.state_handler = state_handler
        self.activable_cursor = activable_cursor
        self.activated_cursor = activated_cursor or activable_cursor
        self._reset()
        
    def _reset(self): 
        self.activation_pos = None
        self.activation_value = None
        self.activation_item_state = None
        
    def set_activable_mouse_cursor(self):
        if self.activable_cursor is not None:
            self.view.viewport().setCursor( self.activable_cursor )
    
    def set_activated_mouse_cursor(self):
        if self.activated_cursor is not None:
            self.view.viewport().setCursor( self.activated_cursor )

    def activated(self, scene_x, scene_y):
        print 'Activated:', self
        self.set_activated_mouse_cursor()
        item_pos = self.item.mapFromScene( scene_x, scene_y )
        print 'Activated:', self, item_pos.x(), item_pos.y()
        self.activation_pos = item_pos
        self.last_pos = self.activation_pos
        self.activation_value = self.attribute_meta.get_native( self.element )
        self.activation_item_state = self.state_handler.get_item_state(self.item)
        self.on_mouse_move( scene_x, scene_y, is_activation = True )
        
    def cancelled(self):
        print 'Cancelled:', self
        if self.activation_item_state is not None:
            self.restore_activation_state()
        self._reset()
    
    def restore_activation_state(self):
        assert self.activation_item_state is not None
        self.state_handler.restore_item_state( self.item, self.activation_item_state )
    
    def commit(self, scene_x, scene_y):
        attribute_value = self.on_mouse_move( scene_x, scene_y )
        print 'Committed:', self, attribute_value
        if attribute_value is not None:
            # Delay until next event loop: destroying the scene while in event
            # handler makes the application crash
            self.view.delayed_element_property_update( self.element, 
                                                       self.attribute_meta,
                                                       attribute_value )
        self._reset()
    
    def on_mouse_move(self, scene_x, scene_y, is_activation = False):
        item_pos = self.item.mapFromScene( scene_x, scene_y )
        if is_activation:
            self._on_activation( item_pos )
        result = self._on_mouse_move( item_pos )
        self.last_pos = item_pos
        return result

    def _on_activation(self, item_pos):
        pass
    
    def _on_mouse_move(self, item_pos):
        raise NotImplemented()

class MoveToolDelegate(ToolDelegate):
    def __init__(self, view, element, item, attribute_meta, state_handler):
        ToolDelegate.__init__( self, view, element, item, attribute_meta, state_handler,
                               activable_cursor = Qt.SizeAllCursor )
        
    def _on_mouse_move(self, item_pos):
        if self.activation_pos is None:
            return None
        delta_pos = item_pos - self.activation_pos
        parent_pos = self.item.mapToParent(delta_pos)   
        self.restore_activation_state()
        self.item.setPos( parent_pos )
        return (parent_pos.x(), -parent_pos.y())

class RotateToolDelegate(ToolDelegate):
    def __init__(self, view, element, item, attribute_meta, state_handler):
        ToolDelegate.__init__( self, view, element, item, attribute_meta, state_handler,
                               activable_cursor = Qt.SizeAllCursor )
        
    def _on_mouse_move(self, item_pos):
        activation_vector = self.activation_pos
        if activation_vector.isNull():
            activation_vector = QtCore.QPointF( 1.0, 0 ) # arbitrary move it
        try:
            angle = vector2d_angle( (activation_vector.x(), activation_vector.y()),
                                    (item_pos.x(), item_pos.y()) )
        except ValueError:
            return None # Current mouse position is the Null vector @todo makes this last value
        # Compute angle between initial press and new one
        self.restore_activation_state()
        self.item.rotate( -angle )
        return angle

class ScaleToolDelegate(ToolDelegate):
    pass

class DirectionToolDelegate(ToolDelegate):
    pass

class ResizeToolDelegate(ToolDelegate):
    pass

class RadiusToolDelegate(ToolDelegate):
    def __init__(self, view, element, item, attribute_meta, state_handler):
        ToolDelegate.__init__( self, view, element, item, attribute_meta, state_handler,
                               activable_cursor = Qt.SizeBDiagCursor )
        
    def _on_mouse_move(self, item_pos):
        r_pos = vector2d_length( item_pos.x(), item_pos.y() )
        r_activation = vector2d_length( self.activation_pos.x(),
                                        self.activation_pos.y() )
        r = abs(self.activation_value + r_pos - r_activation)
        self.item.setRect( -r, -r, r*2, r*2 )
        return r

# ###################################################################
# ###################################################################
# State Managers
# ###################################################################
# ###################################################################

class StateManager(object):
    def get_item_state(self, item):
        """Returns an object representing the current item state."""
        return (item.pos(), item.transform(), self._get_item_state(item))
    
    def _get_item_state(self, item): #IGNORE:W0613
        """Returns an object represent the state specific to the item type."""
        return None
    
    def restore_item_state(self, item, state):
        """Restore the item in the state capture by get_item_state."""
        pos, transform, specific_state = state
        item.setPos( pos )
        item.setTransform( transform ) 
        self._set_item_state( item, specific_state )
        
    def _set_item_state(self, item, state):
        """Restore the item specific state capture by _get_item_state()."""
        pass

class RectangleStateManager(StateManager):
    def _get_item_state(self, item):
        return item.rect()
    
    def _restore_item_state(self, item, state):
        item.setRect( state )

class EllipseStateManager(StateManager):
    def _get_item_state(self, item):
        return (item.rect(), item.startAngle(), item.spanAngle())
    
    def _restore_item_state(self, item, state):
        rect, start_angle, span_angle = state
        item.setRect( rect )
        item.setStartAngle( start_angle )
        item.setSpanAngle( span_angle )


# ###################################################################
# ###################################################################
# Tools Factories
# ###################################################################
# ###################################################################
# Tool selector needs to handle:
# Move: inside
# Resize: 
# - on rectangle: 4 corners, rely on shift modifier to force horizontal/vertical only
# - on circle: 4 middle crossing the axis
# Rotate: 
# - on rectangle: 4 middle handles
# - on circle: 4 handles spread over at 45 degrees
# Using scene item has handle implies:
# -> Creates/destroy item on selection change, hide them during operation
# -> associates them with selected item
# -> compute handle position in item coordinate and map to scene
# -> handle should show no direction (avoid rotation transformation issue)
#
class ToolsFactory(object):
    """Responsible for creating and positioning the "handle" items used to
       activate tools (rotate, resize...) when clicked.
    """  
    def create_tools(self, item, element, view ):
        raise NotImplemented()
    
    def get_pixel_length(self, view):
        """Returns the length of a pixel in scene unit."""
        origin_pos = view.mapToScene( QtCore.QPoint() )
        f = 10000
        unit_pos = view.mapToScene( QtCore.QPoint( UNIT_VECTOR_COORDINATE*f,
                                                   UNIT_VECTOR_COORDINATE*f ) )
        unit_vector = (unit_pos - origin_pos) / f
        unit_length = vector2d_length( unit_vector.x(), unit_vector.y() )
        return unit_length

class CircleToolsFactory(ToolsFactory):

    def make_tools(self, item, element, view):
        attribute_radius = None
        attribute_center = None
        for attribute_meta in element.meta.attributes:
            if attribute_meta.type == metaworld.RADIUS_TYPE:
                attribute_radius = attribute_meta
            elif attribute_meta.type == metaworld.XY_TYPE:
                attribute_center = attribute_center or attribute_meta
        state_manager = EllipseStateManager()
        self.move_tool = MoveToolDelegate( view, element, item, attribute_center,
                                           state_manager )
        self.radius_tool = RadiusToolDelegate( view, element, item, attribute_radius,
                                               state_manager )
    
    def create_tools(self, item, element, view ):
        rect = item.boundingRect()
        y_mid = rect.y()+ rect.height() / 2.0
        x_mid = rect.x() + rect.width() / 2.0
        radius_tool_pos = [ QtCore.QPointF(rect.x(), y_mid), 
                            QtCore.QPointF(rect.right(),y_mid), 
                            QtCore.QPointF(x_mid,rect.y()), 
                            QtCore.QPointF(x_mid,rect.bottom()) ]
        rotate_tool_pos = [ rect.topLeft(), rect.topRight(), 
                           rect.bottomLeft(), rect.bottomRight() ]
        items = []
        pixel_length = self.get_pixel_length( view )
        item_pos = item.mapToScene( QtCore.QPointF() )
        self.make_tools( item, element, view )
#        for index, positions in enumerate( (radius_tool_pos, rotate_tool_pos) ):
        for index, positions in enumerate( (radius_tool_pos, ) ):
            for pos in positions:
                size = QtCore.QPointF( 3*pixel_length, 3*pixel_length )
                bound = QtCore.QRectF( pos - size, pos + size )
                if index == 0:
                    tool_item = view.scene().addRect( bound )
                    tool = self.radius_tool
                else:
                    tool_item = view.scene().addEllipse( bound )
                    tool = self.move_tool
                tool_item.setPos( item_pos )
                tool_item.setZValue( Z_TOOL_ITEMS )
                tool_item.setData( KEY_TOOL, QtCore.QVariant( tool ) )
                items.append( tool_item )
        return self.move_tool, items



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
        self._delayed_property_updates = []
        self._delayed_timer_id = None
        for name, action in tools_actions.iteritems():
            self.__tools_by_actions[action] = name
            self.__tools_group = self.__tools_group or action.actionGroup()
        self._tools_by_name = {
            TOOL_SELECT: SelectTool(self),
            TOOL_PAN: PanTool(self),
            TOOL_MOVE: MoveOrResizeTool(self)
            }
        self._active_tool = None
        self._tools_handle_items = []
        self._current_inner_tool = None
        self._items_by_element = {}
        self._selection_tool_degates_cache = (None,[])
        self.setScene( self.__scene )
        # Notes: we disable interactive mode. It is very easily to make the application
        # crash when interactive mode is allowed an mouse events are "sometimes" 
        # accepted by the overridden view. Instead, we handle selection and panning
        # ourselves.
        self.setInteractive( False )
        self.refreshFromModel()
        self.scale( 1.0, 1.0 )
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

    def is_selected_item(self, item):
        data = item.data( KEY_ELEMENT )
        if data.isValid():
            return data.toPyObject() in self.__world.selected_elements
        return False

    def get_enabled_view_tools(self):
        return set( [TOOL_PAN, TOOL_SELECT, TOOL_MOVE] )

    def get_current_inner_tool(self):
        """Returns the tool delegate to use when the user click inside a shape.
           This is usually the MoveToolDelegate.
        """
        return self._current_inner_tool

    def _update_tools_handle(self):
        """Updates tools' handle on current select item. 
           Must be called whenever the scale factory change or selection change.
        """
        # Removes any existing handle
        # Notes: we need to be very careful there, removing item that have been removed
        # by other means such as clear() cause the application to crash.
        for tool_item in self._tools_handle_items:
            self.scene().removeItem( tool_item )
        self._tools_handle_items = []
        self._current_inner_tool = None 
        # get selected elements, corresponding item and generate new handles
        elements = self.__world.selected_elements
        if len(elements) != 1: # @todo handle multiple selection
            return
        if self._get_active_tool() != self._tools_by_name[TOOL_MOVE]:
            return # No handle for select or pan tool
        element = iter(elements).next()
        item = self._items_by_element.get( element )
        if item is None:
            return
        factory_type = None
        if isinstance( item, QtGui.QGraphicsEllipseItem ):
            factory_type = CircleToolsFactory
        if factory_type is not None:
            self._current_inner_tool, self._tools_handle_items = \
                factory_type().create_tools(item, element, self)
        for tool_item in self._tools_handle_items:
            # Prevent the item from being selected
            tool_item.setAcceptedMouseButtons( Qt.NoButton ) 

    def delayed_element_property_update(self, element, attribute_meta, new_value):
        self._delayed_property_updates.append( (element, attribute_meta, new_value) )
        if self._delayed_timer_id is None:
            self._delayed_timer_id = self.startTimer(0)
        
    def timerEvent(self, event):
        if event.timerId() == self._delayed_timer_id:
            self.killTimer( self._delayed_timer_id )
            self._delayed_timer_id = None
            pending, self._delayed_property_updates = self._delayed_property_updates, []
            for element, attribute_meta, new_value in pending:
                attribute_meta.set_native( element, new_value )
            event.accept()
        else:
            QtGui.QGraphicsView.timerEvent(self, event)
        
#        if self._selection_tool_degates_cache[0] == element:
#            return self._selection_tool_degates_cache[1][:]
#        # Only handle plain rectangle, pixmap and circle at the current time
#        tool_factories = None
#        if isinstance( item, QtGui.QGraphicsRectItem, QtGui.QGraphicsPixmapItem ):
#            return RectangleToolSelector( self, element, item )
##            tool_factories = {
##                metaworld.XY_TYPE: RectangleMoveToolDelegate,
##                metaworld.SIZE_TYPE: RectangleResizeToolDelegate
##                }
#        elif isinstance( item, QtGui.QGraphicsEllipseItem ):
#            return 
##            tool_factories = {
##                metaworld.XY_TYPE: CircleMoveToolDelegate,
##                metaworld.RADIUS_TYPE: CircleRadiusToolDelegate
##                }
#        elif isinstance( item, QtGui.QGraphicsPixmapItem ):
#            tool_factories = {
#                metaworld.XY_TYPE: PixmapMoveToolDelegate,
#                metaworld.SCALE_TYPE: PixmapScaleToolDelegate
#                }
#        available_tools = []
#        for attribute in element.attributes:
#            factory = tool_factories.get(attribute.type)
#            if factory:
#                if factory == MoveOrRadiusToolDelegate:
#                    if available_tools and isinstance( available_tools[-1], 
#                                                       MoveToolDelegate):
#                        del available_tools[-1] # tool replace simple moving tool
#                        
#                tool = factory( self, element, item, attribute )
#                available_tools.append( tool )
#        self._selection_tool_degates_cache = (element, available_tools[:])
#        return available_tools

    def tool_activated( self, tool_name ):
        """Activates the corresponding tool in the view and commit any pending change.
        """
        if self._active_tool:
            self._active_tool.stop_using_tool()
        self._get_active_tool().start_using_tool()
        self._update_tools_handle()
#        if tool_name == TOOL_SELECT:
#            self.setDragMode( QtGui.QGraphicsView.NoDrag )
#        elif tool_name == TOOL_PAN:
#            self.setDragMode( QtGui.QGraphicsView.ScrollHandDrag )

    def selectLevelOnSubWindowActivation( self ):
        """Called when the user switched MDI window."""
        self.__world.game_model.selectLevel( self.__world.key )

    def select_item_element(self, item):
        """Selects the element corresponding to the specified item.
           Called when the user click on an item with the selection tool.
        """
        data = item.data( KEY_ELEMENT )
        if data.isValid():
            element = data.toPyObject()
            self.__world.set_selection( element )

    def _get_active_tool(self):
        name = self.__tools_by_actions.get( self.__tools_group.checkedAction() )
        tool = self._tools_by_name.get(name)
        if tool is None:
            tool =  self._tools_by_name[TOOL_SELECT]
        self._active_tool = tool
        return tool

    def mousePressEvent(self, event):
        self._get_active_tool().on_mouse_press_event( event )
        event.accept()

    def mouseReleaseEvent(self, event):
        self._get_active_tool().on_mouse_release_event( event )
        event.accept()

    def mouseMoveEvent( self, event):
        pos = self.mapToScene( event.pos() ) 
        self.emit( QtCore.SIGNAL('mouseMovedInScene(PyQt_PyObject,PyQt_PyObject)'), pos.x(), pos.y() )

        self._get_active_tool().on_mouse_move_event( event )
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
        self._update_tools_handle()

    def _on_selection_change(self, selection, #IGNORE:W0613
                             selected_elements, deselected_elements,
                             **kwargs): 
        """Ensures that the selected element is seleted in the graphic view.
           Called whenever an element is selected in the tree view or the graphic view.
        """
        # Notes: we do not change selection if the item belong to an item group.
        # All selection events send to an item belonging to a group are forwarded
        # to the item group, which caused infinite recursion (unselect child,
        # then unselect parent, selection parent...)
        for item in self.__scene.items():
            element = item.data(KEY_ELEMENT).toPyObject()
            if element in selection:
##                print 'Selecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
                if not item.isSelected() and item.group() is None:
                    item.setSelected( True )
            elif item.isSelected() and item.group() is None:
##                print 'Unselecting', item, 'isSelected =', item.isSelected()
##                print '    Group is', item.group()
                item.setSelected( False )
        self._update_tools_handle()

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
        self._tools_handle_items = []
        self._current_inner_tool = None
        self._items_by_element = {}
        self.__balls_by_id = {}
        self.__strands = []
        self.__lines = []
        level_element = self.__world.level_root
        self._addElements( scene, level_element, self.__level_elements, elements_to_skip )
        self._addStrands( scene )

        scene_element = self.__world.scene_root
        self._addElements( scene, scene_element, self.__scene_elements, elements_to_skip )

        for element in self.__lines:
            item = self._sceneLineBuilder( scene, element )
            self._items_by_element[element] = item            
        
##        print 'SceneRect:', self.sceneRect()
##        print 'ItemsBoundingRect:', scene.itemsBoundingRect()
##        for item in self.items():
##            print 'Item:', item.boundingRect()

        # Select currently selected item if any
        self._on_selection_change( self.__world.selected_elements, set(), set() )

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
                item.setData( KEY_ELEMENT, QtCore.QVariant( element ) )
                item.setFlag( QtGui.QGraphicsItem.ItemIsSelectable, True )
                if element.tag == 'compositegeom':
                    composite_item = item
                self._items_by_element[element] = item            
        for child_element in element:
            item = self._addElements( scene, child_element, element_set, elements_to_skip )
            if composite_item and item:
                item.setParentItem( composite_item )
        element_set.add( element )
        return item

    @staticmethod
    def _elementV2Pos( element, attribute, default_value = (0.0,0.0) ): # y=0 is bottom => Negate y
        x, y = element.get_native( attribute, default_value )
        return x, -y

    @staticmethod
    def _elementImageWithPosScaleRot( element ):
        image = element.get_native('image')
        imagepos = LevelGraphicView._elementV2Pos( element, 'imagepos' )
        imagescale = element.get_native( 'imagescale', (1.0,1.0) )
        imagerot = element.get_native( 'imagerot' )
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
        x, y = self._elementV2Pos( element, 'center' )
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
            pos = self._elementV2Pos( vertex_element, 'pos' )
            if pos is not None:
                vertexes.append( pos )
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
        x, y = self._elementV2Pos( element, 'pos' )
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
                strand_item.setData( KEY_ELEMENT, QtCore.QVariant( element ) )
                self._items_by_element[element] = strand_item

    def _levelStrandBuilder( self, scene, element ): #IGNORE:W0613
        pen = QtGui.QPen()
        pen.setWidth( 10 )

    def _levelFireBuilder( self, scene, element ):
        x, y = self._elementV2Pos( element, 'center' )
        r = element.get_native( 'radius', 1.0 )
        pen = QtGui.QPen( QtGui.QColor( 255, 64, 0 ) )
        pen.setWidth( 3 )
        item = scene.addEllipse( -r/2, -r/2, r, r, pen )
        self._setLevelItemXYZ( item, x, y )
        return item

    def _sceneSceneLayerBuilder( self, scene, element ):
        x, y = self._elementV2Pos( element, 'center' )
        depth = element.get_native( 'depth', 0.0 ) 
        image = element.get('image')
#        alpha = element.get_native( 'alpha', 1.0 )
        pixmap = self.getImagePixmap( image )
        rotation = element.get_native( 'rotation', 0.0 )
        scalex, scaley = element.get_native( 'scale', (1.0,1.0) )
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
        x, y = self._elementV2Pos( element, 'center' )
        depth = element.get_native( 'depth', 0.0 )
        rotation = element.get_native( 'rotation', 0.0 )
        scalex, scaley = element.get_native( 'scale', (1.0,1.0) )
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
        x, y = self._elementV2Pos( element, 'center' )
        rotation = element.get_native( 'rotation', 0.0 )
        scale = element.get_native( 'scale', 1.0 )
        font = QtGui.QFont()
        font.setPointSize( 24.0 )
        font.setBold( True )
        item = scene.addText( element.get('text'), font )
        item.setDefaultTextColor( QtGui.QColor( 64, 255, 0 ) )
        self._applyTransform( item, 0, 0, x, y, rotation, scale, scale, Z_PHYSIC_ITEMS )
        return item

    def _sceneCircleBuilder( self, scene, element ):
        # Still buggy: when in composite, likely position is likely relative to composite geometry
        x, y = self._elementV2Pos( element, 'center' )
        r = element.get_native( 'radius', 1.0 )
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
        x, y = self._elementV2Pos( element, 'center' )
        rotation = element.get_native( 'rotation', 0.0 )
        width, height = element.get_native( 'size', (1.0,1.0) )
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
        x, y = self._elementV2Pos( element, 'center' )
        rotation = element.get_native( 'rotation', 0.0 )
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
        x, y = self._elementV2Pos( element, 'center' )
        width, height = element.get_native( 'size', (1.0,1.0) )
        forcex, forcey = self._elementV2Pos( element, 'force', (0, 0.1) )
        depth = element.get_native( 'depth', Z_PHYSIC_ITEMS )
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
        x, y = self._elementV2Pos( element, 'center' )
        r = element.get_native( 'radius', 1.0 )
        force_at_edge = element.get_native( 'forceatedge', 0.0 )
        force_at_center = element.get_native( 'forceatcenter', 0.0 )
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


if __name__ == "__main__":
    import unittest

    class VectorTest(unittest.TestCase):

        def test_angle(self):
            def check_unit_rotation(angle, f = 1):
                u = (1,0)
                v = (math.cos( math.radians(angle) )*f, 
                     math.sin( math.radians(angle) )*f)
                actual = vector2d_angle( u, v )
                self.assertAlmostEquals( angle, actual, 1 )
            for factor in (1,5): 
                check_unit_rotation( 0, factor )
                check_unit_rotation( 45, factor )
                check_unit_rotation( 10, factor )
                check_unit_rotation( 60, factor )
                check_unit_rotation( 89, factor )
                check_unit_rotation( 90, factor )
                check_unit_rotation( 135, factor )
                check_unit_rotation( 180, factor )
                check_unit_rotation( -170, factor )
                check_unit_rotation( -90, factor )
                check_unit_rotation( -45, factor )
                check_unit_rotation( -10, factor )
            a0 = (100,0)
            a45 = (10,10) 
            a90 = (0,11)
            am45 = (10,-10) 
            am90 = (0,-1)
            self.assertAlmostEquals( -45, vector2d_angle( a45, a0 ), 1 )
            self.assertAlmostEquals( 45, vector2d_angle( a45, a90 ), 1 )
            self.assertAlmostEquals( -90, vector2d_angle( a45, am45 ), 1 )
            self.assertAlmostEquals( 180, vector2d_angle( a90, am90 ), 1 )
    unittest.main()
