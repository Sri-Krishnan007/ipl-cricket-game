from flask import Flask, render_template, request, session, jsonify
from shot import (
    simulate_ball,
    get_dropdown_data,
    get_shot_rating,
    calculate_effective_score,
    SHOT_MAX_RUNS
)
import random

app = Flask(__name__)
app.secret_key = "ipl_engine"

# ----------------------------
# TEAM DATA
# ----------------------------

CSK_PLAYERS = [
    {"name": "Ruturaj Gaikwad", "bat": 90, "bowl": 0},
    {"name": "Devon Conway", "bat": 88, "bowl": 0},
    {"name": "Ajinkya Rahane", "bat": 86, "bowl": 0},
    {"name": "Shivam Dube", "bat": 77, "bowl": 70},
    {"name": "Ravindra Jadeja", "bat": 75, "bowl": 85},
    {"name": "MS Dhoni", "bat": 80, "bowl": 0},
    {"name": "Moeen Ali", "bat": 70, "bowl": 78},
    {"name": "Deepak Chahar", "bat": 65, "bowl": 92},
    {"name": "Maheesh Theekshana", "bat": 60, "bowl": 90},
    {"name": "Tushar Deshpande", "bat": 60, "bowl": 88},
    {"name": "Matheesha Pathirana", "bat": 60, "bowl": 90},
]

MI_PLAYERS = [
    {"name": "Rohit Sharma", "bat": 80, "bowl": 0},
    {"name": "Ishan Kishan", "bat": 71, "bowl": 0},
    {"name": "Suryakumar Yadav", "bat": 80, "bowl": 0},
    {"name": "Tilak Varma", "bat": 81, "bowl": 0},
    {"name": "Hardik Pandya", "bat": 75, "bowl": 75},
    {"name": "Tim David", "bat": 70, "bowl": 65},
    {"name": "Jasprit Bumrah", "bat": 60, "bowl": 99},
    {"name": "Gerald Coetzee", "bat": 60, "bowl": 85},
    {"name": "Piyush Chawla", "bat": 50, "bowl": 80},
    {"name": "Akash Madhwal", "bat": 60, "bowl": 81},
    {"name": "Naman Dhir", "bat": 75, "bowl": 0},
]

dropdown_data = get_dropdown_data()

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------

def get_overs_display(balls):
    return f"{balls // 6}.{balls % 6}"

def get_outcome_from_effective_score(effective_score, line, length, shot_type):
    """Use simulate_ball logic for consistent results"""
    max_runs = SHOT_MAX_RUNS.get(shot_type, 4)

    # Defense & Leave always dot
    if max_runs == 0:
        return 0

    # Very High
    if effective_score >= 98:
        if max_runs == 6:
            return 6
        else:
            return 4

    # High
    if 85 <= effective_score < 98:
        return 4

    # Medium
    if 75 <= effective_score < 85:
        return 2

    # Low Case - wicket check
    stump_lines = ["Off Stump", "Middle Stump", "Leg Stump"]
    if line in stump_lines and length in ["Yorker", "Good Length", "Full"]:
        wicket_roll = random.randint(1, 100)
        if wicket_roll > effective_score:
            return "W"

    return 0

def get_all_valid_combinations():
    """Get all valid (line, length, variation) combinations from Excel"""
    combinations = []
    for bowling_type in dropdown_data.keys():
        sheet = dropdown_data[bowling_type]
        for line in sheet["lines"]:
            for length in sheet["lengths"]:
                for variation in sheet["variations"]:
                    combinations.append((bowling_type, line, length, variation))
    return combinations

def ai_choose_ball():
    """Choose a random valid bowling combination"""
    valid_combinations = get_all_valid_combinations()
    if not valid_combinations:
        # Fallback to first combination if none found
        bowling_type = list(dropdown_data.keys())[0]
        sheet = dropdown_data[bowling_type]
        return bowling_type, sheet["lines"][0], sheet["lengths"][0], sheet["variations"][0]
    
    bowling_type, line, length, variation = random.choice(valid_combinations)
    return bowling_type, line, length, variation

