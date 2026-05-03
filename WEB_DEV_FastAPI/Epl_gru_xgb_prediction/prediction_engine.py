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
import json
from datetime import datetime
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sqlalchemy import text
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
    "Southampton FC": "Southampton", "Southampton": "Southampton",
    "Leeds United FC": "Leeds", "Leeds United": "Leeds",
    "Sunderland AFC": "Sunderland", "Sunderland": "Sunderland",
    "Birmingham City FC": "Birmingham", "Birmingham City": "Birmingham",
    "Blackburn Rovers FC": "Blackburn", "Blackburn Rovers": "Blackburn",
    "Derby County FC": "Derby", "Derby County": "Derby",
    "Norwich City FC": "Norwich", "Norwich City": "Norwich",
    "Sheffield United FC": "Sheffield United", "Sheffield United": "Sheffield United",
    "Watford FC": "Watford", "Watford": "Watford",
    "West Bromwich Albion FC": "WBA", "West Bromwich Albion": "WBA",
    "Luton Town FC": "Luton", "Luton Town": "Luton",
    "Burnley FC": "Burnley", "Burnley": "Burnley"
}

TEAM_LOGO_MAP = {
    "Manchester City FC": "logos/Manchester_City.png",
    "Manchester United FC": "logos/Manchester_United.png",
    "Tottenham Hotspur FC": "logos/Tottenham_Hotspur.png",
    "Arsenal FC": "logos/Arsenal.png",
    "Liverpool FC": "logos/Liverpool.png",
    "Chelsea FC": "logos/Chelsea.png",
    "Aston Villa FC": "logos/Aston_Villa.png",
    "Newcastle United FC": "logos/Newcastle_United.png",
    "Brighton & Hove Albion FC": "logos/Brighton.png",
    "Brentford FC": "logos/Brentford.png",
    "West Ham United FC": "logos/West_Ham.png",
    "Crystal Palace FC": "logos/Crystal_Palace.png",
    "Fulham FC": "logos/Fulham.png",
    "AFC Bournemouth": "logos/Bournemouth.png",
    "Everton FC": "logos/Everton.png",
    "Nottingham Forest FC": "logos/Nottingham_Forest.png",
    "Wolverhampton Wanderers FC": "logos/Wolverhampton_Wanderers.png",
    "Leicester City FC": "logos/Leicester_City.png",
    "Ipswich Town FC": "logos/ipswich.png",
    "Southampton FC": "logos/Southampton.png",
    "Birmingham City FC": "logos/birmingham.png",
    "Blackburn Rovers FC": "logos/Blackburn_Rovers.png",
    "Derby County FC": "logos/Derby_County.png",
    "Sunderland AFC": "logos/Sunderland_AFC.png",
    "Leeds United FC": "logos/Leeds_United.png",
    "Norwich City FC": "logos/Norwich_City.png",
    "Sheffield United FC": "logos/Sheffield_United.png",
    "Watford FC": "logos/Watford.png",
    "West Bromwich Albion FC": "logos/West_brom.png",
    "Luton Town FC": "logos/Luton_Town.png",
    "Burnley FC": "logos/Burnley.png"
}

# Build normalized lookup so team names like "Man City" resolve correctly.
NORMALIZED_TEAM_LOGO_MAP = {}
for team_name, logo_path in TEAM_LOGO_MAP.items():
    NORMALIZED_TEAM_LOGO_MAP[team_name] = logo_path
    normalized_name = TEAM_NAME_MAP.get(team_name, team_name)
    NORMALIZED_TEAM_LOGO_MAP[normalized_name] = logo_path


def get_team_logo(team_name: str | None):
    if not team_name:
        return None
    logo_path = NORMALIZED_TEAM_LOGO_MAP.get(team_name)
    if not logo_path:
        return None
    logo_path = logo_path.replace("\\", "/")
    if logo_path.startswith("logos/"):
        return f"/{logo_path}"
    if logo_path.startswith("/logos/"):
        return logo_path
    return f"/{logo_path}"

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

