from pprint import pprint
from BeautifulSoup import BeautifulSoup

import re
import json
import urllib2
import sqlalchemy
import ConfigParser
import datetime
import time
import sys
import getopt
import calendar


# Usage information
def usage():
    print "usage information available on github wiki @ https://github.com/wellsoliver/py-nhl/wiki"
    raise SystemExit
    

# Grabs a URL
def fetchurl(url):
    try:
        print url
        res = urllib2.urlopen(url)
        return res.read()
    except:
        return None


# Gets a list of games for the given day
def getgamelist(date):
    gamelisturl = 'http://www.nhl.com/ice/ajax/GCScoreboardJS?today=%s' % date.strftime("%m/%d/%Y")

    try:
        gamelistraw = fetchurl(gamelisturl)
        
        if (len(gamelistraw) == 0): return []
        
        # HACK ALERT substring out the call to the javascript method loadScoreboard() to get raw JSON
        gamelistraw = gamelistraw[15:-1]
        gamelist = json.loads(gamelistraw)
        return gamelist['games']
    except:
        return []


# Gets a specific game
def getgame(game_id, season):
    gameurl = 'http://live.nhl.com/GameData/%s/%s/PlayByPlay.json' % (season, game_id)

    try:
        content = fetchurl(gameurl)
        obj = json.loads(content)
        return obj['data']['game']
    except:
        return None


# Processes an event
def processevent(game_id, event, conn):
    event_id = event['eventid']

    headers = [
        'event_id',
        'formal_event_id',
        'game_id',
        'period',
        'type',
        'description',
        'player_id',
        'team_id',
        'xcoord',
        'ycoord',
        'video_url',
        'altvideo_url',
        'home_score',
        'away_score',
        'home_sog',
        'away_sog',
        'time',
        'goalie_id'
    ]
    
    values = [
        event_id,
        event['formalEventId'],
        game_id,
        event['period'],
        event['type'],
        event['desc'],
        event['pid'] if 'pid' in event else None,
        event['teamid'],
        event['xcoord'],
        event['ycoord'],
        event['video'] if 'video' in event else None,
        event['altVideo'] if 'altVideo' in event else None,
        event['hs'],
        event['as'],
        event['hsog'] if event['type'] in ['Goal', 'Shot'] else None,
        event['asog'] if event['type'] in ['Goal', 'Shot'] else None,
        event['time'],
        event['g_goalieID'] if 'g_goalieID' in event and event['g_goalieID'] <> '' else None
    ]
    
    sql = 'INSERT INTO events (%s) VALUES(%s)' % (','.join(headers), ','.join(['%s'] * len(values)))
    conn.execute(sql, values)

    if 'aoi' in event:
        for player_id in event['aoi']:
            sql = 'INSERT INTO events_players (game_id, event_id, which, player_id) VALUES(%s, %s, %s, %s)'
            conn.execute(sql, [game_id, event_id, 'away', player_id])

    if 'hoi' in event:
        for player_id in event['hoi']:
            sql = 'INSERT INTO events_players (game_id, event_id, which, player_id) VALUES(%s, %s, %s, %s)'
            conn.execute(sql, [game_id, event_id, 'home', player_id])

    if 'apb' in event:
        for player_id in event['apb']:
            sql = 'INSERT INTO events_penaltybox (game_id, event_id, which, player_id) VALUES(%s, %s, %s, %s)'
            conn.execute(sql, [game_id, event_id, 'away', player_id])

    if 'hpb' in event:
        for player_id in event['hpb']:
            sql = 'INSERT INTO events_penaltybox (game_id, event_id, which, player_id) VALUES(%s, %s, %s, %s)'
            conn.execute(sql, [game_id, event_id, 'home', player_id])


# Processes a game
def processgame(game, game_id, date, conn):
    
    # Clear out data
    query = 'DELETE FROM events_players WHERE game_id = %s'
    conn.execute(query, [game_id])

    query = 'DELETE FROM events_penaltybox WHERE game_id = %s'
    conn.execute(query, [game_id])

    query = 'DELETE FROM events WHERE game_id = %s'
    conn.execute(query, [game_id])

    query = 'DELETE FROM games WHERE game_id = %s'
    conn.execute(query, [game_id])
    
    query = 'INSERT INTO games (game_id, away_team_id, home_team_id, date) VALUES(%s, %s, %s, %s)'
    conn.execute(query, [game_id, game['awayteamid'], game['hometeamid'], date])

    query = 'SELECT * FROM teams WHERE team_id = %s'
    result = conn.execute(query, [game['awayteamid']])
    if result.rowcount == 0:
        query = 'INSERT INTO teams (team_id, name, nickname) VALUES(%s, %s, %s)'
        conn.execute(query, [game['awayteamid'], game['awayteamname'], game['awayteamnick']])

    query = 'SELECT * FROM teams WHERE team_id = %s'
    result = conn.execute(query, [game['hometeamid']])
    if result.rowcount == 0:
        query = 'INSERT INTO teams (team_id, name, nickname) VALUES(%s, %s, %s)'
        conn.execute(query, [game['hometeamid'], game['hometeamname'], game['hometeamnick']])
    
    sql = 'DELETE FROM events_players WHERE event_id IN (SELECT event_id FROM events WHERE game_id = %s)'
    conn.execute(sql, [game_id])
    sql = 'DELETE FROM events_penaltybox WHERE event_id IN (SELECT event_id FROM events WHERE game_id = %s)'
    conn.execute(sql, [game_id])
    sql = 'DELETE FROM events WHERE game_id = %s'
    conn.execute(sql, [game_id])
    
    for event in game['plays']['play']:
        processevent(game_id, event, conn)


def main():
    config = ConfigParser.ConfigParser()
    config.readfp(open('py-nhl.ini'))

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

    SEASON = False
    YEAR = False
    MONTH = False
    dates = []

    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:y:m:", ["season=", "year=", "month="])
    except getopt.GetoptError, e:
        usage()

    for o, a in opts:
        if o in ('-y', '--year'): YEAR = int(a)
        elif o in ('-m', '--month'): MONTH = int(a)
        elif o in ('-s', '--season'): SEASON = int(a)

    if SEASON is False:
        usage()

    if YEAR:
        if MONTH:
            for day in xrange (calendar.monthrange(YEAR, MONTH)[1]):
                dates.append(datetime.date(YEAR, MONTH, day + 1))
        else:
            for month in xrange(1,13):
                for day in xrange (calendar.monthrange(YEAR, month)[1]):
                    dates.append(datetime.date(YEAR, month, day + 1))
    else:
        # Just yesterday!
        dates = [datetime.datetime.today() - datetime.timedelta(1)]

    for date in dates:
        gamelist = getgamelist(date)

        for game in gamelist:
            game_id = game['id']
            fetchedgame = getgame(game_id, SEASON)

            if fetchedgame is None: continue
            processgame(fetchedgame, game_id, date, conn)


if __name__ == '__main__':
    main()