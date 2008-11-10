"""Describes the structure and constraints of objects used in data file of WOG."""
from metaworld import *

# Declares all file types

GLOBAL_RESOURCE_FILE = describe_file( 'global.resources' )
GLOBAL_FX_FILE = describe_file( 'global.fx' )
GLOBAL_MATERIALS_FILE = describe_file( 'global.materials' )
GLOBAL_TEXT_FILE = describe_file( 'global.text' )

ISLAND_FILE = describe_file( 'island' )

LEVEL_GAME_FILE = describe_file( 'level.game' )
LEVEL_RESOURCE_FILE = describe_file( 'level.resource' )
LEVEL_SCENE_FILE = describe_file( 'level.scene' )

# Declares the scope hierarchy
LEVEL_SCOPE = describe_scope( 'global.level', files_desc = [
    LEVEL_GAME_FILE,
    LEVEL_SCENE_FILE,
    LEVEL_RESOURCE_FILE
    ] )
ISLAND_SCOPE = describe_scope( 'global.island', files_desc = [
    ISLAND_FILE
    ] )
GLOBAL_SCOPE = describe_scope( 'global',
                               child_scopes = [ ISLAND_SCOPE, LEVEL_SCOPE ],
                               files_desc = [
    GLOBAL_RESOURCE_FILE,
    GLOBAL_FX_FILE,
    GLOBAL_MATERIALS_FILE,
    GLOBAL_TEXT_FILE
    ] )

