import streamlit as st
import streamlit.components.v1 as components
import random
import time
import math

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Traffic Optimizer – Objective 2", layout="wide")
st.title("🚦 Traffic Optimizer & Assistant - Objective 2 Simulation")
st.markdown("""
This assistant predicts upcoming traffic signal phases, estimates ETA, and gives smart speed suggestions to help a car reduce waiting time at red lights and optimize smooth passage through intersections.
""")

# -------------------- SIDEBAR --------------------
st.sidebar.header("Simulation Controls")
init_speed = st.sidebar.slider("Initial Speed (km/h)", 10, 60, 25)
max_speed = st.sidebar.slider("Maximum Speed (km/h)", 10, 60, 60)
min_speed = st.sidebar.slider("Minimum Speed (km/h)", 10, 60, 10)
start_sim = st.sidebar.button("▶ Start Simulation")

# -------------------- TRAFFIC LIGHT SETUP --------------------
signal_positions = [150, 350, 550, 750, 950]
signal_labels = ['B', 'C', 'D', 'E', 'F']
traffic_lights = {}

def initialize_signals():
    for label, pos in zip(signal_labels, signal_positions):
        phase = random.choice(['red', 'green', 'yellow'])
        timer = 5 if phase == 'yellow' else random.randint(30, 60)
        traffic_lights[label] = {"x": pos, "phase": phase, "timer": timer}

initialize_signals()

# -------------------- CAR STATE --------------------
car_pos = 0.0
car_speed = float(init_speed)
waiting = False
waiting_signal = None

# -------------------- SESSION STATE --------------------
if "prev_prediction" not in st.session_state:
    st.session_state.prev_prediction = None
if "last_voice_time" not in st.session_state:
    st.session_state.last_voice_time = 0.0

# -------------------- PLACEHOLDERS --------------------
info_box = st.empty()
road_box = st.empty()

# -------------------- FUNCTIONS --------------------
def update_signals():
    for light in traffic_lights.values():
        light["timer"] -= 1
        if light["timer"] <= 0:
            if light["phase"] == "red":
                light["phase"] = "green"
                light["timer"] = 45
            elif light["phase"] == "green":
                light["phase"] = "yellow"
                light["timer"] = 5
            elif light["phase"] == "yellow":
                light["phase"] = "red"
                light["timer"] = random.randint(30, 60)

def predict_phase(signal, eta):
    if signal["phase"] == "red":
        cycle = [("red", signal["timer"]), ("green", 45), ("yellow", 5)]
    elif signal["phase"] == "green":
        cycle = [("green", signal["timer"]), ("yellow", 5), ("red", 40)]
    elif signal["phase"] == "yellow":
        cycle = [("yellow", signal["timer"]), ("red", 40), ("green", 45)]
    else:
        return "Unknown"
    t = eta
    for phase_name, duration in cycle:
        if t <= duration:
            return phase_name
        t -= duration
    return cycle[-1][0]

# -------------------- SIMULATION LOOP --------------------
if start_sim:
    while car_pos <= 1100:
        update_signals()

        # Get next upcoming signal
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
            predicted = predict_phase(sig, eta)

            # SMART SPEED LOGIC
            if predicted == "red":
                suggestion = "Slow Down"
                if car_speed > min_speed:
                    car_speed -= 2
                    car_speed = max(min_speed, car_speed)
            elif predicted == "green":
                if eta < sig["timer"]:
                    suggestion = "Speed Up"
                    if car_speed < max_speed:
                        car_speed += 2
                        car_speed = min(max_speed, car_speed)
                else:
                    suggestion = "Maintain"
            elif predicted == "yellow":
                suggestion = "Slow Down"
                if car_speed > min_speed:
                    car_speed -= 2
                    car_speed = max(min_speed, car_speed)

            # RED LIGHT STOP LOGIC
            if current_phase == "red" and distance <= 40:
                suggestion = "Stop"
                car_speed = 0
                waiting = True
                waiting_signal = next_signal

        # Resume from red when light turns green
        if waiting and waiting_signal:
            if traffic_lights[waiting_signal]["phase"] == "green":
                waiting = False
                car_speed = 15

        # Debounced Voice Alerts
        now = time.time()
        if (st.session_state.prev_prediction != predicted) and (now - st.session_state.last_voice_time > 5):
            voice_text = ""
            if suggestion == "Speed Up":
                voice_text = "Green signal ahead. Speed up."
            elif suggestion == "Slow Down":
                voice_text = "Red signal ahead. Please slow down."
            elif suggestion == "Stop":
                voice_text = "Stopping at red signal."
            elif suggestion == "Maintain":
                voice_text = "Maintain current speed."
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

        # Move car
        if car_speed > 0:
            car_pos += car_speed * 0.1

        # Info Panel
        eta_str = "N/A" if math.isinf(eta) else f"{int(eta)}s"
        info_box.markdown(
            f"""
            ### 🚘 Vehicle Info  
            - **Speed:** {int(car_speed)} km/h  
            - **Next Signal:** {next_signal or "None"}  
            - **Distance to Signal:** {int(distance)} px  
            - **Current Signal Phase:** {current_phase}  
            - **ETA to Signal:** {eta_str}  
            - **Predicted Phase on Arrival:** {predicted}  
            - **Suggestion:** **{suggestion}**
            """
        )

        # Road Visualization
        road = ["—"] * 120
        for label in signal_labels:
            idx = int(traffic_lights[label]["x"] / 10)
            phase = traffic_lights[label]["phase"]
            road[idx] = {"red": "🟥", "green": "🟩", "yellow": "🟨"}[phase]
        car_idx = int(car_pos / 10)
        if 0 <= car_idx < len(road):
            road[car_idx] = "🔵"
        road_box.markdown("### 🛣️ Road View")
        road_box.code("".join(road))

        # Traffic Light Timers
        cols = st.columns(len(signal_labels))
        for i, label in enumerate(signal_labels):
            sig = traffic_lights[label]
            with cols[i]:
                st.metric(f"Signal {label}", value=sig["phase"].capitalize(), delta=f"{sig['timer']}s")

        time.sleep(1)
