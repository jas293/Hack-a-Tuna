import streamlit as st
import os
from PIL import Image
from tensorflow import keras
import numpy as np
import streamlit_js_eval as st_eval
import pymysql
from datetime import datetime
import folium
from streamlit_folium import folium_static
from haversine import haversine

st.set_page_config(page_title="Fish Detection", page_icon=":anchor:", layout="wide")

page = st.sidebar.selectbox("Navigation", ["Home", "Upload Images", "Find Fish"])

model = keras.models.load_model("fishModel.h5")

def connect_database():
    db_config = {
        "host": "localhost",
        "user": "root",
        "password": "7004",
        "database": "fishdetection",
    }

    # Create a database connection
    try:
        conn = pymysql.connect(**db_config)
    except pymysql.MySQLError as err:
        st.error(f"Error: {err}")
    return conn


def display_images_in_grid(folder_path="images/", num_columns=3):
    # List all files in the specified folder
    files = os.listdir(folder_path)

    # Filter out only image files (e.g., JPEG, PNG, etc.)
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    image_files = [file for file in files if any(file.endswith(ext) for ext in image_extensions)]

    num_images = len(image_files)

    for i in range(0, num_images, num_columns):
        columns = st.columns(num_columns)
        for j in range(num_columns):
            if i + j < num_images:
                image_file = image_files[i + j]
                image_path = os.path.join(folder_path, image_file)
                columns[j].image(image_path, caption=image_file, use_column_width=True)


def homePage():
    st.subheader("Hi, Connect with Fish Lovers")
    st.title("Find and locate fishes near you")
    display_images_in_grid()


def predict_fish_type(model, image):
    # Preprocess the image

    # Make predictions using the model
    predictions = model.predict(image)
    return predictions


def uploadImage(model):
    st.write("Welcome to the Upload Page!")
    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "gif", "bmp"])
    fish_types = ['Black Sea Sprat', 'Gilt-Head Bream', 'Horse Mackerel',
                  'Red Mullet', 'Red Sea Bream', 'Sea Bass',
                  'Shrimp', 'Striped Red Mullet', 'Trout']

    if uploaded_file is not None:
        location = st_eval.get_geolocation()
        latitude = location["coords"]["latitude"]
        longitude = location["coords"]["longitude"]
        with st.spinner("Predicting..."):
            image = Image.open(uploaded_file)
            image = image.resize((224, 224))
            img_array = keras.preprocessing.image.img_to_array(image)
            img_array = np.expand_dims(img_array, axis=0)
            img_array /= 255.0  # Scale the image pixels to 0-1
            predictions = model.predict(img_array)
            predicted_class = np.argmax(predictions, axis=1)
            predicted_fish_type = fish_types[predicted_class[0]]
        # Process the uploaded image
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        st.text(f"User Coordinates: {latitude, longitude}")
        st.write(predicted_fish_type)
        conn = connect_database()
        cursor = conn.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql = "INSERT INTO fish_location (fish_type, latitude, longitude, timestamp) VALUES (%s, %s, %s, %s)"
        values = (predicted_fish_type, latitude, longitude, timestamp)
        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Data has been inserted into the database.")
    else:
        st.write("Please upload an image.")


def findFish():
    location = st_eval.get_geolocation()
    latitude = location["coords"]["latitude"]
    longitude = location["coords"]["longitude"]
    st.write("Welcome to the Find Page!")
    fish_types = ['Black Sea Sprat', 'Gilt-Head Bream', 'Hourse Mackerel',
                  'Red Mullet', 'Red Sea Bream', 'Sea Bass',
                  'Shrimp', 'Striped Red Mullet', 'Trout']

    selected_fish_type = st.selectbox("Select Fish Type", fish_types)

    st.write(f"You searched for: {selected_fish_type}")

    conn = connect_database()
    cursor = conn.cursor()

    # Retrieve locations where the selected fish type is present
    cursor.execute("SELECT latitude, longitude FROM fish_location WHERE fish_type = %s", (selected_fish_type,))
    results = cursor.fetchall()

    if not results:
        st.warning(f"No locations found for {selected_fish_type}.")
    else:
        # Create a folium map centered on the user's location
        fish_map = folium.Map(location=[latitude, longitude], zoom_start=12)

        display_option = st.radio("Display Option", ["All Locations", "Nearest Location", "Latest Location"])

        if display_option == "All Locations":
            # Add markers for all locations
            for result in results:
                lat, lon = result
                folium.Marker([lat, lon]).add_to(fish_map)

        elif display_option == "Nearest Location":
            # Find the nearest location to the user's location
            closest_location = min(results, key=lambda coord: haversine((latitude, longitude), coord))
            folium.Marker([closest_location[0], closest_location[1]]).add_to(fish_map)

        else:  # Display Latest Location
            folium.Marker([latitude, longitude]).add_to(fish_map)

        st.write("Locations of", selected_fish_type)

        # Use folium_static to render the map as an HTML element
        folium_static(fish_map)

    cursor.close()
    conn.close()


if page == "Home":
    homePage()
elif page == "Upload Images":
    uploadImage(model)
elif page == "Find Fish":
    findFish()
