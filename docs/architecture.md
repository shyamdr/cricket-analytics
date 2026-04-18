# Architecture

Visual reference for the InsideEdge / cricket-analytics platform. Complements the text description in the README and the detail in `.kiro/steering/project-architecture.md`.

## System Overview

```mermaid
flowchart TB
    subgraph External["External sources"]
        CS[Cricsheet<br/>JSON + CSV]
        ESPN[ESPN Cricinfo<br/>scraped via Playwright]
        OM[Open-Meteo<br/>historical weather API]
        OSM[OpenStreetMap<br/>Nominatim geocoding]
    end

    subgraph Pipeline["Data pipeline - Dagster orchestrated"]
        direction TB
        Ingest[Ingestion<br/>src/ingestion/]
        Enrich[Enrichment<br/>src/enrichment/]
        DBT[dbt transformations<br/>src/dbt/]
    end

    subgraph Storage["DuckDB - data/cricket.duckdb"]
        direction TB
        Bronze[Bronze<br/>raw + enrichment tables]
        Silver[Silver<br/>12 staging models]
        Gold[Gold<br/>9 analytics models]
    end

    subgraph Serving["Serving layer"]
        API[FastAPI<br/>9 routers]
        UI[Streamlit<br/>legacy internal]
    end

    subgraph Consumers["Consumers"]
        Web[Next.js frontend<br/>Vercel]
        Ops[Ad-hoc SQL<br/>DuckDB CLI]
    end

    CS --> Ingest
    ESPN --> Enrich
    OM --> Enrich
    OSM --> Enrich

    Ingest --> Bronze
    Enrich --> Bronze
    Bronze --> DBT
    DBT --> Silver
    Silver --> DBT
    DBT --> Gold

    Gold --> API
    Gold --> UI
    API --> Web
    Gold --> Ops
```

## Medallion data flow

```mermaid
flowchart LR
    subgraph B["Bronze (raw)"]
        BM[bronze.matches]
        BD[bronze.deliveries]
        BP[bronze.people]
        BEM[bronze.espn_matches]
        BEB[bronze.espn_ball_data]
        BW[bronze.weather]
        BVC[bronze.venue_coordinates]
    end

    subgraph S["Silver (staged)"]
        SM[stg_matches]
        SD[stg_deliveries]
        SP[stg_people]
        SEM[stg_espn_matches]
        SEB[stg_espn_ball_data]
        SWH[stg_weather_hourly]
        SWD[stg_weather_daily]
        SVC[stg_venue_coordinates]
    end

    subgraph G["Gold (analytics)"]
        DM[dim_matches]
        DP[dim_players]
        DT[dim_teams]
        DV[dim_venues]
        FD[fact_deliveries<br/>incremental]
        FB[fact_batting_innings]
        FBO[fact_bowling_innings]
        FMS[fact_match_summary]
        FW[fact_weather]
    end

    BM --> SM
    BD --> SD
    BP --> SP
    BEM --> SEM
    BEB --> SEB
    BW --> SWH
    BW --> SWD
    BVC --> SVC

    SM --> DM
    SEM --> DM
    SP --> DP
    SM --> DP
    SM --> DT
    SM --> DV
    SVC --> DV
    SEM --> DV

    SM --> FD
    SD --> FD
    SM --> FB
    SD --> FB
    SM --> FBO
    SD --> FBO
    SM --> FMS
    SD --> FMS

    SWH --> FW
    SWD --> FW
```

Note: ESPN silver models (stg_espn_*) and weather/geocoding silver models are gated behind the `source_exists` macro — if the bronze table hasn't been created by enrichment, silver returns an empty-shape result and gold still builds.

## Dagster asset graph

```mermaid
flowchart LR
    subgraph IngestionAssets["Ingestion assets (Python)"]
        BMatch[bronze_matches]
        BPeople[bronze_people]
    end

    subgraph DbtAssets["dbt assets 21 models"]
        SilverGroup[Silver 12 models]
        GoldGroup[Gold 9 models]
    end

    subgraph EnrichmentAssets["Enrichment assets (Python)"]
        EspnMatch[espn_match_enrichment]
        EspnBall[espn_ball_enrichment]
        Geo[geocode_venue_coordinates]
        Img[espn_image_enrichment]
        Weather[weather_enrichment]
    end

    BMatch --> SilverGroup
    BPeople --> SilverGroup
    SilverGroup --> GoldGroup

    BMatch --> EspnMatch
    EspnMatch --> EspnBall
    BMatch --> Geo
    BMatch --> Weather
    EspnMatch --> Weather
    BMatch --> Img

    EspnMatch --> SilverGroup
    EspnBall --> SilverGroup
    Geo --> SilverGroup
    Weather --> SilverGroup
```

Jobs:
- `full_pipeline` — materializes everything
- `daily_refresh` — `AssetSelection.all()` with ingestion configured for the `recent_7` profile
- `enrichment_backfill` — enrichment group only, for historical scraping

Schedule: `daily_refresh` at 06:00 UTC.

## Request path (frontend → DB)

```mermaid
sequenceDiagram
    participant Browser
    participant Vercel as Vercel<br/>Next.js SSR
    participant Render as Render<br/>FastAPI
    participant DuckDB as DuckDB<br/>baked into image

    Browser->>Vercel: GET /matches/335982
    Vercel->>Render: GET /api/v1/matches/335982
    Render->>DuckDB: SELECT from main_gold.dim_matches
    DuckDB-->>Render: row
    Render->>DuckDB: SELECT from main_gold.fact_match_summary
    DuckDB-->>Render: rows
    Render-->>Vercel: JSON
    Vercel-->>Browser: rendered HTML
```

Note: Render free tier sleeps after 15 minutes idle. First request after idle takes ~30 seconds to spin up the container.

## Deployment topology

```mermaid
flowchart TB
    subgraph Dev["Developer machine"]
        Code[Python + Next.js code]
        LocalDB[(local DuckDB)]
    end

    subgraph GH["GitHub"]
        Repo[shyamdr/cricket-analytics]
        VRepo[apps/web nested git]
        CI[GitHub Actions CI]
    end

    subgraph Prod["Production"]
        V[Vercel<br/>Next.js frontend]
        R[Render<br/>FastAPI + DuckDB]
    end

    Code -- git push --> Repo
    Code -- git push --> VRepo
    Repo --> CI
    CI -- on main --> R
    VRepo -- auto-deploy --> V
    V -- /api/v1/* --> R
```

- CI does not deploy directly — Render pulls from `main` via its own GitHub integration
- The DuckDB file is rebuilt from scratch inside `Dockerfile.api` on every Render deploy (ingest + dbt seed + dbt run)
- Vercel deploys from the nested `apps/web/` git repo, independent of the root repo

## For more detail

- Per-model columns and grains — `.kiro/steering/dbt-models-reference.md`
- API endpoints — `.kiro/steering/api-endpoints-reference.md`
- Decisions and rationale — `docs/adr/`
- Current progress and backlog — `.kiro/steering/progress.md`