LEVEL_GAME_FILE.add_objects( [
    describe_object( 'level', attributes = [
        int_attribute( 'ballsrequired', default = 0, allow_empty = True, mandatory = True, min_value = 0 ),
        bool_attribute( 'letterboxed', init = False, mandatory = True ),
        bool_attribute( 'visualdebug', init = False, mandatory = True ),
        bool_attribute( 'autobounds', init = True, mandatory = True ),
        rgb_attribute( 'textcolor', init = (255,255,255), mandatory = True ),
        real_attribute( 'timebugprobability', init = 0, min_value = 0, mandatory = True ),
        bool_attribute( 'strandgeom', default = False ),
        bool_attribute( 'allowskip', default = True, allow_empty = True ),
        bool_attribute( 'texteffects', default = False ),
        rgb_attribute( 'cursor1color', default = (255,255,255) ),
        rgb_attribute( 'cursor2color', default = (255,255,255) ),
        rgb_attribute( 'cursor3color', default = (255,255,255) ),
        rgb_attribute( 'cursor4color', default = (255,255,255) ),
        ] ),
    describe_object( 'camera', attributes = [
        enum_attribute( 'aspect', values = ('widescreen', 'normal'), default = 'normal' ),
        xy_attribute( 'endpos' ),
        real_attribute( 'endzoom', min_value = 0.00001 ),
        ] ),
    describe_object( 'poi', attributes = [
        real_attribute( 'pause', min_value = 0, init = 0 ),
        xy_attribute( 'pos', init = (0,0) ),
        real_attribute( 'traveltime', min_value = 0, init = 0 ),
        real_attribute( 'zoom', min_value = 0.00001, init = 0.408 )
        ] ),
    describe_object( 'signpost', attributes = [
        real_attribute( 'alpha', min_value = 0, max_value = 1, init = 1, mandatory = True ),
        rgb_attribute( 'colorize', init = (255,255,255), mandatory = True ),
        real_attribute( 'depth', init = 0, mandatory = True ),
        string_attribute( 'name', init = 'SIGN_POST_', mandatory = 'True' ),
        # @todo makes x,y a composite attribute
        real_attribute( 'x', init = 0, mandatory = True ),
        real_attribute( 'y', init = 0, mandatory = True ),
        angle_degrees_attribute( 'rotation', init = 0, mandatory = True ),
        # @todo makes scalex,scaley a composite attribute
        real_attribute( 'scalex', init = 1, min_value = 0.0000001, mandatory = True ),
        real_attribute( 'scaley', init = 1, min_value = 0.0000001, mandatory = True ),
        reference_attribute( 'text', reference_familly = 'text', reference_scope = LEVEL_SCOPE, init = '', mandatory = True ),
        reference_attribute( 'particles', reference_familly = 'effect', reference_scope = GLOBAL_SCOPE )
        ] ),
    describe_object( 'pipe', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'pipe',
                              reference_scope = LEVEL_SCOPE, init ='exitPipe' ),
        real_attribute( 'depth', init = 0, mandatory = True ),
        enum_attribute( 'type', values = ('', 'BEAUTY', 'BLACK', 'ISH'), init = '', mandatory = True )
        ] ),
    describe_object( 'Vertex', attributes = [   # @todo restrict parent tag
        # @todo makes x,y a composite attribute
        real_attribute( 'x', init = 0, mandatory = True ),
        real_attribute( 'y', init = 0, mandatory = True ),
        ] ),
    describe_object( 'BallInstance', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'BallInstance',
                              reference_scope = LEVEL_SCOPE, init ='1' ),
        string_attribute( 'type', mandatory = True, init = 'common' ),  # @todo makes this a reference
        # @todo makes x,y a composite attribute
        real_attribute( 'x', init = 0, mandatory = True ),
        real_attribute( 'y', init = 0, mandatory = True ),
        angle_degrees_attribute( 'angle', init = 0, mandatory = True ),
        real_attribute( 'depth', init = 0, mandatory = True ),
        bool_attribute( 'discovered', init = 'true', mandatory = True )
        ] ),
    describe_object( 'Strand', attributes = [
        reference_attribute( 'gb1', reference_familly = 'BallInstance', reference_scope = LEVEL_SCOPE,
                             init = '', mandatory = True ),
        reference_attribute( 'gb2', reference_familly = 'BallInstance', reference_scope = LEVEL_SCOPE,
                             init = '', mandatory = True )
        ] ),
    describe_object( 'music', attributes = [
        reference_attribute( 'id', reference_familly = 'sound', reference_scope = LEVEL_SCOPE, mandatory = True )
        ] ),
    describe_object( 'loopsound', attributes = [
        reference_attribute( 'id', reference_familly = 'sound', reference_scope = LEVEL_SCOPE, mandatory = True )
        ] ),
    describe_object( 'levelexit', attributes = [
        string_attribute( 'id', mandatory = True, init = 'theExit' ),
        string_attribute( 'filter', mandatory = True, init = '' ),  # @todo revisit 0..1 occ of enum occurrence
        xy_attribute( 'pos', mandatory = True, init = '0,0' ),
        real_attribute( 'radius', mandatory = True, init = '75' )
        ] ),
    describe_object( 'endoncollision', attributes = [
        reference_attribute( 'id1', reference_familly = 'geometry', reference_scope = LEVEL_SCOPE, mandatory = True ),
        reference_attribute( 'id2', reference_familly = 'geometry', reference_scope = LEVEL_SCOPE, mandatory = True ),
        real_attribute( 'delay', mandatory = True, init = '1' )
        ] ),
    describe_object( 'endonmessage', attributes = [
        string_attribute( 'id', mandatory = True )  # values seems to be hard-coded
        ] ),
    describe_object( 'fire', attributes = [
        real_attribute( 'x', mandatory = True, init = '0' ),
        real_attribute( 'y', mandatory = True, init = '0' ),
        real_attribute( 'radius', mandatory = True, init = '50' ),
        real_attribute( 'depth', mandatory = True, init = '0' ),
        reference_attribute( 'particles', reference_familly = 'effect',
                             reference_scope = GLOBAL_SCOPE, mandatory = True )
        ] ),
    describe_object( 'targetheight', attributes = [
        real_attribute( 'y', mandatory = True, init = '300' )
        ] )
    ] )



LEVEL_RESOURCE_FILE.add_objects( [
    # DUPLICATED FROM GLOBAL SCOPE => makes FACTORY function ?
    describe_object( 'ResourceManifest', attributes = [] ), 
    describe_object( 'Resources', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'resources',
                                  reference_scope = LEVEL_SCOPE ),
            ] ),
    describe_object( 'Image', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'image',
                                  reference_scope = LEVEL_SCOPE ),
            path_attribute( 'path', strip_extension = '.png', mandatory = True )
            ] ),
    describe_object( 'Sound', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'sound',
                                  reference_scope = LEVEL_SCOPE ),
            path_attribute( 'path', strip_extension = '.ogg', mandatory = True )
            ] ),
    describe_object( 'font', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'sound',
                                  reference_scope = LEVEL_SCOPE ),
            path_attribute( 'path', strip_extension = '.png', mandatory = True ) # @todo also check existence of .txt
            ] )
    ] )



