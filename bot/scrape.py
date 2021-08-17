import requests
from bs4 import BeautifulSoup
from re import match


# all countries
import db

countries = ['oesterreich', 'schweiz', 'deutschland', 'italien', 'slovenia',
             'frankreich', 'nederland', 'belgie', 'polska', 'czechia', 'slovakia',
             'spanien', 'kroatien', 'bosnien-herzegowina', 'liechtenstein']


# --- SCRAPERS ---

# returns all regions associated with this country
def get_regions(country):
    regions = set()
    # retrieving the ski-resorts from this country
    winter = BeautifulSoup(requests.get('https://www.bergfex.at/' + str(country) + '/webcams/').text, 'html.parser')
    for r in winter.find('div', class_='section-left').find_all('h2'):
        title = get_title(r)
        if title and title.startswith('Webcams '):
            regions.add(title.split('Webcams ')[1])  # add paragraph heading (= region) to list
    # retrieving the cities in this country
    sommer = BeautifulSoup(requests.get('https://www.bergfex.at/sommer/' + str(country) + '/webcams/').text, 'html.parser')
    for r in sommer.find('div', class_='section-left').find_all('h2'):
        title = get_title(r)
        if title and title.startswith('Webcams '):
            regions.add(title.split('Webcams ')[1])  # add paragraph heading (= region) to list
    return list(regions)


# returns all sub-divisions of regions associated with a region, not scraped from /webcams/
def get_subregions(country):
    sub_regions = dict()
    regions_html = BeautifulSoup(requests.get('https://www.bergfex.at/sommer/' + str(country)).text, 'html.parser')
    # the following code does its best to find the subregions container for all sites
    regions_parsed = regions_html.find_all('div', class_='section-left')[1] if \
        len(regions_html.find_all('div', class_='section-left')) > 1 else \
        regions_html.find('div', class_='section-left')
    for r in regions_parsed.find_all('h2'):
        if r.find('a'):
            # initializes a region with an empty subregions list
            sub_regions[get_title(r)] = []
            subregions_html = BeautifulSoup(requests.get('https://www.bergfex.at/' + str(r.find('a').get('href'))).text, 'html.parser')
            # the following code does its best to find the subregions container for all sites
            subregions_parsed = subregions_html.find_all('div', class_='section-left')[1] if \
                len(subregions_html.find_all('div', class_='section-left')) > 1 else \
                subregions_html.find('div', class_='section-left')
            for s in subregions_parsed.find_all('h2'):
                # goes through all names (= subregions) listed under a region and adds them to the region's list
                sub_regions[get_title(r)].append(get_title(s))
    return sub_regions


# returns all locations associated with this region
def get_locations(region, country=None, links=False, subregion=False):
    locations = set()
    if country is None:
        country = db.get_country(region)
        if country is None:
            return []
    # the following list makes sure, locations are scooped from ski-resorts and cities
    soup = [BeautifulSoup(get_url_text('https://www.bergfex.at/' + str(country) + '/webcams/'), 'html.parser'),
            BeautifulSoup(get_url_text('https://www.bergfex.at/sommer/' + str(country) + '/webcams/'), 'html.parser')]
    found = [True, True]  # checking whether the search in winter/summer shall continue
    i = 0  # winter (= 0), summer (= 1) counter
    for s in soup:
        # initialize first region
        s = s.find('div', class_='section-left').find_next('h2')
        # continue if current h2 field exists and go on as long as searched region is not found
        while get_title(s) and region != get_title(s).split('Webcams ')[1]:
            s = s.find_next('h2')
            if s is None:
                # if search hits None, something is wrong, abort!
                found[i] = False
                break
        # if found[i] == true, desired region has been found
        if found[i] and s.find_next('div', class_='txt_markup grid cols2'):  # region actually has some locations
            # append all found locations to the found list
            found.append(s.find_next('div', class_='txt_markup grid cols2').find_all('li', class_='hastotals'))
        i += 1
    # go through all locations that have been found in winter/summer
    for f in found[2:]:
        for loc in f:
            link = str(loc.find('a').get('href'))
            # if link option is enabled, retrieve the location's link as well
            if links:
                locations.add((loc.find('a').text, link))
            # if subregion option is enabled, retrieve the subregion as well
            elif subregion:
                webcam_page = get_url_text('https://www.bergfex.at' + link)
                sr = BeautifulSoup(webcam_page, 'html.parser').find('nav', 'breadcrumb mobile-hidden') \
                    .find_all('a')[-2].text if webcam_page is not None else '<missing>'
                locations.add((loc.find('a').text, sr))
            # otherwise only add the name to the set (filters duplicates automatically)
            else:
                locations.add(loc.find('a').text)
    return list(locations)


