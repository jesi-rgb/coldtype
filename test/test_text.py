import unittest
from pathlib import Path
from coldtype.geometry import *
from coldtype.text.composer import StSt, Font, Glyphwise, Style
from coldtype.pens.svgpen import SVGPen

tf = Path(__file__).parent
mutator = Font.Cacheable("assets/MutatorSans.ttf")
clarette = Font.Cacheable("~/Type/fonts/fonts/_wdths/ClaretteGX.ttf")

class TestText(unittest.TestCase):
    def _test_glyph_names(self, font_path):
        ss = StSt("CDELOPTY", font_path, 100, wdth=0)
        ssps = ss#.pens()
        self.assertEqual(len(ssps), 8)
        self.assertEqual(ssps[0].glyphName, "C")
        self.assertEqual(ssps[-1].glyphName, "Y")

        fp = Path(font_path)
        op = (tf / f"ignorables/{fp.name}.svg")
        op.parent.mkdir(exist_ok=True)
        op.write_text(SVGPen.Composite(ssps, ssps.ambit(), viewBox=True))
        return ssps

    def test_format_equality(self):
        ttf = self._test_glyph_names("assets/ColdtypeObviously-VF.ttf")
        otf = self._test_glyph_names("assets/ColdtypeObviously_CompressedBlackItalic.otf")
        ufo = self._test_glyph_names("assets/ColdtypeObviously_CompressedBlackItalic.ufo")
        ds = self._test_glyph_names("assets/ColdtypeObviously.designspace")

        # TODO why isn't the ttf version equal to these?
        self.assertEqual(ufo[0].value, ds[0].value)
        self.assertEqual(ufo[-1].value, ds[-1].value)
    
    def test_space(self):
        r = Rect(2000, 1000)

        txt = StSt("A B", mutator, 1000)
        space = txt[1]
        self.assertEqual(space.glyphName, "space")
        self.assertEqual(space.ambit().w, 250)
        self.assertEqual(txt.ambit().w, 1093)
        self.assertEqual(space.ambit().x, 400)
        txt.align(r)
        self.assertEqual(space.ambit().x, 863.5)

        #txt.picklejar(r)

        txt = StSt("A B", mutator, 1000, space=500)
        space = txt[1]
        self.assertEqual(space.glyphName, "space")
        self.assertEqual(space.ambit().w, 500)
        self.assertEqual(txt.ambit().w, 1093+250)
        self.assertEqual(space.ambit().x, 400)
        txt.align(r)
        self.assertEqual(space.ambit().x, 863.5-(250/2))
    
        #txt.picklejar(r)
    
    def test_glyphwise(self):
        r = Rect(1080, 300)
        gl = (Glyphwise(["fi", "j", "o", "ff"],
            lambda i, c: Style(clarette, 300, wdth=1))
            .align(r))
        
        self.assertEqual(len(gl), 4)
        self.assertEqual(gl[0].glyphName, "f_i")
        self.assertEqual(gl[-1].glyphName, "f_f")
        gl.picklejar(r)


if __name__ == "__main__":
    unittest.main()