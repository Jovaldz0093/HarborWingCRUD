from flask import Flask, render_template, request, redirect, url_for
from db import get_connection
from decimal import Decimal, InvalidOperation
from datetime import date

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/passengers")
def passengers():
    search = request.args.get("search", "").strip()

    connection = get_connection()
    cursor = connection.cursor()

    if search:
        keyword = "%" + search + "%"

        cursor.execute("""
            SELECT passenger_id, first_name, last_name, email, phone
            FROM Passenger
            WHERE CAST(passenger_id AS CHAR) LIKE %s
               OR first_name LIKE %s
               OR last_name LIKE %s
               OR email LIKE %s
               OR phone LIKE %s
            ORDER BY passenger_id
        """, (keyword, keyword, keyword, keyword, keyword))
    else:
        cursor.execute("""
            SELECT passenger_id, first_name, last_name, email, phone
            FROM Passenger
            ORDER BY passenger_id
        """)

    passenger_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "passengers.html",
        passengers=passenger_list,
        search=search
    )
@app.route("/add_passenger", methods=["POST"])
def add_passenger():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip() or None
    phone = request.form.get("phone", "").strip() or None
    if not first_name or not last_name:
        return "First name and last name are required.", 400
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO Passenger (first_name, last_name, email, phone)
            VALUES (%s, %s, %s, %s)
        """, (first_name, last_name, email, phone))
        connection.commit()
    except Exception:
        connection.rollback()
        return "Could not add passenger. Please check the information.", 400
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("passengers"))
@app.route("/edit_passenger/<int:passenger_id>", methods=["GET", "POST"])
def edit_passenger(passenger_id):
    connection = get_connection()
    cursor = connection.cursor()
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        if not first_name or not last_name:
            cursor.close()
            connection.close()
            return "First name and last name are required.", 400
        cursor.execute("""
            UPDATE Passenger
            SET first_name = %s,
                last_name = %s,
                email = %s,
                phone = %s
            WHERE passenger_id = %s
        """, (first_name, last_name, email, phone, passenger_id))
        connection.commit()
        cursor.close()
        connection.close()
        return redirect(url_for("passengers"))
    cursor.execute("""
        SELECT passenger_id, first_name, last_name, email, phone
        FROM Passenger
        WHERE passenger_id = %s
    """, (passenger_id,))
    passenger = cursor.fetchone()
    cursor.close()
    connection.close()
    if passenger is None:
        return "Passenger not found.", 404
    return render_template("edit_passenger.html", passenger=passenger)
@app.route("/delete_passenger/<int:passenger_id>", methods=["POST"])
def delete_passenger(passenger_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM Passenger WHERE passenger_id = %s",
            (passenger_id,)
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return "Passenger not found.", 404
        connection.commit()
    except Exception:
        connection.rollback()
        return (
            "Cannot delete this passenger because a reservation may reference them.",
            400
        )
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("passengers"))

@app.route("/reservations")
def reservations():
    search = request.args.get("search", "").strip()

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    if search:
        keyword = "%" + search + "%"

        cursor.execute("""
            SELECT r.reservation_id,
                   r.passenger_id,
                   p.first_name,
                   p.last_name,
                   r.agent_id,
                   r.status_code,
                   r.ticket_code,
                   r.class_code,
                   r.created_at,
                   r.party_size
            FROM Reservation r
            JOIN Passenger p
                ON r.passenger_id = p.passenger_id
            WHERE CAST(r.reservation_id AS CHAR) LIKE %s
               OR p.first_name LIKE %s
               OR p.last_name LIKE %s
            ORDER BY r.reservation_id
        """, (keyword, keyword, keyword))
    else:
        cursor.execute("""
            SELECT r.reservation_id,
                   r.passenger_id,
                   p.first_name,
                   p.last_name,
                   r.agent_id,
                   r.status_code,
                   r.ticket_code,
                   r.class_code,
                   r.created_at,
                   r.party_size
            FROM Reservation r
            JOIN Passenger p
                ON r.passenger_id = p.passenger_id
            ORDER BY r.reservation_id
        """)

    reservation_list = cursor.fetchall()

    cursor.close()
    connection.close()

    # Load options for the Create Reservation form
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT passenger_id, first_name, last_name
        FROM Passenger
        ORDER BY first_name
    """)
    passengers = cursor.fetchall()

    cursor.execute("SELECT * FROM ReservationStatus")
    statuses = cursor.fetchall()

    cursor.execute("SELECT * FROM TicketType")
    tickets = cursor.fetchall()

    cursor.execute("SELECT * FROM TravelClass")
    classes = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "reservations.html",
        reservations=reservation_list,
        passengers=passengers,
        statuses=statuses,
        tickets=tickets,
        classes=classes,
        search=search
    )

