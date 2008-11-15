"""Describes the structure and constraints of objects used in data file of WOG."""
from metaworld import *

# Declares all file types

TREE_GLOBAL_FX = describe_tree( 'global.fx' )
TREE_GLOBAL_MATERIALS = describe_tree( 'global.materials' )
TREE_GLOBAL_RESOURCE = describe_tree( 'global.resources' )
TREE_GLOBAL_TEXT = describe_tree( 'global.text' )

TREE_ISLAND = describe_tree( 'island' )

TREE_BALL_MAIN = describe_tree( 'ball.main' )
TREE_BALL_RESOURCE = describe_tree( 'ball.resource' )

TREE_LEVEL_GAME = describe_tree( 'level.game' )
TREE_LEVEL_SCENE = describe_tree( 'level.scene' )
TREE_LEVEL_RESOURCE = describe_tree( 'level.resource' )

# Declares the world hierarchy
WORLD_LEVEL = describe_world( 'global.level', trees_meta = [
    TREE_LEVEL_GAME,
    TREE_LEVEL_SCENE,
    TREE_LEVEL_RESOURCE
    ] )
WORLD_ISLAND = describe_world( 'global.island', trees_meta = [
    TREE_ISLAND
    ] )
WORLD_BALL = describe_world( 'global.ball', trees_meta = [
    TREE_BALL_MAIN,
    TREE_BALL_RESOURCE
    ] )
WORLD_GLOBAL = describe_world( 'global',
                               child_worlds = [ WORLD_ISLAND, WORLD_LEVEL, WORLD_BALL ],
                               trees_meta = [
    TREE_GLOBAL_RESOURCE,
    TREE_GLOBAL_FX,
    TREE_GLOBAL_MATERIALS,
    TREE_GLOBAL_TEXT
    ] )


TREE_LEVEL_GAME.add_objects( [
    describe_element( 'level', exact_occurrence = 1, attributes = [
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
        ],
        objects = [
        describe_element( 'camera', exact_occurrence = 2, attributes = [
            enum_attribute( 'aspect', values = ('widescreen', 'normal'), default = 'normal' ),
            xy_attribute( 'endpos' ),
            real_attribute( 'endzoom', min_value = 0.00001 ),
            ], objects = [
            describe_element( 'poi', min_occurrence = 1, attributes = [
                real_attribute( 'pause', min_value = 0, init = 0 ),
                xy_attribute( 'pos', init = (0,0) ),
                real_attribute( 'traveltime', min_value = 0, init = 0 ),
                real_attribute( 'zoom', min_value = 0.00001, init = 0.408 )
                ] )
            ] ),
        describe_element( 'signpost', attributes = [
            real_attribute( 'alpha', min_value = 0, max_value = 1, init = 1, mandatory = True ),
            rgb_attribute( 'colorize', init = (255,255,255), mandatory = True ),
            real_attribute( 'depth', init = 0, mandatory = True ),
            string_attribute( 'name', init = 'SIGN_POST_', mandatory = 'True' ),
            # @todo makes x,y a composite attribute
            real_attribute( 'x', init = 0, mandatory = True ),
            real_attribute( 'y', init = 0, mandatory = True ),
            angle_degrees_attribute( 'rotation', init = 0, mandatory = True ),
            reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL,
                                 init = '', mandatory = True ),
            # @todo makes scalex,scaley a composite attribute
            real_attribute( 'scalex', init = 1, min_value = 0.0000001, mandatory = True ),
            real_attribute( 'scaley', init = 1, min_value = 0.0000001, mandatory = True ),
            reference_attribute( 'text', reference_family = 'text', reference_world = WORLD_LEVEL, init = '', mandatory = True ),
            reference_attribute( 'particles', reference_family = 'effect', reference_world = WORLD_GLOBAL )
            ] ),
        describe_element( 'pipe', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'pipe',
                                  reference_world = WORLD_LEVEL, init ='exitPipe' ),
            real_attribute( 'depth', init = 0, mandatory = True ),
            enum_attribute( 'type', values = ('BEAUTY', 'BLACK', 'ISH') )
            ],
            objects = [
            describe_element( 'Vertex', min_occurrence = 2, attributes = [
                # @todo makes x,y a composite attribute
                real_attribute( 'x', init = 0, mandatory = True ),
                real_attribute( 'y', init = 0, mandatory = True ),
                ] ),
            ] ),
        describe_element( 'BallInstance', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'BallInstance',
                                  reference_world = WORLD_LEVEL, init ='1' ),
            reference_attribute( 'type', mandatory = True,
                                 reference_family = 'ball', reference_world = WORLD_GLOBAL ),
            # @todo makes x,y a composite attribute
            real_attribute( 'x', init = 0, mandatory = True ),
            real_attribute( 'y', init = 0, mandatory = True ),
            angle_degrees_attribute( 'angle', init = 0, mandatory = True ),
            real_attribute( 'depth', init = 0, mandatory = True ),
            bool_attribute( 'discovered', init = 'true', mandatory = True )
            ] ),
        describe_element( 'Strand', attributes = [
            reference_attribute( 'gb1', reference_family = 'BallInstance', reference_world = WORLD_LEVEL,
                                 init = '', mandatory = True ),
            reference_attribute( 'gb2', reference_family = 'BallInstance', reference_world = WORLD_LEVEL,
                                 init = '', mandatory = True )
            ] ),
        describe_element( 'music', attributes = [
            reference_attribute( 'id', reference_family = 'sound', reference_world = WORLD_LEVEL, mandatory = True )
            ] ),
        describe_element( 'loopsound', attributes = [
            reference_attribute( 'id', reference_family = 'sound', reference_world = WORLD_LEVEL, mandatory = True )
            ] ),
        describe_element( 'levelexit', attributes = [
            string_attribute( 'id', mandatory = True, init = 'theExit' ),
            string_attribute( 'filter', mandatory = True, init = '' ),  # @todo revisit 0..1 occ of enum occurrence
            xy_attribute( 'pos', mandatory = True, init = '0,0' ),
            real_attribute( 'radius', mandatory = True, init = '75' )
            ] ),
        describe_element( 'endoncollision', attributes = [
            reference_attribute( 'id1', reference_family = 'geometry', reference_world = WORLD_LEVEL, mandatory = True ),
            reference_attribute( 'id2', reference_family = 'geometry', reference_world = WORLD_LEVEL, mandatory = True ),
            real_attribute( 'delay', mandatory = True, init = '1' )
            ] ),
        describe_element( 'endonmessage', attributes = [
            string_attribute( 'id', mandatory = True )  # values seems to be hard-coded
            ] ),
        describe_element( 'fire', attributes = [
            real_attribute( 'x', mandatory = True, init = '0' ),
            real_attribute( 'y', mandatory = True, init = '0' ),
            real_attribute( 'radius', mandatory = True, init = '50' ),
            real_attribute( 'depth', mandatory = True, init = '0' ),
            reference_attribute( 'particles', reference_family = 'effect',
                                 reference_world = WORLD_GLOBAL, mandatory = True )
            ] ),
        describe_element( 'targetheight', attributes = [
            real_attribute( 'y', mandatory = True, init = '300' )
            ] )
        ] )
    ] )

