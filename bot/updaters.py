from datetime import datetime
from re import match, findall

from WebcamBot import last_working
from db import update_database, sql_query, generate_search
from scrape import countries, get_regions, get_locations, get_webcams, get_hq_webcams


# --- BUNDLED UPDATE ---


def update_everything(countries=countries):
    update_database(countries)
    update_urls(['bergfex', 'foto-webcam'], countries)
    update_subregions(countries)
    update_metadata(countries)


# --- MANUAL UPDATERS ---


# adds the url column to the webcams table
def update_urls(source, countries=countries, time=findall('\d+', str(datetime.now()).rsplit(':', 1)[0])):
    # initializing new column:
    # sql_query('ALTER TABLE webcams ADD COLUMN url VARCHAR')
    # sql_query("UPDATE webcams SET url = '<missing>' WHERE url ISNULL")

    print('starting to add webcam urls')
    if 'bergfex' in source:
        # starting with the basic bergfex template url, to be replaced: code, date, time, variant
        bergfex_template = 'https://vcdn.bergfex.at/webcams/archive.new/downsized/?/<c>/#yyyy/#mm/#dd/<c>_#yyyy-#mm-#dd_#hh#nn_####.jpg'
        # searching for missing urls only
        for webcam in sql_query("SELECT DISTINCT w.camid FROM webcams w, locations l, regions r "
                                "WHERE url LIKE '%<missing>' "
                                "AND w.location = l.name AND l.region = r.name AND "
                                + generate_search('r.country', ' '.join(countries))):
            # filtering for numeric webcams codes (= bergfex url code)
            if match('^\d+$', webcam[0]):
                # replacing the template with the code and the two variants
                test_url1 = bergfex_template.replace('?', webcam[0][-1]).replace('<c>', webcam[0]).replace('####', '688d47e0ed941b8b')
                test_url2 = bergfex_template.replace('?', webcam[0][-1]).replace('<c>', webcam[0]).replace('####', '801ea6616676539b')
                if 'no picture' not in last_working(webcam[0], test_url1, time.copy()):
                    url = test_url1
                elif 'no picture' not in last_working(webcam[0], test_url2, time.copy()):
                    url = test_url2
                else:
                    print('not matched:', webcam[0])
                    continue
                sql_query(f"UPDATE webcams SET url = '{url}' WHERE camid = '{webcam[0]}'")
                print('url added:', url)
    if 'foto-webcam' in source:
        # possible tailing templates for foto-webcam associated webcams
        tails = ['#yyyy/#mm/#dd/#hh#nn_hu.jpg', '#yyyy/#mm/#dd/#hh#nnl.jpg', '<missing>']
        # searching for all urls that are found at the foto-webcam.eu website
        for webcam, values in get_hq_webcams().items():
            for value in values:
                if '"link":' in value:
                    # fitting the found urls to the different tails
                    url = value.split(':"', 1)[1][0:-1].replace('\\', '')
                    if match('.+(foto-webcam|megacam|picture-cams|wetter|stwo|relix'
                             '|sauerland|sistrans|regensburg|Burglengenfeld|wilhelmsburg|bielefeld|Raas'
                             '|db0noe|reisen-und-hobby|joeeos|marklex).+', url):
                        url = url + tails[0]
                    elif match('.+(terra-hd).+', url):
                        url = url + tails[1]
                    elif match('.+(asam-live|ig-funk).+', url):
                        url = url + tails[2]
                    else:
                        # a webcam url which does not fit the format, was found
                        print('not matched:', url)
                    # try to update this webcam
                    if sql_query(f"SELECT name FROM webcams WHERE camid = '{webcam}'"):
                        sql_query(f"UPDATE webcams SET url = '{url}' WHERE camid = '{webcam}'")
                        print('url added:', url)
                    else:
                        print('url does not exist in database:', url)
    print('adding urls done')


# manually updates the subregions for each location by pulling it out of the top navigation bar
def update_subregions(countries=countries):
    # initializing new column:
    # sql_query('ALTER TABLE locations ADD COLUMN subregion VARCHAR')
    # sql_query("UPDATE locations SET subregion = '<missing>' WHERE subregion ISNULL")

    # flattening the query result list
    locations = [item for sublist in sql_query("SELECT DISTINCT name FROM locations WHERE subregion = '<missing>'")
                 for item in sublist]
    # going through all specified countries, then regions, then picking out the subregion
    for c in countries:
        for r in get_regions(c):
            for (l, sr) in get_locations(r, c, False, True):
                if l in locations:
                    # fixes issue where subregion would have an ' inside its name
                    sr = str(sr).replace('\'', '`')
                    # if subregion does not exist, insert it
                    if not sql_query(f"SELECT name FROM subregions WHERE name = '{sr}'"):
                        sql_query(f"INSERT INTO subregions (name, region) (VALUES ('{sr}', '{r}'));")
                        print('inserted new subregion: ' + sr)
                    # update the location's subregion
                    sql_query(f"UPDATE locations SET subregion = '{sr}' WHERE name = '{l}'")
                    print('updated location ' + l + ' in subregion ' + sr)
    print('updated all subregion fields')


# manually updates the sea level and viewing direction of each webcam
def update_metadata(countries=countries):
    # initializing new columns:
    # sql_query('ALTER TABLE webcams ADD COLUMN sealevel VARCHAR, ADD COLUMN viewdirection VARCHAR')

    webcams = []
    current_loc = (None, None, [])
    for (location, region, camid) in sql_query("SELECT l.name, l.region, w.camid FROM webcams w, locations l, regions r "
                                               "WHERE " + generate_search('r.country', ' '.join(countries)) + " "
                                               "AND l.region = r.name AND w.location = l.name "
                                               "AND (w.sealevel ISNULL OR w.viewdirection ISNULL) "
                                               "ORDER BY l.name, l.region"):
        if current_loc[0] == location and current_loc[1] == region:
            current_loc[2].append(camid)
        else:
            if current_loc[0] is not None and current_loc[1] is not None:
                webcams.append(current_loc)
            current_loc = (location, region, [camid])
    # going through all webcams and updating their meta-data
    for (location, region, cams) in webcams:
        for (title, code, sealevel, viewdirection) in get_webcams(location, region):
            if str(code) in cams:
                sql_query(f"UPDATE webcams SET sealevel = '{sealevel}', viewdirection = '{viewdirection}' WHERE camid = '{code}'")
                print(title + ' was updated: [sealevel: ' + sealevel + ', viewdirection: ' + viewdirection + ']')
    print('filled all missing metadata')