@app.route("/add_reservation", methods=["POST"])
def add_reservation():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        passenger_id = int(request.form["passenger_id"])
        agent_text = request.form.get("agent_id", "").strip()
        agent_id = int(agent_text) if agent_text else None
        status_code = request.form["status_code"]
        ticket_code = request.form["ticket_code"]
        class_code = request.form["class_code"]
        party_size = int(request.form["party_size"])
        if party_size < 1:
            return "Party size must be at least 1.", 400
        cursor.execute("""
            INSERT INTO Reservation
            (passenger_id, agent_id, status_code,
             ticket_code, class_code, created_at, party_size)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
        """, (
            passenger_id,
            agent_id,
            status_code,
            ticket_code,
            class_code,
            party_size
        ))
        connection.commit()
        return redirect(url_for("reservations"))
    except ValueError:
        connection.rollback()
        return "Please enter valid numeric IDs and party size.", 400
    except Exception as error:
        connection.rollback()
        return f"Could not create reservation: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/edit_reservation/<int:reservation_id>", methods=["GET", "POST"])
def edit_reservation(reservation_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if request.method == "POST":
            passenger_id = int(request.form["passenger_id"])
            agent_text = request.form.get("agent_id", "").strip()
            agent_id = int(agent_text) if agent_text else None
            status_code = request.form["status_code"]
            ticket_code = request.form["ticket_code"]
            class_code = request.form["class_code"]
            party_size = int(request.form["party_size"])
            if party_size < 1:
                return "Party size must be at least 1.", 400
            cursor.execute("""
                UPDATE Reservation
                SET passenger_id = %s,
                    agent_id = %s,
                    status_code = %s,
                    ticket_code = %s,
                    class_code = %s,
                    party_size = %s
                WHERE reservation_id = %s
            """, (
                passenger_id, agent_id, status_code,
                ticket_code, class_code, party_size,
                reservation_id
            ))
            if cursor.rowcount == 0:
                connection.rollback()
                return "Reservation not found or no changes were made.", 404
            connection.commit()
            return redirect(url_for("reservations"))
        cursor.execute("""
            SELECT * FROM Reservation
            WHERE reservation_id = %s
        """, (reservation_id,))
        reservation = cursor.fetchone()
        if reservation is None:
            return "Reservation not found.", 404
        cursor.execute("""
            SELECT passenger_id, first_name, last_name
            FROM Passenger ORDER BY first_name, last_name
        """)
        passengers = cursor.fetchall()
        cursor.execute("""
            SELECT status_code, description
            FROM ReservationStatus ORDER BY status_code
        """)
        statuses = cursor.fetchall()
        cursor.execute("""
            SELECT ticket_code, description
            FROM TicketType ORDER BY ticket_code
        """)
        tickets = cursor.fetchall()
        cursor.execute("""
            SELECT class_code, description
            FROM TravelClass ORDER BY class_code
        """)
        classes = cursor.fetchall()
        return render_template(
            "edit_reservation.html",
            reservation=reservation,
            passengers=passengers,
            statuses=statuses,
            tickets=tickets,
            classes=classes
        )
    except ValueError:
        connection.rollback()
        return "Please enter valid numeric values.", 400
    except Exception as error:
        connection.rollback()
        return f"Could not update reservation: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/delete_reservation/<int:reservation_id>", methods=["POST"])
def delete_reservation(reservation_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM Reservation WHERE reservation_id = %s",
            (reservation_id,)
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return "Reservation not found.", 404
        connection.commit()
        return redirect(url_for("reservations"))
    except Exception:
        connection.rollback()
        return (
            "Cannot delete this reservation because related records "
            "may still be linked to it. Remove its links first.",
            400
        )
    finally:
        cursor.close()
        connection.close()

@app.route("/payments")
def payments():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            p.payment_id,
            p.status_code,
            ps.description AS status_description,
            p.payment_date,
            p.amount
        FROM Payment p
        JOIN PaymentStatus ps
            ON p.status_code = ps.status_code
        WHERE 1=1
    """

    params = []

    if search:
        query += " AND CAST(p.payment_id AS CHAR) LIKE %s"
        params.append("%" + search + "%")

    if status_filter:
        query += " AND p.status_code = %s"
        params.append(status_filter)

    query += " ORDER BY p.payment_id"

    cursor.execute(query, tuple(params))
    payments = cursor.fetchall()

    cursor.execute("""
        SELECT status_code, description
        FROM PaymentStatus
        ORDER BY status_code
    """)
    statuses = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "payments.html",
        payments=payments,
        statuses=statuses,
        search=search,
        status_filter=status_filter
    )

@app.route("/edit_payment/<int:payment_id>", methods=["GET", "POST"])
def edit_payment(payment_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":
        status_code = request.form["status_code"]
        amount = request.form["amount"]

        try:
            cursor.execute("""
                UPDATE Payment
                SET status_code = %s,
                    amount = %s
                WHERE payment_id = %s
            """, (status_code, amount, payment_id))

            connection.commit()
            cursor.close()
            connection.close()

            return redirect(url_for("payments"))

        except Exception as e:
            connection.rollback()
            cursor.close()
            connection.close()
            return f"Error updating payment: {e}"

    cursor.execute("""
        SELECT payment_id, status_code, payment_date, amount
        FROM Payment
        WHERE payment_id = %s
    """, (payment_id,))
    payment = cursor.fetchone()

    cursor.execute("""
        SELECT status_code, description
        FROM PaymentStatus
        ORDER BY status_code
    """)
    statuses = cursor.fetchall()

    cursor.close()
    connection.close()

    if payment is None:
        return "Payment not found", 404

    return render_template(
        "edit_payment.html",
        payment=payment,
        statuses=statuses
    )


@app.route("/delete_payment/<int:payment_id>", methods=["POST"])
def delete_payment(payment_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Check whether the payment is linked to a reservation.
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM ReservationPayment
            WHERE payment_id = %s
        """, (payment_id,))
        result = cursor.fetchone()

        if result["total"] > 0:
            cursor.close()
            connection.close()
            return (
                "Cannot delete this payment because it is linked "
                "to a reservation. Unlink it first.",
                400
            )

        cursor.execute("""
            DELETE FROM Payment
            WHERE payment_id = %s
        """, (payment_id,))

        if cursor.rowcount == 0:
            connection.rollback()
            cursor.close()
            connection.close()
            return "Payment not found", 404

        connection.commit()

    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return f"Error deleting payment: {e}"

    cursor.close()
    connection.close()

    return redirect(url_for("payments"))