def save_historical_data(db: Session):
    df_hist = fetch_historical_data()
    if df_hist is None:
        logger.warning("No historical data to save.")
        return

    # Sort by date and keep only last 25 matches
    df_hist = df_hist.sort_values('Date').tail(25)
    
    if len(df_hist) == 0:
        logger.warning("No historical data after filtering.")
        return

    # Clear existing historical data
    db.query(models.HistoricalMatch).delete()
    db.commit()

    historical_entries = []
    for _, row in df_hist.iterrows():
        historical_entries.append(models.HistoricalMatch(
            date=row['Date'],
            home_team=row['HomeTeam'],
            away_team=row['AwayTeam'],
            home_team_logo=get_team_logo(row['HomeTeam']),
            away_team_logo=get_team_logo(row['AwayTeam']),
            fthg=int(row.get('FTHG', 0)),
            ftag=int(row.get('FTAG', 0)),
            ftr=row.get('FTR', ''),
            hthg=int(row.get('HTHG', 0)),
            htag=int(row.get('HTAG', 0)),
            htr=row.get('HTR', ''),
            hs=int(row.get('HS', 0)),
            as_=int(row.get('AS', 0)),
            hst=int(row.get('HST', 0)),
            ast=int(row.get('AST', 0)),
            hc=int(row.get('HC', 0)),
            ac=int(row.get('AC', 0)),
            hf=int(row.get('HF', 0)),
            af=int(row.get('AF', 0)),
            hy=int(row.get('HY', 0)),
            ay=int(row.get('AY', 0)),
            hr=int(row.get('HR', 0)),
            ar=int(row.get('AR', 0))
        ))

    db.add_all(historical_entries)
    db.commit()
    logger.info(f"Saved {len(historical_entries)} last historical matches to DB.")

def dedupe_prediction_history(db: Session):
    """Remove duplicate prediction history rows and keep the latest entry per match."""
    try:
        db.execute(text(
            """
            DELETE FROM prediction_history
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM prediction_history
                GROUP BY match_date, home_team, away_team
            )
            """
        ))
        db.commit()
        logger.info("Removed duplicate prediction history rows.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to dedupe prediction history: {e}")


def run_prediction_pipeline(db: Session):
    try:
        # Save historical data if not already saved
        save_historical_data(db)
        dedupe_prediction_history(db)

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
                home_team_logo=get_team_logo(row['HomeTeam']),
                away_team_logo=get_team_logo(row['AwayTeam']),
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

            actual_result = None
            model_was_correct = None
            
            history_entries.append(models.PredictionHistory(
                match_date=prediction.match_date,
                home_team=prediction.home_team,
                away_team=prediction.away_team,
                home_team_logo=prediction.home_team_logo,
                away_team_logo=prediction.away_team_logo,
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
                actual_result=actual_result,
                model_was_correct=model_was_correct
            ))

            final_preds.append(prediction)

        db.query(models.Prediction).delete()
        for entry in history_entries:
            db.query(models.PredictionHistory).filter_by(
                match_date=entry.match_date,
                home_team=entry.home_team,
                away_team=entry.away_team
            ).delete()

        db.add_all(final_preds)
        db.add_all(history_entries)
        db.commit()
        logger.info(f"Pipeline complete. {len(final_preds)} live predictions saved and archived.")

        # Create notifications for all users about new predictions
        create_prediction_notifications(db, final_preds)
        create_match_day_notifications(db, to_predict.to_dict('records'))
        create_milestone_notifications(db)
        
        # Update prediction accuracy based on historical results
        compute_prediction_accuracy(db)

    except Exception as e:
        db.rollback()
        logger.error(f"Pipeline failure: {e}")


def create_prediction_notifications(db: Session, predictions: list):
    """Create notifications for users about new predictions."""
    try:
        users = db.query(models.User).all()
        notifications = []
        
        for user in users:
            # Notification for new predictions
            notification = models.Notification(
                user_id=user.id,
                title="New Match Predictions Available",
                message=f"Predictions for {len(predictions)} upcoming EPL matches are now available! Check them out.",
                type="prediction",
                data=json.dumps({"prediction_count": len(predictions)})
            )
            notifications.append(notification)
            
            # If there are high-confidence predictions, notify about them
            high_conf = [p for p in predictions if p.confidence > 0.7]
            if high_conf:
                notification = models.Notification(
                    user_id=user.id,
                    title="High Confidence Predictions",
                    message=f"We have {len(high_conf)} predictions with over 70% confidence. Don't miss out!",
                    type="prediction",
                    data=json.dumps({"high_conf_count": len(high_conf)})
                )
                notifications.append(notification)
        
        db.add_all(notifications)
        db.commit()
        logger.info(f"Created {len(notifications)} prediction notifications for {len(users)} users.")
        
    except Exception as e:
        logger.error(f"Failed to create prediction notifications: {e}")


def create_accuracy_notification(db: Session, match_result: dict):
    """Create notification when a prediction's accuracy is determined."""
    try:
        # Find users who might be interested (perhaps those who viewed the prediction)
        # For now, create for all users or based on some criteria
        users = db.query(models.User).all()
        notifications = []
        
        correct = match_result.get('correct', False)
        home_team = match_result.get('home_team')
        away_team = match_result.get('away_team')
        
        title = "Prediction Result: " + ("Correct!" if correct else "Missed!")
        message = f"Our prediction for {home_team} vs {away_team} was {'correct' if correct else 'incorrect'}."
        
        for user in users:
            notification = models.Notification(
                user_id=user.id,
                title=title,
                message=message,
                type="accuracy",
                data=json.dumps({
                    "home_team": home_team,
                    "away_team": away_team,
                    "correct": correct
                })
            )
            notifications.append(notification)
        
        db.add_all(notifications)
        db.commit()
        logger.info(f"Created accuracy notifications for match: {home_team} vs {away_team}")
        
    except Exception as e:
        logger.error(f"Failed to create accuracy notification: {e}")


