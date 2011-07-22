"""Describes the structure and constraints of elements used in data file of WOG."""
from metaworld import * #@UnusedWildImport

# Declares all file types
TREE_CAMPAIGN = describe_tree( 'campaign' )

TREE_LEVEL_GAME = describe_tree( 'level.game' )
TREE_LEVEL_SCENE = describe_tree( 'level.scene' )

# Declares the world hierarchy
WORLD_LEVEL = describe_world( 'level', trees_meta = [
    TREE_LEVEL_GAME,
    TREE_LEVEL_SCENE,
    ] )
WORLD_CAMPAIGN = describe_world( 'campaign', trees_meta = [
    TREE_CAMPAIGN
    ] )
WORLD_GLOBAL = describe_world( 'game',
                               child_worlds = [ WORLD_CAMPAIGN, WORLD_LEVEL ],
                               trees_meta = [ ] )

LEVELS_ORIGINAL = set( ['level_name_1'] )
LEVELS_ORIGINAL_LOWER = [level_name.lower() for level_name in LEVELS_ORIGINAL]

MATERIALS_ORIGINAL = ["ice", "rock", "grass", "fruit",
                      "sticky", "verysticky", "kindasticky" , "slightlysticky",
                      "slosh", "swamp", "throat", "machine", "IvyTower",
                      "volcanicPercolatorSides", "ServerPlatform",
                      ]

PARTICLEEFFECTS_ORIGINAL = ['unlockfuse', 'unlockburst', 'snowStormFromPoint', 'splash', 'gooFallWide2', 'gooSplatter',
                          'gooSplatterSubtle', 'mistUp',
                          'thruster',
                          'poisonBallBurn', 'poisonArmBurn', 'blackSmokeRising', 'bubblesRisingFromPoint',
                          'bubblesRisingFromPointSlow', 'wogcSmoke', 'wogcSmokeIsh', 'whiteSmokeRising', 'sleepyZzz',
                          'ish_sleepyZzz', 'ishr_sleepyZzz', 'whistle',
                          'worldMap_FactorySmoke', 'BurningManSmoke', 'RobotHeadSmoke', 'distantSmokestack',
                          'worldMap_FactorySmokeWhite', 'cigSmoke', 'gentleFactorySmoke', 'puffyFactorySmoke',
                          'gentleFactorySmokeSepia', 'matchSmoke', 'gooTankStream', 'gooDrips', 'polFountain1', 'polFountain2',
                          'gooMist', 'timebugFizz', 'flashes', 'tubeAirFlowUp', 'tubeAirFlowLeft', 'geomExplosionDust',
                          'ish_FlingTrail', 'ishr_FlingTrail', 'ish_gpu_bitspew', 'ish_bitPop', 'beautypop',
                          'flowerDust', 'OOS_gooDrips', 'OOS_gooGlobs', 'BallExplode_Fuse', 'BallExplode_Bomb', 'BallExplode_ISH',
                          'ISH_undeleteFizz', 'ish_bubbles']

AMBIENTEFFECTS_ORIGINAL = ['bigleaves1', 'smallleaves1', 'rainingleaves', 'rainingleavesRight', 'leavesRight',
                         'snowSparse', 'snowDense', 'snowStorm', 'snowStormC3',
                         'blackBallsRising', 'blackBallsRight', 'blackLeaves', 'blackLeavesHeavy',
                         'rainStreaksHeavy', 'rainStreaksHeavyDistant', 'rainStreaksDown',
                         'mistRight', 'breezeRight', 'breezeUpSlow', 'breezeDownSlow', 'breezeUp', 'mistUpSepia',
                         'ish_BigLeaves', 'ish_SmallLeaves', 'ish_RainLeavesLeft', 'ish_RainLeavesUp', 'ish_RainLeavesUpRed',
                         'ish_BreezeRight', 'ish_HeavyBreezeLeft', 'ish_HeavyBreezeUp', 'OOS_breezeRight']