def _describe_resource_file( tree_meta, resource_world, is_global = False ):
    if is_global:
        resources_object = describe_element( 'Resources', min_occurrence = 1 )
    else:
        resources_object = describe_element( 'Resources', exact_occurrence = 1 )
    resources_object.add_attributes( [
        identifier_attribute( 'id', mandatory = True, reference_family = 'resources',
                              reference_world = resource_world ),
        ] )
    resources_object.add_objects( [
        describe_element( 'Image', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'image',
                                  reference_world = resource_world ),
            path_attribute( 'path', strip_extension = '.png', mandatory = True )
            ] ),
        describe_element( 'Sound', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'sound',
                                  reference_world = resource_world ),
            path_attribute( 'path', strip_extension = '.ogg', mandatory = True )
            ] ),
        describe_element( 'SetDefaults', read_only = True, attributes = [
            string_attribute( 'path', mandatory = True ),
            string_attribute( 'idprefix', mandatory = True )
            ] )
        ] )
    if is_global:
        resources_object.add_objects( [
            describe_element( 'font', attributes = [
                identifier_attribute( 'id', mandatory = True, reference_family = 'font',
                                      reference_world = resource_world ),
                path_attribute( 'path', strip_extension = '.png', mandatory = True ) # @todo also check existence of .txt
                ] )
        ] )
    
    tree_meta.add_objects( [
        # DUPLICATED FROM GLOBAL SCOPE => makes FACTORY function ?
        describe_element( 'ResourceManifest', exact_occurrence = 1, attributes = [], objects = [
            resources_object
            ] )
        ] )

_describe_resource_file( TREE_LEVEL_RESOURCE, WORLD_LEVEL )


ELEMENT_BUTTON = describe_element( 'button', attributes = [
        string_attribute( 'id', mandatory = True ),
        real_attribute( 'x', mandatory = True, init = '0' ),
        real_attribute( 'y', mandatory = True, init = '0' ),
        real_attribute( 'depth', mandatory = True, init = '10' ),
        real_attribute( 'alpha', mandatory = True, init = '1' ),
        real_attribute( 'rotation', mandatory = True, init = '0' ),
        real_attribute( 'scalex', mandatory = True, init = '1' ),
        real_attribute( 'scaley', mandatory = True, init = '1' ),
        rgb_attribute( 'colorize', mandatory = True, init = '255,255,255' ),
        reference_attribute( 'up', reference_family = 'image', reference_world = WORLD_LEVEL,
                             init = '', mandatory = True ),
        reference_attribute( 'over', reference_family = 'image', reference_world = WORLD_LEVEL,
                             init = '', mandatory = True ),
        string_attribute( 'context' ),
        reference_attribute( 'disabled', reference_family = 'image', reference_world = WORLD_LEVEL ),
        reference_attribute( 'font', reference_family = 'font', reference_world = WORLD_GLOBAL ),
        string_attribute( 'onclick' ),
        string_attribute( 'onmouseenter' ),
        string_attribute( 'onmouseexit' ),
        bool_attribute( 'overlay' ),
        bool_attribute( 'screenspace' ),
        reference_attribute( 'text', reference_family = 'text', reference_world = WORLD_GLOBAL ),
        argb_attribute( 'textcolorup' ),
        argb_attribute( 'textcolorupover' ),
        reference_attribute( 'tooltip', reference_family = 'text', reference_world = WORLD_GLOBAL )
        ] )

ELEMENT_RECTANGLE = describe_element( 'rectangle', attributes = [
    identifier_attribute( 'id', mandatory = True, reference_family = 'geometry', reference_world = WORLD_LEVEL ),
    real_attribute( 'x', mandatory = True, init = '0' ),
    real_attribute( 'y', mandatory = True, init = '0' ),
    angle_radians_attribute( 'rotation', mandatory = True, init = '0' ),
    real_attribute( 'width', mandatory = True, init = '100' ),
    real_attribute( 'height', mandatory = True, init = '100' ),
    bool_attribute( 'contacts' ),
    reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL,
                         init = '' ),
    xy_attribute( 'imagepos' ),
    angle_radians_attribute( 'imagerot' ),
    xy_attribute( 'imagescale' ),
    real_attribute( 'rotspeed' ),
    bool_attribute( 'static', default = 'false', init = 'true' ), # Notes: if static = false, then mass is required.
    real_attribute( 'mass' ),
    reference_attribute( 'material', reference_family = 'material', reference_world = WORLD_GLOBAL,
                         init = '' ),
    string_attribute( 'tag' )
    ] )

