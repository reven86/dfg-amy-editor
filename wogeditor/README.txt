* Overview:

Three command-line tools are provided:
wogfile: can pack/unpack a .bin from/to an .xml file.
scanbinfile: convert all .bin file found in a directory into .xml in a target directory
scanxmlfile: help understanding the structure and meaning of .xml by scanning through many at once.

In addition to that, a GUI editor that provides only provides level visualization is available:
wogeditor.

* Running from the source:
- you need to install python 2.5 (http://python.org)
- you need to install the pycrypto extension (http://www.amk.ca/python/code/crypto.html, or https://launchpad.net/python-crypto)
  => just run python setup.py install in the decompressed directory
  => this requires source compilation, you will likely need a C compiler to install it.
- you need to install pyqt4 (only for the editor, http://www.riverbankcomputing.co.uk/software/pyqt/download)

* Generating the executable from the source:
cd src
python setup.py py2exe
Resulting executable are in src/dist

* Running the script:
python aesfile.py input-file.bin output-file.xml

or

python scanbinfile.py resource-directory xml-output-directory


* Running the executable:

aesfile.exe input-file.bin output-file.xml
or
scanbinfile.exe resource-directory xml-output-directory

* Using the editor

First, makes a copy of your game directory and all its sub-directories. It is the directory that contains WorldOfGoo.exe). While no modification is done at the current time, its better to be safe.

Run wogeditor, and go to File/Change WOG Directory, and point to your copy of the game directory.

* Licensing

The projects are under the GPLv3 licensing. See the file COPYING.

* Contact Information

http://sourceforge.net/projects/wogedit
NitroZark <nitrozark at users.sourceforget.net>

