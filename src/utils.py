'''
Created on 23.11.2010

@author: RevEn
'''

import sys
import os

PLATFORM_WIN = 0
PLATFORM_LINUX = 1
PLATFORM_MAC = 2

#print "platform=",sys.platform

if sys.platform == 'win32' or sys.platform == 'cygwin':
    ON_PLATFORM = PLATFORM_WIN
elif sys.platform == 'darwin':
    ON_PLATFORM = PLATFORM_MAC
else:
    ON_PLATFORM = PLATFORM_LINUX


def app_path():
    if hasattr( sys, 'frozen' ):
        return os.path.dirname( sys.executable )
    else:
        return os.path.dirname( sys._getframe( 1 ).f_code.co_filename )

def getRealFilename( path ):
    # Only required on Windows
    # will return the filename in the AcTuaL CaSe it is stored on the drive
    # ensure "clean" split
    path_bits = path.replace( '\\', '/' ).replace( '//', '/' ).split( '/' )
    currentpath = path_bits.pop( 0 ) + "\\"
    for path_bit in path_bits:
        insensitive_match = ''
        sensitive_match = ''
        for entry in os.listdir( currentpath ):
            if entry == path_bit:
                # case senstive match - we can bail
                sensitive_match = entry
                break
            elif entry.lower() == path_bit.lower():
                # case insenstive match
                insensitive_match = entry
                break
        else:
            print "File not Found!", path
            return ''
        if sensitive_match != '':
            currentpath = os.path.join( currentpath, entry )
        elif insensitive_match != '':
            currentpath = os.path.join( currentpath, insensitive_match )
    return currentpath
