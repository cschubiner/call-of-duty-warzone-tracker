import csv
import urllib

import requests

from constants import SAMPLE_MATCHES, SPECIFIC_MATCH_SAMPLE

PLAYER_HANDLES = {
    'clayschubiner',
    'MarkMadness',
    'socom1880',
}

BATTLENET_IDS = [
    'daynine#1168',
]

def get_specific_match_details(match_id):
    #   https://api.tracker.gg/api/v1/warzone/matches/8986566823157720677
    return SPECIFIC_MATCH_SAMPLE

def matches_for_player(battlenet_id):
    for m in SAMPLE_MATCHES:
        yield m
    return

    next = 'null'
    encoded_name = urllib.parse.quote(battlenet_id.lower())
    while next:
        response = requests.get(
            f'https://api.tracker.gg/api/v1/warzone/matches/battlenet/{encoded_name}?type=wz&next={next}')
        response_json = response.json()
        if response.status_code != 200:
            print(str(response_json))
            return

        next = response_json['data']['metadata']['next']
        for m in response_json['data']['matches']:
            yield m

def extract_stats_from_segment(seg, team_members):
    player_name = seg['attributes']['platformUserIdentifier']
    stats = {'player_name': player_name, 'placement':seg['metadata']['placement']['value']}

    # for stat_name in ['kills', 'kdRatio', 'score', 'timePlayed', 'headshots', 'executions', 'assists', 'percentTimeMoving', 'longestStreak', 'scorePerMinute', 'damageDone', 'distanceTraveled', 'deaths', 'damageTaken', 'damageDonePerMinute']:
    for stat_name, stat_dict in seg['stats'].items():
        display_stat_name = stat_dict['displayName']
        stats[display_stat_name] = stat_dict['value']

    return stats


already_seen_match_ids = set()

with open('data_file.csv', 'w') as data_file:
    csv_writer = csv.writer(data_file)
    has_written_header = False

    for battlenet_id in BATTLENET_IDS:
        for match in matches_for_player(battlenet_id):
            match_id = match['attributes']['id']
            if match_id in already_seen_match_ids:
                continue
            already_seen_match_ids.add(match_id)

            match_details = get_specific_match_details(match_id)
            print(match)
            segments = match_details['data']['segments']
            placements = set()
            for seg in segments:
                if seg['metadata']['platformUserHandle'] in PLAYER_HANDLES:
                    placements.add(seg['metadata']['placement']['value'])
            for placement in placements:
                team_segments = [seg for seg in segments if seg['metadata']['placement']['value'] == placement]
                team_members = [seg['attributes']['platformUserIdentifier'] for seg in team_segments]
                for seg in team_segments:
                    stats = extract_stats_from_segment(seg, team_members)
                    if not has_written_header:
                        csv_writer.writerow(stats.keys())
                        has_written_header = True

                    csv_writer.writerow(stats.values())