ANIMATIONS_ORIGINAL = ['blink', 'closer', 'discovery', 'hairblow',
                     'happyTreeDance', 'islandhairblow', 'island_name_in', 'island_name_loop',
                     'island_name_out', 'level_name_popup', 'ocdFlagWave', 'rot_1rps', 'treeBlow_leaf1',
                     'treeBlow_leaf2', 'treeBlow_leaf3', 'treeBlow_trunk']
ANIMATIONS_GLOBAL = []

#@DaB
FILE_ELEMENT = describe_element( 'file', attributes = [
                        string_attribute( 'name', mandatory = True ),
                        string_attribute( 'type', mandatory = True ) ] )
FOLDER_ELEMENT = describe_element( 'folder', attributes = [
        string_attribute( 'name', mandatory = True )], elements = [
        FILE_ELEMENT] )
FOLDER_ELEMENT.add_elements( [FOLDER_ELEMENT] )

LANGUAGE_ATTRIBUTES = []
for lang in ['de', 'es', 'fr', 'it', 'nl', 'pl']:
    LANGUAGE_ATTRIBUTES.append( string_attribute( lang, allow_empty = True, remove_empty = True ) )

TREE_LEVEL_GAME.add_elements( [
    describe_element( 'level', exact_occurrence = 1, groups = 'game', attributes = [],
        elements = [
        describe_element( 'camera', exact_occurrence = 2, groups = 'camera', attributes = [
            enum_attribute( 'aspect', values = ( 'widescreen', 'normal' ), default = 'normal', display_id = True ),
            xy_attribute( 'endpos' ),
            real_attribute( 'endzoom', min_value = 0.00001 )
            ], elements = [
            describe_element( 'poi', min_occurrence = 1, groups = 'camera', attributes = [
                xy_attribute( 'pos', init = '0,0', mandatory = True ),
                real_attribute( 'zoom', min_value = 0.00001, default = 1 , init = 1 , mandatory = True ),
                real_attribute( 'pause', min_value = 0, default = 0 , init = 0 , mandatory = True, tooltip = 'Wait here for n seconds\n' ),
                real_attribute( 'traveltime', min_value = 0, default = 0, init = 3 , mandatory = True, tooltip = 'Time taken to travel TO this position\nIgnored on first POI' )
                ] )
            ] ),
        describe_element( 'music', groups = 'resource', max_occurrence = 1, attributes = [
            reference_attribute( 'sound', map_to = 'id', display_id = True, mandatory = True,
                reference_family = 'sound', reference_world = WORLD_LEVEL )
            ] ),
        describe_element( 'loopsound', groups = 'resource', max_occurrence = 1, attributes = [
            reference_attribute( 'sound', map_to = 'id', display_id = True, mandatory = True,
                reference_family = 'sound', reference_world = WORLD_LEVEL )
            ] ),
        describe_element( 'levelexit', groups = 'game', attributes = [
            string_attribute( 'id', display_id = True, allow_empty = True, remove_empty = True ),
            xy_attribute( 'pos', mandatory = True, init = '0,0' , position = True ),
            radius_attribute( 'radius', mandatory = True, init = '75' ),
            ] ),
        ] )
    ] )


# Values for Tag attribute (Physic items)
_TAG_VALUES = ( 'walkable', )

