import streamlit as st
import streamlit.components.v1 as components
import random
import time
import math
from PIL import Image
import io

##########################
# PAGE CONFIGURATION
##########################
st.set_page_config(page_title="Traffic Optimizer & Assistant", layout="wide")
st.title("Traffic Optimizer & Assistant")
st.markdown("""
This project includes two modules:
- **Objective 1:** Traffic Sign Recognition with voice alerts.
- **Objective 2:** Traffic Light Simulation with speed suggestions and dynamic voice alerts.
""")

# ---------------------------
# Sidebar: Module Selection
# ---------------------------
page = st.sidebar.radio("Select Module", ["Traffic Light Simulation", "Traffic Sign Recognition"])

##########################
# OBJECTIVE 2: TRAFFIC LIGHT SIMULATION
##########################
if page == "Traffic Light Simulation":
    st.header("🚦 Traffic Light Simulation & Speed Suggestions")
    st.markdown("This simulation predicts upcoming traffic light phases, suggests optimal speed, and provides voice alerts accordingly.")

    # Sidebar controls for simulation parameters (for module 2)
    initial_speed = st.sidebar.slider("Initial Speed (km/h)", 10, 60, 25, key="sim_initial")
    max_speed = st.sidebar.slider("Max Speed (km/h)", 10, 60, 60, key="sim_max")
    min_speed = st.sidebar.slider("Min Speed (km/h)", 10, 60, 10, key="sim_min")
    run_sim = st.sidebar.button("▶ Start Simulation (Objective 2)")

    # -----------------------
    # INITIAL SIMULATION STATE (Objective 2)
    # -----------------------
    # Define signal positions (pixels along a simulated road)
    signal_positions = [150, 350, 550, 750, 950]
    signal_labels = ['B', 'C', 'D', 'E', 'F']
    signal_states = {}

    def init_traffic_lights():
        for label, x in zip(signal_labels, signal_positions):
            phase = random.choice(['red', 'green', 'yellow'])
            timer = random.randint(10, 45) if phase != 'yellow' else 5
            signal_states[label] = {'x': x, 'phase': phase, 'timer': timer}
    init_traffic_lights()

    car_x = 0
    car_speed = initial_speed
    waiting_at = None

    # Use session state to smooth advice and store previous predicted phase for voice alert
    if "prev_predicted_phase" not in st.session_state:
        st.session_state.prev_predicted_phase = None
    if "current_advice" not in st.session_state:
        st.session_state.current_advice = "Maintain"
        st.session_state.advice_counter = 0

    # Create placeholders for updating the interface
    info_box = st.empty()
    road_box = st.empty()

    # Run simulation loop when button is pressed
    if run_sim:
        while car_x <= 1100:
            # --- Update signal timers ---
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

            # --- Find next signal ---
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

                # --- Predict phase ---
                rem = eta
                phase = current_phase
                time_left = signal['timer']
                if rem <= time_left:
                    predicted_phase = phase
                elif phase == "red":
                    rem -= time_left
                    if rem <= 45:
                        predicted_phase = "green"
                    elif rem <= 50:
                        predicted_phase = "yellow"
                    else:
                        predicted_phase = "red"
                elif phase == "green":
                    rem -= time_left
                    if rem <= 5:
                        predicted_phase = "yellow"
                    elif rem <= 5 + 40:
                        predicted_phase = "red"
                    else:
                        predicted_phase = "green"
                elif phase == "yellow":
                    rem -= time_left
                    if rem <= 40:
                        predicted_phase = "red"
                    elif rem <= 40 + 45:
                        predicted_phase = "green"
                    else:
                        predicted_phase = "yellow"

                # --- Suggest speed based on current phase ---
                if current_phase == 'red' and distance <= 40:
                    suggestion = 'Slow Down'
                    car_speed = 0
                    waiting_at = next_signal
                elif current_phase == 'green':
                    if car_speed < max_speed:
                        suggestion = 'Speed Up'
                        if random.random() < 0.7:
                            car_speed += 5
                            car_speed = min(car_speed, max_speed)
                    elif car_speed > min_speed:
                        suggestion = 'Slow Down'
                        if random.random() < 0.7:
                            car_speed -= 5
                            car_speed = max(car_speed, min_speed)

            # --- Resume after red ---
            if waiting_at and signal_states[waiting_at]['phase'] == 'green':
                waiting_at = None
                car_speed = 15

            # --- Update advice smoothing ---
            if suggestion == st.session_state.current_advice:
                st.session_state.advice_counter += 1
            else:
                st.session_state.current_advice = suggestion
                st.session_state.advice_counter = 1

            stable_suggestion = st.session_state.current_advice if st.session_state.advice_counter >= 2 else "Maintain"

            # --- Move car forward if not waiting ---
            if car_speed > 0:
                car_x += car_speed * 0.1

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
                - **Advice (Stable):** 🚘 `{stable_suggestion}`
                """
            )

            # --- Voice Alert: Trigger only if the predicted phase has changed ---
            if st.session_state.prev_predicted_phase != predicted_phase:
                voice = ""
                if stable_suggestion == "Speed Up":
                    voice = "Signal is green. You can speed up."
                elif stable_suggestion == "Slow Down":
                    voice = "Red signal ahead. Please slow down."
                elif stable_suggestion == "Maintain":
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

            # --- ROAD VISUALIZATION ---
            road_display = ["-"] * 120
            for lbl in signal_labels:
                pos = int(signal_states[lbl]["x"] / 10)
                phase = signal_states[lbl]["phase"]
                if phase == "red":
                    road_display[pos] = "🟥"
                elif phase == "green":
                    road_display[pos] = "🟩"
                elif phase == "yellow":
                    road_display[pos] = "🟨"
            car_pos_index = int(car_x / 10)
            if 0 <= car_pos_index < len(road_display):
                road_display[car_pos_index] = "🔵"
            st.markdown("### 🛣️ Road View")
            st.code("".join(road_display))
            
            # --- Display signal metrics ---
            cols = st.columns(len(signal_labels))
            for i, lbl in enumerate(signal_labels):
                sig = signal_states[lbl]
                with cols[i]:
                    st.metric(label=f"Signal {lbl}", value=sig['phase'].capitalize(), delta=f"{sig['timer']}s")

            time.sleep(1)

##########################
# OBJECTIVE 1: TRAFFIC SIGN RECOGNITION
##########################
elif page == "Traffic Sign Recognition":
    st.header("🚥 Traffic Sign Recognition")
    st.markdown("Upload an image of a traffic sign to get a prediction.")

    # File uploader for image input
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)

        # Dummy prediction function (replace with your actual model inference)
        def dummy_predict(img):
            # Simulate some delay and random output
            time.sleep(1)
            predicted_class = random.choice(["Stop", "Speed Limit 50", "Yield", "No Entry", "Roundabout"])
            confidence = random.uniform(90, 99)
            return predicted_class, round(confidence, 2)

        if st.button("Predict Traffic Sign"):
            with st.spinner("Predicting..."):
                label, conf = dummy_predict(image)
            st.success(f"Prediction: **{label}** with **{conf}%** confidence")
