
# A Data and Preprocessing Methods

## Data source
We used the public Transfermarkt-based football dataset from the salimt GitHub repository.
The A-stage pipeline focused on three core files:
- player_profiles.csv
- player_market_value.csv
- player_performances.csv

## Preprocessing overview
We standardized column names, parsed date fields, validated key identifiers, reduced each table to analysis-relevant columns, and saved cleaned intermediate parquet files.

## Position handling
Player positions were mapped into four broad groups:
Goalkeeper, Defender, Midfielder, and Forward.
Records with missing or unmappable position information were excluded from the frozen backbone.

## Merge strategy
The frozen lifecycle backbone was built by merging cleaned player profiles with cleaned market value observations on player_id.
The performance table was intentionally kept separate at this stage, because direct merging on player_id alone would create many-to-many duplication without time alignment.

## Age construction
Age was computed vectorially as the difference between market value date and date of birth, divided by 365.25.

## Backbone filters
The frozen backbone retained observations with:
- positive market value
- age between 14 and 45
- broad position in the four main groups
- at least 3 market value observations per player

## Data quality notes
Date of birth was missing for a small subset of player profiles.
The performance table had substantial missingness in minutes_played, so missing values were preserved rather than aggressively imputed.
