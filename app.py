from datetime import date
import os
import pandas as pd
import plotly.express as px
import streamlit as st

# Page Config
st.set_page_config(page_title="Sentinel Fitness Portal", layout="wide")

# File paths for persistent storage
USER_FILE = "users.csv"
DATA_FILE = "fitness_data.csv"

# 1. Initialize Users File (Guarantees ONLY the Coach account exists initially)
if not os.path.exists(USER_FILE):
  default_users = pd.DataFrame([{
      "username": "coach",
      "password": "adminpassword",
      "role": "admin",
      "name": "Coach (Master Control)",
      "email": "coach@sentinel.com",
      "phone": "555-0100",
  }])
  default_users.to_csv(USER_FILE, index=False)

# 2. Initialize Flexible Individual Workout Data File
if not os.path.exists(DATA_FILE):
  default_data = pd.DataFrame(
      columns=["Athlete", "Date", "Exercise", "Value"]
  )
  default_data.to_csv(DATA_FILE, index=False)

# Load data from CSV files
users_df = pd.read_csv(USER_FILE)
df = pd.read_csv(DATA_FILE)

# Initialize Session State for Login
if "authenticated" not in st.session_state:
  st.session_state.authenticated = False
  st.session_state.username = ""
  st.session_state.role = ""
  st.session_state.name = ""

# 3. Login Screen (If not logged in)
if not st.session_state.authenticated:
  st.title("🔒 Sentinel Fitness Portal - Login")
  st.markdown("Please sign in with your assigned credentials.")

  with st.form("login_form"):
    username_input = st.text_input("Username").lower().strip()
    password_input = st.text_input("Password", type="password")
    submit_login = st.form_submit_button("Sign In")

    if submit_login:
      matched_user = users_df[users_df["username"] == username_input]
      if (
          not matched_user.empty
          and matched_user.iloc[0]["password"] == password_input
      ):
        st.session_state.authenticated = True
        st.session_state.username = username_input
        st.session_state.role = matched_user.iloc[0]["role"]
        st.session_state.name = matched_user.iloc[0]["name"]
        st.rerun()
      else:
        st.error("Invalid username or password. Please try again.")
  st.stop()

# 4. Main Dashboard (After Successful Login)
col_top1, col_top2 = st.columns([6, 1])
with col_top1:
  st.title(f"🏋️ Welcome, {st.session_state.name}")
with col_top2:
  if st.button("Log Out"):
    st.session_state.authenticated = False
    st.rerun()

st.markdown("---")