def initialize_weak_shot_balls():
    """Initialize which balls should pick weak shots"""
    total_balls = session["overs"] * 6
    mode = session["mode"]
    
    if mode == "easy":
        weak_percentage = 0.15  # 15%
    elif mode == "medium":
        weak_percentage = 0.08  # 8%
    else:  # hard
        weak_percentage = 0.03  # 3%
    
    num_weak_balls = max(1, int(total_balls * weak_percentage))
    
    # Randomly select which ball numbers should pick weak shots
    weak_ball_numbers = random.sample(range(total_balls), num_weak_balls)
    session["weak_shot_balls"] = weak_ball_numbers

def ai_choose_shot_by_mode(batsman, bowling_type, line, length, variation, mode):
    """Choose shot based on mode and ball number"""
    
    shots = dropdown_data[bowling_type]["shots"]
    shot_scores = []

    for shot in shots:
        shot_rating = get_shot_rating(bowling_type, line, length, variation, shot)
        effective = calculate_effective_score(
            batsman["bat"],
            75,
            shot_rating
        )
        shot_scores.append((shot, effective))

    shot_scores.sort(key=lambda x: x[1])  # Sort by score (lowest to highest)

    # Check if current ball should pick a weak shot
    current_ball = session["balls"]
    weak_ball_numbers = session.get("weak_shot_balls", [])
    
    if current_ball in weak_ball_numbers:
        # Pick a weak shot (from lower 1/3)
        idx = random.randint(0, len(shot_scores)//3) if len(shot_scores)//3 > 0 else 0
        return shot_scores[idx]
    else:
        # Pick a strong shot based on mode
        if mode == "easy":
            # Pick from middle 1/3 of good shots
            start_idx = len(shot_scores) * 2 // 3
            end_idx = len(shot_scores)
            idx = random.randint(start_idx, end_idx - 1) if start_idx < end_idx else end_idx - 1
        elif mode == "medium":
            # Pick from upper 1/3 (good shots)
            start_idx = len(shot_scores) * 2 // 3
            end_idx = len(shot_scores)
            idx = random.randint(start_idx, end_idx - 1) if start_idx < end_idx else end_idx - 1
        else:  # hard
            # Pick from top best shots
            start_idx = len(shot_scores) * 2 // 3
            end_idx = len(shot_scores)
            idx = random.randint(start_idx, end_idx - 1) if start_idx < end_idx else end_idx - 1
        
        return shot_scores[idx]

def generate_commentary(batsman, bowler, result):
    if result == "W":
        return f"OUT! {batsman} dismissed by {bowler}!"
    if result == 6:
        return f"SIX by {batsman}!"
    if result == 4:
        return f"FOUR by {batsman}!"
    if result == 2:
        return f"{batsman} scores 2 runs."
    if result == 1:
        return f"Single taken by {batsman}."
    return f"{batsman} plays a dot ball."

# ----------------------------
# ROUTES
# ----------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/toss", methods=["POST"])
def toss():
    """Display toss screen with conditions"""
    session.clear()
    
    session["team"] = request.form.get("team")
    session["overs"] = int(request.form.get("overs"))
    session["mode"] = request.form.get("mode")
    
    return render_template("toss.html")


@app.route("/calculate_toss", methods=["POST"])
def calculate_toss():
    """Calculate toss result and optimal decision using game theory"""
    import random
    
    # Get toss call
    toss_call = request.form.get("toss_call")
    coin_result = random.choice(["Heads", "Tails"])
    
    # Determine toss winner
    toss_winner = "You" if toss_call == coin_result else "Opponent"
    
    # Get match conditions
    time = request.form.get("time")
    dew = request.form.get("dew")
    pitch = request.form.get("pitch")
    rain = request.form.get("rain")
    humidity = request.form.get("humidity")
    turn = request.form.get("turn")
    ground = request.form.get("ground")
    
    # Payoff matrix
    matrix = {
        "Afternoon Match": (65, 35),
        "Night Match": (30, 70),
        "High Dew": (25, 75),
        "No Dew": (60, 40),
        "Dry Pitch": (60, 40),
        "Green Pitch": (35, 65),
        "Rain Affected": (40, 60),
        "No Rain": (55, 45),
        "High Humidity": (30, 70),
        "Normal Humidity": (50, 50),
        "Slow Turning Pitch": (60, 40),
        "Fast Pitch": (45, 55),
        "Small Ground": (35, 65),
        "Large Ground": (60, 40)
    }
    
    conditions = [time, pitch, ground, dew, rain, humidity, turn]
    
    bat_total = 0
    bowl_total = 0
    
    for cond in conditions:
        if cond in matrix:
            bat, bowl = matrix[cond]
            bat_total += bat
            bowl_total += bowl
    
    # Calculate probabilities
    bat_prob = bat_total / len(conditions)
    bowl_prob = bowl_total / len(conditions)
    
    # Apply bonuses for pitch knowledge
    if "Dry" in pitch or "Slow" in turn:
        bat_prob += 5
    if "Green" in pitch or "High Dew" in dew:
        bowl_prob += 5
    
    # Toss advantage
    if toss_winner == "You":
        if bat_prob > bowl_prob:
            bat_prob += 3
        else:
            bowl_prob += 3
    
    # Normalize
    total = bat_prob + bowl_prob
    bat_percentage = round((bat_prob / total) * 100, 1)
    bowl_percentage = round((bowl_prob / total) * 100, 1)
    
    # Determine optimal decision
    optimal_decision = "BAT" if bat_prob > bowl_prob else "BOWL"
    
    # Store in session
    session["toss_winner"] = toss_winner
    session["coin_result"] = coin_result
    session["bat_percentage"] = bat_percentage
    session["bowl_percentage"] = bowl_percentage
    session["optimal_decision"] = optimal_decision
    
    return render_template("toss_result.html",
                          toss_winner=toss_winner,
                          coin_result=coin_result,
                          toss_call=toss_call,
                          bat_percentage=bat_percentage,
                          bowl_percentage=bowl_percentage,
                          optimal_decision=optimal_decision)
@app.route("/get_sheet_data/<bowling_type>")
def get_sheet_data(bowling_type):
    """Return dropdown data for a specific bowling type"""
    if bowling_type in dropdown_data:
        return jsonify(dropdown_data[bowling_type])
    return jsonify({"error": "Bowling type not found"}), 404

@app.route("/start", methods=["POST"])
def start():
    team = session.get("team")
    decision = request.form.get("decision")
    overs = session.get("overs")
    mode = session.get("mode")

    session["decision"] = decision
    session["balls"] = 0
    session["runs"] = 0
    session["wickets"] = 0
    session["innings"] = 1
    session["target"] = None
    session["commentary"] = []
    
    # Initialize stored bowling choice variables
    session["stored_bowling_type"] = None
    session["stored_line"] = None
    session["stored_length"] = None
    session["stored_variation"] = None

    # Initialize weak shot ball numbers for this innings
    initialize_weak_shot_balls()

    # Get first bowling type for initialization
    first_bowling_type = list(dropdown_data.keys())[0]
    first_sheet = dropdown_data[first_bowling_type]

    return render_template("match.html",
                           runs=0,
                           wickets=0,
                           overs_display="0.0",
                           data=dropdown_data,
                           first_bowling_type=first_bowling_type,
                           first_sheet=first_sheet,
                           commentary=[],
                           current_batsman="Ruturaj Gaikwad",
                           current_bowler="Jasprit Bumrah")

@app.route("/play_ball", methods=["POST"])
def play_ball():

    total_balls = session["overs"] * 6

    if session["balls"] >= total_balls or session["wickets"] >= 10:
        return change_innings()

    user_is_batting = (
        (session["innings"] == 1 and session["decision"] == "bat") or
        (session["innings"] == 2 and session["decision"] == "bowl")
    )

    if session["innings"] == 1:
        batting_team = CSK_PLAYERS if session["decision"] == "bat" else MI_PLAYERS
        bowling_team = MI_PLAYERS if session["decision"] == "bat" else CSK_PLAYERS
    else:
        batting_team = MI_PLAYERS if session["decision"] == "bat" else CSK_PLAYERS
        bowling_team = CSK_PLAYERS if session["decision"] == "bat" else MI_PLAYERS

    current_batsman = batting_team[session["wickets"]]
    over_no = session["balls"] // 6
    bowling_order = sorted([p for p in bowling_team if p["bowl"] > 0],
                           key=lambda x: x["bowl"], reverse=True)
    current_bowler = bowling_order[over_no % len(bowling_order)]

    show_score = request.form.get("show_score")

    if user_is_batting:
        shot = request.form.get("shot")
        
        # USE THE STORED BOWLING CHOICE from /get_effective_scores
        bowling_type = session.get("stored_bowling_type")
        line = session.get("stored_line")
        length = session.get("stored_length")
        variation = session.get("stored_variation")
        
        # If not stored (shouldn't happen), generate new one
        if not bowling_type:
            bowling_type, line, length, variation = ai_choose_ball()
        
        shot_rating = get_shot_rating(bowling_type, line, length, variation, shot)
        effective = calculate_effective_score(
            current_batsman["bat"],
            current_bowler["bowl"],
            shot_rating
        )
    else:
        bowling_type = request.form.get("bowling_type")
        line = request.form.get("line")
        length = request.form.get("length")
        variation = request.form.get("variation")
        
        # Sync dropdowns: validate and correct if needed
        if bowling_type not in dropdown_data:
            bowling_type = list(dropdown_data.keys())[0]
        
        sheet = dropdown_data[bowling_type]
        if line not in sheet["lines"]:
            line = sheet["lines"][0]
        if length not in sheet["lengths"]:
            length = sheet["lengths"][0]
        if variation not in sheet["variations"]:
            variation = sheet["variations"][0]
        
        shot, effective = ai_choose_shot_by_mode(
            current_batsman,
            bowling_type,
            line,
            length,
            variation,
            session["mode"]
        )

    max_runs = 6
    result = get_outcome_from_effective_score(effective, line, length, shot)

    session["balls"] += 1

    if result == "W":
        session["wickets"] += 1
    else:
        session["runs"] += result

    comment = generate_commentary(
        current_batsman["name"],
        current_bowler["name"],
        result
    )
    
    # Add bot's choice to commentary
    if user_is_batting:
        comment += f" | Bot bowled: {bowling_type} ({line}, {length}, {variation})"
    else:
        comment += f" | Bot played: {shot}"

    if show_score:
        comment += f" (Effective Score: {effective})"

    session["commentary"].insert(0, comment)

    # ✅ CLEAR THE STORED BOWLING CHOICE FOR NEXT BALL
    session["stored_bowling_type"] = None
    session["stored_line"] = None
    session["stored_length"] = None
    session["stored_variation"] = None
    session.modified = True

    # Get first bowling type for next render
    first_bowling_type = list(dropdown_data.keys())[0]
    first_sheet = dropdown_data[first_bowling_type]

    return render_template("match.html",
                           runs=session["runs"],
                           wickets=session["wickets"],
                           overs_display=get_overs_display(session["balls"]),
                           data=dropdown_data,
                           first_bowling_type=first_bowling_type,
                           first_sheet=first_sheet,
                           commentary=session["commentary"],
                           current_batsman=current_batsman["name"],
                           current_bowler=current_bowler["name"])

def change_innings():

    if session["innings"] == 1:
        session["target"] = session["runs"] + 1
        session["runs"] = 0
        session["balls"] = 0
        session["wickets"] = 0
        session["innings"] = 2
        session["commentary"] = []
        
        # Initialize weak shot ball numbers for 2nd innings
        initialize_weak_shot_balls()
        
        first_bowling_type = list(dropdown_data.keys())[0]
        first_sheet = dropdown_data[first_bowling_type]
        
        return render_template("match.html",
                               runs=0,
                               wickets=0,
                               overs_display="0.0",
                               data=dropdown_data,
                               first_bowling_type=first_bowling_type,
                               first_sheet=first_sheet,
                               commentary=[],
                               current_batsman="Opponent",
                               current_bowler="CSK Bowler")
    else:
        return render_template("result.html",
                               runs=session["runs"],
                               target=session["target"])


@app.route("/get_effective_scores", methods=["POST"])
def get_effective_scores():
    data = request.json
    action = data.get("action")
    
    # Get current players
    if session["innings"] == 1:
        batting_team = CSK_PLAYERS if session["decision"] == "bat" else MI_PLAYERS
        bowling_team = MI_PLAYERS if session["decision"] == "bat" else CSK_PLAYERS
    else:
        batting_team = MI_PLAYERS if session["decision"] == "bat" else CSK_PLAYERS
        bowling_team = CSK_PLAYERS if session["decision"] == "bat" else MI_PLAYERS
    
    current_batsman = batting_team[session["wickets"]]
    over_no = session["balls"] // 6
    bowling_order = sorted([p for p in bowling_team if p["bowl"] > 0],
                           key=lambda x: x["bowl"], reverse=True)
    current_bowler = bowling_order[over_no % len(bowling_order)]
    
    if action == "batting":
        # User is batting - show bot's bowling choice and all shot scores
        # User is batting - show bot's bowling choice and all shot scores
        # REUSE existing choice for this ball if already stored
        bowling_type = session.get("stored_bowling_type")
        line = session.get("stored_line")
        length = session.get("stored_length")
        variation = session.get("stored_variation")

        if not bowling_type:
            bowling_type, line, length, variation = ai_choose_ball()
        
        # STORE the choice in session so it's reused when play_ball is called
            session["stored_bowling_type"] = bowling_type
            session["stored_line"] = line
            session["stored_length"] = length
            session["stored_variation"] = variation
            session.modified = True  # FORCE save the session
        
        # Get all shot ratings for this bowling combination
        all_shots = dropdown_data[bowling_type]["shots"]
        shot_scores = []
        
        for shot in all_shots:
            shot_rating = get_shot_rating(bowling_type, line, length, variation, shot)
            effective = calculate_effective_score(
                current_batsman["bat"],
                current_bowler["bowl"],
                shot_rating
            )
            shot_scores.append({
                "name": shot,
                "score": effective,
                "type": "shot"
            })
        
        # Sort by score
        shot_scores.sort(key=lambda x: x["score"], reverse=True)
        
        return jsonify({
            "bot_choice": {
                "type": "bowling",
                "bowling_type": bowling_type,
                "line": line,
                "length": length,
                "variation": variation
            },
            "all_scores": shot_scores
        })
    
    else:  # action == "bowling"
        # User is bowling - show bot's shot choice and expected runs for all shots
        bowling_type = data.get("bowling_type")
        line = data.get("line")
        length = data.get("length")
        variation = data.get("variation")
        
        all_shots = dropdown_data[bowling_type]["shots"]
        shot_scores = []
        
        for shot in all_shots:
            shot_rating = get_shot_rating(bowling_type, line, length, variation, shot)
            effective = calculate_effective_score(
                current_batsman["bat"],
                current_bowler["bowl"],
                shot_rating
            )
            max_runs = SHOT_MAX_RUNS.get(shot, 4)
            expected_runs = get_outcome_from_effective_score(effective, line, length, shot)
            
            shot_scores.append({
                "name": shot,
                "score": effective,
                "expected_runs": expected_runs,
                "type": "bowling"
            })
        
        # Sort by score
        shot_scores.sort(key=lambda x: x["score"], reverse=True)
        
        # Get bot's choice
        bot_shot, bot_effective = ai_choose_shot_by_mode(
            current_batsman,
            bowling_type,
            line,
            length,
            variation,
            session["mode"]
        )
        
        return jsonify({
            "bot_choice": {
                "type": "shot",
                "shot": bot_shot,
                "effective_score": bot_effective
            },
            "all_scores": shot_scores
        })
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)