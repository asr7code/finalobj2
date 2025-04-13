import streamlit as st
import streamlit.components.v1 as components
import random
import time
import math

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Traffic Optimizer – Objective 2", layout="wide")
st.title("🚦 Traffic Optimizer & Assistant - Objective 2 Simulation")
st.markdown("""
This assistant uses accurate signal prediction and vehicle ETA to suggest appropriate driving behavior.
The goal is to **reduce red light waiting time** and help drivers **cross at green signals** when realistically possible.
""")

# -------------------- SIDEBAR --------------------
st.sidebar.header("Simulation Controls")
init_speed = st.sidebar.slider("Initial Speed (km/h)", 10, 60, 25)
max_speed = st.sidebar.slider("Maximum Speed (km/h)", 10, 60, 60)
min_speed = st.sidebar.slider("Minimum Speed (km/h)", 10, 60, 10)
driver_type = st.sidebar.selectbox("Driver Behavior", ["Cautious", "Average", "Aggressive"])
start_sim = st.sidebar.button("▶ Start Simulation")

# -------------------- DRIVER BEHAVIOR --------------------
driver_profiles = {
    "Cautious": 0.9,
    "Average": 0.7,
    "Aggressive": 0.4
}
driver_prob = driver_profiles[driver_type]

# -------------------- TRAFFIC LIGHTS --------------------
signal_positions = [150, 350, 550, 750, 950]
signal_labels = ['B', 'C', 'D', 'E', 'F']
traffic_lights = {}
phase_cycle = [("red", 40), ("green", 45), ("yellow", 5)]

# INIT
for label, pos in zip(signal_labels, signal_positions):
    phase = random.choice(['red', 'green', 'yellow'])
    timer = 5 if phase == 'yellow' else random.randint(30, 60)
    traffic_lights[label] = {
        "x": pos,
        "phase": phase,
        "timer": timer,
        "start_time": time.time()
    }

# -------------------- SESSION STATE --------------------
car_pos = 0.0
car_speed = float(init_speed)
waiting = False
waiting_signal = None

if "prev_prediction" not in st.session_state:
    st.session_state.prev_prediction = None
if "last_voice_time" not in st.session_state:
    st.session_state.last_voice_time = 0.0

info_box = st.empty()
road_box = st.empty()

# -------------------- FUNCTIONS --------------------
def update_signals():
    for sig in traffic_lights.values():
        if time.time() - sig["start_time"] >= sig["timer"]:
            i = next(i for i, (ph, _) in enumerate(phase_cycle) if ph == sig["phase"])
            next_i = (i + 1) % len(phase_cycle)
            next_phase, duration = phase_cycle[next_i]
            sig["phase"] = next_phase
            sig["timer"] = duration
            sig["start_time"] = time.time()

def predict_phase_at_arrival(signal, eta):
    elapsed = time.time() - signal["start_time"]
    offset = elapsed + eta
    total_cycle = sum(d for _, d in phase_cycle)
    t = offset % total_cycle
    accum = 0
    for phase, duration in phase_cycle:
        accum += duration
        if t < accum:
            return phase
    return phase_cycle[-1][0]

def calculate_required_speed(distance, time_left):
    return (distance / time_left) * 10 if time_left > 0 else float('inf')

# -------------------- SIMULATION LOOP --------------------
if start_sim:
    while car_pos <= 1100:
        update_signals()
        driver_follows = random.random() < driver_prob

        next_signal = None
        for label in signal_labels:
            if traffic_lights[label]["x"] > car_pos:
                next_signal = label
                break

        suggestion = "Maintain"
        eta = float('inf')
        distance = 0
        predicted = "-"
        current_phase = "-"

        if next_signal:
            sig = traffic_lights[next_signal]
            distance = sig["x"] - car_pos
            current_phase = sig["phase"]
            eta = distance / (car_speed * 0.1) if car_speed > 0 else float('inf')
            predicted = predict_phase_at_arrival(sig, eta)

            if predicted == "green":
                green_left = sig["timer"] - (time.time() - sig["start_time"])
                req_speed = calculate_required_speed(distance, green_left)
                if eta <= green_left and req_speed <= max_speed:
                    suggestion = "Speed Up"
                    if driver_follows and car_speed < max_speed:
                        car_speed += 2
                else:
                    suggestion = "Maintain"

            elif predicted == "red":
                red_left = sig["timer"] - (time.time() - sig["start_time"])
                time_after_red = eta - red_left
                if 0 < time_after_red <= 45:
                    req_speed = calculate_required_speed(distance, time_after_red)
                    if req_speed <= max_speed:
                        suggestion = "Speed Up"
                        if driver_follows and car_speed < max_speed:
                            car_speed += 2
                    else:
                        suggestion = "Maintain"
                else:
                    suggestion = "Slow Down"
                    if driver_follows and car_speed > min_speed:
                        car_speed -= 2

            elif predicted == "yellow":
                suggestion = "Slow Down"
                if driver_follows and car_speed > min_speed:
                    car_speed -= 2

            if current_phase == "red" and distance <= 40:
                suggestion = "Stop"
                car_speed = 0
                waiting = True
                waiting_signal = next_signal

        if waiting and waiting_signal:
            if traffic_lights[waiting_signal]["phase"] == "green":
                waiting = False
                car_speed = 15

        now = time.time()
        if (st.session_state.prev_prediction != predicted) and (now - st.session_state.last_voice_time > 5):
            voice_text = {
                "Speed Up": "Green signal ahead. Speed up.",
                "Slow Down": "Red signal ahead. Please slow down.",
                "Stop": "Stopping at red signal.",
                "Maintain": "Maintain your speed."
            }.get(suggestion, "")
            if voice_text:
                components.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{voice_text}");
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(msg);
                </script>
                """, height=0)
                st.session_state.prev_prediction = predicted
                st.session_state.last_voice_time = now

        if car_speed > 0:
            car_pos += car_speed * 0.1

        eta_str = "Waiting" if math.isinf(eta) else f"{int(eta)}s"
        info_box.markdown(f"""
        ### 🚘 Vehicle Info
        - **Speed:** {int(car_speed)} km/h
        - **Next Signal:** {next_signal or "None"}
        - **Distance to Signal:** {int(distance)} px
        - **Current Signal Phase:** {current_phase}
        - **ETA to Signal:** {eta_str}
        - **Predicted Phase on Arrival:** {predicted}
        - **Suggestion:** **{suggestion}**
        """)

        road = ["—"] * 120
        for label in signal_labels:
            idx = int(traffic_lights[label]["x"] / 10)
            phase = traffic_lights[label]["phase"]
            road[idx] = {"red": "🔳", "green": "🟢", "yellow": "🔶"}[phase]
        car_idx = int(car_pos / 10)
        if 0 <= car_idx < len(road):
            road[car_idx] = "🔵"
        road_box.markdown("### 🚳️ Road View")
        road_box.code("".join(road))

        time.sleep(1)
