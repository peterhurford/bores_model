import datetime
import random
import numpy as np
import squigglepy as sq

from pprint import pprint
from squigglepy.numbers import K, M
from collections import Counter

TODAY = datetime.date(2026, 6, 9)
# Half-life for poll time-decay. 90 days lets the recent Honan poll dominate
# without entirely zeroing out the May 2025 polls.
HALF_LIFE_DAYS = 90

# Raw polls. 'Other' lumps the listed minor candidates plus any "someone else"
# bucket. Most are Dem-partisan-sponsored — we don't down-weight them for that,
# just sample-size-weight and time-decay-weight. Candidates not reported by a
# poll (e.g. Honan only reported L/B/S) are omitted and skipped in the average.
POLLS = [
    {'name': 'Emerson',          'n': 425, 'date': datetime.date(2026, 5, 15),
     'Lasher': 0.22, 'Bores': 0.20, 'Schlossberg': 0.11, 'Conway': 0.09,
     'Other': 0.05, 'Undecided': 0.32},
    {'name': 'Tavern Research',  'n': 879, 'date': datetime.date(2026, 5, 15),
     'Lasher': 0.16, 'Bores': 0.20, 'Schlossberg': 0.17, 'Conway': 0.09,
     'Other': 0.10, 'Undecided': 0.28},
    {'name': 'GQR',              'n': 500, 'date': datetime.date(2026, 5, 15),
     'Lasher': 0.23, 'Bores': 0.26, 'Schlossberg': 0.14, 'Conway': 0.17,
     'Other': 0.00, 'Undecided': 0.18},
    {'name': 'Hart Research',    'n': 400, 'date': datetime.date(2026, 5, 15),
     'Lasher': 0.20, 'Bores': 0.21, 'Schlossberg': 0.17, 'Conway': 0.10,
     'Other': 0.04, 'Undecided': 0.28},
    # Honan Strategy Group (sponsor: Grand Penn Community Alliance), conducted
    # April 16-22, 2026. Only L/B/S were reported publicly; n not disclosed —
    # default to 500 (typical for a sponsor-released primary poll).
    {'name': 'Honan Strategy Group', 'n': 500, 'date': datetime.date(2026, 4, 19),
     'Lasher': 0.28, 'Bores': 0.19, 'Schlossberg': 0.20},
]

CANDS = ['Lasher', 'Bores', 'Schlossberg', 'Conway', 'Other']
ALL_FIELDS = CANDS + ['Undecided']

def time_weight(poll_date):
    days_old = (TODAY - poll_date).days
    return 0.5 ** (days_old / HALF_LIFE_DAYS)

def weighted_avg(field):
    polls_with = [p for p in POLLS if field in p]
    weights = [p['n'] * time_weight(p['date']) for p in polls_with]
    return sum(w * p[field] for w, p in zip(weights, polls_with)) / sum(weights)

# Per-candidate weighted average, then normalize to sum to 1 — necessary
# because partial polls (Honan) leave some fields out, so the raw averages
# wouldn't otherwise sum to 1.
_raw = {f: weighted_avg(f) for f in ALL_FIELDS}
_total = sum(_raw.values())
_normalized = {f: v / _total for f, v in _raw.items()}
RAW_POLL = {c: _normalized[c] for c in CANDS}
UNDECIDED = _normalized['Undecided']

# Post-polling adjustment: shift 1pp from Bores to Lasher.
# Originally added to hack the poll average closer to the Kalshi market avg.
# Currently disabled (see APPLY_ADJUSTMENT) but kept for reference.
APPLY_ADJUSTMENT = False
ADJUSTMENT = {'Bores': -0.01, 'Lasher': +0.01}
_adj = ADJUSTMENT if APPLY_ADJUSTMENT else {}
POLL = {c: RAW_POLL[c] + _adj.get(c, 0) for c in CANDS}

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
# Use lowercase `k` here — uppercase `K` is the squigglepy constant (=1000)
# imported at module scope, and shadowing it would break any later resampling.
for k in [1, 2, 5, 10]:
    flips = ((deficit > 0) & (deficit < k)).sum()
    delta_direct = flips / len(samples)
    delta_density = density_per_vote * k
    one_in_direct = f'1 in {int(round(1/delta_direct)):,}' if delta_direct > 0 else 'n/a'
    one_in_density = f'1 in {int(round(1/delta_density)):,}' if delta_density > 0 else 'n/a'
    print(f'  +{k:2d} votes:  +{delta_direct*100:8.5f}pp ({one_in_direct:>14})'
          f'   +{delta_density*100:.5f}pp ({one_in_density})')
print()

print('=== $ value of a marginal Bores vote ===')
# A vote is only valuable when it flips Bores from losing to winning; winning
# by more doesn't help. EV = P(flip per vote) * value(Bores win). Use the
# density extrapolation for P(flip per vote) (much lower variance than the
# 1-vote direct count). Win value modeled as Lognormal with 90% CI $20M-$150M.
win_value_dist = sq.lognorm(20 * M, 150 * M)
win_value_samples = sq.sample(win_value_dist, n=100_000)
win_value_mean = float(np.mean(win_value_samples))
win_value_median = float(np.median(win_value_samples))
print(f'P(flip per marginal vote) = {density_per_vote*100:.5f}% '
      f'(1 in {int(round(1/density_per_vote)):,})')
print(f'Win-value lognormal: mean ${win_value_mean/M:.1f}M, '
      f'median ${win_value_median/M:.1f}M')
print()
print('  Assumed value of Bores winning      EV per marginal vote')
for label, v in [('$20M  (low end of 90% CI)', 20 * M),
                 (f'${win_value_median/M:.0f}M  (lognorm median)', win_value_median),
                 (f'${win_value_mean/M:.0f}M  (lognorm mean)', win_value_mean),
                 ('$150M (high end of 90% CI)', 150 * M)]:
    ev = density_per_vote * v
    print(f'  {label:<35}  ${ev:>8,.2f}')
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