ELEMENT_BUTTON = describe_element( 'button', groups = 'image', attributes = [
        string_attribute( 'id', display_id = True, mandatory = True ),
        xy_attribute( 'center', mandatory = True, init = '0,0', map_to = ( 'x', 'y' ) , position = True ),
        real_attribute( 'depth', mandatory = True, init = '10' ),
        real_attribute( 'alpha', mandatory = True, init = '1' ),
        real_attribute( 'rotation', mandatory = True, init = '0' ),
        scale_attribute( 'scale', init = '1,1', min_value = 0.0000001, mandatory = True,
                         map_to = ( 'scalex', 'scaley' ) ),
        rgb_attribute( 'colorize', mandatory = True, init = '255,255,255' ),
        reference_attribute( 'up', reference_family = 'image', reference_world = WORLD_LEVEL,
                             init = '', mandatory = True ),
        reference_attribute( 'over', reference_family = 'image', reference_world = WORLD_LEVEL,
                             init = '', mandatory = True ),
        enum_attribute( 'context', ( 'screen' ) ),
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

ELEMENT_RECTANGLE = describe_element( 'rectangle', groups = 'rect', attributes = [
    identifier_attribute( 'id', display_id = True, mandatory = True, allow_empty = True,
        reference_family = 'geometry', reference_world = WORLD_LEVEL ),
    xy_attribute( 'center', mandatory = True, init = '0,0', map_to = ( 'x', 'y' ) , position = True ),
    size_attribute( 'size', mandatory = True, init = '100,100', map_to = ( 'width', 'height' ) ),
    angle_degrees_attribute( 'rotation', mandatory = True, init = '0' ),
    bool_attribute( 'static', default = 'true', tooltip = "If static=true this object cannot move\nIf static=false or empty then a mass is required." ),
    real_attribute( 'mass', tooltip = "Mass of this item.\nRequired if static=false or empty" ),
    reference_attribute( 'material', reference_family = 'material', reference_world = WORLD_GLOBAL,
                          init = '' , allow_empty = True, remove_empty = True ),
    enum_attribute( 'tag', _TAG_VALUES, is_list = True, allow_empty = True, remove_empty = True ),
    reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL,
                         init = '', allow_empty = True, remove_empty = True ),
    xy_attribute( 'imagepos', allow_empty = True, remove_empty = True ),
    angle_degrees_attribute( 'imagerot', allow_empty = True, remove_empty = True ),
    scale_attribute( 'imagescale', allow_empty = True, remove_empty = True ),
    real_attribute( 'rotspeed', allow_empty = True, remove_empty = True ),
    bool_attribute( 'contacts' , allow_empty = True, remove_empty = True ),
    bool_attribute( 'collide', allow_empty = True, remove_empty = True ),
    bool_attribute( 'nogeomcollisions', allow_empty = True, remove_empty = True )
    ] )

ELEMENT_CHILD_RECTANGLE = describe_element( 'rectangle', groups = 'rect', attributes = [
    string_attribute( 'id', display_id = True, allow_empty = True ),
    xy_attribute( 'center', mandatory = True, init = '0,0', map_to = ( 'x', 'y' ), position = True ),
    size_attribute( 'size', mandatory = True, init = '100,100', map_to = ( 'width', 'height' ) ),
    angle_degrees_attribute( 'rotation', mandatory = True, init = '0' ),
    real_attribute( 'mass', tooltip = "Mass of this child" )
] )



ELEMENT_CIRCLE = describe_element( 'circle', groups = 'circle', attributes = [
    identifier_attribute( 'id', display_id = True, mandatory = True, allow_empty = True,
        reference_family = 'geometry', reference_world = WORLD_LEVEL ),
    xy_attribute( 'center', mandatory = True, init = '0,0', map_to = ( 'x', 'y' ) , position = True ),
    radius_attribute( 'radius', mandatory = True, init = '75' ),
    bool_attribute( 'static', default = 'true', tooltip = "If static=true this object cannot move\nIf static=false or empty then a mass is required." ),
    real_attribute( 'mass', tooltip = "Mass of this item.\nRequired if static=false or empty" , allow_empty = True, remove_empty = True ),
    reference_attribute( 'material', reference_family = 'material', reference_world = WORLD_GLOBAL,
                          init = '' , allow_empty = True, remove_empty = True ),
    enum_attribute( 'tag', _TAG_VALUES, is_list = True, allow_empty = True, remove_empty = True ),
    reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL,
                         init = '', allow_empty = True, remove_empty = True ),
    xy_attribute( 'imagepos', allow_empty = True, remove_empty = True ),
    angle_degrees_attribute( 'imagerot', allow_empty = True, remove_empty = True ),
    scale_attribute( 'imagescale', allow_empty = True, remove_empty = True ),
    real_attribute( 'rotspeed', allow_empty = True, remove_empty = True ),
    bool_attribute( 'contacts' ),
    ] )