@app.route("/add_payment", methods=["POST"])
def add_payment():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        status_code = request.form["status_code"]
        amount = Decimal(request.form["amount"])
        if not amount.is_finite() or amount <= 0:
            return "Amount must be greater than zero.", 400
        cursor.execute("""
            INSERT INTO Payment
                (status_code, payment_date, amount)
            VALUES (%s, NOW(), %s)
        """, (status_code, amount))
        connection.commit()
        return redirect(url_for("payments"))
    except (InvalidOperation, ValueError):
        connection.rollback()
        return "Please enter a valid payment amount.", 400
    except Exception as error:
        connection.rollback()
        return f"Could not create payment: {error}", 400
    finally:
        cursor.close()
        connection.close()

@app.route("/airports")
def airports():
    search = request.args.get("search", "").strip()

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    if search:
        keyword = "%" + search + "%"
        cursor.execute("""
            SELECT airport_code, airport_name, location, details
            FROM Airport
            WHERE airport_code LIKE %s
               OR airport_name LIKE %s
               OR location LIKE %s
            ORDER BY airport_code
        """, (keyword, keyword, keyword))
    else:
        cursor.execute("""
            SELECT airport_code, airport_name, location, details
            FROM Airport
            ORDER BY airport_code
        """)

    airport_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "airports.html",
        airports=airport_list,
        search=search
    )

@app.route("/add_airport", methods=["POST"])
def add_airport():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        airport_code = request.form["airport_code"].strip().upper()
        airport_name = request.form["airport_name"].strip()
        location = request.form["location"].strip()
        details = request.form.get("details", "").strip() or None
        if not airport_code or not airport_name or not location:
            return "Airport code, name, and location are required.", 400
        cursor.execute("""
            INSERT INTO Airport
                (airport_code, airport_name, location, details)
            VALUES (%s, %s, %s, %s)
        """, (airport_code, airport_name, location, details))
        connection.commit()
        return redirect(url_for("airports"))
    except Exception as error:
        connection.rollback()
        return f"Could not add airport. Check the code is unique. Details: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/edit_airport/<string:airport_code>", methods=["GET", "POST"])
def edit_airport(airport_code):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if request.method == "POST":
            airport_name = request.form["airport_name"].strip()
            location = request.form["location"].strip()
            details = request.form.get("details", "").strip() or None
            if not airport_name or not location:
                return "Airport name and location are required.", 400
            cursor.execute("""
                UPDATE Airport
                SET airport_name = %s,
                    location = %s,
                    details = %s
                WHERE airport_code = %s
            """, (airport_name, location, details, airport_code))
            if cursor.rowcount == 0:
                connection.rollback()
                return "Airport not found or no changes were made.", 404
            connection.commit()
            return redirect(url_for("airports"))
        cursor.execute("""
            SELECT airport_code, airport_name, location, details
            FROM Airport
            WHERE airport_code = %s
        """, (airport_code,))
        airport = cursor.fetchone()
        if airport is None:
            return "Airport not found.", 404
        return render_template("edit_airport.html", airport=airport)
    except Exception as error:
        connection.rollback()
        return f"Could not update airport: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/delete_airport/<string:airport_code>", methods=["POST"])
