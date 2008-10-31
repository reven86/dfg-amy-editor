# The level editor GUI.

# The following workflow is expected:
# 1) User load a level
# 2) main windows display the scene layout
#    right-side-top-dock display:
#   - level scene tree
#   - level tree (a list in fact)
#   - level resources tree (a list in fact)
# 3) user select an object in one of the tree, related properties are displayed in
#    right-side-down-dock property list
# 4) user edit properties in property list
#
# Later on, provides property edition via scene layout display
# Add toolbar to create new object
#
# In memory, we keep track of two things:
# - updated level
# - specific text/fx resources 


import sys
import os
import aesfile
import xml.etree.ElementTree 
from PyQt4 import QtCore, QtGui
import editleveldialog_ui
import wogeditor_rc

def tr( context, message ):
    return QtCore.QCoreApplication.translate( message )

MODEL_TYPE_LEVEL = 'Level'

class GameModelException(Exception):
    pass

class GameModel(QtCore.QObject):
    def __init__( self, wog_path ):
        """Loads FX, material, text and global resources.
           Loads Balls
           Loads Levels

           The following signals are provided:
           QtCore.SIGNAL('currentModelChanged(PyQt_PyObject,PyQt_PyObject)')
           QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject)')
        """
        QtCore.QObject.__init__( self )
        self._wog_dir = os.path.split( wog_path )[0]
        properties_dir = os.path.join( self._wog_dir, u'properties' )
        self._res_dir = os.path.join( self._wog_dir, u'res' )
        self._effects = self._loadPackedData( properties_dir, 'fx.xml.bin' )
        self._materials = self._loadPackedData( properties_dir, 'materials.xml.bin' )
        self._resources = self._loadPackedData( properties_dir, 'resources.xml.bin' )
        self._texts = self._loadPackedData( properties_dir, 'text.xml.bin' )
        self._levels = self._loadDirList( os.path.join( self._res_dir, 'levels' ) )
        self._balls = self._loadDirList( os.path.join( self._res_dir, 'balls' ) )
        self.level_models_by_name = {}
        self.current_model = None

    def _loadPackedData( self, dir, file_name ):
        path = os.path.join( dir, file_name )
        if not os.path.isfile( path ):
            raise GameModelException( tr( 'LoadData',
                'File "%1" does not exist. You likely provided an incorrect WOG directory.' ).arg( path ) )
        xml_data = aesfile.decrypt_file_data( path )
        xml_tree = xml.etree.ElementTree.fromstring( xml_data )
        return xml_tree

    def _loadDirList( self, dir ):
        if not os.path.isdir( dir ):
            raise GameModelException( tr('LoadLevelList',
                'Directory "%1" does not exist. You likely provided an incorrect WOG directory.' ).arg( dir ) )
        dirs = [ entry for entry in os.listdir( dir )
                 if os.path.isdir( os.path.join( dir, entry ) ) ]
        dirs.sort()
        return dirs

    @property
    def level_names( self ):
        return self._levels

    def selectLevel( self, level_name ):
        if level_name not in self.level_models_by_name:
            self.level_models_by_name[level_name] = LevelModel( self, level_name )
        level_model = self.level_models_by_name[level_name]
        
        old_model = level_model
        self.current_model = level_model
        self.emit( QtCore.SIGNAL('currentModelChanged(PyQt_PyObject,PyQt_PyObject)'),
                   old_model,
                   level_model )

class LevelModel(object):
    def __init__( self, game_model, level_name ):
        self.game_model = game_model
        self.level_name = level_name
        level_dir = os.path.join( game_model._res_dir, 'levels', level_name )
        self.level_tree = game_model._loadPackedData( level_dir, level_name + '.level.bin' )
        self.resource_tree = game_model._loadPackedData( level_dir, level_name + '.resrc.bin' )
        self.scene_tree = game_model._loadPackedData( level_dir, level_name + '.scene.bin' )
        self.selected_object = ('SCENE', 'TAG', 'scene')