ELEMENT_CHILD_CIRCLE = describe_element( 'circle', groups = 'circle', attributes = [
    string_attribute( 'id', display_id = True, allow_empty = True ),
    xy_attribute( 'center', mandatory = True, init = '0,0', map_to = ( 'x', 'y' ), position = True ),
    radius_attribute( 'radius', mandatory = True, init = '75' ),
    real_attribute( 'mass', tooltip = "Mass of this child" , allow_empty = True, remove_empty = True )
    ] )

TREE_LEVEL_SCENE.add_elements( [
    describe_element( 'scene', exact_occurrence = 1, groups = 'image', attributes = [
        rgb_attribute( 'backgroundcolor', mandatory = True, init = '0,0,0' ),
        real_attribute( 'minx', init = '-500', tooltip = "Left edge of playing area\nCamera will not show past here.", allow_empty = True, remove_empty = True ),
        real_attribute( 'miny', init = '-500', tooltip = "Bottom edge of playing area\nCamera will not show past here.", allow_empty = True, remove_empty = True ),
        real_attribute( 'maxx', init = '500', tooltip = "Right edge of playing area\nCamera will not show past here.", allow_empty = True, remove_empty = True ),
        real_attribute( 'maxy', init = '500', tooltip = "Top edge of playing area\nCamera will not show past here." , allow_empty = True, remove_empty = True )
        ],
        elements = [
        describe_element( 'SceneLayer', groups = 'image', attributes = [
            string_attribute( 'name', display_id = True ),
            reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL,
                                 init = '', mandatory = True ),
            xy_attribute( 'center', mandatory = True, init = '0,0', map_to = ( 'x', 'y' ) , position = True ),
            scale_attribute( 'scale', default = '1,1', min_value = 0.000001, map_to = ( 'scalex', 'scaley' ), allow_empty = True, remove_empty = True ),
            angle_degrees_attribute( 'rotation', default = '0', allow_empty = True, remove_empty = True ),
            real_attribute( 'depth', mandatory = True, init = '0' ),
            bool_attribute( 'tilex', default = 'false', allow_empty = True, remove_empty = True ),
            bool_attribute( 'tiley', default = 'false', allow_empty = True, remove_empty = True ),
            int_attribute ( 'tilecountx', allow_empty = True, remove_empty = True ),
            int_attribute ( 'tilecounty', allow_empty = True, remove_empty = True ),
            real_attribute( 'alpha', min_value = 0, max_value = 1, default = '1' , allow_empty = True, remove_empty = True ),
            rgb_attribute( 'colorize', init = '255,255,255', allow_empty = True, remove_empty = True ),
            enum_attribute( 'anim', ANIMATIONS_GLOBAL, allow_empty = True, remove_empty = True ), # @todo Animation are filename in res/anim/*.bintl
            real_attribute( 'animspeed', allow_empty = True, remove_empty = True ),
            real_attribute( 'animdelay', min_value = 0.0001, default = '1', allow_empty = True, remove_empty = True ),
            identifier_attribute( 'id', allow_empty = True, remove_empty = True,
                reference_family = 'image', reference_world = WORLD_LEVEL ),
            enum_attribute( 'context', ( 'screen' ), allow_empty = True, remove_empty = True ),
            ] ),
        ELEMENT_BUTTON,
        describe_element( 'buttongroup', groups = 'image', attributes = [
            string_attribute( 'id', mandatory = True ),
            xy_attribute( 'osx', mandatory = True )
            ],
            elements = [
                ELEMENT_BUTTON
            ] ),
        describe_element( 'label', groups = 'text', attributes = [
            string_attribute( 'id', display_id = True, mandatory = True, init = '', allow_empty = True ),
            xy_attribute( 'position', mandatory = True, init = '0,0', map_to = ( 'x', 'y' ) , position = True ),
            angle_degrees_attribute( 'rotation', mandatory = True, init = '0' ),
            real_attribute( 'scale', mandatory = True, init = '1' ),
            reference_attribute( 'text', reference_family = 'TEXT_LEVELNAME_STR', reference_world = WORLD_LEVEL, mandatory = True ),
            reference_attribute( 'font', reference_family = 'font', reference_world = WORLD_GLOBAL,
                                 mandatory = True ),
            enum_attribute( 'align', ( 'right', 'center', 'left' ), mandatory = True, init = 'center' ),
            real_attribute( 'depth', mandatory = True, init = '10' ),
            bool_attribute( 'overlay', init = 'false', allow_empty = True, remove_empty = True ),
            bool_attribute( 'screenspace', init = 'false', allow_empty = True, remove_empty = True )
            ] ),
        ELEMENT_RECTANGLE,
        ELEMENT_CIRCLE,
        describe_element( 'compositegeom', groups = 'compgeom', attributes = [
            identifier_attribute( 'id', display_id = True,
                mandatory = True, allow_empty = True,
                reference_family = 'geometry', reference_world = WORLD_LEVEL ),
            xy_attribute( 'center', mandatory = True, init = '0,0', map_to = ( 'x', 'y' ) , position = True ),
            angle_degrees_attribute( 'rotation', mandatory = True, init = '0' ),
            bool_attribute( 'static', default = 'true' , tooltip = "If static=true this object and its children cannot move\nIf static=false then all children require a mass." ),
            reference_attribute( 'material', reference_family = 'material', reference_world = WORLD_GLOBAL,
                                 init = '' , allow_empty = True, remove_empty = True ),
            enum_attribute( 'tag', _TAG_VALUES, is_list = True, allow_empty = True, remove_empty = True ),
            reference_attribute( 'image', reference_family = 'image', reference_world = WORLD_LEVEL, allow_empty = True, remove_empty = True ),
            xy_attribute( 'imagepos', allow_empty = True, remove_empty = True ),
            angle_degrees_attribute( 'imagerot', allow_empty = True, remove_empty = True ),
            scale_attribute( 'imagescale', allow_empty = True, remove_empty = True ),
            real_attribute( 'rotspeed' , allow_empty = True, remove_empty = True ),
            bool_attribute( 'contacts' ),
            bool_attribute( 'nogeomcollisions' )
            ],
            elements = [
                ELEMENT_CHILD_RECTANGLE,
                ELEMENT_CHILD_CIRCLE
            ] ),
        describe_element( 'line', groups = 'line', attributes = [
            string_attribute( 'id', display_id = True, mandatory = True,
                              allow_empty = True, init = '' ),
            xy_attribute( 'anchor', mandatory = True, init = '0,0' , position = True ),
            dxdy_attribute( 'normal', mandatory = True, init = '1,0' ),
            reference_attribute( 'material', reference_family = 'material', reference_world = WORLD_GLOBAL,
                                 init = '', allow_empty = True, remove_empty = True ),
           # bool_attribute( 'static', init = 'true' ),
            enum_attribute( 'tag', _TAG_VALUES, is_list = True , allow_empty = True, remove_empty = True )
            ] ),
        describe_element( 'linearforcefield', groups = 'physic', attributes = [
            string_attribute( 'id', display_id = True, allow_empty = True ),
            xy_attribute( 'center', init = '0,0' , allow_empty = True, remove_empty = True, position = True ),
            size_attribute( 'size', map_to = ( 'width', 'height' ) , allow_empty = True, remove_empty = True ),
            enum_attribute( 'type', ( 'force', 'gravity' ), init = 'gravity', mandatory = True ),
            dxdy_attribute( 'force', mandatory = True, init = '0,-10' ),
            real_attribute( 'dampeningfactor', mandatory = True, init = '0' ),
            bool_attribute( 'antigrav', mandatory = True, init = 'false' ),
            real_attribute( 'depth' , allow_empty = True, remove_empty = True ),
            argb_attribute( 'color' , allow_empty = True, remove_empty = True ),
            bool_attribute( 'enabled' , allow_empty = True, remove_empty = True ),
            bool_attribute( 'water', default = 'false' , allow_empty = True, remove_empty = True ),
            bool_attribute( 'geomonly' , allow_empty = True, remove_empty = True )
            ] ),
        describe_element( 'radialforcefield', groups = 'physic', attributes = [
            string_attribute( 'id', display_id = True, allow_empty = True ),
            xy_attribute( 'center', mandatory = True, init = '0,0' , position = True ),
            radius_attribute( 'radius', mandatory = True, init = '100' ),
#            enum_attribute( 'type', ('force', 'gravity'), init = 'gravity', mandatory = True ), # @todo in game, only gravity
            real_attribute( 'forceatcenter', mandatory = True, init = '10' ),
            real_attribute( 'forceatedge', mandatory = True, init = '0' ),
            real_attribute( 'dampeningfactor', mandatory = True, init = '0' ),
            bool_attribute( 'antigrav', mandatory = True, init = 'false' ),
#            real_attribute( 'depth' ),
#            bool_attribute( 'enabled',allow_empty=True,remove_empty=True )
#            bool_attribute( 'geomonly' )
            ] ),
        describe_element( 'hinge', groups = 'physic', attributes = [
            xy_attribute( 'anchor', mandatory = True , position = True ),
            reference_attribute( 'body1', mandatory = True,
                reference_family = 'geometry', reference_world = WORLD_LEVEL ),
            reference_attribute( 'body2', allow_empty = True, remove_empty = True,
                reference_family = 'geometry', reference_world = WORLD_LEVEL ),
            real_attribute( 'bounce' , allow_empty = True, remove_empty = True ),
            real_attribute( 'histop' , allow_empty = True, remove_empty = True ),
            real_attribute( 'lostop' , allow_empty = True, remove_empty = True ),
            real_attribute( 'stopcfm' , allow_empty = True, remove_empty = True ),
            real_attribute( 'stoperp' , allow_empty = True, remove_empty = True )
            ] ),
        describe_element( 'slider', groups = 'physic', attributes = [
            reference_attribute( 'body1', mandatory = True,
                reference_family = 'geometry', reference_world = WORLD_LEVEL ),
            reference_attribute( 'body2', mandatory = True,
                reference_family = 'geometry', reference_world = WORLD_LEVEL ),
            dxdy_attribute( 'axis', mandatory = True ),
            real_attribute( 'bounce', allow_empty = True, remove_empty = True ),
            real_attribute( 'histop', allow_empty = True, remove_empty = True ),
            real_attribute( 'lostop', allow_empty = True, remove_empty = True ),
            real_attribute( 'stopcfm' , allow_empty = True, remove_empty = True ),
            real_attribute( 'stoperp' , allow_empty = True, remove_empty = True )
            ] ),
        describe_element( 'motor', groups = 'physic', attributes = [
            reference_attribute( 'body', reference_family = 'geometry', reference_world = WORLD_LEVEL, mandatory = True ),
            real_attribute( 'maxforce', mandatory = True, init = '20' ),
            real_attribute( 'speed', mandatory = True, init = '-0.01' )
            ] ),
        ] )
    ] )


