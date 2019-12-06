import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

#from coldtype import *

from coldtype.color import normalize_color
from coldtype.geometry import Rect
from coldtype.text import *

from enum import Enum
from random import random
from defcon import Font
import json
import mido
import math
import re

import easing_functions as ef

VIDEO_OFFSET = 86313 # why is this?

easer_ufo = Font(str(Path(__file__).parent.joinpath("easers.ufo")))

eases = dict(
    qei=ef.QuadEaseIn,
    qeo=ef.QuadEaseOut,
    qeio=ef.QuadEaseInOut,
    eei=ef.ExponentialEaseIn,
    eeo=ef.ExponentialEaseOut,
    eeio=ef.ExponentialEaseInOut,
    sei=ef.SineEaseIn,
    seo=ef.SineEaseOut,
    seio=ef.SineEaseInOut,
    beo=ef.BounceEaseOut,
    beio=ef.BounceEaseInOut,
    eleo=ef.ElasticEaseOut,
    elei=ef.ElasticEaseIn,
    )


def ease(style, x):
    if style == "linear":
        return x
    e = eases.get(style)
    if e:
        return e().ease(x)
    else:
        if style in easer_ufo:
            p, tangent = DATPen().glyph(easer_ufo[style]).point_t(t=x)
            return p[1]/1000
        else:
            raise Exception("No easing function with that mnemonic")


def loop(t, times=1, easefn="qeio"):
    lt = t*times*2
    ltf = math.floor(lt)
    ltc = math.ceil(lt)
    if ltc % 2 != 0: # looping back
        lt = 1 - (ltc - lt)
    else: # looping forward
        lt = ltc - lt
    
    easer = easefn
    try:
        iter(easefn) # is-iterable
        if len(easefn) > ltf:
            easer = easefn[ltf]
        elif len(easefn) == 2:
            easer = easefn[ltf % 2]
        elif len(easefn) == 1:
            easer = easefn[0]
    except TypeError:
        pass
    
    if isinstance(easer, str):
        return ease(easer, lt)
    else:
        return easer(lt)


def to_frames(seconds, fps):
    frames = int(round(float(seconds)*fps))
    if frames >= VIDEO_OFFSET:
        frames -= VIDEO_OFFSET
    return frames


class Marker():
    def __init__(self, fps, marker):
        self.marker = marker
        self.start = to_frames(marker.get("start"), fps)
        self.end = to_frames(marker.get("end"), fps)


class ClipType(Enum):
    ClearScreen = "ClearScreen"
    NewLine = "NewLine"
    Isolated = "Isolated"
    JoinPrev = "JoinPrev"


class ClipFlags(Enum):
    FadeIn = "FadeIn"
    FadeOut = "FadeOut"


class Clip():
    def __init__(self, clip, fps=None, markers=[], idx=None, track=0):
        self.idx = idx
        self.clip = clip
        self.styles = []
        self.position = 1
        self.joined = False
        self.joinPrev = None
        self.joinNext = None
        self.track = track
        self.group = None

        if isinstance(clip, dict):
            try:
                self.text, self.transform = clip.get("name").split("|||")
                try:
                    self.transform = eval(f"dict({self.transform})")
                except ValueError:
                    print("Could not eval transform spec")
                    self.transform = dict()
            except ValueError:
                self.text = clip.get("name")
                self.transform = dict()
            
            self.start = to_frames(clip.get("start"), fps)
            self.end = to_frames(clip.get("end"), fps)
            self.inpoint = to_frames(clip.get("inPoint"), fps)
            self.outpoint = to_frames(clip.get("outPoint"), fps)
            self.duration = self.end - self.start
            self.flags = {}

            self.type = ClipType.Isolated
            if self.text.startswith("*"):
                self.text = self.text[1:]
                self.type = ClipType.ClearScreen
            elif self.text.startswith("≈"):
                self.text = self.text[1:]
                self.type = ClipType.NewLine
            elif self.text.startswith("+"):
                self.text = self.text[1:]
                self.type = ClipType.JoinPrev
            
            if self.text.startswith("ƒ"):
                r = r"^([0-9]+)ƒ"
                self.text = self.text[1:]
                value = 3
                match = re.match(r, self.text)
                if match:
                    value = int(match[1])
                    self.text = re.sub(r, "", self.text)
                self.flags[ClipFlags.FadeIn] = value
            
            elif self.text.endswith("ƒ"):
                self.flags[ClipFlags.FadeOut] = 3

            for m in markers:
                if self.inpoint <= m.start and self.outpoint > m.end:
                    self.type = ClipType.NewLine #ClipType.ClearScreen
    
    def addJoin(self, clip, direction):
        if direction == -1:
            self.joinPrev = clip
        elif direction == 1:
            self.joinNext = clip
    
    def joinStart(self):
        if self.joinPrev:
            return self.joinPrev.joinStart()
        else:
            return self.start
    
    def joinEnd(self):
        if self.joinNext:
            return self.joinNext.joinEnd()
        else:
            return self.end
    
    def textForIndex(self, index):
        txt = self.text
        try:
            txt = self.text.split("/")[index]
        except:
            txt = self.text.split("/")[-1]
        return txt, self.addSpace

    def ftext(self):
        txt = self.text
        if self.type == ClipType.Isolated:
            return " " + txt
        else:
            return txt
    
    def __repr__(self):
        return "<TC:({:s}/{:04d}/{:04d}\"{:s}\")>".format([" -1", "NOW", " +1"][self.position+1], self.start, self.end, self.text)