class LevelGraphicView(QtGui.QGraphicsView):
    def __init__( self, level_name, game_model ):
        QtGui.QGraphicsView.__init__( self )
        self.level_name = level_name
        self.game_model = game_model
        self.setWindowTitle( self.tr( u'Level - %1' ).arg( level_name ) )
        self.setAttribute( QtCore.Qt.WA_DeleteOnClose )

    def matchModel( self, model_type, level_name ):
        return model_type == MODEL_TYPE_LEVEL and level_name == self.level_name
    

class MainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self._wog_path = None # Path to worl of goo executable
        
        self.mdiArea = QtGui.QMdiArea()
        self.setCentralWidget(self.mdiArea)
        
        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.createStatusBar()
        self.createDockWindows()
        self.setWindowTitle(self.tr("WOG Editor"))
        
        self._readSettings()

        self._game_model = None
        if self._wog_path:
            self._reloadGameModel()
        else:
            print self._wog_path

    def changeWOGDir(self):
        wog_path =  QtGui.QFileDialog.getOpenFileName( self,
             self.tr( 'Select the file WorldOfGoo.exe to locate WOG top directory' ),
             r'e:\jeux\WorldOfGoo-mod',
             self.tr( 'WorldOfGoo.exe (WorldOfGoo.exe)' ) )
        if wog_path.isEmpty(): # user canceled action
            return
        self._wog_path = unicode(wog_path)
        self._reloadGameModel()

    def _reloadGameModel( self ):
        try:
            self._game_model = GameModel( self._wog_path )
            self.connect( self._game_model, QtCore.SIGNAL('currentModelChanged(PyQt_PyObject,PyQt_PyObject)'),
                          self._refreshSceneTree )
            self.connect( self._game_model, QtCore.SIGNAL('selectedObjectChanged(PyQt_PyObject,PyQt_PyObject)'),
                          self._refreshPropertyList )
        except GameModelException, e:
            QtGui.QMessageBox.warning(self, self.tr("Loading WOG levels"),
                                      unicode(e))

    def _refreshSceneTree( self, old_model, new_model ):
        print 'Refreshed scene tree'
        self.sceneTree.clear()
        
        root_element = new_model.scene_tree
        root_item = None
        item_parent = self.sceneTree
        items_to_process = [ (item_parent, root_element) ]
        while items_to_process:
            item_parent, element = items_to_process.pop(0)
            
            item = QtGui.QTreeWidgetItem( item_parent )
            item.setText( 0, element.tag )
            item.setData( 0, QtCore.Qt.UserRole, QtCore.QVariant( element ) )
            if element == root_element:
                root_item = item
            
            for child_element in element:
                items_to_process.append( (item, child_element) )
        self.sceneTree.expandItem( root_item )  

    def _onSceneTreeSelectionChange( self ):
        """Called whenever the scene tree selection change."""
        selected_items = self.sceneTree.selectedItems()
        if len( selected_items ) == 1:
            item = selected_items[0]
            element = item.data( 0, QtCore.Qt.UserRole ).toPyObject()
            self._refreshPropertyListFromElement( element )
        else:
            for item in self.sceneTree.selectedItems():
                pass # need to get an handle on the element

    def _refreshPropertyList( self, old_object, new_object ):
        print 'Refreshed property list'
        self._refreshPropertyListFromElement( new_object )

    def _refreshPropertyListFromElement( self, element ):
        self.propertiesList.clear()
        attribute_names = element.keys()
        attribute_order = ( 'id', 'name', 'x', 'y', 'depth', 'radius',
                            'rotation', 'scalex', 'scaley', 'image', 'alpha' )
        ordered_attributes = []
        for name in attribute_order:
            try:
                index = attribute_names.index( name )
            except ValueError: # name not found
                pass
            else: # name found
                del attribute_names[index]
                ordered_attributes.append( (name, element.get(name)) )
        ordered_attributes.extend( [ (name, element.get(name)) for name in attribute_names ] )
        for name, value in ordered_attributes:
            item = QtGui.QTreeWidgetItem( self.propertiesList )
            item.setText( 0, name )
            item.setText( 1, value )

    def editLevel( self ):
        if self._game_model:
            dialog = QtGui.QDialog()
            ui = editleveldialog_ui.Ui_Dialog()
            ui.setupUi( dialog )
            for level_name in self._game_model.level_names:
                ui.levelList.addItem( level_name )
            if dialog.exec_() and ui.levelList.currentItem:
                level_name = unicode( ui.levelList.currentItem().text() )
                self._game_model.selectLevel( level_name )
                mdi_child = None
                for window in self.mdiArea.subWindowList():
                    sub_window = window.widget()
                    if sub_window.matchModel( MODEL_TYPE_LEVEL, level_name ):
                        self.mdiArea.setActiveSubWindow( window )
                        return
                sub_window = LevelGraphicView( level_name, self._game_model )
                self.mdiArea.addSubWindow( sub_window )
                sub_window.show()
                
        
    def save(self):
        pass   
