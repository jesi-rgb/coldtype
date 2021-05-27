from coldtype import *
from coldtype.warping import warp_fn

Style.RegisterShorthandPrefix("≈", "~/Type/fonts/fonts")
peshka = Font.Cacheable("≈/CoFoPeshkaVariableV0.5.ttf")

loop = Loop(150, 15, [ # some keyframes
    dict(wdth=0, wght=0, rotate=-15, leading=200,
        font_size=700, warp=0, blur=15),
    dict(wdth=1, wght=1, rotate=0, leading=10,
        font_size=50, warp=200, blur=5),
    dict(wdth=0, wght=1, rotate=15, leading=100,
        font_size=500, warp=50, blur=3),
    dict(wdth=0.5, wght=0.5, rotate=0, leading=-470,
        font_size=330, warp=0, blur=1)
    ])

@animation(timeline=loop)
def warp(f):
    state = f.a.t.current_state(f.i, e="eeio")
    return ((ß:=StSt("WARP\nBLUR", peshka, ro=1, **state))
        .align(f.a.r).pen() # a single, centered vector
        .f(Gradient.V(ß.ambit(), hsl(0.7), hsl(0.9)))
        #.flatten(5) # slower but preserves curves across warp
        .nlt(warp_fn(f.i*30, f.i, mult=int(state["warp"])))
        .f(1).phototype(f.a.r,
            state["blur"], cutw=50, fill=hsl(0.75))
        )