def delete_airport(airport_code):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM Airport WHERE airport_code = %s",
            (airport_code,)
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return "Airport not found.", 404
        connection.commit()
        return redirect(url_for("airports"))
    except Exception:
        connection.rollback()
        return (
            "Cannot delete this airport because a flight schedule "
            "or another record may reference it.",
            400
        )
    finally:
        cursor.close()
        connection.close()

@app.route("/flight_schedules")
def flight_schedules():
    search = request.args.get("search", "").strip()

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    if search:
        keyword = "%" + search + "%"
        cursor.execute("""
            SELECT
                f.flight_number,
                f.airline_code,
                f.aircraft_code,
                f.origin,
                f.destination,
                f.scheduled_departure,
                f.scheduled_arrival
            FROM FlightSchedule f
            WHERE f.flight_number LIKE %s
               OR f.airline_code LIKE %s
               OR f.aircraft_code LIKE %s
               OR f.origin LIKE %s
               OR f.destination LIKE %s
            ORDER BY f.flight_number
        """, (keyword, keyword, keyword, keyword, keyword))
    else:
        cursor.execute("""
            SELECT
                f.flight_number,
                f.airline_code,
                f.aircraft_code,
                f.origin,
                f.destination,
                f.scheduled_departure,
                f.scheduled_arrival
            FROM FlightSchedule f
            ORDER BY f.flight_number
        """)

    flights = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "flight_schedules.html",
        flights=flights,
        search=search
    )

