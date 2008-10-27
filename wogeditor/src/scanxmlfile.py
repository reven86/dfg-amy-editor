"""Scans all XML files in a sub-directory and output all found values for a given node/attribute."""
from __future__ import with_statement
import os
import os.path
import glob
import optparse
import sys
import xml.etree.ElementTree 

OCCURRENCE_TYPE_NODE = 'NODE'
OCCURRENCE_TYPE_ATTRIBUTE = 'ATTRIBUTE'

def find_xml_attribute_value( xml_data, target_node_name, target_attribute_name ):
    """If target_attribute_name is not None, returns a list of all occurrences of the
       specified attribute in the specified node. For each occurrence, a tuple
       (element_node, attribute_value) is in the result list. If the node
       has no attribute of the specified name, then attribute_value is None.

       If target_attribute_name is None, returns a list of (element_node, occurrence_type, name)
       for each attribute and child node of a node with tag target_node_name, where occurrence_type is one of:
       OCCURRENCE_TYPE_NODE: for child node, then <name> is the child node tag name
       OCCURRENCE_TYPE_ATTRIBUTE: for attribute occurrence, then <name> is the attribute name
    """
    element_tree = xml.etree.ElementTree.fromstring( xml_data )
    #xml.etree.ElementTree.dump( element_tree )
    occurrences = []
    for node in element_tree.getiterator( target_node_name ):
        # See c:\Python25\Lib\xml\etree\ElementTree.py for node interface
        if target_attribute_name is not None:
            attribute_value = node.get( target_attribute_name )
            occurrences.append( (node, attribute_value) )
        else:
            for attribute_name, attribute_value in node.items():
                occurrences.append( (node, OCCURRENCE_TYPE_ATTRIBUTE, attribute_name) )
            for child_node in node:
                occurrences.append( (node, OCCURRENCE_TYPE_NODE, child_node.tag) )
    return occurrences

def find_xml_attribute_value_in_directory( xml_dir, target_node_name, target_attribute_name ):
    """Scan all the XML files in the directory and sub-directory for the value of the specified attribute
       in the specified node.
       If target_attribute_name is not None, returns a list of tuple (path, node_element, attribute_value). attribute_value is None if
       an occurrence of the node was found without the attribute.
       If target_attribute_name is None, returns a list of tuple (path, node_element, occurrence_type, name).
       """
    all_occurrences = []
    for entry in os.listdir( xml_dir ):
        entry_path = os.path.join( xml_dir, entry )
        if os.path.isdir( entry_path ):
            all_occurrences.extend( find_xml_attribute_value_in_directory( entry_path,
                                                                           target_node_name,
                                                                           target_attribute_name ) )
        elif os.path.splitext( entry )[1].lower() == '.xml':
            with file( entry_path, 'rb') as f:
                xml_data = f.read()
##                print 'Scanning "%s"' % entry_path
                file_occurrences = find_xml_attribute_value( xml_data,
                                                             target_node_name,
                                                             target_attribute_name )
                for occurrence in file_occurrences:
                    occurrence = list(occurrence)
                    occurrence.insert( 0, entry_path )
                    all_occurrences.append( tuple(occurrence) )
    return all_occurrences

