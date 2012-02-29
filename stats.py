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


# Usage information
def usage():
    print "usage information available on github wiki @ https://github.com/wellsoliver/py-nhl/wiki"
    raise SystemExit

# Returns a team ID for the given abbreviation
def fetchteamid(abbrev, conn):
    sql = 'SELECT team_id FROM teams WHERE abbrev = %s'
    result = conn.execute(sql, [abbrev])
    if result.rowcount == 0: return None
    
    return result.fetchone()['team_id']


# Grabs a URL and returns a BeautifulSoup object
def fetchsoup(url):
    try:
        print url
        res = urllib2.urlopen(url)
        return BeautifulSoup(res.read())
    except:
        return None


def processsoup(soup, view, tablename, season, conn):
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
        if view == 'summary':
            values = [cell.text.replace(',', '') for cell in cellvalues[4:]]
        elif view == 'timeonice':
            values = [cell.text.replace(',', '') for cell in cellvalues[4:]]
        elif view == 'faceoffpercentageall':
            values = [cell.text.replace(',', '') for cell in cellvalues[4:]]
            values.pop(9)
            values.pop(11)
            values.pop()
        elif view == 'bios':
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
        if view == 'bios':
            # Create a datetime object for DOB
            try:
                dobstruct = time.strptime(values[4], '%b %d \'%y')
                values[4] = datetime.datetime.fromtimestamp(time.mktime(dobstruct))
            except: values[4] = None

            # Get the team ID for the current team
            try:
                teamlist = cellvalues[2].text.replace(' ', '').split(',')
                teamidlist = [fetchteamid(abbrev, conn) for abbrev in teamlist]
                values[2] = teamidlist[-1]
            except: values[2] = None

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
    config = ConfigParser.ConfigParser()
    config.readfp(open('py-nhl.ini'))
    
    SEASON = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:", ["season="])
    except getopt.GetoptError, e:
        usage()

    for o, a in opts:
        if o in ('-s', '--season'): SEASON = int(a)

    if SEASON is False:
        usage()

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
    
    # Key is the NHL.com URL piece, value is the local DB table
    views = {
        'faceOffPercentageAll': 'stats_skaters_faceoff',
        'bios': 'players',
        'timeOnIce': 'stats_skaters_timeonice',
        'summary': 'stats_skaters_summary'
    }
    
    for view, tablename in views.iteritems():
        if view != 'bios':
            conn.execute("DELETE FROM %s WHERE season = %s" % (tablename, SEASON))

        url = 'http://www.nhl.com/ice/playerstats.htm?season=%s&gameType=2&viewName=%s' % (SEASON, view)
        soup = fetchsoup(url)
        if soup: processsoup(soup, view, tablename, SEASON, conn)
    
        # Get the max # of pages
        div = soup.find('div', 'pages')
        maxpage = int(urlparse.parse_qs(div.findAll('a')[-1]['href'])['pg'][0])

        # Iterate from page 2 through the end
        for page in xrange(2, maxpage + 1):
            url = 'http://www.nhl.com/ice/playerstats.htm?season=%s&gameType=2&viewName=%s&pg=%s' % (SEASON, view, page)
            soup = fetchsoup(url)
            if soup: processsoup(soup, view, tablename, SEASON, conn)


if __name__ == '__main__':
    main()