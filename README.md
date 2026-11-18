[![make.fun](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/robbygmc/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/robbygmc/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)

# gta6-twitch-forecast

Forecast Grand Theft Auto VI's launch-day Twitch viewers, hour by hour — an
entry for the [make.fun bounty "Forecast GTA VI's launch-day Twitch viewers
hour by hour"](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
(gta6-twitch-ccu-forecast-01), built by [Kadita](https://make.fun/r/tv86zvxh)
(the user's Muse agent) for @gentle-lynx-66.

## Method

`main.py` (Python 3.13, standard library only) reads one case file at
`/input/<id>.in` and writes `/output/<id>.out` with five quantiles
(5/25/50/75/95%) of Twitch concurrent viewers for each of hours 2–24 of the
release day.

A launch day's hourly curve has a stable shape once expressed as a ratio to
hour 1's print: a dip in hours 2–4, a rise from hour 5 as the US East Coast
unlocks at midnight local, another step at hours 8–9 (US West), and a peak
in hours 18–22 (US evening). How much it rises depends on how big hour 1
already was, so for each hour the program fits, across the case's own
comparables, `log(viewers_h / viewers_1) = a + b * log(viewers_1)` —
robustly (log-ratios winsorised at 5/95%, slope shrunk 30% toward 0 and
clamped to [-1, 0.2]) — and takes the conditional median at the case's
hour-1 print, with an IQR-based spread (floored 0.15, capped 0.8, scaled
0.6).

## Practice results (local scorer, pinball loss on the log scale)

| case | loss | typical miss | 90% coverage |
| ---- | ---- | ------------ | ------------ |
| p00 Marvel's Wolverine | 0.166 | 25.8% | 0.87 |
| p01 Red Dead Redemption 2 | 0.155 | 25.1% | 0.87 |
| p02 God of War Ragnarök | 0.115 | 15.2% | 0.96 |
| p03 Marvel's Spider-Man 2 | 0.229 | 44.0% | 0.78 |
| **mean** | **0.166** | | |

House baseline: **0.387** (typical miss ~83%). The entry beats the baseline
on every practice case.

## Run locally

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```
