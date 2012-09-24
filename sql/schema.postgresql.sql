set search_path to nhl;

drop table if exists nhl.teams cascade;
drop table if exists nhl.games cascade;
drop table if exists nhl.events cascade;
drop table if exists nhl.events_players;
drop table if exists nhl.events_penaltybox;

drop table if exists nhl.players cascade;
drop table if exists nhl.stats_skaters_summary;
drop table if exists nhl.stats_skaters_timeonice;

/* USED BY events.py */

create table nhl.teams (
    team_id integer,
    name varchar(35),
    nickname varchar(35),
    primary key(team_id)
);

create table nhl.games (
	season integer,
    game_id integer,
    date date,
    home_team_id integer references nhl.teams(team_id),
    away_team_id integer references nhl.teams(team_id),
    home_team_score integer,
    away_team_score integer,
    rl boolean,
    gcl boolean,
    gcll boolean,
    bs varchar(35),
    bsc varchar(35),
    gs integer,
    primary key(game_id)
);

create table nhl.events (
    event_id integer,
    formal_event_id varchar(15),
    game_id integer references nhl.games(game_id),
    period integer,
    strength integer,
    type varchar(15),
    shot_type varchar(15),
    description varchar(255),
    player_id integer,
    team_id integer references nhl.teams(team_id),
    xcoord integer,
    ycoord integer,
    home_score integer,
    away_score integer,
    home_sog integer,
    away_sog integer,
    time varchar(10),
    video_url varchar(255),
    altvideo_url varchar(255),
    goalie_id integer,
    primary key (game_id, event_id)
);

create table nhl.events_players (
    game_id integer references nhl.games(game_id),
    event_id integer,
    which varchar(15),
    player_id integer,
    foreign key(game_id, event_id) references nhl.events(game_id, event_id)
);

create table nhl.events_penaltybox (
    game_id integer references nhl.games(game_id),
    event_id integer,
    which varchar(15),
    player_id integer,
    foreign key(game_id, event_id) references nhl.events(game_id, event_id)
);

/* USED BY stats.py */

create table nhl.players (
    player_id integer,
    jersey integer,
    name varchar(100),
    team_id integer,
    pos varchar(3),
    dob date,
    birthcity varchar(100),
    state varchar(10),
    country varchar(10),
    height integer,
    weight integer,
    shoots char,
    primary key(player_id)
);

create table nhl.stats_skaters_summary (
    player_id integer,
    season integer,
    gp integer,
    g integer,
    a integer,
    p integer,
    plusminus integer,
    pim integer,
    pp integer,
    sh integer,
    gw integer,
    ot integer,
    s integer,
    s_pct numeric,
    toi_g numeric,
    sft_g numeric,
    fo_pct numeric,
    primary key (player_id, season)
);

create table nhl.stats_skaters_timeonice (
    player_id integer,
    season integer,
    gp integer,
    evenstrength numeric,
    evenstrength_g numeric,
    shorthanded numeric,
    shorthanded_g numeric,
    powerplay numeric,
    powerplay_g numeric,
    total numeric,
    total_g numeric,
    shifts integer,
    total_s numeric,
    shifts_g numeric,
    primary key (player_id, season)
);

create table nhl.stats_skaters_faceoff (
    player_id integer,
    season integer,
    gp integer,
    evenstrength_fow integer,
    evenstrength_fol integer,
    powerplay_fow integer,
    powerplay_fol integer,
    shorthanded_fow integer,
    shorthanded_fol integer,
    home_fow integer,
    home_fol integer,
    road_fow integer,
    road_fol integer,
    fow integer,
    fol integer,
    total integer,
    primary key (player_id, season)
);

create table nhl.stats_goalies_summary (
    player_id integer,
    season integer,
    gp integer,
    gs integer,
    w integer,
    l integer,
	ot integer,
	sa integer,
	ga integer,
	gaa real,
	sv integer,
	sv_pct numeric,
	so integer,
	g integer,
	a integer,
	pim integer,
	toi numeric,
    primary key (player_id, season)
);

create index idx_events_game_id on events(game_id);
create index idx_events_team_id on events(team_id);
create index idx_events_player_id on events(player_id);
create index idx_events_players_player_id on events_players(player_id);
create index idx_events_penaltybox_player_id on events_penaltybox(player_id);