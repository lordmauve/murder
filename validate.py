"""Validate some of the dialogue."""

import re
from collections import Counter
from pathlib import Path

dialogue = Path('dialogue')

characters = {
    'Calico Croker',
    'Lord Cheshire',
    'Pussy Galumps',
    'Donnie Kibble',
    'Doctor Manx',
    'Mrs. Manx',
    'Katerina la Gata',
    'Kitty Morgan',
    'The Captain'
}


choices = {}
predicates = {}
learn = {}


for f in dialogue.glob('*.txt'):
    lines = f.read_text(encoding='utf8').splitlines()

    name = f.stem
    for lineno, l in enumerate(lines, start=1):
        mo = re.match(r'^\[(.*)\](\??)(?: +if +(.*))?$', l)
        if mo:
            key, qmark, ifs = mo.groups()
            cond = set()
            if qmark:
                cond.add(key)
            if ifs:
                for t in ifs.split(','):
                    t = t.strip()
                    if t.startswith('.'):
                        t = name + t
                    cond.add(t)
            if key in characters and not cond:
                print('No ? for [{}] at {}, line {}'.format(key, name, lineno))
            choices.setdefault(name, set()).add(key)
            predicates[name, lineno] = cond

        mo = re.match(r'^LEARN:(.*)', l)
        if mo:
            fact = mo.group(1).strip()
            if fact.startswith('.'):
                fact = name + fact
            learn[name, lineno] = fact


learnable_set = set(learn.values()) | characters | {'Lift',}
for (name, lineno), conds in sorted(predicates.items()):
    for c in conds:
        if c not in learnable_set:
            print("No learnable {} at {}, line {}".format(c, name, lineno))


require = ['About yourself'] + \
    sorted(characters - {'The Captain'}) + ['KM', 'Statue', 'Note']

filemap = [
    ('calico', 'cc'),
    ('cheshire', 'lc'),
    ('pussy', 'pg'),
    ('kibble', 'dk'),
    ('manx', 'dm'),
    ('mrs-manx', 'mm'),
    ('katerina', 'kg'),
    ('kitty', 'km'),
    ('captain', 'cp'),
]

print(' ' * 20, ' '.join(initials for _, initials in filemap))

missing = []
for r in require:
    row = []
    for f, initials in filemap:
        ri = Counter(w[0] for w in r.lower().split())
        if (Counter(initials) & ri) == Counter(initials):
            char = 'x'
        elif r not in choices[f]:
            missing.append((f, r))
            char = ' '
        else:
            char = '*'
        row.append(char)
    print('{:>20}: {} '.format(r, '| '.join(row)))

print()

for n, i in filemap:
    print(' ' * 20, '{} = {}'.format(i, n))


if missing:
    import random
    print()
    print('Perhaps next:')
    for char, choice in random.sample(missing, 3):
        print('Ask {} about {}'.format(char, choice))
