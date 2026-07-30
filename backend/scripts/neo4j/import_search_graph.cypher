// Idempotent graph import for online search.
CREATE CONSTRAINT listing_node_id_unique IF NOT EXISTS FOR (n:Listing) REQUIRE n.listing_node_id IS UNIQUE;
CREATE CONSTRAINT amenity_id_unique IF NOT EXISTS FOR (n:Amenity) REQUIRE n.amenity_id IS UNIQUE;
CREATE CONSTRAINT ward_id_unique IF NOT EXISTS FOR (n:Ward) REQUIRE n.ward_id IS UNIQUE;
CREATE CONSTRAINT street_id_unique IF NOT EXISTS FOR (n:Street) REQUIRE n.street_id IS UNIQUE;
CREATE CONSTRAINT geo_cluster_id_unique IF NOT EXISTS FOR (n:GeoCluster) REQUIRE n.cluster_id IS UNIQUE;
CREATE INDEX listing_id_idx IF NOT EXISTS FOR (n:Listing) ON (n.listing_id);
CREATE INDEX listing_property_type_idx IF NOT EXISTS FOR (n:Listing) ON (n.property_type);
CREATE INDEX listing_price_range_idx IF NOT EXISTS FOR (n:Listing) ON (n.price_range);
CREATE INDEX listing_area_idx IF NOT EXISTS FOR (n:Listing) ON (n.area);
CREATE INDEX listing_bedrooms_idx IF NOT EXISTS FOR (n:Listing) ON (n.bedrooms);
CREATE INDEX amenity_category_idx IF NOT EXISTS FOR (n:Amenity) ON (n.category);

LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_listing_nodes.csv' AS row
WITH row, row.`listing_node_id:ID(Listing)` AS node_id WHERE node_id IS NOT NULL AND node_id <> ''
MERGE (n:Listing {listing_node_id: node_id})
SET n.listing_id = row.`listing_id:string`, n.listing_type = row.`listing_type:string`,
    n.property_type = row.`property_type:string`, n.city_province = row.`city_province:string`,
    n.title = row.`title:string`, n.address = row.`address:string`, n.description = row.`description:string`,
    n.legal_status = row.`legal_status:string`, n.furnishing = row.`furnishing:string`,
    n.balcony_direction = row.`balcony_direction:string`, n.house_direction = row.`house_direction:string`,
    n.ward_commune = row.`ward_commune:string`, n.former_admin_area = row.`former_admin_area:string`,
    n.geo_cluster_150m = row.`geo_cluster_150m:string`, n.data_quality_flags = row.`data_quality_flags:string`,
    n.posted_date = CASE WHEN row.`posted_date:date` IS NULL OR row.`posted_date:date` = '' THEN null ELSE date(row.`posted_date:date`) END,
    n.price_range = toFloatOrNull(row.`price_range:float`), n.area = toFloatOrNull(row.`area:float`),
    n.bedrooms = toIntegerOrNull(row.`bedrooms:float`), n.bathrooms = toIntegerOrNull(row.`bathrooms:float`),
    n.pool = toBooleanOrNull(row.`pool:boolean`), n.gym = toBooleanOrNull(row.`gym:boolean`),
    n.park = toBooleanOrNull(row.`park:boolean`), n.bbq = toBooleanOrNull(row.`bbq:boolean`),
    n.kids_playground = toBooleanOrNull(row.`kids_playground:boolean`),
    n.sports_court = toBooleanOrNull(row.`sports_court:boolean`),
    n.security_24h = toBooleanOrNull(row.`security_24h:boolean`),
    n.reception = toBooleanOrNull(row.`reception:boolean`), n.elevator = toBooleanOrNull(row.`elevator:boolean`),
    n.parking = toBooleanOrNull(row.`parking:boolean`), n.river_view = toBooleanOrNull(row.`river_view:boolean`),
    n.park_view = toBooleanOrNull(row.`park_view:boolean`), n.city_view = toBooleanOrNull(row.`city_view:boolean`),
    n.balcony = toBooleanOrNull(row.`balcony:boolean`), n.garden = toBooleanOrNull(row.`garden:boolean`),
    n.garage = toBooleanOrNull(row.`garage:boolean`), n.terrace = toBooleanOrNull(row.`terrace:boolean`),
    n.latitude = toFloatOrNull(row.`latitude:float`), n.longitude = toFloatOrNull(row.`longitude:float`),
    n.location = CASE WHEN row.`latitude:float` IS NULL OR row.`latitude:float` = '' OR row.`longitude:float` IS NULL OR row.`longitude:float` = ''
                      THEN null ELSE point({latitude: toFloat(row.`latitude:float`), longitude: toFloat(row.`longitude:float`)}) END;

LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_amenity_nodes.csv' AS row
WITH row, row.`amenity_id:ID(Amenity)` AS node_id WHERE node_id IS NOT NULL AND node_id <> ''
MERGE (n:Amenity {amenity_id: node_id})
SET n.name = row.`name:string`, n.category = row.`category:string`, n.street = row.`street:string`,
    n.address = row.`address:string`, n.latitude = toFloatOrNull(row.`latitude:float`),
    n.longitude = toFloatOrNull(row.`longitude:float`),
    n.location = CASE WHEN row.`latitude:float` IS NULL OR row.`latitude:float` = '' OR row.`longitude:float` IS NULL OR row.`longitude:float` = ''
                      THEN null ELSE point({latitude: toFloat(row.`latitude:float`), longitude: toFloat(row.`longitude:float`)}) END;

LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_ward_nodes.csv' AS row
WITH row, row.`ward_id:ID(Ward)` AS node_id WHERE node_id IS NOT NULL AND node_id <> ''
MERGE (n:Ward {ward_id: node_id})
SET n.name = row.`name:string`, n.ward_type = row.`ward_type:string`,
    n.former_admin_area = row.`former_admin_area:string`, n.city_province = row.`city_province:string`;

LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_street_nodes.csv' AS row
WITH row, row.`street_id:ID(Street)` AS node_id WHERE node_id IS NOT NULL AND node_id <> ''
MERGE (n:Street {street_id: node_id}) SET n.name = row.`name:string`, n.ward_id = row.`ward_id:string`;

LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_geo_cluster_nodes.csv' AS row
WITH row, row.`cluster_id:ID(GeoCluster)` AS node_id WHERE node_id IS NOT NULL AND node_id <> ''
MERGE (n:GeoCluster {cluster_id: node_id})
SET n.centroid_latitude = toFloatOrNull(row.`centroid_latitude:float`),
    n.centroid_longitude = toFloatOrNull(row.`centroid_longitude:float`),
    n.listing_count = toIntegerOrNull(row.`listing_count:int`);

LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_listing_near_amenity_relationships.csv' AS row
MATCH (l:Listing {listing_node_id: row.`:START_ID(Listing)`})
MATCH (a:Amenity {amenity_id: row.`:END_ID(Amenity)`})
MERGE (l)-[r:NEAR_AMENITY]->(a)
SET r.category = row.`category:string`, r.rank = toIntegerOrNull(row.`rank:int`),
    r.driving_distance_km = toFloatOrNull(row.`driving_distance_km:float`),
    r.driving_duration_min = toFloatOrNull(row.`driving_duration_min:float`),
    r.threshold_km = toFloatOrNull(row.`threshold_km:float`);

LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_listing_in_ward_relationships.csv' AS row
MATCH (l:Listing {listing_node_id: row.`:START_ID(Listing)`}) MATCH (w:Ward {ward_id: row.`:END_ID(Ward)`}) MERGE (l)-[:IN_WARD]->(w);
LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_listing_on_street_relationships.csv' AS row
MATCH (l:Listing {listing_node_id: row.`:START_ID(Listing)`}) MATCH (s:Street {street_id: row.`:END_ID(Street)`}) MERGE (l)-[:ON_STREET]->(s);
LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_listing_in_cluster_relationships.csv' AS row
MATCH (l:Listing {listing_node_id: row.`:START_ID(Listing)`}) MATCH (g:GeoCluster {cluster_id: row.`:END_ID(GeoCluster)`}) MERGE (l)-[:IN_CLUSTER]->(g);
LOAD CSV WITH HEADERS FROM 'file:///real_estate_graph_ready/neo4j_street_in_ward_relationships.csv' AS row
MATCH (s:Street {street_id: row.`:START_ID(Street)`}) MATCH (w:Ward {ward_id: row.`:END_ID(Ward)`}) MERGE (s)-[:IN_WARD]->(w);

CREATE POINT INDEX listing_location_idx IF NOT EXISTS FOR (n:Listing) ON (n.location);
CREATE POINT INDEX amenity_location_idx IF NOT EXISTS FOR (n:Amenity) ON (n.location);
CREATE FULLTEXT INDEX listing_text_idx IF NOT EXISTS FOR (n:Listing) ON EACH [n.title, n.address, n.description];
CALL db.awaitIndexes(300);
