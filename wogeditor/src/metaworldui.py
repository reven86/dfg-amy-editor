import louie
import metaworld


class ActiveWorldChanged(louie.Signal):
    """Emitted when the current level MDI change.
       Signature: (new_active_world)
       sender: universe the world belong to
    """

class WorldSelectionChanged(louie.Signal):
    """Emitted when the selected elements change.
       Signature: (selected,unselected)
       selected: set of Element that are now selected
       unselected: set of Element that are no longer selected, but were previously selected
       sender: world the element belong to
    """


class DirtyWorldTracker(object):
    """Provides the list of tree that have been modified in a world.
       Use element events to track change. Starts tracking for change
       only once all tree from the world description have been added 
       to the world. 
    """
    def __init__(self, world, is_dirty = False):
        """world: world that is tracked for change.
           is_dirty: is the world initially considered has dirty (new world for example).
        """
        self.__world = world
        if is_dirty:
            self.__dirty_tree_metas = set( self.__world.meta.trees )
        else:
            self.__dirty_tree_metas = set()
        louie.connect( self.__on_tree_added, metaworld.TreeAdded, world )

    def __on_tree_added(self, tree):
        for tree_meta in self.__world.meta.trees:
            if self.__world.find_tree(tree_meta) is None: # level not ready yet
                return
        # all tree are available, setup the level
        for tree in self.__world.trees:
            tree.connect_to_element_events( self.__on_element_added,
                                            self.__on_element_updated,
                                            self.__on_element_about_to_be_removed )

    def __on_element_added(self, element, index_in_parent): #IGNORE:W0613
        self.__dirty_tree_metas.add( element.tree.meta )

    def __on_element_about_to_be_removed(self, element, index_in_parent): #IGNORE:W0613
        self.__dirty_tree_metas.add( element.tree.meta )

    def __on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        self.__dirty_tree_metas.add( element.tree.meta )

    @property
    def is_dirty(self):
        """Returns True if one of the world tree has been modified."""
        return len(self.__dirty_tree_metas) > 0

    @property
    def dirty_trees(self):
        """Returns the list of modified world trees."""
        return [ self.__world.find_tree(tree_meta) 
                 for tree_meta in list(self.__dirty_tree_metas) ]
    
    @property
    def dirty_tree_metas(self):
        """Returns the types of the modified world tree."""
        return list(self.__dirty_tree_metas)

    def is_dirty_tree(self, tree_meta):
        """Return True if the specified type of world tree has been modified."""
        return tree_meta in self.dirty_tree_metas 

    def clean(self):
        """Forget any change made to the trees so that is_dirty returns True."""
        self.__dirty_tree_metas = set()

    def clean_tree(self, tree_meta):
        """Forget any change made to the specified tree type."""
        self.__dirty_tree_metas.remove( tree_meta )

class SelectedElementsTracker(object):
    def __init__(self, world):
        self.__selection = set() # set of selected elements
        self.__world = world

    @property
    def selected_elements(self):
        """List of selected Elements.""" 
        return self.__selection.copy()
        
    def set_selection(self, selected_elements ):
        """Set the list of selected Elements."""
        if isinstance(selected_elements, metaworld.Element):
            selected_elements = [selected_elements]
        old_selection = self.__selection.copy()
        self.__selection = set(selected_elements)  
        self._send_selection_update( old_selection )

    def update_selection( self, selected_elements, deselected_elements ):
        """Adds and remove some Element from the selection."""
        selected_elements = set(selected_elements)
        deselected_elements = set(deselected_elements)
        old_selection = self.__selection.copy()
        self.__selection = self.__selection | selected_elements
        self.__selection = self.__selection - deselected_elements
        self._send_selection_update( old_selection )

    def _send_selection_update(self, old_selection):
        """Broadcast the selection change to the world if required."""
        selected_elements = self.__selection - old_selection
        deselected_elements = old_selection - self.__selection
        if selected_elements or deselected_elements: 
#            print 'Selection changed:'
#            print '  Selection:', self.__selection
#            print '  Selected:',  selected_elements
#            print '  Unselected:',  deselected_elements
            louie.send( WorldSelectionChanged, self.__world, 
                        selected_elements, deselected_elements )
        