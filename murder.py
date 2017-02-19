#!/usr/local/bin/pgzrun
"""Death at Sea.

A murder adventure game.

"""

TITLE = "A Death at Sea"
WIDTH = 800
FONT = "travelling_typewriter"

deck1 = Actor('deck1')
deck1.name = "On Deck"

deck2 = Actor('deck2')
deck2.name = "Lounge"

deck3 = Actor('deck3')
deck3.name = "First-class Cabins"

deck4 = Actor('deck4')
deck4.name = "Second-class Cabins"


lift = Actor('lift', pos=(80, 100))


# Maximum walk speed
MAX_WALK = 3
billy = Actor(
    'billy-standing',
    anchor=('center', 'bottom'),
    pos=(100, 190)
)
billy.real_x = 100
billy.in_lift = False

decks = [deck1, deck2, deck3, deck4]

deck_num = 0
current_deck = deck1

viewport = (0, 0)

level_w = max(d.width for d in decks)



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
    billy.x = billy.real_x - vx
    billy.draw()
    screen.draw.text(
        current_deck.name,
        topright=(WIDTH - 10, 10),
        fontname=FONT,
        fontsize=20,
        color='#cccccc'
    )


def update():
    global frame
    if keyboard.left:
        billy.real_x = max(30, billy.real_x - MAX_WALK)
        billy.image = 'billy-standing-l'
    elif keyboard.right:
        billy.real_x = min(level_w - 30, billy.real_x + MAX_WALK)
        billy.image = 'billy-standing-r'
    else:
        billy.image = 'billy-standing'


def on_mouse_move(rel, buttons):
    global viewport
    if mouse.LEFT not in buttons:
        return
    vx, vy = viewport
    dx, dy = rel
    vx = max(min(vx - dx, level_w - WIDTH), 0)
    viewport = vx, vy


def on_key_down(key):
    global deck_num, current_deck
    if billy.in_lift:
        if key == keys.RETURN:
            billy.in_lift = False
        elif key == keys.UP and deck_num > 0:
            deck_num -= 1
            current_deck = decks[deck_num]
            animate(lift, y=100 * deck_num + 100)
        elif key == keys.DOWN and deck_num < len(decks) - 1:
            deck_num += 1
            current_deck = decks[deck_num]
            animate(lift, y=100 * deck_num + 100)
    else:
        if key == keys.UP:
            if 50 < billy.real_x < 100:
                billy.in_lift = True
