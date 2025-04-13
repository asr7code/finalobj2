import streamlit as st
import streamlit.components.v1 as components
import random
import time
import math

# ------------- Streamlit Setup -------------
st.set_page_config(page_title="Traffic Optimizer – Objective 2", layout="wide")
st.title("🚦 Traffic Optimizer & Assistant – Objective 2")
st.markdown("""
Simulates a smart assistant that guides a car through unsynchronized traffic lights by:
- Predicting upcoming traffic signal phase
- Estimating ETA
- Giving speed suggestions (slow down / speed up)
- Providing voice alerts
""")

# ------------- Sidebar Controls -------------
st.sidebar.header("Simulation Controls")
initial_speed = st.sidebar.slider("Initial Speed (km/h)", 10, 60, 25)
max_speed = st.sidebar.slider("Max Speed", 10, 60, 60)
min_speed = st.sidebar.slider("Min Speed", 10, 60, 10)
run_button = st.sidebar.button("▶ Start Simulation")

# ------------- Traffic Signal Setup -------------
signal_positions = [150, 350, 550, 750, 950]
signal_labels = ['B', 'C', 'D', 'E', 'F']
signal_states = {}

def init_signals():
    for label, x in zip(signal_labels, signal_positions):
        phase = random.choice(['red', 'green', 'yellow'])
        timer = random.randint(10, 45) if phase != 'yellow' else 5
        signal_states[label] = {'x': x, 'phase': phase, 'timer': timer}

init_signals()

# ------------- Initial Variables -------------
car_x = 0
car_speed = initial_speed
waiting_at = None
Kp = 0.1  # Proportional control gain

# ------------- Session State -------------
if "prev_predicted_phase" not in st.session_state:
    st.session_state.prev_predicted_phase = None
if "current_advice" not in st.session_state:
    st.session_state.current_advice = "Maintain"
    st.session_state.advice_counter = 0
if "last_voice_time" not in st.session_state:
    st.session_state.last_voice_time = 0.0

# ------------- Placeholders -------------
info_box = st.empty()
road_box = st.empty()

# ------------- Run Simulation -------------
if run_button:
    while car_x <= 1100:
        # --- Update traffic light timers ---
        for sig in signal_states.values():
            sig['timer'] -= 1
            if sig['timer'] <= 0:
                if sig['phase'] == 'red':
                    sig['phase'] = 'green'
                    sig['timer'] = 45
                elif sig['phase'] == 'green':
                    sig['phase'] = 'yellow'
                    sig['timer'] = 5
                elif sig['phase'] == 'yellow':
                    sig['phase'] = 'red'
                    sig['timer'] = random.randint(30, 60)

        # --- Determine upcoming signal ---
        next_signal = None
        for lbl in signal_labels:
            if signal_states[lbl]['x'] > car_x:
                next_signal = lbl
                break

        suggestion = "Maintain"
        eta = float('inf')
        distance = 0
        predicted_phase = "-"
        current_phase = "-"

        if next_signal:
            signal = signal_states[next_signal]
            distance = signal['x'] - car_x
            current_phase = signal['phase']
            if car_speed > 0:
                eta = distance / (car_speed * 0.1)
            else:
                eta = float('inf')

            # --- Predict phase on arrival ---
            rem = eta
            time_left = signal['timer']
            if rem <= time_left:
                predicted_phase = current_phase
            else:
                rem -= time_left
                if current_phase == 'red':
                    predicted_phase = "green" if rem <= 45 else "red"
                elif current_phase == 'green':
                    predicted_phase = "yellow" if rem <= 5 else "red" if rem <= 45 else "green"
                elif current_phase == 'yellow':
                    predicted_phase = "red" if rem <= 40 else "green"

            # --- Speed advice ---
            if current_phase == 'red' and distance <= 40:
                suggestion = "Slow Down"
                car_speed = 0
                waiting_at = next_signal
            elif current_phase == 'green':
                time_to_reach = eta
                error = time_left - time_to_reach
                delta_speed = Kp * error * 10
                new_speed = car_speed - delta_speed
                new_speed = max(min_speed, min(max_speed, new_speed))
                suggestion = "Speed Up" if new_speed > car_speed else "Slow Down"
                car_speed = new_speed

        # --- Resume after red ---
        if waiting_at and signal_states[waiting_at]['phase'] == 'green':
            waiting_at = None
            car_speed = 15

        # --- Advice stability check ---
        if suggestion == st.session_state.current_advice:
            st.session_state.advice_counter += 1
        else:
            st.session_state.current_advice = suggestion
            st.session_state.advice_counter = 1

        stable_advice = st.session_state.current_advice if st.session_state.advice_counter >= 2 else "Maintain"

        # --- Move car ---
        if car_speed > 0:
            car_x += car_speed * 0.1

        # --- Display Info ---
        eta_str = "N/A" if math.isinf(eta) else f"{int(eta)}s"
        info_box.markdown(
            f"""
            ### 🚘 Vehicle Info  
            - **Speed:** {int(car_speed)} km/h  
            - **Next Signal:** `{next_signal}`  
            - **Distance to Signal:** `{int(distance)} px`  
            - **Current Phase:** `{current_phase}`  
            - **ETA:** `{eta_str}`  
            - **Predicted Phase:** `{predicted_phase}`  
            - **Advice:** 🚘 `{stable_advice}`
            """
        )

        # --- Voice Alert (debounced) ---
        now = time.time()
        if (st.session_state.prev_predicted_phase != predicted_phase) and (now - st.session_state.last_voice_time > 5):
            voice = ""
            if stable_advice == "Speed Up":
                voice = "Signal is green. You can speed up."
            elif stable_advice == "Slow Down":
                voice = "Red signal ahead. Please slow down."
            elif stable_advice == "Maintain":
                voice = "Maintain your current speed."
            components.html(
                f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{voice}");
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(msg);
                </script>
                """,
                height=0
            )
            st.session_state.prev_predicted_phase = predicted_phase
            st.session_state.last_voice_time = now

        # --- Road Visualization ---
        road_display = ["—"] * 120
        for lbl in signal_labels:
            pos = int(signal_states[lbl]["x"] / 10)
            phase = signal_states[lbl]["phase"]
            if phase == "red":
                road_display[pos] = "🟥"
            elif phase == "green":
                road_display[pos] = "🟩"
            elif phase == "yellow":
                road_display[pos] = "🟨"
        car_index = int(car_x / 10)
        if 0 <= car_index < len(road_display):
            road_display[car_index] = "🔵"

        road_box.markdown("### 🛣️ Road View")
        road_box.code("".join(road_display))

        # --- Signal Timers Display ---
        cols = st.columns(len(signal_labels))
        for i, lbl in enumerate(signal_labels):
            sig = signal_states[lbl]
            with cols[i]:
                st.metric(label=f"Signal {lbl}", value=sig['phase'].capitalize(), delta=f"{sig['timer']}s")

        time.sleep(1)