ELEMENT_PARTICLE = describe_element( 'particle', groups = 'image',
                                     min_occurrence = 1, attributes = [
    dxdy_attribute( 'acceleration', mandatory = True, init = '0,0.1' ),
    bool_attribute( 'directed', mandatory = True, init = 'false' ),
    reference_attribute( 'image', is_list = True, reference_family = 'image', reference_world = WORLD_GLOBAL,
                         mandatory = True ),
    angle_degrees_attribute( 'movedir', mandatory = True, init = '0' ),
    angle_degrees_attribute( 'movedirvar', mandatory = True, init = '0' ), # ?
    scale_attribute( 'scale', mandatory = True, init = '1,1' ),
    dxdy_attribute( 'speed', mandatory = True, init = '1,1' ),
    bool_attribute( 'additive' ),
    real_attribute( 'dampening', min_value = 0, max_value = '1' ),
    bool_attribute( 'fade' ),
    real_attribute( 'finalscale', min_value = 0 ),
    xy_attribute( 'lifespan' ), # @todo TYPE OPTIONAL INTERVAL (e.g. 1 or 1,2 are ok)?
    xy_attribute( 'rotation' ), # @todo TYPE OPTIONAL INTERVAL (e.g. 1 or 1,2 are ok)?
    xy_attribute( 'rotspeed' ) # @todo TYPE OPTIONAL INTERVAL (e.g. 1 or 1,2 are ok)?
    ],
    elements = [
        describe_element( 'axialsinoffset', min_occurrence = 1, max_occurrence = 2, attributes = [
            xy_attribute( 'amp', mandatory = True, init = '5,10' ), # @todo just 2 reals (interval)
            enum_attribute( 'axis', ( 'x', 'y' ), mandatory = True, init = 'x' ),
            xy_attribute( 'freq', mandatory = True, init = '5,10' ), # @todo just 2 reals (interval)
            xy_attribute( 'phaseshift', mandatory = True, init = '0.2,0.4' ), # @todo just 2 reals (interval)
        ] )
    ] )

