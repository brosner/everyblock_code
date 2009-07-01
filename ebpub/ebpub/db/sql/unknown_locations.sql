-- Create an "Unknown X" location for every significant location that doesn't
-- already have one.
insert into db_location ("location_type_id", "name", "normalized_name", "slug", "location", "centroid", "display_order", "city", "source", "area", "population", "is_public", "description")
select lt.id, 'Unknown '||lt.plural_name, 'UNKNOWN', 'unknown', null, null, 0, '', '', null, null, false, ''
from db_locationtype lt
where lt.is_significant = true and
not exists (select 1 from db_location l where lt.id=l.location_type_id and slug='unknown');