ELEMENT_CIRCLE = describe_element( 'circle', attributes = [
    identifier_attribute( 'id', mandatory = True, reference_family = 'geometry', reference_world = WORLD_LEVEL ),
    real_attribute( 'x', mandatory = True, init = '0' ),
    real_attribute( 'y', mandatory = True, init = '0' ),
    real_attribute( 'radius', mandatory = True, init = '75' ),
    reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL,
                         init = '' ),
    xy_attribute( 'imagepos' ),
    angle_radians_attribute( 'imagerot' ),
    xy_attribute( 'imagescale' ),
    real_attribute( 'rotspeed' ),
    bool_attribute( 'static', default = 'false', init = 'true' ), # Notes: if static = false, then mass is required.
    string_attribute( 'tag' ),
    bool_attribute( 'contacts' ),
    real_attribute( 'mass' ),
    reference_attribute( 'material', reference_family = 'material', reference_world = WORLD_GLOBAL,
                         init = '' ),
    bool_attribute( 'nogeomcollisions' )
    ] )


TREE_LEVEL_SCENE.add_objects( [
    describe_element( 'scene', exact_occurrence = 1, attributes = [
        rgb_attribute( 'backgroundcolor', mandatory = True, init = '0,0,0' ),
        real_attribute( 'minx', init='-500' ),
        real_attribute( 'miny', init='-500' ),
        real_attribute( 'maxx', init='500' ),
        real_attribute( 'maxy', init='500' )
        ],
        objects = [
        describe_element( 'SceneLayer', attributes = [
            real_attribute( 'x', mandatory = True, init='0' ),
            real_attribute( 'y', mandatory = True, init='0' ),
            real_attribute( 'depth', mandatory = True, init='0' ),
            reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL,
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
            bool_attribute( 'tiley', default='false'),
            rgb_attribute( 'colorize', init = '255,255,255'),
            ] ),
        ELEMENT_BUTTON,
        describe_element( 'buttongroup', attributes = [
            string_attribute( 'id', mandatory = True ),
            xy_attribute( 'osx', mandatory = True )
            ],
            objects = [
                ELEMENT_BUTTON
            ] ),
        describe_element( 'label', attributes = [
            string_attribute( 'id', mandatory = True ),
            real_attribute( 'x', mandatory = True, init = '0' ),
            real_attribute( 'y', mandatory = True, init = '0' ),
            reference_attribute( 'text', reference_family = 'text', reference_world = WORLD_GLOBAL ),
            angle_radians_attribute( 'rotation', mandatory = True, init = '0' ),
            real_attribute( 'scale', mandatory = True, init = '1' ),
            string_attribute( 'font', mandatory = True ),
            enum_attribute( 'align', ('right', 'center', 'left'), mandatory = True, init = 'center' ),
            real_attribute( 'depth', mandatory = True, init = '10' ),
            bool_attribute( 'overlay', mandatory = True, init = 'false' ),
            bool_attribute( 'screenspace', mandatory = True, init = 'false' )
            ] ),
        ELEMENT_RECTANGLE,
        ELEMENT_CIRCLE,
        describe_element( 'compositegeom', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'geometry', reference_world = WORLD_LEVEL ),
            real_attribute( 'x', mandatory = True, init = '0' ),
            real_attribute( 'y', mandatory = True, init = '0' ),
            angle_radians_attribute( 'rotation', mandatory = True, init = '0' ),
            reference_attribute( 'material', reference_family = 'material', reference_world = WORLD_GLOBAL,
                                 init = '', mandatory = True ),
            bool_attribute( 'static', mandatory = True, init = 'true' ),
            string_attribute( 'tag' ),
            reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL ),
            xy_attribute( 'imagepos', default = '0,0' ),
            angle_radians_attribute( 'imagerot' ),
            xy_attribute( 'imagescale' ),
            real_attribute( 'rotspeed' ),
            bool_attribute( 'nogeomcollisions' )
            ],
            objects = [
                ELEMENT_RECTANGLE,
                ELEMENT_CIRCLE
            ] ),
        describe_element( 'line', attributes = [
            string_attribute( 'id', mandatory = True ),
            xy_attribute( 'anchor', mandatory = True, init = '0,0' ),
            xy_attribute( 'normal', mandatory = True, init = '10,0' ),
            reference_attribute( 'material', reference_family = 'material', reference_world = WORLD_GLOBAL,
                                 init = '', mandatory = True ),
            bool_attribute( 'static', init = 'true', mandatory = True ),
            string_attribute( 'tag' )
            ] ),
        describe_element( 'linearforcefield', attributes = [
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
            bool_attribute( 'geomonly' ),
            bool_attribute( 'water', default = 'false' )
            ] ),
        describe_element( 'radialforcefield', attributes = [
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
        describe_element( 'hinge', attributes = [
            xy_attribute( 'anchor', mandatory = True ),
            reference_attribute( 'body1', reference_family = 'geometry', reference_world = WORLD_LEVEL, mandatory = True ),
            reference_attribute( 'body2', reference_family = 'geometry', reference_world = WORLD_LEVEL, mandatory = True ),
            real_attribute( 'bounce' )
            ] ),
        describe_element( 'motor', attributes = [
            reference_attribute( 'body', reference_family = 'geometry', reference_world = WORLD_LEVEL, mandatory = True ),
            real_attribute( 'maxforce', mandatory = True, init = '20' ),
            real_attribute( 'speed', mandatory = True, init = '-0.01' )
            ] ),
        describe_element( 'particles', attributes = [
            real_attribute( 'depth', mandatory = True, init = '-20' ),
            reference_attribute( 'effect', reference_family = 'effect', reference_world = WORLD_GLOBAL, mandatory = True ),
            xy_attribute( 'pos' ),
            real_attribute( 'pretick', default = '0' )
            ] )
        ] )
    ] )


