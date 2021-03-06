import csv
import pickle
import time
import urllib
from datetime import datetime

import requests
from dateutil.parser import parser, parse

from constants import SAMPLE_MATCHES, SPECIFIC_MATCH_SAMPLE

PLAYER_HANDLES = [
    'killacure24',
    'clayschubiner',
    'MarkMadness',
    'socom1880',
    'Rook',
    'Arturias13',
    'Chieffelix47',
]

DEBUG = False

BATTLENET_IDS = [
    'markmadness#1213',
    'Rook#12135',
    'daynine#1168',
    'Chieffelix47#1558',
    'socom1880#1790',
]

def make_api_request(url, big_timeout=False):
    to_sleep = 10
    while True:
        try:
            print(f'Attempting to get {url}...')
            response = requests.get(url)
            if response.status_code != 200:
                err_text = str(response.text)
                print(err_text)
                if 'An unexpected error occured in our system' in err_text and to_sleep > 60:
                    return None
                if not big_timeout and to_sleep > 600:
                    return None
                if to_sleep > 2000:
                    return None

                raise Exception('non 200')

            response_json = response.json()
            return response_json
        except Exception as e:
            print(f'Failed: {e}')
            print(f'Sleeping {to_sleep} seconds...')
            time.sleep(to_sleep)
            to_sleep *= 1.4


def get_specific_match_details(match_id):
    if DEBUG:
        return SPECIFIC_MATCH_SAMPLE

    #   https://api.tracker.gg/api/v1/warzone/matches/8986566823157720677
    if match_id in saved_matches:
        return saved_matches[match_id]

    match_json = make_api_request(f'https://api.tracker.gg/api/v1/warzone/matches/{match_id}')
    saved_matches[match_id] = match_json

    with open("saved_matches.p", "wb") as load_file:
        pickle.dump(saved_matches, load_file)

    return match_json

def matches_for_player(battlenet_id):
    if DEBUG:
        for m in SAMPLE_MATCHES:
            yield m
        return

    next = 'null'
    encoded_name = urllib.parse.quote(battlenet_id.lower())
    while next:
        response_json = make_api_request(f'https://api.tracker.gg/api/v1/warzone/matches/battlenet/{encoded_name}?type=wz&next={next}', big_timeout=True)
        if response_json is None:
            return

        next = response_json['data']['metadata']['next']
        for m in response_json['data']['matches']:
            yield m

        if not isinstance(next, int) or next < 10000000:
            return

def extract_stats_from_segment(seg, team_members):
    player_name = seg['attributes']['platformUserIdentifier']
    stats = {'player_name': player_name, 'placement': seg['metadata']['placement']['value']}
    for p_name in PLAYER_HANDLES:
        stats['has_'+p_name.strip()] = 1 if p_name in team_members else 0

    # for stat_name in ['kills', 'kdRatio', 'score', 'timePlayed', 'headshots', 'executions', 'assists', 'percentTimeMoving', 'longestStreak', 'scorePerMinute', 'damageDone', 'distanceTraveled', 'deaths', 'damageTaken', 'damageDonePerMinute']:
    # for stat_name, stat_dict in seg['stats'].items():
    for stat_name in ['kills', 'kdRatio', 'score', 'timePlayed', 'headshots', 'executions', 'assists', 'percentTimeMoving', 'longestStreak', 'scorePerMinute', 'damageDone', 'distanceTraveled', 'deaths', 'damageTaken', 'damageDonePerMinute', 'medalXp', 'objectiveTeamWiped', 'objectiveLastStandKill', 'matchXp', 'scoreXp', 'totalXp', 'challengeXp', 'objectiveDestroyedVehicleMedium', 'teamSurvivalTime', 'objectiveBrDownEnemyCircle3', 'objectiveBrDownEnemyCircle1', 'objectiveBrMissionPickupTablet', 'bonusXp', 'objectiveReviver', 'objectiveBrKioskBuy', 'objectiveBrDownEnemyCircle6', 'gulagDeaths', 'gulagKills', 'objectiveBrCacheOpen', 'miscXp']:
        if stat_name not in seg['stats']:
            stats[stat_name] = None
        else:
            stats[stat_name] = seg['stats'][stat_name]['value']
            # display_stat_name = stat_dict['displayName']
            # stats[display_stat_name] = stat_dict['value']

    return stats


already_seen_match_ids = set()

saved_matches = dict()
with open("saved_matches.p", "rb") as load_file:
    saved_matches = pickle.load(load_file)


with open('data_file.csv', 'w') as data_file:
    csv_writer = csv.writer(data_file)
    has_written_header = False
    num_columns = None

    for battlenet_id in BATTLENET_IDS:
        for match in matches_for_player(battlenet_id):
            match_id = match['attributes']['id']
            if match_id in already_seen_match_ids:
                continue
            already_seen_match_ids.add(match_id)

            match_details = get_specific_match_details(match_id)
            if match_details is None:
                continue

            segments = match_details['data']['segments']
            placements = set()
            for seg in segments:
                if seg['metadata']['platformUserHandle'] in PLAYER_HANDLES:
                    placements.add(seg['metadata']['placement']['value'])
            for placement in placements:
                team_segments = [seg for seg in segments if seg['metadata']['placement']['value'] == placement]
                team_members = [seg['attributes']['platformUserIdentifier'] for seg in team_segments]
                for seg in team_segments:
                    timestamp = match['metadata']['timestamp']
                    stats = {
                        **extract_stats_from_segment(seg, team_members),
                        'team_size': len(team_members),
                        'match_id': match['attributes']['id'],
                        'match_timestamp': timestamp,
                        'match_unix_timestamp': parse(timestr=timestamp).timestamp(),
                        'match_modeId': match['attributes']['modeId'],
                        'match_mapId': match['attributes']['mapId'],
                        'match_duration': match['metadata']['duration']['value'] / 1000,
                        'match_playerCount': match['metadata']['playerCount'],
                        'match_teamCount': match['metadata']['teamCount'],
                        'match_mapName': match['metadata']['mapName'],
                    }

                    if not has_written_header:
                        csv_writer.writerow(stats.keys())
                        has_written_header = True

                    if not num_columns:
                        num_columns = len(stats)
                    else:
                        assert num_columns == len(stats)

                    csv_writer.writerow(stats.values())
