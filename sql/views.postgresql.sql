set search_path to nhl;

drop view if exists vw_events;
drop view if exists vw_summary;

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

create view vw_summary
as
select
	players.player_id,
	players.name as playername,
	players.team_id,
	teams.name as teamname,
	teams.abbrev,
	stats_skaters_summary.season,
	stats_skaters_summary.gp,
	stats_skaters_summary.g,
	stats_skaters_summary.a,
	stats_skaters_summary.p,
	stats_skaters_summary.plusminus,
	stats_skaters_summary.pim,
	stats_skaters_summary.pp,
	stats_skaters_summary.sh,
	stats_skaters_summary.gw,
	stats_skaters_summary.ot,
	stats_skaters_summary.s,
	stats_skaters_summary.s_pct,
	stats_skaters_summary.toi_g,
	stats_skaters_summary.sft_g,
	stats_skaters_summary.fo_pct
from stats_skaters_summary
inner join players using (player_id)
inner join teams using (team_id);