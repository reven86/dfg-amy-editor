from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
#import qthelper
import louie
#import metaworld
import metaworldui



class MetaWorldPropertyListModel(QtGui.QStandardItemModel):
    def __init__( self, *args ):
        QtGui.QStandardItemModel.__init__( self, *args )
        self.metaworld_element = None
        self.__previous_world = None
        louie.connect( self._on_active_world_change, metaworldui.ActiveWorldChanged )
        self._resetPropertyListModel()

    def _resetPropertyListModel( self, element = None ):
        self.clear()
        self.setHorizontalHeaderLabels( [self.tr('Name'), self.tr('Value')] )
        self.metaworld_element = element

    def _on_active_world_change(self, active_world):
        if self.__previous_world is not None:
            louie.disconnect( self._on_selection_change, metaworldui.WorldSelectionChanged, 
                              self.__previous_world )
        self.__previous_world = active_world
        louie.connect( self._on_selection_change, metaworldui.WorldSelectionChanged, 
                       active_world )

    def _on_selection_change(self, selected_elements, deselected_elements): #IGNORE:W0613
        # Order the properties so that main attributes are at the beginning
        if len(selected_elements) > 0:
            element = list(selected_elements)[0] #@todo handle multiple selection
            self._resetPropertyListModel( element )
            element_meta = element.meta
            world = element.world
            missing_attributes = set( element.keys() )
            for attribute_meta in element_meta.attributes_order:
                attribute_name = attribute_meta.name
                if attribute_name in missing_attributes:
                    missing_attributes.remove( attribute_name )
                attribute_value = element.get( attribute_name )
                item_name = QtGui.QStandardItem( attribute_name )
                item_name.setEditable( False )
                if attribute_value is not None: # bold property name for defined property
                    font = item_name.font()
                    font.setBold( True )
                    if attribute_value is None and attribute_meta.mandatory:
                        # @todo Also put name in red if value is not valid.
                        brush = QtGui.QBrush( QtGui.QColor( 255, 0, 0 ) )
                        font.setForeground( brush )
                    item_name.setFont( font )
                item_value = QtGui.QStandardItem( attribute_value or '' )
                item_value.setData( QtCore.QVariant( (world, element.tree, element_meta, element, attribute_name) ),
                                    Qt.UserRole )
                self.appendRow( [ item_name, item_value ] )
            if missing_attributes:
                print 'Warning: The following attributes of "%s" are missing in metaworld:' % element.tag, ', '.join( missing_attributes )
        else:
            self._resetPropertyListModel()
