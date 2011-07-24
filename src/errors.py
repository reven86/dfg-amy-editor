# To change this template, choose Tools | Templates
# and open the template in the editor.
ISSUE_LEVEL_NONE = 0
ISSUE_LEVEL_ADVICE = 1
ISSUE_LEVEL_WARNING = 2
ISSUE_LEVEL_CRITICAL = 4
ERROR_URL = 'http://goofans.com/developers/world-of-goo-level-editor/reference-guide/errors-and-warnings#%d'
ERROR_MORE_INFO = '&nbsp; <a href="' + ERROR_URL + '"><small><i>[more info]</i></small></a>'
ERROR_FRONT = [''
, 'Advice: '
, '<b>Warning:</b> '
, ''
, '<font color="#BF0000"><b>CRITICAL:</b></font> ']

ERROR_INFO = {0:[ISSUE_LEVEL_NONE, ''],
#Scene Tree Errors
    1:[ISSUE_LEVEL_CRITICAL, '<tt>%s</tt> is not static and has no mass'],
    2:[ISSUE_LEVEL_ADVICE, ' <tt>%s</tt> not static and rotated. It won\'t be where you think!'],
    3:[ISSUE_LEVEL_CRITICAL, '<tt>%s</tt> is not static and child <tt>%s</tt> has no mass'],
    4:[ISSUE_LEVEL_ADVICE, '<tt>%s</tt> : Images on compgeom children are ignored in the game.'], #redundant?
    5:[ISSUE_LEVEL_CRITICAL, '<tt>%s</tt> is non-static and has no children'],
    6:[ISSUE_LEVEL_WARNING, '<tt>%s</tt> is static and has no children.'],
    7:[ISSUE_LEVEL_CRITICAL, '<tt>%s</tt> is static and has a motor'],
    8:[ISSUE_LEVEL_CRITICAL, '<tt>%s</tt> is at the centre of rff %s'],
    9:[ISSUE_LEVEL_ADVICE, '<tt>%s</tt> is spinning but has no hinge!'],
    10:[ISSUE_LEVEL_WARNING, '<tt>%s</tt> is a compgeom child so cannot have a hinge!'],
    11:[ISSUE_LEVEL_CRITICAL, 'linearforcefield <tt>%s</tt> has size but no center'],

#Level Tree Errors
    101:[ISSUE_LEVEL_ADVICE, '<tt>%s</tt> poi traveltime will cause a delay starting the level'],
    102:[ISSUE_LEVEL_WARNING, 'Level has no <tt>normal</tt> camera'],
    103:[ISSUE_LEVEL_WARNING, 'Level has no <tt>widescreen</tt> camera'],
    109:[ISSUE_LEVEL_CRITICAL, 'You can\'t connect <tt>%s (%s)</tt> to <tt>%s (%s)</tt>'],

#Resource Errors
    201:[ISSUE_LEVEL_WARNING, 'Image file extensions must be png (lowercase) %s'],
    202:[ISSUE_LEVEL_ADVICE, '%s unused'],
    203:[ISSUE_LEVEL_WARNING, 'Sound file extensions must be ogg (lowercase) %s'],
    204:[ISSUE_LEVEL_ADVICE, '%s unused'],
    205:[ISSUE_LEVEL_ADVICE, 'Text resource %s unused'],

#Dependancy Errors and Notifications
    304:[ISSUE_LEVEL_ADVICE, 'Custom Materials used <tt>%s</tt>'],
    305:[ISSUE_LEVEL_CRITICAL, 'Material <tt>%s</tt> is missing'],
    308:[ISSUE_LEVEL_ADVICE, 'Custom Animtaions used <tt>%s</tt>'],
    309:[ISSUE_LEVEL_CRITICAL, 'Animation file <tt>%s.anim.binltl</tt> is missing'],

#Global Level Errors
    401:[ISSUE_LEVEL_WARNING, 'the levelexit is outside scene bounds'],
}
