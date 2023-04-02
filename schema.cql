CREATE KEYSPACE placeapp
WITH replication = {'class': 'SimpleStrategy', 'replication_factor' : 3};

CREATE TABLE placeapp.urls (
    url text,
    fetched timestamp,
    size bigint,
    PRIMARY KEY (url)
) WITH compaction = { 'class' : 'SizeTieredCompactionStrategy' };

CREATE TABLE placeapp.pixels (
    board_id int,
    x int,
    y int,
    modified timestamp,
    user text,
    PRIMARY KEY ((x, y), board_id, modified)
) WITH compaction = { 'class' : 'SizeTieredCompactionStrategy' };