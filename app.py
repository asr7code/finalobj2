import streamlit as st
import streamlit.components.v1 as components
import random
import time
import math

##################################
# PAGE SETUP
##################################
st.set_page_config(page_title="Traffic Optimizer – Objective 2", layout="wide")
st.title("🚦 Traffic Optimizer & Assistant - Objective 2 Simulation")
st.markdown("""
This simulation models a smart assistant that guides a vehicle through unsynchronized traffic lights. It estimates the time remaining at the next signal, predicts the phase the car will encounter, and suggests a speed adjustment. Voice alerts are triggered only when the predicted signal phase changes.
""")

##################################
# SIDEBAR CONTROLS
##################################
st.sidebar.header("Simulation Controls")
init_speed = st.sidebar.slider("Initial Speed (km/h)", 10, 60, 25)
max_speed = st.sidebar.slider("Maximum Speed (km/h)", 10, 60, 60)
min_speed = st.sidebar.slider("Minimum Speed (km/h)", 10, 60, 10)
start_sim = st.sidebar.button("▶ Start Simulation")

##################################
# TRAFFIC LIGHT SETUP
##################################
# Positions (in pixels along a horizontal road)
signal_positions = [150, 350, 550, 750, 950]
signal_labels = ['B', 'C', 'D', 'E', 'F']
# Dictionary to hold each signal's state
traffic_lights = {}

def initialize_signals():
    for label, pos in zip(signal_labels, signal_positions):
        # Random initial phase: 'red', 'green', or 'yellow'
        phase = random.choice(['red', 'green', 'yellow'])
        # For yellow, timer is fixed at 5 sec; for red/green, choose randomly between 30 and 60 sec.
        timer = 5 if phase == 'yellow' else random.randint(30, 60)
        traffic_lights[label] = {"x": pos, "phase": phase, "timer": timer}

initialize_signals()

##################################
# CAR STATE VARIABLES
##################################
car_pos = 0.0  # car's x-position (in pixels)
car_speed = float(init_speed)  # current speed (km/h)
waiting = False                # whether the car is halted at a red light
waiting_signal = None          # label of the signal where the car is waiting

# Proportional controller gain for smooth speed adjustments
Kp = 0.2

##################################
# SESSION STATE VARIABLES (for voice alert debouncing)
##################################
if "prev_prediction" not in st.session_state:
    st.session_state.prev_prediction = None
if "last_voice_time" not in st.session_state:
    st.session_state.last_voice_time = 0.0

##################################
# PLACEHOLDERS FOR UI UPDATE
##################################
info_box = st.empty()
road_box = st.empty()
signal_box = st.empty()

##################################
# HELPER FUNCTIONS
##################################
def update_signals():
    """Update timer and cycle phases for each traffic light."""
    for light in traffic_lights.values():
        light["timer"] -= 1
        if light["timer"] <= 0:
            if light["phase"] == "red":
                light["phase"] = "green"
                light["timer"] = 45  # fixed green time
            elif light["phase"] == "green":
                light["phase"] = "yellow"
                light["timer"] = 5   # fixed yellow time
            elif light["phase"] == "yellow":
                light["phase"] = "red"
                light["timer"] = random.randint(30, 60)

def predict_phase(signal, eta):
    """
    Predict the phase the car will encounter upon arrival at the signal.
    We simulate one full cycle starting from the current phase.
    
    Cycle definitions:
    - If current is red: cycle = [("red", timer), ("green", 45), ("yellow", 5)]
    - If current is green: cycle = [("green", timer), ("yellow", 5), ("red", 40)]
    - If current is yellow: cycle = [("yellow", timer), ("red", 40), ("green", 45)]
    """
    if signal["phase"] == "red":
        cycle = [("red", signal["timer"]), ("green", 45), ("yellow", 5)]
    elif signal["phase"] == "green":
        cycle = [("green", signal["timer"]), ("yellow", 5), ("red", 40)]
    elif signal["phase"] == "yellow":
        cycle = [("yellow", signal["timer"]), ("red", 40), ("green", 45)]
    else:
        return "Unknown"
    t_remaining = eta  # seconds until arrival
    for phase_name, duration in cycle:
        if t_remaining <= duration:
            return phase_name
        t_remaining -= duration
    return cycle[-1][0]

