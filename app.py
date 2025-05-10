import os
import re
from datetime import datetime

from flask import Flask, render_template, request
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.environ.get('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['feedback_db']
collection = db['feedback']

def load_mistakes():
    """
    Parse MISTAKES.md and return a list of mistakes with their penalties.
    """
    mistakes = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, 'MISTAKES.md')
    pattern = re.compile(r'^(?P<name>.*?)\s*[-–]?\s*(?P<penalty>\d+/\d+|\d+(?:\.\d+)?)')
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = pattern.match(line)
            if not m:
                continue
            name = m.group('name').strip()
            penalty_text = m.group('penalty')
            if '/' in penalty_text:
                num, denom = penalty_text.split('/')
                penalty = float(num) / float(denom)
            else:
                penalty = float(penalty_text)
            mistakes.append({'name': name, 'penalty': penalty})
    return mistakes

# Load mistakes once at startup
mistakes_list = load_mistakes()

# Initialize Flask app
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        student_name = request.form.get('student_name', '').strip()
        student_email = request.form.get('student_email', '').strip()

        total_penalty = 0.0
        occurrences = []
        # Calculate penalties
        for idx, m in enumerate(mistakes_list):
            count = int(request.form.get(f'count_{idx}', 0))
            occ_penalty = count * m['penalty']
            total_penalty += occ_penalty
            occurrences.append({'name': m['name'], 'count': count, 'penalty': m['penalty']})

        score = max(100.0 - total_penalty, 0.0)

        # Store feedback in MongoDB
        doc = {
            'student_name': student_name,
            'student_email': student_email,
            'occurrences': occurrences,
            'score': score,
            'timestamp': datetime.utcnow()
        }
        collection.insert_one(doc)

        return render_template('result.html',
                               student_name=student_name,
                               student_email=student_email,
                               score=score)

    # GET request
    return render_template('feedback_form.html', mistakes=(enumerate(mistakes_list)))

if __name__ == '__main__':
    app.run(port=80, host='0.0.0.0')