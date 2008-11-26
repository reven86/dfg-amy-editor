from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import qthelper
import louie
import metaworld
import metaworldui



class MetaWorldPropertyListModel(QtGui.QStandardItemModel):
    def __init__( self, *args ):
        QtGui.QStandardItemModel.__init__( self, *args )
        self._element = None
        self._element_tree = None
        self._active_world = None
        # Selection change event are on a per world basis, so listen for the current world
        louie.connect( self._on_active_world_change, metaworldui.ActiveWorldChanged )
        self._resetPropertyListModel()

    def _on_active_world_change(self, active_world):
        if self._active_world is not None:
            louie.disconnect( self._on_selection_change, metaworldui.WorldSelectionChanged, 
                              self._active_world )
            louie.disconnect( self._on_element_issues_updated, 
                              metaworldui.ElementIssuesUpdated,
                              self._active_world )
        self._active_world = active_world
        if active_world is not None:
            louie.connect( self._on_selection_change, metaworldui.WorldSelectionChanged, 
                           active_world )
            louie.connect( self._on_element_issues_updated, 
                           metaworldui.ElementIssuesUpdated,
                           self._active_world )

    def _resetPropertyListModel( self, element = None ):
        """Change the element displayed in the property list.
           Subscribe to update event for the element and unsubscribe from the old one.
        """
        self.clear()
        self.setHorizontalHeaderLabels( [self.tr('Name'), self.tr('Value')] )
        if self._element_tree is not None:
            louie.disconnect( self.__on_element_updated, metaworld.AttributeUpdated, 
                              self._element_tree )
            self._element_tree = None
        self._element = element
        if element is not None:
            self._element_tree = element.tree
            louie.connect( self.__on_element_updated, metaworld.AttributeUpdated, 
                           self._element_tree )

    def __on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        if element != self._element:
            return
        # An attribute of the element has been modified, find it & refresh it
        for item in qthelper.standardModelTreeItems( self ): # returns first columns item
            element, property_name = self.get_item_element_and_property( item )
            if property_name == name:
                attribute_meta = element.meta.attribute_by_name( name )
                self._update_property_name_face( element, attribute_meta, item )
                self._update_property_value( new_value, item )  

    def _on_element_issues_updated( self, elements ):
        if self._element in elements:
            # Element issues have changed, refresh all properties name face
            for item in qthelper.standardModelTreeItems( self ): # returns first columns item
                element, property_name = self.get_item_element_and_property( item )
                attribute_meta = element.meta.attribute_by_name( property_name )
                self._update_property_name_face(element, attribute_meta, item)  

    def _on_selection_change(self, selection, #IGNORE:W0613
                             selected_elements, deselected_elements):
        # On selection change, display the attributes of the new selected element 
        if len(selected_elements) > 0:
            element = list(selected_elements)[0] #@todo handle multiple selection
            self._resetPropertyListModel( element )
            self._refreshPropertyList()
        else:
            self._resetPropertyListModel()

    def get_item_element_and_property( self, item ):
        """Returns the element and the property name associated to an item.
        """
        assert isinstance( item, QtGui.QStandardItem )
        data =  item.data( Qt.UserRole )
        assert data.isValid() # if this fails, then we are trying to edit the item was added incorrectly.
        data = data.toPyObject() 
        world, tree_meta, element_meta, element, property_name = data
        return element, property_name

    def _update_property_name_face( self, element, attribute_meta, item_name, 
                                    world = None ):
        """Apply the style on property name according to its status. 
           Style: 
           - Bold face if the attribute is defined on the element
           - Property name displayed in red if there is an associated issue
        """
        world = world or element.world
        font = item_name.font()
        # bold property name for defined property
        attribute_value = attribute_meta.get(element)
        font.setBold( attribute_value is not None )
        issue = world.element_attribute_issue( element, attribute_meta.name )
        if issue:
            brush = QtGui.QBrush( QtGui.QColor( 255, 0, 0 ) )
            item_name.setForeground( brush )
            item_name.setToolTip( issue )
        else: # Restore default foreground color
            item_name.setData( QtCore.QVariant(), Qt.ForegroundRole )
        item_name.setFont( font )

    def _update_property_value(self, value, item):
        """Update the value of the property."""
        item = qthelper.get_row_item_sibling( item, 1 )
        item.setText( value )
    
    def _refreshPropertyList(self):
        element = self._element
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
            self._update_property_name_face( element, attribute_meta, item_name, world )
            item_value = QtGui.QStandardItem( attribute_value or '' )
            data = (world, element.tree, element_meta, element, attribute_name)
            for item in (item_name, item_value):
                item.setData( QtCore.QVariant( data ), Qt.UserRole )
            self.appendRow( [ item_name, item_value ] )
        if missing_attributes:
            print 'Warning: The following attributes of "%s" are missing in metaworld:' % element.tag, ', '.join( missing_attributes )

class MetaWorldPropertyListView(QtGui.QTreeView):
    def __init__(self, status_bar, *args):
        QtGui.QTreeView.__init__( self, *args )
        self.setRootIsDecorated( False )
        self.setAlternatingRowColors( True )
        delegate = PropertyListItemDelegate( self, status_bar )
        self.setItemDelegate( delegate )
        
def complete_enumerated_property( world, attribute_meta ): #IGNORE:W0613
    return sorted(attribute_meta.values)

def complete_reference_property( world, attribute_meta ):
    return world.list_identifiers( attribute_meta.reference_family )

