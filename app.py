from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    # Mock data as specified in the prompt
    tasks = [
        {
            "id": 1,
            "title": "Update documentation homepage",
            "assignee": "Alex",
            "status": "In Progress"
        },
        {
            "id": 2,
            "title": "Review security patch release",
            "assignee": "Jamie",
            "status": "Completed"
        },
        {
            "id": 3,
            "title": "Draft Q3 product roadmap",
            "assignee": "Morgan",
            "status": "To Do"
        }
    ]
    board_name = "Team Project Alpha Board"
    return render_template('index.html', board_name=board_name, tasks=tasks)

if __name__ == '__main__':
    # Flask app is configured to run on localhost (127.0.0.1) and port 5001 to avoid macOS port 5000 conflict
    app.run(host='127.0.0.1', port=5001, debug=True)

