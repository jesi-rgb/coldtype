import math
from defcon import Font
from pathlib import Path
import easing_functions as ef
from coldtype.pens.datpen import DATPen
from fontTools.misc.bezierTools import splitCubic, splitLine


eases = dict(
    cei=ef.CubicEaseIn,
    ceo=ef.CubicEaseOut,
    ceio=ef.CubicEaseInOut,
    qei=ef.QuadEaseIn,
    qeo=ef.QuadEaseOut,
    qeio=ef.QuadEaseInOut,
    eei=ef.ExponentialEaseIn,
    eeo=ef.ExponentialEaseOut,
    eeio=ef.ExponentialEaseInOut,
    sei=ef.SineEaseIn,
    seo=ef.SineEaseOut,
    seio=ef.SineEaseInOut,
    bei=ef.BounceEaseIn,
    beo=ef.BounceEaseOut,
    beio=ef.BounceEaseInOut,
    eleo=ef.ElasticEaseOut,
    elei=ef.ElasticEaseIn,
    elieo=ef.ElasticEaseInOut)


def curve_pos_and_speed(curve, x):
    x1000 = x*1000
    for idx, (action, pts) in enumerate(curve.value):
        if action in ["moveTo", "endPath", "closePath"]:
            continue
        last_action, last_pts = curve.value[idx-1]
        if action == "curveTo":
            o = -1
            a = last_pts[-1]
            b, c, d = pts
            if x1000 == a[0]:
                o = a[1]/1000
                eb = a
                ec = b
            elif x1000 == d[0]:
                o = d[1]/1000
                eb = c
                ec = d
            elif x1000 > a[0] and x1000 < d[0]:
                e, f = splitCubic(a, b, c, d, x1000, isHorizontal=False)
                ez, ea, eb, ec = e
                o = ec[1]/1000
            else:
                continue
            tangent = math.degrees(math.atan2(ec[1] - eb[1], ec[0] - eb[0]) + math.pi*.5)
            #print(o, tangent)
            if tangent >= 90:
                t = (tangent - 90)/90
            else:
                t = tangent/90
            if o != -1:
                return o, t
    raise Exception("No curve value found!")


def ease(style, x):
    if style == "linear":
        return x
    e = eases.get(style)
    if e:
        return e().ease(x)
    elif False:
        if style in easer_ufo:
            return curve_pos_and_speed(DATPen().glyph(easer_ufo[style]), x)
        else:
            raise Exception("No easing function with that mnemonic")
    else:
        raise Exception("No easing function with that mnemonic")