@app.route("/add_flight_schedule", methods=["POST"])
def add_flight_schedule():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        flight_number = request.form["flight_number"].strip().upper()
        airline_code = request.form["airline_code"].strip().upper()
        aircraft_code = request.form["aircraft_code"].strip().upper()
        origin = request.form["origin"].strip().upper()
        destination = request.form["destination"].strip().upper()
        departure = request.form["scheduled_departure"].strip()
        arrival = request.form["scheduled_arrival"].strip()
        if not all([
            flight_number, airline_code, aircraft_code,
            origin, destination, departure, arrival
        ]):
            return "Please complete all fields.", 400
        if origin == destination:
            return "Origin and destination must be different.", 400
        if arrival <= departure:
            return "Arrival must be later than departure.", 400
        cursor.execute("""
            INSERT INTO FlightSchedule (
                flight_number, airline_code, aircraft_code,
                origin, destination,
                scheduled_departure, scheduled_arrival
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            flight_number, airline_code, aircraft_code,
            origin, destination, departure, arrival
        ))
        connection.commit()
        return redirect(url_for("flight_schedules"))
    except Exception as error:
        connection.rollback()
        return (
            "Could not add flight. Check that the airline, aircraft, "
            "and airport codes exist and the flight number is unique. "
            f"Details: {error}",
            400
        )
    finally:
        cursor.close()
        connection.close()
@app.route("/edit_flight_schedule/<string:flight_number>",
           methods=["GET", "POST"])
def edit_flight_schedule(flight_number):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if request.method == "POST":
            airline_code = request.form["airline_code"].strip().upper()
            aircraft_code = request.form["aircraft_code"].strip().upper()
            origin = request.form["origin"].strip().upper()
            destination = request.form["destination"].strip().upper()
            departure = request.form["scheduled_departure"].strip()
            arrival = request.form["scheduled_arrival"].strip()
            if not all([
                airline_code, aircraft_code, origin,
                destination, departure, arrival
            ]):
                return "Please complete all fields.", 400
            if origin == destination:
                return "Origin and destination must be different.", 400
            if arrival <= departure:
                return "Arrival must be later than departure.", 400
            cursor.execute("""
                UPDATE FlightSchedule
                SET airline_code = %s,
                    aircraft_code = %s,
                    origin = %s,
                    destination = %s,
                    scheduled_departure = %s,
                    scheduled_arrival = %s
                WHERE flight_number = %s
            """, (
                airline_code, aircraft_code, origin, destination,
                departure, arrival, flight_number
            ))
            if cursor.rowcount == 0:
                connection.rollback()
                return "Flight not found or no changes were made.", 404
            connection.commit()
            return redirect(url_for("flight_schedules"))
        cursor.execute("""
            SELECT * FROM FlightSchedule
            WHERE flight_number = %s
        """, (flight_number,))
        flight = cursor.fetchone()
        if flight is None:
            return "Flight not found.", 404
        return render_template("edit_flight_schedule.html", flight=flight)
    except Exception as error:
        connection.rollback()
        return f"Could not update flight: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/delete_flight_schedule/<string:flight_number>",
           methods=["POST"])
def delete_flight_schedule(flight_number):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM FlightSchedule WHERE flight_number = %s",
            (flight_number,)
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return "Flight not found.", 404
        connection.commit()
        return redirect(url_for("flight_schedules"))
    except Exception:
        connection.rollback()
        return (
            "Cannot delete this flight because a flight leg or "
            "another record may reference it.",
            400
        )
    finally:
        cursor.close()
        connection.close()

@app.route("/flight_legs")
def flight_legs():
    search = request.args.get("search", "").strip()

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    if search:
        keyword = "%" + search + "%"
        cursor.execute("""
            SELECT leg_id, flight_number, origin, destination,
                   actual_departure, actual_arrival
            FROM FlightLeg
            WHERE CAST(leg_id AS CHAR) LIKE %s
               OR flight_number LIKE %s
               OR origin LIKE %s
               OR destination LIKE %s
            ORDER BY leg_id
        """, (keyword, keyword, keyword, keyword))
    else:
        cursor.execute("""
            SELECT leg_id, flight_number, origin, destination,
                   actual_departure, actual_arrival
            FROM FlightLeg
            ORDER BY leg_id
        """)

    legs = cursor.fetchall()

    cursor.execute("""
        SELECT flight_number, origin, destination
        FROM FlightSchedule
        ORDER BY flight_number
    """)
    flights = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "flight_legs.html",
        legs=legs,
        flights=flights,
        search=search
    )

@app.route("/add_flight_leg", methods=["POST"])
def add_flight_leg():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        flight_number = request.form["flight_number"]
        origin = request.form["origin"].strip().upper()
        destination = request.form["destination"].strip().upper()
        departure = request.form.get("actual_departure", "").strip() or None
        arrival = request.form.get("actual_arrival", "").strip() or None
        if not origin or not destination:
            return "Origin and destination are required.", 400
        if origin == destination:
            return "Origin and destination must be different.", 400
        if departure and arrival and arrival < departure:
            return "Actual arrival must not be earlier than departure.", 400
        cursor.execute("""
            INSERT INTO FlightLeg
                (flight_number, origin, destination,
                 actual_departure, actual_arrival)
            VALUES (%s, %s, %s, %s, %s)
        """, (flight_number, origin, destination, departure, arrival))
        connection.commit()
        return redirect(url_for("flight_legs"))
    except Exception as error:
        connection.rollback()
        return f"Could not add flight leg: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/edit_flight_leg/<int:leg_id>", methods=["GET", "POST"])
def edit_flight_leg(leg_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if request.method == "POST":
            flight_number = request.form["flight_number"]
            origin = request.form["origin"].strip().upper()
            destination = request.form["destination"].strip().upper()
            departure = request.form.get("actual_departure", "").strip() or None
            arrival = request.form.get("actual_arrival", "").strip() or None
            if not origin or not destination:
                return "Origin and destination are required.", 400
            if origin == destination:
                return "Origin and destination must be different.", 400
            if departure and arrival and arrival < departure:
                return "Actual arrival must not be earlier than departure.", 400
            cursor.execute("""
                UPDATE FlightLeg
                SET flight_number = %s,
                    origin = %s,
                    destination = %s,
                    actual_departure = %s,
                    actual_arrival = %s
                WHERE leg_id = %s
            """, (
                flight_number, origin, destination,
                departure, arrival, leg_id
            ))
            if cursor.rowcount == 0:
                connection.rollback()
                return "Flight leg not found or no changes were made.", 404
            connection.commit()
            return redirect(url_for("flight_legs"))
        cursor.execute(
            "SELECT * FROM FlightLeg WHERE leg_id = %s",
            (leg_id,)
        )
        leg = cursor.fetchone()
        if leg is None:
            return "Flight leg not found.", 404
        cursor.execute("""
            SELECT flight_number, origin, destination
            FROM FlightSchedule
            ORDER BY flight_number
        """)
        flights = cursor.fetchall()
        return render_template(
            "edit_flight_leg.html",
            leg=leg,
            flights=flights
        )
    except Exception as error:
        connection.rollback()
        return f"Could not update flight leg: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/delete_flight_leg/<int:leg_id>", methods=["POST"])
def delete_flight_leg(leg_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM FlightLeg WHERE leg_id = %s",
            (leg_id,)
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return "Flight leg not found.", 404
        connection.commit()
        return redirect(url_for("flight_legs"))
    except Exception:
        connection.rollback()
        return (
            "Cannot delete this flight leg because a reservation "
            "or another record may still reference it.",
            400
        )
    finally:
        cursor.close()
        connection.close()

@app.route("/flight_costs")
def flight_costs():
    search = request.args.get("search", "").strip()
    valid_date = request.args.get("valid_date", "").strip()

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT flight_number, aircraft_code,
               valid_from, valid_to, amount
        FROM FlightCost
        WHERE 1=1
    """
    params = []

    if search:
        keyword = "%" + search + "%"
        query += """
            AND (flight_number LIKE %s
                 OR aircraft_code LIKE %s)
        """
        params.extend([keyword, keyword])

    if valid_date:
        query += """
            AND valid_from <= %s
            AND valid_to >= %s
        """
        params.extend([valid_date, valid_date])

    query += " ORDER BY flight_number, valid_from"

    cursor.execute(query, tuple(params))
    costs = cursor.fetchall()

    cursor.execute("""
        SELECT flight_number
        FROM FlightSchedule
        ORDER BY flight_number
    """)
    flights = cursor.fetchall()

    cursor.execute("""
        SELECT aircraft_code
        FROM AircraftType
        ORDER BY aircraft_code
    """)
    aircraft_types = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "flight_costs.html",
        costs=costs,
        flights=flights,
        aircraft_types=aircraft_types,
        search=search,
        valid_date=valid_date
    )

