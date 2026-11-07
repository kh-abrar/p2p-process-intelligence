# Data source

## Original dataset
van Dongen, B.F. (2019). BPI Challenge 2019. 4TU.ResearchData.
https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1

Event log of purchase-order handling at a large multinational in coatings and paints (Netherlands). Challenge page: https://icpmconference.org/2019/?p=302

## Copy used in this project
- File: `BPI_Challenge_2019.csv.gz`
- Obtained from: GitHub release `dataset-v1` of `jadzoghaib/processlens`
  https://github.com/jadzoghaib/processlens/releases
- Size: 40,896,616 bytes
- SHA-256: `2a6fae0e5b8feffdb1117af024dd4ba93ad1b096d778ddb0306dd55778b238a7`
- Downloaded: 3 November 2026
- Format: CSV conversion of the original XES log (column names such as `case concept:name`).
- Why this copy: data.4tu.nl timed out from my network on 3 November 2026. The official file can replace this one if the site becomes reachable; the ingest script would then need to read XES.

## Contents (verified after loading)
1,595,923 events, 251,734 cases, 42 activities. These match the counts published with the mirror.

## Placement
Put the file in `data/raw/`. It is excluded from git. Verify before use:

    sha256sum data/raw/BPI_Challenge_2019.csv.gz