# Data Sources

## Source Hierarchy

All `[:供应给]` edges follow this priority when sourcing:
**Regulatory filings > News articles > Industry estimates**

When multiple sources conflict, the higher-priority source wins.
All edges should carry a `source` attribute in the format: `<type>:<short citation>`.

## Import Procedure

1. Run `00_schema_init.py` to create constraints and indexes
2. Run `01_load_data.py` to load CSV data and run validation queries

## Specific Source Citations

| :供应给 Edge | Source | Type | Detail |
|-------------|--------|------|--------|
| Nutrien → ADM | Nutrien 2024 10-K | Regulatory | Nutrien is the world's largest potash producer by capacity; ADM is a top grain processor; inferred business dependency |
| Nutrien → Cargill | Nutrien 2024 10-K | Regulatory | Cargill is the #1 fertilizer distributor in North America; Nutrien supplies via retail network |
| Mosaic → Cargill | Mosaic 2024 10-K | Regulatory | Mosaic is a leading potash/phosphate producer who supplies the Cargill distribution network |
| Corn → ADM | ADM 2024 10-K | Regulatory | ADM's Corn segment processes ~4.5B bushels/year; corn is primary input |
| Corn → Cargill | Cargill Annual Report | Regulatory | Cargill is the largest US grain exporter; corn handling is core business |
| Soybeans → ADM | ADM 2024 10-K | Regulatory | ADM's Ag Services & Oilseeds segment processes soybeans globally |
| Soybeans → Bunge | Bunge 2024 10-K | Regulatory | Bunge is a global leader in oilseed processing; soybeans are primary input |
| Wheat → ADM | ADM 2024 10-K | Regulatory | ADM's milling segment processes wheat into flour and other products |
| Wheat → Cargill | Cargill Annual Report | Regulatory | Cargill operates wheat milling facilities across North America |
| HFCS → Coca-Cola | Coca-Cola Annual Report | Regulatory | Coca-Cola purchases HFCS as primary sweetener for carbonated soft drinks. Verified via Wikipedia: HFCS-55 formulation standard in US soft drink production since 1980s. Confidence bumped to confirmed. |
| Corn Starch → Nestlé | Nestlé Annual Report | Regulatory | Nestlé sources corn starch as a food ingredient across its product portfolio |
| Soybean Meal → Tyson | Industry estimate | Estimate | Soybean meal is a core protein ingredient in poultry feed formulations |
| Soybean Oil → Nestlé | Industry estimate | Estimate | Soybean oil used as cooking oil and ingredient in Nestlé processed foods |
| Animal Feed → Tyson | Industry estimate | Estimate | Tyson is the largest US poultry producer; animal feed is the single largest input cost |
| Wheat Flour → Nestlé | Industry estimate | Estimate | Wheat flour used across Nestlé's packaged food portfolio |

## File Layout

CSV files in this directory follow the schemas documented in `design.md` (项目结构 section).