# For later
##def editor_rgb_property( parent, option, index, element, attribute_meta, default_editor_factory ):
##    widget = QtGui.QWidget( parent )
##    hbox = QtGui.QHBoxLayout()
##    hbox.addWidget( default_editor_factory )
##    push_button = QtGui.QPushButton( 
##    hbox.addWidget( push_button )
    

# A dictionnary of specific handler for metawog attribute types.
# completer: called when the user starts editing the property
#           a callable ( world, attribute_meta ) returning a list of valid text value.
ATTRIBUTE_TYPE_EDITOR_HANDLERS = {
    metaworld.BOOLEAN_TYPE: { 'completer': complete_enumerated_property },
    metaworld.ENUMERATED_TYPE: { 'completer': complete_enumerated_property },
    metaworld.REFERENCE_TYPE: { 'completer': complete_reference_property }
    }

class PropertyValidator(QtGui.QValidator):
    def __init__( self, parent, status_bar, world, attribute_meta ):
        QtGui.QValidator.__init__( self, parent )
        self.status_bar = status_bar
        self.attribute_meta = attribute_meta
        self.world = world

    def validate( self, text, pos ):
        """Returns state & pos.
           Valid values for state are: QtGui.QValidator.Invalid, QtGui.QValidator.Acceptable, QtGui.QValidator.Intermediate.
           Returning Invalid actually prevent the user from inputing that a value that would make the text invalid. It is
           better to avoid returning this at it prevent temporary invalid value (when using cut'n'paste for example)."""
        text = unicode(text)
        # An empty mandatory input will be modified in an unset attribute action
        if text or not self.attribute_meta.mandatory:
            status = self.attribute_meta.is_valid_value( text, self.world )
            if status: # error found
                message = status[0] % status[1]
                self.status_bar.showMessage(message, 1000)
                return (QtGui.QValidator.Intermediate,pos)
        return (QtGui.QValidator.Acceptable,pos)


class PropertyListItemDelegate(QtGui.QStyledItemDelegate):
    def __init__( self, parent, status_bar ):
        QtGui.QStyledItemDelegate.__init__( self, parent )
        self.status_bar = status_bar

    def createEditor( self, parent, option, index ):
        """Returns the widget used to edit the item specified by index for editing. The parent widget and style option are used to control how the editor widget appears."""
        # see QDefaultItemEditorFactory::createEditor for example of implementations
        world, tree_meta, element, property_name, attribute_meta, handler_data = self._getHandlerData( index )
        need_specific_editor = handler_data and handler_data.get('editor')
        if need_specific_editor:
            class DefaultEditorFactory(object):
                def __init__( self, *args ):
                    self.args = args
                def __call_( self, parent ):
                    return QtGui.QStyledItemDelegate.createEditor( self.args[0], parent, *(self.args[1:]) )
            editor = handler_data['editor']( parent, option, index, element, attribute_meta, DefaultEditorFactory() )
        else: # No specific, use default QLineEditor
            editor = QtGui.QStyledItemDelegate.createEditor( self, parent, option, index )

        # Set attribute meta validation adapter
        validator = PropertyValidator( editor, self.status_bar, world, attribute_meta )
        editor.setValidator( validator )
        
        if handler_data and handler_data.get('completer'):
            word_list = QtCore.QStringList()
            completer = handler_data['completer'] 
            sorted_word_list = list( completer( world, attribute_meta ) )
            sorted_word_list.sort( lambda x,y: cmp(x.lower(), y.lower()) )
            for word in sorted_word_list:
                word_list.append( word )
            completer = QtGui.QCompleter( word_list, editor )
            completer.setCaseSensitivity( Qt.CaseInsensitive )
            completer.setCompletionMode( QtGui.QCompleter.UnfilteredPopupCompletion )
            editor.setCompleter( completer )
        return editor

    def _getHandlerData( self, index ):
        """Returns data related to item at the specified index.
           Returns: tuple (world, tree_meta, element, property_name, attribute_meta, handler_data). 
           handler_data may be None if no specific handler is defined for the attribute_meta.
           attribute_meta may be None if metawog is missing some attribute declaration.
           """
        data =  index.data( Qt.UserRole ).toPyObject()
        # if this fails, then we are trying to edit the property name or item was added incorrectly.
        assert data is not None
        world, tree_meta, element_meta, element, property_name = data
        if element_meta is None:
            handler_data = None
            attribute_meta = None
            print 'Warning: metawog is incomplet, no attribute description for', tree_meta, element.tag, property_name
        else:
            attribute_meta = element_meta.attributes_by_name.get( property_name )
            if attribute_meta is None:
                print 'Warning: metawog is incomplet, no attribute description for', tree_meta, element.tag, property_name
                handler_data = None
            else:
                handler_data = ATTRIBUTE_TYPE_EDITOR_HANDLERS.get( attribute_meta.type )
        return (world, tree_meta, element, property_name, attribute_meta, handler_data)

    def setEditorData( self, editor, index ):
        """Sets the data to be displayed and edited by the editor from the data model item specified by the model index."""
        world, tree_meta, element, property_name, attribute_meta, handler_data = self._getHandlerData( index )
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
        world, tree_meta, element, property_name, attribute_meta, handler_data = self._getHandlerData( index )
        if not editor.hasAcceptableInput(): # text is invalid, discard it
            return
        # Update the element attribute. The model will be updated 
        # by the element update event.
        new_value = unicode( editor.text() )
        if len(new_value) == 0 and attribute_meta.mandatory:
            element.unset( property_name )
        else:
            element.set( property_name, new_value )
#        model.setData(index, QtCore.QVariant( value ), Qt.EditRole)
#            QtGui.QStyledItemDelegate.setModelData( self, editor, model, index )
    