TREE_CAMPAIGN.add_elements( [
        describe_element( 'campaign', exact_occurrence = 1, attributes = [
            reference_attribute( 'icon', reference_family = 'image', reference_world = WORLD_GLOBAL, mandatory = True ),
            string_attribute( 'map', mandatory = True, init = 'campaign1' ),
            string_attribute( 'name', display_id = True, mandatory = True,
                init = 'Tutorial' )
        ], elements = [
            describe_element( 'level', min_occurrence = 1, attributes = [
                identifier_attribute( 'id', display_id = True, mandatory = True,
                    reference_family = 'level', reference_world = WORLD_CAMPAIGN ),
                reference_attribute( 'name', reference_family = 'text', reference_world = WORLD_CAMPAIGN, init = '', mandatory = True ),
                reference_attribute( 'text', reference_family = 'text', reference_world = WORLD_CAMPAIGN, init = '', mandatory = True ),
                reference_attribute( 'depends', reference_family = 'level', reference_world = WORLD_CAMPAIGN ),
                string_attribute( 'cutscene' ),
                string_attribute( 'oncomplete' ),
                bool_attribute( 'skipeolsequence', init = 'true' )
            ] )
        ] )
    ] )


LEVEL_GAME_TEMPLATE = """\
<level>

	<!-- Camera -->
	<camera aspect="normal" endpos="0,0" endzoom="1">
		<poi pos="0,0" traveltime="0" pause="0" zoom="1" />
	</camera>
	<camera aspect="widescreen" endpos="0,0" endzoom="1">
		<poi pos="0,0" traveltime="0" pause="0" zoom="1" />
	</camera>

	<!-- Level Exit -->
	<levelexit id="theExit" pos="0,0" radius="75" filter="" >
	</levelexit>

</level>
"""

LEVEL_SCENE_TEMPLATE = """\
<scene minx="-500" miny="0" maxx="500" maxy="1000" backgroundcolor="0,0,0" >
	<linearforcefield type="gravity" force="0,-10" dampeningfactor="0" antigrav="true"  />

	<line id="right" tag="" anchor="500,300" normal="-1,0" />
	<line id="left" tag="" anchor="-500,300" normal="1,0" />
	<line id="ground" anchor="0,20" normal="0,1" />
</scene>"""

XSL_ADD_TEMPLATE = """\
<xsl:transform version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <!-- Copy everything not matched by another rule -->
  <xsl:template match="* | comment()">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>

  <!-- Append -->
  <xsl:template match="%(path)s">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates/>
      %(xml_data)s
    </xsl:copy>
  </xsl:template>
</xsl:transform>"""

if __name__ == "__main__":
    print_world_meta( WORLD_GLOBAL )
