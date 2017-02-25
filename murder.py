#!/usr/local/bin/pgzrun
"""Death at Sea.

A murder adventure game.

"""
import re
import sys
import pickle
import pgzero.loaders
import datetime
from pathlib import Path
from collections import OrderedDict, defaultdict
from abc import ABCMeta, abstractmethod
import pygame.transform
from itertools import cycle, chain
import time


has_screen = False
basedir = Path(pgzero.loaders.root)


# This is all the save game state
things_known = set()
all_done = {}


class DialogueMatch:
    """Represent the steps that happen when a dialogue choice is chosen."""
    def __init__(self, conds=None):
        self.conds = conds or []

    def add_condition(self, cond, steps):
        newsteps = []
        for action, text in steps:
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text.strip())
            newsteps.append((action, text))
        self.conds.append((frozenset(cond), newsteps))

    def get_steps(self, done):
        for cond, steps in reversed(self.conds):
            if things_known.issuperset(cond):
                is_done = cond in done
                return steps, is_done
        return None, None

    def set_done(self, done):
        for cond, steps in reversed(self.conds):
            if things_known.issuperset(cond):
                done.add(cond)
                return

    def __repr__(self):
        return '{}({!r})'.format(
            type(self).__name__,
            self.conds
        )


# Choices that correspond to goodbyes
GOODBYES = {'Bye', 'Done'}


class DialogueMenu:
    """Represent a menu of dialogue."""

    def __init__(self, path):
        self.choices = OrderedDict()
        self.path = path

    @property
    def done(self):
        return all_done.setdefault(self.path, defaultdict(set))

    def add_choice(self, key, cond, steps):
        if key in GOODBYES:
            if steps[-1][0] != 'EXIT':
                steps.append(('EXIT', ''))
        try:
            match = self.choices[key]
        except KeyError:
            match = self.choices[key] = DialogueMatch()
        match.add_condition(cond, steps)

    def get_enter(self):
        enter = self.choices.get('enter')
        if enter:
            return enter.get_steps(set())[0]
        return None

    def get_choices(self):
        """Get a list of (choice, done) dialogue choices."""
        opts = []
        for k, v in self.choices.items():
            if k == 'enter':
                continue
            if not isinstance(v, DialogueMatch):
                continue
            steps, done = v.get_steps(self.done[k])
            if steps is not None:
                opts.append((k, done))
        return opts

    def get_steps(self, choice):
        dm = self.choices[choice]
        steps, done = dm.get_steps(self.done)
        if not done and choice not in GOODBYES:
            dm.set_done(self.done[choice])
        return steps

    def validate(self):
        for m in self.choices.values():
            for cond, steps in m.conds:
                for action, value in steps:
                    if action == 'EXIT':
                        return
        raise ValueError("No EXIT action in %r" % self)

    def __bool__(self):
        return bool(self.choices)

    def __repr__(self):
        return '{}({!r}) = {!r}'.format(
            type(self).__name__,
            self.path,
            dict(self.choices)
        )


def load_dialogue(fname):
    """Load the dialogue from the given file."""
    path = basedir / 'dialogue' / '{}.txt'.format(fname)
    patterns = DialogueMenu(fname)
    key = None
    cond = None
    steps = []
    with path.open(encoding='utf8') as f:
        for lineno, l in enumerate(f, start=1):
            l = l.strip()
            mo = re.match(r'^\[(.*)\](\??)(?: +if +(.*))?$', l)
            if mo:
                if key:
                    patterns.add_choice(key, cond, steps)
                    steps = []
                    cond = None
                key, qmark, ifs = mo.groups()
                cond = set()
                if qmark:
                    cond.add(key)
                if ifs:
                    for t in ifs.split(','):
                        t = t.strip()
                        if t.startswith('.'):
                            t = fname + t
                        cond.add(t)
                cond = frozenset(cond)
                continue
            mo = re.match('^([A-Z]+): *(.*)', l)
            if mo:
                action, value = mo.groups()
                if action not in ('YOU', 'THEY', 'EXIT', 'LEARN', 'FORGET', 'EXEC'):
                    raise ValueError(
                        'invalid key %r, %s, line %d' % (action, path, lineno)
                    )
                value = value.strip()
                if action in ('LEARN', 'FORGET') and value.startswith('.'):
                    value = fname + value
                steps.append((action, value))
            else:
                action, text = steps[-1]
                if text:
                    text += '\n'
                text += l
                steps[-1] = action, text

    if key:
        patterns.add_choice(key, cond, steps)

    if patterns:
        patterns.validate()

    return patterns or None