def create_weekly_summary_notification(db: Session):
    """Create weekly summary notifications for users."""
    try:
        # Calculate this week's stats
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        total_predictions = db.query(models.PredictionHistory).filter(
            models.PredictionHistory.created_at >= week_ago
        ).count()
        
        correct_predictions = db.query(models.PredictionHistory).filter(
            models.PredictionHistory.created_at >= week_ago,
            models.PredictionHistory.model_was_correct == True
        ).count()
        
        accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
        
        users = db.query(models.User).all()
        notifications = []
        
        for user in users:
            notification = models.Notification(
                user_id=user.id,
                title="Weekly Prediction Summary",
                message=f"This week: {correct_predictions}/{total_predictions} predictions correct ({accuracy:.1f}% accuracy)",
                type="summary",
                data=json.dumps({
                    "total": total_predictions,
                    "correct": correct_predictions,
                    "accuracy": accuracy
                })
            )
            notifications.append(notification)
        
        db.add_all(notifications)
        db.commit()
        logger.info(f"Created weekly summary notifications for {len(users)} users.")
        
    except Exception as e:
        logger.error(f"Failed to create weekly summary notifications: {e}")


def create_match_day_notifications(db: Session, upcoming_matches: list):
    """Create notifications for matches happening today."""
    try:
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        
        today_matches = [m for m in upcoming_matches if m['Date'].date() == today]
        if not today_matches:
            return
            
        users = db.query(models.User).all()
        notifications = []
        
        for user in users:
            match_list = [f"{m['HomeTeam']} vs {m['AwayTeam']}" for m in today_matches]
            notification = models.Notification(
                user_id=user.id,
                title="Match Day Alert!",
                message=f"{len(today_matches)} EPL matches are happening today. Check our predictions!",
                type="match",
                data=json.dumps({
                    "match_count": len(today_matches),
                    "matches": match_list
                })
            )
            notifications.append(notification)
        
        db.add_all(notifications)
        db.commit()
        logger.info(f"Created match day notifications for {len(today_matches)} matches.")
        
    except Exception as e:
        logger.error(f"Failed to create match day notifications: {e}")


def create_milestone_notifications(db: Session):
    """Create notifications for prediction milestones (e.g., 100 predictions, accuracy milestones)."""
    try:
        total_predictions = db.query(models.PredictionHistory).count()
        correct_predictions = db.query(models.PredictionHistory).filter(
            models.PredictionHistory.model_was_correct == True
        ).count()
        
        accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
        
        users = db.query(models.User).all()
        notifications = []
        
        # Milestone notifications
        milestones = [10, 25, 50, 100, 250, 500, 1000]
        for milestone in milestones:
            if total_predictions == milestone:
                for user in users:
                    notification = models.Notification(
                        user_id=user.id,
                        title="Prediction Milestone Reached!",
                        message=f"We've now made {milestone} predictions! Keep tracking our accuracy.",
                        type="milestone",
                        data=json.dumps({
                            "milestone": milestone,
                            "total_predictions": total_predictions
                        })
                    )
                    notifications.append(notification)
                break
        
        # Accuracy milestone
        accuracy_milestones = [50, 60, 70, 75, 80]
        for acc_milestone in accuracy_milestones:
            if accuracy >= acc_milestone and accuracy < acc_milestone + 1:  # Rough check to avoid spam
                for user in users:
                    notification = models.Notification(
                        user_id=user.id,
                        title="Accuracy Milestone!",
                        message=f"Our model has achieved {accuracy:.1f}% accuracy across all predictions!",
                        type="milestone",
                        data=json.dumps({
                            "accuracy": accuracy,
                            "total": total_predictions,
                            "correct": correct_predictions
                        })
                    )
                    notifications.append(notification)
                break
        
        if notifications:
            db.add_all(notifications)
            db.commit()
            logger.info(f"Created {len(notifications)} milestone notifications.")
        
    except Exception as e:
        logger.error(f"Failed to create milestone notifications: {e}")


