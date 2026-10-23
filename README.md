# HarborWing Air CRUD Application



## Project Description

The HarborWing Air CRUD Application is a web-based system developed using Python, Flask, HTML, and MySQL. It allows users to manage airline-related information through a simple web interface.

## Technologies Used

- Python
- Flask
- HTML and CSS
- MySQL
- MySQL Connector for Python
- MySQL Workbench

## Features

The application supports the following features:

- Manage booking agents.
- Add, view, search, edit, and delete passenger records.
- Manage reservations and view reservation details.
- Add and manage payments, including payment status.
- Manage airport information.
- Manage flight schedules and flight legs.
- Manage flight costs.
- Link reservations to payments and flight legs.
- Remove reservation links without deleting the original payment or flight-leg records.
- Validate records and prevent certain unsafe deletions.
- Search and filter records.

## Project Requirements

Before running the application, install:

- Python
- MySQL Server
- MySQL Workbench (recommended for database management)
- A web browser

## Installation Instructions

### 1. Prepare the project

Place the project files in one folder. Make sure `app.py`, `requirements.txt`, and `schema.sql` are included.

### 2. Install the dependencies

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

### 3. Set up the database

1. Open MySQL Workbench and connect to your MySQL server.
2. Open `schema.sql`.
3. Execute the SQL script to create the database tables.
4. If your project uses the provided sample data generator, install its dependencies and run `generate_data.py` according to its instructions.

**Warning:** The data generator may clear existing data before inserting sample records. Use it only when you are prepared for that behavior.

If the database is already created and populated, do not run the setup or generator again unless needed.

### 4. Configure the database connection

Open `app.py` and locate the database connection settings.

Use your own local MySQL configuration. The example settings are:

- Host: `127.0.0.1`
- Port: `3306`
- User: `root`
- Database: `HarborWingAir`

Enter your actual password through your local configuration. Do not publish your real password or other secrets on GitHub.

### 5. Run the application

In the terminal, run:

```bash
python app.py
```

Open a browser and visit:

http://127.0.0.1:5000

Keep the terminal running while using the application.

## Database Information

The application uses the `HarborWingAir` MySQL database. It stores passenger, booking agent, reservation, payment, airport, flight schedule, flight leg, and flight cost information.

The database also includes linking tables for connecting reservations to payments and flight legs.

### Database Dependency

- **Midterm Drill repository:** https://github.com/Jovaldz0093/HarborWingAir
- **Database:** HarborWingAir
- **Database version:** MySQL 8.0
- **Schema file:** `schema.sql`
- **Reference commit:** `2b6763f` — Add HarborWing Air database project

The CRUD application uses the database schema from the HarborWing Air Midterm Drill project. The reference commit identifies the version of the repository used as the database dependency.

## Error Handling and Data Validation

The application includes checks to help prevent invalid operations. For example, a payment that is still linked to a reservation cannot be deleted until the relationship is removed.

When a reservation-payment or reservation-leg link is removed, the linked payment or flight-leg record remains in the database.

## Known Limitations

- The application is intended as a student project and may require additional security improvements before production use.
- Database access requires a working MySQL server and correctly configured credentials.
- The application depends on the database schema being consistent with the SQL queries in the source code.
- Some operations may be restricted when related records exist.
- The system does not replace a complete commercial airline reservation or ticketing platform.

## Project Files

- `app.py` — Flask application and routes.
- `templates/` — HTML templates.
- `requirements.txt` — Python dependencies.
- `schema.sql` — database schema.
- `generate_data.py` — sample data generator.
- `HarborDiagram.mwb` — MySQL Workbench diagram.
- `HarborEER.png` — exported database diagram.
- `README.md` — project documentation.

## Running the Application

1. Start MySQL Server.
2. Configure the database connection.
3. Install the required Python packages.
4. Run `python app.py`.
5. Open `http://127.0.0.1:5000` in your browser.