TREE_GLOBAL_TEXT.add_objects( [
    describe_element( 'strings', exact_occurrence = 1, attributes = [], objects = [
        describe_element( 'string', min_occurrence = 1, attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'text',
                                  reference_world = WORLD_GLOBAL ),
            string_attribute( 'text', mandatory = True ),  
            string_attribute( 'de' ),  
            string_attribute( 'es' ),  
            string_attribute( 'fr' ),  
            string_attribute( 'it' ),  
            string_attribute( 'nl' ),  
            string_attribute( 'pt' )
            ] )
        ] )
    ] )



_describe_resource_file( TREE_GLOBAL_RESOURCE, WORLD_GLOBAL, is_global = True )

ELEMENT_PARTICLE = describe_element( 'particle', min_occurrence = 1, attributes = [
    xy_attribute( 'acceleration', mandatory = True, init = '0,0.1' ),
    bool_attribute( 'directed', mandatory = True, init = 'false' ),
    reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_GLOBAL,
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
    ],
    objects = [
        describe_element( 'axialsinoffset', min_occurrence = 1, max_occurrence = 2, attributes = [
            xy_attribute( 'amp', mandatory = True, init = '5,10' ), # @todo just 2 reals (interval)
            enum_attribute( 'axis', ('x','y'), mandatory = True, init = 'x' ),
            xy_attribute( 'freq', mandatory = True, init = '5,10' ),# @todo just 2 reals (interval)
            xy_attribute( 'phaseshift', mandatory = True, init = '0.2,0.4' ),# @todo just 2 reals (interval)
        ] )
    ] )
    
TREE_GLOBAL_FX.add_objects( [
    describe_element( 'effects', exact_occurrence = 1, attributes = [], objects = [
        describe_element( 'ambientparticleeffect', attributes = [
            identifier_attribute( 'name', mandatory = True, reference_family = 'effect',
                                  reference_world = WORLD_GLOBAL ),
            int_attribute( 'maxparticles', min_value = 1, mandatory = True, init = '1' ),
            int_attribute( 'margin' ) # ???
            ],
            objects = [
                ELEMENT_PARTICLE
            ] ),
        describe_element( 'particleeffect', attributes = [
            identifier_attribute( 'name', mandatory = True, reference_family = 'effect',
                                  reference_world = WORLD_GLOBAL ),
            int_attribute( 'maxparticles', min_value = 1, mandatory = True, init = '1' ),
            real_attribute( 'rate', min_value = 0.00001 ),
            int_attribute( 'margin' ) # ???
            ],
            objects = [
                ELEMENT_PARTICLE
            ] )
        ])
    ] )



TREE_GLOBAL_MATERIALS.add_objects( [
    describe_element( 'materials', exact_occurrence = 1, attributes = [], objects = [
        describe_element( 'material', attributes = [
            identifier_attribute( 'id', mandatory = True, reference_family = 'material',
                                  reference_world = WORLD_GLOBAL ),
            real_attribute( 'bounce', min_value = 0, mandatory = True, init = '0' ),
            real_attribute( 'friction', min_value = 0, mandatory = True, init = '0' ),
            real_attribute( 'minbouncevel', min_value = 0, mandatory = True, init = '100' ),
            real_attribute( 'stickiness', min_value = 0 )
            ] )
        ] )
    ] )


_describe_resource_file( TREE_BALL_RESOURCE, WORLD_BALL )