##        filename = QtGui.QFileDialog.getSaveFileName(self,
##                    self.tr("Choose a file name"), ".",
##                    self.tr("HTML (*.html *.htm)"))
##        if filename.isEmpty():
##            return
##
##        file = QtCore.QFile(filename)
##        if not file.open(QtCore.QFile.WriteOnly | QtCore.QFile.Text):
##            QtGui.QMessageBox.warning(self, self.tr("Dock Widgets"),
##                                      self.tr("Cannot write file %1:\n%2.")
##                                      .arg(filename)
##                                      .arg(file.errorString()))
##            return
##
##        out = QtCore.QTextStream(file)
##        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
##        out << self.textEdit.toHtml()
##        QtGui.QApplication.restoreOverrideCursor()
##        
##        self.statusBar().showMessage(self.tr("Saved '%1'").arg(filename), 2000)

    def undo( self ):
        pass
        
##    def undo(self):
##        document = self.textEdit.document()
##        document.undo()
        
    def about(self):
        QtGui.QMessageBox.about(self, self.tr("About WOG Editor"),
            self.tr("The <b>WOG editor</b> helps you create new level in WOG"))
    
    def createActions(self):
        self.changeWOGDirAction = QtGui.QAction(QtGui.QIcon(":/images/open.png"), self.tr("&Change WOG directory..."), self)
        self.changeWOGDirAction.setShortcut(self.tr("Ctrl+O"))
        self.changeWOGDirAction.setStatusTip(self.tr("Change World Of Goo top-directory"))
        self.connect(self.changeWOGDirAction, QtCore.SIGNAL("triggered()"), self.changeWOGDir)

        self.editLevelAction = QtGui.QAction(QtGui.QIcon(":/images/open-level.png"), self.tr("&Edit level..."), self)
        self.editLevelAction.setShortcut(self.tr("Ctrl+L"))
        self.editLevelAction.setStatusTip(self.tr("Select a level to edit"))
        self.connect(self.editLevelAction, QtCore.SIGNAL("triggered()"), self.editLevel)
        
        self.saveAct = QtGui.QAction(QtGui.QIcon(":/images/save.png"), self.tr("&Save..."), self)
        self.saveAct.setShortcut(self.tr("Ctrl+S"))
        self.saveAct.setStatusTip(self.tr("Save all changes made to the game"))
        self.connect(self.saveAct, QtCore.SIGNAL("triggered()"), self.save)

