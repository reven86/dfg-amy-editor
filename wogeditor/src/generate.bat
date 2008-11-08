rem Embed image in python file
@echo Generating source embedded images
pyrcc4 -o wogeditor_rc.py wogeditor.qrc

@echo Generating GUI elements from .ui
call pyuic4.bat -o editleveldialog_ui.py  editleveldialog.ui
call pyuic4.bat -o newleveldialog_ui.py  newleveldialog.ui