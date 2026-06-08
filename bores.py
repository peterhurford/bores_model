import random
import numpy as np
import squigglepy as sq

from pprint import pprint
from squigglepy.numbers import K
from collections import Counter

# Raw polls (May 2025). 'Other' lumps the listed minor candidates plus any
# "someone else" bucket. 3 of 4 are Dem-partisan-sponsored — we don't down-
# weight them here, just sample-size-weight.
POLLS = [
    {'name': 'Emerson',          'n': 425,
     'Lasher': 0.22, 'Bores': 0.20, 'Schlossberg': 0.11, 'Conway': 0.09,
     'Other': 0.05, 'Undecided': 0.32},
    {'name': 'Tavern Research',  'n': 879,
     'Lasher': 0.16, 'Bores': 0.20, 'Schlossberg': 0.17, 'Conway': 0.09,
     'Other': 0.10, 'Undecided': 0.28},
    {'name': 'GQR',              'n': 500,
     'Lasher': 0.23, 'Bores': 0.26, 'Schlossberg': 0.14, 'Conway': 0.17,
     'Other': 0.00, 'Undecided': 0.18},
    {'name': 'Hart Research',    'n': 400,
     'Lasher': 0.20, 'Bores': 0.21, 'Schlossberg': 0.17, 'Conway': 0.10,
     'Other': 0.04, 'Undecided': 0.28},
]

CANDS = ['Lasher', 'Bores', 'Schlossberg', 'Conway', 'Other']
total_n = sum(p['n'] for p in POLLS)
RAW_POLL = {c: sum(p['n'] * p[c] for p in POLLS) / total_n for c in CANDS}
UNDECIDED = sum(p['n'] * p['Undecided'] for p in POLLS) / total_n

# Post-polling adjustment: shift 1pp from Bores to Lasher.
# Do this to hack the poll average to be more like the Kalshi market average.
# idk maybe this makes sense because endorsements or something?
ADJUSTMENT = {'Bores': -0.01, 'Lasher': +0.01}
POLL = {c: RAW_POLL[c] + ADJUSTMENT.get(c, 0) for c in CANDS}

# Allocate undecideds proportionally to current named support — no directional
# assumption about who they break for.
decided = sum(POLL.values())
MEAN_SHARES = {c: p + UNDECIDED * p / decided for c, p in POLL.items()}

def _fmt_shares(d):
    return ', '.join(f'{c} {d[c]*100:.1f}%' for c in CANDS)

print(f'Raw poll average:      {_fmt_shares(RAW_POLL)} | Undecided {UNDECIDED*100:.1f}%')
print(f'After adjustment:      {_fmt_shares(POLL)} | Undecided {UNDECIDED*100:.1f}%')
print(f'Means (undecided alloc): {_fmt_shares(MEAN_SHARES)}')
print()

# Total Dirichlet concentration. Smaller -> wider per-candidate spread.
# alpha_0 = 80 keeps the L/B gap distribution polling-error-shaped and pins
# Schloss's win share near 5% given his ~9pp mean deficit.
ALPHA_0 = 80
CANDIDATE_ALPHAS = [ALPHA_0 * MEAN_SHARES[c] for c in MEAN_SHARES]

CANDIDATE_NAMES = list(MEAN_SHARES.keys())  # Lasher, Bores, Schlossberg, Conway, Other

# Squigglepy model
def margin_model():
    total_eligible = ~sq.norm(310*K, 350*K)
    turnout_pct = ~sq.norm(0.25, 0.35)
    total_electorate = turnout_pct * total_eligible
    shares = ~sq.dirichlet(CANDIDATE_ALPHAS)
    share_by_name = dict(zip(CANDIDATE_NAMES, shares))

    bores_pct = share_by_name['Bores']
    lasher_pct = share_by_name['Lasher']
    schloss_pct = share_by_name['Schlossberg']

    main = {'Bores': bores_pct, 'Lasher': lasher_pct, 'Schloss': schloss_pct}
    ranked = sorted(main.items(), key=lambda kv: -kv[1])
    winner, winner_pct = ranked[0]
    second, second_pct = ranked[1]
    win_pct = winner_pct - second_pct

    return {'turnout_pct': turnout_pct,
            'eligible': total_eligible,
            'turnout': total_electorate,
            'bores_pct': bores_pct,
            'bores_votes': bores_pct * total_electorate,
            'lasher_pct': lasher_pct,
            'lasher_votes': lasher_pct * total_electorate,
            'schloss_pct': schloss_pct,
            'schloss_votes': schloss_pct * total_electorate,
            'winner': winner,
            'second': second,
            'win_pct': win_pct,
            'win_votes': win_pct * total_electorate}