def adjust_speed(current_speed, eta, remaining_time):
    """
    Adjust car speed using a proportional (P-controller) approach.
    Error = (remaining green time - ETA) if signal is green.
    A positive error means the car will take too long, so it should speed up.
    Conversely, a negative error means the car is too fast relative to remaining time.
    """
    error = remaining_time - eta  # error in seconds
    delta = Kp * error * 10       # scale adjustment factor as needed
    new_speed = current_speed + delta
    new_speed = max(min_speed, min(max_speed, new_speed))
    return new_speed

##################################
# SIMULATION LOOP (Objective 2)
##################################
if start_sim:
    while car_pos <= 1100:
        update_signals()
        # Determine upcoming signal: first signal with x-position > car_pos
        next_signal = None
        for label in signal_labels:
            if traffic_lights[label]["x"] > car_pos:
                next_signal = label
                break

        # Set defaults
        suggestion = "Maintain"
        eta = float('inf')
        distance = 0
        predicted = "-"
        current_phase = "-"

        if next_signal:
            sig = traffic_lights[next_signal]
            distance = sig["x"] - car_pos
            current_phase = sig["phase"]
            # ETA calculation (using car_speed * 0.1 as pixel per sec conversion)
            eta = distance / (car_speed * 0.1) if car_speed > 0 else float('inf')
            predicted = predict_phase(sig, eta)
            # Speed suggestion logic:
            if current_phase == "red" and distance <= 40:
                suggestion = "Slow Down"
                car_speed = 0
                waiting = True
                waiting_signal = next_signal
            elif current_phase == "green":
                # Use proportional control to adjust speed: error = remaining green time - ETA
                suggestion = "Speed Up" if eta < sig["timer"] else "Slow Down"
                car_speed = adjust_speed(car_speed, eta, sig["timer"])
            elif current_phase == "yellow":
                # For yellow, advise slowing since it's less safe
                suggestion = "Slow Down"
                car_speed = adjust_speed(car_speed, eta, 2)  # treat yellow as 2 sec available

        # Resume movement if waiting and the waiting signal is now green
        if waiting and waiting_signal:
            if traffic_lights[waiting_signal]["phase"] == "green":
                waiting = False
                car_speed = 15  # resume with a moderate speed

        # Debounce: trigger voice alert only if predicted phase changes and >=5 sec elapsed since last alert
        now = time.time()
        if (st.session_state.prev_prediction != predicted) and ((now - st.session_state.last_voice_time) > 5):
            voice_text = ""
            if suggestion == "Speed Up":
                voice_text = "The signal is green. You can speed up."
            elif suggestion == "Slow Down":
                voice_text = "Approach with caution. Please slow down."
            elif suggestion == "Maintain":
                voice_text = "Maintain your current speed."
            components.html(
                f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{voice_text}");
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(msg);
                </script>
                """,
                height=0
            )
            st.session_state.prev_prediction = predicted
            st.session_state.last_voice_time = now

        # Move the car forward if not waiting
        if car_speed > 0:
            car_pos += car_speed * 0.1

        # Display simulation info
        eta_str = "N/A" if math.isinf(eta) else f"{int(eta)}s"
        info_box.markdown(
            f"""
            ### 🚘 Vehicle Info  
            - **Speed:** {int(car_speed)} km/h  
            - **Next Signal:** {next_signal if next_signal else "None"}  
            - **Distance to Signal:** {int(distance)} px  
            - **Current Signal Phase:** {current_phase}  
            - **ETA to Signal:** {eta_str}  
            - **Predicted Phase on Arrival:** {predicted}  
            - **Suggestion:** {suggestion}
            """
        )

        # ROAD VISUALIZATION: Build a road string of 120 characters
        road = ["—"] * 120
        for label in signal_labels:
            pos_index = int(traffic_lights[label]["x"] / 10)
            phase = traffic_lights[label]["phase"]
            # Use emoji markers for phases:
            if phase == "red":
                road[pos_index] = "🟥"
            elif phase == "green":
                road[pos_index] = "🟩"
            elif phase == "yellow":
                road[pos_index] = "🟨"
        car_index = int(car_pos / 10)
        if 0 <= car_index < len(road):
            road[car_index] = "🔵"
        road_box.markdown("#### 🛣️ Road View")
        road_box.code("".join(road))

        # SIGNAL METRICS: Display each signal's phase and timer
        cols = st.columns(len(signal_labels))
        for i, label in enumerate(signal_labels):
            with cols[i]:
                st.metric(label=f"Signal {label}", value=traffic_lights[label]["phase"].capitalize(), delta=f"{traffic_lights[label]['timer']}s")

        time.sleep(1)