@app.route("/add_flight_cost", methods=["POST"])
def add_flight_cost():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        flight_number = request.form["flight_number"]
        aircraft_code = request.form["aircraft_code"]
        valid_from = date.fromisoformat(request.form["valid_from"])
        valid_to = date.fromisoformat(request.form["valid_to"])
        amount = Decimal(request.form["amount"])
        if valid_to < valid_from:
            return "Valid To must be on or after Valid From.", 400
        if not amount.is_finite() or amount <= 0:
            return "Amount must be greater than zero.", 400
        cursor.execute("""
            INSERT INTO FlightCost
                (flight_number, aircraft_code, valid_from, valid_to, amount)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            flight_number, aircraft_code,
            valid_from, valid_to, amount
        ))
        connection.commit()
        return redirect(url_for("flight_costs"))
    except (ValueError, InvalidOperation):
        connection.rollback()
        return "Please enter valid dates and an amount.", 400
    except Exception as error:
        connection.rollback()
        return f"Could not add flight cost. Check for duplicate keys and valid references. Details: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/edit_flight_cost/<string:flight_number>/<string:aircraft_code>/<string:valid_from>",
           methods=["GET", "POST"])
def edit_flight_cost(flight_number, aircraft_code, valid_from):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if request.method == "POST":
            new_valid_from = date.fromisoformat(request.form["valid_from"])
            valid_to = date.fromisoformat(request.form["valid_to"])
            amount = Decimal(request.form["amount"])
            if valid_to < new_valid_from:
                return "Valid To must be on or after Valid From.", 400
            if not amount.is_finite() or amount <= 0:
                return "Amount must be greater than zero.", 400
            cursor.execute("""
                UPDATE FlightCost
                SET valid_from = %s, valid_to = %s, amount = %s
                WHERE flight_number = %s
                  AND aircraft_code = %s
                  AND valid_from = %s
            """, (
                new_valid_from, valid_to, amount,
                flight_number, aircraft_code, valid_from
            ))
            if cursor.rowcount == 0:
                connection.rollback()
                return "Cost record not found or no changes were made.", 404
            connection.commit()
            return redirect(url_for("flight_costs"))
        cursor.execute("""
            SELECT *
            FROM FlightCost
            WHERE flight_number = %s
              AND aircraft_code = %s
              AND valid_from = %s
        """, (flight_number, aircraft_code, valid_from))
        cost = cursor.fetchone()
        if cost is None:
            return "Cost record not found.", 404
        return render_template("edit_flight_cost.html", cost=cost)
    except (ValueError, InvalidOperation):
        connection.rollback()
        return "Please enter valid dates and an amount.", 400
    except Exception as error:
        connection.rollback()
        return f"Could not update flight cost: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/delete_flight_cost/<string:flight_number>/<string:aircraft_code>/<string:valid_from>",
           methods=["POST"])
def delete_flight_cost(flight_number, aircraft_code, valid_from):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            DELETE FROM FlightCost
            WHERE flight_number = %s
              AND aircraft_code = %s
              AND valid_from = %s
        """, (flight_number, aircraft_code, valid_from))
        if cursor.rowcount == 0:
            connection.rollback()
            return "Cost record not found.", 404
        connection.commit()
        return redirect(url_for("flight_costs"))
    except Exception:
        connection.rollback()
        return "Could not delete this flight cost because another record may reference it.", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/reservation_payments", methods=["GET", "POST"])
