set search_path to nhl;

drop view if exists vw_events;

create view vw_events
as
select
    events.*,
    case when events.team_id = games.home_team_id then 'home' else 'away' end as which,
    array(select player_id from events_players where event_id = events.event_id and which = 'home') as hoi,
    array(select player_id from events_players where event_id = events.event_id and which = 'away') as aoi,

    array(select player_id from events_penaltybox where event_id = events.event_id and which = 'home') as hpb,
    array(select player_id from events_penaltybox where event_id = events.event_id and which = 'away') as apb
from events
inner join games using (game_id);