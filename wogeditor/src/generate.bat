rem Embed image in python file
@echo Generating source embedded images
pyrcc4 -o wogeditor_rc.py wogeditor.qrc

@echo Generating GUI elements from .ui
pyuic4.bat -o editleveldialog_ui.py  editleveldialog.ui