# 5. Role-Based Views
if st.session_state.role == "admin":
  # --- ADMIN / MASTER CONTROL VIEW ---
  st.success(
      "🔓 **Master Control Active:** Viewing all athletes and management tools."
  )

  # Tabs for Coach Actions
  tab1, tab2, tab3 = st.tabs([
      "📈 Performance & Analytics",
      "➕ Log Individual Workout",
      "👥 Manage Users & Accounts",
  ])

  with tab1:
    st.sidebar.header("Coach Control Panel")
    athlete_list = df["Athlete"].unique().tolist() if not df.empty else []

    if len(athlete_list) > 0:
      selected_athlete = st.sidebar.selectbox(
          "Select Athlete to View", athlete_list
      )

      # Get available exercises logged for this specific athlete
      athlete_exercises = (
          df[df["Athlete"] == selected_athlete]["Exercise"].unique().tolist()
      )

      if len(athlete_exercises) > 0:
        selected_exercise = st.sidebar.selectbox(
            "Select Exercise for Graph", athlete_exercises
        )

        view_data = df[
            (df["Athlete"] == selected_athlete)
            & (df["Exercise"] == selected_exercise)
        ].copy()
        if not view_data.empty:
          view_data["Date"] = pd.to_datetime(view_data["Date"])
          view_data = view_data.sort_values("Date")
          view_data["Date"] = view_data["Date"].dt.strftime("%Y-%m-%d")

        col1, col2 = st.columns([2, 1])
        with col1:
          st.subheader(
              f"{selected_athlete}'s Progression Timeline:"
              f" {selected_exercise}"
          )
          if not view_data.empty:
            fig = px.line(
                view_data,
                x="Date",
                y="Value",
                markers=True,
                title=f"{selected_exercise} Growth Curve",
            )
            st.plotly_chart(fig, use_container_width=True)
          else:
            st.info("No records found for this exercise.")

        with col2:
          st.subheader(f"🏆 {selected_athlete}'s Personal Bests")
          athlete_records = df[df["Athlete"] == selected_athlete]
          if not athlete_records.empty:
            pb_df = (
                athlete_records.groupby("Exercise")["Value"]
                .max()
                .reset_index()
            )
            pb_df.columns = ["Exercise", "Best Value"]
            st.dataframe(pb_df, use_container_width=True, hide_index=True)
          else:
            st.info("No records available.")
      else:
        st.info("This athlete has no logged workouts yet.")
    else:
      st.info(
          "No workout records exist yet. Go to 'Log Individual Workout' or"
          " 'Manage Users & Accounts' to get started!"
      )
      st.dataframe(df, use_container_width=True)

  with tab2:
    st.subheader("➕ Log an Individual Workout Session")
    athlete_choices = users_df[users_df["role"] == "athlete"]["name"].tolist()

    if len(athlete_choices) > 0:
      with st.form("admin_entry"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
          target_athlete = st.selectbox("Athlete Name", athlete_choices)
        with c2:
          workout_date = st.date_input("Workout Date", value=date.today())
        with c3:
          exercise_name = st.selectbox(
              "Exercise / Metric",
              [
                  "Pushups",
                  "Situps",
                  "Deadhang (s)",
                  "Broad Jump (in)",
                  "Pullups",
                  "Squats",
                  "Mile Run (min)",
              ],
          )
        with c4:
          exercise_value = st.number_input(
              "Result Value", min_value=0.0, value=30.0, step=1.0
          )

        if st.form_submit_button("Save Workout Entry"):
          date_str = workout_date.strftime("%Y-%m-%d")

          duplicate_check = df[
              (df["Athlete"] == target_athlete)
              & (df["Date"] == date_str)
              & (df["Exercise"] == exercise_name)
              & (df["Value"] == exercise_value)
          ]

          if not duplicate_check.empty:
            st.warning(
                "⚠️ This exact workout entry was already logged. Duplicate"
                " prevented."
            )
          else:
            new_row = pd.DataFrame([{
                "Athlete": target_athlete,
                "Date": date_str,
                "Exercise": exercise_name,
                "Value": exercise_value,
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(
                f"Successfully logged {exercise_name} ({exercise_value}) for"
                f" {target_athlete} on {workout_date}!"
            )
            st.rerun()
    else:
      st.warning(
          "⚠️ No athletes found in the system. Please add an athlete account"
          " first under the 'Manage Users & Accounts' tab."
      )

  with tab3:
    st.subheader("👥 User Account Management")

    col_u1, col_u2, col_u3 = st.columns(3)

    with col_u1:
      st.markdown("### Create New User")
      with st.form("create_user_form"):
        new_username = st.text_input("Username (no spaces)")
        new_password = st.text_input("Temporary Password", type="password")
        new_fullname = st.text_input("Full Display Name")
        new_email = st.text_input("Email Address")
        new_phone = st.text_input("Phone Number")
        new_role_choice = st.selectbox(
            "Account Role", ["Athlete", "Master Control (Admin)"]
        )
        submit_user = st.form_submit_button("Create Account")

        if submit_user:
          clean_user = new_username.lower().strip()
          assigned_role = (
              "admin"
              if new_role_choice == "Master Control (Admin)"
              else "athlete"
          )

          if not clean_user or not new_password or not new_fullname:
            st.error("Please fill out required fields.")
          elif clean_user in users_df["username"].values:
            st.error("That username already exists.")
          else:
            new_user_row = pd.DataFrame([{
                "username": clean_user,
                "password": new_password,
                "role": assigned_role,
                "name": new_fullname,
                "email": new_email,
                "phone": new_phone,
            }])
            users_df = pd.concat([users_df, new_user_row], ignore_index=True)
            users_df.to_csv(USER_FILE, index=False)
            st.success(
                f"Created {new_role_choice} account for {new_fullname}!"
            )
            st.rerun()

    with col_u2:
      st.markdown("### Reset Password")
      with st.form("reset_pass_form"):
        target_user_reset = st.selectbox(
            "Select Username to Reset", users_df["username"].tolist()
        )
        new_temp_pass = st.text_input(
            "Enter New Temp Password", type="password"
        )
        submit_reset = st.form_submit_button("Update Password")

        if submit_reset:
          if not new_temp_pass:
            st.error("Please enter a new password.")
          else:
            users_df.loc[
                users_df["username"] == target_user_reset, "password"
            ] = new_temp_pass
            users_df.to_csv(USER_FILE, index=False)
            st.success(f"Password updated for '{target_user_reset}'!")
            st.rerun()

    with col_u3:
      st.markdown("### Delete Account")
      with st.form("delete_user_form"):
        deletable_users = users_df[users_df["role"] != "admin"][
            "username"
        ].tolist()
        if len(deletable_users) > 0:
          target_user_delete = st.selectbox(
              "Select Athlete to Delete", deletable_users
          )
          admin_confirm_pass = st.text_input(
              "Enter Your Admin Password to Confirm", type="password"
          )
          submit_delete = st.form_submit_button("Delete Account")

          if submit_delete:
            current_admin = st.session_state.username
            admin_row = users_df[users_df["username"] == current_admin]

            if (
                not admin_row.empty
                and admin_row.iloc[0]["password"] == admin_confirm_pass
            ):
              users_df = users_df[users_df["username"] != target_user_delete]
              users_df.to_csv(USER_FILE, index=False)
              st.success(
                  f"Successfully deleted account '{target_user_delete}'!"
              )
              st.rerun()
            else:
              st.error("Incorrect admin password. Deletion cancelled.")
        else:
          st.info("No athlete accounts available to delete.")

    st.markdown("---")
    st.markdown("### All Registered Accounts & Contact Info")
    st.dataframe(users_df, use_container_width=True)

else:
  # --- ATHLETE VIEW (Restricted to their own data) ---
  my_name = st.session_state.name
  st.info(f"🔒 **Athlete Portal:** Viewing personal records and progression.")

  my_data = df[df["Athlete"] == my_name].copy()

  if not my_data.empty:
    athlete_exercises = my_data["Exercise"].unique().tolist()
    selected_metric = st.selectbox(
        "Select Exercise to View", athlete_exercises
    )

    exercise_data = my_data[my_data["Exercise"] == selected_metric].copy()
    exercise_data["Date"] = pd.to_datetime(exercise_data["Date"])
    exercise_data = exercise_data.sort_values("Date")
    exercise_data["Date"] = exercise_data["Date"].dt.strftime("%Y-%m-%d")

    col1, col2 = st.columns([2, 1])
    with col1:
      st.subheader(f"Your Progression Timeline: {selected_metric}")
      if not exercise_data.empty:
        fig = px.line(
            exercise_data,
            x="Date",
            y="Value",
            markers=True,
            title=f"Your {selected_metric} Over Time",
        )
        st.plotly_chart(fig, use_container_width=True)
      else:
        st.warning("No records found for this exercise yet.")

    with col2:
      st.subheader("Your Session History")
      st.dataframe(exercise_data, use_container_width=True)
  else:
    st.warning("No performance records found for you yet.")