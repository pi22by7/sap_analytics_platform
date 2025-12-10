# 1. Generator (refer to the challenge doc again after writing logic)
## Arch
- single class as given in doc, driven by conf
- dataclass for config
- out: parquet
- keep lfa1 and mara in mem for faster references

## exec
- MARA and LFA1 in parallel since no deps/FKs, add base_price to MARA as price logic anchor. add perf_bias to LFA1 to model Delays
- VENDOR_CONTRACTS will depend on those two.
- EKKO depends on LFA1
- EKPO depends on EKKO and MARA
- EKBE depends on EKPO

## Pareto: 20% of Vendors = 80% Spend
- spend_potential weight to every vendor ID
- top 20 - weight = 100, bottom 80, weight = 1, very heavy but we can iterate later.
- split 10% as PREF and 90 as STD
- 5% will be SPERR = X

## Pricing
- base_price based on category 
- when bsart = NB, price = 0.90 * base_price (we can randomize the multiplier later for 10-15 range)
- gaussian noise for +-15% variance

## Delivery Delays
- perf_bias for the consistent delay requirement, this will give them "personality"
- EINDT = PO Date + lead time
- - actual = eindt + perf_bias + random_delay (to add variance on top of the bias)

## PO Patterns
- date probability np array, Q4 days get 1.2-1.3x weight
- do large orders first
- check if large order or not, if yes, force BSART = NB, multiply the randomly generated order quantity by 10
