from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import numpy as np
import os

# --- SETUP ---
app = Flask(__name__, template_folder='templates')
app.secret_key = "lab_secret_key"
CORS(app, supports_credentials=True)

# --- DATABASE ---
USERS = {"admin": "science"}

# --- PHYSICS ---
BOLTZMANN_K = 1.380649e-23
ELECTRON_Q = 1.60217663e-19

class DiodePhysics:
    def __init__(self, material, temp_c, zener_v, ideality):
        self.material = material
        self.temp_k = temp_c + 273.15
        self.vt = (BOLTZMANN_K * self.temp_k) / ELECTRON_Q
        self.zener_v = zener_v
        self.n = ideality
        base_is = 1e-12 if material in ['Si', 'Zener'] else 1e-6
        self.Is = base_is * (2 ** ((temp_c - 27) / 10.0))

    def calculate(self, voltage):
        if self.material == 'Zener' and voltage <= -self.zener_v:
            return -1.0 * (abs(voltage) - self.zener_v) / 2.0
        try:
            exponent = voltage / (self.n * self.vt)
            if exponent > 100: exponent = 100
            return self.Is * (np.exp(exponent) - 1)
        except: return 0.0

# --- ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if USERS.get(data.get('username')) == data.get('password'):
        session['user'] = data.get('username')
        return jsonify({"status": "success"})
    return jsonify({"status": "fail"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"status": "logged_out"})

@app.route('/api/measure', methods=['POST'])
def measure():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    model = DiodePhysics(data.get('material', 'Si'), float(data.get('temp', 27)), float(data.get('zener_v', 5.1)), float(data.get('ideality', 1.5)))
    v = float(data.get('voltage', 0))
    i = model.calculate(v)
    # Check for burnout
    status = "OPTIMAL"
    if abs(v*i) > 0.5: status = "CRITICAL (OVERHEAT)" 
    return jsonify({"current": i, "power": v*i, "status": status, "vt": model.vt, "is_leakage": model.Is})

@app.route('/api/sweep', methods=['POST'])
def sweep():
    if 'user' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    model = DiodePhysics(data.get('material', 'Si'), float(data.get('temp', 27)), float(data.get('zener_v', 5.1)), float(data.get('ideality', 1.5)))
    points = [{"v": round(v, 3), "i": model.calculate(v)} for v in np.linspace(float(data.get('start', -2)), 1.5, 150)]
    return jsonify({"data": points})

if __name__ == '__main__':
    app.run(debug=True, port=5000)