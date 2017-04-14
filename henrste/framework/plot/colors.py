BLUE = "#001E90FF"
LILAC = "#007570B3"
RED = "#00FF0000"
BLACK = "#00333333"
GREEN = "#0066A61E"
GRAY = "#00666666"

CC_DCTCP = BLUE
CC_CUBIC = RED
CC_RENO = RED
CC_CUBIC_ECN = BLACK

L4S = BLUE
CLASSIC = RED
AGGR = GREEN

CLASS_NOECT = '#00E7298A'
CLASS_ECT0 = '#00333333'
CLASS_ECT1 = '#00666666'
CLASS_UNKNOWN_UDP = GRAY
UNKNOWN = "#00D2691E"

DROPS_CLASSIC = RED
DROPS_L4S = BLUE
MARKS_L4S = GRAY

title_map = (
    ('cubic-ecn', CC_CUBIC_ECN),
    ('ecn-cubic', CC_CUBIC_ECN),
    ('cubic', CC_CUBIC),
    ('dctcp', CC_DCTCP),
    ('reno', CC_RENO),
    ('ect(1)', CLASS_ECT1),
    ('ect(0)', CLASS_ECT0),
    ('udp=non ect', CLASS_NOECT),
    ('udp', CLASS_UNKNOWN_UDP),
    ('other', UNKNOWN),
)


def get_from_tagname(title):
    title = title.lower()

    for key, value in title_map:
        if key in title:
            return value

    return UNKNOWN
