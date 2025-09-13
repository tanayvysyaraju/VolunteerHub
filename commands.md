# setting up postgres data base 
createdb volunteer_portal
psql -U postgres -d volunteer_portal -f db/schema.sql