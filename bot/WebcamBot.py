from discord import Client
import requests
from datetime import datetime, timedelta
from re import match, findall, split
from random import randrange

from db import *
from scrape import get_url_text


# --- WEBCAM CHECKS ---

# checks whether an url exists by status_code == 200
def exists(path, timeout=0.2):
    print('pinging ' + path)
    try:
        if requests.head(path, timeout=timeout).status_code == 200:
            return True
        else:
            return False
    except Exception:
        return False


# checks whether a foto-webcam camera is offline
def is_offline(camid):
    if exists('https://www.foto-webcam.eu'):
        cam_info = str(get_url_text('https://www.foto-webcam.eu')) \
                      .split('var metadata= new Object({"cams":[', 1)[1] \
                      .split('],"center":"score"});', 1)[0]
        if match('.*{"id":"' + camid + '"[^}]+"offline":false.+', cam_info):
            return False
    return True


# searches for the last working image url
def last_working(camid, url, timestamp):
    timestamp = list(map(lambda x: int(x), timestamp))
    if match('^\d+$', camid):
        delta = 15
        iterations = 24
    else:
        if camid in ['foto-webcam','megacam','picture-cams','wetter','stwo','relix','sauerland','sistrans','regensburg',
                     'Burglengenfeld','wilhelmsburg','bielefeld','Raas','db0noe','reisen-und-hobby','joeeos','marklex',
                     'terra-hd','asam-live','ig-funk'] and is_offline(camid):
            return 'offline', 'no timestamp'
        delta = 10
        iterations = 2
    timestamp[4] = timestamp[4] - timestamp[4] % delta
    for _ in range(iterations):
        test_url = url.replace('#yyyy', f"{timestamp[0]:04d}") \
                      .replace('#mm', f"{timestamp[1]:02d}") \
                      .replace('#dd', f"{timestamp[2]:02d}") \
                      .replace('#hh', f"{timestamp[3]:02d}") \
                      .replace('#nn', f"{timestamp[4]:02d}")
        if is_date_independent(test_url) and exists(test_url, 15):
            # avoiding Discord's image caching by appending a random string of numbers
            return str(test_url) + '?' + str(randrange(42000000)), list(map(lambda x: str(x).zfill(2), timestamp))
        elif exists(test_url):
            return test_url, list(map(lambda x: str(x).zfill(2), timestamp))
        time = datetime.strptime(':'.join(list(map(lambda x: str(x), timestamp))), '%Y:%m:%d:%H:%M') - timedelta(minutes=delta)
        timestamp = [int(time.year), int(time.month), int(time.day), int(time.hour), int(time.minute)]
    return 'no picture', 'no timestamp'


# checks whether the url is date-independent or self-updating
def is_date_independent(url):
    date_independent_urls = ["taschachhaus", "stadtwerke-konstanz", "media.jungfrau.ch"]
    for keyword in date_independent_urls:
        if keyword in url:
            return True
    return False


# --- BOT CLIENT ---

