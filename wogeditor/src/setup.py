from distutils.core import setup
import py2exe

setup(console=['aesfile.py', 'scanbinfile.py', 'scanxmlfile.py'],
      windows=[{"script":"wogeditor.py"}],
      options={"py2exe":{"includes":["sip"]}})