class Timeline():
    def __init__(self, duration, fps=30, storyboard=[0], workareas=None):
        self.fps = fps
        self.duration = round(duration)
        self.storyboard = storyboard
        if len(self.storyboard) == 0:
            self.storyboard.append(0)
        self.storyboard.sort()
        if workareas:
            self.workareas = workareas
        else:
            self.workareas = [range(0, self.duration+1)]
    
    def __str__(self):
        return "<Timeline:{:04d}f@{:02.2f}fps>".format(self.duration, self.fps)


class AnimationFrame():
    def __init__(self, index, animation, filepath, layers):
        self.i = index
        self.a = animation
        self.filepath = filepath
        self.layers = layers

    def __repr__(self):
        return f"<AnimationFrame {self.i}>"

class Animation():
    def __init__(self, render, rect=Rect(0, 0, 1920, 1080), timeline=None, bg=0, layers=None, watches=[]):
        self.render = render
        self.rect = Rect(rect)
        self.r = self.rect
        self.cache = {}
        self.layers = layers
        self.watches = [str(w.expanduser().resolve()) for w in watches]

        if isinstance(timeline, Path):
            if str(timeline).endswith(".json"):
                jsondata = json.loads(timeline.read_text())
                meta = jsondata.get("metadata")
                fps = 1 / meta.get("frameRate")
                duration = int(round(int(meta.get("duration"))/int(meta.get("timebase"))))
                storyboard = []
                tof = lambda s: int(round(float(s)*fps))
                for m in jsondata.get("storyboard"):
                    storyboard.append(tof(m.get("start")))
                workareas = []
                workareas.append(
                    range(
                        max(0, tof(meta.get("inPoint"))),
                        tof(meta.get("outPoint"))+1
                        ))
                self.jsonfile = timeline
                self.timeline = Timeline(
                    duration,
                    fps,
                    storyboard=storyboard,
                    workareas=workareas
                )
                self.clipGroupsByTrack = []
                for tidx, track in enumerate(jsondata.get("tracks")):
                    markers = [Marker(fps, m) for m in track.get("markers")]
                    clips = track.get("clips")
                    gcs = self.groupedClips([Clip(c, fps=fps, markers=markers, track=tidx) for c in clips])
                    self.clipGroupsByTrack.append(gcs)
        elif isinstance(timeline, Timeline):
            self.timeline = timeline
        elif timeline:
            self.timeline = Timeline(timeline, 30)
        else:
            self.timeline = Timeline(1, 30)
        
        self.t = self.timeline # alias
        self.bg = normalize_color(bg)
    
    def groupedClips(self, tcs):
        groups = []
        group = []
        last_clip = None
        for idx, tc in enumerate(tcs):
            if tc.type == ClipType.ClearScreen:
                if len(group) > 0:
                    groups.append(ClipGroup(self, len(groups), group))
                group = []
            elif tc.type == ClipType.JoinPrev:
                if last_clip:
                    last_clip.addJoin(tc, +1)
                    tc.addJoin(last_clip, -1)
            group.append(tc)
            last_clip = tc
        if len(group) > 0:
            groups.append(ClipGroup(self, len(groups), group))
        return groups
    
    def progress(self, i, cyclic=False):
        if cyclic:
            a = (i / (self.timeline.duration/2))
            if a < 1:
                return a
            else:
                return 2 - a
        else:
            return i / self.timeline.duration
    
    def prg(self, i, c=False):
        return self.progress(i, cyclic=c)
    
    def trackClipGroupForFrame(self, track_idx, frame_idx, styles=None):
        groups = self.clipGroupsByTrack[track_idx]
        for group in groups:
            if group.start <= frame_idx and group.end > frame_idx:
                style_groups = None
                if styles:
                    style_groups = []
                    for style in styles:
                        style_groups.append(self.trackClipGroupForFrame(style, frame_idx))
                return group.position(frame_idx, style_groups)

group_pens_cache = {}

