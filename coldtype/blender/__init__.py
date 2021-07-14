# to be loaded from within Blender

import os, math

from coldtype.geometry.rect import Rect
from coldtype.pens.datpen import DATPen, DATPens
from coldtype.pens.blenderpen import BlenderPen, BPH

from coldtype.time import Frame, Timeline
from coldtype.renderable import renderable
from coldtype.renderable.animation import animation

from coldtype.blender.render import blend_source

try:
    import bpy
except ImportError:
    bpy = None
    pass

def b3d(collection, callback=None, plane=False, dn=False):
    pen_mod = None
    if callback and not callable(callback):
        pen_mod = callback[0]
        callback = callback[1]

    def _cast(pen:DATPen):
        if bpy and pen_mod:
            pen_mod(pen)
        pen.add_data("b3d", dict(
            collection=collection,
            callback=callback))
    return _cast


def b3d_mod(callback):
    def _cast(pen:DATPen):
        if bpy:
            callback(pen)
    return _cast


class b3d_mods():
    @staticmethod
    def center(r:Rect):
        return b3d_mod(lambda p:
            p.translate(-r.w/2, -r.h/2))
    
    def centerx(r:Rect):
        return b3d_mod(lambda p:
            p.translate(-r.w/2, 0))
    
    def centery(r:Rect):
        return b3d_mod(lambda p:
            p.translate(0, -r.h/2))


def walk_to_b3d(result:DATPens, dn=False):
    def walker(p:DATPen, pos, data):
        if pos == 0:
            bdata = p.data.get("b3d")
            if bdata:
                coll = BPH.Collection(bdata["collection"])

                if bdata.get("plane"):
                    bp = p.cast(BlenderPen).draw(coll, plane=True)
                else:
                    bp = p.cast(BlenderPen).draw(coll, dn=dn)
                
                if bdata.get("callback"):
                    bdata.get("callback")(bp)

                bp.hide(not p._visible)
    result.walk(walker)


class b3d_renderable(renderable):
    pass


class b3d_animation(animation):
    def __init__(self, rect=(1080, 1080), **kwargs):
        self.func = None
        self.name = None
        self.current_frame = -1
        super().__init__(rect=rect, **kwargs)

        if bpy:
            bpy.data.scenes[0].frame_end = self.t.duration-1
            # don't think this is totally accurate but good enough for now
            if isinstance(self.t.fps, float):
                bpy.data.scenes[0].render.fps = round(self.t.fps)
                bpy.data.scenes[0].render.fps_base = 1.001
            else:
                bpy.data.scenes[0].render.fps = self.t.fps
                bpy.data.scenes[0].render.fps_base = 1
    
    def post_read(self):
        super().post_read()
        if bpy:
            bpy.data.scenes[0].render.filepath = str(self.blender_output_dir()) + "/"
    
    def blender_output_dir(self):
        output_dir = self.output_folder / "_blender"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def blender_render(self, file, blend_file, artifacts, samples=4):
        output_dir = self.blender_output_dir()
        for a in artifacts[:]:
            if a.render == self:
                blend_source(
                    file,
                    blend_file,
                    a.i,
                    output_dir,
                    samples=samples)
        os.system("afplay /System/Library/Sounds/Pop.aiff")
    
    def blender_render_frame(self, file, blend_file, fi, samples=4):
        blend_source(file, blend_file, fi, self.blender_output_dir(), samples)
    
    def blender_rendered_preview(self):
        if bpy: return
        
        from coldtype.img.skiaimage import SkiaImage
        
        @animation(self.rect, timeline=self.timeline, preview_only=1, sort=1000)
        def blender_preview(f):
            try:
                out = self.blender_output_dir()
                return SkiaImage(out / "{:04d}.png".format(f.i))
            except:
                pass
        
        return blender_preview


if __name__ == "<run_path>":
    from coldtype.text.composer import StSt, Font
    from coldtype.color import hsl

    fnt = Font.Cacheable("~/Type/fonts/fonts/PappardelleParty-VF.ttf")

    @b3d_renderable()
    def draw_bg(r):
        return DATPens([
            (DATPen(r.inset(0, 0)).f(hsl(0.85, 1, 0.7))
                .tag("BG2")
                .chain(b3d("Text", plane=1)))])
    
    @b3d_animation(timeline=Timeline(60, 30), bg=0, layer=1, rstate=1)
    def draw_dps(f, rs):
        if bpy:
            bpy.data.objects['Light'].rotation_euler[2] = f.e("l", rng=(0, math.radians(360)), to1=0)
            
            centroid = BPH.AddOrFind("Centroid",
                lambda: bpy.ops.object.empty_add(type="PLAIN_AXES"))
            centroid.location = (5.4, 5.4, 0)
            centroid.rotation_euler[2] = f.e("l", rng=(0, math.radians(360)), to1=0)

        if False: # if you want to render in a multi-plexed fashion
            if not bpy and not rs.previewing:
                draw_dps.blender_render_frame("scratch.blend", f.i)

        txt = (StSt("ABCDEFG", fnt, 330, palette=0)
            .align(f.a.r)
            .collapse()
            .map(lambda i, p: p.explode())
            .collapse()
            .pmap(lambda i,p: p
                .declare(fa:=f.adj(-i*1))
                .cond(p.ambit().y > 570, lambda pp:
                    pp.translate(0, fa.e("seio", 2, rng=(50, 0))))
                .cond(p.ambit().mxy < 490, lambda pp:
                    pp.translate(0, fa.e("seio", 2, rng=(-50, 0))))
                .tag(f"Hello{i}")
                .chain(b3d_mods.center(f.a.r))
                .chain(b3d("Text", lambda bp: bp
                    .extrude(fa.e("eeio", 1, rng=(0.25, 2)))
                    .metallic(1)))))
        
        return DATPens([txt])
    
    previewer = draw_dps.blender_rendered_preview()
    
    #def build(artifacts):
    #    draw_dps.blender_render("scratch.blend", artifacts[:1], samples=8)

    #def release(artifacts):
    #    draw_dps.blender_render("scratch.blend", artifacts, samples=8)