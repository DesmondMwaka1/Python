import os
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import joblib
import requests
import io
import logging
import sys
import warnings
from datetime import datetime
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sqlalchemy.orm import Session
import models

# Try to import xgboost; handle error gracefully
try:
    import xgboost as xgb
except ImportError:
    xgb = None

# Suppress pandas fragmentation warnings
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

logger = logging.getLogger(__name__)

# ==========================================
# 0. CONFIGURATION & MAPPING
# ==========================================
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
SPORT = "soccer_epl"
REGION = "uk"
MARKET = "h2h"

TEAM_NAME_MAP = {
    "Manchester City FC": "Man City", "Manchester City": "Man City",
    "Manchester United FC": "Man United", "Manchester United": "Man United",
    "Tottenham Hotspur FC": "Tottenham", "Tottenham Hotspur": "Tottenham",
    "Arsenal FC": "Arsenal", "Arsenal": "Arsenal",
    "Liverpool FC": "Liverpool", "Liverpool": "Liverpool",
    "Chelsea FC": "Chelsea", "Chelsea": "Chelsea",
    "Aston Villa FC": "Aston Villa", "Aston Villa": "Aston Villa",
    "Newcastle United FC": "Newcastle", "Newcastle United": "Newcastle",
    "Brighton & Hove Albion FC": "Brighton", "Brighton and Hove Albion": "Brighton",
    "Brentford FC": "Brentford", "Brentford": "Brentford",
    "West Ham United FC": "West Ham", "West Ham United": "West Ham",
    "Crystal Palace FC": "Crystal Palace", "Crystal Palace": "Crystal Palace",
    "Fulham FC": "Fulham", "Fulham": "Fulham",
    "AFC Bournemouth": "Bournemouth", "Bournemouth": "Bournemouth",
    "Everton FC": "Everton", "Everton": "Everton",
    "Nottingham Forest FC": "Nott'm Forest", "Nottingham Forest": "Nott'm Forest",
    "Wolverhampton Wanderers FC": "Wolves", "Wolverhampton Wanderers": "Wolves",
    "Leicester City FC": "Leicester", "Leicester City": "Leicester",
    "Ipswich Town FC": "Ipswich", "Ipswich Town": "Ipswich",
    "Southampton FC": "Southampton", "Southampton": "Southampton"
}

class FootballGRU(nn.Module):
    def __init__(self, input_size=32, hidden_size=32, num_classes=3, num_layers=1):
        super().__init__()
        self.hidden_size, self.num_layers = hidden_size, num_layers
        self.gru = nn.GRU(input_size, hidden_size, num_layers=num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, num_classes)
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        _, hn = self.gru(x, h0)
        latent = hn[-1]
        return self.fc(latent), latent

# Essential for joblib/torch loading cross-compatibility
sys.modules['__main__'].FootballGRU = FootballGRU

def fetch_real_time_odds():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {'apiKey': ODDS_API_KEY, 'regions': REGION, 'markets': MARKET, 'oddsFormat': 'decimal'}
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200: return {}
        data = response.json()
        odds_lookup = {}
        for match in data:
            h_norm = TEAM_NAME_MAP.get(match['home_team'], match['home_team'])
            a_norm = TEAM_NAME_MAP.get(match['away_team'], match['away_team'])
            h_odds, d_odds, a_odds = [], [], []
            for bookie in match['bookmakers']:
                m_data = next((m for m in bookie['markets'] if m['key'] == 'h2h'), None)
                if m_data:
                    for outcome in m_data['outcomes']:
                        if outcome['name'] == match['home_team']: h_odds.append(outcome['price'])
                        elif outcome['name'] == match['away_team']: a_odds.append(outcome['price'])
                        elif outcome['name'] == 'Draw': d_odds.append(outcome['price'])
            if h_odds and d_odds and a_odds:
                odds_lookup[f"{h_norm}|{a_norm}"] = (np.mean(h_odds), np.mean(d_odds), np.mean(a_odds))
        return odds_lookup
    except Exception as e:
        logger.error(f"Odds Error: {e}")
        return {}

