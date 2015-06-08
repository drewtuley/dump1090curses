create table if not exists registration (
    icao_code text primary key,
    registration text,
    created datetime
);

CREATE INDEX if not exists reg_idx on registration(icao_code);

CREATE TABLE IF NOT EXISTS observation (
    instance int,
    icao_code text,
    starttime datetime,
    endtime datetime null
);

CREATE INDEX IF NOT EXISTS obv_idx on observation(instance, icao_code);

CREATE TABLE IF NOT EXISTS location (
    name text primary key,
    latitude float,
    longitude float
);

