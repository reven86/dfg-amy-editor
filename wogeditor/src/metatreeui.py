from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import qthelper
import louie
import metaworld
import metaworldui


class MetaWorldTreeModel(QtGui.QStandardItemModel):
    def __init__( self, meta_tree, *args ):
        QtGui.QStandardItemModel.__init__( self, *args )
        self._metaworld_tree = None
        self._meta_tree = meta_tree
        self._setHeaders()

    @property
    def metaworld_tree( self ):
        return self._metaworld_tree

    @property
    def meta_tree(self):
        return self._meta_tree

    def set_metaworld_tree( self, tree ):
        assert tree is not None
        assert tree.meta == self._meta_tree, (tree.meta, self._meta_tree)
        # setup event listener for the tree
# Notes: somehow the tree remain empty if we do not allow setting twice. To investigate...
#        if tree == self._metaworld_tree:
#            return
        if self._metaworld_tree is not None:
            self._metaworld_tree.disconnect_from_element_events( 
                self._onElementAdded, self._onElementUpdated,
                self._onElementAboutToBeRemoved )
        self._metaworld_tree = tree
        if tree is not None:
            self._metaworld_tree.connect_to_element_events( 
                self._onElementAdded, self._onElementUpdated,
                self._onElementAboutToBeRemoved )
        self._refreshTreeRoot()
        
    def _refreshTreeRoot(self):
        # refresh items
        self.clear()
        self._setHeaders()
        if self._metaworld_tree.root:
            self._insertElementTreeInTree( self, self._metaworld_tree.root )

    def _setHeaders(self):
        self.setHorizontalHeaderLabels( [self.tr('Element')] )

    def _onElementAdded(self, element, index_in_parent ):
        if element.parent is None:
            self._refreshTreeRoot()
        else:
            parent_item = self._findItemByElement( element.parent )
            if parent_item is not None:
                self._insertElementNodeInTree( parent_item, element, index_in_parent )
            else:
                print 'Warning: parent_element not found in tree view', element.parent

    def _onElementUpdated(self, element, attribute_name, new_value, old_value):
        pass # for later when name will be displayed in tree view
#        print
#        print '************ Element updated', attribute_name, new_value
#        print

    def _onElementAboutToBeRemoved(self, element, index_in_parent ): #IGNORE:W0613
        item = self._findItemByElement( element )
        if item is not None:
            item_row = item.row()
            item.parent().removeRow( item_row )
        # Notes: selection will be automatically switched to the previous row in the tree view.

    def _findItemByElement( self, element ):
        """Returns the tree view item corresponding to the specified element.
           None if the element is not in the tree.
        """
        for item in qthelper.standardModelTreeItems( self ):
            if item.data( Qt.UserRole ).toPyObject() is element:
                return item
        return None

    @staticmethod
    def _insertElementTreeInTree( item_parent, element, index = None ):
        """Inserts a sub-tree of item in item_parent at the specified index corresponding to the tree of the specified element.
           Returns the new root item of the sub-tree.
           index: if None, append the new sub-tree after all the parent chidlren.
        """
        items_to_process = [ (item_parent, element, index) ]
        while items_to_process:
            item_parent, element, index = items_to_process.pop(0)
            item = MetaWorldTreeModel._insertElementNodeInTree( item_parent, 
                                                                    element, 
                                                                    index )
            for child_element in element:
                items_to_process.append( (item, child_element, None) )

    @staticmethod
    def _insertElementNodeInTree( item_parent, element, index = None ):
        """Inserts a single child node in item_parent at the specified index corresponding to the specified element and returns item.
           index: if None, append the new child item after all the parent chidlren.
        """
        if index is None:
            index = item_parent.rowCount()
        item = QtGui.QStandardItem( element.tag )
        item.setData( QtCore.QVariant( element ), Qt.UserRole )
        item.setFlags( item.flags() & ~Qt.ItemIsEditable )
        item_parent.insertRow( index, item )
        return item

