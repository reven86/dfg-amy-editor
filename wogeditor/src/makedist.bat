SET VERSION=0.3.1
SET SEVENZIPPATH=c:\wut\files\7-Zip\7z.exe

@echo "Build zip package distribution"
@echo "Deleting old temporary files..."
@del /Q *.pyc
@del /Q *.pyo
@del /Q wogeditor-%VERSION%-bin.zip 
@del /Q wogeditor-%VERSION%-src.zip
python deldir.py build dist wogeditor-src-%VERSION% wogeditor-%VERSION% 

@call generate.bat

@echo Tagging release in subversion
svn delete --force https://wogedit.svn.sourceforge.net/svnroot/wogedit/tags/releases/%VERSION% -m "Release %VERSION%"
svn copy https://wogedit.svn.sourceforge.net/svnroot/wogedit/trunk https://wogedit.svn.sourceforge.net/svnroot/wogedit/tags/releases/%VERSION% -m "Release %VERSION%"

@echo Exporting tagged sourcehttps://wogedit.svn.sourceforge.net/svnroot/wogedit/tags/releases/%VERSION% -m "Release %VERSION%"
svn export https://wogedit.svn.sourceforge.net/svnroot/wogedit/tags/releases/%VERSION%/wogeditor wogeditor-src-%VERSION%

@echo Building executable from sources
python setup.py --quiet py2exe

ren dist wogeditor-%VERSION%
copy ..\COPYING wogeditor-%VERSION%
copy ..\NEWS wogeditor-%VERSION%
copy ..\KNOWNBUGS.txt wogeditor-%VERSION%
copy ..\README.txt wogeditor-%VERSION%
call %SEVENZIPPATH% a -tzip wogeditor-%VERSION%-bin.zip wogeditor-%VERSION%
call %SEVENZIPPATH% a -tzip wogeditor-%VERSION%-src.zip wogeditor-src-%VERSION%

@echo "Deleting temporary files..."
python deldir.py build dist wogeditor-src-%VERSION% wogeditor-%VERSION% 