LEVEL_SCENE_FILE.add_objects( [
    describe_object( 'scene', attributes = [
        rgb_attribute( 'backgroundcolor', mandatory = True, init = '0,0,0' ),
        real_attribute( 'minx', init='-500' ),
        real_attribute( 'miny', init='-500' ),
        real_attribute( 'maxx', init='500' ),
        real_attribute( 'maxy', init='500' )
        ] ),
    describe_object( 'SceneLayer', attributes = [
        real_attribute( 'x', mandatory = True, init='0' ),
        real_attribute( 'y', mandatory = True, init='0' ),
        real_attribute( 'depth', mandatory = True, init='0' ),
        reference_attribute( 'image', reference_familly = 'image', reference_scope = LEVEL_SCOPE,
                             init = '', mandatory = True ),
        real_attribute( 'alpha', min_value = 0, max_value = 1, default = '1' ),
        string_attribute( 'anim' ),     # @todo where is that defined ???
        real_attribute( 'animdelay', min_value = 0.0001, default = '1' ),
        real_attribute( 'animspeed' ),
        angle_degrees_attribute( 'rotation', default = '0' ),
        string_attribute( 'name' ),
        enum_attribute( 'context', ('screen',) ),
        real_attribute( 'scalex', default='1'),
        real_attribute( 'scaley', default='1'),
        bool_attribute( 'tilex', default='false'),
        bool_attribute( 'tiley', default='false')
        ] ),
    describe_object( 'button', attributes = [
        string_attribute( 'id', mandatory = True ),
        real_attribute( 'x', mandatory = True, init = '0' ),
        real_attribute( 'y', mandatory = True, init = '0' ),
        real_attribute( 'depth', mandatory = True, init = '10' ),
        real_attribute( 'alpha', mandatory = True, init = '1' ),
        real_attribute( 'rotation', mandatory = True, init = '0' ),
        real_attribute( 'scalex', mandatory = True, init = '1' ),
        real_attribute( 'scaley', mandatory = True, init = '1' ),
        rgb_attribute( 'colorize', mandatory = True, init = '255,255,255' ),
        reference_attribute( 'up', reference_familly = 'image', reference_scope = LEVEL_SCOPE,
                             init = '', mandatory = True ),
        reference_attribute( 'over', reference_familly = 'image', reference_scope = LEVEL_SCOPE,
                             init = '', mandatory = True ),
        string_attribute( 'context' ),
        reference_attribute( 'disabled', reference_familly = 'image', reference_scope = LEVEL_SCOPE ),
        reference_attribute( 'font', reference_familly = 'font', reference_scope = GLOBAL_SCOPE ),
        string_attribute( 'onclick' ),
        string_attribute( 'onmouseenter' ),
        string_attribute( 'onmouseexit' ),
        bool_attribute( 'overlay' ),
        bool_attribute( 'screenspace' ),
        reference_attribute( 'text', reference_familly = 'text', reference_scope = GLOBAL_SCOPE ),
        argb_attribute( 'textcolorup' ),
        argb_attribute( 'textcolorupover' ),
        reference_attribute( 'tooltip', reference_familly = 'text', reference_scope = GLOBAL_SCOPE )
        ] ),
    describe_object( 'buttongroup', attributes = [
        string_attribute( 'id', mandatory = True ),
        xy_attribute( 'osx', mandatory = True )
        ] ),
    describe_object( 'label', attributes = [
        string_attribute( 'id', mandatory = True ),
        real_attribute( 'x', mandatory = True, init = '0' ),
        real_attribute( 'y', mandatory = True, init = '0' ),
        reference_attribute( 'text', reference_familly = 'text', reference_scope = GLOBAL_SCOPE ),
        angle_radians_attribute( 'rotation', mandatory = True, init = '0' ),
        real_attribute( 'scale', mandatory = True, init = '1' ),
        string_attribute( 'font', mandatory = True ),
        enum_attribute( 'align', ('right', 'center', 'left'), mandatory = True, init = 'center' ),
        real_attribute( 'depth', mandatory = True, init = '10' ),
        bool_attribute( 'overlay', mandatory = True, init = 'false' ),
        bool_attribute( 'screenspace', mandatory = True, init = 'false' )
        ] ),
    describe_object( 'rectangle', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'geometry', reference_scope = LEVEL_SCOPE ),
        real_attribute( 'x', mandatory = True, init = '0' ),
        real_attribute( 'y', mandatory = True, init = '0' ),
        angle_radians_attribute( 'rotation', mandatory = True, init = '0' ),
        real_attribute( 'width', mandatory = True, init = '100' ),
        real_attribute( 'height', mandatory = True, init = '100' ),
        bool_attribute( 'contacts' ),
        reference_attribute( 'image', reference_familly = 'image', reference_scope = LEVEL_SCOPE,
                             init = '' ),
        xy_attribute( 'imagepos' ),
        angle_radians_attribute( 'imagerot' ),
        xy_attribute( 'imagescale' ),
        real_attribute( 'rotspeed' ),
        bool_attribute( 'static', default = 'false', init = 'true' ), # Notes: if static = false, then mass is required.
        real_attribute( 'mass' ),
        reference_attribute( 'material', reference_familly = 'material', reference_scope = GLOBAL_SCOPE,
                             init = '' ),
        string_attribute( 'tag' )
        ] ),
    describe_object( 'circle', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'geometry', reference_scope = LEVEL_SCOPE ),
        real_attribute( 'x', mandatory = True, init = '0' ),
        real_attribute( 'y', mandatory = True, init = '0' ),
        real_attribute( 'radius', mandatory = True, init = '75' ),
        reference_attribute( 'image', reference_familly = 'image', reference_scope = LEVEL_SCOPE,
                             init = '' ),
        xy_attribute( 'imagepos' ),
        angle_radians_attribute( 'imagerot' ),
        xy_attribute( 'imagescale' ),
        real_attribute( 'rotspeed' ),
        bool_attribute( 'static', default = 'false', init = 'true' ), # Notes: if static = false, then mass is required.
        string_attribute( 'tag' ),
        bool_attribute( 'contacts' ),
        real_attribute( 'mass' ),
        reference_attribute( 'material', reference_familly = 'material', reference_scope = GLOBAL_SCOPE,
                             init = '' ),
        bool_attribute( 'nogeomcollisions' )
        ] ),
    describe_object( 'compositegeom', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'geometry', reference_scope = LEVEL_SCOPE ),
        real_attribute( 'x', mandatory = True, init = '0' ),
        real_attribute( 'y', mandatory = True, init = '0' ),
        angle_radians_attribute( 'rotation', mandatory = True, init = '0' ),
        reference_attribute( 'material', reference_familly = 'material', reference_scope = GLOBAL_SCOPE,
                             init = '', mandatory = True ),
        bool_attribute( 'static', mandatory = True, init = 'true' ),
        string_attribute( 'tag' ),
        reference_attribute( 'image', reference_familly = 'image', reference_scope = LEVEL_SCOPE ),
        xy_attribute( 'imagepos', default = '0,0' ),
        angle_radians_attribute( 'imagerot' ),
        xy_attribute( 'imagescale' ),
        real_attribute( 'rotspeed' ),
        bool_attribute( 'nogeomcollisions' )
        ] ),
    describe_object( 'line', attributes = [
        string_attribute( 'id', mandatory = True ),
        xy_attribute( 'anchor', mandatory = True, init = '0,0' ),
        xy_attribute( 'normal', mandatory = True, init = '10,0' ),
        reference_attribute( 'material', reference_familly = 'material', reference_scope = GLOBAL_SCOPE,
                             init = '', mandatory = True ),
        bool_attribute( 'static', init = 'true', mandatory = True ),
        string_attribute( 'tag' )
        ] ),
    describe_object( 'linearforcefield', attributes = [
        string_attribute( 'id', mandatory = True ),
        xy_attribute( 'force', mandatory = True, init = '0,-10' ),
        real_attribute( 'dampeningfactor', mandatory = True, init = '0' ),
        bool_attribute( 'antigrav', mandatory = True, init = 'false' ),
        enum_attribute( 'type', ('force', 'gravity'), init = 'gravity', mandatory = True ),
        xy_attribute( 'center', init = '0,0' ),
        real_attribute( 'width' ),
        real_attribute( 'height' ),
        real_attribute( 'depth' ),
        argb_attribute( 'color' ),
        bool_attribute( 'enabled' ),
        bool_attribute( 'geomonly' )
        ] ),
    describe_object( 'radialforcefield', attributes = [
        string_attribute( 'id', mandatory = True ),
        real_attribute( 'forceatcenter', mandatory = True, init = '10,0' ),
        real_attribute( 'forceatedge', mandatory = True, init = '0,0' ),
        real_attribute( 'dampeningfactor', mandatory = True, init = '0' ),
        bool_attribute( 'antigrav', mandatory = True, init = 'false' ),
        enum_attribute( 'type', ('force', 'gravity'), init = 'gravity', mandatory = True ), # @todo in game, only gravity
        xy_attribute( 'center', mandatory = True, init = '0,0' ),
        real_attribute( 'radius', mandatory = True, init = '100' ),
        real_attribute( 'depth' ),
        bool_attribute( 'enabled' ),
        bool_attribute( 'geomonly' )
        ] ),
    describe_object( 'hinge', attributes = [
        xy_attribute( 'anchor', mandatory = True ),
        reference_attribute( 'body1', reference_familly = 'geometry', reference_scope = LEVEL_SCOPE, mandatory = True ),
        reference_attribute( 'body2', reference_familly = 'geometry', reference_scope = LEVEL_SCOPE, mandatory = True ),
        real_attribute( 'bounce' )
        ] ),
    describe_object( 'motor', attributes = [
        reference_attribute( 'body', reference_familly = 'geometry', reference_scope = LEVEL_SCOPE, mandatory = True ),
        real_attribute( 'maxforce', mandatory = True, init = '20' ),
        real_attribute( 'speed', mandatory = True, init = '-0.01' )
        ] ),
    describe_object( 'particles', attributes = [
        real_attribute( 'depth', mandatory = True, init = '-20' ),
        reference_attribute( 'effect', reference_familly = 'effect', reference_scope = GLOBAL_SCOPE, mandatory = True ),
        xy_attribute( 'pos' ),
        real_attribute( 'pretick', default = '0' )
        ] )
    ] )