def reservation_payments():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if request.method == "POST":
            reservation_id = int(request.form["reservation_id"])
            payment_id = int(request.form["payment_id"])
            cursor.execute("""
                SELECT reservation_id
                FROM Reservation
                WHERE reservation_id = %s
            """, (reservation_id,))
            if cursor.fetchone() is None:
                return "Reservation not found.", 404
            cursor.execute("""
                SELECT payment_id
                FROM Payment
                WHERE payment_id = %s
            """, (payment_id,))
            if cursor.fetchone() is None:
                return "Payment not found.", 404
            cursor.execute("""
                SELECT reservation_id
                FROM ReservationPayment
                WHERE reservation_id = %s
                  AND payment_id = %s
            """, (reservation_id, payment_id))
            if cursor.fetchone():
                return "This payment is already linked to that reservation.", 400
            cursor.execute("""
                INSERT INTO ReservationPayment
                    (reservation_id, payment_id)
                VALUES (%s, %s)
            """, (reservation_id, payment_id))
            connection.commit()
            return redirect(url_for("reservation_payments"))
        cursor.execute("""
            SELECT
                rp.reservation_id,
                rp.payment_id,
                p.first_name,
                p.last_name,
                pay.status_code,
                pay.payment_date,
                pay.amount
            FROM ReservationPayment rp
            JOIN Reservation r
                ON rp.reservation_id = r.reservation_id
            JOIN Passenger p
                ON r.passenger_id = p.passenger_id
            JOIN Payment pay
                ON rp.payment_id = pay.payment_id
            ORDER BY rp.reservation_id, rp.payment_id
        """)
        links = cursor.fetchall()
        cursor.execute("""
            SELECT reservation_id
            FROM Reservation
            ORDER BY reservation_id
        """)
        reservations = cursor.fetchall()
        cursor.execute("""
            SELECT payment_id, amount, status_code
            FROM Payment
            ORDER BY payment_id
        """)
        payments = cursor.fetchall()
        return render_template(
            "reservation_payments.html",
            links=links,
            reservations=reservations,
            payments=payments
        )
    except ValueError:
        connection.rollback()
        return "Please select valid reservation and payment IDs.", 400
    except Exception as error:
        connection.rollback()
        return f"Could not process the payment link: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route(
    "/unlink_payment/<int:reservation_id>/<int:payment_id>",
    methods=["POST"]
)
def unlink_payment(reservation_id, payment_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            DELETE FROM ReservationPayment
            WHERE reservation_id = %s
              AND payment_id = %s
        """, (reservation_id, payment_id))
        if cursor.rowcount == 0:
            connection.rollback()
            return "Payment link not found.", 404
        connection.commit()
        return redirect(url_for("reservation_payments"))
    except Exception as error:
        connection.rollback()
        return f"Could not remove payment link: {error}", 400
    finally:
        cursor.close()
        connection.close()
@app.route("/reservation_legs", methods=["GET", "POST"])
def reservation_legs():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == "POST":
            reservation_id = request.form.get("reservation_id")
            leg_id = request.form.get("leg_id")
            if not reservation_id or not leg_id:
                return "Please select a reservation and flight leg."
            reservation_id = int(reservation_id)
            leg_id = int(leg_id)
            cursor.execute(
                "SELECT reservation_id FROM Reservation WHERE reservation_id = %s",
                (reservation_id,)
            )
            reservation = cursor.fetchone()
            cursor.execute(
                "SELECT leg_id FROM FlightLeg WHERE leg_id = %s",
                (leg_id,)
            )
            leg = cursor.fetchone()
            if not reservation or not leg:
                return "Reservation or flight leg not found."
            cursor.execute(
                """
                SELECT reservation_id
                FROM ReservationLeg
                WHERE reservation_id = %s AND leg_id = %s
                """,
                (reservation_id, leg_id)
            )
            if cursor.fetchone():
                return "This reservation is already linked to that flight leg."
            cursor.execute(
                """
                INSERT INTO ReservationLeg (reservation_id, leg_id)
                VALUES (%s, %s)
                """,
                (reservation_id, leg_id)
            )
            conn.commit()
            return redirect(url_for("reservation_legs"))
        cursor.execute(
            """
            SELECT
                rl.reservation_id,
                rl.leg_id,
                p.first_name,
                p.last_name,
                fl.flight_number,
                fl.origin,
                fl.destination,
                fl.actual_departure,
                fl.actual_arrival
            FROM ReservationLeg rl
            JOIN Reservation r
                ON rl.reservation_id = r.reservation_id
            JOIN Passenger p
                ON r.passenger_id = p.passenger_id
            JOIN FlightLeg fl
                ON rl.leg_id = fl.leg_id
            ORDER BY rl.reservation_id, rl.leg_id
            """
        )
        links = cursor.fetchall()
        cursor.execute(
            "SELECT reservation_id FROM Reservation ORDER BY reservation_id"
        )
        reservations = cursor.fetchall()
        cursor.execute(
            """
            SELECT leg_id, flight_number, origin, destination
            FROM FlightLeg
            ORDER BY leg_id
            """
        )
        legs = cursor.fetchall()
        return render_template(
            "reservation_legs.html",
            links=links,
            reservations=reservations,
            legs=legs
        )
    except Exception as e:
        conn.rollback()
        return f"Could not process the reservation-flight leg link: {e}"
    finally:
        cursor.close()
        conn.close()


@app.route("/booking_agents")
def booking_agents():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT agent_id, agent_name, details
        FROM BookingAgent
        ORDER BY agent_id
    """)

    agents = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "booking_agents.html",
        agents=agents
    )