# NOTES: this has been generated from scanxmlfile with -w options. Need a lot of clean up.
TREE_BALL_MAIN.add_objects( [
        describe_element( 'ball', min_occurrence=1, max_occurrence=1, attributes = [
            identifier_attribute( 'name', mandatory = True, reference_family = 'ball',
                                  reference_world = WORLD_GLOBAL ),
            int_attribute( 'mass', min_value=0.00001, mandatory = True, init = '20'),  # [8-600] Median:20 Samples: 20 | 30 | 10 | 60 | 600
            unknown_attribute( 'shape', mandatory = True, init = 'circle,30'),  # Samples: circle,30 | circle,30,0.25 | circle,24,0.1 | circle,50,0 | rectangle,50,50
            real_attribute( 'speedvariance', min_value=0, mandatory = True, init = '0.2'),  # [0.0-0.3] Median:0.2 Samples: 0.2 | 0 | 0.3 | 0.0
            int_attribute( 'strands', min_value=0, mandatory = True, init = '0'),  # [0-4] Median:1 Samples: 0 | 2 | 1 | 4 | 3
            real_attribute( 'walkspeed', min_value=0, mandatory = True, init = '0'),  # [0.0-0.15] Median:0.1 Samples: 0 | 0.1 | 0.0 | 0.05 | 0.15
            real_attribute( 'climbspeed', min_value=0, init = '0'),  # [0.0-2.8] Median:1.0 Samples: 0 | 2.0 | 0.0 | 1.8 | 0.9
            real_attribute( 'towermass', min_value=0, init = '5'),  # [0.0-200.0] Median:5.0 Samples: 5 | 3.0 | 10 | 200 | 20
            unknown_attribute( 'jump', init = '0.0,0.0'),  # Samples: 0.0,0.0 | 0,0 | 0.0,0.3 | 0.4,1.2 | 0.0,0.4
            bool_attribute( 'detachable', init = 'false'),
            bool_attribute( 'draggable', init = 'false'),
            bool_attribute( 'grumpy', init = 'true'),
            bool_attribute( 'invulnerable', init = 'true'),
            unknown_attribute( 'blinkcolor', init = '0,0,0'),  # Samples: 0,0,0 | 0,255,0
            bool_attribute( 'suckable', init = 'false'),
            int_attribute( 'walkforce', min_value=0, init = '0'),  # [0-3000] Median:0 Samples: 0 | 500 | 3000
            bool_attribute( 'autoboundsunattached', init = 'true'),
            bool_attribute( 'hideeyes', init = 'false'),
            real_attribute( 'burntime', min_value=0.00001, init = '2.0'),  # [0.1-7.0] Median:2.0 Samples: 2.0 | 3.0 | 5 | 0.1 | 7.0
            bool_attribute( 'collidewithattached', init = 'true'),
            real_attribute( 'detonateforce', min_value=0, init = '500'),  # [0.0-1000.0] Median:300.0 Samples: 500 | 300 | 0.01 | 0 | 2
            int_attribute( 'detonateradius', min_value=0, init = '100'),  # [0-500] Median:100 Samples: 100 | 200 | 0 | 350 | 10
            bool_attribute( 'climber', init = 'false'),
            bool_attribute( 'collideattached', init = 'true'),
            bool_attribute( 'alwayslookatmouse', init = 'true'),
            unknown_attribute( 'material', init = 'BlockBall'),  # Samples: BlockBall | rock | BoneBall | UglyBall | BeautyBall
            bool_attribute( 'stuckattachment', init = 'false'),
            int_attribute( 'wakedist', min_value=0.00001, init = '30'),  # [30-600] Median:30 Samples: 30 | 200 | 60 | 600
            bool_attribute( 'autobounds', init = 'false'),
            unknown_attribute( 'attenuationdeselect', init = '0, 1'),  # Samples: 0, 1 | 0.05, 1.2, 1.0 | 0.1, 1.1, 1.0
            unknown_attribute( 'attenuationdrag', init = '0, 1'),  # Samples: 0, 1 | 0.05, 1.2, 1.0 | 0.1, 1.1, 1.0
            unknown_attribute( 'attenuationdrop', init = '0, 1'),  # Samples: 0, 1 | 0.05, 1.2, 1.0 | 0.1, 1.1, 1.0
            unknown_attribute( 'attenuationselect', init = '0, 1'),  # Samples: 0, 1 | 0.05, 1.0, 1.2 | 0.1, 1.0, 1.1
            unknown_attribute( 'contains', init = '10,UtilGooGlobber'),  # Samples: 10,UtilGooGlobber | 42,ZBomb | 1,Pilot | 80,UndeletePillFizz | 4,Spam
            real_attribute( 'popduration', min_value=0.00001, init = '0.25'),  # [0.1-4.0] Median:0.25 Samples: 0.25 | 1.0 | 0.1 | 4
            unknown_attribute( 'popparticles', init = 'beautypop'),  # Samples: beautypop | OOS_gooGlobs | ISH_undeleteFizz | ish_bitPop
            unknown_attribute( 'popsound', init = 'SOUND_BALL_BIT_POP1'),  # Samples: SOUND_BALL_BIT_POP1 | SOUND_BALL_ZBOMBMOM_POP | SOUND_BALL_UNDELETEPILLFIZZ_POP4 | SOUND_BALL_UNDELETEPILL_POP | SOUND_BALL_UTILGOOGLOBBERMOM_POP
            unknown_attribute( 'statescales', init = 'tank,0.12'),  # Samples: tank,0.12 | attached,1.25 | attached,1.65, detaching,1.3 | attached,1.75, detaching,1.3, tank,1.0
            real_attribute( 'antigrav', min_value=0.00001, init = '1.0'),  # [0.5-14.0] Median:1.0 Samples: 1.0 | 4.5 | 14 | 0.5 | 3
            unknown_attribute( 'explosionparticles', init = 'BallExplode_ISH'),  # Samples: BallExplode_ISH | BallExplode_Bomb | BallExplode_Fuse
            bool_attribute( 'static', init = 'true'),
            bool_attribute( 'sticky', init = 'false'),
            bool_attribute( 'isbehindstrands', init = 'false'),
            bool_attribute( 'stacking', init = 'true'),
            real_attribute( 'dampening', min_value=0.00001, init = '0.1'),  # [0.005-0.115] Median:0.1 Samples: 0.1 | 0.005 | 0.115
            bool_attribute( 'hingedrag', init = 'true'),
            bool_attribute( 'jumponwakeup', init = 'true'),
            int_attribute( 'maxattachspeed', min_value=0.00001, init = '1000'),  # [1000-1000] Median:1000 Samples: 1000
            bool_attribute( 'staticwhensleeping', init = 'true'),
            bool_attribute( 'autodisable', init = 'true'),
            int_attribute( 'dragmass', min_value=0.00001, init = '100'),  # [40-100] Median:40 Samples: 100 | 40
            bool_attribute( 'isantigravunattached', init = 'true'),
            bool_attribute( 'stickyattached', init = 'true'),
            bool_attribute( 'stickyunattached', init = 'false'),
            unknown_attribute( 'fling', init = '200,2.5'),  # Samples: 200,2.5
            unknown_attribute( 'popdelay', init = '2,12'),  # Samples: 2,12 | 2,2
            unknown_attribute( 'spawn', init = 'WindowRect'),  # Samples: WindowRect | WindowSquare
            bool_attribute( 'autoattach', init = 'true'),
            bool_attribute( 'distantsounds', init = 'false'),
            bool_attribute( 'fallingattachment', init = 'false'),
            bool_attribute( 'flammable', init = 'false'),
        ], objects = [
            describe_element( 'detachstrand', min_occurrence=0, max_occurrence=1, attributes = [
                int_attribute( 'maxlen', min_value=0.00001, mandatory = True, init = '60'),  # [60-160] Median:60 Samples: 60 | 160 | 70
                unknown_attribute( 'image', init = 'IMAGE_BALL_BALLOON_SPLAT1'),  # Samples: IMAGE_BALL_BALLOON_SPLAT1 | IMAGE_BALL_COMMON_BLACK_DSTRAND | IMAGE_BALL_WATER_DSTRAND | IMAGE_BALL_POKEY_DSTRAND | IMAGE_BALL_PILOT_ARROW
            ] ),
            describe_element( 'marker', min_occurrence=0, max_occurrence=1, attributes = [
                unknown_attribute( 'detach', mandatory = True, init = 'IMAGE_BALL_POKEY_DETACHMARKER_P1'),  # Samples: IMAGE_BALL_POKEY_DETACHMARKER_P1 | IMAGE_BALL_COMMON_DRAGMARKER_P1 | IMAGE_BALL_IVY_DETACHMARKER_P1 | IMAGE_BALL_UTILATTACHWALKABLE_DRAGMARKER_P1 | IMAGE_BALL_RECTHEAD_DRAGMARKER
                unknown_attribute( 'drag', mandatory = True, init = 'IMAGE_BALL_COMMON_DRAGMARKER_P1'),  # Samples: IMAGE_BALL_COMMON_DRAGMARKER_P1 | IMAGE_BALL_UTILATTACHWALKABLE_DRAGMARKER_P1 | IMAGE_BALL_DRAINED_DRAGMARKER_P1 | IMAGE_BALL_BOMBSTICKY_DRAGMARKER | IMAGE_BALL_RECTHEAD_DRAGMARKER
                int_attribute( 'rotspeed', mandatory = True, init = '2'),  # [-2-2] Median:2 Samples: 2 | -2 | 0
            ] ),
            describe_element( 'part', min_occurrence=0, max_occurrence=10, attributes = [
                unknown_attribute( 'image', mandatory = True, init = 'IMAGE_BALL_GENERIC_EYE_GLASS_1,IMAGE_BALL_GENERIC_EYE_GLASS_2,IMAGE_BALL_GENERIC_EYE_GLASS_3'),  # Samples: IMAGE_BALL_GENERIC_EYE_GLASS_1,IMAGE_BALL_GENERIC_EYE_GLASS_2,IMAGE_BALL_GENERIC_EYE_GLASS_3 | IMAGE_BALL_GENERIC_EYE_GLASS_1,IMAGE_BALL_GENERIC_EYE_GLASS_2 | IMAGE_BALL_GENERIC_EYE_GLASS_1 | IMAGE_BALL_GENERIC_HILITE2 | IMAGE_BALL_GENERIC_HILITE1
                int_attribute( 'layer', min_value=0, mandatory = True, init = '2'),  # [0-4] Median:1 Samples: 2 | 1 | 0 | 3 | 4
                unknown_attribute( 'name', mandatory = True, init = 'body'),  # Samples: body | lefteye | righteye | lips | hilite1
                real_attribute( 'scale', min_value=0.00001, mandatory = True, init = '0.5'),  # [0.25-1.45] Median:0.71875 Samples: 0.5 | 1 | 0.6 | 0.5390625 | 0.75
                unknown_attribute( 'x', mandatory = True, init = '0'),  # Samples: 0 | -12,-8 | 8,12 | -10,-6 | -5,0
                unknown_attribute( 'y', mandatory = True, init = '0'),  # Samples: 0 | 0,0 | -5,5 | 0,7 | 6,10
                bool_attribute( 'rotate', init = 'true'),
                unknown_attribute( 'state', init = 'attached'),  # Samples: attached | climbing,walking,falling,dragging,detaching,standing,tank | climbing,walking,falling,attached,dragging,detaching,standing,tank,stuck,stuck_attached,stuck_detaching | climbing,walking,falling,dragging,detaching,standing,tank,sleeping,stuck,stuck_attached,stuck_detaching | climbing,walking,falling,dragging,detaching,standing,tank,sleeping,stuck,stuck_attached,stuck_detaching,pipe
                unknown_attribute( 'stretch', init = '16,2,0.5'),  # Samples: 16,2,0.5 | 24,1.2,0.9 | 32,2,0.5 | 24,1.75,0.65 | 12,2,0.5
                bool_attribute( 'eye', init = 'true'),
                unknown_attribute( 'pupil', init = 'IMAGE_BALL_GENERIC_PUPIL1'),  # Samples: IMAGE_BALL_GENERIC_PUPIL1 | IMAGE_BALL_BEAUTY_PUPIL | IMAGE_BALL_UGLY_PUPIL | IMAGE_BALL_BIT_PUPIL | IMAGE_BALL_BEAUTYPRODUCTEYE_PUPIL
                int_attribute( 'pupilinset', min_value=0.00001, init = '13'),  # [10-116] Median:13 Samples: 13 | 12 | 10 | 14 | 50
                unknown_attribute( 'xrange', init = '-18,0'),  # Samples: -18,0 | 0,18 | -20,-10 | 10,20 | -90,-70,
                unknown_attribute( 'yrange', init = '-12,12'),  # Samples: -12,12 | 20,40 | -6,6 | -8,8 | -115,-35
            ] ),
            describe_element( 'particles', min_occurrence=0, max_occurrence=3, attributes = [
                unknown_attribute( 'id', mandatory = True, init = 'sleepyZzz'),  # Samples: sleepyZzz | ish_smallfire | ish_sleepyZzz | poisonBallBurn | fireRobotHead
                bool_attribute( 'overball', mandatory = True, init = 'true'),
                unknown_attribute( 'states', mandatory = True, init = 'sleeping'),  # Samples: sleeping | onfire | falling
            ] ),
            describe_element( 'shadow', min_occurrence=0, max_occurrence=1, attributes = [
                unknown_attribute( 'image', mandatory = True, init = 'IMAGE_BALL_GENERIC_SHADOW0'),  # Samples: IMAGE_BALL_GENERIC_SHADOW0 | IMAGE_BALL_GENERIC_SHADOW1 | IMAGE_BALL_BEAUTY_SHADOW | IMAGE_BALL_COMMON_ALBINO_SHADOWGLOW | IMAGE_BALL_UGLY_SHADOW
                bool_attribute( 'additive', init = 'true'),
            ] ),
            describe_element( 'sinvariance', min_occurrence=0, max_occurrence=7, attributes = [
                real_attribute( 'amp', min_value=0, mandatory = True, init = '0.1'),  # [0.0-1.0] Median:0.1 Samples: 0.1 | 0.02 | 0.03 | 0.5 | 0.05
                real_attribute( 'freq', min_value=0, mandatory = True, init = '1.2'),  # [0.0-2.0] Median:0.8 Samples: 1.2 | 0.3 | 1.5 | 0.4 | 0.8
                real_attribute( 'shift', min_value=0, mandatory = True, init = '0.0'),  # [0.0-0.8] Median:0.0 Samples: 0.0 | 0 | 0.5 | 0.8
            ], objects = [
                describe_element( 'sinanim', min_occurrence=1, max_occurrence=8, attributes = [
                    real_attribute( 'amp', mandatory = True, init = '0.1'),  # [-3.0-12.0] Median:0.1 Samples: 0.1 | 2 | 0.5 | 0.2 | 0.06
                    unknown_attribute( 'axis', mandatory = True, init = 'y'),  # Samples: y | x
                    real_attribute( 'freq', min_value=0.00001, mandatory = True, init = '2.0'),  # [0.2-22.0] Median:2.0 Samples: 2.0 | 1.0 | 0.25 | .20 | 1.2
                    unknown_attribute( 'part', mandatory = True, init = 'body'),  # Samples: body | lefteye | righteye | lefteye,righteye | body,shine
                    real_attribute( 'shift', min_value=0, mandatory = True, init = '0'),  # [0.0-0.8] Median:0.0 Samples: 0 | 0.5 | 0.33 | 0.1 | 0.66
                    unknown_attribute( 'state', mandatory = True, init = 'walking'),  # Samples: walking | climbing | falling | dragging | attached
                    unknown_attribute( 'type', mandatory = True, init = 'scale'),  # Samples: scale | translate
                ] ),
            ] ),
            describe_element( 'sound', min_occurrence=0, max_occurrence=28, attributes = [
                unknown_attribute( 'event', mandatory = True, init = 'death'),  # Samples: death | land | bounce | pickup | marker
                unknown_attribute( 'id', mandatory = True, allow_empty = True, init = 'SOUND_BALL_GENERIC_STICK1,SOUND_BALL_GENERIC_STICK2,SOUND_BALL_GENERIC_STICK3,SOUND_BALL_GENERIC_STICK4,SOUND_BALL_GENERIC_STICK5,SOUND_BALL_GENERIC_STICK6'),  # Samples: SOUND_BALL_GENERIC_STICK1,SOUND_BALL_GENERIC_STICK2,SOUND_BALL_GENERIC_STICK3,SOUND_BALL_GENERIC_STICK4,SOUND_BALL_GENERIC_STICK5,SOUND_BALL_GENERIC_STICK6 | SOUND_BALL_GENERIC_MUMBLE1,SOUND_BALL_GENERIC_MUMBLE2,SOUND_BALL_GENERIC_MUMBLE3,SOUND_BALL_GENERIC_MUMBLE4,SOUND_BALL_GENERIC_MUMBLE5,SOUND_BALL_GENERIC_MUMBLE6,SOUND_BALL_GENERIC_MUMBLE7 | SOUND_BALL_GENERIC_BOUNCE1,SOUND_BALL_GENERIC_BOUNCE2,SOUND_BALL_GENERIC_BOUNCE3,SOUND_BALL_GENERIC_BOUNCE4 | SOUND_BALL_GENERIC_DEATH1,SOUND_BALL_GENERIC_DEATH2,SOUND_BALL_GENERIC_DEATH3,SOUND_BALL_GENERIC_DEATH4,SOUND_BALL_GENERIC_DEATH5 | SOUND_BALL_GENERIC_DETACHED1
            ] ),
            describe_element( 'splat', min_occurrence=0, max_occurrence=1, attributes = [
                unknown_attribute( 'image', mandatory = True, init = 'IMAGE_FX_SMOKEBLACK'),  # Samples: IMAGE_FX_SMOKEBLACK | IMAGE_BALL_WATER_SPLAT1,IMAGE_BALL_WATER_SPLAT2 | IMAGE_BALL_TIMEBUG_SPLAT1,IMAGE_BALL_TIMEBUG_SPLAT2 | IMAGE_BALL_FISH_SPLAT1,IMAGE_BALL_FISH_SPLAT2 | IMAGE_BALL_PILOT_SPLAT1,IMAGE_BALL_PILOT_SPLAT2
            ] ),
            describe_element( 'strand', min_occurrence=0, max_occurrence=1, attributes = [
                real_attribute( 'dampfac', min_value=0.00001, mandatory = True, init = '0.9'),  # [0.002-1.9] Median:0.9 Samples: 0.9 | 0.002 | 1.9 | 0.1 | 0.2
                unknown_attribute( 'image', mandatory = True, init = 'IMAGE_BALL_FUSE_STRAND'),  # Samples: IMAGE_BALL_FUSE_STRAND | IMAGE_BALL_UTILGOOGLOBBERMOM_STRAND | IMAGE_BALL_DRAINEDISH_STRAND | IMAGE_BALL_FISH_STRING3 | IMAGE_BALL_WATER_STRAND
                unknown_attribute( 'inactiveimage', mandatory = True, init = 'IMAGE_BALL_GENERIC_ARM_INACTIVE'),  # Samples: IMAGE_BALL_GENERIC_ARM_INACTIVE | IMAGE_BALL_BALLOON_INACTIVE | IMAGE_BALL_GOOPRODUCT_STRAND | IMAGE_BALL_UTILNOATTACHUNWALKABLE_STRAND | IMAGE_BALL_BOMBSHAFT_STRAND
                int_attribute( 'maxforce', min_value=0.00001, mandatory = True, init = '600'),  # [200-2000] Median:600 Samples: 600 | 800 | 1000 | 200 | 300
                int_attribute( 'maxlen2', min_value=0.00001, mandatory = True, init = '140'),  # [50-380] Median:140 Samples: 140 | 50 | 380 | 300 | 120
                int_attribute( 'minlen', min_value=0.00001, mandatory = True, init = '100'),  # [10-150] Median:100 Samples: 100 | 130 | 10 | 150 | 40
                int_attribute( 'springconstmax', min_value=0.00001, mandatory = True, init = '9'),  # [1-10] Median:9 Samples: 9 | 10 | 1 | 2 | 6
                int_attribute( 'springconstmin', min_value=0.00001, mandatory = True, init = '9'),  # [1-10] Median:9 Samples: 9 | 10 | 2 | 1 | 6
                unknown_attribute( 'type', mandatory = True, init = 'spring'),  # Samples: spring | rope
                int_attribute( 'maxlen1', min_value=0.00001, init = '200'),  # [80-500] Median:200 Samples: 200 | 300 | 80 | 180 | 130
                bool_attribute( 'walkable', init = 'false'),
                int_attribute( 'shrinklen', min_value=0.00001, init = '90'),  # [80-160] Median:90 Samples: 90 | 100 | 120 | 130 | 160
                int_attribute( 'burnspeed', min_value=0.00001, init = '3'),  # [2-3] Median:3 Samples: 3 | 2
                unknown_attribute( 'burntimage', init = 'IMAGE_BALL_BOMBMINI_STRAND_BURNT'),  # Samples: IMAGE_BALL_BOMBMINI_STRAND_BURNT | IMAGE_BALL_PIXEL_ARM | IMAGE_BALL_BOMBSTICKY_STRAND_BURNT | IMAGE_BALL_PIXELPRODUCT_ARM | IMAGE_BALL_FUSE_STRAND_BURNT
                unknown_attribute( 'fireparticles', init = 'fireArmBurn'),  # Samples: fireArmBurn | ish_smallfire | poisonArmBurn
                int_attribute( 'ignitedelay', min_value=0, init = '0'),  # [0-0] Median:0 Samples: 0
                int_attribute( 'thickness', min_value=0.00001, init = '40'),  # [10-40] Median:20 Samples: 40 | 10 | 20
                bool_attribute( 'rope', init = 'true'),
                bool_attribute( 'geom', init = 'false'),
            ] )
        ] )
    ] )

