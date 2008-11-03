from __future__ import with_statement
import sys
from Crypto.Cipher import AES
import optparse 

def make_aes_cipher():
    """Returns a new cipher object initialized with the correct key
       that can be used to encrypt/decrypt files."""
    # AES 192 bits keys used to encrypt/decrypt data
    key = '0D0607070C01080506090904060D030F03060E010E02070B'

    def key_as_binary( key ):
        """Converts the specified hexadecimal string into a byte string."""
        assert len(key) % 2 == 0
        binary_key = []
        for index in xrange(0,len(key),2):
            binary_key.append( chr(int(key[index:index+2],16)) )
        return ''.join( binary_key )
    
    binary_key = key_as_binary( key )
    cipher = AES.new(binary_key, AES.MODE_CBC)
    return cipher

def encrypt_file_data( output_path, xml_data ):
    """Encrypt the string xml_data into a .bin file output_path."""
    cipher = make_aes_cipher()
    # adds filler so that input data length is a multiple of 16
    filler = '\xfd\xfd\xfd\xfd' + '\0' * 12
    filler_size = 16 - len(xml_data) % 16
    xml_data += filler[0:filler_size]
    # encrypt the data
    encrypted_data = cipher.encrypt( xml_data )
    with file( output_path, 'wb' ) as fout:
        fout.write( encrypted_data )
    return True

def encrypt_file( input_path, output_path ):
    """Encrypt XML file input_path into .bin file output_path using AES algorithm."""
    cipher = make_aes_cipher()
    with file( input_path, 'rb' ) as f:
        xml_data = f.read()
        if encrypt_file_data( output_path, xml_data ):
            print 'Encrypted "%s" into "%s"' % (input_path, output_path)
    return True

def decrypt_file_data( input_path ):
    """Decrypt a .bin file input_path and return the corresponding XML. May raise IOError exception."""
    cipher = make_aes_cipher()
    with file( input_path, 'rb' ) as f:
        crypted_data = f.read()
        xml_data = cipher.decrypt( crypted_data )
        # clean-up the data. Usually has '\xfd\xfd\xfd\xfd\0' at the
        # end, but this may be truncated to first '\xfd' if
        # size is nearly a multiple of 16, though there will
        # always be at least one '\xfd'.
        zero_index = xml_data.find( '\0' )
        if zero_index != -1:
            xml_data = xml_data[:zero_index]
        fd_index = xml_data.find( '\xfd' )
        if fd_index != -1:
            xml_data = xml_data[:fd_index]
    return xml_data

def decrypt_file( input_path, output_path ):
    """Decrypt a .bin file input_path into .xml file output_path using AES algorithm."""
    xml_data = decrypt_file_data( input_path )
    with file( output_path, 'wb' ) as fout:
        fout.write( xml_data )
        print 'Decrypted "%s" into "%s"' % (input_path, output_path)
    return True

def main():
    parser = optparse.OptionParser( """
1. %prog --decrypt encrypted-path decrypted-path
2. %prog --encrypt decrypted-path encrypted-path

Usage 1 will decrypt the file specified by 'encrypted-path' into the
file 'decrypted-path' (the file is overwriten if it exist').

Usage 2 will encrypt the file specified by 'decrypted-path' into the
file 'encrypted-path' (the file is overwriten if it exist').

Typically, encrypted-path file should have an extension .bin, and
decrypted-path file should have an extension .xml.
""" )
    parser.add_option( '-d', '--decrypt', dest='decrypt', action="store_true", default = False,
                       help = 'Decrypt the input path into the output path' )
    parser.add_option( '-e', '--encrypt', dest='encrypt', action="store_true", default = False,
                       help = 'Encrypt the input path into the output path' )
    (options, args) = parser.parse_args()
    if len(args) != 2:
        parser.error( 'You must specify the input and ouput path' )
    if args[0] == args[1]:
        parser.error( 'Input path must be different from output path' )

    if options.decrypt:
        return decrypt_file( args[0], args[1] )
    elif options.encrypt:
        return encrypt_file( args[0], args[1] )
    else:
        parser.error( 'You must specify either --decrypt or --encrypt' )

if __name__ == '__main__':
    succeed = main()
    if not succeed:
        print 'Failed'
        sys.exit( 2 )
