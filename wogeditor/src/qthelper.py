"""Some helpers to work around some ackward aspect of the pyqt API.
"""
from PyQt4 import QtCore, QtGui

def iterQTreeWidget( tree_or_item, flag = QtGui.QTreeWidgetItemIterator.All ):
    iterator = QtGui.QTreeWidgetItemIterator(tree_or_item, flag)
    while True:
        iterator.__iadd__(1)
        value = iterator.value()
        if value is None:
            break
        yield value

def standardModelTreeItems( model, root_index = None ):
    """Returns all the row items (at column 0) of the specified index recursively. If no index is specified,
       returns all row items of the model.
       model: a QStandardItemModel
       root_index: a QModelIndex.
    """
    if root_index is None or not root_index.isValid():
        parent_indexes = [ model.index(row,0) for row in xrange(0,model.rowCount()) ]
    else:
        parent_indexes = [ root_index ]
    items = []
    while parent_indexes:
        index = parent_indexes.pop()
        parent_indexes.extend( [ index.child(row,0) for row in xrange(0,model.rowCount(index)) ] )
        items.append( model.itemFromIndex(index) )
    return items
    
def index_path( index ):
    """Returns a list of tuple (row,column) corresponding to the index path starting from
       the root.
       index: instance of QModelIndex
    """
    path = []
    if not index.isValid():
        return [(-1,-1)]
    if index.parent().isValid():
        path.extend( index_path(index.parent()) )
    path.append( (index.row(),index.column()) )
    return path

def index_path_str(index, separator = None):
    """Returns a string representing the index path.
       index: instance of QModelIndex
    """
    separator = separator or ' / '
    return separator.join( ['%d:%d' % xy for xy in index_path(index) ] )
