import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
from statistics import fmean
from scipy.stats import poisson

def import_next_ten():

    game_data = []
    # Scrape this season's page
    res = requests.get(f'https://understat.com/league/EPL/2024')
    soup = BeautifulSoup(res.content, 'lxml')
    scripts = soup.find_all('script')

    # Get fixtures data
    string = scripts[1].string
    ind_start = string.index("('") + 2
    ind_end = string.index("')")
    json_data = string[ind_start:ind_end]
    json_data = json_data.encode('utf8').decode('unicode_escape')
    data = json.loads(json_data)

    # Format new data
    for d in data:
        if d['isResult'] == False:
            game_data.append({
                'match_id': d['id'],
                'isResult': d['isResult'],
                'season': 2024,
                'competition': 'EPL',
                'date': d['datetime'],
                'home_team': d['h']['title'],
                'away_team': d['a']['title'],
                'h_id': d['h']['id'],
                'a_id': d['a']['id'],
                'home_goals': d["goals"]["h"],
                'away_goals': d["goals"]["a"],
                'home_xG':d['xG']['h'],
                'away_xG': d['xG']['a']
            })

    fixtures = pd.DataFrame(game_data[:10])

    fixtures['isResult'] = fixtures['isResult'].astype(bool)
    fixtures['season'] = fixtures['season'].astype(int)
    fixtures['date'] = pd.to_datetime(fixtures['date'])
    fixtures['h_id'] = fixtures['h_id'].astype(int)
    fixtures['a_id'] = fixtures['a_id'].astype(int)

    return fixtures

def add_stats(fixtures: pd.DataFrame):

    with open('data/EPL_stats.json', 'r') as stats_json:
        EPL_stats = json.load(stats_json)

    fixtures[['H_Off', 'H_Def', 'A_Off', 'A_Def', 'avg_HxG', 'avg_AxG', 'uncertain']] = 0.0

    for i, row in fixtures.iterrows():
        uncertain = 0

        h_team, a_team = row['home_team'], row['away_team']

        H_Off = fmean(EPL_stats['teams'][h_team]['stats']['H_Off'])
        H_Def = fmean(EPL_stats['teams'][h_team]['stats']['H_Def'])
        A_Off = fmean(EPL_stats['teams'][a_team]['stats']['A_Off'])
        A_Def = fmean(EPL_stats['teams'][a_team]['stats']['A_Def'])
        avg_HxG = fmean(EPL_stats['averages']['HxG'])
        avg_AxG = fmean(EPL_stats['averages']['AxG'])

        h_games = EPL_stats['teams'][h_team]['games']['H']
        a_games = EPL_stats['teams'][h_team]['games']['A']

        if h_games < 10 or a_games < 10:
            uncertain = 1

        fixtures.loc[i, ['H_Off', 'H_Def', 'A_Off', 'A_Def', 'avg_HxG', 'avg_AxG', 'uncertain']] = H_Off, H_Def, A_Off, A_Def, avg_HxG, avg_AxG, uncertain

    return fixtures

def sim_game(HO, HD, AO, AD, HAvg, AAvg):
        
    hWin_scores = [(x, y) for x in range(11) for y in range(11) if x > y]
    draw_scores = [(x, x) for x in range(11)]
    aWin_scores = [(x, y) for x in range(11) for y in range(11) if x < y]

    xHxG = HAvg * HO * AD
    xAxG = AAvg * AO * HD

    h_prob = 0.0
    d_prob = 0.0
    a_prob = 0.0

    for score in hWin_scores:
        h_prob += poisson.pmf(score[0], xHxG) * poisson.pmf(score[1], xAxG)
    for score in draw_scores:
        d_prob += poisson.pmf(score[0], xHxG) * poisson.pmf(score[1], xAxG)
    for score in aWin_scores:
        a_prob += poisson.pmf(score[0], xHxG) * poisson.pmf(score[1], xAxG)

    return h_prob, d_prob, a_prob

def sim_future_games(fixtures: pd.DataFrame):

    fixtures[['H_prob', 'D_prob', 'A_prob']] = 0.0

    for i, row in fixtures.iterrows():

        H_Off, H_Def, A_Off, A_Def, avg_HxG, avg_AxG = row['H_Off'], row['H_Def'], row['A_Off'], row['A_Def'], row['avg_HxG'], row['avg_AxG']

        fixtures.loc[i, ['H_prob', 'D_prob', 'A_prob']] = sim_game(H_Off, H_Def, A_Off, A_Def, avg_HxG, avg_AxG)

    fixtures['pred_result'] = fixtures[['H_prob', 'D_prob', 'A_prob']].idxmax(axis=1).apply(lambda x: x[0])

    return fixtures

if __name__ == '__main__':

    next_ten = import_next_ten()
    next_ten = add_stats(next_ten.copy())
    next_ten = sim_future_games(next_ten.copy())
    
    next_ten.set_index('match_id', inplace=True)
    next_ten.to_json('data/EPL_next_ten.json', orient='table', indent=4)