def compute_prediction_accuracy(db: Session):
    """Analyze the last 10 historical matches vs predictions and compute accuracy metrics."""
    try:
        logger.info("Starting prediction accuracy computation...")
        
        # Get the last 10 historical matches (most recent first)
        historical_matches = db.query(models.HistoricalMatch).order_by(models.HistoricalMatch.date.desc()).limit(10).all()
        logger.info(f"Found {len(historical_matches)} historical matches (last 10)")
        
        # Get all prediction history entries
        predictions = db.query(models.PredictionHistory).all()
        logger.info(f"Found {len(predictions)} prediction history entries")
        
        # Create lookup dictionaries for faster matching
        hist_lookup = {}
        for match in historical_matches:
            key = (match.date.date(), match.home_team.lower(), match.away_team.lower())
            hist_lookup[key] = match
        
        pred_lookup = {}
        for pred in predictions:
            key = (pred.match_date.date(), pred.home_team.lower(), pred.away_team.lower())
            pred_lookup[key] = pred
        
        updated_predictions = []
        total_checked = 0
        correct_predictions = 0
        home_correct = 0
        draw_correct = 0
        away_correct = 0
        
        # Match predictions with historical results for the last 10 matches
        for pred_key, prediction in pred_lookup.items():
            if pred_key in hist_lookup:
                historical = hist_lookup[pred_key]
                total_checked += 1
                
                # Map historical result to our format
                actual_result = historical.ftr  # H, D, A
                
                # Determine if prediction was correct
                predicted_outcome = prediction.outcome
                was_correct = False
                
                if predicted_outcome == "Home Win" and actual_result == "H":
                    was_correct = True
                    home_correct += 1
                elif predicted_outcome == "Draw" and actual_result == "D":
                    was_correct = True
                    draw_correct += 1
                elif predicted_outcome == "Away Win" and actual_result == "A":
                    was_correct = True
                    away_correct += 1
                
                if was_correct:
                    correct_predictions += 1
                
                # Update the prediction record
                prediction.actual_result = actual_result
                prediction.model_was_correct = was_correct
                updated_predictions.append(prediction)
                
                logger.debug(f"Match {historical.home_team} vs {historical.away_team}: Predicted {predicted_outcome}, Actual {actual_result}, Correct: {was_correct}")
        
        # Save updates to database
        if updated_predictions:
            db.bulk_save_objects(updated_predictions)
            db.commit()
            logger.info(f"Updated {len(updated_predictions)} prediction records with actual results")
        
        # Calculate accuracy metrics
        accuracy = (correct_predictions / total_checked * 100) if total_checked > 0 else 0
        
        # Calculate confidence-based accuracy
        high_conf_correct = 0
        high_conf_total = 0
        for pred in updated_predictions:
            if pred.confidence > 0.7:
                high_conf_total += 1
                if pred.model_was_correct:
                    high_conf_correct += 1
        
        high_conf_accuracy = (high_conf_correct / high_conf_total * 100) if high_conf_total > 0 else 0
        
        # Calculate recent accuracy (last 30 days)
        thirty_days_ago = datetime.utcnow() - pd.Timedelta(days=30)
        recent_predictions = [p for p in updated_predictions if p.match_date >= thirty_days_ago]
        recent_correct = sum(1 for p in recent_predictions if p.model_was_correct)
        recent_accuracy = (recent_correct / len(recent_predictions) * 100) if recent_predictions else 0
        
        accuracy_stats = {
            "total_predictions_analyzed": total_checked,
            "correct_predictions": correct_predictions,
            "overall_accuracy": round(accuracy, 2),
            "home_win_accuracy": round((home_correct / (home_correct + draw_correct + away_correct) * 100) if (home_correct + draw_correct + away_correct) > 0 else 0, 2),
            "draw_accuracy": round((draw_correct / (home_correct + draw_correct + away_correct) * 100) if (home_correct + draw_correct + away_correct) > 0 else 0, 2),
            "away_win_accuracy": round((away_correct / (home_correct + draw_correct + away_correct) * 100) if (home_correct + draw_correct + away_correct) > 0 else 0, 2),
            "high_confidence_accuracy": round(high_conf_accuracy, 2),
            "high_confidence_predictions": high_conf_total,
            "recent_accuracy_30_days": round(recent_accuracy, 2),
            "recent_predictions_count": len(recent_predictions),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Accuracy computation complete: {accuracy:.2f}% overall accuracy from last {total_checked} matches")
        return accuracy_stats
        
    except Exception as e:
        logger.error(f"Failed to compute prediction accuracy: {e}")
        db.rollback()
        return {
            "error": str(e),
            "total_predictions_analyzed": 0,
            "correct_predictions": 0,
            "overall_accuracy": 0.0,
            "last_updated": datetime.utcnow().isoformat()
        }


def get_prediction_accuracy_stats(db: Session):
    """Get cached or compute fresh accuracy statistics for the last 10 matches."""
    try:
        # Try to get from cache first (you could implement caching here)
        # For now, always compute fresh
        return compute_prediction_accuracy(db)
    except Exception as e:
        logger.error(f"Failed to get prediction accuracy stats: {e}")
        return {
            "error": str(e),
            "total_predictions_analyzed": 0,
            "correct_predictions": 0,
            "overall_accuracy": 0.0,
            "last_updated": datetime.utcnow().isoformat()
        }