def main():
    parser = optparse.OptionParser( """%prog xml-dir-path node_name [attribute_name]

This applications scan all XML contained in the specified directory and its sub-directory and print all value found for the given node_name/attribute_name pair.
If no attribute is specified, then the list of all attributes and child node tag found for the node <node_name> is dumped.

Example:
%prog c:\\wog\\xml level letterboxed

Will dump all the value of the attribute "letterboxed" found in node "level"
""" )
    parser.add_option( '-u', '--unique', dest='unique_value', action="store_true", default = False,
                       help = 'Show only unique attribute values' )
    (options, args) = parser.parse_args()
    if len(args) < 2 or len(args) > 3:
        parser.error( 'You must specify the input directory, the node name and the attribute name' )

    xml_dir, target_node_name = args[0], args[1]
    # Set target_attribute_name if we are scanning for all attributes associated to the node.
    target_attribute_name = len(args) == 3 and args[2] or None

    if options.unique_value and target_attribute_name is None:
        parser.error( 'Can not specify options --unique when listing all attributes of a node' )
    
    if not os.path.isdir( xml_dir ):
        parser.error( '"%s" is not a directory' % xml_dir )

    occurrences = find_xml_attribute_value_in_directory( xml_dir, target_node_name, target_attribute_name )
    if options.unique_value:
        unique_values = {} # map value/occurrences
        for path, node_element, attribute_value in occurrences:
            if attribute_value not in unique_values:
                unique_values[attribute_value] = []
            unique_values[attribute_value].append( (path, node_element, attribute_value) )
        for value, occurrences in unique_values.iteritems():
            if value is None:
                attribute_message = 'no attribute "%s"' % target_attribute_name
            else:
                attribute_message = 'attribute "%s"="%s"' % (target_attribute_name, value)
            print '* %d occurrences of node "%s" with %s' % (
                len(occurrences), target_node_name, attribute_message)
            for path, node_element, attribute_value in occurrences:
              print '  - "%s"' % path
        print '%d distinct values found' % len(unique_values)
    elif target_attribute_name:
        for path, node_element, attribute_value in occurrences:
            if attribute_value is None:
                print '%s: node "%s" occurrence with no attribute named "%s"' % (
                    path, target_node_name, target_attribute_name)
            else:
                print '%s: node "%s", %s="%s"' % (
                    path, target_node_name, target_attribute_name, attribute_value)
        print '%d occurrences found' % len(occurrences)
    else: # listing all attributes & child nodes
        def listAllAttributes( occurrences ):
            unique_attributes = {}
            attributes_by_node = {}
            for path, node_element, occurrence_type, attribute_name in occurrences:
                if occurrence_type is not OCCURRENCE_TYPE_ATTRIBUTE:
                    continue
                if attribute_name not in unique_attributes:
                    unique_attributes[attribute_name] = []
                unique_attributes[attribute_name].append( (path, node_element, attribute_name) )
                if node_element not in attributes_by_node:
                    attributes_by_node[node_element] = set()
                attributes_by_node[node_element].add( attribute_name )
            sorted_attribute_names = unique_attributes.keys()
            sorted_attribute_names.sort()
            for attribute_name in sorted_attribute_names:
                occurrences = unique_attributes[attribute_name]
                missing_count = 0
                for node, attribute_names in attributes_by_node.iteritems():
                    if attribute_name not in attribute_names:
                        missing_count += 1
                is_optional = (missing_count > 0)
                if is_optional:
                    print 'Node "%s", attribute "%s" is optional, occurrences with/without attribute: %d/%d' % (
                        target_node_name, attribute_name, len(occurrences), missing_count)
                else:
                    print 'Node "%s", attribute "%s" is mandatory (%d occurrences found)' % (
                        target_node_name, attribute_name, len(occurrences))
            print '%d attributes found' % len(unique_attributes)

        def listAllChildNodeTags( occurrences ):
            unique_tags = {}
            child_by_node = {}
            for path, node_element, occurrence_type, child_tag_name in occurrences:
                if occurrence_type is not OCCURRENCE_TYPE_NODE:
                    continue
                if child_tag_name not in unique_tags:
                    unique_tags[child_tag_name] = []
                unique_tags[child_tag_name].append( (path, node_element, child_tag_name) )
                if node_element not in child_by_node:
                    child_by_node[node_element] = {}
                if child_tag_name not in child_by_node[node_element]:
                    child_by_node[node_element][child_tag_name] = []
                child_by_node[node_element][child_tag_name].append( (path, node_element, child_tag_name) )
            sorted_tag_names = unique_tags.keys()
            sorted_tag_names.sort()
##            for tag_name in sorted_tag_names:
##                print 'Node "%s" has child node with tag "%s"' % (
##                    target_node_name, tag_name)
            for tag_name in sorted_tag_names:
                occurrences = unique_tags[tag_name]
                occurrences_by_children_count = {}
                for node, children_by_tag_name in child_by_node.iteritems():
                    if tag_name not in children_by_tag_name:
                        count = 0
                    else:
                        count = len(children_by_tag_name[tag_name])
                    if count not in occurrences_by_children_count:
                        occurrences_by_children_count[count] = 0
                    occurrences_by_children_count[count] = occurrences_by_children_count.get(count, 0) + 1
                is_optional = 0 in occurrences_by_children_count
                has_one = 1 in occurrences_by_children_count
                is_fixed_count = len(occurrences_by_children_count) == 1
                has_many = len( [count for count in occurrences_by_children_count if count > 1] )
##                if is_fixed_count:
##                    print 'Node "%s" always have %d occurrences of child tag "%s"' % (
##                        target_node_name, occurrences_by_children_count.keys()[0], tag_name )
##                elif is_optional and has_one and not has_many:
##                    print 'Node "%s" always have 0 or 1 occurrences of child tag "%s"' % (
##                        target_node_name, tag_name )
##                elif has_many:
                min_occurrences = min(occurrences_by_children_count)
                max_occurrences = max(occurrences_by_children_count)
                print 'Node "%s" have [%d-%d] occurrences of child tag "%s"' % (
                    target_node_name, min_occurrences, max_occurrences, tag_name )
            print '%d child tags found for node "%s"' % (len(sorted_tag_names), target_node_name)
                    
        listAllAttributes( occurrences )
        listAllChildNodeTags( occurrences )
    return True

if __name__ == '__main__':
    succeed = main()
    if not succeed:
        print 'Failed'
        sys.exit( 2 )

