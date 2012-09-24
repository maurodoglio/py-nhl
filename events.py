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
import os


# Usage information
def usage():
    print "usage information available on github wiki @ https://github.com/wellsoliver/py-nhl/wiki"
    raise SystemExit


# Returns list of games
def getgamelist(**kwargs):
    months = []
    games = []
    dates = []

    if 'date' in kwargs:
        dates.append(kwargs['date'])
    elif 'year':
        year = kwargs['year']
        if 'month' in kwargs:
            months.append(kwargs['month'])
        else:
            for month in xrange(1,13):
                months.append(month)

        for month in months:
            url = 'http://www.nhl.com/ice/ajax/gamecalendarjson.htm?month=%d&year=%d' % (month, year)
            res = fetchurl(url)
            gamelist = json.loads(res)

            for date in gamelist['gameDates']:
                if date['n'] > 0:
                    gamedate = datetime.datetime.strptime(date['gd'], '%m/%d/%Y')
                    if 'day' in kwargs and gamedate.day != kwargs['day']: continue
                    dates.append(gamedate)


    for date in dates:
        gamelisturl = 'http://www.nhl.com/ice/ajax/GCScoreboardJS?today=%s' % date.strftime("%m/%d/%Y")
        try:
            gamelistraw = fetchurl(gamelisturl)
        
            if (len(gamelistraw) == 0): return []
        
            # HACK ALERT substring out the call to the javascript method loadScoreboard() to get raw JSON
            gamelistraw = gamelistraw[15:-1]
            gamelist = json.loads(gamelistraw)['games']
        except:
            gamelist = []

        for game in gamelist:
            game['date'] = date # Keep track of this
            games.append(game)

    return games


# Grabs a URL
def fetchurl(url):
    try:
        print url
        res = urllib2.urlopen(url)
        return res.read()
    except:
        return None


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
        'strength',
        'type',
        'shot_type',
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
    
    goalie_id = event['g_goalieID'] if 'g_goalieID' in event and event['g_goalieID'] <> '' else None
    if goalie_id is None and 'pid2' in event and len(str(event['pid2'])) > 0:
        goalie_id = event['pid2']
    
    values = [
        event_id,
        event['formalEventId'],
        game_id,
        event['period'],
        event['strength'],
        event['type'],
        event['g_shotType'] if 'g_shotType' in event and event['g_shotType'] <> '' else None,
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
        goalie_id
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
def processgame(season, game, gameinfo, conn):
    
    game_id = gameinfo['id']
    
    # Clear out data
    query = 'DELETE FROM events_players WHERE game_id = %s'
    conn.execute(query, [game_id])

    query = 'DELETE FROM events_penaltybox WHERE game_id = %s'
    conn.execute(query, [game_id])

    query = 'DELETE FROM events WHERE game_id = %s'
    conn.execute(query, [game_id])

    query = 'DELETE FROM games WHERE game_id = %s'
    conn.execute(query, [game_id])
    
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

    values = [season, \
        game_id, \
        game['awayteamid'], \
        game['hometeamid'], \
        gameinfo['date'], \
        gameinfo['hts'], \
        gameinfo['ats'], \
        gameinfo['rl'], \
        gameinfo['gcl'], \
        gameinfo['gcll'], \
        gameinfo['bs'], \
        gameinfo['bsc'], \
        gameinfo['gs']
    ]
    query = 'INSERT INTO games (season, game_id, away_team_id, home_team_id, date, home_team_score, away_team_score, rl, gcl, gcll, bs, bsc, gs) VALUES(%s)' % ','.join(['%s'] * len(values))
    conn.execute(query, values)

    for event in game['plays']['play']:
        processevent(game_id, event, conn)


def main():
    pwd = os.path.dirname(__file__)
    if pwd == '': pwd = '.'
    config = ConfigParser.ConfigParser()
    config.readfp(open('%s/py-nhl.ini' % pwd))

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
    DAY = False
    gameargs = {}

    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:y:m:d:", ["season=", "year=", "month=", "day="])
    except getopt.GetoptError, e:
        usage()

    for o, a in opts:
        if o in ('-y', '--year'): YEAR = int(a)
        elif o in ('-m', '--month'): MONTH = int(a)
        elif o in ('-d', '--day'): DAY = int(a)
        elif o in ('-s', '--season'): SEASON = int(a)

    if SEASON is False: usage()
    
    if YEAR:
        gameargs['year'] = YEAR
        if MONTH:
            gameargs['month'] = MONTH
            if DAY:
                gameargs['day'] = DAY
    else:
        # Just yesterday!
        gameargs['date'] = [datetime.datetime.today() - datetime.timedelta(1)]

    gamelist = getgamelist(**gameargs)
    for game in gamelist:
        game_id = game['id']
        fetchedgame = getgame(game_id, SEASON)
        
        if fetchedgame is None: continue
        processgame(SEASON, fetchedgame, game, conn)


if __name__ == '__main__':
    main()