class ClipGroup():
    def __init__(self, animation, index, clips):
        self.index = index
        self.clips = clips
        self.start = clips[0].start
        self.end = clips[-1].end
        self.track = clips[0].track
        self.animation = animation

        for idx, clip in enumerate(clips):
            clip.idx = idx
            clip.group = self
    
    def styles(self):
        all_styles = set()
        for clip in self.clips:
            for style in clip.styles:
                all_styles.add(style)
        return all_styles
    
    def lines(self):
        lines = []
        line = []
        for clip in self.clips:
            if clip.type == ClipType.NewLine:
                lines.append(line)
                line = [clip]
            else:
                line.append(clip)
        if len(line) > 0:
            lines.append(line)
        return lines
    
    def position(self, idx, styles):
        for clip in self.clips:
            clip.joined = False
        for clip in self.clips:
            clip.styles = []
            if styles:
                for style in styles:
                    if style:
                        for style_clip in style.clips:
                            if clip.start >= style_clip.start and clip.end <= style_clip.end:
                                clip.styles.append(style_clip.ftext().strip())
            if clip.start > idx:
                clip.position = 1
            elif clip.start <= idx and clip.end > idx:
                clip.position = 0
                before_clip = clip
                while before_clip.type == ClipType.JoinPrev:
                    before_clip = self.clips[before_clip.idx-1]
                    before_clip.joined = True
                try:
                    after_clip = self.clips[clip.idx+1]
                    while after_clip.type == ClipType.JoinPrev:
                        after_clip.joined = True
                        after_clip = self.clips[after_clip.idx+1]
                except IndexError:
                    pass
            else:
                clip.position = -1
        return self
    
    def currentSyllable(self):
        for clip in self.clips:
            if clip.position == 0:
                return clip
    
    def currentWord(self):
        for clip in self.clips:
            if clip.position == 0:
                clips = [clip]
                before_clip = clip
                # walk back
                while before_clip.type == ClipType.JoinPrev:
                    before_clip = self.clips[before_clip.idx-1]
                    clips.insert(0, before_clip)
                # walk forward
                try:
                    after_clip = self.clips[clip.idx+1]
                    while after_clip.type == ClipType.JoinPrev:
                        clips.append(after_clip)
                        after_clip = self.clips[after_clip.idx+1]
                except IndexError:
                    pass
                return clips
    
    def currentLine(self):
        for line in self.lines():
            for clip in line:
                if clip.position == 0:
                    return line

    def sibling(self, clip, direction, wrap=False):
        try:
            if clip.idx + direction < 0 and not wrap:
                return None
            return self.clips[clip.idx + direction]
        except IndexError:
            return None
    
    def text(self):
        txt = ""
        for c in self.clips:
            if c.type == ClipType.ClearScreen:
                pass
            elif c.type == ClipType.Isolated:
                txt += "( )"
            elif c.type == ClipType.JoinPrev:
                txt += "|"
            elif c.type == ClipType.NewLine:
                txt += "/(\\n)/"
            txt += c.text
        return txt
        #return "|".join([(c.text + "/") if c.eol else c.text for c in self.clips])
    
    def ClearCache():
        global group_pens_cache
        group_pens_cache = {}
    
    def pens(self, render_clip_fn, rect, graf_style, fit=None, cache=True):
        global group_pens_cache
        
        if cache:
            if group_pens_cache.get(self.track, dict()).get(self.index):
                return group_pens_cache[self.track][self.index]
        
        group_pens = []
        lines = []
        for idx, _line in enumerate(self.lines()):
            slugs = []
            for clip in _line:
                slugs.append(render_clip_fn(clip))
            lines.append(slugs)
        lockups = []
        for line in lines:
            lockup = Lockup(line, preserveLetters=True, nestSlugs=True)
            if fit:
                lockup.fit(fit)
            lockups.append(lockup)
        graf = Graf(lockups, rect, graf_style)
        pens = graf.pens().align(rect)
        for pens in pens.pens:
            for pen in pens.pens:
                pen.removeOverlap()
            group_pens.append(pens)
        track_cache = group_pens_cache.get(self.track, dict())
        track_cache[self.index] = group_pens
        group_pens_cache[self.track] = track_cache
        return group_pens
    
    def iterate_pens(self, pens):
        for idx, line in enumerate(self.lines()):
            _pens = pens[idx]
            for cidx, clip in enumerate(line):
                p = _pens.pens[cidx].copy()
                yield idx, clip, p
    
    def __repr__(self):
        return "<ClipGroup {:04d}-{:04d} \"{:s}\">".format(self.start, self.end, self.text())
    
    def __hash__(self):
        return self.text()


def s_to_f(s, fps):
    return math.floor(s*fps)


def midi_to_frames(f, fps, bpm=120, length=None, loop_length=None):
    mid = mido.MidiFile(f)
    time = 0
    cumulative_time = 0
    events = []
    open_notes = {}
    for i, track in enumerate(mid.tracks):
        for msg in track:
            delta_s = mido.tick2second(msg.time, mid.ticks_per_beat, mido.bpm2tempo(bpm))
            cumulative_time += delta_s
            if msg.type == "note_on":
                open_notes[msg.note] = cumulative_time
            elif msg.type == "note_off":
                o = open_notes.get(msg.note)
                open_notes[msg.note] = None
                events.append((msg.note, s_to_f(o, fps), s_to_f(cumulative_time, fps)))
    
    if length and loop_length:
        looped = []
        loop_count = math.floor(loop_length / length)
        bps = bpm / 60
        offset = bps * fps
        for l in range(1, round(loop_count)):
            for (note, start, end) in events:
                looped.append((note, int(round(start+offset*l*length)), int(round(end+offset*l*length))))
        events.extend(looped)
    return events

def sibling(root, file):
    return Path(root).parent.joinpath(file)

if __name__ == "__main__":
    print("qeio", ease("qeio", 0.25))
    print("b1o", ease("b1o", 1))