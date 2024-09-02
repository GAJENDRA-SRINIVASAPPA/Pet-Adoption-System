from datetime import datetime
import pandas as pd
import streamlit as st
import mysql.connector
import requests
from PIL import Image
import base64
from io import BytesIO
import sqlite3


# Function to create a MySQL connection
def create_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Gajendra@123",
        database="pet"
    )

# Function to close the database connection
def close_connection(connection):
    connection.close()

# Function to create the Users table if it doesn't exist
def create_users_table():
    connection = sqlite3.connect("your_database_name.db")  # Replace with your actual database name
    cursor = connection.cursor()

    # Create the Users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Insert a default user for testing purposes
    cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", ("admin", "admin123"))
    cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", ("user", "user123"))

    # Commit changes and close the connection
    connection.commit()
    connection.close()

# Call the function to create the table
create_users_table()

# Function to check if the user is authenticated
def authenticate(username, password):
    connection = sqlite3.connect("your_database_name.db")  # Replace with your actual database name
    cursor = connection.cursor()

    query = "SELECT * FROM Users WHERE username=? AND password=?"
    cursor.execute(query, (username, password))
    result = cursor.fetchone()

    cursor.close()
    connection.close()

    return result is not None

# Function to register a new user
def register_user(username, password):
    connection = sqlite3.connect("your_database_name.db")  # Replace with your actual database name
    cursor = connection.cursor()

    # Check if the username already exists
    cursor.execute("SELECT * FROM Users WHERE username=?", (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        print("Username already exists. Please choose a different username.")
    else:
        # Insert the new user into the Users table
        cursor.execute("INSERT INTO Users (username, password) VALUES (?, ?)", (username, password))
        print("Registration successful!")

    # Commit changes and close the connection
    connection.commit()
    connection.close()

# Example usage
# Register a new user
new_username = "newuser"
new_password = "newuser123"
register_user(new_username, new_password)

# Authenticate with the new user
is_authenticated = authenticate(new_username, new_password)

if is_authenticated:
    print("Authentication successful!")
else:
    print("Authentication failed.")


# Function to view records based on the table name
def view_records(connection, table_name):
    cursor = connection.cursor()
    cursor.execute(f'SELECT * FROM {table_name}')
    records = cursor.fetchall()
    cursor.close()
    return records

# Function to grant admin privilege
def grant_admin_privilege(user_id):
    try:
        response = requests.get(f"http://localhost:8501/grant/{user_id}")
        response.raise_for_status()
        st.success("Admin privilege granted successfully!")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to grant admin privilege. {e}")

# Function to revoke admin privilege
def revoke_admin_privilege(user_id):
    try:
        response = requests.get(f"http://localhost:8501/revoke/{user_id}")
        response.raise_for_status()
        st.success("Admin privilege revoked successfully!")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to revoke admin privilege. {e}")

# Function to get column names of a table
def get_column_names(connection, table_name):
    cursor = connection.cursor()
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    cursor.close()
    return [column[0] for column in columns]

# Function to insert a new record
def insert_record(connection, table_name, values):
    cursor = connection.cursor()
    placeholders = ', '.join(['%s'] * len(values))
    query = f"INSERT INTO {table_name} VALUES ({placeholders})"
    cursor.execute(query, values)
    connection.commit()
    cursor.close()

# Function to update a record
def update_record(connection, table_name, updated_values, record_id):
    cursor = connection.cursor()
    placeholders = ', '.join([f"{column}=%s" for column in get_column_names(connection, table_name)])
    query = f"UPDATE {table_name} SET {placeholders} WHERE {table_name}ID=%s"
    cursor.execute(query, updated_values + [record_id])
    connection.commit()
    cursor.close()

# Function to delete a record
def delete_record(connection, table_name, record_id):
    cursor = connection.cursor()
    cursor.execute(f"DELETE FROM {table_name} WHERE {table_name}ID = %s", (record_id,))
    connection.commit()
    cursor.close()


# Function for Nested Query with Additional Join
def nested_query_with_join(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        # Nested Query with Additional Join: Fetch Adopters, Adopted Pets, and Adoption Details
        cursor.execute("""
            SELECT Adopter.AdopterID, Adopter.Name, 
                   Pet.PetID, Pet.Breed, Adoption.AdoptionDate, Adoption.AdoptionFee
            FROM Adopter
            JOIN Adoption ON Adopter.AdopterID = Adoption.AdopterID
            JOIN Pet ON Adoption.PetID = Pet.PetID
        """)
        results = cursor.fetchall()
    except mysql.connector.Error as err:
        st.error(f"Error in nested query with join: {err}")
        results = None
    finally:
        cursor.close()
    return results

# Function for Aggregate Query: Count Adoptions per Adopter
def aggregate_query(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        # Aggregate Query: Count Adoptions per Adopter
        cursor.execute("""
            SELECT Adopter.AdopterID, Adopter.Name, COUNT(Adoption.AdoptionID) as TotalAdoptions
            FROM Adopter
            LEFT JOIN Adoption ON Adopter.AdopterID = Adoption.AdopterID
            GROUP BY Adopter.AdopterID, Adopter.Name
        """)
        results = cursor.fetchall()
    except mysql.connector.Error as err:
        st.error(f"Error in aggregate query: {err}")
        results = None
    finally:
        cursor.close()
    return results


# Left Join Pets and Adoptions
def left_join_pets_adoptions(connection):
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT Pet.PetID, Pet.Species, Pet.Breed, Pet.Age, Pet.Size, Pet.Color, Pet.Temperament, Pet.HealthStatus,
                   Pet.ShelterID, Adoption.AdoptionID, Adoption.AdoptionDate, Adoption.AdoptionFee
            FROM Pet
            LEFT JOIN Adoption ON Pet.PetID = Adoption.PetID
        """)
        results = cursor.fetchall()
    except mysql.connector.Error as err:
        st.error(f"Error in left join: {err}")
        results = None
    finally:
        cursor.close()
    return results


# Function for Best Pet Breeds based on Adoption Fees
def get_best_breeds(limit_count):
    connection = create_connection()
    cursor = connection.cursor()

    try:
        # Call the stored procedure
        cursor.callproc("GetBestBreeds", (limit_count,))
        connection.commit()

        # Fetch the result from the stored procedure
        for result in cursor.stored_results():
            rows = result.fetchall()

        return rows

    except mysql.connector.Error as err:
        st.error(f"Error: {err}")
        return None

    finally:
        cursor.close()
        close_connection(connection)


# Login Page
def login():
    if 'login_status' not in st.session_state:
        st.session_state.login_status = False
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False  
    st.title("Welcome to 'Furry Friends Finder: The Ultimate Furry Pet Adoption Platform'")

    st.header("Login Page")
    
    if not st.session_state.login_status:
        user_type = st.radio("Select User Type", ["Admin", "User"])
        username = st.text_input(f"{user_type} Username:")
        password = st.text_input(f"{user_type} Password:", type="password")
        login_button = st.button("Login")

        if login_button:
            if authenticate(username, password):
                st.success("Login successful!")
                st.session_state.login_status = True
                st.session_state.is_admin = (user_type == "Admin")
            else:
                st.error("Invalid credentials. Please try again.")

    # Display the main application if logged in
    if st.session_state.login_status:
        main_application()
    

# Main Application
def main_application():
    # Function to convert image to base64
    def image_to_base64(image):
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()

    # Open an image file
    with Image.open('C:\\Users\\Dell\\Pictures\\Dog-Adoption.jpg') as img:
        # Resize the image
        img = img.resize((100, 100))

    # Create a connection at the beginning
    connection = create_connection()

    # Display the welcome message and introduction
    st.title("“Furry Friends Finder: The Ultimate Pet Adoption Platform”")
    st.markdown(
        """
        Welcome to “Pawsitive Partners: Your Guide to Pet Adoption”! This platform is your 
        one-stop solution for managing the pet adoption process with ease and efficiency. 
        Navigate through our user-friendly interface to explore information about potential pet companions,
          successful adoptions, generous donors, dedicated fosters, comprehensive medical records, 
          adorable pets, welcoming shelters, and professional vet clinics.

    🐕 Kickstart your journey by selecting a category from our navigation panel. Let’s create some ‘pawsitive’ stories together! 🐾
        """
    )
     
    # Display the image with custom HTML/CSS for alignment
    st.markdown(
        f'<img src="data:image/png;base64,{image_to_base64(img)}" style="float: right; width: 100px; height: 100px;">',
        unsafe_allow_html=True
    )

    # Sidebar for navigation
    page = st.sidebar.radio("Navigation", ["Home", "View Adopters", "View Adoptions", "View Donors",
                                           "View Fosters", "View Medical Records", "View Pets",
                                           "View Shelters", "View Vet Clinics", "Manage Users/Admin", "More..."],
                            key="navigation")

    # Home Page
    if page == "Home":
        st.header("👈Begin your journey by choosing a category from Left options! (❁´◡`❁)")

    # View Adopters Page
    elif page == "View Adopters":
        st.header("View Adopters")
        connection = create_connection()
        adopters = view_records(connection, "Adopter")
        if not adopters:
            st.warning("No adopters found.")
        else:
            columns = get_column_names(connection, "Adopter")
            adopters_df = pd.DataFrame(adopters, columns=columns)
            st.table(adopters_df)

        # Insert new record section
        st.subheader("Insert New Adopter Record")
        new_adopter_values = st.text_input("Enter values separated by commas")
        if st.button("Insert Adopter Record"):
            new_adopter_values_list = new_adopter_values.split(',')
            insert_record(connection, "Adopter", new_adopter_values_list)
            st.success("Record inserted successfully!")
        
        # Delete record section
        st.subheader("Delete Adopter Record")
        adopter_id_to_delete = st.text_input("Enter AdopterID to delete")
        if st.button("Delete Adopter Record"):
            delete_record(connection, "Adopter", adopter_id_to_delete)
            st.success("Record deleted successfully!")

        # Update record section
        st.subheader("Update Adopter Record")
        adopter_id_to_update = st.text_input("Enter AdopterID to update")
        updated_adopter_values = st.text_input("Enter updated values separated by commas")
        if st.button("Update Adopter Record"):
            updated_adopter_values_list = updated_adopter_values.split(',')
            update_record(connection, "Adopter", updated_adopter_values_list, adopter_id_to_update)
            st.success("Record updated successfully!")

    # View Adoptions Page
    elif page == "View Adoptions":
        st.header("View Adoptions")
        connection = create_connection()
        adoptions = view_records(connection, "Adoption")

        if not adoptions:
            st.warning("No adoptions found.")
        else:
            columns = get_column_names(connection, "Adoption")
            adoptions_df = pd.DataFrame(adoptions, columns=columns)
            st.table(adoptions_df)

        # Insert new record button
        st.subheader("Insert New Adoption")
        new_adoption_values = st.text_input("Enter values separated by commas")
        if st.button("Insert Adoption"):
            new_adoption_values_list = new_adoption_values.split(',')
            if len(new_adoption_values_list)<6:
                new_adoption_values_list.append(datetime.now().strftime('%Y-%m-%d'))
            insert_record(connection, "Adoption", new_adoption_values_list)
            st.success("Record inserted successfully!")

        # Delete record button
        st.subheader("Delete Adoption")
        adoption_id_to_delete = st.text_input("Enter AdoptionID to delete")
        if st.button("Delete Adoption"):
            delete_record(connection, "Adoption", adoption_id_to_delete)
            st.success("Record deleted successfully!")

        # Update record button
        st.subheader("Update Adoption")
        adoption_id_to_update = st.text_input("Enter AdoptionID to update")
        updated_values = st.text_input("Enter updated values separated by commas")
        if st.button("Update Adoption"):
            updated_values_list = updated_values.split(',')
            update_record(connection, "Adoption", updated_values_list, adoption_id_to_update)
            st.success("Record updated successfully!")

        close_connection(connection)

    # View Donors Page
    elif page == "View Donors":
        st.header("View Donors")
        connection = create_connection()
        donors = view_records(connection, "Donor")
        if not donors:
            st.warning("No donors found.")
        else:
            columns = get_column_names(connection, "Donor")
            donors_df = pd.DataFrame(donors, columns=columns)
            st.table(donors_df)

        # Insert new record button
        st.subheader("Insert New Donor")
        new_donor_values = st.text_input("Enter values separated by commas")
        if st.button("Insert Donor"):
            new_donor_values_list = new_donor_values.split(',')
            insert_record(connection, "Donor", new_donor_values_list)
            st.success("Record inserted successfully!")

        # Delete record button
        st.subheader("Delete Donor")
        donor_id_to_delete = st.text_input("Enter DonorID to delete")
        if st.button("Delete Donor"):
            delete_record(connection, "Donor", donor_id_to_delete)
            st.success("Record deleted successfully!")

        # Update record button
        st.subheader("Update Donor")
        donor_id_to_update = st.text_input("Enter DonorID to update")
        updated_values = st.text_input("Enter updated values separated by commas")
        if st.button("Update Donor"):
            updated_values_list = updated_values.split(',')
            update_record(connection, "Donor", updated_values_list, donor_id_to_update)
            st.success("Record updated successfully!")
        close_connection(connection)

    # View Fosters Page
    elif page == "View Fosters":
        st.header("View Fosters")
        connection = create_connection()
        fosters = view_records(connection, "Foster")
        if not fosters:
            st.warning("No fosters found.")
        else:
            columns = get_column_names(connection, "Foster")
            fosters_df = pd.DataFrame(fosters, columns=columns)
            st.table(fosters_df)

        # Insert new record button
        st.subheader("Insert New Foster")
        new_foster_values = st.text_input("Enter values separated by commas")
        if st.button("Insert Foster"):
            new_foster_values_list = new_foster_values.split(',')
            insert_record(connection, "Foster", new_foster_values_list)
            st.success("Record inserted successfully!")

        # Delete record button
        st.subheader("Delete Foster")
        foster_id_to_delete = st.text_input("Enter FosterID to delete")
        if st.button("Delete Foster"):
            delete_record(connection, "Foster", foster_id_to_delete)
            st.success("Record deleted successfully!")

        # Update record button
        st.subheader("Update Foster")
        foster_id_to_update = st.text_input("Enter FosterID to update")
        updated_foster_values = st.text_input("Enter updated values separated by commas")
        if st.button("Update Foster"):
            updated_foster_values_list = updated_foster_values.split(',')
            update_record(connection, "Foster", updated_foster_values_list, foster_id_to_update)
            st.success("Record updated successfully!")
        close_connection(connection)

    # View Medical Records Page
    elif page == "View Medical Records":
        st.header("View Medical Records")
        connection = create_connection()
        medical_records = view_records(connection, "MedicalRecord")
        if not medical_records:
            st.warning("No medical records found.")
        else:
            columns = get_column_names(connection, "MedicalRecord")
            medical_records_df = pd.DataFrame(medical_records, columns=columns)
            st.table(medical_records_df)

        # Insert new record button
        st.subheader("Insert New Medical Record")
        new_medical_record_values = st.text_input("Enter values separated by commas")
        if st.button("Insert Medical Record"):
            new_medical_record_values_list = new_medical_record_values.split(',')
            insert_record(connection, "MedicalRecord", new_medical_record_values_list)
            st.success("Record inserted successfully!")

        # Delete record button
        st.subheader("Delete Medical Record")
        record_id_to_delete = st.text_input("Enter RecordID to delete")
        if st.button("Delete Medical Record"):
            delete_record(connection, "MedicalRecord", record_id_to_delete)
            st.success("Record deleted successfully!")

            # Update record button
        st.subheader("Update Medical Record")
        record_id_to_update = st.text_input("Enter RecordID to update")
        updated_medical_record_values = st.text_input("Enter updated values separated by commas")
        if st.button("Update Medical Record"):
            updated_medical_record_values_list = updated_medical_record_values.split(',')
            update_record(connection, "MedicalRecord", updated_medical_record_values_list, record_id_to_update)
            st.success("Record updated successfully!")
        close_connection(connection)

    # View Pets Page
    elif page == "View Pets":
        st.header("View Pets")
        connection = create_connection()
        pets = view_records(connection, "Pet")
        if not pets:
            st.warning("No pets found.")
        else:
            columns = get_column_names(connection, "Pet")
            pets_df = pd.DataFrame(pets, columns=columns)
            st.table(pets_df)

        # Insert new record button
        st.subheader("Insert New Pet Record")
        new_pet_values = st.text_input("Enter values separated by commas")
        if st.button("Insert Pet Record"):
            new_pet_values_list = new_pet_values.split(',')
            insert_record(connection, "Pet", new_pet_values_list)
            st.success("Record inserted successfully!")

        # Delete record button
        st.subheader("Delete Pet Record")
        pet_id_to_delete = st.text_input("Enter PetID to delete")
        if st.button("Delete Pet Record"):
            delete_record(connection, "Pet", pet_id_to_delete)
            st.success("Record deleted successfully!")

        # Update record button
        st.subheader("Update Pet Record")
        pet_id_to_update = st.text_input("Enter PetID to update")
        updated_pet_values = st.text_input("Enter updated values separated by commas")
        if st.button("Update Pet Record"):
            updated_pet_values_list = updated_pet_values.split(',')
            update_record(connection, "Pet", updated_pet_values_list, pet_id_to_update)
            st.success("Record updated successfully!")
        close_connection(connection)

    # View Shelters Page
    elif page == "View Shelters":
        st.header("View Shelters")
        connection = create_connection()
        shelters = view_records(connection, "Shelter")
        if not shelters:
            st.warning("No shelters found.")
        else:
            columns = get_column_names(connection, "Shelter")
            shelters_df = pd.DataFrame(shelters, columns=columns)
            st.table(shelters_df)

        # Insert new record button
        st.subheader("Insert New Shelter Record")
        new_shelter_values = st.text_input("Enter values separated by commas")
        if st.button("Insert Shelter Record"):
            new_shelter_values_list = new_shelter_values.split(',')
            insert_record(connection, "Shelter", new_shelter_values_list)
            st.success("Record inserted successfully!")

        # Delete record button
        st.subheader("Delete Shelter Record")
        shelter_id_to_delete = st.text_input("Enter ShelterID to delete")
        if st.button("Delete Shelter Record"):
            delete_record(connection, "Shelter", shelter_id_to_delete)
            st.success("Record deleted successfully!")

        # Update record button
        st.subheader("Update Shelter Record")
        shelter_id_to_update = st.text_input("Enter ShelterID to update")
        updated_shelter_values = st.text_input("Enter updated values separated by commas")
        if st.button("Update Shelter Record"):
            updated_shelter_values_list = updated_shelter_values.split(',')
            update_record(connection, "Shelter", updated_shelter_values_list, shelter_id_to_update)
            st.success("Record updated successfully!")
        close_connection(connection)

    # View Vet Clinics Page
    elif page == "View Vet Clinics":
        st.header("View Vet Clinics")
        connection = create_connection()
        vetclinics = view_records(connection, "VetClinic")
        if not vetclinics:
            st.warning("No vet clinics found.")
        else:
            columns = get_column_names(connection, "VetClinic")
            vetclinics_df = pd.DataFrame(vetclinics, columns=columns)
            st.table(vetclinics_df)

        # Insert new record button
        st.subheader("Insert New Vet Clinic Record")
        new_vetclinic_values = st.text_input("Enter values separated by commas")
        if st.button("Insert Vet Clinic Record"):
            new_vetclinic_values_list = new_vetclinic_values.split(',')
            insert_record(connection, "VetClinic", new_vetclinic_values_list)
            st.success("Record inserted successfully!")

        # Delete record button
        st.subheader("Delete Vet Clinic Record")
        vetclinic_id_to_delete = st.text_input("Enter ClinicID to delete")
        if st.button("Delete Vet Clinic Record"):
            delete_record(connection, "VetClinic", vetclinic_id_to_delete)
            st.success("Record deleted successfully!")

        # Update record button
        st.subheader("Update Vet Clinic Record")
        vetclinic_id_to_update = st.text_input("Enter ClinicID to update")
        updated_vetclinic_values = st.text_input("Enter updated values separated by commas")
        if st.button("Update Vet Clinic Record"):
            updated_vetclinic_values_list = updated_vetclinic_values.split(',')
            update_record(connection, "VetClinic", updated_vetclinic_values_list, vetclinic_id_to_update)
            st.success("Record updated successfully!")
        close_connection(connection)

    
    # Manage Users Page
    elif page == "Manage Users/Admin":
        st.header("Manage Users/admin")

            # User creation form (only for admin users)
        if st.session_state.is_admin:
            st.subheader("Create New User/Admin")
            new_privilege = st.selectbox("Privilege:", ["user", "admin"])
            new_username = st.text_input("UserName/AdminName:")
            new_password = st.text_input("Password:", type="password")
            
            if new_privilege == 'user' :
                create_user_button = st.button("Create User")
            else:
                create_user_button = st.button("Create Admin")
            if create_user_button:
                # Add logic to create a new user
                st.success("User created successfully!")
        else:
            st.warning("This page can be accessed by only admin.")
        
    elif page == "More...":
        st.header("Analysis:")
        
        # Nested Query for : details of adopters, their adopted pets, and the adoption process.
        st.subheader("Here are the details of adopters, their adopted pets, and the adoption process.")
        nested_query_with_join_result = nested_query_with_join(connection)
        if nested_query_with_join_result:
            columns = ["AdopterID", "Name" ,"PetID", "Breed", "AdoptionDate", "AdoptionFee"]
            nested_query_with_join_df = pd.DataFrame(nested_query_with_join_result, columns=columns)
            st.table(nested_query_with_join_df)
           
        # Aggregate Query Example : to find total no. of adoptions group by adopter 
        st.subheader("Total number of adoptions for each adopter.")
        aggregate_query_result = aggregate_query(connection)
        if aggregate_query_result:
            columns = ["AdopterID", "Name","TotalAdoptions"]
            aggregate_query_df = pd.DataFrame(aggregate_query_result, columns=columns)
            st.table(aggregate_query_df)
            
        # Left Join Pets and Adoptions
        st.subheader( "Here are individuals with their pets and corresponding adoption details.")
        left_join_result = left_join_pets_adoptions(connection)
        if left_join_result:
        #     columns = get_column_names(connection, "Pet") + get_column_names(connection, "Adoption")
            left_join_df = pd.DataFrame(left_join_result)
            st.table(left_join_df)

        # Procedure :
        
        st.title("Best Pet Breeds based on Adoption Fees")
        limit_count = st.number_input("Enter the number of breeds to display:", min_value=1, value=3)
        get_best_breeds_button = st.button("Get Best Breeds")

        # Event handler for the button
        if get_best_breeds_button:
            result = get_best_breeds(limit_count)

            # Display the result using Streamlit
            if result:
                columns = ["Breed", "AverageAdoptionFee"]
                result_df = pd.DataFrame(result, columns=columns)
                st.table(result_df)
            else:
                st.warning("No data available.")
# Run the login function
login()