GLOBAL_TEXT_FILE.add_objects( [
    describe_object( 'strings', attributes = [] ),
    describe_object( 'string', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'text',
                                  reference_scope = GLOBAL_SCOPE ),
            string_attribute( 'text', mandatory = True ),  
            string_attribute( 'de' ),  
            string_attribute( 'es' ),  
            string_attribute( 'fr' ),  
            string_attribute( 'it' ),  
            string_attribute( 'nl' ),  
            string_attribute( 'pt' )
            ] )
    ] )



GLOBAL_RESOURCE_FILE.add_objects( [
    describe_object( 'ResourceManifest', attributes = [] ),
    describe_object( 'Resources', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'resources',
                                  reference_scope = GLOBAL_SCOPE ),
            ] ),
    describe_object( 'Image', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'image',
                                  reference_scope = GLOBAL_SCOPE ),
            path_attribute( 'path', strip_extension = '.png', mandatory = True )
            ] ),
        # hide object SetDefaults, this is not usable by automated tools
    describe_object( 'Sound', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'sound',
                                  reference_scope = GLOBAL_SCOPE ),
            path_attribute( 'path', strip_extension = '.ogg', mandatory = True )
            ] ),
    describe_object( 'font', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_familly = 'font',
                                  reference_scope = GLOBAL_SCOPE ),
            path_attribute( 'path', strip_extension = '.png', mandatory = True ) # @todo also check existence of .txt
            ] )
    ] )


    