TITLE = "A Death at Sea"
WIDTH = 800
HEIGHT = 600
FONT = "travelling_typewriter"

# All NPCs are anchored at center bottom
CANC = ('center', 'bottom')

bridge = Actor('bridge')
bridge.name = "Bridge"

deck1 = Actor('deck1')
deck1.name = "On Deck"
deck1.music = "deck1"

deck2 = Actor('deck2')
deck2.name = "Lounge"
deck2.music = "deck2"

deck3_start = Actor('deck3-start')
deck3 = Actor('deck3-later')
deck3_start.name = deck3.name = "First-class Cabins"
deck3.music = "deck3"

deck4 = Actor('deck4')
deck4.name = "Second-class Cabins"
deck4.music = "deck4"

baines_room = Actor('baines-room')
baines_room.name = "Cabin 35"

cheshire_room = Actor('cheshire-room')
cheshire_room.name = "Cabin 37"
cheshire_room.music = "deck3"

luggage_room = Actor('luggage-room')
luggage_room.name = "Luggage Room"
luggage_room.music = "deck4"

kitty_room = Actor('kitty-room')
kitty_room.name = "Cabin 46"
kitty_room.music = "deck4"

kitty = Actor('kitty-sitting', anchor=CANC)
kitty.real_x = 300
kitty.name = "Kitty Morgan"

cheshire = Actor('lord-cheshire', anchor=CANC)
cheshire.real_x = 1200
cheshire.name = "Lord Cheshire"

manx = Actor('doctor-manx', anchor=CANC)
manx.real_x = 1000
manx.name = "Doctor Manx"

mrs_manx = Actor('mrs-manx', anchor=CANC)
mrs_manx.real_x = 940
mrs_manx.name = "Mrs. Manx"

kibble = Actor('donnie-kibble', anchor=CANC)
kibble.real_x = 400
kibble.name = "Donnie Kibble"

pussy = Actor('pussy-galumps', anchor=CANC)
pussy.real_x = 300
pussy.name = "Pussy Galumps"

katerina = Actor('katerina-la-gata', anchor=CANC)
katerina.real_x = 400
katerina.name = "Katerina la Gata"

calico = Actor('calico-croker', anchor=CANC)
calico.real_x = 670
calico.name = "Calico Croker"

captain = Actor('captain', anchor=CANC)
captain.real_x = 250
captain.name = "The Captain"

lift = Actor('lift', pos=(80, 400))


# Maximum walk speed
MAX_WALK = 3
billy = Actor(
    'billy-standing',
    anchor=CANC,
    pos=(100, 190)
)
billy.real_x = 100
billy.in_lift = False
billy.dialogue_with = None
billy.dir = None

decks = [bridge, deck1, deck2, deck3, deck4]
bridge.actors = [captain]
deck1.actors = [katerina]
deck2.actors = [cheshire, manx, mrs_manx, kibble, pussy]
deck3_start.actors = [captain]
deck3.actors = [calico]
deck4.actors = []
baines_room.actors = []
cheshire_room.actors = []
kitty_room.actors = [kitty]
luggage_room.actors = []


class Interactable(metaclass=ABCMeta):
    W = 35
    def __init__(self, pos):
        self.pos = pos

    @abstractmethod
    def caption(self):
        pass

    @abstractmethod
    def use(self):
        pass

    def is_next_to(self):
        l = self.pos - self.W
        r = self.pos + self.W
        return l < billy.real_x < r


class InteractableIf(Interactable):
    def __init__(self, pos, must_know=frozenset()):
        self.pos = pos
        self.must_know = frozenset(must_know)

    def is_next_to(self):
        return super().is_next_to() and things_known.issuperset(self.must_know)