# scans a discord channel for !w commands, accesses the webcam database and, provides result
class WebcamBot(Client):
    async def on_ready(self):
        print('login successful')
    async def on_message(self, message):
        # help message
        if str(message.content) == '!w' or str(message) == '!w help':
            # logging
            print(str(message.author) + ' in ' + str(message.channel) + ': ' + str(message.content))
            await message.channel.send('This bot has access to all webcams that are available on \"bergfex.com\" or \"foto-webcam.eu\":\n'
                                     + '**!w**\n -> shows this message\n'
                                     + '**!w  CONTINENT  --countries**\n -> shows all countries associated with that continent term\n'
                                     + '**!w  COUNTRY  --regions**\n -> shows all regions associated with that country term\n'
                                     + '**!w  REGION  --subregions**\n -> shows all subregions associated with that region term\n'
                                     + '**!w  REGION  --locations**\n -> shows all locations associated with that region term\n'
                                     + '**!w  LOCATION  [--webcams]**\n -> shows all webcams associated with that location term\n'
                                     + '**!w  LOCATION , WEBCAM**\n -> gets the latest accessible photo for that webcam\n'
                                     + '**!w  LOCATION , WEBCAM  -d  [dd.mm.yyyy.]hh.mm**\n -> gets the photo at that timestamp [and date]\n')

        elif str(message.content).startswith('!wsql'):      # SQL piping (incl. keyword filter, no printing > 10000)
            # logging
            print(str(message.author) + ' in ' + str(message.channel) + ': ' + str(message.content))
            query = str(message.content).split('!wsql', 1)[1].strip()
            for x in ['insert', 'update', 'delete', 'create', 'drop', 'alter',
                      'truncate', 'rename', 'grant', 'revoke', 'rollback', 'transaction']:
                if x in query.lower():
                    await message.channel.send("Don't even try.")
                    return
            result = sql_query(query)
            if result:
                if len(str(result)) < 10000:
                    text = ''
                    for element in result:
                        text += str(element) + '\n'
                    for i in range(0, len(text), 2000):
                        await message.channel.send(text[i:i + 2000])
                else:
                    await message.channel.send('These ' + str(len(str(result))) + ' characters are a bit too much.')
            else:
                await message.channel.send('There are no results for this query.')

        # info display for countries, regions, locations, webcams
        elif str(message.content).startswith('!w'):
            # logging
            print(str(message.author) + ' in ' + str(message.channel) + ': ' + str(message.content))
            content = str(message.content).split('!w', 1)[1].strip()
            if all(list(map(lambda x: len(x) < 2, content.split(' ')))):
                await message.channel.send('Your search term is too short.')
            else:
                result = None
                if ',' not in content:
                    query = content.split(' --')[0]
                    if '--countries' in content:           # asking for countries
                        result = sql_query('SELECT continent, name FROM countries WHERE '
                                           + generate_search('continent', query) + ' ORDER BY continent')
                    elif '--regions' in content:          # asking for regions
                        result = sql_query('SELECT c.name, r.name FROM regions r JOIN countries c ON r.country = c.internal WHERE '
                                           + generate_search('c.name', query) + ' ORDER BY c.name')
                    elif '--subregions' in content:       # asking for subregions
                        result = sql_query('SELECT region, name FROM subregions WHERE '
                                           + generate_search('region', query) + ' ORDER BY region')
                    elif '--locations' in content:        # asking for locations
                        result = sql_query('SELECT subregion, name FROM locations WHERE '
                                           + generate_search('region', query) + ' ORDER BY subregion')
                    elif '--webcams' in content or True:  # for webcams
                        result = sql_query('SELECT location, name FROM webcams WHERE '
                                               + generate_search('location', query) + ' ORDER BY location')
                    if result:
                        text = ''
                        for element in result:  # formatting bold headers
                            if element[0] in text:
                                text += ', ' + element[1]
                            else:
                                text += '\n**' + element[0] + '**\n' + str(element[1])
                        for i in range(0, len(text), 2000):  # splitting in pieces of 2000 chars
                            await message.channel.send(text[i:i + 2000])
                        return

                # search for specific webcam
                else:
                    location = split(' *, *', content.rsplit(' -d ', 1)[0], 1)[0]
                    webcam = split(' *, *', content.rsplit(' -d ', 1)[0], 1)[1]
                    result = sql_query('SELECT camid, url FROM webcams WHERE '
                                      + generate_search('location', location) + ' AND '
                                      + generate_search('name', webcam))
                    for webcam in result:
                        if not match('.*<missing>', webcam[1]):
                            timestamp = findall('\d+', str(datetime.now()).rsplit(':', 1)[0])
                            if match('.+d *\d+.*', content):
                                date = content.rsplit(' -d ', 1)[1].split('.')
                                if len(date) == 5 and match('[0-3]?[0-9],[0-1]?[0-9],20[1-2][0-9],'
                                                            '[0-2]?[0-9],[0-5]?[0-9]', ','.join(date)):
                                    timestamp = date.copy()
                                    timestamp[0] = date[2]
                                    timestamp[2] = date[0]
                                elif len(date) == 2 and match('[0-2]?[0-9],[0-5]?[0-9]', ','.join(date)):
                                    timestamp[3] = date[0]
                                    timestamp[4] = date[1]
                                else:
                                    await message.channel.send('Unknown time format.')
                                    return
                            url, time = last_working(webcam[0], webcam[1], timestamp)
                            if url == 'offline':
                                await message.channel.send('This webcam is offline.')
                            elif url == 'no picture':
                                await message.channel.send('No picture was found in the last few hours.')
                            else:
                                await message.channel.send('This picture was taken at '
                                                           + time[2] + '.'      # day
                                                           + time[1] + '.'      # month
                                                           + time[0] + ' at '   # year
                                                           + time[3] + ':'      # hour
                                                           + time[4] + '.')     # minute
                                await message.channel.send(url)
                            return
                    await message.channel.send('No accessible webcam was found in the database.')
                    return
                if not result:
                    await message.channel.send('There are no results for this query.')
                else:
                    await message.channel.send('Unknown command.')
