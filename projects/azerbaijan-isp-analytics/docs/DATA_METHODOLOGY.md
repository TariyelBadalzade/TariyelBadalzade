# Data methodology and simulation assumptions

All customer-level records are synthetic. No company database or customer list was used. The geographic allocation is a national-style simulation, not an ISP's actual footprint, subscriber market share, or an official fixed-broadband estimate.

## Geographic method

Administrative-unit weights equal population at 1 January 2026 multiplied by the corresponding economic region's 2025 household Internet-access rate. The largest-remainder method allocates exactly 10,000 subscribers. Baku is then split across its 12 districts in proportion to the same population table. Household Internet access includes connection types beyond fixed broadband; population is a proxy for households, so these weights are an approximation.

Eastern Zangazur's missing Internet-access rate is imputed with the national 90.8% rate. Population registration does not establish physical service availability, particularly for resettlement areas. The synthetic operator is assumed to serve every listed administrative unit. Existing map geometry may lag current administrative boundaries.

## Public sources

- State Statistical Committee, population at 1 January 2026, table 2.4: https://stat.gov.az/source/demoqraphy/ap/en/2_4en.xls
- Azerbaijani labels for the same table: https://stat.gov.az/source/demoqraphy/ap/az/2_4.xls
- State Statistical Committee, 2025 household Internet access by economic region, table 2.29: https://stat.gov.az/source/digital_development/en/002_29en.xls
- Public retail tariff reference, accessed 21 October 2026: https://www.az-net.az/ — 100/150/250/500/750/1000 Mbps at 25/30/36/40/45/50 AZN per month.
- Public single static-IP monthly fee reference, accessed 21 October 2026: https://aztelekom.az/az-en/internet-en/individual-static-ip-en — 5 AZN.

The references anchor the geography and price levels; the dataset does not represent either provider's customers. Retail rates are a current snapshot, not historical transaction prices. The [geographic distribution CSV](../data/geographic_distribution.csv) records the public population/access inputs and exact allocated subscriber counts.

## Explicit simulation assumptions

Business mix, tariff take-up by location, connection state, connection technology, acquisition trend, churn, suspension, usage, balances, payments, penalties, and static-IP adoption are modeling assumptions, not measured Azerbaijan statistics. Business packages and extra-address billing are fictional. Urban locations have a larger assumed premium/business mix; lower-speed published retail plans are more common elsewhere.

Reporting period: 1 January 2024–21 October 2026. Status dates are distributed through account tenure rather than concentrated in one month. Active accounts have no termination date. Speeds are advertised Mbps; upload/download columns contain simulated session bytes, not speed measurements.

## Billing grain

butun_musteriler has 10,000 unique subscribers. static_ip has 10,000 monthly invoices: 500 selected active accounts times 20 periods (March 2025–October 2026). Business accounts are more likely to receive static IP in the simulation. Most invoices use 5 AZN for one address; selected businesses have assumed multi-address charges of 10 or 15 AZN. Static-IP user visuals count distinct account codes, while fee/payment totals sum invoice rows. Monthly invoice starts are not new signups.

Identifiers, contact fields, document/tax fields, passwords, MACs and IPs remain visibly synthetic. IPs use documentation ranges and repeat intentionally. No operational credentials are present.
