/*

some just some audit-y stuff to compare data against NHL.com or whatever

*/

-- Regular season LA Kings goal & shot totals by players
select
    player_id,
    name,
    sum(case when type = 'Goal' then 1 else 0 end) g,
    sum(1) s,
    stats_skaters_summary.g as real_g,
    stats_skaters_summary.s as real_s
into temporary table _totals
from nhl.events
inner join nhl.games using (game_id)
inner join nhl.players using (player_id)
inner join nhl.stats_skaters_summary using (player_id)
where
    events.team_id = 26
    and type in ('Goal', 'Shot')
    and date between '2011-10-07' and '2012-04-07'
    and period <= 4
    and stats_skaters_summary.season = 20112012
group by events.player_id, players.name, stats_skaters_summary.g, stats_skaters_summary.s
order by g desc;

select * from _totals where g <> real_g or s <> real_s;