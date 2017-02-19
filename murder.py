WIDTH = 800

deck1 = Actor('deck1', anchor=('left', 'top'))
deck2 = Actor('deck2', anchor=('left', 'top'))
deck3 = Actor('deck3', anchor=('left', 'top'))
deck4 = Actor('deck4', anchor=('left', 'top'))


decks = [deck1, deck2, deck3, deck4]

viewport = (0, 0)

level_w = max(d.width for d in decks)


def draw():
    screen.clear()
    vx, vy = viewport
    for i, d in enumerate(decks):
        d.topleft = -vx, -vy + 150 * i
        d.draw()


frame = 0
def update():
    global frame
    frame += 1


def on_mouse_move(rel, buttons):
    global viewport
    if mouse.LEFT not in buttons:
        return
    vx, vy = viewport
    dx, dy = rel
    vx = max(min(vx - dx, level_w - WIDTH), 0)
    viewport = vx, vy