GLOBAL_FX_FILE.add_objects( [
    describe_object( 'effects', attributes = [] ),
    describe_object( 'ambientparticleeffect', attributes = [
            identifier_attribute( 'name', mandatory = True, reference_familly = 'effect',
                                  reference_scope = GLOBAL_SCOPE ),
            int_attribute( 'maxparticles', min_value = 1, mandatory = True, init = '1' ),
            int_attribute( 'margin' ) # ???
            ] ),
    describe_object( 'particleeffect', attributes = [
            identifier_attribute( 'name', mandatory = True, reference_familly = 'effect',
                                  reference_scope = GLOBAL_SCOPE ),
            int_attribute( 'maxparticles', min_value = 1, mandatory = True, init = '1' ),
            real_attribute( 'rate', min_value = 0.00001 ),
            int_attribute( 'margin' ) # ???
            ] ),
    describe_object( 'particle', attributes = [
        xy_attribute( 'acceleration', mandatory = True, init = '0,0.1' ),
        bool_attribute( 'directed', mandatory = True, init = 'false' ),
        reference_attribute( 'image', reference_familly = 'image', reference_scope = GLOBAL_SCOPE,
                             mandatory = True ),
        angle_degrees_attribute( 'movedir', mandatory = True, init = '0' ),
        angle_degrees_attribute( 'movedirvar', mandatory = True, init = '0' ), # ?
        xy_attribute( 'scale', mandatory = True, init = '1,1' ), # @todo scale attribute ?  
        xy_attribute( 'speed', mandatory = True, init = '1,1' ), # @todo direction attribute ?  
        bool_attribute( 'additive' ),
        real_attribute( 'dampening', min_value = 0, max_value = '1' ),
        bool_attribute( 'fade' ),
        real_attribute( 'finalscale', min_value = 0 ),
        xy_attribute( 'lifespan' ), # @todo TYPE OPTIONAL INTERVAL (e.g. 1 or 1,2 are ok)?
        xy_attribute( 'rotation' ), # @todo TYPE OPTIONAL INTERVAL (e.g. 1 or 1,2 are ok)?
        xy_attribute( 'rotspeed' ) # @todo TYPE OPTIONAL INTERVAL (e.g. 1 or 1,2 are ok)?
        ] )
    ] )



