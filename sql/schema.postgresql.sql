set search_path to nhl;

drop table if exists teams cascade;
drop table if exists games cascade;
drop table if exists players cascade;
drop table if exists events cascade;
drop table if exists events_players;
drop table if exists events_penaltybox;

create table teams (
    team_id integer,
    name varchar(35),
    nickname varchar(35),
    primary key(team_id)
);

create table games (
    game_id integer,
    away_team_id integer,
    home_team_id integer,
    date date,
    primary key(game_id)
);

create table players (
    player_id integer,
    team_id integer,
    name varchar(55),
    height integer,
    weight integer,
    dob date,
    primary key(player_id)
);

create table events (
    event_id integer,
    formal_event_id varchar(15),
    game_id integer references games(game_id),
    period integer,
    type varchar(15),
    description varchar(255),
    player_id integer,
    team_id integer references teams(team_id),
    xcoord integer,
    ycoord integer,
    home_score integer,
    away_score integer,
    home_sog integer,
    away_sog integer,
    time numeric,
    video_url varchar(255),
    altvideo_url varchar(255),
    goalie_id integer,
    primary key (game_id, event_id)
);

create table events_players (
    game_id integer,
    event_id integer,
    which varchar(15),
    player_id integer,
    foreign key(game_id, event_id) references events(game_id, event_id)
);

create table events_penaltybox (
    game_id integer,
    event_id integer,
    which varchar(15),
    player_id integer,
    foreign key(game_id, event_id) references events(game_id, event_id)
);

/*

note - I am not puting a FK restraint on player_id values since there may be some
fluky HTML parsing error and I'd rather have the data even if I don't have the
player record

*/