@app.route("/add_booking_agent", methods=["POST"])
def add_booking_agent():
    agent_name = request.form["agent_name"].strip()
    details = request.form.get("details", "").strip()

    if not agent_name:
        return "Agent name is required.", 400

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO BookingAgent (agent_name, details)
            VALUES (%s, %s)
        """, (agent_name, details or None))

        connection.commit()

    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return f"Error adding booking agent: {e}"

    cursor.close()
    connection.close()

    return redirect(url_for("booking_agents"))

@app.route("/edit_booking_agent/<int:agent_id>", methods=["GET", "POST"])
def edit_booking_agent(agent_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":
        agent_name = request.form["agent_name"].strip()
        details = request.form.get("details", "").strip()

        if not agent_name:
            cursor.close()
            connection.close()
            return "Agent name is required.", 400

        try:
            cursor.execute("""
                UPDATE BookingAgent
                SET agent_name = %s, details = %s
                WHERE agent_id = %s
            """, (agent_name, details or None, agent_id))

            connection.commit()
            cursor.close()
            connection.close()

            return redirect(url_for("booking_agents"))

        except Exception as e:
            connection.rollback()
            cursor.close()
            connection.close()
            return f"Error updating booking agent: {e}"

    cursor.execute("""
        SELECT agent_id, agent_name, details
        FROM BookingAgent
        WHERE agent_id = %s
    """, (agent_id,))

    agent = cursor.fetchone()

    cursor.close()
    connection.close()

    if agent is None:
        return "Booking agent not found.", 404

    return render_template("edit_booking_agent.html", agent=agent)


@app.route("/delete_booking_agent/<int:agent_id>", methods=["POST"])
def delete_booking_agent(agent_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM Reservation
            WHERE agent_id = %s
        """, (agent_id,))

        result = cursor.fetchone()

        if result["total"] > 0:
            cursor.close()
            connection.close()
            return (
                "Cannot delete this agent because existing reservations "
                "refer to them.",
                400
            )

        cursor.execute("""
            DELETE FROM BookingAgent
            WHERE agent_id = %s
        """, (agent_id,))

        if cursor.rowcount == 0:
            connection.rollback()
            cursor.close()
            connection.close()
            return "Booking agent not found.", 404

        connection.commit()

    except Exception as e:
        connection.rollback()
        cursor.close()
        connection.close()
        return f"Error deleting booking agent: {e}"

    cursor.close()
    connection.close()

    return redirect(url_for("booking_agents"))


@app.route("/unlink_leg/<int:reservation_id>/<int:leg_id>", methods=["POST"])
def unlink_leg(reservation_id, leg_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM ReservationLeg
            WHERE reservation_id = %s AND leg_id = %s
            """,
            (reservation_id, leg_id)
        )

        conn.commit()
        return redirect(url_for("reservation_legs"))

    except Exception as e:
        conn.rollback()
        return f"Could not unlink flight leg: {e}"

    finally:
        cursor.close()
        conn.close()

@app.route("/reservation_details")
def reservation_details():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                r.reservation_id,
                r.passenger_id,
                r.agent_id,
                r.status_code,
                r.ticket_code,
                r.class_code,
                r.created_at,
                r.party_size,
                p.first_name,
                p.last_name
            FROM Reservation r
            JOIN Passenger p
                ON r.passenger_id = p.passenger_id
            ORDER BY r.reservation_id
        """)
        reservations = cursor.fetchall()
        selected_id = request.args.get("reservation_id")
        details = None
        payments = []
        legs = []
        if selected_id:
            cursor.execute("""
                SELECT
                    r.*,
                    p.first_name,
                    p.last_name,
                    p.email,
                    p.phone
                FROM Reservation r
                JOIN Passenger p
                    ON r.passenger_id = p.passenger_id
                WHERE r.reservation_id = %s
            """, (selected_id,))
            details = cursor.fetchone()
            if details:
                cursor.execute("""
                    SELECT
                        pay.payment_id,
                        pay.status_code,
                        pay.payment_date,
                        pay.amount
                    FROM ReservationPayment rp
                    JOIN Payment pay
                        ON rp.payment_id = pay.payment_id
                    WHERE rp.reservation_id = %s
                    ORDER BY pay.payment_id
                """, (selected_id,))
                payments = cursor.fetchall()
                cursor.execute("""
                    SELECT
                        fl.leg_id,
                        fl.flight_number,
                        fl.origin,
                        fl.destination,
                        fl.actual_departure,
                        fl.actual_arrival
                    FROM ReservationLeg rl
                    JOIN FlightLeg fl
                        ON rl.leg_id = fl.leg_id
                    WHERE rl.reservation_id = %s
                    ORDER BY fl.leg_id
                """, (selected_id,))
                legs = cursor.fetchall()
        return render_template(
            "reservation_details.html",
            reservations=reservations,
            details=details,
            payments=payments,
            legs=legs,
            selected_id=selected_id
        )
    except Exception as e:
        return f"Could not load reservation details: {e}"
    finally:
        cursor.close()
        conn.close()
if __name__ == "__main__":
    app.run(debug=False)
