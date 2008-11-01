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
##
##class QTreeWidgetItemIterator(QtGui.QTreeWidgetItemIterator):
##    """Provides a pythonic iterator over the item of a QTreeWidget items."""
##    def __init__(self, *args):
##        QtGui.QTreeWidgetItemIterator.__init__(self, *args)
##
##    def __next__(self):
##        self.__iadd__(1)
##        value = self.value()
##        if value:
##            return self.value()
##        else:
##            raise StopIteration