TREE_ISLAND.add_objects( [
        describe_element( 'island', exact_occurrence = 1, attributes = [
            reference_attribute( 'icon', reference_family = 'image', reference_world = WORLD_GLOBAL, mandatory = True ),
            string_attribute( 'map', mandatory = True, init = 'island5'),
            string_attribute( 'name', mandatory = True, init = 'Cog in the Machine'),  # Samples: Cog in the Machine | The Goo Filled Hills | Information Superhighay | Little Miss World of Goo | End of the World
        ], objects = [
            describe_element( 'level', min_occurrence=1, attributes = [
                identifier_attribute( 'id', mandatory = True, reference_family = 'level',
                                      reference_world = WORLD_ISLAND ),
                reference_attribute( 'name', reference_family = 'text', reference_world = WORLD_ISLAND, init = '', mandatory = True ),
                reference_attribute( 'text', reference_family = 'text', reference_world = WORLD_ISLAND, init = '', mandatory = True ),
                reference_attribute( 'depends', reference_family = 'level', reference_world = WORLD_ISLAND),
                string_attribute( 'ocd', init = 'balls,10'),
                string_attribute( 'cutscene'),  # Samples: levelFadeOut,Chapter5End,gooTransition_out | x,whistleUnlock,gooTransition_out | levelFadeOut,Chapter4End,gooTransition_out | x,Chapter2Mid,gooTransition_out | levelFadeOut,Chapter1End,gooTransition_out
                string_attribute( 'oncomplete'),  # Samples: expandchapter4 | unlockwogcorp | unlockwhistle
                bool_attribute( 'skipeolsequence', init = 'true')
            ] )
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


if __name__ == "__main__":
    print_world_meta( WORLD_GLOBAL )

