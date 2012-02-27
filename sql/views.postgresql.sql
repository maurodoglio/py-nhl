set search_path to nhl;

drop view if exists vw_events;

create view vw_events
as
select
    events.*,
    array(select player_id from events_players where event_id = events.event_id) as poi,
    array(select player_id from events_penaltybox where event_id = events.event_id) as pb
from events;