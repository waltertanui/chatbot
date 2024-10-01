import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
import re


# Load environment variables from .env file
load_dotenv()

# Get Firebase credentials path from .env
firebase_credentials_path = os.getenv('FIREBASE_CREDENTIALS_PATH')

# Initialize Firebase
cred = credentials.Certificate(firebase_credentials_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)



def extract_preferences(user_input):
    preferences = {}
    
    # Extract fuel type
    fuel_types = ['electric', 'gasoline', 'petrol', 'hybrid']
    for fuel in fuel_types:
        if fuel in user_input.lower():
            preferences['fuel'] = fuel
            break
    
    # Extract price
    price_match = re.search(r'\$?(\d+),?(\d+)?', user_input)
    if price_match:
        price = int(price_match.group(1) + (price_match.group(2) or ''))
        preferences['price'] = price
    
    # Extract brand
    brands = ['BMW', 'Mercedes-Benz', 'Toyota', 'Nissan', 'Lamborghini', 'Hyundai']
    for brand in brands:
        if brand.lower() in user_input.lower():
            preferences['brand'] = brand
            break
    
    # Extract car type
    car_types = ['SUV', 'Sedan', 'Truck', 'Convertible']
    for car_type in car_types:
        if car_type.lower() in user_input.lower():
            preferences['carType'] = car_type
            break
    
    # Extract color
    colors = ['black', 'white', 'red', 'blue', 'green', 'silver', 'gray']
    for color in colors:
        if color in user_input.lower():
            preferences['color'] = color
            break
    
    return preferences

def query_firestore(preferences):
    cars_ref = db.collection('cars')
    query = cars_ref

    if 'fuel' in preferences:
        query = query.where('fuel', '==', preferences['fuel'].capitalize())
    if 'brand' in preferences:
        query = query.where('brand', '==', preferences['brand'])
    if 'carType' in preferences:
        query = query.where('carType', '==', preferences['carType'])
    if 'color' in preferences:
        query = query.where('color', '==', preferences['color'].capitalize())
    
    results = query.limit(5).get()
    cars = [doc.to_dict() for doc in results]
    
    if 'price' in preferences:
        cars = [car for car in cars if float(car.get('price', 0)) <= float(preferences['price'])]
    
    return cars

def format_car(car):
    return f"""
{car.get('brand', 'N/A')} {car.get('name', 'N/A')}
Type: {car.get('carType', 'N/A')}
Color: {car.get('color', 'N/A')}
Interior Color: {car.get('interiorColor', 'N/A')}
Transmission: {car.get('transmission', 'N/A')}
Engine: {car.get('engine', 'N/A')}
Fuel: {car.get('fuel', 'N/A')}
Mileage: {car.get('mileage', 'N/A')}
Price: ${car.get('price', 'N/A')}
VIN: {car.get('VIN', 'N/A')}
"""

def generate_response(cars, preferences):
    if not cars:
        return "I'm sorry, I couldn't find any cars matching your preferences. Could you please try with different criteria?"
    
    response = f"I found {len(cars)} car(s) matching your preferences. Here are the details:\n\n"
    for i, car in enumerate(cars, 1):
        response += f"{i}. {format_car(car)}\n"
    
    response += "\nIs there anything specific you'd like to know about these cars?"
    return response

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Car Recommendation Chatbot API"}), 200

@app.route('/chat', methods=['POST'])
@limiter.limit("10 per minute")
def chat():
    if not request.json or 'message' not in request.json:
        return jsonify({"error": "Invalid request. 'message' field is required."}), 400
    
    user_input = request.json['message']
    if not isinstance(user_input, str) or len(user_input) > 500:  # Example input validation
        return jsonify({"error": "Invalid input. Message must be a string no longer than 500 characters."}), 400
    
    preferences = extract_preferences(user_input)
    cars = query_firestore(preferences)
    response = generate_response(cars, preferences)
    
    return jsonify({'response': response}), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
