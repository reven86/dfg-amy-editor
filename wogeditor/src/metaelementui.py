from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
#import qthelper
import louie
import metaworld
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

class MetaWorldPropertyListView(QtGui.QTreeView):
    def __init__(self, status_bar, *args):
        QtGui.QTreeView.__init__( self, *args )
        self.setRootIsDecorated( False )
        self.setAlternatingRowColors( True )
        delegate = PropertyListItemDelegate( self, status_bar )
        self.setItemDelegate( delegate )
        


def validate_enumerated_property( world, attribute_meta, text ):
    type_name = attribute_meta.name
    is_list = attribute_meta.is_list
    text = unicode( text )
    input_values = text.split(',')
    if len(input_values) == 0:
        if is_list:
            return QtGui.QValidator.Acceptable
        return QtGui.QValidator.Intermediate, 'One %s value is required' % type_name
    elif len(input_values) != 1 and not is_list:
        return QtGui.QValidator.Intermediate, 'Only one %s value is allowed' % type_name
    for input_value in input_values:
        if input_value not in attribute_meta.values:
            return ( QtGui.QValidator.Intermediate, 'Invalid %s value: "%%1". Valid values: %%2' % type_name,
                     input_value, ','.join(attribute_meta.values) )
    return QtGui.QValidator.Acceptable

def complete_enumerated_property( world, attribute_meta ):
    return sorted(attribute_meta.values)

def do_validate_numeric_property( attribute_meta, text, value_type, error_message ):
    try:
        value = value_type(str(text))
        if attribute_meta.min_value is not None and value < attribute_meta.min_value:
            return QtGui.QValidator.Intermediate, 'Value must be >= %1', str(attribute_meta.min_value)
        if attribute_meta.max_value is not None and value > attribute_meta.max_value:
            return QtGui.QValidator.Intermediate, 'Value must be < %1', str(attribute_meta.max_value)
        return QtGui.QValidator.Acceptable
    except ValueError:
        return QtGui.QValidator.Intermediate, error_message

def validate_integer_property( world, attribute_meta, text ):
    return do_validate_numeric_property( attribute_meta, text, int, 'Value must be an integer' )

def validate_real_property( world, attribute_meta, text ):
    return do_validate_numeric_property( attribute_meta, text, float, 'Value must be a real number' )

def validate_rgb_property( world, attribute_meta, text ):
    text = unicode(text)
    values = text.split(',')
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

def validate_xy_property( world, attribute_meta, text ):
    text = unicode(text)
    values = text.split(',')
    if len(values) != 2:
        return QtGui.QValidator.Intermediate, 'Position must be of the form "X,Y" were X and Y are real number'
    for name, value in zip('XY', values):
        try:
            value = float(value)
        except ValueError:
            return QtGui.QValidator.Intermediate, 'Position must be of the form "X,Y" were X and Y are real number'
    return QtGui.QValidator.Acceptable

def validate_reference_property( world, attribute_meta, reference_value ):
    reference_value = unicode(reference_value)
    if world.is_valid_attribute_reference( attribute_meta, reference_value ):
        return QtGui.QValidator.Acceptable
    return QtGui.QValidator.Intermediate, '"%%1" is not a valid reference to an element of type %s' % attribute_meta.reference_family, reference_value

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
# validator: called whenever the user change the text.
#           a callable(attribute_meta, text) returning either QtGui.QValidator.Acceptable if text is a valid value,
#           or a tuple (QtGui.QValidator.Intermediate, message, arg1, arg2...) if the text is invalid. Message must be
#           in QString format (e.g. %1 for arg 1...). The message is displayed in the status bar.
# converter: called when the user valid the text (enter key usualy) to store the edited value into the model.
#            a callable(editor, model, index, attribute_meta).
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
    def __init__( self, parent, status_bar, world, attribute_meta, validator ):
        QtGui.QValidator.__init__( self, parent )
        self.status_bar = status_bar
        self.attribute_meta = attribute_meta
        self.validator = validator
        self.world = world

    def validate( self, text, pos ):
        """Returns state & pos.
           Valid values for state are: QtGui.QValidator.Invalid, QtGui.QValidator.Acceptable, QtGui.QValidator.Intermediate.
           Returning Invalid actually prevent the user from inputing that a value that would make the text invalid. It is
           better to avoid returning this at it prevent temporary invalid value (when using cut'n'paste for example)."""
        status = self.validator( self.world, self.attribute_meta, text )
        if type(status) == tuple:
            message = status[1]
            args = status[2:]
            status = status[0]
            message = self.tr(message)
            for arg in args:
                message = message.arg(arg)
            self.status_bar.showMessage(message, 1000)
        return ( status, pos )


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
        if handler_data and handler_data.get('validator'):
            validator = PropertyValidator( editor, self.status_bar, world, attribute_meta, handler_data['validator'] )
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
        need_specific_converter = handler_data and handler_data.get('converter')
        if need_specific_converter:
            handler_data['converter']( editor, model, index, attribute_meta )
        else:
##            value = editor.text()
##            model.setData(index, QtCore.QVariant( value ), Qt.EditRole)
            QtGui.QStyledItemDelegate.setModelData( self, editor, model, index )
    

