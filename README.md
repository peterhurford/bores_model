# bores_model

A Monte Carlo model of the NY-17 Democratic primary, focused on Mike Bores'
chances and the marginal value of a single additional vote.

## Installation and running

Requires Python 3.10+.

```
pip install -r requirements.txt
python bores.py
```

A sample run is checked in as `model_output.txt`. Re-running will produce
slightly different numbers because the Monte Carlo is unseeded; set
`random.seed(...)` and `np.random.seed(...)` at the top of `bores.py` if you
want reproducibility.

## The model

### Pipeline

1. **Weighted poll average.** Each poll is weighted by sample size *and* by an
   exponential time-decay (90-day half-life, anchored to `TODAY = 2026-06-09`),
   so the more recent Honan poll carries weight without entirely zeroing out the
   May polls. Per-candidate averages are then normalized to sum to 1, which is
   necessary because partial polls (Honan) leave some fields out.
2. **Adjustment (currently disabled).** `APPLY_ADJUSTMENT = False`. The code
   retains an optional 1pp shift from Bores to Lasher — originally a hack to pull
   the polling average toward the Kalshi market average — but it is off by
   default. Flip the flag to re-enable it.
3. **Undecided allocation.** Allocate the undecided bloc proportionally to each
   candidate's current named support — no directional assumption about who they
   break for.
4. **Dirichlet sampling.** Treat the resulting mean shares as the center of a
   Dirichlet with total concentration `ALPHA_0 = 80`. This calibrates the
   Lasher–Bores gap distribution to look roughly polling-error-shaped and pins
   Schlossberg's win probability near 5% given his mean deficit.
5. **Turnout.** Eligible voters ~ Normal(310K, 350K); turnout ~ Normal(25%, 35%).
6. **100,000 sims.** For each, draw shares and turnout, compute vote totals, and
   pick a winner among Bores / Lasher / Schlossberg (Conway and Other are
   treated as non-contenders for the win).

### Outputs

- **Percentiles** for turnout, each contender's vote share and vote count, and
  the winning margin (both percentage points and raw votes).
- **Win frequencies** for each candidate.
- **Marginal value of a vote.** For K ∈ {1, 2, 5, 10}, the probability that K
  additional Bores votes flip the election, reported both as a direct flip-count
  and as a local-density extrapolation (density of the vote deficit just above
  zero, times K). The density estimate is much lower-variance for small K.
- **Dollar value of a marginal vote.** Multiplies the per-vote flip probability
  by the value of a Bores win — modeled as Lognormal with a 90% CI of
  $20M–$150M — and reports the EV per marginal vote across several assumed win
  values.
- **Ten random sampled elections,** printed in full.

See `model_output.txt` for a sample run.
