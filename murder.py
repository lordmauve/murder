#!/usr/local/bin/pgzrun
"""Death at Sea.

A murder adventure game.

"""
import re
import yaml
import pgzero.loaders
from pathlib import Path
from collections import OrderedDict

basedir = Path(pgzero.loaders.root)


def load_dialogue(character):
    """Load the dialogue for the given character."""
    path = basedir / 'dialogue' / '{}.txt'.format(character)
    patterns = OrderedDict()
    key = None
    steps = []
    with path.open(encoding='utf8') as f:
        for lineno, l in enumerate(f, start=1):
            l = l.strip()
            if not l:
                continue
            mo = re.match(r'^\[(.*)\]$', l)
            if mo:
                if key:
                    patterns[key] = steps
                    steps = []
                key = mo.group(1)
                continue
            mo = re.match('^([A-Z]+): *(.*)', l)
            if mo:
                action = mo.group(1)
                if action not in ('YOU', 'THEY', 'EXIT'):
                    raise ValueError(
                        'invalid key %r, %s, line %d' % (action, path, lineno)
                    )
                steps.append(mo.groups())
            else:
                action, text = steps[-1]
                if text:
                    text += '\n'
                text += l
                steps[-1] = action, text

    if key:
        patterns[key] = steps
        steps = []

    out_patterns = OrderedDict()
    for k, v in patterns.items():
        pats = out_patterns
        parts = k.split('.')
        for path in parts[:-1]:
            pats = pats.setdefault(path, OrderedDict())
        pats[parts[-1]] = v

    return out_patterns


TITLE = "A Death at Sea"
WIDTH = 800
HEIGHT = 600
FONT = "travelling_typewriter"

# All NPCs are anchored at center bottom
CANC = ('center', 'bottom')

deck1 = Actor('deck1')
deck1.name = "On Deck"

deck2 = Actor('deck2')
deck2.name = "Lounge"

deck3 = Actor('deck3')
deck3.name = "First-class Cabins"

deck4 = Actor('deck4')
deck4.name = "Second-class Cabins"

kitty = Actor('kitty-morgan', anchor=CANC)
kitty.real_x = 500
kitty.name = "Kitty Morgan"

cheshire = Actor('lord-cheshire', anchor=CANC)
cheshire.real_x = 400
cheshire.name = "Lord Cheshire"
cheshire.dialogue = load_dialogue('cheshire')

manx = Actor('doctor-manx', anchor=CANC)
manx.real_x = 1200
manx.name = "Doctor Manx"

buster = Actor('buster-baines', anchor=CANC)
buster.real_x = 400
buster.name = "Buster Bains"

calico = Actor('calico-croker', anchor=CANC)
calico.real_x = 500
calico.name = "Calico Croker"


lift = Actor('lift', pos=(80, 100))


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
billy.knows = {'Bye'}  # Start only knowing how to end a conversation

decks = [deck1, deck2, deck3, deck4]
actors = [[buster], [cheshire, manx], [calico], [kitty]]

deck_num = 0
current_deck = deck1

viewport = (0, 0)

for d in decks:
    d.level_width = d.width
deck1.level_width -= 312


def draw():
    screen.clear()
    if billy.in_lift:
        draw_lift()
    else:
        draw_deck()


def draw_lift():
    lift.draw()
    screen.draw.text(
        'Deck %s: %s' % (deck_num + 1, current_deck.name),
        midleft=(lift.x + 60, lift.y),
        fontname=FONT,
        fontsize=20,
        color='#cccccc'
    )


def get_actors():
    """Get a list of the actors on the current deck."""
    return actors[deck_num]


def draw_deck():
    vx, vy = viewport
    current_deck.left = -vx
    current_deck.top = 50
    current_deck.draw()
    for a in get_actors():
        a.pos = a.real_x - vx, 186
        a.draw()
    billy.x = billy.real_x - vx
    billy.draw()
    screen.draw.text(
        current_deck.name,
        topright=(WIDTH - 10, 10),
        fontname=FONT,
        fontsize=20,
        color='#cccccc'
    )
    if billy.dialogue_with:
        billy.dialogue_menu.draw()
    else:
        draw_action_caption()


def draw_action_caption():
    for a in get_actors():
        if billy.colliderect(a):
            draw_caption('Talk to %s' % a.name)
            break
    else:
        if is_by_lift():
            draw_caption('Use lift')