def fetch_upcoming_fixtures():
    url = "https://api.football-data.org/v4/competitions/PL/matches"
    headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
    params = {'status': 'SCHEDULED'}
    live_odds_data = fetch_real_time_odds()
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        all_matches = data.get('matches', [])
        if not all_matches: return pd.DataFrame()
        
        all_matches.sort(key=lambda x: x['utcDate'])
        next_10 = all_matches[:10]
        fix_rows = []
        for m in next_10:
            m_date = pd.to_datetime(m['utcDate']).tz_localize(None)
            h_name = TEAM_NAME_MAP.get(m['homeTeam']['name'], m['homeTeam']['name'])
            a_name = TEAM_NAME_MAP.get(m['awayTeam']['name'], m['awayTeam']['name'])
            odds_key = f"{h_name}|{a_name}"
            o_h, o_d, o_a = live_odds_data.get(odds_key, (2.30, 3.30, 3.00))
            fix_rows.append({
                "Date": m_date, "HomeTeam": h_name, "AwayTeam": a_name,
                "AvgH": round(o_h, 2), "AvgD": round(o_d, 2), "AvgA": round(o_a, 2), "FTR": "U"
            })
        return pd.DataFrame(fix_rows)
    except Exception as e:
        logger.error(f"Fixtures Error: {e}")
        return pd.DataFrame()

def fetch_historical_data():
    now = datetime.now()
    season = f"{str(now.year-1)[2:]}{str(now.year)[2:]}" if now.month < 8 else f"{str(now.year)[2:]}{str(now.year+1)[2:]}"
    url = f"https://www.football-data.co.uk/mmz4281/{season}/E0.csv"
    try:
        r = requests.get(url)
        df = pd.read_csv(io.StringIO(r.text))
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').dt.tz_localize(None)
        df['HomeTeam'] = df['HomeTeam'].apply(lambda x: TEAM_NAME_MAP.get(x, x))
        df['AwayTeam'] = df['AwayTeam'].apply(lambda x: TEAM_NAME_MAP.get(x, x))
        return df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
    except Exception as e:
        logger.error(f"Historical Data Error: {e}")
        return None

