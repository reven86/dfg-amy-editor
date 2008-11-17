import louie
import metaworld


class ActiveWorldChanged(louie.Signal):
    """Emitted when the current level MDI change.
       Signature: (new_active_world)
       sender: universe the world belong to
    """

class WorldSelectionChanged(louie.Signal):
    """Emitted when the selected elements change.
       Signature: (selection,selected,unselected)
       selected: set of Element that are now selected
       unselected: set of Element that are no longer selected, but were previously selected
       sender: world the element belong to
    """

class RefreshElementIssues(louie.Signal):
    """Emitted periodically from a timer to refresh element issue status.
       Signature: (), sender: Anonymous
    """ 

class ElementIssuesUpdated(louie.Signal):
    """Emitted when existing element issues have been updated
       Signature: (elements), sender: world
       elements: list of Element with modified issue
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
        
    def _check_selected_elements( self, selected_elements ):
        for element in selected_elements:
            assert element.tree is not None
            assert element.tree.world == self.__world
        
    def set_selection(self, selected_elements ):
        """Set the list of selected Elements."""
        if isinstance(selected_elements, metaworld.Element):
            selected_elements = [selected_elements]
        self._check_selected_elements( selected_elements )
        old_selection = self.__selection.copy()
        self.__selection = set(selected_elements)  
        self._send_selection_update( old_selection )

    def update_selection( self, selected_elements, deselected_elements ):
        """Adds and remove some Element from the selection."""
        selected_elements = set(selected_elements)
        deselected_elements = set(deselected_elements)
        self._check_selected_elements(selected_elements)
        old_selection = self.__selection.copy()
        self.__selection = self.__selection | selected_elements
        self.__selection = self.__selection - deselected_elements
        self._send_selection_update( old_selection )

    def _send_selection_update(self, old_selection):
        """Broadcast the selection change to the world if required."""
        if None in self.__selection:
            self.__selection.remove( None )
        selected_elements = self.__selection - old_selection
        deselected_elements = old_selection - self.__selection
        if selected_elements or deselected_elements: 
#            print 'Selection changed:'
#            print '  Selection:', self.__selection
#            print '  Selected:',  selected_elements
#            print '  Unselected:',  deselected_elements
            louie.send( WorldSelectionChanged, self.__world, 
                        self.__selection.copy(), 
                        selected_elements, deselected_elements )
        
        
CRITICAL_ISSUE = 'critical'
WARNING_ISSUE = 'warning'

class ElementIssueTracker(object):
    """Track a list of issue for all elements.
       Tracked issues concerns invalid element property, incorrect number of children,
       other constraints (missing mass for dynamic object...) 
    """
    def __init__(self, world):
        """world: world that is tracked for change.
        """
        self.__world = world
        louie.connect( self.__on_tree_added, metaworld.TreeAdded, world )
        louie.connect( self.__on_refresh_element_status, RefreshElementIssues )
        self._issues_by_element = {} #dict element:(child,attribute,node)
        self._pending_full_check = set()
        self._pending_updated = {}
        self._modified_element_issues = set()

    def element_issue_level(self, element):
        """Returns the most critical level of issue for the element.
           None if there is no pending issue.
        """
        if element in self._issues_by_element:
            return CRITICAL_ISSUE
        return None

    def element_issue_report(self, element):
        """Returns a small report of all the element issues.
        """
        issues = self._issues_by_element[element]
        if issues:
            nodes, attributes, occurrences = issues
            report = []
            if occurrences:
                for format, args in occurrences.itervalues():
                    report.append( format % args )
            if attributes:
                report.append( 'Attribute issue:')
                for name in sorted(attributes):
                    format, args = attributes[name]
                    report.append( '- "%(name)s": %(message)s' % {
                        'name':name,'message':format % args } )
            return '\n'.join( report )
        return ''

    def __on_tree_added(self, tree):
        for tree_meta in self.__world.meta.trees:
            if self.__world.find_tree(tree_meta) is None: # level not ready yet
                return
        # all tree are available, setup the level
        for tree in self.__world.trees:
            tree.connect_to_element_events( self.__on_element_added,
                                            self.__on_element_updated,
                                            self.__on_element_about_to_be_removed )
            self.__on_element_added( tree.root, 0 )

    def __on_element_added(self, element, index_in_parent): #IGNORE:W0613
        self._pending_full_check.add( element )

    def __on_element_about_to_be_removed(self, element, index_in_parent): #IGNORE:W0613
        parent = element.parent
        if parent is not None:
            self._pending_full_check.add(parent)

    def __on_element_updated(self, element, name, new_value, old_value): #IGNORE:W0613
        if element not in self._pending_updated:
            self._pending_updated[element] = set()
        self._pending_updated[element].add( name )

    def __on_refresh_element_status(self):
        import time
        start_time = time.clock()
        
        for element in self._pending_full_check:
            self._check_element( element )
        self._pending_full_check.clear()
        
        print 'Refreshed element status: %.3fs' % (time.clock()-start_time)
        start_time = time.clock()
        elements, self._modified_element_issues = self._modified_element_issues, set()
        louie.send( ElementIssuesUpdated, self.__world, elements )
        print 'Broadcast modified element issues: %.3fs' % (time.clock()-start_time)
        
         
    def _check_element(self, element):
        if element.parent is None and element.tree is None:  # deleted element
            return None
        # check child for issues
        child_issues = {}
        children_by_meta = {}
        for child in element:
            issue = self._check_element(child)
            if issue is not None:
                child_issues[child] = issue
            if child.meta not in children_by_meta: 
                children_by_meta[child.meta] = []
            children_by_meta[child.meta].append(child)
        # check attribute for issues
        attribute_issues = {}
        for attribute_meta in element.meta.attributes:
            status = element.is_attribute_valid( attribute_meta, self.__world )
            if status is not None:
                attribute_issues[attribute_meta.name] = status 
        # check node issues (mandatory children...)
        node_issues = {}
        for child_meta in element.meta.immediate_child_elements():
            status = self._check_child_occurrences( child_meta, children_by_meta )
            if status is not None:
                node_issues[child_meta] = status
        # synthesis of issues
        if child_issues or attribute_issues or node_issues:
            self._issues_by_element[element] = (child_issues, 
                                                attribute_issues, 
                                                node_issues)
            self._modified_element_issues.add( element )
            return True
        return None
            
    def _check_child_occurrences(self, meta, children_by_meta):
        occurrences = len(children_by_meta.get(meta,()))
        if ( meta.min_occurrence is not None 
             and occurrences < meta.min_occurrence ):
            if meta.min_occurrence == meta.max_occurrence:
                if meta.min_occurrence == 1:
                    return 'Element must have one %(type)s child', {'type':meta}
                return 'Element must have exactly %(count)d %(type)s children', {
                    'type':meta,'count':meta.min_occurrence}
            if meta.min_occurrence == 1:
                return 'Element must have at least one %(type)s child', {'type':meta}
            return 'Element must have at least %(count)d %(type)s children', {
                'type':meta,'count':meta.min_occurrence}
        if ( meta.max_occurrence is not None 
             and occurrences > meta.max_occurrence ):
            if meta.max_occurrence == 1:
                return 'Element must have no more than one %(type)s child', {'type':meta}
            return 'Element must have no more than %(count)d %(type)s children', {
                'type':meta,'count':meta.max_occurrence}
        return None
        