def draw_caption(caption):
    screen.draw.text(
        caption,
        midtop=(WIDTH // 2, 220),
        fontname=FONT,
        fontsize=20,
        color='#cccccc'
    )


def update():
    global frame, viewport
    if keyboard.left:
        billy.real_x = max(30, billy.real_x - MAX_WALK)
        billy.image = 'billy-standing-l'
    elif keyboard.right:
        billy.real_x = min(current_deck.level_width - 30, billy.real_x + MAX_WALK)
        billy.image = 'billy-standing-r'

    vx, vy = viewport
    l_edge = WIDTH // 3
    r_edge = l_edge * 2
    if billy.real_x > vx + r_edge:
        vx = min(billy.real_x - r_edge, current_deck.width - WIDTH)
    if billy.real_x < vx + l_edge:
        vx = max(billy.real_x - l_edge, 0)
    viewport = vx, vy


def on_mouse_move(rel, buttons):
    global viewport
    if mouse.LEFT not in buttons:
        return
    vx, vy = viewport
    dx, dy = rel
    vx = max(min(vx - dx, level_w - WIDTH), 0)
    viewport = vx, vy


TWEEN = 'accel_decel'



def is_by_lift():
    return 50 < billy.real_x < 120


def on_key_down(key):
    if billy.dialogue_with:
        on_key_down_dialogue(key)
    else:
        on_key_down_walk(key)


def on_key_down_walk(key):
    global deck_num, current_deck, viewport
    if billy.in_lift:
        if key == keys.RETURN:
            billy.in_lift = False
            viewport = 0, 0
        elif key == keys.UP and deck_num > 0:
            deck_num -= 1
            current_deck = decks[deck_num]
            animate(lift, y=100 * deck_num + 100, tween=TWEEN)
        elif key == keys.DOWN and deck_num < len(decks) - 1:
            deck_num += 1
            current_deck = decks[deck_num]
            animate(lift, y=100 * deck_num + 100, tween=TWEEN)
    else:
        if key == keys.UP:
            billy.image = 'billy-back'


def on_key_down_dialogue(key):
    if key == keys.UP:
        billy.dialogue_menu.up()
    elif key == keys.DOWN:
        billy.dialogue_menu.down()
    elif key == keys.RETURN:
        billy.dialogue_menu.select()


class DialogueChoices:
    def __init__(self, options, parent=None):
        self.options = options
        self.parent = parent

    def start(self):
        if self.parent is None and 'enter' in self.options:
            self.play_dialogue(self.options['enter'])
        else:
            self.show()

    def show(self):
        self.selected = 0
        self.choices = [
            (k, v)
            for k, v in self.options.items()
            if k in billy.knows
        ]
        billy.dialogue_menu = self

    def draw(self):
        for i, opt in enumerate(self.choices):
            key, steps = opt
            color = '#cccccc' if i != self.selected else 'white'
            screen.draw.text(
                key,
                bottomleft=(30, 230 + 30 * i),
                fontname=FONT,
                fontsize=20,
                color=color
            )

    def up(self):
        self.selected = (self.selected - 1) % len(self.choices)

    def down(self):
        self.selected = (self.selected + 1) % len(self.choices)

    def select(self):
        _, steps = self.choices[self.selected]
        self.play_dialogue(steps)

    def play_dialogue(self, steps):
        billy.dialogue_menu = DialogueChat(steps, self)


class DialogueChat:
    def __init__(self, steps, parent):
        self.steps = steps[:]
        self.parent = parent
        self.select()

    def draw(self):
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
            topleft=(30, 240),
            width=WIDTH-60,
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
        try:
            self.action, self.text = self.steps.pop(0)
        except IndexError:
            self.parent.show()
        if self.action == 'EXIT':
            billy.dialogue_menu = None
            billy.dialogue_with = None

    def up(self):
        """no-op."""

    def down(self):
        """no-op."""


def start_dialogue(character):
    """Start a dialogue with a character."""
    billy.knows.add(character.name)  # Learn about this character
    try:
        dialogue = character.dialogue
    except AttributeError:
        return
    billy.dialogue_with = character
    DialogueChoices(dialogue).start()


def on_key_up(key):
    if billy.dialogue_with:
        return

    if key == keys.UP:
        for a in get_actors():
            if billy.colliderect(a):
                start_dialogue(a)
        if is_by_lift():
            billy.in_lift = True
    else:
        billy.image = 'billy-standing'