def run_prediction_pipeline(db: Session):
    try:
        if xgb is None:
            logger.error("Pipeline failure: xgboost is not installed in the environment.")
            return

        df_hist = fetch_historical_data()
        df_upcoming = fetch_upcoming_fixtures()
        
        if df_hist is None or df_upcoming.empty:
            logger.warning("Pipeline aborted: Missing historical or upcoming data.")
            return

        le = LabelEncoder()
        all_teams = pd.concat([df_hist['HomeTeam'], df_hist['AwayTeam'], df_upcoming['HomeTeam'], df_upcoming['AwayTeam']]).unique()
        le.fit(all_teams)
        
        # De-fragment by copying after concatenation
        df_full = pd.concat([df_hist, df_upcoming], ignore_index=True).copy()
        df_full['HomeTeam_ID'] = le.transform(df_full['HomeTeam'])
        df_full['AwayTeam_ID'] = le.transform(df_full['AwayTeam'])

        df_full = df_full.sort_values('Date').reset_index(drop=True)
        df_full['h2h_id'] = df_full.apply(lambda x: f"{min(str(x['HomeTeam']), str(x['AwayTeam']))}_{max(str(x['HomeTeam']), str(x['AwayTeam']))}", axis=1)
        
        # Initialize rates
        df_full['h2h_home_win_rate'] = 0.33
        df_full['h2h_draw_rate'] = 0.33
        
        for _, group in df_full.groupby('h2h_id'):
            past = group['FTR'].shift(1)
            count = np.arange(len(group))
            mask = count > 0
            df_full.loc[group.index[mask], 'h2h_home_win_rate'] = (past == 'H').cumsum()[mask] / count[mask]
            df_full.loc[group.index[mask], 'h2h_draw_rate'] = (past == 'D').cumsum()[mask] / count[mask]

        to_predict = df_full[df_full['FTR'] == 'U'].copy()
        seqs, static_facts = [], []
        window = 5
        null_vector = np.zeros(16, dtype=np.float32)

        for _, match in to_predict.iterrows():
            h_id, a_id = match['HomeTeam'], match['AwayTeam']
            history_pool = df_full[df_full['Date'] < match['Date']]
            
            h_h = history_pool[(history_pool['HomeTeam'] == h_id) | (history_pool['AwayTeam'] == h_id)].tail(window)
            a_h = history_pool[(history_pool['HomeTeam'] == a_id) | (history_pool['AwayTeam'] == a_id)].tail(window)
            
            def get_vector(r):
                cols = ['FTHG','FTAG','HTHG','HTAG','HS','AS','HST','AST','HC','AC','HF','AF','HY','AY','HR','AR']
                # Notebook logic: fillna(0)
                return r[cols].fillna(0).values.astype(np.float32)

            h_seq = [get_vector(r) for _, r in h_h.iterrows()]
            while len(h_seq) < window: h_seq.insert(0, null_vector)
            
            a_seq = [get_vector(r) for _, r in a_h.iterrows()]
            while len(a_seq) < window: a_seq.insert(0, null_vector)
            
            seqs.append(np.hstack([np.array(h_seq), np.array(a_seq)]))
            static_facts.append([
                match['HomeTeam_ID'], match['AwayTeam_ID'], 
                match['AvgH'], match['AvgD'], match['AvgA'], 
                match['h2h_home_win_rate'], match['h2h_draw_rate']
            ])

        if not seqs: return

        # Robust Model Loading
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        gru_model = FootballGRU().to(device)
        
        # Load pkl which could be state_dict or full model
        loaded_obj = joblib.load("models/final_model_GRU_5.pkl")
        if isinstance(loaded_obj, dict):
            gru_model.load_state_dict(loaded_obj)
        elif hasattr(loaded_obj, 'state_dict'):
            gru_model.load_state_dict(loaded_obj.state_dict())
        else:
            # Fallback if it's just the weights file directly from torch.save
            gru_model.load_state_dict(torch.load("models/final_model_GRU_5.pkl", map_location=device))
        
        gru_model.eval()

        with torch.no_grad():
            _, momentum_raw = gru_model(torch.tensor(np.array(seqs), dtype=torch.float32).to(device))
            momentum = momentum_raw.cpu().numpy()

        scaler = MinMaxScaler(feature_range=(0, 100))
        m_scaled = scaler.fit_transform(momentum)

        xgb_model = joblib.load("models/best_model_6_tuned_xgboost.pkl")
        static_arr = np.array(static_facts)
        
        # Ensure static_arr is 2D even if 1 row
        if static_arr.ndim == 1:
            static_arr = static_arr.reshape(1, -1)
            
        probs = xgb_model.predict_proba(np.hstack([static_arr, momentum]))

        final_preds = []
        history_entries = []
        for i, (_, row) in enumerate(to_predict.iterrows()):
            p = probs[i]
            ms = m_scaled[i]
            
            prediction = models.Prediction(
                match_date=row['Date'],
                home_team=row['HomeTeam'],
                away_team=row['AwayTeam'],
                home_team_id=int(row['HomeTeam_ID']),
                away_team_id=int(row['AwayTeam_ID']),
                avg_h=row['AvgH'], avg_d=row['AvgD'], avg_a=row['AvgA'],
                h_attacking=float(np.mean(ms[0:4])),
                h_defending=float(np.mean(ms[4:8])),
                h_volatility=float(np.mean(ms[8:12])),
                h_efficiency=float(np.mean(ms[12:16])),
                a_attacking=float(np.mean(ms[16:20])),
                a_defending=float(np.mean(ms[20:24])),
                a_volatility=float(np.mean(ms[24:28])),
                a_efficiency=float(np.mean(ms[28:32])),
                prob_home=round(float(p[2]), 3),
                prob_draw=round(float(p[1]), 3),
                prob_away=round(float(p[0]), 3),
                outcome={0: 'Away Win', 1: 'Draw', 2: 'Home Win'}[np.argmax(p)],
                confidence=round(float(np.max(p)), 3)
            )

            history_entries.append(models.PredictionHistory(
                match_date=prediction.match_date,
                home_team=prediction.home_team,
                away_team=prediction.away_team,
                home_team_id=prediction.home_team_id,
                away_team_id=prediction.away_team_id,
                avg_h=prediction.avg_h,
                avg_d=prediction.avg_d,
                avg_a=prediction.avg_a,
                h_attacking=prediction.h_attacking,
                h_defending=prediction.h_defending,
                h_volatility=prediction.h_volatility,
                h_efficiency=prediction.h_efficiency,
                a_attacking=prediction.a_attacking,
                a_defending=prediction.a_defending,
                a_volatility=prediction.a_volatility,
                a_efficiency=prediction.a_efficiency,
                prob_home=prediction.prob_home,
                prob_draw=prediction.prob_draw,
                prob_away=prediction.prob_away,
                outcome=prediction.outcome,
                confidence=prediction.confidence,
            ))

            final_preds.append(prediction)

        db.query(models.Prediction).delete()
        db.add_all(final_preds)
        db.add_all(history_entries)
        db.commit()
        logger.info(f"Pipeline complete. {len(final_preds)} live predictions saved and archived.")

    except Exception as e:
        db.rollback()
        logger.error(f"Pipeline failure: {e}")