class MetaWorldTreeView(QtGui.QTreeView):
    def __init__( self, *args ):
        QtGui.QTreeView.__init__( self, *args )
        # Hook context menu popup signal
        self.setContextMenuPolicy( Qt.CustomContextMenu )
        self.connect( self, QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                      self._onContextMenu )
        louie.connect( self._on_active_world_change, metaworldui.ActiveWorldChanged )
        
    def setModel(self, model):
        QtGui.QTreeView.setModel(self, model)
        assert self.selectionModel() is not None
        self.connect( self.selectionModel(), 
                      QtCore.SIGNAL("selectionChanged(QItemSelection,QItemSelection)"),
                      self._onTreeViewSelectionChange )
        
    def _on_active_world_change(self, active_world):
        """Refresh a tree view with the new root element."""
        model = self.model()
        # disconnect for previous world selection events
        if model is not None and model.metaworld_tree is not None:
            old_world = model.metaworld_tree.world
            louie.disconnect( self._on_selection_change, metaworldui.WorldSelectionChanged, 
                              old_world )
        # connect to new world selection events & refresh tree view
        if model is None or active_world is None:
            model.set_metaworld_tree( None )
            self.hide()
        else:
            model_tree = active_world.find_tree( model.meta_tree )
            if model_tree is not None:
                louie.connect( self._on_selection_change, metaworldui.WorldSelectionChanged, 
                               active_world )
                model.set_metaworld_tree( model_tree )
                root_index = model.index(0,0)
                self.setExpanded( root_index, True )
                self.show()
            else: # the new world has no tree of the type of the view
                self.hide()

    def _on_selection_change(self, selected_elements, deselected_elements): #IGNORE:W0613
        """Select the item corresponding to element in the tree view.
        """
        selected_meta_tree = set( [element.tree.meta 
                                   for element in selected_elements] )
        model = self.model()
        selection_model = self.selectionModel()
        if model is not None and selection_model is not None:
            if model.meta_tree in selected_meta_tree:
                element = list(selected_elements)[0] # @todo handle multiple selection
                selected_item = model._findItemByElement( element )
                if selected_item:
                    selected_index = selected_item.index()
                    selection_model.select( selected_index, 
                                            QtGui.QItemSelectionModel.ClearAndSelect )
                    self.setExpanded( selected_index, True )
                    self.parent().raise_() # Raise the dock windows associated to the tree view
                    self.scrollTo( selected_index )
                else:
                    print 'Warning: selected item not found in tree view.', element
            else:
                selection_model.clear()
        
    def _onTreeViewSelectionChange( self, selected, deselected ): #IGNORE:W0613
        """Called whenever the scene tree selection change."""
        selected_indexes = selected.indexes()
        if len( selected_indexes ) == 1: # Do not handle multiple selection yet
            item = self.model().itemFromIndex( selected_indexes[0] )
            element = item.data( Qt.UserRole ).toPyObject()
            element.world.set_selection( element )

    def _onContextMenu( self, menu_pos ):
        # Select the right clicked item
        index = self.indexAt(menu_pos)
        if index.isValid():
            element = index.data( Qt.UserRole ).toPyObject()
            if element is None:
                print 'Warning: somehow managed to activate context menu on non item???'
            else:
                selection_model = self.selectionModel()
                selection_model.select( index, QtGui.QItemSelectionModel.ClearAndSelect )
                # Notes: a selectionChanged signal may have been emitted due to selection change.
                # Check out FormWindow::initializePopupMenu in designer, it does plenty of interesting stuff...
                menu = QtGui.QMenu( self )
                if not element.is_root(): 
                    remove_action = menu.addAction( self.tr("Remove element") )
                    menu.addSeparator()
                else:
                    remove_action = None
                if index.parent() is None:
                    remove_action.setEnable( False )
                child_element_meta_by_actions = {}
                element_meta = element.meta
                for tag in sorted(element_meta.immediate_child_tags()):
                    child_element_meta = element_meta.find_immediate_child_by_tag(tag)
                    if not child_element_meta.read_only:
                        action = menu.addAction( self.tr("Add child %1").arg(tag) )
                        child_element_meta_by_actions[action] = child_element_meta
                selected_action = menu.exec_( self.viewport().mapToGlobal(menu_pos) )
                selected_element_meta = child_element_meta_by_actions.get( selected_action )
                if selected_element_meta:
                    self._appendChildTag( index, selected_element_meta )
                elif remove_action is not None and selected_action is remove_action:
                    element_to_remove = self.model().itemFromIndex( index ).data( Qt.UserRole ).toPyObject()
                    element_to_remove.parent.remove( element_to_remove )
        
    def _appendChildTag( self, parent_element_index, new_element_meta ):
        """Adds the specified child tag to the specified element and update the tree view."""
        parent_element = parent_element_index.data( Qt.UserRole ).toPyObject()
        if parent_element is not None:
            # build the list of attributes with their initial values.
            mandatory_attributes = {}
            for attribute_meta in new_element_meta.attributes:
                if attribute_meta.mandatory:
                    init_value = attribute_meta.init
                    if init_value is None:
                        init_value = ''
                    if attribute_meta.type == metaworld.IDENTIFIER_TYPE:
                        init_value = parent_element.world.generate_unique_identifier(
                            attribute_meta )
                    mandatory_attributes[attribute_meta.name] = init_value
            # Notes: when the element is added, the ElementAdded signal will cause the
            # corresponding item to be inserted into the tree.
            child_element = parent_element.make_child( new_element_meta, 
                                                       mandatory_attributes )
            # Select new item in tree view
            item_child = self.model()._findItemByElement( child_element )
            selection_model = self.selectionModel()
            selection_model.select( item_child.index(), QtGui.QItemSelectionModel.ClearAndSelect )
            self.scrollTo( item_child.index() )
        else:
            print 'Warning: attempting to add an element to an item without associated elements!', parent_element, parent_element_index