# rutinel_model

A Monte Carlo model of the CO-08 Democratic primary (June 30, 2026), focused on
Manny Rutinel's chances against Shannon Bird and the marginal value of a single
additional vote.

## Installation and running

Requires Python 3.10+.

```
pip install -r requirements.txt
python rutinel.py
```

A sample run is checked in as `model_output.txt`. Re-running will produce
slightly different numbers because the Monte Carlo is unseeded; set
`random.seed(...)` and `np.random.seed(...)` at the top of `rutinel.py` if you
want reproducibility.

## The race

Three Democrats filed for CO-08: Manny Rutinel (progressive), Shannon Bird
(moderate), and Evan Munsing. Munsing effectively exited in late May but remains
on the printed ballot, so polls still record ~5% support for him. The model
carries Munsing as a candidate but he is a non-contender for the win in
practice. The winner faces Republican Rep. Gabe Evans in November.

The three available polls are all partisan-sponsored: two GBAO polls for the
Latino Victory Fund (April and June) and one Normington, Petts & Associates poll
for the Bird campaign (April). The April polls show a Rutinel/Bird tie; the June
GBAO poll shows Rutinel +13.

## The model

### Pipeline

1. **Weighted poll average.** Each poll is weighted by sample size *and* by an
   exponential time-decay (90-day half-life, anchored to `TODAY = 2026-06-20`),
   so the recent June poll carries more weight without zeroing out the April
   polls. Per-candidate averages are then normalized to sum to 1, which also
   absorbs the small rounding gaps in the reported toplines.
2. **Adjustment (currently disabled).** `APPLY_ADJUSTMENT = False`. The code
   retains an optional hook to shift mass between candidates (e.g. to pull the
   polling average toward a betting-market consensus), but it is off by default.
3. **Undecided allocation.** Allocate the undecided bloc proportionally to each
   candidate's current named support — no directional assumption about who they
   break for.
4. **Dirichlet sampling.** Treat the resulting mean shares as the center of a
   Dirichlet with total concentration `ALPHA_0 = 80` (effective sample ~80,
   deliberately wider than any single n~400 poll to absorb model uncertainty and
   the April→June trend). This calibrates the Rutinel–Bird gap distribution to
   look roughly polling-error-shaped.
5. **Turnout.** Dem-primary-eligible pool (registered Democrats plus
   unaffiliated voters who return the Democratic ballot) ~ Normal 90% CI
   270K–330K; ballot-return rate ~ Normal 90% CI 27%–38%. This centers total
   ballots cast around ~100K (90% CI ~75K–135K), built up from ~160K registered
   Democrats and ~165K unaffiliated voters, with the upper end driven by the
   contested Bennet–Weiser gubernatorial primary topping the same June 30
   ballot. These are rough CO-08 estimates — adjust as better data arrives.
6. **100,000 sims.** For each, draw shares and turnout, compute vote totals, and
   pick a winner among Rutinel / Bird / Munsing (Munsing is on the ballot but
   effectively never wins).

### Outputs

- **Percentiles** for turnout, each candidate's vote share and vote count, and
  the winning margin (both percentage points and raw votes).
- **Win frequencies** for each candidate.
- **Marginal value of a vote.** For K ∈ {1, 2, 5, 10}, the probability that K
  additional Rutinel votes flip the election, reported both as a direct
  flip-count and as a local-density extrapolation (density of the vote deficit
  just above zero, times K). The density estimate is much lower-variance for
  small K.
- **Dollar value of a marginal vote.** Multiplies the per-vote flip probability
  by the value of a Rutinel win — modeled as Lognormal with a 90% CI of
  $20M–$150M — and reports the EV per marginal vote across several assumed win
  values.
- **Ten random sampled elections,** printed in full.

See `model_output.txt` for a sample run.