class Door(InteractableIf):
    def __init__(
            self,
            pos,
            dest,
            dest_pos,
            caption=None,
            must_know=frozenset()):
        super().__init__(pos, must_know)
        self.dest = dest
        self.dest_pos = dest_pos
        self._caption = caption

    def caption(self):
        return self._caption or "Enter {}".format(self.dest.name)

    def use(self):
        enter(self.dest, self.dest_pos)


current_music = None


def enter(deck, pos=None):
    """Enter the given deck/room at the given x pos."""
    global current_deck, viewport, current_music
    if has_screen:
        screen.clear()
        screen.draw.text(
            current_deck.name,
            topright=(WIDTH - 10, 10),
            fontname=FONT,
            fontsize=20,
            color='#cccccc'
        )
    current_deck = deck
    if pos is not None:
        billy.real_x = pos
    if current_deck.width < WIDTH:
        vx = -(WIDTH - current_deck.width) // 2
    else:
        vx = min(current_deck.width - WIDTH, max(billy.real_x - WIDTH // 2, 0))
    viewport = vx, viewport[1]
    try:
        music_name = deck.music
    except AttributeError:
        music.stop()
    else:
        if current_music != deck.music:
            current_music = music_name
            music.play(music_name)
            music.set_volume(0.6)


class Lift(InteractableIf):
    W = 35

    def __init__(self, pos=85, must_know=frozenset()):
        super().__init__(pos, must_know)

    def caption(self):
        return "Use lift"

    def use(self):
        global current_music
        things_known.add('Lift')
        billy.in_lift = True
        current_music = 'elevator'
        music.play('elevator')
        music.set_volume(0.3)


class Observation(InteractableIf):
    def __init__(self, pos, name, dialogue, must_know=frozenset()):
        super().__init__(pos, must_know)
        self.name = name
        self._dialogue_file = dialogue
        self.dialogue = load_dialogue(dialogue)

    def use(self):
        billy.dialogue_with = self
        DialogueChoices(self.dialogue).start()

    def caption(self):
        return "Examine {}".format(self.name)


bridge.objects = [Lift()]
deck1.objects = [
    Lift(),
    Observation(1065, 'Life Ring', 'life-ring', {'Wrote note', 'Was on deck'}),
    Observation(1185, 'Fire Hose', 'fire-hose', {'Wrote note', 'Was on deck'}),
]
deck2.objects = [Lift()]
deck3_start.objects = [
    Lift(must_know={'Two Glasses', 'Luggage key'}),
    Door(310, baines_room, 55, must_know={'Buster Baines'}),
]
deck3.objects = [
    Lift(),
    Door(875, cheshire_room, 405, must_know={"Cheshire's Room"}),
]
deck4.objects = [
    Lift(),
    Door(575, kitty_room, 405, must_know={"Kitty Morgan"}),
    Door(850, luggage_room, 55, must_know={"Luggage"}),
]
baines_room.objects = [
    Door(55, deck3_start, 310, "To the corridor"),
    Observation(165, 'Two Glasses', 'two-glasses'),
    Observation(300, 'Corpse', 'corpse'),
]
cheshire_room.objects = [
    Door(405, deck3, 875, "To the corridor"),
    Observation(280, 'Photo', 'photo', {"Katerina la Gata"}),
    Observation(225, 'Document', 'document'),
]
kitty_room.objects = [
    Door(405, deck4, 575, "To the corridor"),
    Observation(235, 'Newspaper', 'newspaper', {'Newspaper'}),
]
luggage_room.objects = [
    Door(55, deck4, 850, "To the corridor"),
    Observation(180, 'Trunk', 'trunk')
]


all_deck_objects = [
    bridge, deck1, deck2, deck3, deck4, baines_room, cheshire_room, kitty_room,
    luggage_room, deck3_start
]

deck_num = 3
current_deck = deck3_start

viewport = (0, 0)

for d in all_deck_objects:
    d.level_width = d.width
deck1.level_width -= 312
bridge.level_width = 425
luggage_room.level_width = 225


def reload_dialogue():
    """Load all dialogue.

    Press F5 to reload all when changed.

    """
    calico.dialogue = load_dialogue('calico')
    captain.dialogue = load_dialogue('captain')
    cheshire.dialogue = load_dialogue('cheshire')
    kibble.dialogue = load_dialogue('kibble')
    katerina.dialogue = load_dialogue('katerina')
    kitty.dialogue = load_dialogue('kitty')
    manx.dialogue = load_dialogue('manx')
    mrs_manx.dialogue = load_dialogue('mrs-manx')
    pussy.dialogue = load_dialogue('pussy')
    if billy.dialogue_with:
        start_dialogue(billy.dialogue_with)
    for d in all_deck_objects:
        for o in d.objects:
            if isinstance(o, Observation):
                o.dialogue = load_dialogue(o._dialogue_file)



reload_dialogue()
game_screen = None

TITLE_BAR = Rect(0, 0, WIDTH, 50)
PANEL = Rect(0, 50, WIDTH, 145)
TEXT_AREA = Rect(0, 195, WIDTH, HEIGHT - 195)
BLACK = 0, 0, 0



def draw():
    global has_screen
    has_screen = True
    if game_screen:
        return game_screen.draw()

    if billy.in_lift:
        draw_lift()
    else:
        draw_deck()


def draw_lift():
    screen.clear()
    lift.draw()
    screen.draw.text(
        'Deck %s: %s' % (deck_num or "A", current_deck.name),
        midleft=(lift.x + 60, lift.y),
        fontname=FONT,
        fontsize=20,
        color='#cccccc'
    )


def clear_text_area():
    screen.draw.filled_rect(TEXT_AREA, BLACK)


def draw_deck():
    screen.draw.filled_rect(PANEL, BLACK)
    vx, vy = viewport
    current_deck.left = -vx
    current_deck.top = 50
    current_deck.draw()
    for a in current_deck.actors:
        a.pos = a.real_x - vx, 186
        a.draw()
    billy.x = billy.real_x - vx
    billy.draw()


action_caption = None


def update_action_caption():
    global action_caption
    new_caption = None
    for a in current_deck.actors:
        if billy.colliderect(a):
            new_caption = 'Talk to %s' % a.name
            break
    else:
        for o in current_deck.objects:
            if o.is_next_to():
                new_caption = o.caption()
                break
    if new_caption != action_caption:
        clear_text_area()
        if new_caption:
            draw_caption(new_caption)
        action_caption = new_caption


def draw_caption(caption):
    screen.draw.text(
        caption,
        midtop=(WIDTH // 2, 220),
        fontname=FONT,
        fontsize=20,
        color='#cccccc'
    )


def update():
    if not billy.dialogue_with and not game_screen:
        move_billy()
        update_action_caption()


def move_billy():
    global frame, viewport
    if keyboard.left:
        billy.real_x -= MAX_WALK
        if billy.real_x < 30:
            billy.real_x = 30
            stop_billy_anim()
        else:
            play_billy_anim(billy_walk_l)
            billy.dir = 'l'
    elif keyboard.right:
        billy.real_x += MAX_WALK
        if billy.real_x >= current_deck.level_width - 30:
            billy.real_x = current_deck.level_width - 30
            stop_billy_anim()
        else:
            play_billy_anim(billy_walk_r)
            billy.dir = 'r'
    else:
        stop_billy_anim()

    if current_deck.width > WIDTH:
        vx, vy = viewport
        l_edge = WIDTH // 3
        r_edge = l_edge * 2
        if billy.real_x > vx + r_edge:
            vx = min(billy.real_x - r_edge, current_deck.width - WIDTH)
        if billy.real_x < vx + l_edge:
            vx = max(billy.real_x - l_edge, 0)
        viewport = vx, vy


billy_walk_r = [
    images.billy_walking_r_0,
    images.billy_walking_r_1,
    images.billy_walking_r_2,
    images.billy_walking_r_3,
    images.billy_walking_r_4,
    images.billy_walking_r_5,
    images.billy_walking_r_6,
    images.billy_walking_r_7,
]
billy_walk_l = [
    pygame.transform.flip(im, True, False)
    for im in billy_walk_r
]
billy.anim = None


def play_billy_anim(frames):
    if billy.anim is frames:
        return
    billy.anim = frames
    billy.frames = cycle(frames)
    next_frame()
    clock.schedule_interval(next_frame, 0.07)
    sounds.footsteps.play(-1)


def stop_billy_anim():
    billy.anim = None
    clock.unschedule(next_frame)
    if billy.dir and not isinstance(billy.image, str):
        billy.image = 'billy-standing-' + billy.dir
    sounds.footsteps.stop()


def next_frame():
    billy.image = next(billy.frames)


TWEEN = 'accel_decel'


def on_key_down(key):
    if key == keys.F5:
        reload_dialogue()
        return
    if billy.dialogue_with:
        on_key_down_dialogue(key)
    else:
        on_key_down_walk(key)


def on_key_down_walk(key):
    global deck_num, current_deck, viewport
    if billy.in_lift:
        if key == keys.RETURN:
            billy.in_lift = False
            enter(current_deck)
        elif key == keys.UP and deck_num > 0:
            deck_num -= 1
            current_deck = decks[deck_num]
            animate(lift, y=100 * deck_num + 100, tween=TWEEN)
            clock.schedule_unique(ding, 0.8)
        elif key == keys.DOWN and deck_num < len(decks) - 1:
            deck_num += 1
            current_deck = decks[deck_num]
            animate(lift, y=100 * deck_num + 100, tween=TWEEN)
            clock.schedule_unique(ding, 0.8)
    else:
        if key == keys.UP:
            billy.image = 'billy-back'
            billy.dir = None
        elif key == keys.DOWN:
            billy.image = 'billy-standing'
            billy.dir = None
        elif key == keys.ESCAPE:
            show_menu()


def ding():
    sounds.ding.play()


def on_key_down_dialogue(key):
    if key == keys.UP:
        billy.dialogue_menu.up()
    elif key == keys.DOWN:
        billy.dialogue_menu.down()
    elif key == keys.RETURN:
        billy.dialogue_menu.select()
    elif key == keys.ESCAPE:
        back = getattr(billy.dialogue_menu, 'back', None)
        if back:
            back()


class DialogueChoices:
    def __init__(self, options, parent=None):
        self.options = options
        self.parent = parent

    def start(self):
        if self.parent is None:
            enter_steps = self.options.get_enter()
            if enter_steps:
                self.play_dialogue(enter_steps)
                return
        self.show()

    def show(self):
        self.choices = self.options.get_choices()
        if not self.choices:
            if self.parent:
                billy.dialogue_menu = self.parent
                return
            else:
                billy.dialogue_with = None
                billy.dialogue_menu = None
                clear_text_area()
                return
        billy.dialogue_menu = self

        for selected, (key, done) in enumerate(self.choices):
            if not done:
                self.selected = selected
                break
        else:
            self.selected = 0
        if len(self.choices) > self.MAX_SHOW:
            self.offset = min(
                max(0, self.selected - self.MAX_SHOW // 2),
                len(self.choices) - self.MAX_SHOW
            )
        else:
            self.offset = 0
        self.draw()

    MAX_SHOW = 11

    def draw(self):
        clear_text_area()
        choices = self.choices[self.offset:self.offset + self.MAX_SHOW]
        if self.offset > 0:
            screen.draw.text(
                '/\\',
                topleft=(30, 230),
                fontname=FONT,
                fontsize=14,
                color='#aaaaaa'
            )
        for i, opt in enumerate(choices):
            choice_num = i + self.offset
            key, is_done = opt
            if is_done:
                color = '#ff4444' if choice_num == self.selected else '#aa0000'
            else:
                color = '#aaaaaa' if choice_num != self.selected else 'white'
            screen.draw.text(
                key,
                bottomleft=(60, 260 + 30 * i),
                fontname=FONT,
                fontsize=20,
                color=color
            )
            if is_done:
                screen.draw.text(
                    '-' * int(len(key) * 1.6),
                    bottomleft=(60, 260 + 30 * i),
                    fontname=FONT,
                    fontsize=20,
                    color=color
                )
        if self.offset + self.MAX_SHOW < len(self.choices):
            screen.draw.text(
                '\/',
                bottomleft=(30, 240 + 30 * self.MAX_SHOW),
                fontname=FONT,
                fontsize=14,
                color='#aaaaaa'
            )

    def up(self):
        self.selected = (self.selected - 1) % len(self.choices)
        if self.selected < self.offset:
            self.offset = max(self.selected, 0)
        elif self.selected >= self.offset + self.MAX_SHOW:
            self.offset = min(self.selected, len(self.choices) - self.MAX_SHOW)
        self.draw()

    def down(self):
        self.selected = (self.selected + 1) % len(self.choices)
        if self.selected >= self.offset + self.MAX_SHOW:
            self.offset = min(self.selected - self.MAX_SHOW + 1, len(self.choices) - self.MAX_SHOW)
        elif self.selected < self.offset:
            self.offset = max(self.selected, 0)
        self.draw()

    def select(self):
        key, done = self.choices[self.selected]
        steps = self.options.get_steps(key)
        self.play_dialogue(steps)

    def play_dialogue(self, steps):
        billy.dialogue_menu = DialogueChat(steps, self)


class DialogueChat:
    def __init__(self, steps, parent):
        self.steps = steps[:]
        self.parent = parent
        self.select()

    def draw(self):
        clear_text_area()
        if self.action == 'YOU':
            color = '#cc4466'
            screen.draw.text(
                'Billy',
                bottomleft=(30, 230),
                fontname=FONT,
                fontsize=20,
                color=color
            )
        elif self.action == 'THEY':
            color = '#66cc44'
            screen.draw.text(
                billy.dialogue_with.name,
                bottomright=(WIDTH - 30, 230),
                fontname=FONT,
                fontsize=20,
                color=color
            )
        screen.draw.text(
            self.text,
            topleft=(30, 250),
            width=WIDTH - 60,
            fontname=FONT,
            fontsize=18,
            color='#cccccc'
        )
        screen.draw.text(
            "Continue",
            bottomright=(WIDTH - 30, HEIGHT - 30),
            fontname=FONT,
            fontsize=18,
            color='white'
        )

    def select(self):
        """Proceed to the next step."""
        while True:
            try:
                action, text = self.steps.pop(0)
            except IndexError:
                self.parent.show()
                return
            if action == 'LEARN':
                things_known.add(text)
                continue
            elif action == 'FORGET':
                things_known.discard(text)
                continue
            elif action == 'EXEC':
                exec(text, globals())
                continue
            elif action in ('YOU', 'THEY'):
                self.action, self.text = action, text
            break

        if action == 'EXIT':
            if billy.dialogue_menu is self or billy.dialogue_menu is self.parent:
                billy.dialogue_menu = None
                billy.dialogue_with = None
                clear_text_area()
                SaveMenu.autosave()
        else:
            self.draw()

    def up(self):
        """no-op."""

    def down(self):
        """no-op."""


def start_dialogue(character):
    """Start a dialogue with a character."""
    stop_billy_anim()
    things_known.add(character.name)  # Learn about this character
    try:
        dialogue = character.dialogue
    except AttributeError:
        return
    if not dialogue:
        return
    billy.dialogue_with = character
    DialogueChoices(dialogue).start()


def on_key_up(key):
    if billy.dialogue_with or billy.in_lift:
        return

    if key == keys.UP:
        for a in current_deck.actors:
            if billy.colliderect(a):
                start_dialogue(a)
                return
        for o in current_deck.objects:
            if o.is_next_to():
                o.use()
                return
    else:
        billy.image = 'billy-standing'



def show_menu():
    PauseMenu().show()


class GameMenu:
    def __init__(self):
        self.selected = 0

    def show(self):
        billy.dialogue_with = billy.dialogue_menu = self
        self.draw()

    def draw(self):
        clear_text_area()
        for i, opt in enumerate(self.choices):
            color = '#aaaaaa' if i != self.selected else 'white'
            screen.draw.text(
                opt,
                midtop=(WIDTH // 2, 260 + 30 * i),
                fontname=FONT,
                fontsize=20,
                color=color
            )

    def up(self):
        self.selected = (self.selected - 1) % len(self.choices)
        self.draw()

    def down(self):
        self.selected = (self.selected + 1) % len(self.choices)
        self.draw()

    def select(self):
        choice = self.choices[self.selected]
        self.draw()
        self.do(choice)

    def close(self):
        billy.dialogue_with = billy.dialogue_menu = None
        clear_text_area()


class PauseMenu(GameMenu):
    def __init__(self):
        super().__init__()
        self.choices = [
            'Load Game',
            'Save Game',
            'Quick-save & Exit'
        ]
        if not any(savesdir.glob('*.save')):
            del self.choices[:1]

    def do(self, choice):
        if choice == 'Load Game':
            LoadMenu().show()
        elif choice == 'Save Game':
            SaveMenu().show()
        else:
            SaveMenu.autosave()
            sys.exit(0)

    def back(self):
        self.close()


savesdir = basedir / 'saves'
AUTOSAVE_INTERVAL = 300  # seconds

class LoadMenu(GameMenu):
    def __init__(self):
        super().__init__()
        self.choices = []
        for p in sorted(savesdir.glob('*.save')):
            mtime = p.stat().st_mtime
            dt = datetime.datetime.fromtimestamp(mtime)
            name = '{}: saved {:%Y-%m-%d %H:%M}'.format(p.stem, dt)
            self.choices.append(name)

    def back(self):
        PauseMenu().show()

    def do(self, choice):
        if ':' in choice:
            choice = choice.split(':', 1)[0]
        self.load(choice)
        self.close()

    @staticmethod
    def load(name):
        global things_known, all_done, deck_num
        savefile = savesdir / '{}.save'.format(name)
        with savefile.open('rb') as f:
            data = pickle.load(f)
        deck = next(
            (d for d in all_deck_objects
             if d.image == data['current_deck.image']),
            None
        )
        if deck:
            enter(deck, pos=data['billy.real_x'])
        things_known = data['things_known']
        all_done = data['all_done']
        deck_num = data['deck_num']
        lift.y = data['lift.y']


class SaveMenu(GameMenu):
    def __init__(self):
        super().__init__()
        self.choices = []
        for n in range(1, 6):
            name = 'Slot %d' % n
            obj = savesdir / '{}.save'.format(name)
            if obj.exists():
                mtime = obj.stat().st_mtime
                dt = datetime.datetime.fromtimestamp(mtime)
                name = '{}: saved {:%Y-%m-%d %H:%M}'.format(name, dt)
            self.choices.append(name)

    def do(self, choice):
        if ':' in choice:
            choice = choice.split(':', 1)[0]
        self.save(choice)
        self.close()

    @staticmethod
    def autosave():
        print("Auto-saving...")
        SaveMenu.save('Auto-save')

    @staticmethod
    def save(name):
        data = {
            'things_known': things_known,
            'all_done': all_done,
            'billy.real_x': billy.real_x,
            'lift.y': lift.y,
            'current_deck.image': current_deck.image,
            'deck_num': deck_num,
        }
        if not savesdir.exists():
            savesdir.mkdir()
        savefile = savesdir / '{}.save'.format(name)
        with savefile.open('wb') as f:
            pickle.dump(data, f, -1)

    def back(self):
        PauseMenu().show()


def start_ending():
    global current_deck, viewport
    current_deck = Actor('deck2')
    current_deck.name = "Lounge"
    current_deck.actors = [
        captain, cheshire, calico, katerina, manx, mrs_manx, pussy,
        kibble, kitty
    ]
    for i, a in enumerate(current_deck.actors):
        a.real_x = 100 + 37 * i
    captain.real_x -= 30
    pussy.image = 'pussy-end'
    kibble.image = 'donnie-end'
    cheshire.image = 'lord-cheshire-end'
    billy.image = 'billy-standing'
    kitty.image = 'kitty-morgan'
    billy.real_x = 475
    viewport = 0, viewport[1]
    clock.unschedule(SaveMenu.autosave)
    draw_deck()
    music.play('reveal')
    billy.dialogue_with = captain
    DialogueChoices(load_dialogue('ending')).start()


class IntroScreen:
    MUSIC = 'deck1'
    def __init__(self):
        self.intro = Actor('intro', topleft=(0, 50))
        self.ship_images = cycle(['ship1', 'ship2', 'ship3'])
        self.moon_images = cycle(['moon1', 'moon2', 'moon3'])
        self.ship = Actor('ship1', anchor=('right', 'center'), pos=(100, 140))
        self.moon = Actor('moon1', topleft=(615, 147), anchor=('left', 'top'))
        self.itexts = iter(self.texts)
        self.drawn = False

    def show(self):
        global game_screen
        game_screen = self
        clock.schedule_interval(self.update_ship, 0.1)
        clock.schedule_interval(self.update_moon, 0.3)
        clock.schedule_unique(self.next_text, 5)
        self.next_text()
        music.play(self.MUSIC)
        billy.dialogue_with = billy.dialogue_menu = self

    def update_ship(self):
        self.ship.x += 1
        if self.ship.x % 3 == 0:
            self.ship.image = next(self.ship_images)

    def update_moon(self):
        self.moon.image = next(self.moon_images)


    texts = [
        "A Death At Sea\n\nBy Daniel Pope",
        "The Atlantic, 1927",
        "S.S. Felicia",
        "The Captain has just summoned\nme, the porter, to Deck 3...",
    ]
    slide_time = 5

    def draw(self):
        if not self.drawn:
            screen.clear()
        else:
            screen.draw.filled_rect(PANEL, BLACK)
        self.intro.draw()
        self.moon.draw()
        self.ship.draw()

        if not self.drawn:
            screen.draw.text(
                self.text,
                midtop=(WIDTH // 2, 350 - (self.text.count('\n') + 1) // 2 * 22),
                fontname=FONT,
                fontsize=22,
                color='#cccccc',
                align='center'
            )
            self.drawn = True

    def next_text(self):
        try:
            self.text = next(self.itexts)
        except StopIteration:
            self.end()
        else:
            self.drawn = False
            clock.schedule_unique(self.next_text, self.slide_time)

    def end(self):
        global game_screen
        music.stop()
        game_screen = None
        billy.dialogue_with = billy.dialogue_menu = None
        clear_text_area()

    def back(self):
        self.end()

    def select(self):
        self.next_text()


    def up(self):
        """no-op"""
    down = up


class Ending(IntroScreen):
    TEXTS = {
        'Kibble': [
            "Kibble and Manx were confined to\nrooms for the rest of the voyage.",
            "When we reached New York,\nI testified in their trial.",
            "Donnie Kibble was jailed for 15 years.",
            "Karl Manx received a 5 year prison sentence."
        ],
        'Manx': [
            "Manx and Kibble were confined to\nrooms for the rest of the voyage.",
            "When we reached New York,\nI testified in their trial.",
            "Karl Manx was jailed for 15 years.",
            "Donnie Kibble received a 7 year prison sentence."
        ],
        'Both': [
            "Manx and Kibble were confined to\nrooms for the rest of the voyage.",
            "When we reached New York,\nI testified in their trial.",
            "Manx and Kibble were each jailed for 12 years.",
        ]
    }
    MUSIC = 'outtro'

    def __init__(self, whodunnit):
        self.texts = self.TEXTS[whodunnit]
        super().__init__()

    def end(self):
        theend = 'The End'
        spelling = [theend[:n] for n in range(len(theend) + 1)]
        self.texts = spelling
        self.itexts = iter(spelling)
        clock.schedule_unique(self.next_text, 0.1)
        self.slide_time = 0.1
        self.end = lambda: None


def game_over(whodunnit):
    screen.clear()
    Ending(whodunnit).show()



try:
    LoadMenu.load('Auto-save')
except IOError:
    IntroScreen().show()


#for t in sorted(things_known):
#    print(repr(t))
