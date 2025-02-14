from flask import Flask, render_template, request, send_from_directory  # type: ignore
import requests  # type: ignore
from datetime import datetime

app = Flask(__name__, template_folder=".", static_folder=".")

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d'):
    return datetime.fromtimestamp(value).strftime(format)

def get_division(contest_name):
    if "Div. 1" in contest_name:
        return "DIV-1"
    elif "Div. 2" in contest_name:
        return "DIV-2"
    elif "Div. 3" in contest_name:
        return "DIV-3"
    else:
        return "N/A"

@app.route('/', methods=['GET', 'POST'])
def index():
    rating_options = list(range(800, 3600, 100))
    
    if request.method == 'POST':
        username = request.form.get('username')
        rating_input = request.form.get('rating')
        
        try:
            rating = int(rating_input)
        except ValueError:
            return "Rating must be an integer", 400

        url = f"https://codeforces.com/api/user.status?handle={username}"
        response = requests.get(url)
        if response.status_code != 200:
            return "Error calling Codeforces API.", 500

        data = response.json()
        if data['status'] != 'OK':
            return "Error from Codeforces API: " + data.get('comment', 'Unknown error.')

        submissions = data['result']
        solved_problems = {}
        solved_problems_of_rating = {}

        for sub in submissions:
            if sub.get('verdict') == 'OK':
                problem = sub.get('problem')
                key = f"{problem.get('contestId')}-{problem.get('index')}"
                
                if key not in solved_problems:
                    solved_problems[key] = problem.copy()
                    solved_problems[key]['submission_date'] = sub.get('creationTimeSeconds')
                
                if problem.get('rating') == rating and key not in solved_problems_of_rating:
                    solved_problems_of_rating[key] = problem.copy()
                    solved_problems_of_rating[key]['submission_date'] = sub.get('creationTimeSeconds')

        total_solved_problems = len(solved_problems)
        total_solved_problems_of_rating = len(solved_problems_of_rating)
        percentage_solved = (
            (total_solved_problems_of_rating / total_solved_problems) * 100
            if total_solved_problems > 0 else 0
        )

        problems_list = list(solved_problems_of_rating.values())

        contest_info = {}
        contests_url = "https://codeforces.com/api/contest.list?gym=false"
        contest_response = requests.get(contests_url)
        if contest_response.status_code == 200:
            contest_data = contest_response.json()
            if contest_data.get("status") == "OK":
                for contest in contest_data["result"]:
                    contest_info[contest["id"]] = {
                        "startTime": contest.get("startTimeSeconds", 0),
                        "name": contest.get("name", "")
                    }

        def sort_key(problem):
            contest_data = contest_info.get(problem.get('contestId'))
            if contest_data and contest_data.get('startTime'):
                return contest_data.get('startTime')
            return problem.get('submission_date', 0)

        problems_list.sort(key=sort_key, reverse=True)

        for problem in problems_list:
            contest_data = contest_info.get(problem.get('contestId'))
            if contest_data:
                problem['contestStart'] = contest_data.get('startTime')
                problem['division'] = contest_data.get('name', '')
            else:
                problem['contestStart'] = problem.get('submission_date', 0)
                problem['division'] = "N/A"

        return render_template(
            'result.html',
            problems=problems_list,
            username=username,
            rating=rating,
            total_solved_problems=total_solved_problems,
            total_solved_problems_of_rating=total_solved_problems_of_rating,
            percentage_solved=percentage_solved
        )

    return render_template('index.html', rating_options=rating_options)

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(".", filename)

if __name__ == '__main__':
    app.run(debug=True)