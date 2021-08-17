import psycopg2

from scrape import countries, get_regions, get_subregions, get_locations, get_webcams


# --- GENERAL DB UPDATER ---

# updates the database for a given set of countries
def update_database(countries=countries, subregions=False):
    print('updating database')
    for c in countries:
        print('\nCOUNTRY:', c)
        if subregions:
            for r, s_list in get_subregions(c).items():
                print('REGION:', r)
                for s in s_list:
                    print('- SUBREGION:', s)
                    sql_query(f"INSERT INTO subregions (name, region) (VALUES ('{s}', '{r}'));")
        for r in get_regions(c):
            print('REGION:', r)
            sql_query(f"INSERT INTO regions (name, country) (VALUES ('{r}', '{c}'));")
            for l in get_locations(r, c):
                print('- LOCATION:', l)
                sql_query(f"INSERT INTO locations (name, region, subregion) (VALUES ('{l}', '{r}', '<missing>'));")
                for w in get_webcams(l, r, c):
                    sql_query(f"INSERT INTO webcams (camid, name, location, url, sealevel, viewdirection) (VALUES "
                              f"('{w[1]}', '{w[0]}', '{l}', '<missing>', '{w[2]}', '{w[3]}'));")
    sql_query("UPDATE regions r SET locations = "
              "(SELECT COUNT(DISTINCT r.name) FROM locations l WHERE l.region = r.name);")
    sql_query("UPDATE locations l SET webcams = "
              "(SELECT COUNT(DISTINCT w.camid) FROM webcams w WHERE w.location = l.name AND w.url NOT LIKE '%<missing>%');")
    print('update done')


# --- QUERY TOOLS ---

# executes an sql query on the webcam database
def sql_query(query):
    con = psycopg2.connect(port=***REMOVED***, database='postgres', user='postgres')
    cur = con.cursor()
    result = None
    try:
        cur.execute("SET search_path = 'webcams';")
        cur.execute(query)
        con.commit()
        result = list(cur.fetchall())
    except Exception:
        pass
    cur.close()
    con.close()
    return result


# generates an sql query clause with conditions based on a search term
def generate_search(col, term):
    words = term.lower().split(' ')
    search = "LOWER(" + col + ") LIKE '%" + words[0] + "%'"
    for w in words[1:]:
        search += " AND LOWER(" + col + ") LIKE '%" + w + "%'"
    return search


# --- HELPER METHODS ---

# retrieves a region's country
def get_country(region):
    result = sql_query(f"SELECT c.internal FROM countries c join regions r on r.country = c.name "
                       f"WHERE r.name = '{region}'")
    if result:
        return result[0][0]
    else:
        return None