PCT_FIELDS = {'turnout_pct', 'bores_pct', 'lasher_pct', 'schloss_pct', 'win_pct'}

def fmt(field, value):
    if isinstance(value, str):
        return value
    if field == 'turnout_pct':
        return f'{value * 100:.1f}%'
    if field in PCT_FIELDS:
        return f'{value * 100:.1f}pp'
    return f'{int(round(value)):,}'

def fmt_percentiles(field, values):
    digits = 3 if field in PCT_FIELDS else 0
    pcts = sq.get_percentiles(values, digits=digits)
    return {p: fmt(field, v) for p, v in pcts.items()}

print('VOTES DECIDING THE ELECTION')
samples = sq.sample(margin_model, n=100_000, verbose=True)
print()

by_field = {k: [s[k] for s in samples] for k in samples[0]}
numeric_fields = [k for k, v in by_field.items() if not isinstance(v[0], str)]
categorical_fields = [k for k in by_field if k not in numeric_fields]

print('=== Percentiles ===')
for field in numeric_fields:
    print(f'{field}:')
    pprint(fmt_percentiles(field, by_field[field]))
    print('-')

print('=== Outcome frequencies ===')
for field in categorical_fields:
    counts = Counter(by_field[field])
    n = sum(counts.values())
    print(f'{field}:')
    pprint({name: f'{c / n * 100:.1f}%' for name, c in counts.most_common()})
    print('-')

CAND_ROWS = [
    ('Bores',       'bores_pct',   'bores_votes'),
    ('Lasher',      'lasher_pct',  'lasher_votes'),
    ('Schlossberg', 'schloss_pct', 'schloss_votes'),
]

print('=== Marginal value of bonus Bores votes ===')
# Treat each "bonus" vote as a person who otherwise wouldn't have voted, voting
# for Bores. Bores wins (vs L/S) iff bores_votes + K > max(lasher_votes, schloss_votes).
# So a +K bonus flips an election iff the unrounded vote deficit is in (0, K).
bores_v = np.array([s['bores_votes'] for s in samples])
lasher_v = np.array([s['lasher_votes'] for s in samples])
schloss_v = np.array([s['schloss_votes'] for s in samples])
deficit = np.maximum(lasher_v, schloss_v) - bores_v  # positive => Bores losing
baseline_p = (deficit < 0).mean()
print(f'Baseline P(Bores wins): {baseline_p*100:.3f}%')

# Direct flip counts (high-variance for small K because few sims land in a 1-vote
# window). Also report a local-density extrapolation: density of `deficit` just
# above 0, times K.
window = 200
in_window = ((deficit > 0) & (deficit < window)).sum()
density_per_vote = in_window / window / len(samples)  # P(flip) per additional vote

print(f'                  direct count                  density extrapolation')
for K in [1, 2, 5, 10]:
    flips = ((deficit > 0) & (deficit < K)).sum()
    delta_direct = flips / len(samples)
    delta_density = density_per_vote * K
    one_in_direct = f'1 in {int(round(1/delta_direct)):,}' if delta_direct > 0 else 'n/a'
    one_in_density = f'1 in {int(round(1/delta_density)):,}' if delta_density > 0 else 'n/a'
    print(f'  +{K:2d} votes:  +{delta_direct*100:8.5f}pp ({one_in_direct:>14})'
          f'   +{delta_density*100:.5f}pp ({one_in_density})')
print()

print('=== Random sample elections ===')
for i, idx in enumerate(random.sample(range(len(samples)), 10), 1):
    s = samples[idx]
    print(f'Election #{i}: turnout {fmt("turnout_pct", s["turnout_pct"])} '
          f'of {fmt("eligible", s["eligible"])} eligible '
          f'= {fmt("turnout", s["turnout"])} voters')
    ranked = sorted(CAND_ROWS, key=lambda r: -s[r[1]])
    for name, pct_key, votes_key in ranked:
        print(f'  {name:<11} {fmt(pct_key, s[pct_key]):>6}  '
              f'({fmt(votes_key, s[votes_key]):>8} votes)')
    print(f'  -> {s["winner"]} beats {s["second"]} by '
          f'{fmt("win_pct", s["win_pct"])} '
          f'({fmt("win_votes", s["win_votes"])} votes)')
    print()
