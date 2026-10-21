# Frozen packet helper contract

Input files: S01_WDI原始观测.json is an unmodified two-element WDI API
response; S02_指标定义汇编.json contains three named raw API responses plus
their retrieval provenance; S04_待审旧稿D0.xlsx contains the original internal
draft; S06_版本与授权.json is an explicitly fictional business contract.
S03 and S05 explain source meanings and the work request.

Select the latest approved chief-analyst version effective no later than
the supplied offset-aware as_of. The helper supports a real_gdp_review
contract, not a nominal market-size or PPP project. Its countries, years,
baseline and diagnostic tolerance come from that contract, not its filename.
The tolerance is a team reconciliation convention, not a World Bank rule.

Require unique country/year/indicator keys, a complete 72-record response,
one page, finite positive GDP levels, finite official percentage changes,
three matching indicator definitions, and a snapshot update date no later
than as_of. Never zero-fill missing observations or resolve duplicate keys
by arrival order. Preserve the source's actual lastupdated as a dataset
update field, not an individual country's announcement date.

Per country/year: current USD and constant 2015 USD levels, official annual
percentage change, constant-price index (2019=100). Starting in 2020,
derive real growth and nominal-dollar growth as 100*(this/prior-1), and
reconcile the former to the supplied official percentage. A percentage-point
difference is subtraction of percentage values, not relative percent change.
2019-derived growth and delta stay null: the packet has no 2018 level.
The official 2019 growth observation may be retained, clearly labelled as
published rather than independently reconstructed from this packet.

The draft's numerator/denominator indicator IDs and exact values are
preserved as evidence. Mixed-price growth is invalid; same current-dollar
ratios are nominal-dollar changes, not real growth. Diagnosing that original
draft does not identify a World Bank vintage revision. No earlier official
vintage is supplied, so vintage attribution is unresolved, not reconstructed.

Output binds the actual raw inputs, this entrypoint/reference/script and the
selected contract. Deterministic results contain no wall-clock execution claim.
Local artifact hashes show which files were processed, not a trusted execution
signature, expert review or proof of any live external business action.
