from flask import (
    Flask,
    render_template,
    request,
    jsonify
)
import datetime
import csv


# Create the application instance
app = Flask(__name__, template_folder="")

# Create a URL route in our application for "/"
@app.route('/')
def home():
    """
    This function just responds to the browser ULR
    localhost:5000/

    :return:        the rendered template 'home.html'
    """
    return render_template('index.html')


@app.route('/results')
def results():
    return render_template('results.html')


@app.route('/today', methods=['POST', 'GET'])
def today():
    # return today's voting results
    return jsonify(get_resuts_by_date(datetime.datetime.now().strftime("%x")))


@app.route('/getresults', methods=['POST', 'GET'])
def get_results():
    date = request.args['date']

    return jsonify(get_resuts_by_date(date))


@app.route('/getall', methods=['GET'])
def get_all_results():
    results = []

    csv_name = "voting_data.csv"

    dates = []

    with open(csv_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            if not dates.__contains__(row[0]):
                dates.append(row[0])

    for date in dates:
        results.append(get_resuts_by_date(date))

    return jsonify({"data": results, "dates": dates})


@app.route('/voted', methods=['POST', 'GET'])
def voted():
    my_ip = request.args['ip']

    if has_voted(my_ip):
        return "True"
    else:
        return "False"


@app.route('/poll', methods=['POST', 'GET'])
def poll():
    vote = request.args['answer']
    ip = request.args['ip']
    date = datetime.datetime.now().strftime("%x")

    # ensure client hasn't voted yet
    if not has_voted(ip):
        # append to csv
        with open('voting_data.csv', 'a') as fd:
            fd.write(date + "," + ip + "," + vote + '\n')

    return render_template('results.html')


# checks if vote has been made
def has_voted(ip):

    csv_name = "voting_data.csv"
    votes = {}

    with open(csv_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        date = datetime.datetime.now().strftime("%x")

        for row in csv_reader:
            if votes.has_key(row[0]):
                votes[str(row[0])].append(row[1])
            else:
                votes[str(row[0])] = [row[1]]

        # print(votes)
        if votes.has_key(date):
            for my_ip in votes[date]:
                if my_ip == ip:
                    return True

        return False


# gets results by date
def get_resuts_by_date(date):
    csv_name = "voting_data.csv"

    with open(csv_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0

        bullCount = 0
        bearCount = 0

        for row in csv_reader:
            if row[0] == date:
                if row[2] == "bull":
                    bullCount += 1
                else:
                    bearCount += 1
        return {"date": date, "bullCount": bullCount, "bearCount": bearCount}


# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    app.run(debug=True)