GLOBAL_MATERIALS_FILE.add_objects( [
    describe_object( 'materials', attributes = [] ),
    describe_object( 'material', attributes = [
        identifier_attribute( 'id', mandatory = True, reference_familly = 'material',
                              reference_scope = GLOBAL_SCOPE ),
        real_attribute( 'bounce', min_value = 0, mandatory = True, init = '0' ),
        real_attribute( 'friction', min_value = 0, mandatory = True, init = '0' ),
        real_attribute( 'minbouncevel', min_value = 0, mandatory = True, init = '100' ),
        real_attribute( 'stickiness', min_value = 0 )
        ] )
    ] )

LEVEL_GAME_TEMPLATE = """\
<level ballsrequired="1" letterboxed="false" visualdebug="false" autobounds="true" textcolor="255,255,255" timebugprobability="0" strandgeom="false" allowskip="true" >

	<!-- Camera -->
	<camera aspect="normal" endpos="0,0" endzoom="1">
		<poi pos="0,0" traveltime="0" pause="0" zoom="1" />
	</camera>
	<camera aspect="widescreen" endpos="0,0" endzoom="1.273">
		<poi pos="0,0" traveltime="0" pause="0" zoom="1.273" />
	</camera>

	<!-- Level Exit -->
	<levelexit id="theExit" pos="0,0" radius="75" filter="" >
	</levelexit>

</level>
"""

LEVEL_SCENE_TEMPLATE = """\
<scene minx="-500" miny="0" maxx="500" maxy="1000" backgroundcolor="0,0,0" >
	<linearforcefield type="gravity" force="0,-10" dampeningfactor="0" antigrav="true" geomonly="false" />

	<line id="" static="true" tag="detaching" material="rock" anchor="500,300" normal="-1,0" />
	<line id="" static="true" tag="detaching" material="rock" anchor="-500,300" normal="1,0" />
	<line id="" static="true" material="rock" anchor="0,20" normal="0,1" />
</scene>"""

LEVEL_RESOURCE_TEMPLATE = """\
<ResourceManifest>
	<Resources id="scene_NewTemplate" >
		<SetDefaults path="./" idprefix="" />
	</Resources>
</ResourceManifest>
"""
