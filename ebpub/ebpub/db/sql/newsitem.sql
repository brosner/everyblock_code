-- Add geometric index, which can't be expressed in Django model syntax.
CREATE INDEX db_newsitem_location ON db_newsitem USING GIST (location GIST_GEOMETRY_OPS);

-- Add partial indexes for the value columns. We only want to index values that are not NULL.
CREATE INDEX db_attribute_varchar01 ON db_attribute (varchar01) WHERE varchar01 IS NOT NULL;
CREATE INDEX db_attribute_varchar02 ON db_attribute (varchar02) WHERE varchar02 IS NOT NULL;
CREATE INDEX db_attribute_varchar03 ON db_attribute (varchar03) WHERE varchar03 IS NOT NULL;
CREATE INDEX db_attribute_varchar04 ON db_attribute (varchar04) WHERE varchar04 IS NOT NULL;
CREATE INDEX db_attribute_varchar05 ON db_attribute (varchar05) WHERE varchar05 IS NOT NULL;
CREATE INDEX db_attribute_date01 ON db_attribute (date01) WHERE date01 IS NOT NULL;
CREATE INDEX db_attribute_date02 ON db_attribute (date02) WHERE date02 IS NOT NULL;
CREATE INDEX db_attribute_date03 ON db_attribute (date03) WHERE date03 IS NOT NULL;
CREATE INDEX db_attribute_date04 ON db_attribute (date04) WHERE date04 IS NOT NULL;
CREATE INDEX db_attribute_date05 ON db_attribute (date05) WHERE date05 IS NOT NULL;
CREATE INDEX db_attribute_time01 ON db_attribute (time01) WHERE time01 IS NOT NULL;
CREATE INDEX db_attribute_time02 ON db_attribute (time02) WHERE time02 IS NOT NULL;
CREATE INDEX db_attribute_datetime01 ON db_attribute (datetime01) WHERE datetime01 IS NOT NULL;
CREATE INDEX db_attribute_datetime02 ON db_attribute (datetime02) WHERE datetime02 IS NOT NULL;
CREATE INDEX db_attribute_datetime03 ON db_attribute (datetime03) WHERE datetime03 IS NOT NULL;
CREATE INDEX db_attribute_datetime04 ON db_attribute (datetime04) WHERE datetime04 IS NOT NULL;
CREATE INDEX db_attribute_bool01 ON db_attribute (bool01) WHERE bool01 IS NOT NULL;
CREATE INDEX db_attribute_bool02 ON db_attribute (bool02) WHERE bool02 IS NOT NULL;
CREATE INDEX db_attribute_bool03 ON db_attribute (bool03) WHERE bool03 IS NOT NULL;
CREATE INDEX db_attribute_bool04 ON db_attribute (bool04) WHERE bool04 IS NOT NULL;
CREATE INDEX db_attribute_bool05 ON db_attribute (bool05) WHERE bool05 IS NOT NULL;
CREATE INDEX db_attribute_int01 ON db_attribute (int01) WHERE int01 IS NOT NULL;
CREATE INDEX db_attribute_int02 ON db_attribute (int02) WHERE int02 IS NOT NULL;
CREATE INDEX db_attribute_int03 ON db_attribute (int03) WHERE int03 IS NOT NULL;
CREATE INDEX db_attribute_int04 ON db_attribute (int04) WHERE int04 IS NOT NULL;
CREATE INDEX db_attribute_int05 ON db_attribute (int05) WHERE int05 IS NOT NULL;
CREATE INDEX db_attribute_int06 ON db_attribute (int06) WHERE int06 IS NOT NULL;
CREATE INDEX db_attribute_int07 ON db_attribute (int07) WHERE int07 IS NOT NULL;

ALTER TABLE db_newsitem ALTER COLUMN schema_id SET STATISTICS 5;
ALTER TABLE db_newsitem ALTER COLUMN item_date SET STATISTICS 75;
