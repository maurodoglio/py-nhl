drop view if exists nhl.vw_events;
drop view if exists nhl.vw_summary;
drop view if exists nhl.vw_timeonice;

create view nhl.vw_events
as
select
    events.*,
    case when events.team_id = games.home_team_id then 'home' else 'away' end as which,
    array(select player_id from nhl.events_players where event_id = events.event_id and which = 'home') as hoi,
    array(select player_id from nhl.events_players where event_id = events.event_id and which = 'away') as aoi,

    array(select player_id from nhl.events_penaltybox where event_id = events.event_id and which = 'home') as hpb,
    array(select player_id from nhl.events_penaltybox where event_id = events.event_id and which = 'away') as apb
from nhl.events
inner join nhl.games using (game_id);

create view nhl.vw_summary
as
select
	players.player_id,
	players.name as playername,
	players.team_id,
	teams.name as teamname,
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
from nhl.stats_skaters_summary
inner join nhl.players using (player_id)
left join nhl.teams using (team_id);

create view nhl.vw_timeonice
as
select
	players.player_id,
	players.name as playername,
	players.team_id,
	teams.name as teamname,
	stats_skaters_timeonice.season,
	stats_skaters_timeonice.gp,
	stats_skaters_timeonice.evenstrength,
	stats_skaters_timeonice.evenstrength_g,
	stats_skaters_timeonice.shorthanded,
	stats_skaters_timeonice.shorthanded_g,
	stats_skaters_timeonice.powerplay,
	stats_skaters_timeonice.powerplay_g,
	stats_skaters_timeonice.total,
	stats_skaters_timeonice.total_g,
	stats_skaters_timeonice.shifts,
	stats_skaters_timeonice.total_s,
	stats_skaters_timeonice.shifts_g
from nhl.stats_skaters_timeonice
inner join nhl.players using (player_id)
left join nhl.teams using (team_id);