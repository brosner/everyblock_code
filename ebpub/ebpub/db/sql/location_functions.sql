-- Add geometric index, which can't be expressed in Django model syntax.
CREATE INDEX db_location_location ON db_location USING GIST (location GIST_GEOMETRY_OPS);

ALTER TABLE db_location ALTER COLUMN location_type_id SET STATISTICS 5;
ALTER TABLE db_location ALTER COLUMN location SET STATISTICS 75;

-- A wrapper function for ST_Intersects() that can deal with geometries of 'GeometryCollection' type.
-- The only restriction is that possible collection geometry is the second argument.
CREATE OR REPLACE FUNCTION intersecting_collection(other geometry, possible_coll geometry) RETURNS boolean AS $$
    BEGIN
        IF (GeometryType(possible_coll) = 'GEOMETRYCOLLECTION') THEN
            FOR i IN 1..ST_NumGeometries(possible_coll) LOOP
                IF ST_Intersects(ST_GeometryN(possible_coll, i), other) = 't' THEN
                    RETURN 't';
                END IF;
            END LOOP;
            RETURN 'f';
        ELSE
            RETURN ST_Intersects(possible_coll, other);
        END IF;
    END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_loc_area() RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.location IS NOT NULL and NEW.area IS NULL THEN
            NEW.area = ST_Area(ST_Transform(NEW.location, 3395));
        END IF;
        RETURN NEW;
    END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_loc_area BEFORE INSERT OR UPDATE ON db_location
    FOR EACH ROW EXECUTE PROCEDURE set_loc_area();