##        self.undoAct = QtGui.QAction(QtGui.QIcon(":/images/undo.png"), self.tr("&Undo"), self)
##        self.undoAct.setShortcut(self.tr("Ctrl+Z"))
##        self.undoAct.setStatusTip(self.tr("Undo the last action"))
##        self.connect(self.undoAct, QtCore.SIGNAL("triggered()"), self.undo)

        self.quitAct = QtGui.QAction(self.tr("&Quit"), self)
        self.quitAct.setShortcut(self.tr("Ctrl+Q"))
        self.quitAct.setStatusTip(self.tr("Quit the application"))
        self.connect(self.quitAct, QtCore.SIGNAL("triggered()"), self.close)
        
        self.aboutAct = QtGui.QAction(self.tr("&About"), self)
        self.aboutAct.setStatusTip(self.tr("Show the application's About box"))
        self.connect(self.aboutAct, QtCore.SIGNAL("triggered()"), self.about)

    def createMenus(self):
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.changeWOGDirAction)
        self.fileMenu.addAction(self.editLevelAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAct)
        
        self.editMenu = self.menuBar().addMenu(self.tr("&Edit"))
##        self.editMenu.addAction(self.editLevelAction)
        
        self.menuBar().addSeparator()

        # @todo add Windows menu. Take MDI example as model.        
        
        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.addAction(self.aboutAct)

    def createToolBars(self):
        self.fileToolBar = self.addToolBar(self.tr("File"))
        self.fileToolBar.addAction(self.changeWOGDirAction)
        self.fileToolBar.addAction(self.editLevelAction)
        
##        self.editToolBar = self.addToolBar(self.tr("Edit"))
##        self.editToolBar.addAction(self.undoAct)
        
    def createStatusBar(self):
        self.statusBar().showMessage(self.tr("Ready"))
        
    def createDockWindows(self):
        dock = QtGui.QDockWidget(self.tr("Scene"), self)
        dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
    
        self.sceneTree = QtGui.QTreeWidget(dock)
        self.sceneTree.headerItem().setText( 0, self.tr( 'Element' ) )
        dock.setWidget(self.sceneTree)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        
        dock = QtGui.QDockWidget(self.tr("Properties"), self)
        self.propertiesList = QtGui.QTreeWidget(dock)
        self.propertiesList.setRootIsDecorated( False )
        self.propertiesList.setAlternatingRowColors( True )
        self.propertiesList.headerItem().setText( 0, self.tr( 'Name' ) )
        self.propertiesList.headerItem().setText( 1, self.tr( 'Value' ) )
        dock.setWidget(self.propertiesList)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        self.connect(self.sceneTree, QtCore.SIGNAL("itemSelectionChanged()"),
                     self._onSceneTreeSelectionChange)


    def _readSettings( self ):
        """Reads setting from previous session & restore window state."""
        settings = QtCore.QSettings()
        settings.beginGroup( "MainWindow" )
        self._wog_path = unicode( settings.value( "wog_path", QtCore.QVariant(u'') ).toString() )
        self.resize( settings.value( "size", QtCore.QVariant( QtCore.QSize(640,480) ) ).toSize() )
        self.move( settings.value( "pos", QtCore.QVariant( QtCore.QPoint(200,200) ) ).toPoint() )
        settings.endGroup()

    def _writeSettings( self ):
        """Persists the session window state for future restoration."""
        # Settings should be stored in HKEY_CURRENT_USER\Software\WOGCorp\WOG Editor
        settings = QtCore.QSettings() #@todo makes helper to avoid QVariant conversions
        settings.beginGroup( "MainWindow" )
        settings.setValue( "wog_path", QtCore.QVariant( QtCore.QString(self._wog_path or u'') ) )
        settings.setValue( "size", QtCore.QVariant( self.size() ) )
        settings.setValue( "pos", QtCore.QVariant( self.pos() ) )
        settings.endGroup()

    def closeEvent( self, event ):
        """Called when user close the main window."""
        #@todo check if user really want to quit
        if True:
            self._writeSettings()
            event.accept()
        else:
            event.ignore()

        
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    # Set keys for settings
    app.setOrganizationName( "WOGCorp" )
    app.setOrganizationDomain( "wogedit.sourceforge.net" )
    app.setApplicationName( "Wog Editor" )
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())