# returns all webcams associated with this location
def get_webcams(location, region, country=None):
    webcams = set()
    duplicates = []
    if country is None:
        country = db.get_country(region)
        if country is None:
            return []
    for l in get_locations(region, country, True, False):
        if l[0] == location:
            html = get_url_text('https://www.bergfex.at' + l[1])
            if html is not None:
                soup1 = BeautifulSoup(html, 'html.parser')
                # getting all webcams
                soup1 = soup1.find_all('div', class_='col')
                for s in soup1:
                    # retrieves the webcam link
                    a = s.find('a')
                    # making sure the webcams belong to the location and it's not a suggestion
                    if a and a.get('title') and not a.get('title').startswith('Webcam'):
                        title = a.get('title')
                        # filtering the webcams code from the link
                        code = str(a.get('href')).split('webcams/c')[1].split('/', 1)[0]
                        # duplicate handling
                        if code not in duplicates:
                            html = get_url_text('https://www.bergfex.at' + l[1] + 'c' + code + '/')
                            if html is not None:
                                duplicates.append(title)  # title has been used
                                duplicates.append(code)  # code has been used
                                # title has not been used but code has -> duplicate naming, resolved by adding number
                                if title in duplicates:
                                    title += ' ' + str(duplicates.count(title))  # numbering the title
                                soup2 = BeautifulSoup(html, 'html.parser')
                                sealevel, viewdirection = get_metadata(soup2)
                                indicator = soup2.find('div', class_='section-full')
                                # found webcams is a 'foto-webcam', will be marked with '[UHD]'
                                if 'foto-webcam' in str(indicator) and indicator and indicator.find('iframe'):
                                    webcams.add((title + ' [UHD]',
                                                 indicator.find('iframe').get('src').split('webcam/')[1].split('?')[0],
                                                 sealevel, viewdirection))
                                # found webcam belonging to bergfex
                                else:
                                    webcams.add((title, code, sealevel, viewdirection))
    return list(webcams)


# gets all webcams in a dictionary
def get_hq_webcams():
    webcams = {}
    soup = BeautifulSoup(requests.get('https://foto-webcam.eu').text, 'html.parser')
    info = soup.find('body').find('script',language='JavaScript')
    info = str(info).split('var metadata= new Object({"cams":[{', 1)[1].split('}],"center":"score"});', 1)[0]
    for w in info.split('},{'):
        key = w[6:].split('",', 1)[0]
        content = w[6:].split('",', 1)[1].split(',')
        webcams[key] = content
    return webcams

# filters out the meta-data for a saved webcam, currently sealevel and viewing direction
def get_metadata(html):
    metadata = []
    element = html.find('dl').find('dt')
    searching = True
    while element is not None:
        if match('Seehöhe|Blickrichtung', str(element.text)):
            searching = False
            element = element.find_next_sibling()
            continue
        if not searching:
            metadata.append(str(element.text).replace('\xa0', ' '))
            searching = True
        element = element.find_next_sibling()
    while len(metadata) < 2:
        metadata.append('-')
    return metadata


# --- HELPER METHODS ---

# tries 3 times to get the html document
def get_url_text(url):
    for i in range(3):
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            return r.text
    return None


# gets the title of a given html statement
def get_title(junk):
    if junk and junk.find('a'):
        return junk.find('a').text.replace('&amp;', '&')
    else:
        return None
