import pandas as pd
import streamlit as st
import numpy as np
import json
import os

next_ten = pd.read_json('data/EPL_next_ten.json', orient='table')
next_ten.reset_index(inplace=True)

st.set_page_config(layout="wide")
st.title('EPL Betting Recommendations')

# st.write(next_ten)

frac = 10

def calc_bet(match: pd.Series, H_odds, D_odds, A_odds):

    marg = 1.8

    if match['uncertain'] == 1:
        return 'N', 0.0

    bet = 'N'
    b = 0.0 # Represents the decimal odds - 1, i.e. the multiplier to calculate profit relative to the bet amount if the bet wins.

    # Check each outcome to see if the margin is exceeded. Place a bet on the outcome with the greatest margin.
    if match['H_prob'] * H_odds > marg:
        bet = 'H'
        marg = match['H_prob'] * H_odds
        b = H_odds - 1
        p = match['H_prob']
    if match['D_prob'] * D_odds > marg:
        bet = 'D'
        marg = match['D_prob'] * D_odds
        b = D_odds - 1
        p = match['D_prob']
    if match['A_prob'] * A_odds > marg:
        bet = 'A'
        marg = match['A_prob'] * A_odds
        b = A_odds - 1
        p = match['A_prob']

    # Calculate Kelly Criterion of the bet
    f = (((b + 1) * p) - 1) / b if b else 0.0
    f = np.maximum(f, 0.0)

    return bet, f

# Initialize session state for bet recommendations if not already present
if 'recommendations' not in st.session_state:
    st.session_state['recommendations'] = [None] * len(next_ten)

# Display table headers
header_cols = st.columns([5, 1.5, 1.5, 1.5, 2, 2, 2, 2, 1, 2, 2])
header_cols[0].write("Match")
header_cols[1].write("Home")
header_cols[2].write("Draw")
header_cols[3].write("Away")
header_cols[4].write("Odds Home")
header_cols[5].write("Odds Draw")
header_cols[6].write("Odds Away")
header_cols[7].write("Calculate")
header_cols[8].write("Bet")
header_cols[9].write("Bankroll %")

# Loop through each game and create a row in the table with user inputs
for index, row in next_ten.iterrows():
    col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11 = st.columns([5, 1.5, 1.5, 1.5, 2, 2, 2, 2, 1, 2, 2])

    # Display game information
    col1.write(f"{row['home_team']} vs {row['away_team']}")
    col2.write(f"{round(row['H_prob'], 2)}")
    col3.write(f"{round(row['D_prob'], 2)}")
    col4.write(f"{round(row['A_prob'], 2)}")

    # Input fields for odds
    odds_home = col5.text_input("Enter Home Odds",key=f"odds_home_{index}", label_visibility="collapsed")
    odds_draw = col6.text_input("Enter Draw Odds", key=f"odds_draw_{index}", label_visibility="collapsed")
    odds_away = col7.text_input("Enter Away Odds", key=f"odds_away_{index}", label_visibility="collapsed")

    # Button to calculate bet recommendation
    if col8.button("Bet", key=index):
            
        odds_home = float(odds_home) if odds_home else 0
        odds_draw = float(odds_draw) if odds_draw else 0
        odds_away = float(odds_away) if odds_away else 0
        
        # Call the bet recommendation function
        recommendation, fraction = calc_bet(row, odds_home, odds_draw, odds_away)
        
        col9.write(f"{recommendation}")
        col10.write(f"{(fraction / frac):.2%}")

        # Store the recommendation in session state
        st.session_state['recommendations'][index] = (recommendation, fraction)

    # Display previous recommendation if it exists
    elif st.session_state['recommendations'][index] is not None:
        recommendation, fraction = st.session_state['recommendations'][index]
        col9.write(f"{recommendation}")
        col10.write(f"{(fraction / frac):.2%}")


    # Add button to save placed bets
    if col11.button("Bet placed", key=f'Bet placed {index}'):

        if odds_home and odds_draw and odds_away and (st.session_state['recommendations'][index] is not None):

            bet_placed = {'match_id': row['match_id'], 'home_team': row['home_team'], 'away_team': row['away_team'], 
                          'H_prob': row['H_prob'], 'D_prob': row['D_prob'], 'A_prob': row['A_prob'],
                          'H_odds': odds_home, 'D_odds': odds_draw, 'A_odds': odds_away, 
                          'Bet': recommendation, 'Bankroll %': (fraction / frac) * 100}
        
        try:
            bets_data = pd.read_json('data/EPL_bets_placed.json', orient='table')
            bets_data = pd.concat([bets_data, pd.DataFrame([bet_placed])], ignore_index=False)
        except ValueError:
            bets_data = pd.DataFrame([bet_placed])

        bets_data.set_index('match_id', inplace=True)
        bets_data.to_json('data/EPL_bets_placed.json', orient='table', indent=4)
