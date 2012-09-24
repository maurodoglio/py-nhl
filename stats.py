from pprint import pprint
from BeautifulSoup import BeautifulSoup

import re
import json
import urllib2
import urlparse
import sqlalchemy
import ConfigParser
import datetime
import time
import sys
import getopt
import os

# Usage information
def usage():
    print "usage information available on github wiki @ https://github.com/wellsoliver/py-nhl/wiki"
    raise SystemExit


# Grabs a URL and returns a BeautifulSoup object
def fetchsoup(url, **kwargs):
    try:
        if 'verbose' in kwargs: print url
        res = urllib2.urlopen(url)
        return BeautifulSoup(res.read())
    except:
        return None


def processsoup(soup, position, view, tablename, season, conn):
    table = soup.find('table', 'data')
    tablerows = table.find('tbody').findAll('tr')
    
    view = view.lower();
    
    for row in tablerows:
        cellvalues = row.findAll('td')
        try:
            player_id = re.search('=(\d+)$', cellvalues[1].find('a')['href']).groups()[0]
        except:
            print 'cannot get player ID from row'
            continue
        
        # Get the list of values we want based on the view
        if view == 'summary' and position == 'S':
            values = [cell.text.replace(',', '') for cell in cellvalues[4:]]
        elif view == 'summary' and position == 'G':
            values = [cell.text.replace(',', '') for cell in cellvalues[3:]]
        elif view == 'timeonice':
            values = [cell.text.replace(',', '') for cell in cellvalues[4:]]
        elif view == 'faceoffpercentageall':
            values = [cell.text.replace(',', '') for cell in cellvalues[4:]]
            values.pop(9)
            values.pop(11)
            values.pop()
        elif view == 'bios' or view == 'goaliebios':
            values = [cell.text for cell in cellvalues[:-8]]
            # sometimes NHL.com lists a player on two pages... *shrug*
            query = 'SELECT * FROM players WHERE player_id = %s'
            result = conn.execute(query, [player_id])
            if result.rowcount > 0: continue

        if view in ['summary', 'timeonice', 'faceoffpercentageall']:
            # sometimes NHL.com lists a player on two pages... *shrug*
            query = 'DELETE FROM %s WHERE player_id = %s AND season = %s' % (tablename, player_id, season)
            conn.execute(query)

        # Convert times to decimals
        for i, value in enumerate(values):
            if (':' in value):
                valuelist = [int(x) for x in value.split(':')]
                values[i] = round(valuelist[0] + (valuelist[1] / 60.0), 2)

        # Custom handling
        if view == 'bios' or view == 'goaliebios':
            # Create a datetime object for DOB
            try:
                idx = 4 if view == 'bios' else 3
                dobstruct = time.strptime(values[idx], '%b %d \'%y')
                values[idx] = datetime.datetime.fromtimestamp(time.mktime(dobstruct))
            except:
                idx = 4 if view == 'bios' else 3
                values[idx] = None
            
            # Set a position for a goalie
            if view == 'goaliebios':
                values.insert(3, 'G')

            # TODO Get the team ID for the current team
            # teamabbr = cellvalues[2].text.replace(' ', '').split(',')[-1]
            values[2] = None
        elif view == 'summary' and position == 'S':
            # Game-tying goals removed for 2004/2005, removing it for prior years
            del values[11]

        # Convert emptys to null
        for i, value in enumerate(values):
            if type(value) is unicode and len(value) == 0: value = None
            values[i] = value

        # Insert season
        if view in ['summary', 'timeonice', 'faceoffpercentageall']: values.insert(0, season)
        # Insert player ID
        values.insert(0, player_id)
        
        query = 'INSERT INTO %s VALUES(%s)' % (tablename, ','.join(['%s'] * len(values)))
        conn.execute(query, values)


def main():
    pwd = os.path.dirname(__file__)
    if pwd == '': pwd = '.'
    config = ConfigParser.ConfigParser()
    config.readfp(open('%s/py-nhl.ini' % pwd))
    
    SEASON = False
    VIEW = False
    POSITION = 'S'

    positions = ['S', 'G']

    # Key is the NHL.com URL piece, value is the local DB table
    views = {
        'S': {
            'faceOffPercentageAll': 'stats_skaters_faceoff',
            'bios': 'players',
            'timeOnIce': 'stats_skaters_timeonice',
            'summary': 'stats_skaters_summary'
        }, 'G': {
            'summary': 'stats_goalies_summary',
            'goalieBios': 'players',
        }
    }
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:v:p:", ["season=","view=", "position="])
    except getopt.GetoptError, e:
        usage()

    for o, a in opts:
        if o in ('-s', '--season'): SEASON = int(a)
        elif o in ('-p', '--position'): POSITION = a
        elif o in ('-v', '--view'): VIEW = a

    if POSITION not in positions:
        print 'invalid position %s' % POSITION
        usage()
        raise SystemExit
    if VIEW not in views[POSITION].keys():
        print 'invalid view %s' % VIEW
        usage()
        raise SystemExit
    
    if SEASON is False:
        usage()

    if VIEW:
        runviews = [VIEW]
    else:
        runviews = views[POSITION].keys()

    try:
        ENGINE = config.get('database', 'engine')
        HOST = config.get('database', 'host')
        DATABASE = config.get('database', 'database')

        USER = None if not config.has_option('database', 'user') else config.get('database', 'user')
        SCHEMA = None if not config.has_option('database', 'schema') else config.get('database', 'schema')
        PASSWORD = None if not config.has_option('database', 'password') else config.get('database', 'password')

    except ConfigParser.NoOptionError:
        print 'Need to define engine, user, password, host, and database parameters'
        raise SystemExit

    if USER and PASSWORD: string = '%s://%s:%s@%s/%s' % (ENGINE, USER, PASSWORD, HOST, DATABASE)
    else:  string = '%s://%s/%s' % (ENGINE, HOST, DATABASE)

    try:
        db = sqlalchemy.create_engine(string)
        conn = db.connect()
    except:
        print 'Cannot connect to database'
        raise SystemExit

    if SCHEMA: conn.execute('SET search_path TO %s' % SCHEMA)
    
    for view in runviews:
        tablename = views[POSITION][view]
        if view not in ['bios', 'goalieBios']:
            conn.execute("DELETE FROM %s WHERE season = %s" % (tablename, SEASON))

        # position S/G
        url = 'http://www.nhl.com/ice/playerstats.htm?season=%s&position=%s&gameType=2&viewName=%s' % (SEASON, POSITION, view)
        soup = fetchsoup(url, verbose=True)
        if soup: processsoup(soup, POSITION, view, tablename, SEASON, conn)
        else: continue
    
        # Get the max # of pages
        div = soup.find('div', 'pages')
        maxpage = int(urlparse.parse_qs(div.findAll('a')[-1]['href'])['pg'][0])

        # Iterate from page 2 through the end
        for page in xrange(2, maxpage + 1):
            url = 'http://www.nhl.com/ice/playerstats.htm?season=%s&position=%s&gameType=2&viewName=%s&pg=%s' % (SEASON, POSITION, view, page)
            soup = fetchsoup(url, verbose=True)
            if soup: processsoup(soup, POSITION, view, tablename, SEASON, conn)


if __name__ == '__main__':
    main()
