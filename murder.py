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
                if action not in ('YOU', 'THEY', 'EXIT', 'LEARN'):
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

    out_patterns = OrderedDict()
    for k, v in patterns.items():
        pats = out_patterns
        parts = k.split('.')
        for path in parts[:-1]:
            pats = pats.setdefault(path, OrderedDict())
        steps = []
        for action, text in v:
            text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text.strip())
            steps.append((action, text))
        pats[parts[-1]] = steps

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

deck3 = Actor('deck3-start')
deck3.name = "First-class Cabins"

deck4 = Actor('deck4')
deck4.name = "Second-class Cabins"

baines_room = Actor('baines-room')
baines_room.name = "Cabin 35"

kitty = Actor('kitty-morgan', anchor=CANC)
kitty.real_x = 500
kitty.name = "Kitty Morgan"

cheshire = Actor('lord-cheshire', anchor=CANC)
cheshire.real_x = 400
cheshire.name = "Lord Cheshire"

manx = Actor('doctor-manx', anchor=CANC)
manx.real_x = 1200
manx.name = "Doctor Manx"

katerina = Actor('katerina-la-gata', anchor=CANC)
katerina.real_x = 400
katerina.name = "Katerina la Gata"

calico = Actor('calico-croker', anchor=CANC)
calico.real_x = 500
calico.name = "Calico Croker"

captain = Actor('captain', anchor=CANC)
captain.real_x = 250
captain.name = "The Captain"

lift = Actor('lift', pos=(80, 300))


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
deck1.actors = [katerina]
deck2.actors = [cheshire, manx]
deck3.actors = [calico, captain]
deck4.actors = [kitty]
baines_room.actors = []


class Door:
    W = 35

    def __init__(self, pos, dest, dest_pos, caption=None):
        self.pos = pos
        self.dest = dest
        self.dest_pos = dest_pos
        self._caption = caption

    def is_next_to(self):
        return self.pos - self.W < billy.real_x < self.pos + self.W

    def caption(self):
        return self._caption or "Enter {}".format(self.dest.name)

    def use(self):
        enter(self.dest, self.dest_pos)


def enter(deck, pos=None):
    """Enter the given deck/room at the given x pos."""
    global current_deck, viewport
    current_deck = deck
    if pos is not None:
        billy.real_x = pos
    if current_deck.width < WIDTH:
        vx = -(WIDTH - current_deck.width) // 2
    else:
        vx = min(current_deck.width - WIDTH, max(billy.real_x - WIDTH // 2, 0))
    viewport = vx, viewport[1]


class Lift:
    W = 35

    def __init__(self, pos=85):
        self.pos = pos

    def is_next_to(self):
        return self.pos - self.W < billy.real_x < self.pos + self.W

    def caption(self):
        return "Use lift"

    def use(self):
        billy.in_lift = True


deck1.objects = [Lift()]
deck2.objects = [Lift()]
deck3.objects = [Lift(), Door(310, baines_room, 55)]
deck4.objects = [Lift()]
baines_room.objects = [Door(55, deck3, 310, "To the corridor")]


all_deck_objects = [deck1, deck2, deck3, deck4, baines_room]

deck_num = 2
current_deck = deck3

viewport = (0, 0)

for d in all_deck_objects:
    d.level_width = d.width
deck1.level_width -= 312


def reload_dialogue():
    """Load all dialogue.

    Press F5 to reload all when changed.

    """
    cheshire.dialogue = load_dialogue('cheshire')
    katerina.dialogue = load_dialogue('katerina')
    calico.dialogue = load_dialogue('calico')
    captain.dialogue = load_dialogue('captain')
    if billy.dialogue_with:
        start_dialogue(billy.dialogue_with)


reload_dialogue()


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


def draw_deck():
    vx, vy = viewport
    current_deck.left = -vx
    current_deck.top = 50
    current_deck.draw()
    for a in current_deck.actors:
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
    for a in current_deck.actors:
        if billy.colliderect(a):
            draw_caption('Talk to %s' % a.name)
            return
    for o in current_deck.objects:
        if o.is_next_to():
            draw_caption(o.caption())
            return


def draw_caption(caption):
    screen.draw.text(
        caption,
        midtop=(WIDTH // 2, 220),
        fontname=FONT,
        fontsize=20,
        color='#cccccc'
    )


def update():
    if not billy.dialogue_with:
        move_billy()


def move_billy():
    global frame, viewport
    if keyboard.left:
        billy.real_x = max(30, billy.real_x - MAX_WALK)
        billy.image = 'billy-standing-l'
    elif keyboard.right:
        billy.real_x = min(current_deck.level_width - 30, billy.real_x + MAX_WALK)
        billy.image = 'billy-standing-r'

    if current_deck.width > WIDTH:
        vx, vy = viewport
        l_edge = WIDTH // 3
        r_edge = l_edge * 2
        if billy.real_x > vx + r_edge:
            vx = min(billy.real_x - r_edge, current_deck.width - WIDTH)
        if billy.real_x < vx + l_edge:
            vx = max(billy.real_x - l_edge, 0)
        viewport = vx, vy


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
        self.done = options.setdefault('__done', set())
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
            if key in self.done:
                color = '#ff4444' if i == self.selected else '#cc0000'
            else:
                color = '#cccccc' if i != self.selected else 'white'
            screen.draw.text(
                key,
                bottomleft=(30, 260 + 30 * i),
                fontname=FONT,
                fontsize=20,
                color=color
            )
            if key in self.done:
                screen.draw.text(
                    '-' * len(key),
                    bottomleft=(30, 260 + 30 * i),
                    fontname=FONT,
                    fontsize=20,
                    color=color
                )

    def up(self):
        self.selected = (self.selected - 1) % len(self.choices)

    def down(self):
        self.selected = (self.selected + 1) % len(self.choices)

    def select(self):
        key, steps = self.choices[self.selected]
        if key not in ('Bye', 'Back'):
            self.done.add(key)
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
                self.action, self.text = self.steps.pop(0)
            except IndexError:
                self.parent.show()
                return
            if self.action == 'LEARN':
                billy.knows.add(self.text)
                continue
            break

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
