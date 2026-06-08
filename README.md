# bores_model

A Monte Carlo model of the NY-17 Democratic primary, focused on Mike Bores'
chances and the marginal value of a single additional vote.

## Running

```
pip install numpy squigglepy
python bores.py
```

## The model

### Inputs

Four public polls from May 2025 (Emerson, Tavern Research, GQR, Hart), with
shares for Lasher, Bores, Schlossberg, Conway, "Other", and Undecided. Three
of the four are Democratic-partisan-sponsored; the model does not down-weight
them, only sample-size-weights them.

### Pipeline

1. **Sample-size-weighted poll average** across the four polls.
2. **Adjustment.** Shift 1pp from Bores to Lasher to bring the polling
   average closer to the Kalshi market average (rationalized post hoc as an
   endorsement effect).
3. **Undecided allocation.** Allocate the ~26% undecided proportionally to
   each candidate's current named support — no directional assumption.
4. **Dirichlet sampling.** Treat the resulting mean shares as the center of
   a Dirichlet with total concentration `alpha_0 = 80`. This calibrates the
   Lasher–Bores gap distribution to look roughly polling-error-shaped and
   pins Schlossberg's win probability near 5% given his ~9pp deficit.
5. **Turnout.** Eligible voters ~ Normal(310K, 350K); turnout ~ Normal(25%, 35%).
6. **100,000 sims.** For each, draw shares and turnout, compute vote totals,
   pick a winner among Bores / Lasher / Schlossberg (Conway and Other treated
   as non-contenders for the win).

### Outputs

- Percentiles for turnout, each contender's vote share and vote count, and
  the winning margin (both percentage points and raw votes).
- Win frequencies for each candidate.
- **Marginal value of a vote.** For K ∈ {1, 2, 5, 10}, the probability that
  K additional Bores votes flip the election, reported both as a direct
  flip-count and as a local-density extrapolation (density of the vote
  deficit just above zero, times K). The density estimate is much
  lower-variance for small K.
- Ten random sampled elections, printed in full.

## Caveats

- The 1pp Bores→Lasher adjustment is a market-anchoring hack, not a
  principled prior.
- Pollster-house effects are ignored.
- Undecideds break proportionally; a directional break (e.g. late-deciders
  favoring the most-known candidate) is not modeled.
- "Other" and Conway can win in the Dirichlet draws but are excluded from
  the winner tally — fine while their combined mean share is small, would
  need revisiting otherwise.
